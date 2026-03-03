"""Testes de smoke do endpoint de health-check e das rotas principais."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Retorna um TestClient reutilizável para todos os testes do módulo."""
    with TestClient(app) as c:
        yield c


def test_health_ok(client: TestClient) -> None:
    """GET /api/health deve retornar 200 e status 'ok'."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "version" in data


def test_openapi_docs(client: TestClient) -> None:
    """GET /api/docs deve responder com 200."""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_hardware_snapshot(client: TestClient) -> None:
    """GET /api/hardware/snapshot deve retornar dados de hardware."""
    response = client.get("/api/hardware/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data


def test_fans_list(client: TestClient) -> None:
    """GET /api/fans/ deve retornar uma lista (pode estar vazia)."""
    response = client.get("/api/fans/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_profiles_list(client: TestClient) -> None:
    """GET /api/profiles/ deve retornar uma lista de perfis."""
    response = client.get("/api/profiles/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
