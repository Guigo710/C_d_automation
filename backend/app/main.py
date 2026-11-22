from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auditoria.rotas import router as auditoria_router
from app.campanhas.rotas import router as campanhas_router
from app.configuracao.chaves import Cofre
from app.configuracao.rotas import router as configuracao_router
from app.core.config import Settings
from app.core.db import Banco
from app.core.seguranca import VerificadorDeToken
from app.fila.fila import Fila
from app.organizacoes.rotas import router as organizacoes_router
from app.prospeccao import servico as prospeccao
from app.prospeccao.rotas import router as prospeccao_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    banco = Banco(settings.database_url)
    fila = Fila(banco, settings.job_lease_segundos, settings.worker_intervalo_segundos)
    fila.registrar(prospeccao.TIPO_JOB, prospeccao.executor(settings))

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        banco.abrir()
        if settings.worker_ativo:
            fila.iniciar()
        try:
            yield
        finally:
            fila.parar()
            banco.fechar()

    app = FastAPI(title="Commercial Department Automation", lifespan=ciclo_de_vida)
    app.state.settings = settings
    app.state.banco = banco
    app.state.fila = fila
    app.state.verificador = VerificadorDeToken(settings)
    app.state.cofre = Cofre(settings.chave_cifragem)

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
    app.include_router(auditoria_router)
    app.include_router(configuracao_router)
    app.include_router(campanhas_router)
    app.include_router(prospeccao_router)
    return app
