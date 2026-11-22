from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.operacao import servico
from app.operacao.esquemas import (
    EmpresaDaCampanhaDetalhe,
    EmpresaDaCampanhaResumo,
    PromocaoIn,
    PromocaoOut,
)

router = APIRouter(tags=["operação"])

Promover = Annotated[Contexto, Depends(exige("lead.promover"))]
Ler = Annotated[Contexto, Depends(exige("operacao.ler"))]


def _nao_encontrado() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Não encontrado")


@router.post("/campanhas/{campanha_id}/promocoes", response_model=PromocaoOut)
def promover(
    campanha_id: uuid.UUID,
    dados: PromocaoIn,
    contexto: Promover,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
) -> PromocaoOut:
    """Sobe os aprovados para a operação. Cada clique manda uma Idempotency-Key nova;
    repetir a mesma chave devolve o mesmo resultado sem duplicar nada."""
    try:
        return servico.promover(contexto, campanha_id, dados.candidato_ids, idempotency_key)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro


@router.get("/campanhas/{campanha_id}/empresas", response_model=list[EmpresaDaCampanhaResumo])
def listar(campanha_id: uuid.UUID, contexto: Ler) -> list[EmpresaDaCampanhaResumo]:
    try:
        return servico.listar(contexto, campanha_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro


@router.get("/empresas-da-campanha/{empresa_id}", response_model=EmpresaDaCampanhaDetalhe)
def detalhe(empresa_id: uuid.UUID, contexto: Ler) -> EmpresaDaCampanhaDetalhe:
    try:
        return servico.detalhe(contexto, empresa_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrado() from erro
