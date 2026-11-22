"""Gera o contrato OpenAPI da API, de onde o frontend gera os tipos.

Uso: python -m app.openapi_export ../frontend/openapi.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.main import create_app


def contrato() -> dict[str, Any]:
    # O contrato não depende de banco nem de segredos reais.
    settings = Settings(database_url="postgresql://contrato", supabase_jwt_secret="contrato")
    esquema: dict[str, Any] = create_app(settings).openapi()
    return esquema


def serializar(esquema: dict[str, Any]) -> str:
    return json.dumps(esquema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../frontend/openapi.json")
    destino.write_text(serializar(contrato()), encoding="utf-8")
    print(f"contrato gravado em {destino}")
