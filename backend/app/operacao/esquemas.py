from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.prospeccao.esquemas import ContatoOut, EmpresaResumo

StatusDaFicha = Literal["preparando", "pronta", "falhou"]


class PromocaoIn(BaseModel):
    candidato_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=500)]


class ResponsavelIn(BaseModel):
    vendedor_id: uuid.UUID


class PromocaoOut(BaseModel):
    promovidas: list[uuid.UUID]
    ignoradas: list[uuid.UUID]


class Responsavel(BaseModel):
    id: uuid.UUID
    nome: str


class EmpresaDaCampanhaResumo(BaseModel):
    id: uuid.UUID
    campanha_id: uuid.UUID
    campanha_nome: str
    tier: str
    nota_total: int | None
    ficha_status: StatusDaFicha
    responsavel: Responsavel | None
    promovida_em: datetime
    empresa: EmpresaResumo


class EventoDoHistorico(BaseModel):
    tipo: str
    por_usuario: uuid.UUID | None
    de_usuario: uuid.UUID | None
    para_usuario: uuid.UUID | None
    detalhes: dict[str, Any]
    ocorrido_em: datetime


class EmpresaDaCampanhaDetalhe(EmpresaDaCampanhaResumo):
    endereco: str | None
    sinais: dict[str, Any]
    ficha: str | None
    contatos: list[ContatoOut]
    contato_oculto: bool
    historico: list[EventoDoHistorico]
