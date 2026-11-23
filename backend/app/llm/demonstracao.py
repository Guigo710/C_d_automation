"""Cliente de IA de demonstração: respostas plausíveis, montadas só a partir dos fatos da
entrada, sem chamar a Claude e sem custo. Usado com CLIENTE_IA=demonstracao no modo demo."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

from app.llm.cliente import MODELO_PADRAO, RespostaDaIA


class ClienteDeDemonstracao:
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
        fatos: dict[str, Any] = json.loads(entrada.splitlines()[1])
        ids = re.findall(r"^(E\d+):", entrada, flags=re.MULTILINE)
        sinais = fatos.get("sinais") or {}
        lojas = int(sinais.get("lojas", 0) or 0)
        linhas = sinais.get("linhas_de_produto") or []
        canal = sinais.get("canal_de_compras")
        nome = fatos.get("nome_fantasia") or fatos.get("razao_social")
        segmento = fatos.get("segmento") or "varejo"

        if "ficha" in esquema["properties"]:
            partes = [f"{nome} atua no segmento {segmento.lower()}"]
            partes.append(f", com {lojas} {'lojas' if lojas > 1 else 'loja'}" if lojas else "")
            partes.append(f", e trabalha com {', '.join(linhas)}." if linhas else ".")
            if canal:
                partes.append(f" As compras passam por {canal}.")
            partes.append(
                " Vale a abordagem pela recorrência de compra de mercearia e bebidas."
                " Gancho: apresentar a tabela de primeira compra e a rota de entrega da região."
            )
            return RespostaDaIA(
                dados={"ficha": "".join(partes), "fatos_citados": ids[:3]},
                modelo=modelo,
                custo_usd=Decimal(0),
            )

        aderencia = min(95, 55 + 10 * lojas + (5 if linhas else 0))
        potencial = min(95, 45 + 8 * lojas + (10 if canal else 0))
        lacunas = [] if lojas else ["número de lojas"]
        if not fatos.get("site"):
            lacunas.append("site oficial")
        dados = {
            "aderencia": aderencia,
            "potencial": potencial,
            "justificativa_aderencia": f"{segmento} na região, com {lojas or 'número não informado de'} loja(s).",
            "justificativa_potencial": (
                f"Compra centralizada ({canal})."
                if canal
                else "Volume provável de varejo de bairro."
            ),
            "evidencias_citadas": ids[:2],
            "lacunas": lacunas,
            "confianca": 0.85 if lojas else 0.55,
        }
        return RespostaDaIA(dados=dados, modelo=modelo, custo_usd=Decimal(0))
