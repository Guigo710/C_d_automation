"""Chaves de API das organizações, cifradas pela aplicação (ticket 05, ADR 0001).

A chave inteira só existe em memória: no banco fica cifrada e pela API só volta o final.
Os agentes obtêm a chave da organização por `obter_chave`.
"""

from __future__ import annotations

from typing import Literal

from cryptography.fernet import Fernet, InvalidToken

from app.core.db import Conexao

Fornecedor = Literal["anthropic", "google_places", "brave"]
FORNECEDORES: tuple[Fornecedor, ...] = ("anthropic", "google_places", "brave")


class CifragemIndisponivel(Exception):
    """CHAVE_CIFRAGEM não foi configurada."""


class Cofre:
    def __init__(self, chave_cifragem: str | None) -> None:
        self._fernet = Fernet(chave_cifragem.encode()) if chave_cifragem else None

    def _exigir(self) -> Fernet:
        if self._fernet is None:
            raise CifragemIndisponivel
        return self._fernet

    def cifrar(self, texto: str) -> bytes:
        return self._exigir().encrypt(texto.encode())

    def decifrar(self, dados: bytes) -> str:
        try:
            return self._exigir().decrypt(bytes(dados)).decode()
        except InvalidToken as erro:
            raise CifragemIndisponivel("Chave de cifragem não confere") from erro


def final_da_chave(chave: str) -> str:
    return chave[-4:] if len(chave) > 8 else "****"


def salvar_chave(conn: Conexao, cofre: Cofre, fornecedor: Fornecedor, chave: str) -> None:
    conn.execute(
        "INSERT INTO chaves_api (fornecedor, chave_cifrada, final) VALUES (%s, %s, %s) "
        "ON CONFLICT (organizacao_id, fornecedor) DO UPDATE SET "
        "chave_cifrada = EXCLUDED.chave_cifrada, final = EXCLUDED.final, "
        "atualizada_por = app.usuario_atual(), atualizada_em = now()",
        (fornecedor, cofre.cifrar(chave), final_da_chave(chave)),
    )


def remover_chave(conn: Conexao, fornecedor: Fornecedor) -> bool:
    return conn.execute("DELETE FROM chaves_api WHERE fornecedor = %s", (fornecedor,)).rowcount > 0


def obter_chave(conn: Conexao, cofre: Cofre, fornecedor: Fornecedor) -> str | None:
    """A chave da organização da transação, decifrada, ou None se não houver."""
    linha = conn.execute(
        "SELECT chave_cifrada FROM chaves_api WHERE fornecedor = %s", (fornecedor,)
    ).fetchone()
    return cofre.decifrar(linha["chave_cifrada"]) if linha else None
