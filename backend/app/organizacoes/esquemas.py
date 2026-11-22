from __future__ import annotations

import uuid

from pydantic import BaseModel


class OrganizacaoOut(BaseModel):
    id: uuid.UUID
    nome: str


class UsuarioOut(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papel: str
    ativo: bool


class EuOut(BaseModel):
    usuario_id: uuid.UUID
    nome: str
    email: str
    papel: str
    organizacao: OrganizacaoOut
