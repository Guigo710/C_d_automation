"""Transações em que os workers agem em nome de uma organização, com o papel 'sistema'.

O RLS continua valendo: o worker só enxerga e grava dados da organização do job.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.db import Banco, Conexao


@contextmanager
def como_sistema(
    banco: Banco, organizacao_id: uuid.UUID, usuario_id: uuid.UUID | None = None
) -> Iterator[Conexao]:
    with banco.transacao() as conn:
        claims = {
            "sub": str(usuario_id) if usuario_id else "",
            "role": "authenticated",
            "organizacao_id": str(organizacao_id),
            "papel": "sistema",
        }
        conn.execute("SET LOCAL ROLE authenticated")
        conn.execute("SELECT set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))
        yield conn
