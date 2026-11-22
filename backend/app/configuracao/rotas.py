from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.contexto import Contexto
from app.auth.permissoes import exige
from app.configuracao import chaves, repositorio, servico
from app.configuracao.esquemas import (
    ChaveIn,
    ConfiguracaoDaOrganizacao,
    MunicipioOut,
    SegmentoOut,
    TetoIn,
)

router = APIRouter(tags=["configuração"])

LerConfiguracao = Annotated[Contexto, Depends(exige("configuracao.ler"))]
Administrar = Annotated[Contexto, Depends(exige("configuracao.administrar"))]


@router.get("/catalogo-segmentos", response_model=list[SegmentoOut])
def catalogo_segmentos(contexto: LerConfiguracao) -> list[SegmentoOut]:
    return repositorio.listar_segmentos(contexto.conn)


@router.get("/municipios-atendidos", response_model=list[MunicipioOut])
def municipios_atendidos(contexto: LerConfiguracao) -> list[MunicipioOut]:
    return repositorio.listar_municipios(contexto.conn)


@router.get("/configuracao", response_model=ConfiguracaoDaOrganizacao)
def ler_configuracao(contexto: Administrar) -> ConfiguracaoDaOrganizacao:
    return servico.configuracao(contexto)


@router.put("/configuracao/teto", response_model=ConfiguracaoDaOrganizacao)
def definir_teto(dados: TetoIn, contexto: Administrar) -> ConfiguracaoDaOrganizacao:
    return servico.definir_teto(contexto, dados.teto_mensal_usd)


@router.put("/configuracao/chaves/{fornecedor}", response_model=ConfiguracaoDaOrganizacao)
def salvar_chave(
    fornecedor: chaves.Fornecedor, dados: ChaveIn, request: Request, contexto: Administrar
) -> ConfiguracaoDaOrganizacao:
    try:
        return servico.salvar_chave(contexto, request.app.state.cofre, fornecedor, dados.chave)
    except chaves.CifragemIndisponivel as erro:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Cifragem de chaves não configurada no servidor"
        ) from erro


@router.delete("/configuracao/chaves/{fornecedor}", response_model=ConfiguracaoDaOrganizacao)
def remover_chave(
    fornecedor: chaves.Fornecedor, contexto: Administrar
) -> ConfiguracaoDaOrganizacao:
    return servico.remover_chave(contexto, fornecedor)
