from __future__ import annotations

import uuid

from pydantic import BaseModel


class SegmentoOut(BaseModel):
    id: uuid.UUID
    nome: str
    cnaes: list[str]


class MunicipioOut(BaseModel):
    municipio_ibge: str
    nome: str
    uf: str
    tem_rota: bool
