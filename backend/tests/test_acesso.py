"""Ticket 01: login, "minha organização" e isolamento entre organizações."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import Dados, UsuarioDeTeste, emitir_token

Como = Callable[[UsuarioDeTeste], dict[str, str]]


def test_usuario_ve_a_propria_organizacao_e_o_papel(
    client: TestClient, dados: Dados, como: Como
) -> None:
    resposta = client.get("/eu", headers=como(dados.a.coordenador))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["papel"] == "coordenador"
    assert corpo["email"] == "coordenador.a@exemplo.com"
    assert corpo["organizacao"] == {"id": str(dados.a.id), "nome": "Organização A"}


def test_sem_token_a_api_recusa(client: TestClient, dados: Dados) -> None:
    assert client.get("/eu").status_code == 401


def test_token_com_assinatura_invalida_e_recusado(client: TestClient, dados: Dados) -> None:
    token = emitir_token(dados.a.vendedor.id) + "x"
    resposta = client.get("/eu", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 401


def test_usuario_sem_perfil_e_recusado(
    client: TestClient, dados: Dados, conn_admin: psycopg.Connection
) -> None:
    sem_perfil = uuid.uuid4()
    conn_admin.execute("INSERT INTO auth.users (id, email) VALUES (%s, 'x@exemplo.com')", (sem_perfil,))

    resposta = client.get("/eu", headers={"Authorization": f"Bearer {emitir_token(sem_perfil)}"})

    assert resposta.status_code == 403


def test_usuario_inativo_e_recusado(
    client: TestClient, dados: Dados, como: Como, conn_admin: psycopg.Connection
) -> None:
    conn_admin.execute(
        "UPDATE perfis SET ativo = false WHERE usuario_id = %s", (dados.a.vendedor.id,)
    )
    assert client.get("/eu", headers=como(dados.a.vendedor)).status_code == 403


def test_claims_do_token_nao_mudam_a_organizacao_do_usuario(
    client: TestClient, dados: Dados
) -> None:
    token = emitir_token(dados.a.vendedor.id, organizacao_id=str(dados.b.id), papel="administrador")

    corpo = client.get("/eu", headers={"Authorization": f"Bearer {token}"}).json()

    assert corpo["organizacao"]["id"] == str(dados.a.id)
    assert corpo["papel"] == "vendedor"


def test_usuario_le_a_propria_organizacao_por_id(
    client: TestClient, dados: Dados, como: Como
) -> None:
    resposta = client.get(f"/organizacoes/{dados.a.id}", headers=como(dados.a.vendedor))
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Organização A"


def test_organizacao_de_outra_organizacao_nao_e_encontrada(
    client: TestClient, dados: Dados, como: Como
) -> None:
    # A consulta por id não filtra por organização: quem barra é o RLS.
    resposta = client.get(f"/organizacoes/{dados.b.id}", headers=como(dados.a.administrador))
    assert resposta.status_code == 404


def test_hook_do_supabase_poe_organizacao_e_papel_do_perfil_no_token(
    dados: Dados, conn_admin: psycopg.Connection
) -> None:
    evento = {
        "user_id": str(dados.b.coordenador.id),
        "claims": {"sub": str(dados.b.coordenador.id), "papel": "administrador"},
    }
    linha = conn_admin.execute(
        "SELECT public.custom_access_token_hook(%s::jsonb)", (json.dumps(evento),)
    ).fetchone()
    assert linha is not None

    claims = linha[0]["claims"]
    assert claims["organizacao_id"] == str(dados.b.id)
    assert claims["papel"] == "coordenador"


def test_hook_nao_poe_claims_para_usuario_inativo(
    dados: Dados, conn_admin: psycopg.Connection
) -> None:
    conn_admin.execute(
        "UPDATE perfis SET ativo = false WHERE usuario_id = %s", (dados.a.coordenador.id,)
    )
    evento = {"user_id": str(dados.a.coordenador.id), "claims": {"papel": "coordenador"}}
    linha = conn_admin.execute(
        "SELECT public.custom_access_token_hook(%s::jsonb)", (json.dumps(evento),)
    ).fetchone()
    assert linha is not None

    claims = linha[0]["claims"]
    assert "organizacao_id" not in claims
    assert "papel" not in claims
