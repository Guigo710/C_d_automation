"""Login de demonstração, sem Supabase. Só existe com DEMO_LOCAL=true e só atende localhost.

Emite um token assinado com o mesmo segredo que a API usa para validar, para um usuário
que já tem perfil no banco. A API continua lendo organização e papel do perfil.
"""

from __future__ import annotations

import time
import uuid

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.core.db import Banco

router = APIRouter(prefix="/demo", tags=["demo"], include_in_schema=False)

HOSTS_LOCAIS = frozenset({"127.0.0.1", "::1", "localhost"})


class UsuarioDeDemo(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papel: str
    organizacao: str


class LoginDeDemo(BaseModel):
    usuario_id: uuid.UUID


class TokenDeDemo(BaseModel):
    access_token: str


def _so_local(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in HOSTS_LOCAIS:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@router.get("/usuarios", response_model=list[UsuarioDeDemo])
def usuarios(request: Request) -> list[UsuarioDeDemo]:
    _so_local(request)
    banco: Banco = request.app.state.banco
    with banco.transacao() as conn:
        linhas = conn.execute(
            "SELECT p.usuario_id AS id, p.nome, p.email, p.papel, o.nome AS organizacao "
            "FROM perfis p JOIN organizacoes o ON o.id = p.organizacao_id WHERE p.ativo "
            "ORDER BY o.nome, array_position(ARRAY['coordenador', 'vendedor', 'administrador'], "
            "p.papel), p.nome"
        ).fetchall()
    return [UsuarioDeDemo.model_validate(linha) for linha in linhas]


@router.post("/login", response_model=TokenDeDemo)
def login(dados: LoginDeDemo, request: Request) -> TokenDeDemo:
    _so_local(request)
    segredo = request.app.state.settings.supabase_jwt_secret
    if not segredo:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Defina SUPABASE_JWT_SECRET")
    agora = int(time.time())
    token = jwt.encode(
        {
            "sub": str(dados.usuario_id),
            "role": "authenticated",
            "aud": request.app.state.settings.jwt_audience,
            "iat": agora,
            "exp": agora + 8 * 3600,
        },
        segredo,
        algorithm="HS256",
    )
    return TokenDeDemo(access_token=token)
