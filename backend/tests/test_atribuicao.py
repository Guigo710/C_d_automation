"""Ticket 12: coordenador atribui e transfere."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import Dados, UsuarioDeTeste, _criar_usuario
from tests.test_qualificacao import (  # noqa: F401  (fixtures)
    _limpar_chamadas,
    campanha,
    organizacao,
)
from tests.test_vendedor import operacao, segundo_vendedor  # noqa: F401  (fixtures)

Como = Callable[[UsuarioDeTeste], dict[str, str]]


def _responsavel(
    client: TestClient, como: Como, usuario: UsuarioDeTeste, empresa_id: str, vendedor_id: Any
) -> Any:
    return client.put(
        f"/empresas-da-campanha/{empresa_id}/responsavel",
        json={"vendedor_id": str(vendedor_id)},
        headers=como(usuario),
    )


def test_coordenador_atribui_e_depois_transfere(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],  # noqa: F811
    segundo_vendedor: UsuarioDeTeste,  # noqa: F811
) -> None:
    empresa_id = operacao["empresas"]["Bom Preço Taquaral"]

    atribuida = _responsavel(client, como, dados.a.coordenador, empresa_id, dados.a.vendedor.id)
    transferida = _responsavel(client, como, dados.a.coordenador, empresa_id, segundo_vendedor.id)

    assert atribuida.status_code == 200
    assert transferida.status_code == 200
    historico = transferida.json()["historico"]
    assert [h["tipo"] for h in historico[-2:]] == ["atribuida", "transferida"]
    assert historico[-1] == {
        **historico[-1],
        "por_usuario": str(dados.a.coordenador.id),
        "de_usuario": str(dados.a.vendedor.id),
        "para_usuario": str(segundo_vendedor.id),
    }
    # O novo responsável vê o contato; o anterior deixa de ver a empresa.
    novo = client.get(f"/empresas-da-campanha/{empresa_id}", headers=como(segundo_vendedor)).json()
    assert novo["contato_oculto"] is False
    antigo = client.get(f"/empresas-da-campanha/{empresa_id}", headers=como(dados.a.vendedor))
    assert antigo.status_code == 404
    acoes = [
        e["acao"]
        for e in client.get("/auditoria", headers=como(dados.a.administrador)).json()["itens"]
    ]
    assert "empresa.atribuida" in acoes
    assert "empresa.transferida" in acoes


def test_so_vendedor_membro_da_campanha_recebe_empresa(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],  # noqa: F811
    conn_admin: psycopg.Connection,
) -> None:
    empresa_id = operacao["empresas"]["Bom Preço Taquaral"]
    de_fora = _criar_usuario(conn_admin, dados.a.id, "vendedor", "fora")

    for destino in (de_fora.id, dados.a.coordenador.id, dados.b.vendedor.id):
        resposta = _responsavel(client, como, dados.a.coordenador, empresa_id, destino)
        assert resposta.status_code == 422


def test_vendedor_nao_atribui_nem_transfere(
    client: TestClient,
    dados: Dados,
    como: Como,
    operacao: dict[str, Any],  # noqa: F811
    segundo_vendedor: UsuarioDeTeste,  # noqa: F811
) -> None:
    empresa_id = operacao["empresas"]["Bom Preço Taquaral"]
    client.post(f"/empresas-da-campanha/{empresa_id}/assumir", headers=como(dados.a.vendedor))

    resposta = _responsavel(client, como, dados.a.vendedor, empresa_id, segundo_vendedor.id)

    assert resposta.status_code == 403
