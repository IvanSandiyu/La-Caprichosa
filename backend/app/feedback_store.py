from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import TURSO_TOKEN, TURSO_URL
from .db import get_conn

_FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS players_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue TEXT NOT NULL,
    player_id INTEGER,
    player_name TEXT NOT NULL,
    game TEXT,
    message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
)
"""

_COLS = ["id", "issue", "player_id", "player_name", "game", "message", "created_at"]


def _remote() -> bool:
    """Con TURSO_URL+TURSO_TOKEN configurados, los reportes van a Turso; si no,
    caen en la base SQLite local de siempre."""
    return bool(TURSO_URL and TURSO_TOKEN)


def _http_url() -> str:
    url = (TURSO_URL or "").strip()
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://") :]
    return url.rstrip("/")


# --- tipos del protocolo Hrana v2 (SQL sobre HTTP) ---

def _py_to_value(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "real", "value": str(v)}
    return {"type": "text", "value": str(v)}


def _value_to_py(v):
    if v is None:
        return None
    if not isinstance(v, dict):
        return v
    t = v.get("type")
    val = v.get("value")
    if t == "integer":
        return int(val)
    if t == "real":
        return float(val)
    if t in ("null",) or val is None:
        return None
    return val


def _turso_query(sql: str, args: list | None = None) -> list[list]:
    """Ejecuta una sentencia vía la HTTP API de Turso (/v2/pipeline)."""
    stmt: dict = {"sql": sql}
    if args:
        stmt["args"] = [_py_to_value(a) for a in args]
    payload = json.dumps({"requests": [{"type": "execute", "stmt": stmt}]}).encode("utf-8")
    req = urllib.request.Request(
        f"{_http_url()}/v2/pipeline",
        data=payload,
        headers={
            "Authorization": f"Bearer {TURSO_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Turso HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Turso inaccesible: {e.reason}") from e

    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"Turso sin respuesta: {data}")
    first = results[0]
    if first.get("type") == "error":
        err = first.get("error") or {}
        raise RuntimeError(f"Turso: {err.get('message') or err.get('code') or first}")
    if first.get("type") == "ok":
        response = first.get("response") or {}
        if response.get("type") == "execute":
            result = response.get("result") or {}
            return [
                [_value_to_py(cell) for cell in row]
                for row in (result.get("rows") or [])
            ]
        if response.get("type") == "error":
            err = response.get("error") or {}
            raise RuntimeError(f"Turso: {err.get('message') or err.get('code') or response}")
    raise RuntimeError(f"Turso: respuesta inesperada {first}")


def ensure_feedback_table(remote: bool | None = None) -> None:
    remote = _remote() if remote is None else remote
    if remote:
        _turso_query(_FEEDBACK_DDL)
    else:
        conn = get_conn()
        conn.execute(_FEEDBACK_DDL)
        conn.commit()


def add_feedback(
    issue: str,
    player_id: int | None,
    player_name: str,
    game: str | None,
    message: str,
    remote: bool | None = None,
) -> int:
    remote = _remote() if remote is None else remote
    args = [issue, player_id, player_name, game, message]
    if remote:
        rows = _turso_query(
            "INSERT INTO players_feedback (issue, player_id, player_name, game, message) "
            "VALUES (?, ?, ?, ?, ?) RETURNING id",
            args,
        )
        if not rows:
            raise RuntimeError("Turso no devolvió el id insertado")
        return int(rows[0][0])
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO players_feedback (issue, player_id, player_name, game, message) "
        "VALUES (?, ?, ?, ?, ?)",
        args,
    )
    conn.commit()
    return int(cur.lastrowid)


def list_feedback(limit: int = 500, remote: bool | None = None) -> list[dict]:
    remote = _remote() if remote is None else remote
    capped = min(limit, 1000)
    if remote:
        rows = _turso_query(
            "SELECT id, issue, player_id, player_name, game, message, created_at "
            "FROM players_feedback ORDER BY id DESC LIMIT ?",
            [capped],
        )
        return [dict(zip(_COLS, r)) for r in rows]
    conn = get_conn()
    return [
        dict(r)
        for r in conn.execute(
            "SELECT id, issue, player_id, player_name, game, message, created_at "
            "FROM players_feedback ORDER BY id DESC LIMIT ?",
            (capped,),
        ).fetchall()
    ]