from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Tier = Literal["A", "B", "C"]
StatusCampanha = Literal["rascunho", "ativa", "pausada", "encerrada"]
CodigoIbge = Annotated[str, StringConstraints(pattern=r"^[0-9]{7}$")]


class CampanhaIn(BaseModel):
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    status: StatusCampanha = "rascunho"
    municipios_ibge: Annotated[list[CodigoIbge], Field(min_length=1)]
    segmento_ids: Annotated[list[uuid.UUID], Field(min_length=1)]
    tiers_alvo: Annotated[list[Tier], Field(min_length=1)]
    limite_empresas: Annotated[int, Field(gt=0, le=100_000)]
    teto_gasto_usd: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
    membro_ids: list[uuid.UUID] = []


class SegmentoDaCampanha(BaseModel):
    id: uuid.UUID
    nome: str


class MembroDaCampanha(BaseModel):
    id: uuid.UUID
    nome: str


class CampanhaResumo(BaseModel):
    id: uuid.UUID
    nome: str
    status: StatusCampanha
    limite_empresas: int
    teto_gasto_usd: Decimal
    criada_em: datetime


class MetricasDaCampanha(BaseModel):
    candidatos: int
    pendentes: int
    aprovados: int
    recusados: int
    na_operacao: int
    gasto_usd: Decimal


class CampanhaNaLista(CampanhaResumo):
    municipios_ibge: list[str]
    tiers_alvo: list[str]
    segmentos: list[str]
    metricas: MetricasDaCampanha


class CampanhaOut(CampanhaResumo):
    municipios_ibge: list[str]
    tiers_alvo: list[Tier]
    segmentos: list[SegmentoDaCampanha]
    membros: list[MembroDaCampanha]
    atualizada_em: datetime
