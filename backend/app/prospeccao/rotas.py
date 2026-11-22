from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.prospeccao import servico
from app.prospeccao.esquemas import (
    CandidatoDetalhe,
    ExecucaoOut,
    PaginaDeCandidatos,
    StatusCandidato,
)
from app.qualificacao import servico as qualificacao

router = APIRouter(tags=["prospecção"])

Executar = Annotated[Contexto, Depends(exige("prospeccao.executar"))]
Ler = Annotated[Contexto, Depends(exige("prospeccao.ler"))]


def _nao_encontrado() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Não encontrado")


@router.post(
    "/campanhas/{campanha_id}/execucoes",
    response_model=ExecucaoOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def iniciar_execucao(campanha_id: uuid.UUID, contexto: Executar) -> ExecucaoOut:
    try:
        return servico.iniciar_execucao(contexto, campanha_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro
    except servico.ExecucaoEmAndamento as erro:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Já existe uma execução em andamento nesta campanha"
        ) from erro


@router.get("/campanhas/{campanha_id}/execucoes", response_model=list[ExecucaoOut])
def listar_execucoes(campanha_id: uuid.UUID, contexto: Ler) -> list[ExecucaoOut]:
    try:
        return servico.listar_execucoes(contexto, campanha_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro


@router.get("/execucoes/{execucao_id}", response_model=ExecucaoOut)
def buscar_execucao(execucao_id: uuid.UUID, contexto: Ler) -> ExecucaoOut:
    try:
        return servico.buscar_execucao(contexto, execucao_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro


@router.get("/campanhas/{campanha_id}/candidatos", response_model=PaginaDeCandidatos)
def listar_candidatos(
    campanha_id: uuid.UUID,
    contexto: Ler,
    status_candidato: Annotated[StatusCandidato | None, Query(alias="status")] = None,
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
    tier: Literal["A", "B", "C"] | None = None,
    segmento: str | None = None,
) -> PaginaDeCandidatos:
    try:
        return servico.listar_candidatos(
            contexto, campanha_id, status_candidato, limite, deslocamento, tier, segmento
        )
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro


@router.get("/candidatos/{candidato_id}", response_model=CandidatoDetalhe)
def buscar_candidato(candidato_id: uuid.UUID, contexto: Ler) -> CandidatoDetalhe:
    try:
        return servico.buscar_candidato(contexto, candidato_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro


@router.post("/campanhas/{campanha_id}/qualificacoes", status_code=status.HTTP_202_ACCEPTED)
def qualificar(campanha_id: uuid.UUID, contexto: Executar) -> dict[str, str]:
    """Põe na fila a qualificação dos candidatos ainda não qualificados (por exemplo, depois
    de cadastrar a chave da Claude API)."""
    try:
        qualificacao.enfileirar(contexto, campanha_id)
    except qualificacao.NaoEncontrado as erro:
        raise _nao_encontrado() from erro
    return {"status": "na_fila"}
