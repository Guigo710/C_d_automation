"""Validação do token emitido pelo Supabase Auth (ADR 0003)."""

from __future__ import annotations

from functools import cached_property
from typing import Any

import jwt

from app.core.config import Settings


class TokenInvalido(Exception):
    pass


class VerificadorDeToken:
    def __init__(self, settings: Settings) -> None:
        if not settings.supabase_jwt_secret and not settings.supabase_url:
            raise ValueError("Defina SUPABASE_JWT_SECRET ou SUPABASE_URL para validar tokens")
        self._settings = settings

    @cached_property
    def _jwks(self) -> jwt.PyJWKClient:
        return jwt.PyJWKClient(f"{self._settings.supabase_url}/auth/v1/.well-known/jwks.json")

    def verificar(self, token: str) -> dict[str, Any]:
        """Devolve as claims de um token válido ou levanta TokenInvalido."""
        try:
            if self._settings.supabase_jwt_secret:
                chave: Any = self._settings.supabase_jwt_secret
                algoritmos = ["HS256"]
            else:
                chave = self._jwks.get_signing_key_from_jwt(token).key
                algoritmos = ["ES256", "RS256"]
            claims: dict[str, Any] = jwt.decode(
                token,
                chave,
                algorithms=algoritmos,
                audience=self._settings.jwt_audience,
                options={"require": ["sub", "exp"]},
            )
        except jwt.PyJWTError as erro:
            raise TokenInvalido(str(erro)) from erro
        return claims
