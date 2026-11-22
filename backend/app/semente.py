"""Configuração inicial de uma organização, preenchida pelo administrador da plataforma.

Na v0 não há tela para estas regras (ADR 0005). Os valores da Destak abaixo vêm das
hipóteses H1 e H2 do levantamento e dos CNAEs do Plano v2; ajustar quando a Destak
responder o levantamento (perguntas 2.4, 3.1 a 3.6).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import psycopg


@dataclass(frozen=True)
class Municipio:
    ibge: str
    nome: str
    uf: str
    tem_rota: bool


@dataclass(frozen=True)
class Semente:
    perfil_ideal: str
    segmentos: dict[str, list[str]]
    municipios: list[Municipio]
    clientes_atuais: list[str] = field(default_factory=list)


DESTAK = Semente(
    perfil_ideal=(
        "Varejo alimentar do interior de São Paulo (regiões de Campinas, Sorocaba e Jundiaí) "
        "que compra de atacadista com recorrência.\n"
        "Tier A (muito bom): atacarejo, distribuidor ou rede com várias lojas e volume alto.\n"
        "Tier B (bom): varejo de bairro (supermercado, mercearia, padaria, empório) com "
        "pedido recorrente.\n"
        "Tier C (aceitável): ticket pequeno ou dados incompletos, mas dentro da região e do "
        "segmento."
    ),
    segmentos={
        "Atacarejo": ["4711301"],
        "Supermercado": ["4711302"],
        "Mercearia e minimercado": ["4712100"],
        "Distribuidora": ["4639701", "4691500"],
        "Padaria": ["4721102"],
        "Hortifruti": ["4724500"],
        "Conveniência": ["4729602"],
        "Empório": ["4729699"],
    },
    municipios=[
        Municipio("3509502", "Campinas", "SP", tem_rota=True),
        Municipio("3552205", "Sorocaba", "SP", tem_rota=True),
        Municipio("3525904", "Jundiaí", "SP", tem_rota=True),
    ],
)


def semear(database_url: str, organizacao_id: uuid.UUID, semente: Semente) -> int:
    """Grava a semente como nova versão da configuração. Devolve o número da versão."""
    with psycopg.connect(database_url) as conn, conn.transaction():
        linha = conn.execute(
            "SELECT coalesce(max(versao), 0) + 1 FROM configuracoes_organizacao "
            "WHERE organizacao_id = %s",
            (organizacao_id,),
        ).fetchone()
        assert linha is not None
        versao: int = linha[0]
        conn.execute(
            "INSERT INTO configuracoes_organizacao (organizacao_id, versao, perfil_ideal) "
            "VALUES (%s, %s, %s)",
            (organizacao_id, versao, semente.perfil_ideal),
        )
        for nome, cnaes in semente.segmentos.items():
            conn.execute(
                "INSERT INTO catalogo_segmentos (organizacao_id, nome, cnaes) VALUES (%s, %s, %s) "
                "ON CONFLICT (organizacao_id, nome) DO UPDATE SET cnaes = EXCLUDED.cnaes",
                (organizacao_id, nome, cnaes),
            )
        for m in semente.municipios:
            conn.execute(
                "INSERT INTO municipios_atendidos (organizacao_id, municipio_ibge, nome, uf, tem_rota) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (organizacao_id, municipio_ibge) "
                "DO UPDATE SET nome = EXCLUDED.nome, uf = EXCLUDED.uf, tem_rota = EXCLUDED.tem_rota",
                (organizacao_id, m.ibge, m.nome, m.uf, m.tem_rota),
            )
        for cnpj in semente.clientes_atuais:
            conn.execute(
                "INSERT INTO clientes_atuais (organizacao_id, cnpj) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (organizacao_id, cnpj),
            )
    return versao
