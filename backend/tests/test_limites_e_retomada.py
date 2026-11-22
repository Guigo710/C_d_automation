"""Ticket 06: limite, teto de gasto e retomada da execução.

O agente falso devolve 3 supermercados em Campinas, cada um custando US$ 0,03.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.agentes import Interrompido
from tests.conftest import Dados, UsuarioDeTeste, criar_segmento

Como = Callable[[UsuarioDeTeste], dict[str, str]]


@pytest.fixture
def executar(
    client: TestClient, dados: Dados, conn_admin: psycopg.Connection, como: Como
) -> Callable[..., dict[str, Any]]:
    """Cria uma campanha de supermercados em Campinas, executa e devolve a execução."""
    segmento = criar_segmento(conn_admin, dados.a.id, "Supermercado", ["4711302"])
    coord = como(dados.a.coordenador)

    def _executar(**campanha: Any) -> dict[str, Any]:
        corpo = {
            "nome": "Teste de limites",
            "status": "ativa",
            "municipios_ibge": ["3509502"],
            "segmento_ids": [str(segmento)],
            "tiers_alvo": ["A", "B", "C"],
            "limite_empresas": 100,
            "teto_gasto_usd": "10.00",
            **campanha,
        }
        campanha_id = client.post("/campanhas", json=corpo, headers=coord).json()["id"]
        execucao_id = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord).json()["id"]
        client.app.state.fila.drenar()  # type: ignore[attr-defined]
        execucao: dict[str, Any] = client.get(f"/execucoes/{execucao_id}", headers=coord).json()
        return execucao

    return _executar


@pytest.fixture
def agente(client: TestClient) -> Iterator[Callable[[str], None]]:
    settings = client.app.state.settings  # type: ignore[attr-defined]
    original = settings.agente_prospeccao

    def _trocar(referencia: str) -> None:
        settings.agente_prospeccao = referencia

    yield _trocar
    settings.agente_prospeccao = original


def test_execucao_para_no_teto_da_campanha(executar: Callable[..., dict[str, Any]]) -> None:
    execucao = executar(teto_gasto_usd="0.06")

    assert execucao["status"] == "parcial"
    assert execucao["motivo_parada"] == "teto_de_gasto"
    assert execucao["gravadas"] == 2
    assert execucao["custo_usd"] == "0.0600"


def test_execucao_para_no_teto_mensal_da_organizacao(
    executar: Callable[..., dict[str, Any]], dados: Dados, conn_admin: psycopg.Connection
) -> None:
    conn_admin.execute(
        "UPDATE organizacoes SET teto_mensal_usd = 0.03 WHERE id = %s", (dados.a.id,)
    )

    execucao = executar(teto_gasto_usd="10.00")

    assert execucao["motivo_parada"] == "teto_de_gasto"
    assert execucao["gravadas"] == 1


def test_sem_saldo_a_execucao_nem_chama_o_agente(executar: Callable[..., dict[str, Any]]) -> None:
    execucao = executar(teto_gasto_usd="0.00")

    assert execucao["status"] == "parcial"
    assert execucao["motivo_parada"] == "teto_de_gasto"
    assert execucao["encontradas"] == 0


def test_execucao_para_exatamente_no_limite_de_empresas(
    executar: Callable[..., dict[str, Any]],
) -> None:
    execucao = executar(limite_empresas=1)

    assert execucao["motivo_parada"] == "limite_de_empresas"
    assert execucao["gravadas"] == 1
    assert execucao["custo_usd"] == "0.0300"


def test_execucao_interrompida_retoma_sem_duplicar_nem_cobrar_de_novo(
    client: TestClient,
    dados: Dados,
    como: Como,
    conn_admin: psycopg.Connection,
    agente: Callable[[str], None],
) -> None:
    coord = como(dados.a.coordenador)
    segmento = criar_segmento(conn_admin, dados.a.id, "Supermercado", ["4711302"])
    corpo = {
        "nome": "Retomada",
        "status": "ativa",
        "municipios_ibge": ["3509502"],
        "segmento_ids": [str(segmento)],
        "tiers_alvo": ["A", "B", "C"],
        "limite_empresas": 100,
        "teto_gasto_usd": "10.00",
    }
    campanha_id = client.post("/campanhas", json=corpo, headers=coord).json()["id"]
    execucao_id = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord).json()["id"]
    fila = client.app.state.fila  # type: ignore[attr-defined]

    agente("tests.agentes:AgenteQueCaiNoTerceiro")
    with pytest.raises(Interrompido):
        fila.drenar()

    no_meio = client.get(f"/execucoes/{execucao_id}", headers=coord).json()
    assert no_meio["status"] == "executando"
    assert no_meio["gravadas"] == 2

    # O processo "acorda": o lease venceu e o worker retoma o mesmo job.
    conn_admin.execute(
        "UPDATE jobs SET lease_ate = now() - interval '1 second' WHERE id = %s", (execucao_id,)
    )
    agente("falso")
    fila.drenar()

    final = client.get(f"/execucoes/{execucao_id}", headers=coord).json()
    assert final["status"] == "concluida"
    assert final["gravadas"] == 3
    assert final["duplicadas"] == 0
    assert final["custo_usd"] == "0.0900"
    assert client.get(f"/campanhas/{campanha_id}/candidatos", headers=coord).json()["total"] == 3
