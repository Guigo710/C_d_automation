from __future__ import annotations

import uuid

from pydantic import BaseModel


class OrganizacaoOut(BaseModel):
    id: uuid.UUID
    nome: str


class EuOut(BaseModel):
    usuario_id: uuid.UUID
    nome: str
    email: str
    papel: str
    organizacao: OrganizacaoOut
