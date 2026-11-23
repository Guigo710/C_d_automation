# Commercial Department Automation

Plataforma em que agentes de IA encontram e pontuam empresas compradoras para uma organização; o coordenador faz a triagem e os vendedores assumem as empresas. A Destak é a primeira organização.

- Vocabulário: [GLOSSARY.md](GLOSSARY.md)
- Decisões: [docs/adr](docs/adr)
- Spec e tickets da v0: [.scratch/v0-demonstracao](.scratch/v0-demonstracao)

## Estado (23/11/2026)

Os tickets 01 a 09 e 11 a 13 da v0 estão implementados, e os 85 testes de API passam contra o PostgreSQL de teste (23/11/2026). Ainda não exercitados: a chamada real à Claude API (qualificação e ficha) e o agente de prospecção real. O ticket 10 (publicação no Supabase, Render e Vercel) depende de criar as contas.

O que roda em segundo plano, na fila do PostgreSQL (ADR 0004): prospecção (Agente de prospecção; o falso por padrão), qualificação (Agente 2, Claude Haiku 5.5) e ficha de abordagem (Claude Haiku 5.5). O Agente de prospecção real entra por `AGENTE_PROSPECCAO=pacote.modulo:Classe`; o contrato está em `backend/app/prospeccao/agente.py`.

## Estrutura

| Pasta | O quê |
|---|---|
| `backend/` | API FastAPI (Python 3.12+) |
| `frontend/` | SPA React + Vite + TypeScript |
| `supabase/migrations/` | Esquema do banco, RLS e funções (aplicados em ordem) |

## Desenvolvimento

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env   # preencher
.venv\Scripts\uvicorn app.main:create_app --factory --reload
```

Testes (precisam do Docker para o PostgreSQL de teste; o projeto compose `destak` não toca em outros containers, volumes ou imagens):

```powershell
docker compose -p destak up -d db-test
cd backend
.venv\Scripts\python -m pytest
.venv\Scripts\python -m mypy
.venv\Scripts\python -m ruff check app tests
```

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env   # preencher
npm run dev
```

### Contrato entre API e frontend

Os tipos do frontend são gerados do OpenAPI da API. Quando a API mudar:

```powershell
cd backend; .venv\Scripts\python -m app.openapi_export ..\frontend\openapi.json
cd ..\frontend; npm run gen:api
```

Um teste do backend falha se `frontend/openapi.json` estiver desatualizado, e o build do frontend quebra se o código usar o contrato antigo.

### Criar organização e usuários (administrador da plataforma)

```powershell
cd backend
.venv\Scripts\python -m app.cli criar-organizacao --nome "Destak"
.venv\Scripts\python -m app.cli semear-configuracao --organizacao-id <id>
.venv\Scripts\python -m app.cli criar-usuario --organizacao-id <id> --nome "Ana" --email ana@exemplo.com --papel coordenador
```
