from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.configuracao import repositorio
from app.configuracao.esquemas import MunicipioOut, SegmentoOut

router = APIRouter(tags=["configuração"])

LerConfiguracao = Annotated[Contexto, Depends(exige("configuracao.ler"))]


@router.get("/catalogo-segmentos", response_model=list[SegmentoOut])
def catalogo_segmentos(contexto: LerConfiguracao) -> list[SegmentoOut]:
    return repositorio.listar_segmentos(contexto.conn)


@router.get("/municipios-atendidos", response_model=list[MunicipioOut])
def municipios_atendidos(contexto: LerConfiguracao) -> list[MunicipioOut]:
    return repositorio.listar_municipios(contexto.conn)
