from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class SegmentoOut(BaseModel):
    id: uuid.UUID
    nome: str
    cnaes: list[str]


class MunicipioOut(BaseModel):
    municipio_ibge: str
    nome: str
    uf: str
    tem_rota: bool


class ChaveStatus(BaseModel):
    fornecedor: str
    configurada: bool
    final: str | None
    atualizada_em: datetime | None


class ConfiguracaoDaOrganizacao(BaseModel):
    teto_mensal_usd: Decimal
    gasto_do_mes_usd: Decimal
    chaves: list[ChaveStatus]


class TetoIn(BaseModel):
    teto_mensal_usd: Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class ChaveIn(BaseModel):
    chave: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=500)]
