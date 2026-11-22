"""Ticket 04: execução da prospecção com o agente falso.

O agente falso lê app/prospeccao/exemplos/empresas_ficticias.json, que tem 3
supermercados em Campinas (um deles com CNPJ baixado) e 2 padarias em Campinas.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.conftest import Dados, UsuarioDeTeste, criar_segmento

Como = Callable[[UsuarioDeTeste], dict[str, str]]

CAMPINAS = "3509502"


def _drenar(client: TestClient) -> None:
    client.app.state.fila.drenar()  # type: ignore[attr-defined]


@pytest.fixture
def campanha(
    client: TestClient, dados: Dados, conn_admin: psycopg.Connection, como: Como
) -> Callable[..., str]:
    supermercado = criar_segmento(conn_admin, dados.a.id, "Supermercado", ["4711302"])
    padaria = criar_segmento(conn_admin, dados.a.id, "Padaria", ["4721102"])
    ids = {"Supermercado": supermercado, "Padaria": padaria}

    def _criar(segmentos: tuple[str, ...] = ("Supermercado",), **extra: Any) -> str:
        corpo = {
            "nome": "Campanha de teste",
            "status": "ativa",
            "municipios_ibge": [CAMPINAS],
            "segmento_ids": [str(ids[s]) for s in segmentos],
            "tiers_alvo": ["A", "B", "C"],
            "limite_empresas": 100,
            "teto_gasto_usd": "10.00",
            **extra,
        }
        resposta = client.post("/campanhas", json=corpo, headers=como(dados.a.coordenador))
        assert resposta.status_code == 201, resposta.text
        campanha_id: str = resposta.json()["id"]
        return campanha_id

    return _criar


def test_execucao_grava_candidatos_com_evidencias(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord = como(dados.a.coordenador)
    campanha_id = campanha()

    iniciada = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord)
    assert iniciada.status_code == 202
    assert iniciada.json()["status"] == "na_fila"

    _drenar(client)

    execucao = client.get(f"/execucoes/{iniciada.json()['id']}", headers=coord).json()
    assert execucao["status"] == "concluida"
    assert execucao["gravadas"] == 3
    assert execucao["custo_usd"] == "0.0900"

    pagina = client.get(f"/campanhas/{campanha_id}/candidatos", headers=coord).json()
    assert pagina["total"] == 3
    assert {c["status"] for c in pagina["itens"]} == {"coletado"}
    assert {c["empresa"]["segmento"] for c in pagina["itens"]} == {"Supermercado"}

    detalhe = client.get(f"/candidatos/{pagina['itens'][0]['id']}", headers=coord).json()
    assert {e["fonte"] for e in detalhe["evidencias"]} >= {"receita", "google_places"}
    assert all(e["coletado_em"] for e in detalhe["evidencias"])
    assert detalhe["contatos"]


def test_executar_de_novo_nao_duplica_candidatos(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord = como(dados.a.coordenador)
    campanha_id = campanha()

    client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord)
    _drenar(client)
    segunda = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord).json()
    _drenar(client)

    execucao = client.get(f"/execucoes/{segunda['id']}", headers=coord).json()
    assert execucao["gravadas"] == 0
    assert execucao["duplicadas"] == 3
    assert client.get(f"/campanhas/{campanha_id}/candidatos", headers=coord).json()["total"] == 3


def test_empresa_ja_em_outra_campanha_ativa_nao_entra_de_novo(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord = como(dados.a.coordenador)
    primeira = campanha()
    client.post(f"/campanhas/{primeira}/execucoes", headers=coord)
    _drenar(client)

    segunda = campanha(segmentos=("Supermercado", "Padaria"))
    client.post(f"/campanhas/{segunda}/execucoes", headers=coord)
    _drenar(client)

    pagina = client.get(f"/campanhas/{segunda}/candidatos", headers=coord).json()
    assert {c["empresa"]["segmento"] for c in pagina["itens"]} == {"Padaria"}


def test_execucao_para_no_limite_de_empresas(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord = como(dados.a.coordenador)
    campanha_id = campanha(limite_empresas=2)

    execucao_id = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord).json()["id"]
    _drenar(client)

    execucao = client.get(f"/execucoes/{execucao_id}", headers=coord).json()
    assert execucao["status"] == "parcial"
    assert execucao["motivo_parada"] == "limite_de_empresas"
    assert client.get(f"/campanhas/{campanha_id}/candidatos", headers=coord).json()["total"] == 2


def test_nao_inicia_segunda_execucao_enquanto_a_primeira_esta_na_fila(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord = como(dados.a.coordenador)
    campanha_id = campanha()

    client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord)
    resposta = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord)

    assert resposta.status_code == 409
    _drenar(client)


def test_so_coordenador_inicia_execucao(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha_id = campanha()
    for usuario in (dados.a.vendedor, dados.a.administrador):
        resposta = client.post(f"/campanhas/{campanha_id}/execucoes", headers=como(usuario))
        assert resposta.status_code == 403


def test_outra_organizacao_nao_ve_execucao_nem_candidatos(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord_a, coord_b = como(dados.a.coordenador), como(dados.b.coordenador)
    campanha_id = campanha()
    execucao_id = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord_a).json()["id"]
    _drenar(client)
    candidato_id = client.get(f"/campanhas/{campanha_id}/candidatos", headers=coord_a).json()[
        "itens"
    ][0]["id"]

    assert client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord_b).status_code == 404
    assert client.get(f"/execucoes/{execucao_id}", headers=coord_b).status_code == 404
    assert client.get(f"/campanhas/{campanha_id}/candidatos", headers=coord_b).status_code == 404
    assert client.get(f"/candidatos/{candidato_id}", headers=coord_b).status_code == 404


def test_vendedor_nao_ve_candidatos_antes_da_triagem(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha_id = campanha(membro_ids=[str(dados.a.vendedor.id)])
    resposta = client.get(f"/campanhas/{campanha_id}/candidatos", headers=como(dados.a.vendedor))
    assert resposta.status_code == 403


def test_agente_desconhecido_faz_a_execucao_falhar_sem_derrubar_a_fila(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    coord = como(dados.a.coordenador)
    campanha_id = campanha()
    execucao_id = client.post(f"/campanhas/{campanha_id}/execucoes", headers=coord).json()["id"]
    settings = client.app.state.settings  # type: ignore[attr-defined]
    original = settings.agente_prospeccao
    settings.agente_prospeccao = "modulo_que_nao_existe:Agente"
    try:
        _drenar(client)
    finally:
        settings.agente_prospeccao = original

    execucao = client.get(f"/execucoes/{execucao_id}", headers=coord).json()
    assert execucao["status"] == "falhou"
    assert execucao["erro"]


def test_id_inexistente_responde_nao_encontrado(
    client: TestClient, dados: Dados, como: Como
) -> None:
    resposta = client.get(f"/execucoes/{uuid.uuid4()}", headers=como(dados.a.coordenador))
    assert resposta.status_code == 404
