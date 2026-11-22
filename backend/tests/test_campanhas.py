"""Ticket 03: campanhas."""

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
JUNDIAI = "3525904"


@pytest.fixture
def segmentos(dados: Dados, conn_admin: psycopg.Connection) -> dict[str, uuid.UUID]:
    return {
        "supermercado_a": criar_segmento(conn_admin, dados.a.id, "Supermercado", ["4711302"]),
        "padaria_a": criar_segmento(conn_admin, dados.a.id, "Padaria", ["4721102"]),
        "supermercado_b": criar_segmento(conn_admin, dados.b.id, "Supermercado", ["4711302"]),
    }


def _nova_campanha(
    dados: Dados, segmentos: dict[str, uuid.UUID], **mudancas: Any
) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "nome": "Supermercados de Campinas",
        "municipios_ibge": [CAMPINAS],
        "segmento_ids": [str(segmentos["supermercado_a"])],
        "tiers_alvo": ["A", "B"],
        "limite_empresas": 300,
        "teto_gasto_usd": "20.00",
        "membro_ids": [str(dados.a.vendedor.id)],
    }
    corpo.update(mudancas)
    return corpo


def test_coordenador_cria_e_consulta_campanha(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    criada = client.post(
        "/campanhas", json=_nova_campanha(dados, segmentos), headers=como(dados.a.coordenador)
    )
    assert criada.status_code == 201

    detalhe = client.get(f"/campanhas/{criada.json()['id']}", headers=como(dados.a.coordenador))

    assert detalhe.status_code == 200
    corpo = detalhe.json()
    assert corpo["nome"] == "Supermercados de Campinas"
    assert corpo["status"] == "rascunho"
    assert corpo["municipios_ibge"] == [CAMPINAS]
    assert corpo["tiers_alvo"] == ["A", "B"]
    assert corpo["limite_empresas"] == 300
    assert corpo["teto_gasto_usd"] == "20.00"
    assert [s["nome"] for s in corpo["segmentos"]] == ["Supermercado"]
    assert [m["id"] for m in corpo["membros"]] == [str(dados.a.vendedor.id)]


def test_coordenador_lista_as_campanhas_da_organizacao(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    client.post(
        "/campanhas", json=_nova_campanha(dados, segmentos), headers=como(dados.a.coordenador)
    )

    lista = client.get("/campanhas", headers=como(dados.a.coordenador)).json()

    assert [c["nome"] for c in lista] == ["Supermercados de Campinas"]


def test_coordenador_edita_campanha_e_muda_status(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    coord = como(dados.a.coordenador)
    campanha_id = client.post(
        "/campanhas", json=_nova_campanha(dados, segmentos), headers=coord
    ).json()["id"]
    edicao = _nova_campanha(
        dados,
        segmentos,
        nome="Padarias de Jundiaí",
        municipios_ibge=[JUNDIAI],
        segmento_ids=[str(segmentos["padaria_a"])],
        status="ativa",
        membro_ids=[],
    )

    resposta = client.put(f"/campanhas/{campanha_id}", json=edicao, headers=coord)

    assert resposta.status_code == 200
    corpo = client.get(f"/campanhas/{campanha_id}", headers=coord).json()
    assert corpo["nome"] == "Padarias de Jundiaí"
    assert corpo["status"] == "ativa"
    assert corpo["municipios_ibge"] == [JUNDIAI]
    assert [s["nome"] for s in corpo["segmentos"]] == ["Padaria"]
    assert corpo["membros"] == []


def test_segmento_fora_do_catalogo_da_organizacao_e_recusado(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    corpo = _nova_campanha(dados, segmentos, segmento_ids=[str(segmentos["supermercado_b"])])

    resposta = client.post("/campanhas", json=corpo, headers=como(dados.a.coordenador))

    assert resposta.status_code == 422


def test_membro_precisa_ser_vendedor_da_organizacao(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    for membro in (dados.a.coordenador, dados.b.vendedor):
        corpo = _nova_campanha(dados, segmentos, membro_ids=[str(membro.id)])
        resposta = client.post("/campanhas", json=corpo, headers=como(dados.a.coordenador))
        assert resposta.status_code == 422


def test_vendedor_nao_cria_nem_edita_campanha(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    corpo = _nova_campanha(dados, segmentos)
    assert client.post("/campanhas", json=corpo, headers=como(dados.a.vendedor)).status_code == 403

    campanha_id = client.post("/campanhas", json=corpo, headers=como(dados.a.coordenador)).json()[
        "id"
    ]
    editar = client.put(f"/campanhas/{campanha_id}", json=corpo, headers=como(dados.a.vendedor))
    assert editar.status_code == 403


def test_vendedor_ve_so_as_campanhas_de_que_participa(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    coord = como(dados.a.coordenador)
    client.post("/campanhas", json=_nova_campanha(dados, segmentos, nome="Com ele"), headers=coord)
    sem = client.post(
        "/campanhas",
        json=_nova_campanha(dados, segmentos, nome="Sem ele", membro_ids=[]),
        headers=coord,
    ).json()["id"]

    lista = client.get("/campanhas", headers=como(dados.a.vendedor)).json()

    assert [c["nome"] for c in lista] == ["Com ele"]
    assert client.get(f"/campanhas/{sem}", headers=como(dados.a.vendedor)).status_code == 404


def test_campanhas_de_uma_organizacao_nao_aparecem_para_outra(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    campanha_id = client.post(
        "/campanhas", json=_nova_campanha(dados, segmentos), headers=como(dados.a.coordenador)
    ).json()["id"]

    assert client.get("/campanhas", headers=como(dados.b.coordenador)).json() == []
    assert (
        client.get(f"/campanhas/{campanha_id}", headers=como(dados.b.coordenador)).status_code
        == 404
    )


def test_catalogo_de_segmentos_mostra_so_os_da_organizacao(
    client: TestClient, dados: Dados, segmentos: dict[str, uuid.UUID], como: Como
) -> None:
    catalogo = client.get("/catalogo-segmentos", headers=como(dados.b.coordenador)).json()

    assert [s["id"] for s in catalogo] == [str(segmentos["supermercado_b"])]


def test_coordenador_lista_vendedores_para_escolher_membros(
    client: TestClient, dados: Dados, como: Como
) -> None:
    vendedores = client.get("/usuarios?papel=vendedor", headers=como(dados.a.coordenador)).json()

    assert [v["id"] for v in vendedores] == [str(dados.a.vendedor.id)]
