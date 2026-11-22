# Commercial Department Automation

Plataforma em que agentes de IA encontram e pontuam empresas compradoras para uma organização; o coordenador faz a triagem e os vendedores assumem as empresas. A Destak é a primeira organização.

- Vocabulário: [GLOSSARY.md](GLOSSARY.md)
- Decisões: [docs/adr](docs/adr)
- Spec e tickets da v0: [.scratch/v0-demonstracao](.scratch/v0-demonstracao)

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

Testes (precisam do Docker para o PostgreSQL de teste):

```powershell
docker compose up -d db-test
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
.venv\Scripts\python -m app.cli criar-usuario --organizacao-id <id> --nome "Ana" --email ana@exemplo.com --papel coordenador
```
