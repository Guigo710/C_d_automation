"""Agente de prospecção falso: devolve empresas fictícias de um arquivo de exemplo.

Serve para construir e demonstrar a plataforma antes de o agente real ficar pronto.
Filtra o arquivo pelos municípios e segmentos da campanha. Todos os dados são inventados.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.prospeccao.agente import (
    CandidatoProspectado,
    Contato,
    Evidencia,
    FotoDaCampanha,
)

ARQUIVO_PADRAO = Path(__file__).parent / "exemplos" / "empresas_ficticias.json"


class AgenteFalso:
    def __init__(self, arquivo: Path = ARQUIVO_PADRAO) -> None:
        self._arquivo = arquivo

    def executar(self, campanha: FotoDaCampanha) -> Iterator[CandidatoProspectado]:
        dados: list[dict[str, Any]] = json.loads(self._arquivo.read_text(encoding="utf-8"))
        segmentos = {s.nome for s in campanha.segmentos}
        municipios = set(campanha.municipios_ibge)
        for empresa in dados:
            if empresa["municipio_ibge"] in municipios and empresa["segmento"] in segmentos:
                yield _candidato(empresa)


def _candidato(empresa: dict[str, Any]) -> CandidatoProspectado:
    return CandidatoProspectado(
        cnpj=empresa["cnpj"],
        razao_social=empresa["razao_social"],
        nome_fantasia=empresa.get("nome_fantasia"),
        situacao_cadastral=empresa.get("situacao_cadastral"),
        endereco=empresa.get("endereco"),
        municipio_ibge=empresa["municipio_ibge"],
        segmento=empresa["segmento"],
        site=empresa.get("site"),
        contatos=[Contato(**c) for c in empresa.get("contatos", [])],
        sinais=empresa.get("sinais", {}),
        evidencias=[
            Evidencia(
                campo=e["campo"],
                valor=e.get("valor"),
                fonte=e["fonte"],
                url=e.get("url"),
                coletado_em=datetime.fromisoformat(e["coletado_em"]),
            )
            for e in empresa.get("evidencias", [])
        ],
        custo_usd=Decimal(str(empresa.get("custo_usd", "0.03"))),
    )
