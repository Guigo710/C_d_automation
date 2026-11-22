"""Registro de auditoria. Os outros módulos registram eventos por `registrar`."""

from __future__ import annotations

from typing import Any

from app.auditoria import repositorio
from app.auditoria.esquemas import PaginaDeEventos
from app.auth.contexto import Contexto


def registrar(
    contexto: Contexto,
    acao: str,
    recurso_tipo: str | None = None,
    recurso_id: object | None = None,
    detalhes: dict[str, Any] | None = None,
) -> None:
    repositorio.registrar(
        contexto.conn,
        contexto.usuario.id,
        acao,
        recurso_tipo,
        str(recurso_id) if recurso_id is not None else None,
        detalhes,
    )


def listar(contexto: Contexto, limite: int, antes_de: int | None) -> PaginaDeEventos:
    itens = repositorio.listar(contexto.conn, limite, antes_de)
    proximo = itens[-1].id if len(itens) == limite else None
    return PaginaDeEventos(itens=itens, proximo_antes_de=proximo)
