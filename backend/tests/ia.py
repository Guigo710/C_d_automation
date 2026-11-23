"""Cliente de IA falso e determinístico, usado só nos testes."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, ClassVar

from app.llm.cliente import MODELO_PADRAO, RespostaDaIA

CUSTO_POR_CHAMADA = Decimal("0.01")


class ClienteFalso:
    """Aderência 90 para quem tem 3 lojas ou mais, 60 para os demais; potencial 70.

    Comportamentos especiais pelo nome fantasia, para exercitar a validação:
    - "Mercado Vila Nova": confiança 0,4 (baixa).
    - "Pães do Cambuí": sempre cita uma evidência que não existe (vai para revisão).
    """

    chamadas: ClassVar[list[str]] = []

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
        ClienteFalso.chamadas.append(entrada)
        if "ficha" in esquema["properties"]:
            return RespostaDaIA(
                dados={"ficha": "Ficha de teste com fatos.", "fatos_citados": ["E1"]},
                modelo=modelo,
                custo_usd=CUSTO_POR_CHAMADA,
            )
        fatos = json.loads(entrada.splitlines()[1])
        ids = re.findall(r"^(E\d+):", entrada, flags=re.MULTILINE)
        lojas = int((fatos.get("sinais") or {}).get("lojas", 0))
        nome = fatos.get("nome_fantasia")
        dados = {
            "aderencia": 90 if lojas >= 3 else 60,
            "potencial": 70,
            "justificativa_aderencia": f"{lojas} loja(s) no segmento {fatos.get('segmento')}.",
            "justificativa_potencial": "Compra recorrente provável.",
            "evidencias_citadas": ids[:2] if nome != "Pães do Cambuí" else ["E999"],
            "lacunas": [] if lojas else ["número de lojas"],
            "confianca": 0.4 if nome == "Mercado Vila Nova" else 0.9,
        }
        return RespostaDaIA(dados=dados, modelo=modelo, custo_usd=CUSTO_POR_CHAMADA)
