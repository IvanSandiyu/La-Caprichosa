"""Generación determinista de puzzles tipo Futbol Link.

Cada día produce un puzzle: un jugador misterioso + 5 compañeros
con los que compartió equipo.
"""

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .config import EXCLUDED_CLUBS

Difficulty = Literal["facil", "normal", "dificil"]

TEAMMATES_COUNT = 5
MAX_TRIES = 300

# brecha de años (desde el año actual hacia atrás) en la que deben encuadrar
# los debuts (estimados como año de nacimiento + 18) del misterioso y sus
# compañeros. 0 = sin restricción (dificil: cualquier época).
GAP_YEARS: dict[Difficulty, int] = {
    "facil": 5,
    "normal": 10,
    "dificil": 0,
}


def _debut_window_sql(alias: str, cur_year: int, gap: int) -> tuple[str, tuple]:
    """Devuelve (SQL, params) que exige que el jugador haya debutado en la ventana.

    La ventana es [cur_year - gap, cur_year]. Si gap==0 no se restringe.
    """
    if gap <= 0:
        return "", ()
    cond = (
        f"({alias}.dob IS NULL"
        f" OR substr({alias}.dob,1,4) GLOB '*[a-z]*'"
        f" OR CAST(substr({alias}.dob,1,4) AS INTEGER) + 18 >= ?)"
    )
    return cond, (cur_year - gap,)


@dataclass
class LinkPuzzle:
    game_date: date
    difficulty: Difficulty
    mystery_player: dict
    teammates: list[dict] = field(default_factory=list)


def _career_range(conn: sqlite3.Connection, player_id: int) -> tuple[int, int] | None:
    """Estimación confiable del rango activo [inicio, fin].

    Devuelve None cuando NO podemos confiar en la fecha de nacimiento para
    ubicar la carrera del jugador (sin DOB, o el DOB es el marcador de
    "fecha desconocida" 2000-01-01). En esos casos no puede garantizarse
    que haya coincidido con otro jugador, así que se trata como "era
    desconocida".
    """
    row = conn.execute("SELECT dob FROM players WHERE player_id=?", (player_id,)).fetchone()
    if not row or not row[0]:
        return None
    dob = row[0].strip()
    if not dob or dob.startswith("2000-01-01"):
        return None
    try:
        y = int(dob[:4])
    except (ValueError, IndexError):
        return None
    return (y + 18, y + 37)


def _clubmates(
    conn: sqlite3.Connection,
    player_id: int,
    cur_year: int,
    gap: int,
) -> list[dict]:
    """Find players who share a club AND whose careers overlap.

    We estimate each player's active years as [dob+18, dob+37]. Two players
    overlap if their ranges intersect. Players whose career era cannot be
    reliably determined (missing or placeholder DOB) are EXCLUDED, because we
    can't guarantee they coincided with the mystery player.
    """
    m_range = _career_range(conn, player_id)
    if m_range is None:
        return []
    m_start, m_end = m_range
    window_sql, window_params = _debut_window_sql("p", cur_year, gap)
    rows = conn.execute(
        f"""
        SELECT DISTINCT
            p.player_id, p.name, p.image_url, c.name AS club,
            p.dob AS p_dob, m.dob AS m_dob
        FROM player_clubs pc1
        JOIN player_clubs pc2 ON pc1.club_id = pc2.club_id AND pc2.player_id != pc1.player_id
        JOIN players p ON p.player_id = pc2.player_id
        JOIN players m ON m.player_id = pc1.player_id
        JOIN clubs c ON c.club_id = pc1.club_id
        WHERE pc1.player_id = ?
          AND p.image_url IS NOT NULL AND p.image_url != ''
          AND p.image_url NOT LIKE '%default.jpg%'
          AND pc1.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
          {('AND ' + window_sql) if window_sql else ''}
        """,
        (player_id, *EXCLUDED_CLUBS, *window_params),
    ).fetchall()

    result = []
    for r in rows:
        p_range = _career_range(conn, r[0])
        if p_range is None:
            continue  # era incierta → no podemos garantizar la coincidencia
        p_start, p_end = p_range
        if p_end < m_start or m_end < p_start:
            continue  # no overlap → skip
        result.append({"id": r[0], "name": r[1], "image_url": r[2], "club": r[3]})

    return result


def _player_hints(conn: sqlite3.Connection, player_id: int) -> dict:
    """Pistas para un jugador: años activos estimados y lista de clubes."""
    years: str | None = None
    rng = _career_range(conn, player_id)
    if rng:
        start, end = rng
        today_year = date.today().year
        if end > today_year:
            end = today_year
        if start <= end:
            years = f"{start}-{end}"
    clubs = [
        r[0]
        for r in conn.execute(
            "SELECT c.name FROM player_clubs pc JOIN clubs c ON c.club_id = pc.club_id "
            "WHERE pc.player_id = ? ORDER BY c.name",
            (player_id,),
        ).fetchall()
        if r[0]
    ]
    return {"years": years, "clubs": clubs}


def _mystery_candidates(
    conn: sqlite3.Connection,
    difficulty: Difficulty,
    cur_year: int,
    gap: int,
) -> list[dict]:
    """Players with enough clubmates who have photos and overlapping careers."""
    min_clubmates = {"facil": 20, "normal": 10, "dificil": 5}.get(difficulty, 10)
    window_sql, window_params = _debut_window_sql("p", cur_year, gap)
    rows = conn.execute(
        f"""
        SELECT p.player_id, p.name, p.image_url, COUNT(DISTINCT pc2.player_id) AS n
        FROM players p
        JOIN player_clubs pc1 ON pc1.player_id = p.player_id
        JOIN player_clubs pc2 ON pc1.club_id = pc2.club_id AND pc2.player_id != p.player_id
        JOIN players p2 ON p2.player_id = pc2.player_id
          AND p2.image_url IS NOT NULL AND p2.image_url != ''
          AND p2.image_url NOT LIKE '%default.jpg%'
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
          AND p.image_url NOT LIKE '%default.jpg%'
          AND p.dob IS NOT NULL AND p.dob != '' AND p.dob NOT LIKE '2000-01-01%'
          AND pc1.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
          {('AND ' + window_sql) if window_sql else ''}
          AND (
            p2.dob IS NULL
            OR ABS(CAST(strftime('%Y', p.dob) AS INT) - CAST(strftime('%Y', p2.dob) AS INT)) <= 19
          )
        GROUP BY p.player_id
        HAVING n >= ?
        """,
        (*EXCLUDED_CLUBS, *window_params, min_clubmates),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2], "n": r[3]} for r in rows]


def _generate(
    game_date: date,
    difficulty: Difficulty,
    conn: sqlite3.Connection,
) -> LinkPuzzle | None:
    rng = random.Random(f"link-{game_date.isoformat()}-{difficulty}")
    cur_year = game_date.year
    gap = GAP_YEARS[difficulty]
    candidates = _mystery_candidates(conn, difficulty, cur_year, gap)
    if not candidates:
        return None

    rng.shuffle(candidates)

    for mystery in candidates:
        clubmates = _clubmates(conn, mystery["id"], cur_year, gap)
        if len(clubmates) < TEAMMATES_COUNT:
            continue

        # deduplicate by player_id, keeping earliest club
        seen: dict[int, dict] = {}
        for cm in clubmates:
            if cm["id"] not in seen and cm.get("image_url"):
                seen[cm["id"]] = cm
        unique = list(seen.values())

        if len(unique) < TEAMMATES_COUNT:
            continue

        # prefer teammates from different clubs
        rng.shuffle(unique)
        chosen: list[dict] = []
        used_clubs: set[str] = set()
        for cm in unique:
            if len(chosen) >= TEAMMATES_COUNT:
                break
            if cm["club"] not in used_clubs:
                chosen.append(cm)
                used_clubs.add(cm["club"])
        # fill remaining if not enough unique clubs
        for cm in unique:
            if len(chosen) >= TEAMMATES_COUNT:
                break
            if cm not in chosen:
                chosen.append(cm)

        return LinkPuzzle(
            game_date=game_date,
            difficulty=difficulty,
            mystery_player={
                "id": mystery["id"],
                "name": mystery["name"],
                "image_url": mystery["image_url"],
            },
            teammates=[
                {
                    "id": cm["id"],
                    "name": cm["name"],
                    "image_url": cm["image_url"],
                    "club": cm["club"],
                    "years": _player_hints(conn, cm["id"])["years"],
                    "clubs": _player_hints(conn, cm["id"])["clubs"],
                }
                for cm in chosen[:TEAMMATES_COUNT]
            ],
        )

    return None


def generate_link_puzzle(
    game_date: date,
    difficulty: Difficulty = "normal",
    conn: sqlite3.Connection | None = None,
) -> LinkPuzzle | None:
    from .db import get_conn
    conn = conn or get_conn()
    return _generate(game_date, difficulty, conn)
