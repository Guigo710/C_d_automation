"""Prompt D: ficha de abordagem que o vendedor lê ao abrir a empresa."""

from __future__ import annotations

from typing import Any

from app.qualificacao.prompt import entrada as montar_entrada

VERSAO = "d-ficha-v1"

INSTRUCOES = """\
Você escreve a ficha de abordagem de um estabelecimento comercial para um vendedor de uma \
empresa atacadista, que vai ler antes do primeiro contato. Você recebe fatos numerados \
(E1, E2, ...) sobre o estabelecimento.

Regras:
- Use somente os fatos fornecidos. Nada de suposições apresentadas como fato.
- Escreva em português, em até 120 palavras, em três partes curtas: quem é o \
estabelecimento, por que vale a abordagem e um gancho para a primeira conversa.
- Em fatos_citados, liste os identificadores (como "E1") dos fatos usados. Cite só \
identificadores que aparecem na entrada.
"""

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ficha": {"type": "string"},
        "fatos_citados": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ficha", "fatos_citados"],
    "additionalProperties": False,
}


class FichaInvalida(Exception):
    pass


def entrada(fatos: dict[str, Any], evidencias: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return montar_entrada(fatos, evidencias)


def validar(resposta: dict[str, Any], ids_oferecidos: list[str]) -> tuple[str, list[str]]:
    ficha = str(resposta.get("ficha", "")).strip()
    citados = [str(c) for c in resposta.get("fatos_citados", [])]
    if not ficha:
        raise FichaInvalida("ficha vazia")
    if not citados:
        raise FichaInvalida("nenhum fato citado")
    inexistentes = set(citados) - set(ids_oferecidos)
    if inexistentes:
        raise FichaInvalida(f"cita fato inexistente: {sorted(inexistentes)}")
    return ficha, citados
