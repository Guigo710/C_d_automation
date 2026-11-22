"""Script do administrador da plataforma: cria organizações e usuários sem tela (ADR 0001).

Exemplos:
    python -m app.cli criar-organizacao --nome "Destak"
    python -m app.cli criar-usuario --organizacao-id <uuid> --nome "Ana" \
        --email ana@destak.com.br --papel coordenador

Sem --senha, o usuário recebe um convite por e-mail do Supabase para criar a senha.
"""

from __future__ import annotations

import argparse
import uuid
from typing import Any

import httpx
import psycopg

from app.core.config import Settings

PAPEIS = ("administrador", "coordenador", "vendedor")


class AdminDoSupabase:
    """Cria usuários no Supabase Auth com a chave de serviço."""

    def __init__(self, url: str, chave_de_servico: str) -> None:
        self._http = httpx.Client(
            base_url=f"{url}/auth/v1",
            headers={"apikey": chave_de_servico, "Authorization": f"Bearer {chave_de_servico}"},
            timeout=30,
        )

    def criar_usuario(self, email: str, senha: str | None) -> uuid.UUID:
        if senha:
            corpo: dict[str, Any] = {"email": email, "password": senha, "email_confirm": True}
            resposta = self._http.post("/admin/users", json=corpo)
        else:
            resposta = self._http.post("/invite", json={"email": email})
        resposta.raise_for_status()
        return uuid.UUID(resposta.json()["id"])


def criar_organizacao(settings: Settings, nome: str) -> uuid.UUID:
    with psycopg.connect(settings.database_url) as conn:
        linha = conn.execute(
            "INSERT INTO organizacoes (nome) VALUES (%s) RETURNING id", (nome,)
        ).fetchone()
    assert linha is not None
    organizacao_id: uuid.UUID = linha[0]
    return organizacao_id


def criar_usuario(
    settings: Settings,
    admin: AdminDoSupabase,
    organizacao_id: uuid.UUID,
    nome: str,
    email: str,
    papel: str,
    senha: str | None,
) -> uuid.UUID:
    usuario_id = admin.criar_usuario(email, senha)
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(
            "INSERT INTO perfis (usuario_id, organizacao_id, nome, email, papel) "
            "VALUES (%s, %s, %s, %s, %s)",
            (usuario_id, organizacao_id, nome, email, papel),
        )
    return usuario_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    comandos = parser.add_subparsers(dest="comando", required=True)

    org = comandos.add_parser("criar-organizacao")
    org.add_argument("--nome", required=True)

    usr = comandos.add_parser("criar-usuario")
    usr.add_argument("--organizacao-id", required=True, type=uuid.UUID)
    usr.add_argument("--nome", required=True)
    usr.add_argument("--email", required=True)
    usr.add_argument("--papel", required=True, choices=PAPEIS)
    usr.add_argument("--senha")

    args = parser.parse_args()
    settings = Settings()  # type: ignore[call-arg]

    if args.comando == "criar-organizacao":
        print(criar_organizacao(settings, args.nome))
        return

    if not settings.supabase_url or not settings.supabase_service_role_key:
        parser.error("Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no backend/.env")
    admin = AdminDoSupabase(settings.supabase_url, settings.supabase_service_role_key)
    print(
        criar_usuario(
            settings, admin, args.organizacao_id, args.nome, args.email, args.papel, args.senha
        )
    )


if __name__ == "__main__":
    main()
