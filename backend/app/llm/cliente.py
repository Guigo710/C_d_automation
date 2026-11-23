"""Interface única para modelos de IA, com implementação para a Claude API.

Quem chama passa as instruções fixas (cacheadas), a entrada variável e um esquema JSON;
recebe a resposta já decodificada e o custo da chamada. As regras de negócio validam a
resposta contra o esquema e as evidências antes de gravar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import anthropic

MODELO_PADRAO = "claude-haiku-5-5"

# US$ por milhão de tokens (Claude API, prompts de até 100 mil tokens no Haiku 5.5).
# Escrita em cache custa 1,25x a entrada; leitura em cache, 0,1x.
PRECOS: dict[str, tuple[Decimal, Decimal]] = {
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50")),
    "claude-sonnet-5-5": (Decimal("2.00"), Decimal("10.00")),
}


class RespostaInvalida(Exception):
    """A IA recusou, foi cortada ou devolveu algo fora do esquema."""


@dataclass(frozen=True)
class RespostaDaIA:
    dados: dict[str, Any]
    modelo: str
    custo_usd: Decimal


class ClienteDeIA(Protocol):
    def gerar(
        self,
        *,
        chave_api: str,
        instrucoes: str,
        entrada: str,
        esquema: dict[str, Any],
        max_tokens: int = 1000,
        modelo: str = MODELO_PADRAO,
    ) -> RespostaDaIA: ...


def custo(
    modelo: str, entrada: int, saida: int, cache_escrita: int = 0, cache_leitura: int = 0
) -> Decimal:
    preco_entrada, preco_saida = PRECOS[modelo]
    total = (
        preco_entrada * entrada
        + preco_entrada * Decimal("1.25") * cache_escrita
        + preco_entrada * Decimal("0.10") * cache_leitura
        + preco_saida * saida
    )
    return total / Decimal(1_000_000)


class ClienteClaude:
    def __init__(self, timeout_segundos: float = 60.0, max_tentativas: int = 2) -> None:
        self._timeout = timeout_segundos
        self._tentativas = max_tentativas

    def gerar(
        self,
        *,
        chave_api: str,
        instrucoes: str,
        entrada: str,
        esquema: dict[str, Any],
        max_tokens: int = 1000,
        modelo: str = MODELO_PADRAO,
    ) -> RespostaDaIA:
        cliente = anthropic.Anthropic(
            api_key=chave_api, timeout=self._timeout, max_retries=self._tentativas
        )
        resposta = cliente.messages.create(
            model=modelo,
            max_tokens=max_tokens,
            # Instruções fixas primeiro e cacheadas; a entrada variável vem depois.
            system=[{"type": "text", "text": instrucoes, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": entrada}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": esquema},
            },
        )
        uso = resposta.usage
        valor = custo(
            modelo,
            uso.input_tokens,
            uso.output_tokens,
            uso.cache_creation_input_tokens or 0,
            uso.cache_read_input_tokens or 0,
        )
        if resposta.stop_reason != "end_turn":
            raise RespostaInvalida(f"A IA parou com stop_reason={resposta.stop_reason}")
        texto = next((b.text for b in resposta.content if b.type == "text"), None)
        if texto is None:
            raise RespostaInvalida("A IA não devolveu texto")
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError as erro:
            raise RespostaInvalida("A IA devolveu JSON inválido") from erro
        return RespostaDaIA(dados=dados, modelo=modelo, custo_usd=valor)


def carregar_cliente(referencia: str) -> ClienteDeIA:
    """'claude' ou 'pacote.modulo:Classe' (por exemplo, um cliente falso nos testes)."""
    if referencia == "claude":
        return ClienteClaude()
    if referencia == "demonstracao":
        from app.llm.demonstracao import ClienteDeDemonstracao

        return ClienteDeDemonstracao()
    import importlib

    modulo, _, classe = referencia.partition(":")
    cliente: ClienteDeIA = getattr(importlib.import_module(modulo), classe)()
    return cliente
