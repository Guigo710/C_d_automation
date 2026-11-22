from __future__ import annotations

import uuid

from app.auth.contexto import Contexto
from app.campanhas import repositorio
from app.campanhas.esquemas import CampanhaIn, CampanhaOut, CampanhaResumo
from app.configuracao import repositorio as configuracao


class CampanhaNaoEncontrada(Exception):
    pass


class CampanhaInvalida(Exception):
    pass


def _validar(contexto: Contexto, dados: CampanhaIn) -> None:
    pedidos = set(dados.segmento_ids)
    if configuracao.segmentos_existentes(contexto.conn, list(pedidos)) != pedidos:
        raise CampanhaInvalida("Segmento fora do catálogo da organização")
    membros = set(dados.membro_ids)
    if membros and repositorio.vendedores_ativos(contexto.conn, list(membros)) != membros:
        raise CampanhaInvalida("Todo membro precisa ser vendedor ativo da organização")


def listar(contexto: Contexto) -> list[CampanhaResumo]:
    return repositorio.listar(contexto.conn)


def buscar(contexto: Contexto, campanha_id: uuid.UUID) -> CampanhaOut:
    campanha = repositorio.buscar(contexto.conn, campanha_id)
    if campanha is None:
        raise CampanhaNaoEncontrada
    return campanha


def criar(contexto: Contexto, dados: CampanhaIn) -> CampanhaOut:
    _validar(contexto, dados)
    return buscar(contexto, repositorio.criar(contexto.conn, dados))


def atualizar(contexto: Contexto, campanha_id: uuid.UUID, dados: CampanhaIn) -> CampanhaOut:
    _validar(contexto, dados)
    if not repositorio.atualizar(contexto.conn, campanha_id, dados):
        raise CampanhaNaoEncontrada
    return buscar(contexto, campanha_id)
