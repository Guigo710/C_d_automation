"""Triagem: o coordenador decide quais candidatos seguem (ticket 08)."""

from __future__ import annotations

import uuid

from app.auditoria import servico as auditoria
from app.auth.contexto import Contexto
from app.triagem.esquemas import AprovacaoOut


class NaoEncontrado(Exception):
    pass


class EstadoInvalido(Exception):
    pass


def aprovar(contexto: Contexto, campanha_id: uuid.UUID, ids: list[uuid.UUID]) -> AprovacaoOut:
    """Aprova em lote os candidatos pendentes da campanha; os demais ids são ignorados."""
    linhas = contexto.conn.execute(
        "UPDATE candidatos SET status = 'aprovado', decidido_por = %(u)s, decidido_em = now() "
        "WHERE campanha_id = %(c)s AND id = ANY(%(ids)s) AND status = 'pendente' RETURNING id",
        {"u": contexto.usuario.id, "c": campanha_id, "ids": ids},
    ).fetchall()
    aprovados = [linha["id"] for linha in linhas]
    if aprovados:
        auditoria.registrar(
            contexto,
            "candidatos.aprovados",
            "campanha",
            campanha_id,
            {"candidatos": [str(i) for i in aprovados]},
        )
    restantes = [i for i in dict.fromkeys(ids) if i not in set(aprovados)]
    return AprovacaoOut(aprovados=aprovados, ignorados=restantes)


def _status(contexto: Contexto, candidato_id: uuid.UUID) -> dict[str, object]:
    linha = contexto.conn.execute(
        "SELECT status, recusa_sugerida FROM candidatos WHERE id = %s FOR UPDATE", (candidato_id,)
    ).fetchone()
    if linha is None:
        raise NaoEncontrado
    return linha


def recusar(contexto: Contexto, candidato_id: uuid.UUID, motivo: str) -> None:
    atual = _status(contexto, candidato_id)
    if atual["status"] not in ("pendente", "recusado", "coletado"):
        raise EstadoInvalido("Só candidatos ainda não aprovados podem ser recusados")
    contexto.conn.execute(
        "UPDATE candidatos SET status = 'recusado', motivo_recusa = %s, recusa_sugerida = false, "
        "decidido_por = %s, decidido_em = now() WHERE id = %s",
        (motivo, contexto.usuario.id, candidato_id),
    )
    auditoria.registrar(
        contexto, "candidato.recusado", "candidato", candidato_id, {"motivo": motivo}
    )


def restaurar(contexto: Contexto, candidato_id: uuid.UUID) -> None:
    atual = _status(contexto, candidato_id)
    if atual["status"] != "recusado" or not atual["recusa_sugerida"]:
        raise EstadoInvalido("Só recusas sugeridas por regra podem ser restauradas")
    contexto.conn.execute(
        "UPDATE candidatos SET status = 'pendente', motivo_recusa = NULL, recusa_sugerida = false, "
        "decidido_por = %s, decidido_em = now() WHERE id = %s",
        (contexto.usuario.id, candidato_id),
    )
    auditoria.registrar(contexto, "candidato.restaurado", "candidato", candidato_id)


def trocar_tier(contexto: Contexto, candidato_id: uuid.UUID, tier: str, justificativa: str) -> None:
    atual = _status(contexto, candidato_id)
    if atual["status"] not in ("pendente", "aprovado"):
        raise EstadoInvalido("O tier só muda em candidatos pendentes ou aprovados")
    contexto.conn.execute(
        "UPDATE candidatos SET tier_final = %s, justificativa_tier = %s, decidido_por = %s, "
        "decidido_em = now() WHERE id = %s",
        (tier, justificativa, contexto.usuario.id, candidato_id),
    )
    auditoria.registrar(
        contexto, "candidato.tier_alterado", "candidato", candidato_id,
        {"tier": tier, "justificativa": justificativa},
    )  # fmt: skip
