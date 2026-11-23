"""Ticket 07: qualificação (Agente 2).

Campanha de supermercados e padarias em Campinas. O agente falso devolve, nesta ordem:
Bom Preço Taquaral (3 lojas, site), Mercado Vila Nova (1 loja, sem site), Super Baixada
(CNPJ baixado), Trigo Dourado (padaria, 2 lojas, site) e Pães do Cambuí (padaria). O
cliente de IA falso está em tests/ia.py.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import semente
from tests.conftest import Dados, UsuarioDeTeste
from tests.ia import ClienteFalso

Como = Callable[[UsuarioDeTeste], dict[str, str]]

CAMPINAS = "3509502"
VALINHOS = "3556206"  # fora dos municípios atendidos da semente


@pytest.fixture(autouse=True)
def _limpar_chamadas() -> Iterator[None]:
    ClienteFalso.chamadas.clear()
    yield


@pytest.fixture
def organizacao(client: TestClient, dados: Dados, banco: str, como: Como) -> None:
    """Regras de exemplo da Destak na organização A e chave da Claude cadastrada."""
    semente.semear(banco, dados.a.id, semente.DESTAK)
    client.put(
        "/configuracao/chaves/anthropic",
        json={"chave": "sk-ant-chave-de-teste-1234"},
        headers=como(dados.a.administrador),
    )


@pytest.fixture
def campanha(
    client: TestClient, dados: Dados, conn_admin: psycopg.Connection, como: Como, organizacao: None
) -> Callable[..., str]:
    def _criar(**extra: Any) -> str:
        segmentos = conn_admin.execute(
            "SELECT id FROM catalogo_segmentos WHERE organizacao_id = %s "
            "AND nome IN ('Supermercado', 'Padaria')",
            (dados.a.id,),
        ).fetchall()
        corpo = {
            "nome": "Supermercados e padarias de Campinas",
            "status": "ativa",
            "municipios_ibge": [CAMPINAS],
            "segmento_ids": [str(s[0]) for s in segmentos],
            "tiers_alvo": ["A", "B", "C"],
            "limite_empresas": 100,
            "teto_gasto_usd": "10.00",
            **extra,
        }
        resposta = client.post("/campanhas", json=corpo, headers=como(dados.a.coordenador))
        assert resposta.status_code == 201, resposta.text
        campanha_id: str = resposta.json()["id"]
        client.post(f"/campanhas/{campanha_id}/execucoes", headers=como(dados.a.coordenador))
        return campanha_id

    return _criar


def _fila(client: TestClient) -> Any:
    return client.app.state.fila  # type: ignore[attr-defined]


def _candidatos(client: TestClient, como: Como, dados: Dados, campanha_id: str) -> dict[str, Any]:
    itens = client.get(
        f"/campanhas/{campanha_id}/candidatos", headers=como(dados.a.coordenador)
    ).json()["itens"]
    return {c["empresa"]["nome_fantasia"]: c for c in itens}


def _execucoes(client: TestClient, como: Como, dados: Dados, campanha_id: str) -> dict[str, Any]:
    lista = client.get(
        f"/campanhas/{campanha_id}/execucoes", headers=como(dados.a.coordenador)
    ).json()
    return {e["tipo"]: e for e in lista}


def test_qualificacao_da_notas_tier_e_recusas_sugeridas(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha_id = campanha()
    _fila(client).drenar()

    c = _candidatos(client, como, dados, campanha_id)

    assert c["Bom Preço Taquaral"]["status"] == "pendente"
    assert c["Bom Preço Taquaral"]["tier_sugerido"] == "A"
    assert c["Mercado Vila Nova"]["tier_sugerido"] == "B"
    assert c["Mercado Vila Nova"]["baixa_confianca"] is True
    assert c["Trigo Dourado"]["tier_sugerido"] == "B"
    assert c["Super Baixada"]["status"] == "recusado"
    assert c["Super Baixada"]["motivo_recusa"] == "cnpj_inativo"
    assert c["Super Baixada"]["recusa_sugerida"] is True
    assert _execucoes(client, como, dados, campanha_id)["qualificacao"]["status"] == "concluida"


def test_detalhe_mostra_notas_justificativa_e_versao_das_regras(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha_id = campanha()
    _fila(client).drenar()
    candidato_id = _candidatos(client, como, dados, campanha_id)["Bom Preço Taquaral"]["id"]

    d = client.get(f"/candidatos/{candidato_id}", headers=como(dados.a.coordenador)).json()

    assert d["nota_aderencia"] == 90
    assert d["nota_potencial"] == 70
    assert d["nota_geografia"] == 100  # Campinas tem rota na semente
    assert d["justificativas"]["aderencia"]
    assert d["justificativas"]["evidencias_citadas"]
    assert d["modelo"] == "claude-haiku-5-5"
    assert d["versao_prompt"] == "c-qualificacao-v1"
    assert d["versao_regras"] == 1
    assert {ct["status_validacao"] for ct in d["contatos"]} == {"valido"}


def test_resposta_com_evidencia_inexistente_vai_para_revisao(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha_id = campanha()
    _fila(client).drenar()

    paes = _candidatos(client, como, dados, campanha_id)["Pães do Cambuí"]
    detalhe = client.get(f"/candidatos/{paes['id']}", headers=como(dados.a.coordenador)).json()

    assert paes["em_revisao"] is True
    assert paes["tier_sugerido"] is None
    assert "inexistente" in detalhe["motivo_revisao"]
    # Reenviada uma vez: duas chamadas para a mesma empresa.
    assert sum('"Pães do Cambuí"' in e for e in ClienteFalso.chamadas) == 2


def test_ia_nao_recebe_telefone_nem_email(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha()
    _fila(client).drenar()

    assert ClienteFalso.chamadas
    for entrada in ClienteFalso.chamadas:
        assert "@" not in entrada
        assert "(19)" not in entrada


def test_exclusoes_por_regra(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],
    conn_admin: psycopg.Connection,
) -> None:
    conn_admin.execute(
        "INSERT INTO clientes_atuais (organizacao_id, cnpj) VALUES (%s, '99000001000107')",
        (dados.a.id,),
    )
    conn_admin.execute(
        "INSERT INTO lista_bloqueio (organizacao_id, tipo, valor) "
        "VALUES (%s, 'dominio', 'trigodourado.example.com')",
        (dados.a.id,),
    )
    campanha_id = campanha()
    _fila(client).drenar()

    c = _candidatos(client, como, dados, campanha_id)
    assert c["Bom Preço Taquaral"]["motivo_recusa"] == "ja_e_cliente"
    assert c["Trigo Dourado"]["motivo_recusa"] == "opt_out"


def test_fora_da_regiao_e_mesma_raiz_de_cnpj_em_outra_campanha(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],
    conn_admin: psycopg.Connection,
) -> None:
    # Outra campanha ativa já tem uma filial do Mercado Vila Nova (mesmo CNPJ básico).
    outra = conn_admin.execute(
        "INSERT INTO campanhas (organizacao_id, nome, status, municipios_ibge, limite_empresas, "
        "teto_gasto_usd, criada_por) VALUES (%s, 'Outra', 'ativa', '{3509502}', 10, 1, %s) "
        "RETURNING id",
        (dados.a.id, dados.a.coordenador.id),
    ).fetchone()
    filial = conn_admin.execute(
        "INSERT INTO empresas (organizacao_id, cnpj, razao_social) "
        "VALUES (%s, '99000002000299', 'Filial') RETURNING id",
        (dados.a.id,),
    ).fetchone()
    assert outra and filial
    conn_admin.execute(
        "INSERT INTO candidatos (organizacao_id, campanha_id, empresa_id) VALUES (%s, %s, %s)",
        (dados.a.id, outra[0], filial[0]),
    )

    campanha_id = campanha()
    _fila(client).processar_proximo()  # só a prospecção
    conn_admin.execute(
        "UPDATE campanhas SET municipios_ibge = %s WHERE id = %s",
        ([CAMPINAS, VALINHOS], campanha_id),
    )
    conn_admin.execute(
        "UPDATE empresas SET municipio_ibge = %s WHERE cnpj = '99000004000128'", (VALINHOS,)
    )
    conn_admin.execute(
        "UPDATE empresas SET municipio_ibge = '3550308' WHERE cnpj = '99000001000107'"
    )
    _fila(client).drenar()

    c = _candidatos(client, como, dados, campanha_id)
    assert c["Mercado Vila Nova"]["motivo_recusa"] == "duplicado"
    assert c["Bom Preço Taquaral"]["motivo_recusa"] == "fora_da_regiao"
    # Valinhos está na campanha, mas não é atendido pela organização: geografia 0.
    trigo = client.get(
        f"/candidatos/{c['Trigo Dourado']['id']}", headers=como(dados.a.coordenador)
    ).json()
    assert trigo["nota_geografia"] == 0


def test_mudar_as_regras_nao_altera_candidatos_ja_qualificados(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],
    conn_admin: psycopg.Connection,
) -> None:
    campanha_id = campanha()
    _fila(client).drenar()
    antes = _candidatos(client, como, dados, campanha_id)["Bom Preço Taquaral"]

    conn_admin.execute(
        "INSERT INTO configuracoes_organizacao (organizacao_id, versao, perfil_ideal, pesos, cortes) "
        'VALUES (%s, 2, \'outro\', \'{"aderencia": 10, "potencial": 10, "geografia": 10, '
        '"dados": 70}\', \'{"A": 99, "B": 98, "C": 97}\')',
        (dados.a.id,),
    )
    depois = client.get(f"/candidatos/{antes['id']}", headers=como(dados.a.coordenador)).json()

    assert depois["nota_total"] == antes["nota_total"]
    assert depois["tier_sugerido"] == "A"
    assert depois["versao_regras"] == 1


def test_sem_chave_da_ia_a_qualificacao_falha_e_pode_ser_repetida(
    client: TestClient,
    dados: Dados,
    como: Como,
    campanha: Callable[..., str],
) -> None:
    admin, coord = como(dados.a.administrador), como(dados.a.coordenador)
    client.delete("/configuracao/chaves/anthropic", headers=admin)
    campanha_id = campanha()
    _fila(client).drenar()

    qualificacao = _execucoes(client, como, dados, campanha_id)["qualificacao"]
    assert qualificacao["status"] == "falhou"
    assert "chave" in qualificacao["erro"].lower()
    assert (
        _candidatos(client, como, dados, campanha_id)["Bom Preço Taquaral"]["status"] == "coletado"
    )

    client.put(
        "/configuracao/chaves/anthropic", json={"chave": "sk-ant-nova-chave-5678"}, headers=admin
    )
    assert client.post(f"/campanhas/{campanha_id}/qualificacoes", headers=coord).status_code == 202
    _fila(client).drenar()

    assert (
        _candidatos(client, como, dados, campanha_id)["Bom Preço Taquaral"]["tier_sugerido"] == "A"
    )


def test_qualificacao_para_no_teto_de_gasto(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    # Prospecção: 5 empresas x US$ 0,03 = 0,15. Sobra US$ 0,01 = uma chamada de IA.
    campanha_id = campanha(teto_gasto_usd="0.16")
    _fila(client).drenar()

    qualificacao = _execucoes(client, como, dados, campanha_id)["qualificacao"]
    assert qualificacao["status"] == "parcial"
    assert qualificacao["motivo_parada"] == "teto_de_gasto"
    c = _candidatos(client, como, dados, campanha_id)
    assert c["Bom Preço Taquaral"]["status"] == "pendente"
    assert c["Mercado Vila Nova"]["status"] == "coletado"


def test_vendedor_nao_pede_qualificacao(
    client: TestClient, dados: Dados, como: Como, campanha: Callable[..., str]
) -> None:
    campanha_id = campanha()
    resposta = client.post(
        f"/campanhas/{campanha_id}/qualificacoes", headers=como(dados.a.vendedor)
    )
    assert resposta.status_code == 403
