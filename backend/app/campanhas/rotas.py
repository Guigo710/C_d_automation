from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.campanhas import servico
from app.campanhas.esquemas import CampanhaIn, CampanhaNaLista, CampanhaOut

router = APIRouter(tags=["campanhas"])

LerCampanhas = Annotated[Contexto, Depends(exige("campanha.ler"))]
EditarCampanhas = Annotated[Contexto, Depends(exige("campanha.editar"))]


def _nao_encontrada() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Campanha não encontrada")


@router.get("/campanhas", response_model=list[CampanhaNaLista])
def listar(contexto: LerCampanhas) -> list[CampanhaNaLista]:
    return servico.listar(contexto)


@router.get("/campanhas/{campanha_id}", response_model=CampanhaOut)
def buscar(campanha_id: uuid.UUID, contexto: LerCampanhas) -> CampanhaOut:
    try:
        return servico.buscar(contexto, campanha_id)
    except servico.CampanhaNaoEncontrada as erro:
        raise _nao_encontrada() from erro


@router.post("/campanhas", response_model=CampanhaOut, status_code=status.HTTP_201_CREATED)
def criar(dados: CampanhaIn, contexto: EditarCampanhas) -> CampanhaOut:
    try:
        return servico.criar(contexto, dados)
    except servico.CampanhaInvalida as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erro)) from erro


@router.put("/campanhas/{campanha_id}", response_model=CampanhaOut)
def atualizar(campanha_id: uuid.UUID, dados: CampanhaIn, contexto: EditarCampanhas) -> CampanhaOut:
    try:
        return servico.atualizar(contexto, campanha_id, dados)
    except servico.CampanhaInvalida as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erro)) from erro
    except servico.CampanhaNaoEncontrada as erro:
        raise _nao_encontrada() from erro
