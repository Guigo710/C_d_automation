"""Mapa único de permissões por papel. A API decide, não a tela."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, status

from app.auth.contexto import Contexto, ContextoDep

ADMINISTRADOR = "administrador"
COORDENADOR = "coordenador"
VENDEDOR = "vendedor"
TODOS = frozenset({ADMINISTRADOR, COORDENADOR, VENDEDOR})

PERMISSOES: dict[str, frozenset[str]] = {
    "organizacao.ler": TODOS,
    "sessao.registrar": TODOS,
    "auditoria.ler": frozenset({ADMINISTRADOR}),
    "usuarios.listar": frozenset({ADMINISTRADOR, COORDENADOR}),
    "configuracao.ler": TODOS,
    "configuracao.administrar": frozenset({ADMINISTRADOR}),
    "campanha.ler": TODOS,
    "campanha.editar": frozenset({COORDENADOR}),
    "prospeccao.executar": frozenset({COORDENADOR}),
    "prospeccao.ler": frozenset({ADMINISTRADOR, COORDENADOR}),
    "triagem.decidir": frozenset({COORDENADOR}),
    "lead.promover": frozenset({COORDENADOR}),
    "operacao.ler": TODOS,
    "lead.assumir": frozenset({VENDEDOR}),
}


def exige(permissao: str) -> Callable[[Contexto], Contexto]:
    papeis = PERMISSOES[permissao]

    def dependencia(contexto: ContextoDep) -> Contexto:
        if contexto.usuario.papel not in papeis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão")
        return contexto

    return dependencia
