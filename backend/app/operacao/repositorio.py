from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.db import Conexao
from app.operacao.esquemas import (
    EmpresaDaCampanhaDetalhe,
    EmpresaDaCampanhaResumo,
    EventoDoHistorico,
)

_EMPRESA_JSON = (
    "json_build_object('id', e.id, 'cnpj', e.cnpj, 'razao_social', e.razao_social, "
    "'nome_fantasia', e.nome_fantasia, 'situacao_cadastral', e.situacao_cadastral, "
    "'municipio_ibge', e.municipio_ibge, 'segmento', e.segmento, 'site', e.site)"
)
_RESPONSAVEL_JSON = (
    "CASE WHEN p.usuario_id IS NULL THEN NULL "
    "ELSE json_build_object('id', p.usuario_id, 'nome', p.nome) END"
)
_COLUNAS = (
    f"ec.id, ec.campanha_id, ec.tier, ec.nota_total, ec.ficha_status, ec.promovida_em, "
    f"{_RESPONSAVEL_JSON} AS responsavel, {_EMPRESA_JSON} AS empresa"
)
_DE = (
    "FROM empresas_da_campanha ec JOIN empresas e ON e.id = ec.empresa_id "
    "LEFT JOIN perfis p ON p.usuario_id = ec.responsavel_id"
)


# --- promoção ----------------------------------------------------------------------------


def reservar_chave(conn: Conexao, chave: str, campanha_id: uuid.UUID) -> dict[str, Any] | None:
    """Registra a chave do clique. Se ela já existia, devolve o resultado gravado antes."""
    nova = conn.execute(
        "INSERT INTO promocoes (chave, campanha_id) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING RETURNING chave",
        (chave, campanha_id),
    ).fetchone()
    if nova:
        return None
    anterior = conn.execute(
        "SELECT resultado FROM promocoes WHERE chave = %s FOR UPDATE", (chave,)
    ).fetchone()
    assert anterior is not None
    resultado: dict[str, Any] = anterior["resultado"] or {"promovidas": [], "ignoradas": []}
    return resultado


def gravar_resultado(conn: Conexao, chave: str, resultado: dict[str, Any]) -> None:
    conn.execute(
        "UPDATE promocoes SET resultado = %s WHERE chave = %s", (json.dumps(resultado), chave)
    )


def promover(
    conn: Conexao, campanha_id: uuid.UUID, candidato_ids: list[uuid.UUID]
) -> list[dict[str, Any]]:
    """Cria a empresa da campanha para cada candidato aprovado que ainda não foi promovido,
    exceto clientes atuais e empresas bloqueadas. Devolve as empresas criadas."""
    linhas = conn.execute(
        "INSERT INTO empresas_da_campanha (campanha_id, empresa_id, candidato_id, tier, nota_total) "
        "SELECT c.campanha_id, c.empresa_id, c.id, coalesce(c.tier_final, c.tier_sugerido, 'C'), "
        "c.nota_total FROM candidatos c JOIN empresas e ON e.id = c.empresa_id "
        "WHERE c.campanha_id = %(campanha)s AND c.id = ANY(%(ids)s) AND c.status = 'aprovado' "
        "AND NOT EXISTS (SELECT 1 FROM clientes_atuais ca WHERE ca.cnpj = e.cnpj) "
        "AND NOT EXISTS (SELECT 1 FROM lista_bloqueio b WHERE b.tipo = 'cnpj' "
        "                AND upper(b.valor) = e.cnpj) "
        "ON CONFLICT DO NOTHING "
        "RETURNING id, candidato_id",
        {"campanha": campanha_id, "ids": candidato_ids},
    ).fetchall()
    return list(linhas)


def registrar_no_historico(
    conn: Conexao,
    empresa_da_campanha_id: uuid.UUID,
    tipo: str,
    por_usuario: uuid.UUID | None,
    de_usuario: uuid.UUID | None = None,
    para_usuario: uuid.UUID | None = None,
    detalhes: dict[str, Any] | None = None,
    ocorrido_em: Any = None,
) -> None:
    conn.execute(
        "INSERT INTO historico (empresa_da_campanha_id, tipo, por_usuario, de_usuario, "
        "para_usuario, detalhes, ocorrido_em) VALUES (%s, %s, %s, %s, %s, %s, coalesce(%s, now()))",
        (
            empresa_da_campanha_id,
            tipo,
            por_usuario,
            de_usuario,
            para_usuario,
            json.dumps(detalhes or {}),
            ocorrido_em,
        ),
    )


def decisao_do_candidato(conn: Conexao, candidato_id: uuid.UUID) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT decidido_por, decidido_em FROM candidatos WHERE id = %s", (candidato_id,)
    ).fetchone()


def assumir(conn: Conexao, empresa_da_campanha_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
    linha = conn.execute(
        "UPDATE empresas_da_campanha SET responsavel_id = %s "
        "WHERE id = %s AND responsavel_id IS NULL RETURNING id",
        (usuario_id, empresa_da_campanha_id),
    ).fetchone()
    return linha is not None


def vendedor_da_campanha(conn: Conexao, campanha_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
    linha = conn.execute(
        "SELECT 1 FROM campanha_membros m JOIN perfis p ON p.usuario_id = m.usuario_id "
        "WHERE m.campanha_id = %s AND m.usuario_id = %s AND p.papel = 'vendedor' AND p.ativo",
        (campanha_id, usuario_id),
    ).fetchone()
    return linha is not None


def trocar_responsavel(
    conn: Conexao, empresa_da_campanha_id: uuid.UUID, usuario_id: uuid.UUID
) -> None:
    conn.execute(
        "UPDATE empresas_da_campanha SET responsavel_id = %s WHERE id = %s",
        (usuario_id, empresa_da_campanha_id),
    )


# --- leitura -----------------------------------------------------------------------------


def listar(conn: Conexao, campanha_id: uuid.UUID) -> list[EmpresaDaCampanhaResumo]:
    linhas = conn.execute(
        f"SELECT {_COLUNAS} {_DE} WHERE ec.campanha_id = %s "
        "ORDER BY ec.tier, ec.nota_total DESC NULLS LAST, e.razao_social",
        (campanha_id,),
    ).fetchall()
    return [EmpresaDaCampanhaResumo.model_validate(linha) for linha in linhas]


def buscar(conn: Conexao, empresa_da_campanha_id: uuid.UUID) -> dict[str, Any] | None:
    return conn.execute(
        f"SELECT {_COLUNAS}, ec.ficha, ec.responsavel_id, ec.empresa_id, e.endereco, e.sinais "
        f"{_DE} WHERE ec.id = %s",
        (empresa_da_campanha_id,),
    ).fetchone()


def contatos(conn: Conexao, empresa_id: uuid.UUID) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT tipo, valor, nome, fonte, status_validacao FROM contatos WHERE empresa_id = %s "
        "ORDER BY tipo, valor",
        (empresa_id,),
    ).fetchall()


def historico(conn: Conexao, empresa_da_campanha_id: uuid.UUID) -> list[EventoDoHistorico]:
    linhas = conn.execute(
        "SELECT tipo, por_usuario, de_usuario, para_usuario, detalhes, ocorrido_em "
        "FROM historico WHERE empresa_da_campanha_id = %s ORDER BY ocorrido_em, id",
        (empresa_da_campanha_id,),
    ).fetchall()
    return [EventoDoHistorico.model_validate(linha) for linha in linhas]


def montar_detalhe(
    linha: dict[str, Any],
    contatos_visiveis: list[dict[str, Any]],
    contato_oculto: bool,
    eventos: list[EventoDoHistorico],
) -> EmpresaDaCampanhaDetalhe:
    return EmpresaDaCampanhaDetalhe.model_validate(
        {
            **linha,
            "contatos": contatos_visiveis,
            "contato_oculto": contato_oculto,
            "historico": eventos,
        }
    )


# --- ficha (worker) ----------------------------------------------------------------------


def fichas_em_preparo(conn: Conexao, campanha_id: uuid.UUID, limite: int) -> list[dict[str, Any]]:
    fichas = conn.execute(
        "SELECT ec.id, e.id AS empresa_id, e.razao_social, e.nome_fantasia, e.segmento, "
        "e.municipio_ibge::text AS municipio_ibge, e.endereco, e.site, e.sinais "
        "FROM empresas_da_campanha ec JOIN empresas e ON e.id = ec.empresa_id "
        "WHERE ec.campanha_id = %s AND ec.ficha_status = 'preparando' "
        "ORDER BY ec.promovida_em LIMIT %s",
        (campanha_id, limite),
    ).fetchall()
    for ficha in fichas:
        ficha["evidencias"] = conn.execute(
            "SELECT campo, valor, fonte, coletado_em FROM evidencias WHERE empresa_id = %s "
            "AND campo NOT IN ('telefone', 'email', 'whatsapp', 'contato') "
            "ORDER BY coletado_em, campo",
            (ficha["empresa_id"],),
        ).fetchall()
    return fichas


def gravar_ficha(
    conn: Conexao,
    empresa_da_campanha_id: uuid.UUID,
    ficha: str | None,
    fatos: list[str],
    status: str,
) -> None:
    conn.execute(
        "UPDATE empresas_da_campanha SET ficha = %s, ficha_fatos = %s, ficha_status = %s, "
        "ficha_gerada_em = now() WHERE id = %s",
        (ficha, json.dumps(fatos), status, empresa_da_campanha_id),
    )
