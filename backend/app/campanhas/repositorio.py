from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.campanhas.esquemas import CampanhaIn, CampanhaOut, CampanhaResumo
from app.core.db import Conexao

_COLUNAS = (
    "id, nome, status, limite_empresas, teto_gasto_usd, criada_em, atualizada_em, "
    "municipios_ibge::text[] AS municipios_ibge, tiers_alvo::text[] AS tiers_alvo"
)


def listar(conn: Conexao) -> list[CampanhaResumo]:
    linhas = conn.execute(
        "SELECT id, nome, status, limite_empresas, teto_gasto_usd, criada_em "
        "FROM campanhas ORDER BY criada_em DESC"
    ).fetchall()
    return [CampanhaResumo.model_validate(linha) for linha in linhas]


def buscar(conn: Conexao, campanha_id: uuid.UUID) -> CampanhaOut | None:
    linha = conn.execute(
        f"SELECT {_COLUNAS} FROM campanhas WHERE id = %s", (campanha_id,)
    ).fetchone()
    if linha is None:
        return None
    segmentos = conn.execute(
        "SELECT s.id, s.nome FROM campanha_segmentos cs "
        "JOIN catalogo_segmentos s ON s.id = cs.segmento_id "
        "WHERE cs.campanha_id = %s ORDER BY s.nome",
        (campanha_id,),
    ).fetchall()
    membros = conn.execute(
        "SELECT p.usuario_id AS id, p.nome FROM campanha_membros m "
        "JOIN perfis p ON p.usuario_id = m.usuario_id "
        "WHERE m.campanha_id = %s ORDER BY p.nome",
        (campanha_id,),
    ).fetchall()
    return CampanhaOut.model_validate({**linha, "segmentos": segmentos, "membros": membros})


def criar(conn: Conexao, dados: CampanhaIn) -> uuid.UUID:
    linha = conn.execute(
        "INSERT INTO campanhas (nome, status, municipios_ibge, tiers_alvo, limite_empresas, "
        "teto_gasto_usd) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (
            dados.nome,
            dados.status,
            dados.municipios_ibge,
            list(dados.tiers_alvo),
            dados.limite_empresas,
            dados.teto_gasto_usd,
        ),
    ).fetchone()
    assert linha is not None
    campanha_id: uuid.UUID = linha["id"]  # type: ignore[assignment]
    _substituir_vinculos(conn, campanha_id, dados)
    return campanha_id


def atualizar(conn: Conexao, campanha_id: uuid.UUID, dados: CampanhaIn) -> bool:
    cursor = conn.execute(
        "UPDATE campanhas SET nome = %s, status = %s, municipios_ibge = %s, tiers_alvo = %s, "
        "limite_empresas = %s, teto_gasto_usd = %s, atualizada_em = now() WHERE id = %s",
        (
            dados.nome,
            dados.status,
            dados.municipios_ibge,
            list(dados.tiers_alvo),
            dados.limite_empresas,
            dados.teto_gasto_usd,
            campanha_id,
        ),
    )
    if cursor.rowcount == 0:
        return False
    _substituir_vinculos(conn, campanha_id, dados)
    return True


def _substituir_vinculos(conn: Conexao, campanha_id: uuid.UUID, dados: CampanhaIn) -> None:
    conn.execute("DELETE FROM campanha_segmentos WHERE campanha_id = %s", (campanha_id,))
    conn.execute("DELETE FROM campanha_membros WHERE campanha_id = %s", (campanha_id,))
    for segmento_id in dict.fromkeys(dados.segmento_ids):
        conn.execute(
            "INSERT INTO campanha_segmentos (campanha_id, segmento_id) VALUES (%s, %s)",
            (campanha_id, segmento_id),
        )
    for usuario_id in dict.fromkeys(dados.membro_ids):
        conn.execute(
            "INSERT INTO campanha_membros (campanha_id, usuario_id) VALUES (%s, %s)",
            (campanha_id, usuario_id),
        )


def vendedores_ativos(conn: Conexao, ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Ids, entre os pedidos, que são vendedores ativos da organização (o RLS filtra)."""
    linhas = conn.execute(
        "SELECT usuario_id FROM perfis WHERE usuario_id = ANY(%s) AND papel = 'vendedor' AND ativo",
        (list(ids),),
    ).fetchall()
    return {linha["usuario_id"] for linha in linhas}  # type: ignore[misc]
