"""Ticket 11: vendedor assume, com contato oculto."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.conftest import Dados, UsuarioDeTeste, _criar_usuario
from tests.test_qualificacao import (  # noqa: F401  (fixtures)
    _candidatos,
    _fila,
    _limpar_chamadas,
    campanha,
    organizacao,
)

Como = Callable[[UsuarioDeTeste], dict[str, str]]


@pytest.fixture
def segundo_vendedor(dados: Dados, conn_admin: psycopg.Connection) -> UsuarioDeTeste:
    return _criar_usuario(conn_admin, dados.a.id, "vendedor", "a2")


@pytest.fixture
def operacao(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
    segundo_vendedor: UsuarioDeTeste,
) -> dict[str, Any]:
    """Campanha com os dois vendedores; Bom Preço e Vila Nova promovidos e com ficha."""
    campanha_id = campanha(membro_ids=[str(dados.a.vendedor.id), str(segundo_vendedor.id)])
    _fila(client).drenar()
    c = _candidatos(client, como, dados, campanha_id)
    ids = [c["Bom Preço Taquaral"]["id"], c["Mercado Vila Nova"]["id"]]
    coord = como(dados.a.coordenador)
    client.post(f"/campanhas/{campanha_id}/aprovacoes", json={"candidato_ids": ids}, headers=coord)
    client.post(
        f"/campanhas/{campanha_id}/promocoes",
        json={"candidato_ids": ids},
        headers={**coord, "Idempotency-Key": "clique-vendedor"},
    )
    _fila(client).drenar()
    empresas = client.get(f"/campanhas/{campanha_id}/empresas", headers=coord).json()
    return {
        "campanha_id": campanha_id,
        "empresas": {e["empresa"]["nome_fantasia"]: e["id"] for e in empresas},
    }


def test_vendedor_ve_empresas_disponiveis_sem_contato(
    client: TestClient, dados: Dados, como: Como, operacao: dict[str, Any]
) -> None:
    vendedor = como(dados.a.vendedor)

    lista = client.get(f"/campanhas/{operacao['campanha_id']}/empresas", headers=vendedor).json()
    detalhe = client.get(
        f"/empresas-da-campanha/{operacao['empresas']['Bom Preço Taquaral']}", headers=vendedor
    ).json()

    assert len(lista) == 2
    assert detalhe["ficha"]
    assert detalhe["contato_oculto"] is True
    assert detalhe["contatos"] == []
    assert "compras@" not in str(detalhe)


def test_ao_assumir_o_vendedor_passa_a_ver_o_contato(
    client: TestClient, dados: Dados, como: Como, operacao: dict[str, Any]
) -> None:
    vendedor = como(dados.a.vendedor)
    empresa_id = operacao["empresas"]["Bom Preço Taquaral"]

    resposta = client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=vendedor)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["responsavel"]["id"] == str(dados.a.vendedor.id)
    assert corpo["contato_oculto"] is False
    assert {c["tipo"] for c in corpo["contatos"]} == {"telefone", "email"}
    assert corpo["historico"][-1]["tipo"] == "assumida"
    eventos = client.get("/auditoria", headers=como(dados.a.administrador)).json()["itens"]
    assert any(e["acao"] == "empresa.assumida" for e in eventos)


def test_empresa_de_outro_vendedor_nao_e_encontrada(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],
    segundo_vendedor: UsuarioDeTeste,
) -> None:
    empresa_id = operacao["empresas"]["Bom Preço Taquaral"]
    client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=como(segundo_vendedor))
    vendedor = como(dados.a.vendedor)

    assert client.get(f"/empresas-da-campanha/{empresa_id}", headers=vendedor).status_code == 404
    lista = client.get(f"/campanhas/{operacao['campanha_id']}/empresas", headers=vendedor).json()
    assert [e["empresa"]["nome_fantasia"] for e in lista] == ["Mercado Vila Nova"]


def test_dois_vendedores_ao_mesmo_tempo_so_um_fica_com_a_empresa(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],
    segundo_vendedor: UsuarioDeTeste,
) -> None:
    empresa_id = operacao["empresas"]["Mercado Vila Nova"]
    cabecalhos = [como(dados.a.vendedor), como(segundo_vendedor)]

    with ThreadPoolExecutor(max_workers=2) as pool:
        respostas = list(
            pool.map(
                lambda c: client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=c),
                cabecalhos,
            )
        )

    codigos = sorted(r.status_code for r in respostas)
    assert codigos in ([200, 409], [200, 404])  # o perdedor já não enxerga a empresa
    coord = como(dados.a.coordenador)
    detalhe = client.get(f"/empresas-da-campanha/{empresa_id}", headers=coord).json()
    assert detalhe["responsavel"] is not None
    assert [h["tipo"] for h in detalhe["historico"]].count("assumida") == 1


def test_segundo_vendedor_recebe_aviso_ao_tentar_empresa_ja_assumida(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],
    segundo_vendedor: UsuarioDeTeste,
) -> None:
    empresa_id = operacao["empresas"]["Mercado Vila Nova"]
    client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=como(dados.a.vendedor))

    resposta = client.post(
        f"/empresas-da-campanha/{empresa_id}/assumir", headers=como(segundo_vendedor)
    )

    assert resposta.status_code in (404, 409)


def test_vendedor_fora_da_campanha_nao_ve_nada(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],
    conn_admin: psycopg.Connection,
) -> None:
    de_fora = _criar_usuario(conn_admin, dados.a.id, "vendedor", "fora")
    cab = como(de_fora)

    assert (
        client.get(f"/campanhas/{operacao['campanha_id']}/empresas", headers=cab).status_code == 404
    )
    empresa_id = operacao["empresas"]["Mercado Vila Nova"]
    assert client.get(f"/empresas-da-campanha/{empresa_id}", headers=cab).status_code == 404
    assert (
        client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=cab).status_code == 404
    )


def test_coordenador_ve_todos_os_contatos_e_nao_assume(
    client: TestClient, dados: Dados, como: Como, operacao: dict[str, Any]
) -> None:
    coord = como(dados.a.coordenador)
    empresa_id = operacao["empresas"]["Bom Preço Taquaral"]

    detalhe = client.get(f"/empresas-da-campanha/{empresa_id}", headers=coord).json()

    assert detalhe["contato_oculto"] is False
    assert detalhe["contatos"]
    assert (
        client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=coord).status_code == 403
    )
