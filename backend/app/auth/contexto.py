"""Quem está chamando a API, e a transação em que a requisição roda.

O perfil (organização e papel) vem sempre do banco, nunca das claims do token. Depois de
lê-lo, a transação muda para o papel `authenticated` e grava as claims da requisição, para
que o RLS restrinja toda consulta à organização do usuário (ADR 0002).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.db import Banco, Conexao
from app.core.seguranca import TokenInvalido, VerificadorDeToken


@dataclass(frozen=True)
class Usuario:
    id: uuid.UUID
    organizacao_id: uuid.UUID
    papel: str
    nome: str
    email: str


@dataclass(frozen=True)
class Contexto:
    conn: Conexao
    usuario: Usuario


def _token_do_cabecalho(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente")
    return authorization[7:].strip()


def contexto_da_requisicao(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> Iterator[Contexto]:
    verificador: VerificadorDeToken = request.app.state.verificador
    banco: Banco = request.app.state.banco

    try:
        claims = verificador.verificar(_token_do_cabecalho(authorization))
        usuario_id = uuid.UUID(str(claims["sub"]))
    except (TokenInvalido, ValueError) as erro:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from erro

    with banco.transacao() as conn:
        perfil = conn.execute(
            "SELECT usuario_id, organizacao_id, papel, nome, email, ativo "
            "FROM perfis WHERE usuario_id = %s",
            (usuario_id,),
        ).fetchone()
        if perfil is None or not perfil["ativo"]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário sem acesso")

        usuario = Usuario(
            id=usuario_id,
            organizacao_id=perfil["organizacao_id"],
            papel=str(perfil["papel"]),
            nome=str(perfil["nome"]),
            email=str(perfil["email"]),
        )
        claims_da_requisicao = {
            "sub": str(usuario.id),
            "role": "authenticated",
            "organizacao_id": str(usuario.organizacao_id),
            "papel": usuario.papel,
        }
        conn.execute("SET LOCAL ROLE authenticated")
        conn.execute(
            "SELECT set_config('request.jwt.claims', %s, true)",
            (json.dumps(claims_da_requisicao),),
        )
        yield Contexto(conn=conn, usuario=usuario)


ContextoDep = Annotated[Contexto, Depends(contexto_da_requisicao)]
