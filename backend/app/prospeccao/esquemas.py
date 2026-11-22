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
    tipo: str
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
    nota_total: int | None
    tier_sugerido: str | None
    tier_final: str | None
    motivo_recusa: str | None
    recusa_sugerida: bool
    baixa_confianca: bool
    em_revisao: bool


class PaginaDeCandidatos(BaseModel):
    itens: list[CandidatoResumo]
    total: int


class ContatoOut(BaseModel):
    tipo: str
    valor: str
    nome: str | None
    fonte: str
    status_validacao: str | None


class EvidenciaOut(BaseModel):
    campo: str
    valor: str | None
    fonte: str
    url: str | None
    coletado_em: datetime


class CandidatoDetalhe(CandidatoResumo):
    endereco: str | None
    sinais: dict[str, Any]
    nota_aderencia: int | None
    nota_potencial: int | None
    nota_geografia: int | None
    nota_dados: int | None
    justificativas: dict[str, Any]
    lacunas: list[str]
    confianca: Decimal | None
    motivo_revisao: str | None
    modelo: str | None
    versao_prompt: str | None
    versao_regras: int | None
    contatos: list[ContatoOut]
    evidencias: list[EvidenciaOut]
