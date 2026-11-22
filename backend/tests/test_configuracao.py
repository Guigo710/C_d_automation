"""Ticket 05: chaves de API e teto mensal."""

from __future__ import annotations

from collections.abc import Callable

import psycopg
from fastapi.testclient import TestClient

from app.configuracao import chaves
from app.core.sistema import como_sistema
from tests.conftest import Dados, UsuarioDeTeste

Como = Callable[[UsuarioDeTeste], dict[str, str]]

CHAVE = "sk-ant-api03-exemplo-de-chave-de-teste-ABCD"


def test_chave_salva_nunca_volta_inteira(client: TestClient, dados: Dados, como: Como) -> None:
    admin = como(dados.a.administrador)

    salva = client.put("/configuracao/chaves/anthropic", json={"chave": CHAVE}, headers=admin)
    lida = client.get("/configuracao", headers=admin)

    for resposta in (salva, lida):
        assert resposta.status_code == 200
        assert CHAVE not in resposta.text
        anthropic = next(c for c in resposta.json()["chaves"] if c["fornecedor"] == "anthropic")
        assert anthropic == {**anthropic, "configurada": True, "final": "ABCD"}


def test_chave_fica_cifrada_no_banco(
    client: TestClient, dados: Dados, como: Como, conn_admin: psycopg.Connection
) -> None:
    client.put(
        "/configuracao/chaves/google_places",
        json={"chave": CHAVE},
        headers=como(dados.a.administrador),
    )

    linha = conn_admin.execute("SELECT chave_cifrada FROM chaves_api").fetchone()
    assert linha is not None
    assert CHAVE.encode() not in bytes(linha[0])


def test_agentes_obtem_a_chave_da_propria_organizacao(
    client: TestClient, dados: Dados, como: Como
) -> None:
    client.put(
        "/configuracao/chaves/anthropic", json={"chave": CHAVE}, headers=como(dados.a.administrador)
    )
    banco = client.app.state.banco  # type: ignore[attr-defined]
    cofre = client.app.state.cofre  # type: ignore[attr-defined]

    with como_sistema(banco, dados.a.id) as conn:
        assert chaves.obter_chave(conn, cofre, "anthropic") == CHAVE
    with como_sistema(banco, dados.b.id) as conn:
        assert chaves.obter_chave(conn, cofre, "anthropic") is None


def test_remover_chave(client: TestClient, dados: Dados, como: Como) -> None:
    admin = como(dados.a.administrador)
    client.put("/configuracao/chaves/brave", json={"chave": CHAVE}, headers=admin)

    resposta = client.delete("/configuracao/chaves/brave", headers=admin)

    brave = next(c for c in resposta.json()["chaves"] if c["fornecedor"] == "brave")
    assert brave["configurada"] is False


def test_teto_mensal_e_gasto_do_mes(
    client: TestClient, dados: Dados, como: Como, conn_admin: psycopg.Connection
) -> None:
    admin = como(dados.a.administrador)
    conn_admin.execute(
        "INSERT INTO jobs (organizacao_id, tipo, status, custo_usd) VALUES "
        "(%(a)s, 'prospeccao', 'concluida', 1.25), (%(a)s, 'prospeccao', 'concluida', 0.50), "
        "(%(b)s, 'prospeccao', 'concluida', 9.00)",
        {"a": dados.a.id, "b": dados.b.id},
    )
    conn_admin.execute(
        "INSERT INTO jobs (organizacao_id, tipo, status, custo_usd, criado_em) "
        "VALUES (%s, 'prospeccao', 'concluida', 7.00, now() - interval '62 days')",
        (dados.a.id,),
    )

    resposta = client.put("/configuracao/teto", json={"teto_mensal_usd": "30.00"}, headers=admin)

    assert resposta.status_code == 200
    assert resposta.json()["teto_mensal_usd"] == "30.00"
    assert resposta.json()["gasto_do_mes_usd"] == "1.7500"


def test_so_administrador_mexe_na_configuracao(
    client: TestClient, dados: Dados, como: Como
) -> None:
    for usuario in (dados.a.coordenador, dados.a.vendedor):
        cab = como(usuario)
        assert client.get("/configuracao", headers=cab).status_code == 403
        assert (
            client.put("/configuracao/teto", json={"teto_mensal_usd": "1"}, headers=cab).status_code
            == 403
        )
        assert (
            client.put(
                "/configuracao/chaves/anthropic", json={"chave": CHAVE}, headers=cab
            ).status_code
            == 403
        )


def test_configuracao_de_uma_organizacao_nao_aparece_para_outra(
    client: TestClient, dados: Dados, como: Como
) -> None:
    client.put(
        "/configuracao/chaves/anthropic", json={"chave": CHAVE}, headers=como(dados.a.administrador)
    )

    outra = client.get("/configuracao", headers=como(dados.b.administrador)).json()

    assert all(not c["configurada"] for c in outra["chaves"])
