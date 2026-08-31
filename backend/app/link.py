"""Generación determinista de puzzles tipo Futbol Link.

Cada día produce un puzzle: un jugador misterioso + 5 compañeros
con los que compartió equipo.
"""

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

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


def _clubmates(
    conn: sqlite3.Connection,
    player_id: int,
    cur_year: int,
    gap: int,
) -> list[dict]:
    """Find players who share a club AND whose careers could overlap.

    We estimate each player's active years as [dob+18, dob+37].
    Two players overlap if their ranges intersect.
    Players without DOB are included (fallback: assume possible overlap).
    """
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
          {('AND ' + window_sql) if window_sql else ''}
        """,
        (player_id, *window_params),
    ).fetchall()

    result = []
    for r in rows:
        p_dob, m_dob = r[4], r[5]
        # if both have DOB, check career overlap
        if p_dob and m_dob:
            try:
                p_year = int(p_dob[:4])
                m_year = int(m_dob[:4])
                # estimated active range: age 18–37
                p_start, p_end = p_year + 18, p_year + 37
                m_start, m_end = m_year + 18, m_year + 37
                if p_end < m_start or m_end < p_start:
                    continue  # no overlap → skip
            except (ValueError, IndexError):
                pass  # bad DOB format → include anyway
        result.append({"id": r[0], "name": r[1], "image_url": r[2], "club": r[3]})

    return result


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
          {('AND ' + window_sql) if window_sql else ''}
          AND (
            p.dob IS NULL OR p2.dob IS NULL
            OR ABS(CAST(strftime('%Y', p.dob) AS INT) - CAST(strftime('%Y', p2.dob) AS INT)) <= 19
          )
        GROUP BY p.player_id
        HAVING n >= ?
        """,
        (*window_params, min_clubmates),
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
                {"id": cm["id"], "name": cm["name"], "image_url": cm["image_url"], "club": cm["club"]}
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
