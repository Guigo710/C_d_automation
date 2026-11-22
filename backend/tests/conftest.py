"""Base de testes: API real contra PostgreSQL real com RLS, duas organizações."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import jwt
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

RAIZ = Path(__file__).resolve().parents[2]
MIGRACOES = RAIZ / "supabase" / "migrations"
STUB = Path(__file__).parent / "sql" / "supabase_stub.sql"

URL_BANCO = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:54329/postgres"
)
SEGREDO_JWT = "segredo-de-teste-com-pelo-menos-32-bytes"


@dataclass(frozen=True)
class UsuarioDeTeste:
    id: uuid.UUID
    organizacao_id: uuid.UUID
    papel: str
    nome: str
    email: str


@dataclass(frozen=True)
class OrganizacaoDeTeste:
    id: uuid.UUID
    nome: str
    administrador: UsuarioDeTeste
    coordenador: UsuarioDeTeste
    vendedor: UsuarioDeTeste


@dataclass(frozen=True)
class Dados:
    a: OrganizacaoDeTeste
    b: OrganizacaoDeTeste


def _recriar_banco() -> None:
    with psycopg.connect(URL_BANCO, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("DROP SCHEMA IF EXISTS app CASCADE")
        conn.execute("DROP SCHEMA IF EXISTS auth CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(STUB.read_text(encoding="utf-8"))
        conn.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role")
        for migracao in sorted(MIGRACOES.glob("*.sql")):
            conn.execute(migracao.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def banco() -> Iterator[str]:
    _recriar_banco()
    yield URL_BANCO


@pytest.fixture(scope="session")
def settings(banco: str) -> Settings:
    return Settings(
        database_url=banco,
        supabase_jwt_secret=SEGREDO_JWT,
        worker_ativo=False,  # a fila é drenada pelos testes, de forma síncrona
        agente_prospeccao="falso",
    )


@pytest.fixture(scope="session")
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c


def _tabelas_de_negocio(conn: psycopg.Connection) -> list[str]:
    linhas = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'").fetchall()
    return [f"public.{linha[0]}" for linha in linhas]


def _criar_usuario(
    conn: psycopg.Connection, organizacao_id: uuid.UUID, papel: str, rotulo: str
) -> UsuarioDeTeste:
    usuario_id = uuid.uuid4()
    email = f"{papel}.{rotulo}@exemplo.com"
    nome = f"{papel.title()} {rotulo.upper()}"
    conn.execute("INSERT INTO auth.users (id, email) VALUES (%s, %s)", (usuario_id, email))
    conn.execute(
        "INSERT INTO perfis (usuario_id, organizacao_id, nome, email, papel) "
        "VALUES (%s, %s, %s, %s, %s)",
        (usuario_id, organizacao_id, nome, email, papel),
    )
    return UsuarioDeTeste(usuario_id, organizacao_id, papel, nome, email)


def _criar_organizacao(conn: psycopg.Connection, rotulo: str) -> OrganizacaoDeTeste:
    nome = f"Organização {rotulo.upper()}"
    linha = conn.execute(
        "INSERT INTO organizacoes (nome) VALUES (%s) RETURNING id", (nome,)
    ).fetchone()
    assert linha is not None
    org_id: uuid.UUID = linha[0]
    return OrganizacaoDeTeste(
        id=org_id,
        nome=nome,
        administrador=_criar_usuario(conn, org_id, "administrador", rotulo),
        coordenador=_criar_usuario(conn, org_id, "coordenador", rotulo),
        vendedor=_criar_usuario(conn, org_id, "vendedor", rotulo),
    )


@pytest.fixture
def conn_admin(banco: str) -> Iterator[psycopg.Connection]:
    """Conexão de superusuário, para preparar cenários fora da API."""
    with psycopg.connect(banco, autocommit=True) as conn:
        yield conn


@pytest.fixture
def dados(conn_admin: psycopg.Connection) -> Dados:
    tabelas = _tabelas_de_negocio(conn_admin) + ["auth.users"]
    conn_admin.execute(f"TRUNCATE {', '.join(tabelas)} CASCADE")
    return Dados(a=_criar_organizacao(conn_admin, "a"), b=_criar_organizacao(conn_admin, "b"))


def criar_segmento(
    conn: psycopg.Connection, organizacao_id: uuid.UUID, nome: str, cnaes: list[str]
) -> uuid.UUID:
    linha = conn.execute(
        "INSERT INTO catalogo_segmentos (organizacao_id, nome, cnaes) VALUES (%s, %s, %s) "
        "RETURNING id",
        (organizacao_id, nome, cnaes),
    ).fetchone()
    assert linha is not None
    segmento_id: uuid.UUID = linha[0]
    return segmento_id


def emitir_token(usuario_id: uuid.UUID, **extra: object) -> str:
    agora = int(time.time())
    claims: dict[str, object] = {
        "sub": str(usuario_id),
        "role": "authenticated",
        "aud": "authenticated",
        "iat": agora,
        "exp": agora + 3600,
        **extra,
    }
    return jwt.encode(claims, SEGREDO_JWT, algorithm="HS256")


@pytest.fixture
def como() -> Callable[[UsuarioDeTeste], dict[str, str]]:
    """Cabeçalhos de autorização para chamar a API como um usuário."""

    def _como(usuario: UsuarioDeTeste) -> dict[str, str]:
        return {"Authorization": f"Bearer {emitir_token(usuario.id)}"}

    return _como
