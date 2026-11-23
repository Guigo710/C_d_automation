"""O login de demonstração não pode existir fora do modo demo nem atender quem não é local."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import Dados


def test_sem_modo_demo_as_rotas_de_demo_nao_existem(client: TestClient, dados: Dados) -> None:
    assert client.get("/demo/usuarios").status_code == 404
    login = client.post("/demo/login", json={"usuario_id": str(dados.a.coordenador.id)})
    assert login.status_code == 404


def test_modo_demo_recusa_quem_nao_esta_em_localhost(settings: Settings, dados: Dados) -> None:
    com_demo = settings.model_copy(update={"demo_local": True})
    # O TestClient se apresenta como o host "testclient", que não é local.
    with TestClient(create_app(com_demo)) as remoto:
        assert remoto.get("/demo/usuarios").status_code == 404
        login = remoto.post("/demo/login", json={"usuario_id": str(dados.a.coordenador.id)})
        assert login.status_code == 404
