"""Ticket 13: exportar aprovados para Excel."""

from __future__ import annotations

import io
from collections.abc import Callable

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from tests.conftest import Dados, UsuarioDeTeste
from tests.test_qualificacao import (  # noqa: F401  (fixtures)
    _candidatos,
    _fila,
    _limpar_chamadas,
    campanha,
    organizacao,
)

Como = Callable[[UsuarioDeTeste], dict[str, str]]


def _com_aprovados(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> str:
    campanha_id = campanha(membro_ids=[str(dados.a.vendedor.id)])
    _fila(client).drenar()
    c = _candidatos(client, como, dados, campanha_id)
    client.post(
        f"/campanhas/{campanha_id}/aprovacoes",
        json={"candidato_ids": [c["Bom Preço Taquaral"]["id"], c["Trigo Dourado"]["id"]]},
        headers=como(dados.a.coordenador),
    )
    return campanha_id


def test_coordenador_exporta_os_aprovados(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _com_aprovados(client, dados, como, campanha)

    resposta = client.get(
        f"/campanhas/{campanha_id}/aprovados.xlsx", headers=como(dados.a.coordenador)
    )

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/vnd.openxmlformats")
    aba = load_workbook(io.BytesIO(resposta.content)).active
    linhas = list(aba.iter_rows(values_only=True))
    assert linhas[0][:3] == ("Empresa", "Razão social", "CNPJ")
    assert {linha[0] for linha in linhas[1:]} == {"Bom Preço Taquaral", "Trigo Dourado"}
    assert all("@" not in str(celula) for linha in linhas for celula in linha)
    eventos = client.get("/auditoria", headers=como(dados.a.administrador)).json()["itens"]
    assert any(e["acao"] == "exportacao.aprovados" for e in eventos)


def test_vendedor_e_administrador_nao_exportam(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _com_aprovados(client, dados, como, campanha)
    for usuario in (dados.a.vendedor, dados.a.administrador):
        resposta = client.get(f"/campanhas/{campanha_id}/aprovados.xlsx", headers=como(usuario))
        assert resposta.status_code == 403


def test_outra_organizacao_nao_exporta(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],  # noqa: F811
) -> None:
    campanha_id = _com_aprovados(client, dados, como, campanha)
    resposta = client.get(
        f"/campanhas/{campanha_id}/aprovados.xlsx", headers=como(dados.b.coordenador)
    )
    assert resposta.status_code == 404
