from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.exportacao import servico

router = APIRouter(tags=["exportação"])

TIPO_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/campanhas/{campanha_id}/aprovados.xlsx",
    response_class=Response,
    responses={200: {"content": {TIPO_XLSX: {}}}},
)
def exportar_aprovados(
    campanha_id: uuid.UUID, contexto: Annotated[Contexto, Depends(exige("exportar.xlsx"))]
) -> Response:
    try:
        nome, conteudo = servico.exportar_aprovados(contexto, campanha_id)
    except servico.NaoEncontrado as erro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campanha não encontrada") from erro
    return Response(
        content=conteudo,
        media_type=TIPO_XLSX,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )
