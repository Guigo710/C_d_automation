from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.organizacoes import servico
from app.organizacoes.esquemas import EuOut, OrganizacaoOut

router = APIRouter(tags=["organizações"])

LerOrganizacao = Annotated[Contexto, Depends(exige("organizacao.ler"))]


@router.get("/eu", response_model=EuOut)
def eu(contexto: LerOrganizacao) -> EuOut:
    return servico.eu(contexto)


@router.get("/organizacoes/{organizacao_id}", response_model=OrganizacaoOut)
def organizacao(organizacao_id: uuid.UUID, contexto: LerOrganizacao) -> OrganizacaoOut:
    try:
        return servico.organizacao(contexto, organizacao_id)
    except servico.OrganizacaoNaoEncontrada as erro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organização não encontrada") from erro
