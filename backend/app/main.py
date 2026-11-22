from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.core.db import Banco
from app.core.seguranca import VerificadorDeToken
from app.organizacoes.rotas import router as organizacoes_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    banco = Banco(settings.database_url)

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        banco.abrir()
        try:
            yield
        finally:
            banco.fechar()

    app = FastAPI(title="Commercial Department Automation", lifespan=ciclo_de_vida)
    app.state.settings = settings
    app.state.banco = banco
    app.state.verificador = VerificadorDeToken(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["infra"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(organizacoes_router)
    return app
