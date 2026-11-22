"""O contrato da API usado pelo frontend precisa estar em dia com a API."""

from __future__ import annotations

from pathlib import Path

from app.openapi_export import contrato, serializar

CONTRATO_DO_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "openapi.json"


def test_contrato_do_frontend_esta_atualizado() -> None:
    atual = serializar(contrato())
    gravado = CONTRATO_DO_FRONTEND.read_text(encoding="utf-8")
    assert gravado == atual, (
        "A API mudou: rode `python -m app.openapi_export` no backend e `npm run gen:api` "
        "no frontend"
    )
