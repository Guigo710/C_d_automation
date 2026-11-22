from __future__ import annotations

from decimal import Decimal

from app.auditoria import servico as auditoria
from app.auth.contexto import Contexto
from app.configuracao import chaves
from app.configuracao.esquemas import ChaveStatus, ConfiguracaoDaOrganizacao


def configuracao(contexto: Contexto) -> ConfiguracaoDaOrganizacao:
    conn = contexto.conn
    org = conn.execute(
        "SELECT teto_mensal_usd, app.gasto_do_mes() AS gasto FROM organizacoes WHERE id = %s",
        (contexto.usuario.organizacao_id,),
    ).fetchone()
    assert org is not None
    salvas = {
        linha["fornecedor"]: linha
        for linha in conn.execute(
            "SELECT fornecedor, final, atualizada_em FROM chaves_api"
        ).fetchall()
    }
    return ConfiguracaoDaOrganizacao(
        teto_mensal_usd=org["teto_mensal_usd"],
        gasto_do_mes_usd=org["gasto"],
        chaves=[
            ChaveStatus(
                fornecedor=f,
                configurada=f in salvas,
                final=salvas[f]["final"] if f in salvas else None,
                atualizada_em=salvas[f]["atualizada_em"] if f in salvas else None,
            )
            for f in chaves.FORNECEDORES
        ],
    )


def definir_teto(contexto: Contexto, teto: Decimal) -> ConfiguracaoDaOrganizacao:
    contexto.conn.execute(
        "UPDATE organizacoes SET teto_mensal_usd = %s WHERE id = %s",
        (teto, contexto.usuario.organizacao_id),
    )
    auditoria.registrar(
        contexto,
        "teto_mensal.alterado",
        "organizacao",
        contexto.usuario.organizacao_id,
        {"teto_mensal_usd": str(teto)},
    )
    return configuracao(contexto)


def salvar_chave(
    contexto: Contexto, cofre: chaves.Cofre, fornecedor: chaves.Fornecedor, chave: str
) -> ConfiguracaoDaOrganizacao:
    chaves.salvar_chave(contexto.conn, cofre, fornecedor, chave)
    auditoria.registrar(contexto, "chave_api.alterada", "chave_api", fornecedor)
    return configuracao(contexto)


def remover_chave(contexto: Contexto, fornecedor: chaves.Fornecedor) -> ConfiguracaoDaOrganizacao:
    if chaves.remover_chave(contexto.conn, fornecedor):
        auditoria.registrar(contexto, "chave_api.removida", "chave_api", fornecedor)
    return configuracao(contexto)
