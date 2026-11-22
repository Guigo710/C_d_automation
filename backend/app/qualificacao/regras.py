"""Regras objetivas da qualificação (Agente 2), sem IA: exclusões, validação de contatos,
notas de geografia e de qualidade dos dados, total e tier. Ficam fora do modelo de
propósito: precisam ser auditáveis e reproduzíveis.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

MotivoRecusa = Literal[
    "fora_do_perfil",
    "cnpj_inativo",
    "fora_da_regiao",
    "dados_incompletos",
    "ja_e_cliente",
    "duplicado",
    "opt_out",
]
StatusContato = Literal["valido", "invalido", "risco"]

# DDDs em uso no Brasil (Anatel).
DDDS_VALIDOS = frozenset(
    {11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38,
     41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68,
     69, 71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95,
     96, 97, 98, 99}
)  # fmt: skip

_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")
_PALAVRAS_DE_CONTABILIDADE = ("contab", "contador", "escritorio", "assessoria")
DIAS_DE_EVIDENCIA_RECENTE = 180


@dataclass(frozen=True)
class Contato:
    tipo: str
    valor: str


@dataclass(frozen=True)
class Evidencia:
    fonte: str
    coletado_em: datetime


@dataclass(frozen=True)
class Empresa:
    cnpj: str
    situacao_cadastral: str | None
    municipio_ibge: str | None
    site: str | None
    contatos: list[Contato] = field(default_factory=list)
    evidencias: list[Evidencia] = field(default_factory=list)


@dataclass(frozen=True)
class Bloqueios:
    cnpjs: frozenset[str] = frozenset()
    emails: frozenset[str] = frozenset()
    telefones: frozenset[str] = frozenset()
    dominios: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Regras:
    pesos: dict[str, int]
    cortes: dict[str, int]


# --- contatos -----------------------------------------------------------------------------


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def validar_contato(contato: Contato) -> StatusContato:
    if contato.tipo == "email":
        email = contato.valor.strip().lower()
        if not _EMAIL.match(email):
            return "invalido"
        dominio = email.split("@", 1)[1]
        if any(p in dominio for p in _PALAVRAS_DE_CONTABILIDADE):
            return "risco"  # o e-mail cadastrado na Receita costuma ser do contador
        return "valido"
    digitos = so_digitos(contato.valor)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11) or int(digitos[:2]) not in DDDS_VALIDOS:
        return "invalido"
    return "valido"


def dominio_de(texto: str | None) -> str | None:
    if not texto:
        return None
    texto = texto.strip().lower()
    if "@" in texto:
        return texto.split("@", 1)[1]
    texto = re.sub(r"^[a-z]+://", "", texto).split("/", 1)[0]
    return texto.removeprefix("www.") or None


# --- exclusões ----------------------------------------------------------------------------


def exclusao(
    empresa: Empresa,
    municipios_da_campanha: Iterable[str],
    clientes_atuais: frozenset[str],
    mesma_raiz_em_uso: bool,
    bloqueios: Bloqueios,
) -> MotivoRecusa | None:
    """O motivo de recusa sugerido por regra, ou None se a empresa segue para as notas."""
    situacao = (empresa.situacao_cadastral or "").strip().upper()
    if situacao and situacao != "ATIVA":
        return "cnpj_inativo"
    if empresa.municipio_ibge not in set(municipios_da_campanha):
        return "fora_da_regiao"
    if empresa.cnpj in clientes_atuais:
        return "ja_e_cliente"
    if mesma_raiz_em_uso:  # outro estabelecimento do mesmo CNPJ básico já em prospecção
        return "duplicado"
    if _bloqueada(empresa, bloqueios):
        return "opt_out"
    return None


def _bloqueada(empresa: Empresa, bloqueios: Bloqueios) -> bool:
    if empresa.cnpj in bloqueios.cnpjs:
        return True
    dominios = {dominio_de(empresa.site)}
    for contato in empresa.contatos:
        if contato.tipo == "email":
            if contato.valor.strip().lower() in bloqueios.emails:
                return True
            dominios.add(dominio_de(contato.valor))
        elif so_digitos(contato.valor) in bloqueios.telefones:
            return True
    return bool(dominios & bloqueios.dominios)


# --- notas --------------------------------------------------------------------------------


def nota_geografia(
    municipio_ibge: str | None, com_rota: frozenset[str], atendidos: frozenset[str]
) -> int:
    if municipio_ibge in com_rota:
        return 100
    if municipio_ibge in atendidos:
        return 60
    return 0


def nota_dados(empresa: Empresa, status_dos_contatos: list[StatusContato], agora: datetime) -> int:
    ativo = (empresa.situacao_cadastral or "").strip().upper() == "ATIVA"
    casado_com_loja = any(e.fonte == "google_places" for e in empresa.evidencias)
    recentes = [
        e for e in empresa.evidencias
        if agora - e.coletado_em <= timedelta(days=DIAS_DE_EVIDENCIA_RECENTE)
    ]  # fmt: skip
    nota = 0
    if ativo and casado_com_loja:
        nota += 30
    if "valido" in status_dos_contatos:
        nota += 30
    if empresa.site:
        nota += 20
    if len(recentes) >= 3:
        nota += 20
    return nota


def total_e_tier(
    regras: Regras, aderencia: int, potencial: int, geografia: int, dados: int
) -> tuple[int, str | None]:
    """Total ponderado (arredondado para cima a partir de ,5) e tier; None abaixo do corte C."""
    p = regras.pesos
    soma = (
        Decimal(p["aderencia"]) * aderencia
        + Decimal(p["potencial"]) * potencial
        + Decimal(p["geografia"]) * geografia
        + Decimal(p["dados"]) * dados
    ) / Decimal(sum(p.values()))
    total = int(soma.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    for tier in ("A", "B", "C"):
        if total >= regras.cortes[tier]:
            return total, tier
    return total, None
