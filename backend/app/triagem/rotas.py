from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.campanhas import repositorio as campanhas
from app.triagem import servico
from app.triagem.esquemas import AprovacaoIn, AprovacaoOut, RecusaIn, TrocaDeTierIn

router = APIRouter(tags=["triagem"])

Triar = Annotated[Contexto, Depends(exige("triagem.decidir"))]


def _erro(erro: Exception) -> HTTPException:
    if isinstance(erro, servico.NaoEncontrado):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Candidato não encontrado")
    return HTTPException(status.HTTP_409_CONFLICT, str(erro))


@router.post("/campanhas/{campanha_id}/aprovacoes", response_model=AprovacaoOut)
def aprovar(campanha_id: uuid.UUID, dados: AprovacaoIn, contexto: Triar) -> AprovacaoOut:
    if campanhas.buscar(contexto.conn, campanha_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campanha não encontrada")
    return servico.aprovar(contexto, campanha_id, dados.candidato_ids)


@router.post("/candidatos/{candidato_id}/recusa", status_code=status.HTTP_204_NO_CONTENT)
def recusar(candidato_id: uuid.UUID, dados: RecusaIn, contexto: Triar) -> Response:
    try:
        servico.recusar(contexto, candidato_id, dados.motivo)
    except (servico.NaoEncontrado, servico.EstadoInvalido) as erro:
        raise _erro(erro) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/candidatos/{candidato_id}/restauracao", status_code=status.HTTP_204_NO_CONTENT)
def restaurar(candidato_id: uuid.UUID, contexto: Triar) -> Response:
    try:
        servico.restaurar(contexto, candidato_id)
    except (servico.NaoEncontrado, servico.EstadoInvalido) as erro:
        raise _erro(erro) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/candidatos/{candidato_id}/tier", status_code=status.HTTP_204_NO_CONTENT)
def trocar_tier(candidato_id: uuid.UUID, dados: TrocaDeTierIn, contexto: Triar) -> Response:
    try:
        servico.trocar_tier(contexto, candidato_id, dados.tier, dados.justificativa)
    except (servico.NaoEncontrado, servico.EstadoInvalido) as erro:
        raise _erro(erro) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)
