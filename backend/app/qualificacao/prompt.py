"""Prompt C: notas de aderência e potencial, com justificativa e evidências citadas."""

from __future__ import annotations

import json
from typing import Any

VERSAO = "c-qualificacao-v1"
LIMIAR_DE_CONFIANCA = 0.6

INSTRUCOES_BASE = """\
Você avalia estabelecimentos comerciais como possíveis compradores de uma organização que \
vende por atacado. Para cada estabelecimento você recebe fatos numerados (E1, E2, ...) \
coletados de fontes públicas, e devolve duas notas de 0 a 100:

- aderencia: o quanto o estabelecimento combina com o perfil ideal da organização \
(segmento, porte, região, mix de produtos).
- potencial: o quanto ele tende a comprar com volume e recorrência (número de lojas, \
canal de compras centralizado, linhas de produto).

Regras:
- Use somente os fatos fornecidos. Não invente dados sobre o estabelecimento.
- Em evidencias_citadas, liste os identificadores (como "E1") dos fatos que sustentam \
as notas. Cite apenas identificadores que aparecem na entrada.
- Em lacunas, liste o que falta saber para avaliar melhor (por exemplo, "número de lojas").
- confianca vai de 0 a 1. Com poucos fatos ou fatos conflitantes, use confiança baixa.
- Escreva as justificativas em português, em uma ou duas frases.
"""

ESQUEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "aderencia": {"type": "integer"},
        "potencial": {"type": "integer"},
        "justificativa_aderencia": {"type": "string"},
        "justificativa_potencial": {"type": "string"},
        "evidencias_citadas": {"type": "array", "items": {"type": "string"}},
        "lacunas": {"type": "array", "items": {"type": "string"}},
        "confianca": {"type": "number"},
    },
    "required": [
        "aderencia",
        "potencial",
        "justificativa_aderencia",
        "justificativa_potencial",
        "evidencias_citadas",
        "lacunas",
        "confianca",
    ],
    "additionalProperties": False,
}


def instrucoes(perfil_ideal: str) -> str:
    """Fixas por organização e versão das regras, para aproveitar o cache de prompt."""
    return f"{INSTRUCOES_BASE}\nPerfil ideal da organização:\n{perfil_ideal.strip()}\n"


def entrada(fatos: dict[str, Any], evidencias: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Texto da entrada e a lista de identificadores de evidência oferecidos."""
    linhas = [
        "Estabelecimento:",
        json.dumps(fatos, ensure_ascii=False, sort_keys=True),
        "",
        "Fatos:",
    ]
    ids = []
    for i, ev in enumerate(evidencias, start=1):
        ident = f"E{i}"
        ids.append(ident)
        linhas.append(
            f"{ident}: {ev['campo']} = {ev['valor']} (fonte: {ev['fonte']}, "
            f"coletado em {ev['coletado_em']:%Y-%m-%d})"
        )
    return "\n".join(linhas), ids


class RespostaForaDoEsquema(Exception):
    pass


def validar(resposta: dict[str, Any], ids_oferecidos: list[str]) -> dict[str, Any]:
    """Confere faixas e evidências. Levanta RespostaForaDoEsquema se algo não bate."""
    try:
        aderencia = int(resposta["aderencia"])
        potencial = int(resposta["potencial"])
        confianca = float(resposta["confianca"])
        citadas = [str(c) for c in resposta["evidencias_citadas"]]
        lacunas = [str(item) for item in resposta["lacunas"]]
    except (KeyError, TypeError, ValueError) as erro:
        raise RespostaForaDoEsquema(f"campo ausente ou de tipo errado: {erro}") from erro
    if not (0 <= aderencia <= 100 and 0 <= potencial <= 100 and 0 <= confianca <= 1):
        raise RespostaForaDoEsquema("nota ou confiança fora da faixa")
    inexistentes = set(citadas) - set(ids_oferecidos)
    if inexistentes:
        raise RespostaForaDoEsquema(f"cita evidência inexistente: {sorted(inexistentes)}")
    if not citadas:
        raise RespostaForaDoEsquema("nenhuma evidência citada")
    return {
        "aderencia": aderencia,
        "potencial": potencial,
        "confianca": round(confianca, 2),
        "evidencias_citadas": citadas,
        "lacunas": lacunas,
        "justificativa_aderencia": str(resposta["justificativa_aderencia"]),
        "justificativa_potencial": str(resposta["justificativa_potencial"]),
    }
