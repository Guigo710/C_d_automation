from __future__ import annotations

import uuid

from app.core.db import Conexao
from app.organizacoes.esquemas import OrganizacaoOut, UsuarioOut


def listar_usuarios(conn: Conexao, papel: str | None) -> list[UsuarioOut]:
    linhas = conn.execute(
        "SELECT usuario_id AS id, nome, email, papel, ativo FROM perfis "
        "WHERE (%(papel)s::text IS NULL OR papel = %(papel)s) ORDER BY nome",
        {"papel": papel},
    ).fetchall()
    return [UsuarioOut.model_validate(linha) for linha in linhas]


def buscar_organizacao(conn: Conexao, organizacao_id: uuid.UUID) -> OrganizacaoOut | None:
    # Sem filtro de organização de propósito: o RLS só deixa ver a do usuário.
    linha = conn.execute(
        "SELECT id, nome FROM organizacoes WHERE id = %s", (organizacao_id,)
    ).fetchone()
    return OrganizacaoOut.model_validate(linha) if linha else None
