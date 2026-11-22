from __future__ import annotations

import uuid

from app.auth.contexto import Contexto
from app.organizacoes import repositorio
from app.organizacoes.esquemas import EuOut, OrganizacaoOut


class OrganizacaoNaoEncontrada(Exception):
    pass


def organizacao(contexto: Contexto, organizacao_id: uuid.UUID) -> OrganizacaoOut:
    encontrada = repositorio.buscar_organizacao(contexto.conn, organizacao_id)
    if encontrada is None:
        raise OrganizacaoNaoEncontrada
    return encontrada


def eu(contexto: Contexto) -> EuOut:
    usuario = contexto.usuario
    return EuOut(
        usuario_id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel,
        organizacao=organizacao(contexto, usuario.organizacao_id),
    )
