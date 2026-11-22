from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.auditoria import servico
from app.auditoria.esquemas import PaginaDeEventos
from app.auth.contexto import Contexto
from app.auth.permissoes import exige

router = APIRouter(tags=["auditoria"])


@router.post("/eu/login", status_code=status.HTTP_204_NO_CONTENT)
def registrar_login(contexto: Annotated[Contexto, Depends(exige("sessao.registrar"))]) -> Response:
    """O frontend avisa a API logo após o login no Supabase."""
    servico.registrar(contexto, "login", "usuario", contexto.usuario.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auditoria", response_model=PaginaDeEventos)
def listar(
    contexto: Annotated[Contexto, Depends(exige("auditoria.ler"))],
    limite: Annotated[int, Query(ge=1, le=200)] = 50,
    antes_de: int | None = None,
) -> PaginaDeEventos:
    return servico.listar(contexto, limite, antes_de)
