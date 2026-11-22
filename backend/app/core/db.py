"""Acesso ao PostgreSQL: pool de conexões e transações."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Conexao = psycopg.Connection[dict[str, Any]]


class Banco:
    def __init__(self, url: str) -> None:
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=False,
        )

    def abrir(self) -> None:
        self._pool.open(wait=True)

    def fechar(self) -> None:
        self._pool.close()

    @contextmanager
    def transacao(self) -> Iterator[Conexao]:
        """Uma conexão dentro de uma transação: commit no fim, rollback em exceção."""
        with self._pool.connection() as conn, conn.transaction():
            yield conn  # type: ignore[misc]
