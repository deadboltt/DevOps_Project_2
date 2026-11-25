from unittest.mock import MagicMock, patch
import psycopg2
import pytest

import app as task_app


@pytest.fixture
def client():
    task_app._db_initialized = False
    task_app.app.config["TESTING"] = True
    with task_app.app.test_client() as test_client:
        yield test_client


def _mock_conn_with_cursor(fetchone_value=None, fetchall_value=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    cursor.fetchall.return_value = fetchall_value or []
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cursor


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["service"] == "task-api"
    assert "/healthz" in data["endpoints"]


def test_healthz_ok(client):
    conn, _ = _mock_conn_with_cursor(fetchone_value=(1,))
    with patch("app.get_db_connection", return_value=conn):
        resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok", "database": "connected"}


def test_healthz_db_down(client):
    with patch("app.get_db_connection", side_effect=psycopg2.OperationalError("db unreachable")):
        resp = client.get("/healthz")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "error"


def test_create_task_validation(client):
    resp = client.post("/tasks", json={"title": "   "})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "title is required"


def test_create_and_list_tasks(client):
    created_row = {"id": 1, "title": "Write tests", "done": False, "created_at": "2026-11-25"}
    conn, _ = _mock_conn_with_cursor(fetchone_value=created_row, fetchall_value=[created_row])
    with patch("app.get_db_connection", return_value=conn):
        post_resp = client.post("/tasks", json={"title": "Write tests"})
        list_resp = client.get("/tasks")

    assert post_resp.status_code == 201
    assert post_resp.get_json()["title"] == "Write tests"
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()) == 1


def test_metrics_endpoint(client):
    conn, _ = _mock_conn_with_cursor(fetchone_value=(3,))
    with patch("app.get_db_connection", return_value=conn):
        client.get("/")
        resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")
    assert "task_api_http_requests_total" in body
    assert "task_api_http_request_duration_seconds" in body
    assert "task_api_tasks_count 3.0" in body
