"""Ticket 09: promoção e ficha de abordagem."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import Dados, UsuarioDeTeste
from tests.test_qualificacao import (  # noqa: F401  (fixtures)
    _candidatos,
    _fila,
    _limpar_chamadas,
    campanha,
    organizacao,
)

Como = Callable[[UsuarioDeTeste], dict[str, str]]


def _aprovados(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> tuple[str, dict[str, Any]]:
    """Campanha triada com Bom Preço e Vila Nova aprovados."""
    campanha_id = campanha()
    _fila(client).drenar()
    c = _candidatos(client, como, dados, campanha_id)
    client.post(
        f"/campanhas/{campanha_id}/aprovacoes",
        json={"candidato_ids": [c["Bom Preço Taquaral"]["id"], c["Mercado Vila Nova"]["id"]]},
        headers=como(dados.a.coordenador),
    )
    return campanha_id, c


def _promover(
    client: TestClient, dados: Dados, como: Como, campanha_id: str, ids: list[str], chave: str
) -> Any:
    return client.post(
        f"/campanhas/{campanha_id}/promocoes",
        json={"candidato_ids": ids},
        headers={**como(dados.a.coordenador), "Idempotency-Key": chave},
    )


def _empresas(client: TestClient, dados: Dados, como: Como, campanha_id: str) -> list[Any]:
    resposta = client.get(f"/campanhas/{campanha_id}/empresas", headers=como(dados.a.coordenador))
    assert resposta.status_code == 200
    lista: list[Any] = resposta.json()
    return lista


def test_promocao_cria_empresas_sem_responsavel_e_registra_historico(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    ids = [c["Bom Preço Taquaral"]["id"], c["Mercado Vila Nova"]["id"], c["Trigo Dourado"]["id"]]

    resposta = _promover(client, dados, como, campanha_id, ids, "clique-0001")

    assert resposta.status_code == 200
    assert set(resposta.json()["promovidas"]) == set(ids[:2])
    assert resposta.json()["ignoradas"] == [ids[2]]  # pendente, não aprovado
    empresas = _empresas(client, dados, como, campanha_id)
    assert {e["empresa"]["nome_fantasia"] for e in empresas} == {
        "Bom Preço Taquaral",
        "Mercado Vila Nova",
    }
    assert all(e["responsavel"] is None for e in empresas)
    assert {e["tier"] for e in empresas} == {"A", "B"}

    detalhe = client.get(
        f"/empresas-da-campanha/{empresas[0]['id']}", headers=como(dados.a.coordenador)
    ).json()
    assert [h["tipo"] for h in detalhe["historico"]] == ["aprovada", "promovida"]
    assert detalhe["historico"][1]["por_usuario"] == str(dados.a.coordenador.id)
    eventos = client.get("/auditoria", headers=como(dados.a.administrador)).json()["itens"]
    assert any(e["acao"] == "candidatos.promovidos" for e in eventos)


def test_repetir_o_clique_ou_o_lote_nao_duplica(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    ids = [c["Bom Preço Taquaral"]["id"], c["Mercado Vila Nova"]["id"]]

    primeira = _promover(client, dados, como, campanha_id, ids, "clique-0002").json()
    mesmo_clique = _promover(client, dados, como, campanha_id, ids, "clique-0002").json()
    outro_clique = _promover(client, dados, como, campanha_id, ids, "clique-0003").json()

    assert mesmo_clique == primeira
    assert outro_clique["promovidas"] == []
    assert len(_empresas(client, dados, como, campanha_id)) == 2


def test_promocao_exige_chave_de_idempotencia(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    resposta = client.post(
        f"/campanhas/{campanha_id}/promocoes",
        json={"candidato_ids": [c["Bom Preço Taquaral"]["id"]]},
        headers=como(dados.a.coordenador),
    )
    assert resposta.status_code == 422


def test_promocao_ignora_clientes_atuais_e_bloqueados(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
    conn_admin: psycopg.Connection,
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    # Viraram cliente e pediram bloqueio depois da aprovação.
    conn_admin.execute(
        "INSERT INTO clientes_atuais (organizacao_id, cnpj) VALUES (%s, '99000001000107')",
        (dados.a.id,),
    )
    conn_admin.execute(
        "INSERT INTO lista_bloqueio (organizacao_id, tipo, valor) VALUES (%s, 'cnpj', '99000002000114')",
        (dados.a.id,),
    )
    ids = [c["Bom Preço Taquaral"]["id"], c["Mercado Vila Nova"]["id"]]

    resposta = _promover(client, dados, como, campanha_id, ids, "clique-0004").json()

    assert resposta["promovidas"] == []
    assert _empresas(client, dados, como, campanha_id) == []


def test_ficha_fica_em_preparo_ate_o_job_terminar(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    _promover(client, dados, como, campanha_id, [c["Bom Preço Taquaral"]["id"]], "clique-0005")

    antes = _empresas(client, dados, como, campanha_id)[0]
    assert antes["ficha_status"] == "preparando"

    _fila(client).drenar()

    detalhe = client.get(
        f"/empresas-da-campanha/{antes['id']}", headers=como(dados.a.coordenador)
    ).json()
    assert detalhe["ficha_status"] == "pronta"
    assert detalhe["ficha"]
    assert detalhe["contato_oculto"] is False
    assert detalhe["contatos"]


def test_so_coordenador_promove(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    for usuario in (dados.a.vendedor, dados.a.administrador):
        resposta = client.post(
            f"/campanhas/{campanha_id}/promocoes",
            json={"candidato_ids": [c["Bom Preço Taquaral"]["id"]]},
            headers={**como(usuario), "Idempotency-Key": f"clique-{uuid.uuid4()}"},
        )
        assert resposta.status_code == 403


def test_outra_organizacao_nao_promove_nem_ve(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    _promover(client, dados, como, campanha_id, [c["Bom Preço Taquaral"]["id"]], "clique-0006")
    empresa_id = _empresas(client, dados, como, campanha_id)[0]["id"]
    outra = como(dados.b.coordenador)

    resposta = client.post(
        f"/campanhas/{campanha_id}/promocoes",
        json={"candidato_ids": [c["Mercado Vila Nova"]["id"]]},
        headers={**outra, "Idempotency-Key": "clique-0007"},
    )
    assert resposta.status_code == 404
    assert client.get(f"/empresas-da-campanha/{empresa_id}", headers=outra).status_code == 404


def test_candidato_enviado_fica_marcado_como_promovido(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id, c = _aprovados(client, dados, como, campanha)
    _promover(client, dados, como, campanha_id, [c["Bom Preço Taquaral"]["id"]], "clique-0008")

    depois = _candidatos(client, como, dados, campanha_id)

    assert depois["Bom Preço Taquaral"]["promovido"] is True
    assert depois["Mercado Vila Nova"]["promovido"] is False
