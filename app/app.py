import os
import time
from flask import Flask, jsonify, request, Response
import psycopg2
from psycopg2.extras import RealDictCursor
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUEST_COUNT = Counter(
    "task_api_http_requests_total",
    "Total HTTP requests to the Task API",
    ["method", "endpoint", "status"],
)
TASKS_GAUGE = Gauge("task_api_tasks_count", "Current number of tasks in PostgreSQL")


def get_db_connection():
    """Create a PostgreSQL connection from environment configuration."""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "task-db"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "tasks"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        connect_timeout=5,
    )


_db_initialized = False


def ensure_db():
    """Ensure the tasks table exists using a PostgreSQL advisory lock."""
    global _db_initialized
    if _db_initialized:
        return
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(424242)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("SELECT pg_advisory_unlock(424242)")
        conn.commit()
    _db_initialized = True


@app.after_request
def record_metrics(response):
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=str(response.status_code),
    ).inc()
    return response


@app.get("/")
def index():
    return jsonify(
        {
            "service": "task-api",
            "endpoints": ["/healthz", "/tasks", "/metrics"],
        }
    )


@app.get("/healthz")
def healthz():
    try:
        ensure_db()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as exc:
        return jsonify({"status": "error", "detail": str(exc)}), 503


@app.get("/tasks")
def list_tasks():
    ensure_db()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title, done, created_at FROM tasks ORDER BY id ASC")
            rows = cur.fetchall()
    TASKS_GAUGE.set(len(rows))
    return jsonify(rows), 200


@app.post("/tasks")
def create_task():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    ensure_db()
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO tasks (title) VALUES (%s) RETURNING id, title, done, created_at",
                (title,),
            )
            created = cur.fetchone()
        conn.commit()
    return jsonify(created), 201


@app.get("/metrics")
def metrics():
    try:
        ensure_db()
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM tasks")
                count = cur.fetchone()[0]
        TASKS_GAUGE.set(count)
    except Exception:
        pass
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
