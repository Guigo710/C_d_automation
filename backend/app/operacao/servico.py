"""Operação (Agente 3): promoção dos aprovados e ficha de abordagem (ticket 09).

A promoção é código, numa única transação e idempotente por clique: gravar no banco precisa
dar sempre o mesmo resultado e não pode duplicar. A IA entra depois, só para escrever a ficha.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from app.auditoria import servico as auditoria
from app.auth.contexto import Contexto
from app.campanhas import repositorio as campanhas
from app.configuracao import chaves
from app.core.config import Settings
from app.core.sistema import como_sistema
from app.fila.fila import Fila, Job
from app.llm.cliente import RespostaInvalida, carregar_cliente
from app.operacao import prompt_ficha
from app.operacao import repositorio as repo
from app.operacao.esquemas import EmpresaDaCampanhaDetalhe, EmpresaDaCampanhaResumo, PromocaoOut
from app.qualificacao.repositorio import enfileirar_se_nao_houver, saldo

TIPO_JOB_FICHA = "ficha"
PAPEIS_QUE_VEEM_CONTATO = frozenset({"coordenador", "administrador"})


class NaoEncontrado(Exception):
    pass


def promover(
    contexto: Contexto, campanha_id: uuid.UUID, ids: list[uuid.UUID], chave: str
) -> PromocaoOut:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    anterior = repo.reservar_chave(contexto.conn, chave, campanha_id)
    if anterior is not None:
        return PromocaoOut.model_validate(anterior)

    criadas = repo.promover(contexto.conn, campanha_id, ids)
    for criada in criadas:
        decisao = repo.decisao_do_candidato(contexto.conn, criada["candidato_id"])
        if decisao and decisao["decidido_em"]:
            repo.registrar_no_historico(
                contexto.conn,
                criada["id"],
                "aprovada",
                decisao["decidido_por"],
                ocorrido_em=decisao["decidido_em"],
            )
        repo.registrar_no_historico(contexto.conn, criada["id"], "promovida", contexto.usuario.id)

    promovidos = {c["candidato_id"] for c in criadas}
    resultado = PromocaoOut(
        promovidas=[c["candidato_id"] for c in criadas],
        ignoradas=[i for i in dict.fromkeys(ids) if i not in promovidos],
    )
    repo.gravar_resultado(contexto.conn, chave, resultado.model_dump(mode="json"))
    if criadas:
        auditoria.registrar(
            contexto,
            "candidatos.promovidos",
            "campanha",
            campanha_id,
            {"candidatos": [str(i) for i in resultado.promovidas]},
        )
        enfileirar_se_nao_houver(contexto.conn, TIPO_JOB_FICHA, campanha_id)
    return resultado


def listar(contexto: Contexto, campanha_id: uuid.UUID) -> list[EmpresaDaCampanhaResumo]:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    return repo.listar(contexto.conn, campanha_id)


def detalhe(contexto: Contexto, empresa_da_campanha_id: uuid.UUID) -> EmpresaDaCampanhaDetalhe:
    linha = repo.buscar(contexto.conn, empresa_da_campanha_id)
    if linha is None:
        raise NaoEncontrado
    ve_contato = (
        contexto.usuario.papel in PAPEIS_QUE_VEEM_CONTATO
        or linha["responsavel_id"] == contexto.usuario.id
    )
    contatos = repo.contatos(contexto.conn, linha["empresa_id"]) if ve_contato else []
    eventos = repo.historico(contexto.conn, empresa_da_campanha_id)
    return repo.montar_detalhe(linha, contatos, not ve_contato, eventos)


# --- ficha (worker) ----------------------------------------------------------------------


def executor(settings: Settings, cofre: chaves.Cofre) -> ExecutorDeFicha:
    return ExecutorDeFicha(settings, cofre)


class ExecutorDeFicha:
    def __init__(self, settings: Settings, cofre: chaves.Cofre) -> None:
        self._settings = settings
        self._cofre = cofre

    def __call__(self, fila: Fila, job: Job) -> None:
        assert job.campanha_id is not None
        campanha_id = job.campanha_id

        def sistema() -> Any:
            return como_sistema(fila.banco, job.organizacao_id, job.criado_por)

        def terminar(status: str, motivo: str | None = None, erro: str | None = None) -> None:
            with sistema() as conn:
                conn.execute(
                    "UPDATE jobs SET status = %s, motivo_parada = %s, erro = %s, "
                    "terminado_em = now(), lease_ate = NULL WHERE id = %s",
                    (status, motivo, erro, job.id),
                )

        with sistema() as conn:
            chave_ia = chaves.obter_chave(conn, self._cofre, "anthropic")
        cliente = carregar_cliente(self._settings.cliente_ia)

        while True:
            with sistema() as conn:
                fichas = repo.fichas_em_preparo(conn, campanha_id, 50)
            if not fichas:
                break
            for ficha in fichas:
                with sistema() as conn:
                    sem_saldo = saldo(conn, campanha_id) <= 0
                if sem_saldo:
                    terminar("parcial", "teto_de_gasto")
                    return
                if chave_ia is None:
                    terminar(
                        "falhou",
                        "sem_chave_ia",
                        "Cadastre a chave da Claude API na configuração da organização",
                    )
                    return

                fatos = {
                    k: ficha[k]
                    for k in ("razao_social", "nome_fantasia", "segmento", "municipio_ibge",
                              "endereco", "site", "sinais")
                }  # fmt: skip
                entrada, ids = prompt_ficha.entrada(fatos, ficha["evidencias"])
                custo = Decimal(0)
                texto: str | None = None
                citados: list[str] = []
                for _ in range(2):
                    try:
                        gerada = cliente.gerar(
                            chave_api=chave_ia,
                            instrucoes=prompt_ficha.INSTRUCOES,
                            entrada=entrada,
                            esquema=prompt_ficha.ESQUEMA,
                            max_tokens=900,
                        )
                        custo += gerada.custo_usd
                        texto, citados = prompt_ficha.validar(gerada.dados, ids)
                        break
                    except (RespostaInvalida, prompt_ficha.FichaInvalida):
                        texto = None

                with sistema() as conn:
                    if texto is None:
                        repo.gravar_ficha(conn, ficha["id"], None, [], "falhou")
                    else:
                        repo.gravar_ficha(conn, ficha["id"], texto, citados, "pronta")
                    conn.execute(
                        "UPDATE jobs SET encontradas = encontradas + 1, "
                        "gravadas = gravadas + %s, custo_usd = custo_usd + %s, "
                        "ultima_atividade = now() WHERE id = %s",
                        (1 if texto else 0, custo, job.id),
                    )
                    fila.renovar_lease(conn, job.id)

        terminar("concluida")
