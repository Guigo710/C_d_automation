from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventoOut(BaseModel):
    id: int
    usuario_id: uuid.UUID | None
    acao: str
    recurso_tipo: str | None
    recurso_id: str | None
    detalhes: dict[str, Any]
    criado_em: datetime


class PaginaDeEventos(BaseModel):
    itens: list[EventoOut]
    proximo_antes_de: int | None
