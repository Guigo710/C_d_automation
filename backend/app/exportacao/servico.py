"""Exportação dos aprovados de uma campanha para Excel (ticket 13).

Só o coordenador exporta, e cada exportação fica na auditoria. Na v0 o arquivo é gerado
sob demanda e baixado direto (sem bucket). Contatos não vão para a planilha: uma lista
exportada sai da empresa junto com quem sai da empresa.
"""

from __future__ import annotations

import io
import uuid

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from app.auditoria import servico as auditoria
from app.auth.contexto import Contexto
from app.campanhas import repositorio as campanhas


class NaoEncontrado(Exception):
    pass


COLUNAS = [
    ("Empresa", "nome"),
    ("Razão social", "razao_social"),
    ("CNPJ", "cnpj"),
    ("Segmento", "segmento"),
    ("Município (IBGE)", "municipio_ibge"),
    ("Endereço", "endereco"),
    ("Site", "site"),
    ("Tier", "tier"),
    ("Nota total", "nota_total"),
    ("Aderência", "nota_aderencia"),
    ("Potencial", "nota_potencial"),
    ("Geografia", "nota_geografia"),
    ("Dados", "nota_dados"),
]


def exportar_aprovados(contexto: Contexto, campanha_id: uuid.UUID) -> tuple[str, bytes]:
    campanha = campanhas.buscar(contexto.conn, campanha_id)
    if campanha is None:
        raise NaoEncontrado
    linhas = contexto.conn.execute(
        "SELECT coalesce(e.nome_fantasia, e.razao_social) AS nome, e.razao_social, "
        "e.cnpj::text AS cnpj, e.segmento, e.municipio_ibge::text AS municipio_ibge, e.endereco, "
        "e.site, coalesce(c.tier_final, c.tier_sugerido) AS tier, c.nota_total, c.nota_aderencia, "
        "c.nota_potencial, c.nota_geografia, c.nota_dados "
        "FROM candidatos c JOIN empresas e ON e.id = c.empresa_id "
        "WHERE c.campanha_id = %s AND c.status = 'aprovado' "
        "ORDER BY coalesce(c.tier_final, c.tier_sugerido), c.nota_total DESC NULLS LAST, nome",
        (campanha_id,),
    ).fetchall()

    planilha = Workbook()
    aba = planilha.active
    aba.title = "Aprovados"
    aba.append([titulo for titulo, _ in COLUNAS])
    for linha in linhas:
        aba.append([linha[campo] for _, campo in COLUNAS])
    for indice, (titulo, _) in enumerate(COLUNAS, start=1):
        aba.column_dimensions[get_column_letter(indice)].width = max(12, len(titulo) + 4)
    aba.freeze_panes = "A2"
    buffer = io.BytesIO()
    planilha.save(buffer)

    auditoria.registrar(
        contexto, "exportacao.aprovados", "campanha", campanha_id, {"linhas": len(linhas)}
    )
    nome = f"aprovados-{campanha.nome[:40].strip().replace(' ', '-').lower()}.xlsx"
    return nome, buffer.getvalue()
