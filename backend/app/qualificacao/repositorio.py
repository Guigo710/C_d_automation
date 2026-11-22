from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from app.core.db import Conexao
from app.prospeccao.repositorio import gasto_da_campanha, saldo_mensal_da_organizacao
from app.qualificacao.regras import Bloqueios, Regras, StatusContato, so_digitos


@dataclass(frozen=True)
class RegrasVigentes:
    versao: int
    perfil_ideal: str
    regras: Regras


@dataclass(frozen=True)
class ContextoDaCampanha:
    municipios: list[str]
    com_rota: frozenset[str]
    atendidos: frozenset[str]
    clientes_atuais: frozenset[str]
    bloqueios: Bloqueios


def regras_vigentes(conn: Conexao) -> RegrasVigentes | None:
    linha = conn.execute(
        "SELECT versao, perfil_ideal, pesos, cortes FROM configuracoes_organizacao "
        "ORDER BY versao DESC LIMIT 1"
    ).fetchone()
    if linha is None:
        return None
    return RegrasVigentes(
        versao=linha["versao"],
        perfil_ideal=linha["perfil_ideal"],
        regras=Regras(pesos=dict(linha["pesos"]), cortes=dict(linha["cortes"])),
    )


def contexto_da_campanha(conn: Conexao, campanha_id: uuid.UUID) -> ContextoDaCampanha | None:
    campanha = conn.execute(
        "SELECT municipios_ibge::text[] AS municipios FROM campanhas WHERE id = %s", (campanha_id,)
    ).fetchone()
    if campanha is None:
        return None
    municipios = conn.execute(
        "SELECT municipio_ibge::text AS m, tem_rota FROM municipios_atendidos"
    ).fetchall()
    clientes = conn.execute("SELECT cnpj::text AS cnpj FROM clientes_atuais").fetchall()
    bloqueios = conn.execute("SELECT tipo, lower(valor) AS valor FROM lista_bloqueio").fetchall()

    def de(tipo: str) -> frozenset[str]:
        valores = (b["valor"] for b in bloqueios if b["tipo"] == tipo)
        return frozenset(so_digitos(v) if tipo == "telefone" else v for v in valores)

    return ContextoDaCampanha(
        municipios=list(campanha["municipios"]),
        com_rota=frozenset(m["m"] for m in municipios if m["tem_rota"]),
        atendidos=frozenset(m["m"] for m in municipios),
        clientes_atuais=frozenset(c["cnpj"] for c in clientes),
        bloqueios=Bloqueios(
            cnpjs=frozenset(v.upper() for v in de("cnpj")),
            emails=de("email"),
            telefones=de("telefone"),
            dominios=de("dominio"),
        ),
    )


def proximos_coletados(conn: Conexao, campanha_id: uuid.UUID, limite: int) -> list[dict[str, Any]]:
    """Candidatos ainda não qualificados, com empresa, contatos e evidências."""
    candidatos = conn.execute(
        "SELECT c.id, e.id AS empresa_id, e.cnpj::text AS cnpj, e.razao_social, e.nome_fantasia, "
        "e.situacao_cadastral, e.municipio_ibge::text AS municipio_ibge, e.segmento, e.site, "
        "e.endereco, e.sinais FROM candidatos c JOIN empresas e ON e.id = c.empresa_id "
        "WHERE c.campanha_id = %s AND c.status = 'coletado' ORDER BY c.criado_em LIMIT %s",
        (campanha_id, limite),
    ).fetchall()
    for candidato in candidatos:
        candidato["contatos"] = conn.execute(
            "SELECT id, tipo, valor FROM contatos WHERE empresa_id = %s ORDER BY tipo, valor",
            (candidato["empresa_id"],),
        ).fetchall()
        candidato["evidencias"] = conn.execute(
            "SELECT campo, valor, fonte, coletado_em FROM evidencias WHERE empresa_id = %s "
            "ORDER BY coletado_em, campo",
            (candidato["empresa_id"],),
        ).fetchall()
    return candidatos


def mesma_raiz_em_uso(
    conn: Conexao, campanha_id: uuid.UUID, empresa_id: uuid.UUID, cnpj: str
) -> bool:
    """Outro estabelecimento do mesmo CNPJ básico (8 primeiros caracteres) nesta campanha ou
    em outra campanha ativa."""
    linha = conn.execute(
        "SELECT 1 FROM candidatos ca JOIN empresas e ON e.id = ca.empresa_id "
        "JOIN campanhas cp ON cp.id = ca.campanha_id "
        "WHERE left(e.cnpj, 8) = left(%s, 8) AND e.id <> %s "
        "AND (ca.campanha_id = %s OR cp.status = 'ativa') LIMIT 1",
        (cnpj, empresa_id, campanha_id),
    ).fetchone()
    return linha is not None


def saldo(conn: Conexao, campanha_id: uuid.UUID) -> Decimal:
    teto = conn.execute(
        "SELECT teto_gasto_usd FROM campanhas WHERE id = %s", (campanha_id,)
    ).fetchone()
    assert teto is not None
    saldo_campanha: Decimal = teto["teto_gasto_usd"] - gasto_da_campanha(conn, campanha_id)
    return min(saldo_campanha, saldo_mensal_da_organizacao(conn))


def marcar_contatos(conn: Conexao, status: dict[uuid.UUID, StatusContato]) -> None:
    for contato_id, valor in status.items():
        conn.execute("UPDATE contatos SET status_validacao = %s WHERE id = %s", (valor, contato_id))


def gravar_recusa_sugerida(
    conn: Conexao, candidato_id: uuid.UUID, motivo: str, versao_regras: int, **notas: Any
) -> None:
    conn.execute(
        "UPDATE candidatos SET status = 'recusado', recusa_sugerida = true, motivo_recusa = %s, "
        "versao_regras = %s, qualificado_em = now(), "
        "nota_aderencia = %s, nota_potencial = %s, nota_geografia = %s, nota_dados = %s, "
        "nota_total = %s WHERE id = %s",
        (
            motivo,
            versao_regras,
            notas.get("aderencia"),
            notas.get("potencial"),
            notas.get("geografia"),
            notas.get("dados"),
            notas.get("total"),
            candidato_id,
        ),
    )


def gravar_qualificacao(
    conn: Conexao,
    candidato_id: uuid.UUID,
    *,
    notas: dict[str, int],
    tier: str,
    resposta: dict[str, Any],
    modelo: str,
    versao_prompt: str,
    versao_regras: int,
    baixa_confianca: bool,
) -> None:
    conn.execute(
        "UPDATE candidatos SET status = 'pendente', nota_aderencia = %(aderencia)s, "
        "nota_potencial = %(potencial)s, nota_geografia = %(geografia)s, nota_dados = %(dados)s, "
        "nota_total = %(total)s, tier_sugerido = %(tier)s, justificativas = %(justificativas)s, "
        "lacunas = %(lacunas)s, confianca = %(confianca)s, baixa_confianca = %(baixa)s, "
        "modelo = %(modelo)s, versao_prompt = %(prompt)s, versao_regras = %(regras)s, "
        "qualificado_em = now() WHERE id = %(id)s",
        {
            **notas,
            "tier": tier,
            "justificativas": json.dumps(
                {
                    "aderencia": resposta["justificativa_aderencia"],
                    "potencial": resposta["justificativa_potencial"],
                    "evidencias_citadas": resposta["evidencias_citadas"],
                },
                ensure_ascii=False,
            ),
            "lacunas": resposta["lacunas"],
            "confianca": resposta["confianca"],
            "baixa": baixa_confianca,
            "modelo": modelo,
            "prompt": versao_prompt,
            "regras": versao_regras,
            "id": candidato_id,
        },
    )


def gravar_revisao(
    conn: Conexao,
    candidato_id: uuid.UUID,
    motivo: str,
    geografia: int,
    dados: int,
    versao_prompt: str,
    versao_regras: int,
) -> None:
    conn.execute(
        "UPDATE candidatos SET status = 'pendente', em_revisao = true, motivo_revisao = %s, "
        "nota_geografia = %s, nota_dados = %s, versao_prompt = %s, versao_regras = %s, "
        "qualificado_em = now() WHERE id = %s",
        (motivo[:500], geografia, dados, versao_prompt, versao_regras, candidato_id),
    )


def ler_cache(conn: Conexao, chave: str) -> dict[str, Any] | None:
    linha = conn.execute("SELECT resposta FROM llm_cache WHERE hash = %s", (chave,)).fetchone()
    return dict(linha["resposta"]) if linha else None


def gravar_cache(conn: Conexao, chave: str, modelo: str, resposta: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO llm_cache (hash, modelo, resposta) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (chave, modelo, json.dumps(resposta, ensure_ascii=False)),
    )


def registrar_progresso(
    conn: Conexao,
    job_id: uuid.UUID,
    resultado: Literal["qualificada", "recusada", "revisao"],
    custo: Decimal,
) -> None:
    """Em jobs de qualificação: encontradas = processadas, gravadas = qualificadas,
    duplicadas = recusadas por regra."""
    conn.execute(
        "UPDATE jobs SET encontradas = encontradas + 1, gravadas = gravadas + %(q)s, "
        "duplicadas = duplicadas + %(r)s, custo_usd = custo_usd + %(custo)s, "
        "ultima_atividade = now() WHERE id = %(id)s",
        {
            "q": 1 if resultado == "qualificada" else 0,
            "r": 1 if resultado == "recusada" else 0,
            "custo": custo,
            "id": job_id,
        },
    )


def enfileirar_se_nao_houver(conn: Conexao, tipo: str, campanha_id: uuid.UUID) -> None:
    conn.execute(
        "INSERT INTO jobs (tipo, campanha_id) SELECT %(tipo)s, %(c)s WHERE NOT EXISTS ("
        "SELECT 1 FROM jobs WHERE tipo = %(tipo)s AND campanha_id = %(c)s "
        "AND status IN ('na_fila', 'executando'))",
        {"tipo": tipo, "c": campanha_id},
    )
