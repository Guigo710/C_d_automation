from __future__ import annotations

import uuid
from collections.abc import Sequence

from app.configuracao.esquemas import MunicipioOut, SegmentoOut
from app.core.db import Conexao


def listar_segmentos(conn: Conexao) -> list[SegmentoOut]:
    linhas = conn.execute(
        "SELECT id, nome, cnaes::text[] AS cnaes FROM catalogo_segmentos ORDER BY nome"
    ).fetchall()
    return [SegmentoOut.model_validate(linha) for linha in linhas]


def segmentos_existentes(conn: Conexao, ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    """Ids, entre os pedidos, que estão no catálogo da organização (o RLS filtra)."""
    linhas = conn.execute(
        "SELECT id FROM catalogo_segmentos WHERE id = ANY(%s)", (list(ids),)
    ).fetchall()
    return {linha["id"] for linha in linhas}  # type: ignore[misc]


def listar_municipios(conn: Conexao) -> list[MunicipioOut]:
    linhas = conn.execute(
        "SELECT municipio_ibge, nome, uf, tem_rota FROM municipios_atendidos ORDER BY nome"
    ).fetchall()
    return [MunicipioOut.model_validate(linha) for linha in linhas]
