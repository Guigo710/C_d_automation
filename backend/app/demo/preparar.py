"""Prepara a demonstração local: banco 'demo' no PostgreSQL de teste, organização Destak com
regras de exemplo, quatro usuários fictícios, chave de IA de mentira e uma campanha pronta.

Uso (com `docker compose -p destak up -d db-test` rodando):
    python -m app.demo.preparar

Recria o banco 'demo' do zero a cada execução. Não toca no banco 'postgres' dos testes nem
em nenhum outro container. Também cria backend/.env.demo e frontend/.env.demo, se não
existirem (os dois ficam fora do git).
"""

from __future__ import annotations

import secrets
import uuid
from pathlib import Path

import psycopg
from cryptography.fernet import Fernet
from psycopg import sql

from app import semente
from app.configuracao.chaves import Cofre

BACKEND = Path(__file__).resolve().parents[2]
RAIZ = BACKEND.parent
MIGRACOES = RAIZ / "supabase" / "migrations"
STUB = BACKEND / "tests" / "sql" / "supabase_stub.sql"

SERVIDOR = "postgresql://postgres:postgres@localhost:54329"
BANCO_DEMO = "demo"

USUARIOS = [
    ("Ana Lima", "ana.coordenadora@demo.local", "coordenador"),
    ("Bruno Souza", "bruno.vendedor@demo.local", "vendedor"),
    ("Carla Dias", "carla.vendedora@demo.local", "vendedor"),
    ("Diego Alves", "diego.admin@demo.local", "administrador"),
]


def _ler_env(arquivo: Path) -> dict[str, str]:
    if not arquivo.exists():
        return {}
    pares = (linha.split("=", 1) for linha in arquivo.read_text(encoding="utf-8").splitlines())
    return {p[0].strip(): p[1].strip() for p in pares if len(p) == 2 and not p[0].startswith("#")}


def garantir_arquivos_env() -> dict[str, str]:
    env_backend = BACKEND / ".env.demo"
    if not env_backend.exists():
        env_backend.write_text(
            "# Gerado por python -m app.demo.preparar. Só para a demonstração local.\n"
            f"DATABASE_URL={SERVIDOR}/{BANCO_DEMO}\n"
            f"SUPABASE_JWT_SECRET={secrets.token_urlsafe(48)}\n"
            f"CHAVE_CIFRAGEM={Fernet.generate_key().decode()}\n"
            "DEMO_LOCAL=true\n"
            "CLIENTE_IA=demonstracao\n"
            "AGENTE_PROSPECCAO=falso\n"
            'CORS_ORIGINS=["http://localhost:5173"]\n'
            "WORKER_INTERVALO_SEGUNDOS=1\n",
            encoding="utf-8",
        )
    env_frontend = RAIZ / "frontend" / ".env.demo"
    if not env_frontend.exists():
        env_frontend.write_text(
            "VITE_DEMO_LOCAL=true\nVITE_API_URL=http://localhost:8000\n", encoding="utf-8"
        )
    return _ler_env(env_backend)


def recriar_banco() -> None:
    with psycopg.connect(f"{SERVIDOR}/postgres", autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (BANCO_DEMO,),
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(BANCO_DEMO)))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(BANCO_DEMO)))
    with psycopg.connect(f"{SERVIDOR}/{BANCO_DEMO}", autocommit=True) as conn:
        conn.execute(STUB.read_text(encoding="utf-8"))
        conn.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role")
        for migracao in sorted(MIGRACOES.glob("*.sql")):
            conn.execute(migracao.read_text(encoding="utf-8"))


def semear(env: dict[str, str]) -> None:
    url = f"{SERVIDOR}/{BANCO_DEMO}"
    with psycopg.connect(url, autocommit=True) as conn:
        linha = conn.execute(
            "INSERT INTO organizacoes (nome) VALUES ('Destak') RETURNING id"
        ).fetchone()
        assert linha is not None
        org: uuid.UUID = linha[0]
        ids: dict[str, uuid.UUID] = {}
        for nome, email, papel in USUARIOS:
            usuario = uuid.uuid4()
            ids[email] = usuario
            conn.execute("INSERT INTO auth.users (id, email) VALUES (%s, %s)", (usuario, email))
            conn.execute(
                "INSERT INTO perfis (usuario_id, organizacao_id, nome, email, papel) "
                "VALUES (%s, %s, %s, %s, %s)",
                (usuario, org, nome, email, papel),
            )

    semente.semear(url, org, semente.DESTAK)

    cofre = Cofre(env["CHAVE_CIFRAGEM"])
    coordenadora = ids["ana.coordenadora@demo.local"]
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO chaves_api (organizacao_id, fornecedor, chave_cifrada, final, "
            "atualizada_por) VALUES (%s, 'anthropic', %s, 'DEMO', %s)",
            (org, cofre.cifrar("demo-local-sem-custo"), ids["diego.admin@demo.local"]),
        )
        segmentos = [
            linha[0]
            for linha in conn.execute(
                "SELECT id FROM catalogo_segmentos WHERE organizacao_id = %s AND nome IN "
                "('Supermercado', 'Padaria', 'Atacarejo', 'Mercearia e minimercado')",
                (org,),
            ).fetchall()
        ]
        campanha = conn.execute(
            "INSERT INTO campanhas (organizacao_id, nome, status, municipios_ibge, tiers_alvo, "
            "limite_empresas, teto_gasto_usd, criada_por) VALUES (%s, %s, 'ativa', %s, "
            "'{A,B,C}', 300, 10, %s) RETURNING id",
            (
                org,
                "Varejo alimentar de Campinas e Jundiaí",
                ["3509502", "3525904"],
                coordenadora,
            ),
        ).fetchone()
        assert campanha is not None
        for segmento in segmentos:
            conn.execute(
                "INSERT INTO campanha_segmentos (campanha_id, segmento_id, organizacao_id) "
                "VALUES (%s, %s, %s)",
                (campanha[0], segmento, org),
            )
        for email in ("bruno.vendedor@demo.local", "carla.vendedora@demo.local"):
            conn.execute(
                "INSERT INTO campanha_membros (campanha_id, usuario_id, organizacao_id) "
                "VALUES (%s, %s, %s)",
                (campanha[0], ids[email], org),
            )


def main() -> None:
    env = garantir_arquivos_env()
    recriar_banco()
    semear(env)
    print("Demo pronta: banco 'demo' recriado com a Destak, 4 usuários e 1 campanha.")


if __name__ == "__main__":
    main()
