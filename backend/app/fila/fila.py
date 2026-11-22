"""Fila de jobs numa tabela do PostgreSQL (ADR 0004).

A interface é pequena de propósito (`enfileirar`, `processar_proximo`, `drenar`, `iniciar`,
`parar`) para ser trocada por Celery no VPS sem mexer nas regras de negócio.

Um job "executando" cujo lease venceu (o processo dormiu ou caiu) volta a ser
reivindicável, e o executor do tipo retoma de onde parou: toda tarefa precisa ser
idempotente.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from app.core.db import Banco, Conexao

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Job:
    id: uuid.UUID
    organizacao_id: uuid.UUID
    tipo: str
    campanha_id: uuid.UUID | None
    criado_por: uuid.UUID | None
    tentativas: int


Executor = Callable[["Fila", Job], None]


class Fila:
    def __init__(self, banco: Banco, lease_segundos: int, intervalo_segundos: float) -> None:
        self.banco = banco
        self._lease = lease_segundos
        self._intervalo = intervalo_segundos
        self._executores: dict[str, Executor] = {}
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def registrar(self, tipo: str, executor: Executor) -> None:
        self._executores[tipo] = executor

    @staticmethod
    def enfileirar(conn: Conexao, tipo: str, campanha_id: uuid.UUID | None = None) -> uuid.UUID:
        """Cria o job na transação de quem pede (a organização vem do RLS)."""
        linha = conn.execute(
            "INSERT INTO jobs (tipo, campanha_id) VALUES (%s, %s) RETURNING id",
            (tipo, campanha_id),
        ).fetchone()
        assert linha is not None
        job_id: uuid.UUID = linha["id"]
        return job_id

    def renovar_lease(self, conn: Conexao, job_id: uuid.UUID) -> None:
        conn.execute(
            "UPDATE jobs SET lease_ate = now() + make_interval(secs => %s), "
            "ultima_atividade = now() WHERE id = %s",
            (self._lease, job_id),
        )

    def _reivindicar(self) -> Job | None:
        # Como dono das tabelas: a fila atende todas as organizações.
        with self.banco.transacao() as conn:
            linha = conn.execute(
                "UPDATE jobs SET status = 'executando', tentativas = tentativas + 1, "
                "iniciado_em = coalesce(iniciado_em, now()), ultima_atividade = now(), "
                "lease_ate = now() + make_interval(secs => %s) "
                "WHERE id = (SELECT id FROM jobs "
                "  WHERE status = 'na_fila' OR (status = 'executando' AND lease_ate < now()) "
                "  ORDER BY criado_em FOR UPDATE SKIP LOCKED LIMIT 1) "
                "RETURNING id, organizacao_id, tipo, campanha_id, criado_por, tentativas",
                (self._lease,),
            ).fetchone()
        return Job(**linha) if linha else None

    def _falhar(self, job: Job, erro: Exception) -> None:
        with self.banco.transacao() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'falhou', erro = %s, terminado_em = now(), "
                "lease_ate = NULL WHERE id = %s",
                (f"{type(erro).__name__}: {erro}"[:2000], job.id),
            )

    def processar_proximo(self) -> bool:
        """Executa um job, se houver. Devolve se havia algum."""
        job = self._reivindicar()
        if job is None:
            return False
        executor = self._executores.get(job.tipo)
        try:
            if executor is None:
                raise RuntimeError(f"Tipo de job sem executor: {job.tipo}")
            executor(self, job)
        except Exception as erro:  # o job falha, o worker continua
            log.exception("job %s falhou", job.id)
            self._falhar(job, erro)
        return True

    def drenar(self) -> int:
        """Processa todos os jobs disponíveis, de forma síncrona. Usado nos testes."""
        total = 0
        while self.processar_proximo():
            total += 1
        return total

    def iniciar(self) -> None:
        self._parar.clear()
        self._thread = threading.Thread(target=self._laco, name="worker-fila", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _laco(self) -> None:
        while not self._parar.is_set():
            try:
                if not self.processar_proximo():
                    self._parar.wait(self._intervalo)
            except Exception:  # erro de conexão etc.: espera e tenta de novo
                log.exception("erro no worker da fila")
                self._parar.wait(self._intervalo)
