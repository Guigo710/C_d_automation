"""Ticket 02: registro de auditoria imutável."""

from __future__ import annotations

from collections.abc import Callable

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.conftest import Dados, UsuarioDeTeste

Como = Callable[[UsuarioDeTeste], dict[str, str]]


def _eventos(client: TestClient, como: Como, usuario: UsuarioDeTeste) -> list[dict[str, object]]:
    resposta = client.get("/auditoria", headers=como(usuario))
    assert resposta.status_code == 200
    itens: list[dict[str, object]] = resposta.json()["itens"]
    return itens


def test_login_fica_registrado_na_auditoria(client: TestClient, dados: Dados, como: Como) -> None:
    assert client.post("/eu/login", headers=como(dados.a.vendedor)).status_code == 204

    eventos = _eventos(client, como, dados.a.administrador)

    assert len(eventos) == 1
    assert eventos[0]["acao"] == "login"
    assert eventos[0]["usuario_id"] == str(dados.a.vendedor.id)


def test_so_administrador_le_a_auditoria(client: TestClient, dados: Dados, como: Como) -> None:
    assert client.get("/auditoria", headers=como(dados.a.coordenador)).status_code == 403
    assert client.get("/auditoria", headers=como(dados.a.vendedor)).status_code == 403


def test_eventos_de_uma_organizacao_nao_aparecem_para_outra(
    client: TestClient, dados: Dados, como: Como
) -> None:
    client.post("/eu/login", headers=como(dados.b.coordenador))

    assert _eventos(client, como, dados.a.administrador) == []
    assert len(_eventos(client, como, dados.b.administrador)) == 1


@pytest.mark.parametrize("comando", ["UPDATE auditoria SET acao = 'x'", "DELETE FROM auditoria"])
def test_banco_recusa_alterar_ou_apagar_evento(
    client: TestClient, dados: Dados, como: Como, conn_admin: psycopg.Connection, comando: str
) -> None:
    client.post("/eu/login", headers=como(dados.a.vendedor))

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn_admin.execute(comando)
