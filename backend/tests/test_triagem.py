"""Ticket 08: kanban de triagem.

Usa o mesmo cenário da qualificação: depois de drenar a fila, Bom Preço (A), Vila Nova (B),
Trigo Dourado (B) e Pães do Cambuí (revisão) ficam pendentes; Super Baixada fica recusada
por CNPJ inativo (sugerido).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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


def _triada(client: TestClient, campanha: Callable[..., str]) -> str:  # noqa: F811
    campanha_id = campanha()
    _fila(client).drenar()
    return campanha_id


def test_coordenador_aprova_em_lote_e_fica_na_auditoria(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    c = _candidatos(client, como, dados, campanha_id)
    ids = [c["Bom Preço Taquaral"]["id"], c["Mercado Vila Nova"]["id"], c["Super Baixada"]["id"]]

    resposta = client.post(
        f"/campanhas/{campanha_id}/aprovacoes",
        json={"candidato_ids": ids},
        headers=como(dados.a.coordenador),
    )

    assert resposta.status_code == 200
    assert set(resposta.json()["aprovados"]) == set(ids[:2])
    assert resposta.json()["ignorados"] == [ids[2]]  # recusado não é aprovado em lote
    depois = _candidatos(client, como, dados, campanha_id)
    assert depois["Bom Preço Taquaral"]["status"] == "aprovado"
    eventos = client.get("/auditoria", headers=como(dados.a.administrador)).json()["itens"]
    assert any(e["acao"] == "candidatos.aprovados" for e in eventos)


def test_recusa_exige_motivo(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    alvo = _candidatos(client, como, dados, campanha_id)["Trigo Dourado"]["id"]
    coord = como(dados.a.coordenador)

    assert client.post(f"/candidatos/{alvo}/recusa", json={}, headers=coord).status_code == 422
    assert (
        client.post(
            f"/candidatos/{alvo}/recusa", json={"motivo": "qualquer"}, headers=coord
        ).status_code
        == 422
    )
    ok = client.post(
        f"/candidatos/{alvo}/recusa", json={"motivo": "dados_incompletos"}, headers=coord
    )

    assert ok.status_code == 204
    trigo = _candidatos(client, como, dados, campanha_id)["Trigo Dourado"]
    assert trigo["status"] == "recusado"
    assert trigo["motivo_recusa"] == "dados_incompletos"
    assert trigo["recusa_sugerida"] is False


def test_troca_de_tier_exige_justificativa(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    alvo = _candidatos(client, como, dados, campanha_id)["Mercado Vila Nova"]["id"]
    coord = como(dados.a.coordenador)

    sem = client.put(f"/candidatos/{alvo}/tier", json={"tier": "A"}, headers=coord)
    com = client.put(
        f"/candidatos/{alvo}/tier",
        json={"tier": "A", "justificativa": "Abriu segunda loja em outubro"},
        headers=coord,
    )

    assert sem.status_code == 422
    assert com.status_code == 204
    vila = _candidatos(client, como, dados, campanha_id)["Mercado Vila Nova"]
    assert vila["tier_final"] == "A"
    assert vila["tier_sugerido"] == "B"


def test_coordenador_restaura_recusa_sugerida(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    baixada = _candidatos(client, como, dados, campanha_id)["Super Baixada"]["id"]

    resposta = client.post(f"/candidatos/{baixada}/restauracao", headers=como(dados.a.coordenador))

    assert resposta.status_code == 204
    depois = _candidatos(client, como, dados, campanha_id)["Super Baixada"]
    assert depois["status"] == "pendente"
    assert depois["motivo_recusa"] is None


def test_recusa_do_coordenador_nao_pode_ser_restaurada(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    alvo = _candidatos(client, como, dados, campanha_id)["Trigo Dourado"]["id"]
    coord = como(dados.a.coordenador)
    client.post(f"/candidatos/{alvo}/recusa", json={"motivo": "fora_do_perfil"}, headers=coord)

    assert client.post(f"/candidatos/{alvo}/restauracao", headers=coord).status_code == 409


def test_filtros_por_tier_e_segmento(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    coord = como(dados.a.coordenador)

    def nomes(**query: Any) -> set[str]:
        itens = client.get(
            f"/campanhas/{campanha_id}/candidatos", params=query, headers=coord
        ).json()["itens"]
        return {c["empresa"]["nome_fantasia"] for c in itens}

    assert nomes(tier="A") == {"Bom Preço Taquaral"}
    assert nomes(segmento="Padaria") == {"Trigo Dourado", "Pães do Cambuí"}
    assert nomes(status="recusado") == {"Super Baixada"}


def test_vendedor_e_outra_organizacao_nao_triam(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _triada(client, campanha)
    alvo = _candidatos(client, como, dados, campanha_id)["Trigo Dourado"]["id"]
    corpo = {"candidato_ids": [alvo]}

    vendedor = como(dados.a.vendedor)
    assert (
        client.post(
            f"/campanhas/{campanha_id}/aprovacoes", json=corpo, headers=vendedor
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/candidatos/{alvo}/recusa", json={"motivo": "duplicado"}, headers=vendedor
        ).status_code
        == 403
    )

    outra = como(dados.b.coordenador)
    assert (
        client.post(f"/campanhas/{campanha_id}/aprovacoes", json=corpo, headers=outra).status_code
        == 404
    )
    assert (
        client.post(
            f"/candidatos/{alvo}/recusa", json={"motivo": "duplicado"}, headers=outra
        ).status_code
        == 404
    )
