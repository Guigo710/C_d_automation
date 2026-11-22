from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any, Literal

from app.core.db import Conexao
from app.prospeccao.agente import CandidatoProspectado, FotoDaCampanha, SegmentoAlvo
from app.prospeccao.esquemas import (
    CandidatoDetalhe,
    CandidatoResumo,
    ExecucaoOut,
    PaginaDeCandidatos,
)

_COLUNAS_JOB = (
    "id, tipo, campanha_id, status, motivo_parada, encontradas, gravadas, duplicadas, custo_usd, "
    "erro, criado_em, iniciado_em, terminado_em"
)

_COLUNAS_CANDIDATO = (
    "c.id, c.campanha_id, c.status, c.criado_em, c.nota_total, c.tier_sugerido, c.tier_final, "
    "c.motivo_recusa, c.recusa_sugerida, c.baixa_confianca, c.em_revisao"
)

_EMPRESA_JSON = (
    "json_build_object('id', e.id, 'cnpj', e.cnpj, 'razao_social', e.razao_social, "
    "'nome_fantasia', e.nome_fantasia, 'situacao_cadastral', e.situacao_cadastral, "
    "'municipio_ibge', e.municipio_ibge, 'segmento', e.segmento, 'site', e.site)"
)


# --- execuções ---------------------------------------------------------------------------


def execucao_em_andamento(conn: Conexao, campanha_id: uuid.UUID) -> bool:
    linha = conn.execute(
        "SELECT 1 FROM jobs WHERE campanha_id = %s AND tipo = 'prospeccao' "
        "AND status IN ('na_fila', 'executando')",
        (campanha_id,),
    ).fetchone()
    return linha is not None


def buscar_execucao(conn: Conexao, job_id: uuid.UUID) -> ExecucaoOut | None:
    linha = conn.execute(f"SELECT {_COLUNAS_JOB} FROM jobs WHERE id = %s", (job_id,)).fetchone()
    return ExecucaoOut.model_validate(linha) if linha else None


def listar_execucoes(conn: Conexao, campanha_id: uuid.UUID) -> list[ExecucaoOut]:
    linhas = conn.execute(
        f"SELECT {_COLUNAS_JOB} FROM jobs WHERE campanha_id = %s ORDER BY criado_em DESC",
        (campanha_id,),
    ).fetchall()
    return [ExecucaoOut.model_validate(linha) for linha in linhas]


Resultado = Literal["gravada", "duplicada", "ja_processada"]


def registrar_progresso(
    conn: Conexao, job_id: uuid.UUID, resultado: Resultado, custo: Decimal
) -> None:
    """Conta o candidato no job. Um candidato que este mesmo job já gravou antes de ser
    interrompido não conta de novo, nem o seu custo."""
    if resultado == "ja_processada":
        conn.execute("UPDATE jobs SET ultima_atividade = now() WHERE id = %s", (job_id,))
        return
    conn.execute(
        "UPDATE jobs SET encontradas = encontradas + 1, "
        "gravadas = gravadas + %(g)s, duplicadas = duplicadas + %(d)s, "
        "custo_usd = custo_usd + %(custo)s, ultima_atividade = now() WHERE id = %(id)s",
        {
            "g": 1 if resultado == "gravada" else 0,
            "d": 1 if resultado == "duplicada" else 0,
            "custo": custo,
            "id": job_id,
        },
    )


def terminar_execucao(
    conn: Conexao, job_id: uuid.UUID, status: str, motivo: str | None = None
) -> None:
    conn.execute(
        "UPDATE jobs SET status = %s, motivo_parada = %s, terminado_em = now(), lease_ate = NULL "
        "WHERE id = %s",
        (status, motivo, job_id),
    )


# --- fotografia da campanha --------------------------------------------------------------


def foto_da_campanha(conn: Conexao, campanha_id: uuid.UUID) -> FotoDaCampanha | None:
    campanha = conn.execute(
        "SELECT id, organizacao_id, municipios_ibge::text[] AS municipios_ibge, "
        "limite_empresas, teto_gasto_usd FROM campanhas WHERE id = %s",
        (campanha_id,),
    ).fetchone()
    if campanha is None:
        return None
    segmentos = conn.execute(
        "SELECT s.nome, s.cnaes::text[] AS cnaes FROM campanha_segmentos cs "
        "JOIN catalogo_segmentos s ON s.id = cs.segmento_id WHERE cs.campanha_id = %s "
        "ORDER BY s.nome",
        (campanha_id,),
    ).fetchall()
    saldo_campanha = campanha["teto_gasto_usd"] - gasto_da_campanha(conn, campanha_id)
    saldo_mensal = saldo_mensal_da_organizacao(conn)
    return FotoDaCampanha(
        organizacao_id=campanha["organizacao_id"],
        campanha_id=campanha_id,
        municipios_ibge=list(campanha["municipios_ibge"]),
        segmentos=[SegmentoAlvo(nome=str(s["nome"]), cnaes=list(s["cnaes"])) for s in segmentos],
        limite_empresas=int(campanha["limite_empresas"]),
        saldo_teto_usd=max(min(saldo_campanha, saldo_mensal), Decimal(0)),
    )


def saldo_mensal_da_organizacao(conn: Conexao) -> Decimal:
    linha = conn.execute(
        "SELECT teto_mensal_usd - app.gasto_do_mes() AS saldo FROM organizacoes "
        "WHERE id = app.organizacao_atual()"
    ).fetchone()
    assert linha is not None
    saldo: Decimal = linha["saldo"]
    return saldo


def gasto_da_campanha(conn: Conexao, campanha_id: uuid.UUID) -> Decimal:
    linha = conn.execute(
        "SELECT coalesce(sum(custo_usd), 0) AS total FROM jobs WHERE campanha_id = %s",
        (campanha_id,),
    ).fetchone()
    assert linha is not None
    total: Decimal = linha["total"]
    return total


def candidatos_na_campanha(conn: Conexao, campanha_id: uuid.UUID) -> int:
    linha = conn.execute(
        "SELECT count(*) AS n FROM candidatos WHERE campanha_id = %s", (campanha_id,)
    ).fetchone()
    assert linha is not None
    return int(linha["n"])


# --- gravação de um candidato ------------------------------------------------------------


def gravar_candidato(
    conn: Conexao, campanha_id: uuid.UUID, job_id: uuid.UUID, c: CandidatoProspectado
) -> Resultado:
    """Grava empresa, contatos, evidências e candidato. Mesmo CNPJ já nesta campanha ou em
    outra campanha ativa da organização conta como duplicada e não é gravado de novo; se foi
    este mesmo job que o gravou (execução retomada), é 'ja_processada'."""
    cnpj = c.cnpj.strip().upper()
    existente = conn.execute(
        "SELECT ca.job_id FROM candidatos ca JOIN empresas e ON e.id = ca.empresa_id "
        "JOIN campanhas cp ON cp.id = ca.campanha_id "
        "WHERE e.cnpj = %s AND (ca.campanha_id = %s OR cp.status = 'ativa') "
        "ORDER BY (ca.job_id = %s) DESC NULLS LAST LIMIT 1",
        (cnpj, campanha_id, job_id),
    ).fetchone()
    if existente:
        return "ja_processada" if existente["job_id"] == job_id else "duplicada"

    linha = conn.execute(
        "INSERT INTO empresas (cnpj, razao_social, nome_fantasia, situacao_cadastral, endereco, "
        "municipio_ibge, segmento, site, sinais) "
        "VALUES (%(cnpj)s, %(razao)s, %(fantasia)s, %(situacao)s, %(endereco)s, %(municipio)s, "
        "%(segmento)s, %(site)s, %(sinais)s) "
        "ON CONFLICT (organizacao_id, cnpj) DO UPDATE SET razao_social = EXCLUDED.razao_social, "
        "nome_fantasia = EXCLUDED.nome_fantasia, situacao_cadastral = EXCLUDED.situacao_cadastral, "
        "endereco = EXCLUDED.endereco, municipio_ibge = EXCLUDED.municipio_ibge, "
        "segmento = EXCLUDED.segmento, site = EXCLUDED.site, sinais = EXCLUDED.sinais, "
        "atualizada_em = now() RETURNING id",
        {
            "cnpj": cnpj,
            "razao": c.razao_social,
            "fantasia": c.nome_fantasia,
            "situacao": c.situacao_cadastral,
            "endereco": c.endereco,
            "municipio": c.municipio_ibge,
            "segmento": c.segmento,
            "site": c.site,
            "sinais": json.dumps(c.sinais, ensure_ascii=False),
        },
    ).fetchone()
    assert linha is not None
    empresa_id = linha["id"]

    for contato in c.contatos:
        conn.execute(
            "INSERT INTO contatos (empresa_id, tipo, valor, nome, fonte) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (empresa_id, tipo, valor) DO NOTHING",
            (empresa_id, contato.tipo, contato.valor, contato.nome, contato.fonte),
        )
    for ev in c.evidencias:
        conn.execute(
            "INSERT INTO evidencias (empresa_id, campo, valor, fonte, url, coletado_em) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (empresa_id, ev.campo, ev.valor, ev.fonte, ev.url, ev.coletado_em),
        )
    conn.execute(
        "INSERT INTO candidatos (campanha_id, empresa_id, job_id) VALUES (%s, %s, %s)",
        (campanha_id, empresa_id, job_id),
    )
    return "gravada"


# --- leitura de candidatos ---------------------------------------------------------------


def listar_candidatos(
    conn: Conexao,
    campanha_id: uuid.UUID,
    status: str | None,
    limite: int,
    deslocamento: int,
    tier: str | None = None,
    segmento: str | None = None,
) -> PaginaDeCandidatos:
    filtro = {"campanha": campanha_id, "status": status, "tier": tier, "segmento": segmento}
    filtros_sql = (
        "c.campanha_id = %(campanha)s AND (%(status)s::text IS NULL OR c.status = %(status)s) "
        "AND (%(tier)s::text IS NULL OR coalesce(c.tier_final, c.tier_sugerido) = %(tier)s) "
        "AND (%(segmento)s::text IS NULL OR e.segmento = %(segmento)s)"
    )
    total = conn.execute(
        f"SELECT count(*) AS n FROM candidatos c JOIN empresas e ON e.id = c.empresa_id "
        f"WHERE {filtros_sql}",
        filtro,
    ).fetchone()
    linhas = conn.execute(
        f"SELECT {_COLUNAS_CANDIDATO}, {_EMPRESA_JSON} AS empresa "
        "FROM candidatos c JOIN empresas e ON e.id = c.empresa_id "
        f"WHERE {filtros_sql} "
        "ORDER BY c.nota_total DESC NULLS LAST, c.criado_em, e.razao_social "
        "LIMIT %(limite)s OFFSET %(desloc)s",
        {**filtro, "limite": limite, "desloc": deslocamento},
    ).fetchall()
    assert total is not None
    return PaginaDeCandidatos(
        itens=[CandidatoResumo.model_validate(linha) for linha in linhas],
        total=int(total["n"]),
    )


def buscar_candidato(conn: Conexao, candidato_id: uuid.UUID) -> CandidatoDetalhe | None:
    linha = conn.execute(
        f"SELECT {_COLUNAS_CANDIDATO}, {_EMPRESA_JSON} AS empresa, "
        "e.endereco, e.sinais, e.id AS empresa_id, c.nota_aderencia, c.nota_potencial, "
        "c.nota_geografia, c.nota_dados, c.justificativas, c.lacunas, c.confianca, "
        "c.motivo_revisao, c.modelo, c.versao_prompt, c.versao_regras "
        "FROM candidatos c JOIN empresas e ON e.id = c.empresa_id WHERE c.id = %s",
        (candidato_id,),
    ).fetchone()
    if linha is None:
        return None
    contatos = conn.execute(
        "SELECT tipo, valor, nome, fonte, status_validacao FROM contatos WHERE empresa_id = %s "
        "ORDER BY tipo, valor",
        (linha["empresa_id"],),
    ).fetchall()
    evidencias = conn.execute(
        "SELECT campo, valor, fonte, url, coletado_em FROM evidencias WHERE empresa_id = %s "
        "ORDER BY coletado_em, campo",
        (linha["empresa_id"],),
    ).fetchall()
    dados: dict[str, Any] = {**linha, "contatos": contatos, "evidencias": evidencias}
    return CandidatoDetalhe.model_validate(dados)
