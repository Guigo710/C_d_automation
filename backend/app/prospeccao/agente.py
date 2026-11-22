"""Contrato do Agente de prospecção (ticket 04, spec "Contrato do agente de prospecção").

O agente recebe a fotografia de uma campanha e devolve candidatos, um a um, com as
evidências de cada dado e o custo gasto para obtê-lo. De onde ele tira os dados é escolha
de quem o escreve.

A plataforma, e não o agente, é dona de: gravar no banco, tirar duplicatas, aplicar
exclusões, controlar o limite de empresas e o teto de gasto (ela para de consumir o
iterador quando eles acabam), registrar o andamento e retomar depois de uma interrupção.
Como a plataforma deduplica por CNPJ, chamar o agente de novo para a mesma campanha é
seguro.

Para usar outro agente, defina AGENTE_PROSPECCAO como "pacote.modulo:Classe". A classe é
instanciada sem argumentos e precisa ter o método `executar`.
"""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class SegmentoAlvo:
    nome: str
    cnaes: list[str]


@dataclass(frozen=True)
class FotoDaCampanha:
    organizacao_id: uuid.UUID
    campanha_id: uuid.UUID
    municipios_ibge: list[str]
    segmentos: list[SegmentoAlvo]
    limite_empresas: int
    saldo_teto_usd: Decimal


@dataclass(frozen=True)
class Evidencia:
    """De onde veio um dado: fonte (ex.: 'receita', 'google_places', 'site'), link e data."""

    campo: str
    valor: str | None
    fonte: str
    url: str | None
    coletado_em: datetime


@dataclass(frozen=True)
class Contato:
    tipo: Literal["telefone", "email", "whatsapp"]
    valor: str
    fonte: str
    nome: str | None = None


@dataclass(frozen=True)
class CandidatoProspectado:
    cnpj: str
    razao_social: str
    municipio_ibge: str
    segmento: str
    nome_fantasia: str | None = None
    situacao_cadastral: str | None = None
    endereco: str | None = None
    site: str | None = None
    contatos: list[Contato] = field(default_factory=list)
    sinais: dict[str, Any] = field(default_factory=dict)
    evidencias: list[Evidencia] = field(default_factory=list)
    custo_usd: Decimal = Decimal(0)


class AgenteDeProspeccao(Protocol):
    def executar(self, campanha: FotoDaCampanha) -> Iterator[CandidatoProspectado]: ...


def carregar_agente(referencia: str) -> AgenteDeProspeccao:
    """'falso' ou 'pacote.modulo:Classe'."""
    if referencia == "falso":
        from app.prospeccao.agente_falso import AgenteFalso

        return AgenteFalso()
    modulo, _, classe = referencia.partition(":")
    if not classe:
        raise ValueError("AGENTE_PROSPECCAO deve ser 'falso' ou 'pacote.modulo:Classe'")
    agente: AgenteDeProspeccao = getattr(importlib.import_module(modulo), classe)()
    return agente
