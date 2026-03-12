"""Testes de integração da API v1 – smoke tests e validação de contratos."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Retorna um TestClient reutilizável para todos os testes do módulo."""
    with TestClient(app) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_ok(client: TestClient) -> None:
    """GET /api/v1/health deve retornar 200 e status 'ok'."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["success"] is True
    assert "uptime_seconds" in data
    assert "version" in data
    assert "timestamp" in data
    assert "os" in data


def test_health_backward_compat(client: TestClient) -> None:
    """GET /api/health (alias legado) deve continuar funcionando para Docker HEALTHCHECK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_docs(client: TestClient) -> None:
    """GET /api/docs deve responder com 200."""
    response = client.get("/api/docs")
    assert response.status_code == 200


# ── Hardware ──────────────────────────────────────────────────────────────────

def test_hardware_snapshot(client: TestClient) -> None:
    """GET /api/v1/hardware/snapshot deve retornar estrutura de hardware válida."""
    response = client.get("/api/v1/hardware/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "disks" in data
    assert "gpus" in data
    assert "temperatures" in data
    assert "timestamp" in data


def test_hardware_history_default(client: TestClient) -> None:
    """GET /api/v1/hardware/history deve retornar lista (pode estar vazia inicialmente)."""
    response = client.get("/api/v1/hardware/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_hardware_history_limit(client: TestClient) -> None:
    """GET /api/v1/hardware/history?limit=5 deve retornar no máximo 5 entradas."""
    response = client.get("/api/v1/hardware/history?limit=5")
    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_hardware_history_limit_validation(client: TestClient) -> None:
    """GET /api/v1/hardware/history?limit=0 deve retornar 422 (fora do range 1–500)."""
    response = client.get("/api/v1/hardware/history?limit=0")
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "error" in body


def test_hardware_cpu(client: TestClient) -> None:
    """GET /api/v1/hardware/cpu deve retornar estatísticas da CPU."""
    response = client.get("/api/v1/hardware/cpu")
    assert response.status_code == 200
    data = response.json()
    assert "usage_percent" in data
    assert "frequency_mhz" in data


# ── Ventoinhas ────────────────────────────────────────────────────────────────

def test_fans_list(client: TestClient) -> None:
    """GET /api/v1/fans/ deve retornar uma lista (pode estar vazia)."""
    response = client.get("/api/v1/fans/")
    assert response.status_code == 200
    fans = response.json()
    assert isinstance(fans, list)
    for fan in fans:
        assert "id" in fan
        assert "rpm" in fan
        assert "speed_mode" in fan
        assert fan["speed_mode"] in (None, "auto", "quiet", "balanced", "turbo")


def test_fan_mode_valid(client: TestClient) -> None:
    """POST /api/v1/fans/{id}/mode deve aceitar todos os modos válidos."""
    for mode in ("quiet", "balanced", "turbo", "auto"):
        resp = client.post("/api/v1/fans/test_fan_1/mode", json={"mode": mode})
        assert resp.status_code == 200, f"Modo '{mode}' deveria retornar 200: {resp.text}"
        body = resp.json()
        assert body["mode"] == mode
        assert body["fan_id"] == "test_fan_1"


def test_fan_mode_invalid(client: TestClient) -> None:
    """POST /api/v1/fans/{id}/mode com modo inválido deve retornar 422 com body padrão de erro."""
    resp = client.post("/api/v1/fans/test_fan_1/mode", json={"mode": "invalid_mode"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert "error" in body


# ── Perfis ────────────────────────────────────────────────────────────────────

def test_profiles_list(client: TestClient) -> None:
    """GET /api/v1/profiles/ deve retornar uma lista de perfis."""
    response = client.get("/api/v1/profiles/")
    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, list)
    assert len(profiles) >= 1


def test_profile_not_found(client: TestClient) -> None:
    """GET /api/v1/profiles/{id} com ID inexistente deve retornar 404 com body padrão."""
    response = client.get("/api/v1/profiles/perfil_que_nao_existe_xyzabc")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "error" in body
    assert "detail" in body


def test_active_profile(client: TestClient) -> None:
    """GET /api/v1/profiles/active deve retornar 200 ou 404 (sem perfil ativo)."""
    response = client.get("/api/v1/profiles/active")
    assert response.status_code in (200, 404)
