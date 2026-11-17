import os
import secrets

from flask import Flask, abort, jsonify, redirect, request
from psycopg_pool import ConnectionPool

app = Flask(__name__)
pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=2, max_size=10)

with pool.connection() as conn:
    conn.execute("SELECT pg_advisory_xact_lock(1)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS links (
            code TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            clicks BIGINT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

@app.get("/health")
def health():
    return "ok"

@app.post("/links")
def create():
    url = (request.get_json(silent=True) or {}).get("url", "")
    if not url.startswith(("http://", "https://")):
        abort(400)
    code = secrets.token_urlsafe(5)
    with pool.connection() as conn:
        conn.execute("INSERT INTO links (code, url) VALUES (%s, %s)", (code, url))
    return jsonify(code=code), 201

@app.get("/<code>")
def go(code):
    with pool.connection() as conn:
        row = conn.execute(
            "UPDATE links SET clicks = clicks + 1 WHERE code = %s RETURNING url",
            (code,),
        ).fetchone()
    if not row:
        abort(404)
    return redirect(row[0], 302)
