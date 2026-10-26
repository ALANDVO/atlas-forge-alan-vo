"""Tests for clips API."""

import os
import uuid
from fastapi.testclient import TestClient

# Set test database environment variable BEFORE importing app
TEST_DB = "test_atlas_forge.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["ATLAS_FORGE_DB_PATH"] = TEST_DB

from app.main import app
from app.core.database import init_db, get_settings

init_db(get_settings().db_path)

client = TestClient(app)


def _create_test_composition():
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
    return response.json()["id"]


def test_create_clip():
    comp_id = _create_test_composition()
    clip_id = str(uuid.uuid4())
    payload = {
        "id": clip_id,
        "composition_id": comp_id,
        "element_id": "v1",
        "tag_name": "video",
        "track_index": 0,
        "start_sec": 0.0,
        "duration_sec": 10.0,
        "label": "Main Video",
        "x_offset": 0.0,
        "y_offset": 0.0,
        "scale": 1.0,
        "opacity": 1.0,
        "color_grading": "",
        "src_path": "video.mp4",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    response = client.post("/api/v1/clips", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == clip_id
    assert data["composition_id"] == comp_id
    assert data["label"] == "Main Video"


def test_list_clips():
    comp_id = _create_test_composition()
    clip_id = str(uuid.uuid4())
    payload = {
        "id": clip_id,
        "composition_id": comp_id,
        "element_id": "v1",
        "tag_name": "video",
        "track_index": 0,
        "start_sec": 0.0,
        "duration_sec": 10.0,
        "label": "Main Video",
        "x_offset": 0.0,
        "y_offset": 0.0,
        "scale": 1.0,
        "opacity": 1.0,
        "color_grading": "",
        "src_path": "video.mp4",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    client.post("/api/v1/clips", json=payload)
    
    response = client.get(f"/api/v1/clips?composition_id={comp_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["label"] == "Main Video"


def test_override_clip():
    comp_id = _create_test_composition()
    clip_id = str(uuid.uuid4())
    payload = {
        "id": clip_id,
        "composition_id": comp_id,
        "element_id": "v1",
        "tag_name": "video",
        "track_index": 0,
        "start_sec": 0.0,
        "duration_sec": 10.0,
        "label": "Main Video",
        "x_offset": 0.0,
        "y_offset": 0.0,
        "scale": 1.0,
        "opacity": 1.0,
        "color_grading": "",
        "src_path": "video.mp4",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    client.post("/api/v1/clips", json=payload)
    
    # Override the clip
    override = {
        "label": "Updated Video",
        "scale": 1.5,
        "opacity": 0.8,
    }
    response = client.patch(f"/api/v1/clips/{clip_id}", json=override)
    assert response.status_code == 200
    data = response.json()
    assert data["clip"]["label"] == "Updated Video"
    assert data["clip"]["scale"] == 1.5
    assert data["clip"]["opacity"] == 0.8
    assert "label" in data["applied_fields"]
    assert "scale" in data["applied_fields"]
    assert "opacity" in data["applied_fields"]


def test_delete_clip():
    comp_id = _create_test_composition()
    clip_id = str(uuid.uuid4())
    payload = {
        "id": clip_id,
        "composition_id": comp_id,
        "element_id": "v1",
        "tag_name": "video",
        "track_index": 0,
        "start_sec": 0.0,
        "duration_sec": 10.0,
        "label": "Main Video",
        "x_offset": 0.0,
        "y_offset": 0.0,
        "scale": 1.0,
        "opacity": 1.0,
        "color_grading": "",
        "src_path": "video.mp4",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    client.post("/api/v1/clips", json=payload)
    
    response = client.delete(f"/api/v1/clips/{clip_id}")
    assert response.status_code == 204
    
    # Verify deleted
    response = client.get(f"/api/v1/clips?composition_id={comp_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
