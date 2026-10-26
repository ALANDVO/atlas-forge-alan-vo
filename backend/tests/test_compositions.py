"""Tests for compositions API."""

import os
import pytest
from fastapi.testclient import TestClient

# Set test database environment variable BEFORE importing app
TEST_DB = "test_atlas_forge.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["ATLAS_FORGE_DB_PATH"] = TEST_DB

from app.main import app
from app.core.database import init_db, get_settings

# Initialize database before tests
init_db(get_settings().db_path)

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def _create_test_composition():
    """Helper to create a test composition."""
    payload = {
        "title": "Test Composition",
        "entry_path": "index.html",
        "scaffold_root_path": "index.html",
        "html_source": "<html><body><video id='v1' data-start='0' data-duration='10'></video></body></html>",
        "composition_attr_id": "composition",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "duration_sec": 10.0,
        "total_frames": 300,
        "readiness_score": 0,
    }
    response = client.post("/api/v1/compositions", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Composition"
    assert data["status"] == "ready"
    assert "id" in data
    return data["id"]


def test_create_composition():
    _create_test_composition()


def test_list_compositions():
    _create_test_composition()
    response = client.get("/api/v1/compositions")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


def test_get_composition():
    comp_id = _create_test_composition()
    response = client.get(f"/api/v1/compositions/{comp_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == comp_id
    assert data["title"] == "Test Composition"
    assert "clips" in data
    assert "audit_events" in data
    assert "diagnostics" in data


def test_diagnostics():
    comp_id = _create_test_composition()
    response = client.get(f"/api/v1/diagnostics/{comp_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["composition_id"] == comp_id
    assert "readiness_score" in data
    assert "issues" in data
    assert "peak_concurrency_windows" in data


def test_delete_composition():
    comp_id = _create_test_composition()
    response = client.delete(f"/api/v1/compositions/{comp_id}")
    assert response.status_code == 204
    response = client.get(f"/api/v1/compositions/{comp_id}")
    assert response.status_code == 404
