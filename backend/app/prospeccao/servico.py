from __future__ import annotations

import uuid
from decimal import Decimal

from app.auth.contexto import Contexto
from app.campanhas import repositorio as campanhas
from app.core.config import Settings
from app.core.sistema import como_sistema
from app.fila.fila import Fila, Job
from app.prospeccao import repositorio
from app.prospeccao.agente import carregar_agente
from app.prospeccao.esquemas import CandidatoDetalhe, ExecucaoOut, PaginaDeCandidatos
from app.qualificacao.repositorio import enfileirar_se_nao_houver

TIPO_JOB = "prospeccao"


class NaoEncontrado(Exception):
    pass


class ExecucaoEmAndamento(Exception):
    pass


# --- pela API ----------------------------------------------------------------------------


def iniciar_execucao(contexto: Contexto, campanha_id: uuid.UUID) -> ExecucaoOut:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    if repositorio.execucao_em_andamento(contexto.conn, campanha_id):
        raise ExecucaoEmAndamento
    job_id = Fila.enfileirar(contexto.conn, TIPO_JOB, campanha_id)
    execucao = repositorio.buscar_execucao(contexto.conn, job_id)
    assert execucao is not None
    return execucao


def buscar_execucao(contexto: Contexto, job_id: uuid.UUID) -> ExecucaoOut:
    execucao = repositorio.buscar_execucao(contexto.conn, job_id)
    if execucao is None:
        raise NaoEncontrado
    return execucao


def listar_execucoes(contexto: Contexto, campanha_id: uuid.UUID) -> list[ExecucaoOut]:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    return repositorio.listar_execucoes(contexto.conn, campanha_id)


def listar_candidatos(
    contexto: Contexto,
    campanha_id: uuid.UUID,
    status: str | None,
    limite: int,
    deslocamento: int,
    tier: str | None = None,
    segmento: str | None = None,
) -> PaginaDeCandidatos:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    return repositorio.listar_candidatos(
        contexto.conn, campanha_id, status, limite, deslocamento, tier, segmento
    )


def buscar_candidato(contexto: Contexto, candidato_id: uuid.UUID) -> CandidatoDetalhe:
    candidato = repositorio.buscar_candidato(contexto.conn, candidato_id)
    if candidato is None:
        raise NaoEncontrado
    return candidato


# --- pelo worker -------------------------------------------------------------------------


def executor(settings: Settings) -> ExecutorDeProspeccao:
    return ExecutorDeProspeccao(settings)


class ExecutorDeProspeccao:
    """Roda o agente de prospecção para a campanha do job e grava cada candidato na sua
    própria transação, para que o progresso sobreviva a uma interrupção."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def __call__(self, fila: Fila, job: Job) -> None:
        assert job.campanha_id is not None
        campanha_id = job.campanha_id
        banco = fila.banco

        def terminar(status: str, motivo: str | None = None) -> None:
            with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
                repositorio.terminar_execucao(conn, job.id, status, motivo)
                # Terminada a prospecção, o Agente 2 qualifica o que foi coletado.
                enfileirar_se_nao_houver(conn, "qualificacao", campanha_id)

        with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
            foto = repositorio.foto_da_campanha(conn, job.campanha_id)
            if foto is None:
                repositorio.terminar_execucao(conn, job.id, "falhou", "campanha_nao_encontrada")
                return
            gravadas = repositorio.candidatos_na_campanha(conn, job.campanha_id)

        if gravadas >= foto.limite_empresas:
            terminar("parcial", "limite_de_empresas")
            return
        if foto.saldo_teto_usd <= 0:
            terminar("parcial", "teto_de_gasto")
            return

        # A plataforma controla limite e teto: para de consumir o agente quando acabam.
        gasto = Decimal(0)
        agente = carregar_agente(self._settings.agente_prospeccao)
        for candidato in agente.executar(foto):
            with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
                resultado = repositorio.gravar_candidato(conn, job.campanha_id, job.id, candidato)
                repositorio.registrar_progresso(conn, job.id, resultado, candidato.custo_usd)
                fila.renovar_lease(conn, job.id)
            if resultado == "ja_processada":
                continue
            gasto += candidato.custo_usd
            if resultado == "gravada":
                gravadas += 1
            if gravadas >= foto.limite_empresas:
                terminar("parcial", "limite_de_empresas")
                return
            if gasto >= foto.saldo_teto_usd:
                terminar("parcial", "teto_de_gasto")
                return

        terminar("concluida")
