from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

MotivoRecusa = Literal[
    "fora_do_perfil",
    "cnpj_inativo",
    "fora_da_regiao",
    "dados_incompletos",
    "ja_e_cliente",
    "duplicado",
    "opt_out",
]


class AprovacaoIn(BaseModel):
    candidato_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=500)]


class AprovacaoOut(BaseModel):
    aprovados: list[uuid.UUID]
    ignorados: list[uuid.UUID]


class RecusaIn(BaseModel):
    motivo: MotivoRecusa


class TrocaDeTierIn(BaseModel):
    tier: Literal["A", "B", "C"]
    justificativa: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3)]
