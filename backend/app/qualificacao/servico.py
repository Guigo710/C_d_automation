"""Agente 2: qualifica os candidatos coletados de uma campanha (ticket 07).

Exclusões, validação de contatos, geografia e qualidade dos dados são regras em código;
a IA dá só as notas de aderência e potencial, com justificativa e evidências citadas. Total
e tier são calculados pelo código com os pesos e cortes da organização, e cada candidato
guarda a versão das regras usada.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.auth.contexto import Contexto
from app.campanhas import repositorio as campanhas
from app.configuracao import chaves
from app.core.config import Settings
from app.core.sistema import como_sistema
from app.fila.fila import Fila, Job
from app.llm.cliente import MODELO_PADRAO, RespostaInvalida, carregar_cliente
from app.qualificacao import prompt, regras
from app.qualificacao import repositorio as repo

TIPO_JOB = "qualificacao"
TAMANHO_DO_LOTE = 50
TENTATIVAS_DA_IA = 2  # a resposta inválida é reenviada uma vez
CAMPOS_DE_CONTATO = frozenset({"telefone", "email", "whatsapp", "contato"})


class NaoEncontrado(Exception):
    pass


def enfileirar(contexto: Contexto, campanha_id: uuid.UUID) -> None:
    """Pedido manual do coordenador (por exemplo, depois de cadastrar a chave da IA)."""
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    repo.enfileirar_se_nao_houver(contexto.conn, TIPO_JOB, campanha_id)


def executor(settings: Settings, cofre: chaves.Cofre) -> ExecutorDeQualificacao:
    return ExecutorDeQualificacao(settings, cofre)


class ExecutorDeQualificacao:
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
            vigentes = repo.regras_vigentes(conn)
            contexto = repo.contexto_da_campanha(conn, campanha_id)
            chave_ia = chaves.obter_chave(conn, self._cofre, "anthropic")
        if vigentes is None:
            terminar(
                "falhou",
                "organizacao_sem_configuracao",
                "A organização não tem regras configuradas",
            )
            return
        if contexto is None:
            terminar("falhou", "campanha_nao_encontrada")
            return

        cliente = carregar_cliente(self._settings.cliente_ia)
        instrucoes = prompt.instrucoes(vigentes.perfil_ideal)

        while True:
            with sistema() as conn:
                lote = repo.proximos_coletados(conn, campanha_id, TAMANHO_DO_LOTE)
            if not lote:
                break
            for candidato in lote:
                empresa = _empresa(candidato)
                with sistema() as conn:
                    duplicado = repo.mesma_raiz_em_uso(
                        conn, campanha_id, candidato["empresa_id"], empresa.cnpj
                    )
                motivo = regras.exclusao(
                    empresa,
                    contexto.municipios,
                    contexto.clientes_atuais,
                    duplicado,
                    contexto.bloqueios,
                )
                if motivo:
                    with sistema() as conn:
                        repo.gravar_recusa_sugerida(conn, candidato["id"], motivo, vigentes.versao)
                        repo.registrar_progresso(conn, job.id, "recusada", Decimal(0))
                        fila.renovar_lease(conn, job.id)
                    continue

                status_contatos = {
                    c["id"]: regras.validar_contato(regras.Contato(c["tipo"], c["valor"]))
                    for c in candidato["contatos"]
                }
                geografia = regras.nota_geografia(
                    empresa.municipio_ibge, contexto.com_rota, contexto.atendidos
                )
                dados = regras.nota_dados(
                    empresa, list(status_contatos.values()), datetime.now(UTC)
                )

                with sistema() as conn:
                    sem_saldo = repo.saldo(conn, campanha_id) <= 0
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

                evidencias_para_ia = [
                    e for e in candidato["evidencias"] if e["campo"] not in CAMPOS_DE_CONTATO
                ]
                entrada, ids = prompt.entrada(_fatos(candidato), evidencias_para_ia)
                hash_ = hashlib.sha256(
                    f"{MODELO_PADRAO}\n{prompt.VERSAO}\n{instrucoes}\n{entrada}".encode()
                ).hexdigest()
                with sistema() as conn:
                    em_cache = repo.ler_cache(conn, hash_)

                custo = Decimal(0)
                resposta: dict[str, Any] | None = None
                motivo_revisao = ""
                if em_cache is not None:
                    resposta = prompt.validar(em_cache, ids)
                else:
                    for _ in range(TENTATIVAS_DA_IA):
                        try:
                            gerada = cliente.gerar(
                                chave_api=chave_ia,
                                instrucoes=instrucoes,
                                entrada=entrada,
                                esquema=prompt.ESQUEMA,
                                max_tokens=1000,
                            )
                            custo += gerada.custo_usd
                            resposta = prompt.validar(gerada.dados, ids)
                            with sistema() as conn:
                                repo.gravar_cache(conn, hash_, gerada.modelo, gerada.dados)
                            break
                        except (RespostaInvalida, prompt.RespostaForaDoEsquema) as erro:
                            motivo_revisao = str(erro)

                with sistema() as conn:
                    repo.marcar_contatos(conn, status_contatos)
                    if resposta is None:
                        repo.gravar_revisao(
                            conn, candidato["id"], motivo_revisao, geografia, dados,
                            prompt.VERSAO, vigentes.versao,
                        )  # fmt: skip
                        repo.registrar_progresso(conn, job.id, "revisao", custo)
                    else:
                        total, tier = regras.total_e_tier(
                            vigentes.regras,
                            resposta["aderencia"],
                            resposta["potencial"],
                            geografia,
                            dados,
                        )
                        notas = {
                            "aderencia": resposta["aderencia"],
                            "potencial": resposta["potencial"],
                            "geografia": geografia,
                            "dados": dados,
                            "total": total,
                        }
                        if tier is None:
                            repo.gravar_recusa_sugerida(
                                conn, candidato["id"], "fora_do_perfil", vigentes.versao, **notas
                            )
                            repo.registrar_progresso(conn, job.id, "recusada", custo)
                        else:
                            repo.gravar_qualificacao(
                                conn,
                                candidato["id"],
                                notas=notas,
                                tier=tier,
                                resposta=resposta,
                                modelo=MODELO_PADRAO,
                                versao_prompt=prompt.VERSAO,
                                versao_regras=vigentes.versao,
                                baixa_confianca=resposta["confianca"] < prompt.LIMIAR_DE_CONFIANCA,
                            )
                            repo.registrar_progresso(conn, job.id, "qualificada", custo)
                    fila.renovar_lease(conn, job.id)

        terminar("concluida")


def _empresa(candidato: dict[str, Any]) -> regras.Empresa:
    return regras.Empresa(
        cnpj=candidato["cnpj"],
        situacao_cadastral=candidato["situacao_cadastral"],
        municipio_ibge=candidato["municipio_ibge"],
        site=candidato["site"],
        contatos=[regras.Contato(c["tipo"], c["valor"]) for c in candidato["contatos"]],
        evidencias=[
            regras.Evidencia(e["fonte"], e["coletado_em"]) for e in candidato["evidencias"]
        ],
    )


def _fatos(candidato: dict[str, Any]) -> dict[str, Any]:
    """O que a IA vê da empresa: nada de contato pessoal, só dados comerciais."""
    return {
        "razao_social": candidato["razao_social"],
        "nome_fantasia": candidato["nome_fantasia"],
        "segmento": candidato["segmento"],
        "municipio_ibge": candidato["municipio_ibge"],
        "endereco": candidato["endereco"],
        "site": candidato["site"],
        "sinais": candidato["sinais"],
    }
