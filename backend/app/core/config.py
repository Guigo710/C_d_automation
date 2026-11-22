"""Configuração da API, lida de variáveis de ambiente (ou de backend/.env)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Conexão direta com o PostgreSQL (no Supabase, a connection string do usuário postgres).
    database_url: str

    # Validação do token do Supabase Auth: segredo HS256 (projetos com "Legacy JWT secret")
    # ou, sem segredo, as chaves públicas publicadas pelo projeto em SUPABASE_URL.
    supabase_jwt_secret: str | None = None
    supabase_url: str | None = None
    jwt_audience: str = "authenticated"

    # Só para o script do administrador da plataforma (criar organizações e usuários).
    supabase_service_role_key: str | None = None

    cors_origins: list[str] = ["http://localhost:5173"]

    # Worker de jobs no mesmo processo da API (ADR 0004). Nos testes fica desligado e a
    # fila é drenada de forma síncrona.
    worker_ativo: bool = True
    worker_intervalo_segundos: float = 2.0
    job_lease_segundos: int = 120

    # Agente de prospecção: "falso" ou "pacote.modulo:Classe".
    agente_prospeccao: str = "falso"
