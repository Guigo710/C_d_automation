from __future__ import annotations

import uuid

from app.auth.contexto import Contexto
from app.campanhas import repositorio as campanhas
from app.core.config import Settings
from app.core.sistema import como_sistema
from app.fila.fila import Fila, Job
from app.prospeccao import repositorio
from app.prospeccao.agente import carregar_agente
from app.prospeccao.esquemas import CandidatoDetalhe, ExecucaoOut, PaginaDeCandidatos

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
    contexto: Contexto, campanha_id: uuid.UUID, status: str | None, limite: int, deslocamento: int
) -> PaginaDeCandidatos:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise NaoEncontrado
    return repositorio.listar_candidatos(contexto.conn, campanha_id, status, limite, deslocamento)


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
        banco = fila.banco

        with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
            foto = repositorio.foto_da_campanha(conn, job.campanha_id)
            if foto is None:
                repositorio.terminar_execucao(conn, job.id, "falhou", "campanha_nao_encontrada")
                return
            ja_gravadas = repositorio.candidatos_na_campanha(conn, job.campanha_id)
            if ja_gravadas >= foto.limite_empresas:
                repositorio.terminar_execucao(conn, job.id, "parcial", "limite_de_empresas")
                return

        agente = carregar_agente(self._settings.agente_prospeccao)
        gravadas = ja_gravadas
        for candidato in agente.executar(foto):
            with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
                resultado = repositorio.gravar_candidato(conn, job.campanha_id, job.id, candidato)
                repositorio.registrar_progresso(conn, job.id, resultado, candidato.custo_usd)
                fila.renovar_lease(conn, job.id)
            if resultado == "gravada":
                gravadas += 1
            if gravadas >= foto.limite_empresas:
                with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
                    repositorio.terminar_execucao(conn, job.id, "parcial", "limite_de_empresas")
                return

        with como_sistema(banco, job.organizacao_id, job.criado_por) as conn:
            repositorio.terminar_execucao(conn, job.id, "concluida")
