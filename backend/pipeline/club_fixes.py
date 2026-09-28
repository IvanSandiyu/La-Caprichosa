"""Aplica `club_fixes.json` (feedback curado de usuarios) sobre la BDD.

Cada feedback "clubes incompletos" produce una entrada durable en
`club_fixes.json`:

    [{
      "player_id": -100910,
      "name": "Juan Román Riquelme",
      "club_fixes": [{"club_id": 1030, "name": "Argentinos Juniors"}],
      "reason": "feedback 22/9: jugó en Argentinos Juniors y en la selección"
    }]

`club_fixes` son clubes que YA están en la tabla `clubs` (el jugador debe
haberlos tenido); solo se agrega la relación `player_clubs` que al dataset
base le faltaba, de forma idempotente (`INSERT OR IGNORE`).

Corre en cada rebuild vía `build_dataset.py` para que el fix no se pierda.
"""

import json
import sqlite3
from pathlib import Path

from app.text import normalize

FIXES = Path(__file__).resolve().parent / "club_fixes.json"


def _load() -> list[dict]:
    if not FIXES.exists():
        return []
    try:
        return json.loads(FIXES.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def apply_club_fixes(conn: sqlite3.Connection) -> int:
    """Inserta las relaciones `player_clubs` faltantes. Devuelve cuantas aplico."""
    entries = _load()
    if not entries:
        return 0

    known_clubs = {
        r[0] for r in conn.execute("SELECT club_id FROM clubs").fetchall()
    }

    applied = 0
    for entry in entries:
        pid = entry.get("player_id")
        if pid is None:
            continue
        exists = conn.execute(
            "SELECT 1 FROM players WHERE player_id = ?", (pid,)
        ).fetchone()
        if not exists:
            print(f"  [club_fixes] {entry.get('name')!r}: player_id {pid} no existe, omitido")
            continue
        for club in entry.get("club_fixes", []):
            cid = club.get("club_id")
            if cid is None:
                continue
            if cid not in known_clubs:
                # El club no esta en la tabla: lo creamos para no perderlo.
                conn.execute(
                    "INSERT OR IGNORE INTO clubs VALUES (?, ?, ?)",
                    (cid, club.get("name") or str(cid), normalize(club.get("name") or str(cid))),
                )
                known_clubs.add(cid)
            conn.execute(
                "INSERT OR IGNORE INTO player_clubs VALUES (?, ?)", (pid, cid)
            )
            applied += 1
    conn.commit()
    return applied
