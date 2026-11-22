from __future__ import annotations

import json
import uuid
from typing import Any

from app.auditoria.esquemas import EventoOut
from app.core.db import Conexao


def registrar(
    conn: Conexao,
    usuario_id: uuid.UUID | None,
    acao: str,
    recurso_tipo: str | None = None,
    recurso_id: str | None = None,
    detalhes: dict[str, Any] | None = None,
) -> None:
    # organizacao_id vem do default da coluna: a organização da requisição.
    conn.execute(
        "INSERT INTO auditoria (usuario_id, acao, recurso_tipo, recurso_id, detalhes) "
        "VALUES (%s, %s, %s, %s, %s)",
        (usuario_id, acao, recurso_tipo, recurso_id, json.dumps(detalhes or {})),
    )


def listar(conn: Conexao, limite: int, antes_de: int | None) -> list[EventoOut]:
    linhas = conn.execute(
        "SELECT id, usuario_id, acao, recurso_tipo, recurso_id, detalhes, criado_em "
        "FROM auditoria WHERE (%(antes)s::bigint IS NULL OR id < %(antes)s) "
        "ORDER BY id DESC LIMIT %(limite)s",
        {"antes": antes_de, "limite": limite},
    ).fetchall()
    return [EventoOut.model_validate(linha) for linha in linhas]
