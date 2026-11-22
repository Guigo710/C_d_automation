from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

StatusJob = Literal["na_fila", "executando", "concluida", "parcial", "falhou"]
StatusCandidato = Literal["coletado", "pendente", "aprovado", "recusado"]


class ExecucaoOut(BaseModel):
    id: uuid.UUID
    campanha_id: uuid.UUID | None
    status: StatusJob
    motivo_parada: str | None
    encontradas: int
    gravadas: int
    duplicadas: int
    custo_usd: Decimal
    erro: str | None
    criado_em: datetime
    iniciado_em: datetime | None
    terminado_em: datetime | None


class EmpresaResumo(BaseModel):
    id: uuid.UUID
    cnpj: str
    razao_social: str
    nome_fantasia: str | None
    situacao_cadastral: str | None
    municipio_ibge: str | None
    segmento: str | None
    site: str | None


class CandidatoResumo(BaseModel):
    id: uuid.UUID
    status: StatusCandidato
    criado_em: datetime
    empresa: EmpresaResumo


class PaginaDeCandidatos(BaseModel):
    itens: list[CandidatoResumo]
    total: int


class ContatoOut(BaseModel):
    tipo: str
    valor: str
    nome: str | None
    fonte: str


class EvidenciaOut(BaseModel):
    campo: str
    valor: str | None
    fonte: str
    url: str | None
    coletado_em: datetime


class CandidatoDetalhe(CandidatoResumo):
    endereco: str | None
    sinais: dict[str, Any]
    contatos: list[ContatoOut]
    evidencias: list[EvidenciaOut]
