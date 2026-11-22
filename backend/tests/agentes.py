"""Agentes de prospecção usados só nos testes."""

from __future__ import annotations

from collections.abc import Iterator

from app.prospeccao.agente import CandidatoProspectado, FotoDaCampanha
from app.prospeccao.agente_falso import AgenteFalso


class Interrompido(BaseException):
    """Simula o processo morrendo no meio (não é capturado pela fila, como uma queda)."""


class AgenteQueCaiNoTerceiro:
    def executar(self, campanha: FotoDaCampanha) -> Iterator[CandidatoProspectado]:
        for i, candidato in enumerate(AgenteFalso().executar(campanha)):
            if i == 2:
                raise Interrompido
            yield candidato
