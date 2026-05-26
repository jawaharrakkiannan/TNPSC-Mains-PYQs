# tests/test_review_server.py
import json
import pytest
from scripts.review_server import create_app
from tests.conftest import MINIMAL_QUESTIONS


@pytest.fixture
def app(tmp_path):
    raw = tmp_path / "questions_raw.json"
    raw.write_text(json.dumps(MINIMAL_QUESTIONS), encoding="utf-8")
    app = create_app(
        raw_path=str(raw),
        corrected_path=str(tmp_path / "corrected.json"),
    )
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"review" in r.data.lower()


def test_api_questions_returns_list(client):
    r = client.get("/api/questions")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert isinstance(data, list)
    assert data[0]["year"] == 2024


def test_api_save_writes_file(client, tmp_path):
    modified = json.loads(json.dumps(MINIMAL_QUESTIONS))
    modified[0]["english"] = "Modified English text"
    r = client.post("/api/save", json=modified)
    assert r.status_code == 200
    corrected = list(tmp_path.glob("corrected.json"))
    assert len(corrected) == 1
    saved = json.loads(corrected[0].read_text(encoding="utf-8"))
    assert saved[0]["english"] == "Modified English text"


def test_api_status_has_progress(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["total"] == 1
    assert data["reviewed"] == 0


def test_api_questions_prefers_corrected(tmp_path):
    raw = tmp_path / "questions_raw.json"
    raw.write_text(json.dumps(MINIMAL_QUESTIONS), encoding="utf-8")
    corrected_data = json.loads(json.dumps(MINIMAL_QUESTIONS))
    corrected_data[0]["english"] = "Corrected English text"
    corrected = tmp_path / "corrected.json"
    corrected.write_text(json.dumps(corrected_data), encoding="utf-8")
    app = create_app(raw_path=str(raw), corrected_path=str(corrected))
    app.config["TESTING"] = True
    r = app.test_client().get("/api/questions")
    data = json.loads(r.data)
    assert data[0]["english"] == "Corrected English text"
