"""Generación determinista de puzzles tipo Conexiones.

Cada día produce un puzzle de 4 grupos × 4 jugadores usando un RNG
con semilla derivada de la fecha y la dificultad.
"""

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .config import EXCLUDED_CLUBS, MIN_SEASON

Difficulty = Literal["facil", "normal", "dificil"]

MISTAKES: dict[Difficulty, int | None] = {
    "facil": None,   # sin límite
    "normal": 4,
    "dificil": 3,
}

REQUIRED_GROUPS = 4
GROUP_SIZE = 4
MIN_POOL_PER_LABEL = 6  # mínimo de jugadores por etiqueta para ser útil
MAX_TRIES = 200


@dataclass
class PuzzleGroup:
    name: str           # nombre visible de la conexión
    group_type: str     # club | nationality | position | last_name | first_name
    player_ids: list[int] = field(default_factory=list)
    player_names: list[str] = field(default_factory=list)
    image_urls: list[str | None] = field(default_factory=list)


@dataclass
class Puzzle:
    game_date: date
    difficulty: Difficulty
    groups: list[PuzzleGroup]
    player_ids: list[int] = field(default_factory=list)


# ── queries ────────────────────────────────────────────────────────────

def _club_players(conn: sqlite3.Connection, club_id: int, exclude: set[int]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_clubs pc
        JOIN players p ON p.player_id = pc.player_id
        WHERE pc.club_id = ? AND p.player_id NOT IN ({ids})
          AND p.image_url IS NOT NULL AND p.image_url != ''
          AND p.image_url NOT LIKE '%default.jpg%'
          AND p.last_season >= ?
        LIMIT 20
        """.format(ids=",".join("?" * len(exclude)) or "0"),
        (club_id, *exclude, MIN_SEASON),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _nationality_players(conn: sqlite3.Connection, country: str, exclude: set[int]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_countries pc
        JOIN players p ON p.player_id = pc.player_id
        WHERE pc.country = ? AND p.player_id NOT IN ({ids})
          AND p.image_url IS NOT NULL AND p.image_url != ''
          AND p.image_url NOT LIKE '%default.jpg%'
          AND p.last_season >= ?
        LIMIT 20
        """.format(ids=",".join("?" * len(exclude)) or "0"),
        (country, *exclude, MIN_SEASON),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _position_players(conn: sqlite3.Connection, position: str, exclude: set[int]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT player_id, name, image_url
        FROM players
        WHERE position = ? AND player_id NOT IN ({ids})
          AND image_url IS NOT NULL AND image_url != ''
          AND image_url NOT LIKE '%default.jpg%'
          AND last_season >= ?
        LIMIT 20
        """.format(ids=",".join("?" * len(exclude)) or "0"),
        (position, *exclude, MIN_SEASON),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _last_name(name: str) -> str:
    parts = name.strip().split()
    if len(parts) <= 1:
        return name
    return " ".join(parts[1:])


def _last_name_players(conn: sqlite3.Connection, last: str, exclude: set[int]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT player_id, name, image_url
        FROM players
        WHERE name LIKE '%' || ? || '%'
          AND player_id NOT IN ({ids})
          AND image_url IS NOT NULL AND image_url != ''
          AND image_url NOT LIKE '%default.jpg%'
          AND last_season >= ?
        LIMIT 20
        """.format(ids=",".join("?" * len(exclude)) or "0"),
        (last, *exclude, MIN_SEASON),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _first_name_players(conn: sqlite3.Connection, first: str, exclude: set[int]) -> list[dict]:
    rows = conn.execute(
        """
        SELECT player_id, name, image_url
        FROM players
        WHERE name LIKE ? || '%'
          AND player_id NOT IN ({ids})
          AND image_url IS NOT NULL AND image_url != ''
          AND image_url NOT LIKE '%default.jpg%'
          AND last_season >= ?
        LIMIT 20
        """.format(ids=",".join("?" * len(exclude)) or "0"),
        (first, *exclude, MIN_SEASON),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


QUERY_MAP = {
    "club": _club_players,
    "nationality": _nationality_players,
    "position": _position_players,
    "last_name": _last_name_players,
    "first_name": _first_name_players,
}


def _available_clubs(conn: sqlite3.Connection) -> list[dict]:
    return [
        {"type": "club", "label": r["name"], "id": r["club_id"]}
        for r in conn.execute(
            f"""
            SELECT c.club_id, c.name, COUNT(DISTINCT pc.player_id) AS n
            FROM clubs c JOIN player_clubs pc ON pc.club_id = c.club_id
            JOIN players p ON p.player_id = pc.player_id
            WHERE p.image_url IS NOT NULL AND p.image_url != ''
              AND p.image_url NOT LIKE '%default.jpg%'
              AND p.last_season >= ?
              AND c.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
            GROUP BY c.club_id HAVING n >= ?
            """,
            (MIN_SEASON, *EXCLUDED_CLUBS, MIN_POOL_PER_LABEL),
        ).fetchall()
    ]


def _available_nationalities(conn: sqlite3.Connection) -> list[dict]:
    return [
        {"type": "nationality", "label": r["country"]}
        for r in conn.execute(
            """
            SELECT pc.country, COUNT(DISTINCT pc.player_id) AS n
            FROM player_countries pc
            JOIN players p ON p.player_id = pc.player_id
            WHERE p.image_url IS NOT NULL AND p.image_url != ''
              AND p.image_url NOT LIKE '%default.jpg%'
              AND p.last_season >= ?
            GROUP BY pc.country HAVING n >= ?
            """,
            (MIN_SEASON, MIN_POOL_PER_LABEL),
        ).fetchall()
    ]


def _available_positions(conn: sqlite3.Connection) -> list[dict]:
    return [
        {"type": "position", "label": r["position"]}
        for r in conn.execute(
            """
            SELECT position, COUNT(*) AS n
            FROM players WHERE position IS NOT NULL
              AND image_url IS NOT NULL AND image_url != ''
              AND image_url NOT LIKE '%default.jpg%'
              AND last_season >= ?
            GROUP BY position HAVING n >= ?
            """,
            (MIN_SEASON, MIN_POOL_PER_LABEL),
        ).fetchall()
    ]


def _available_last_names(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT name, COUNT(*) AS n FROM players
        WHERE image_url IS NOT NULL AND image_url != ''
          AND image_url NOT LIKE '%default.jpg%'
          AND last_season >= ?
        GROUP BY name HAVING n >= ? AND n <= 12
        """,
        (MIN_SEASON, GROUP_SIZE),
    ).fetchall()
    return [
        {"type": "last_name", "label": _last_name(r[0]), "display": r[0]}
        for r in rows
    ]


def _available_first_names(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT SUBSTR(name, 1, INSTR(name || ' ', ' ') - 1) AS first,
               COUNT(*) AS n
        FROM players
        WHERE image_url IS NOT NULL AND image_url != ''
          AND image_url NOT LIKE '%default.jpg%'
          AND last_season >= ?
        GROUP BY first HAVING n >= ? AND n <= 15
        """,
        (MIN_SEASON, GROUP_SIZE),
    ).fetchall()
    return [
        {"type": "first_name", "label": r[0]}
        for r in rows
    ]


# ── generador ──────────────────────────────────────────────────────────

def _pick_group(
    conn: sqlite3.Connection,
    rng: random.Random,
    available: list[dict],
    exclude: set[int],
) -> PuzzleGroup | None:
    """Intenta armar un grupo de 4 jugadores con una conexión."""
    labels = list(available)
    rng.shuffle(labels)
    for info in labels:
        gtype = info["type"]
        label = info["label"]
        query_fn = QUERY_MAP[gtype]
        if gtype == "club":
            candidates = query_fn(conn, info["id"], exclude)
        else:
            candidates = query_fn(conn, label, exclude)
        if len(candidates) < GROUP_SIZE:
            continue
        chosen = rng.sample(candidates, GROUP_SIZE)
        return PuzzleGroup(
            name=label,
            group_type=gtype,
            player_ids=[p["id"] for p in chosen],
            player_names=[p["name"] for p in chosen],
            image_urls=[p["image_url"] for p in chosen],
        )
    return None


def _generate(
    game_date: date,
    difficulty: Difficulty,
    conn: sqlite3.Connection,
) -> Puzzle | None:
    rng = random.Random(f"conexiones-{game_date.isoformat()}-{difficulty}")

    all_available = (
        _available_clubs(conn)
        + _available_nationalities(conn)
        + _available_positions(conn)
        + _available_last_names(conn)
        + _available_first_names(conn)
    )
    if not all_available:
        return None

    for _ in range(MAX_TRIES):
        shuffled = list(all_available)
        rng.shuffle(shuffled)
        groups: list[PuzzleGroup] = []
        used_ids: set[int] = set()

        for _ in range(REQUIRED_GROUPS):
            g = _pick_group(conn, rng, shuffled, used_ids)
            if g is None:
                break
            groups.append(g)
            used_ids.update(g.player_ids)

        if len(groups) == REQUIRED_GROUPS:
            total = len(used_ids)
            if total == REQUIRED_GROUPS * GROUP_SIZE:
                player_ids = []
                for g in groups:
                    player_ids.extend(g.player_ids)
                return Puzzle(
                    game_date=game_date,
                    difficulty=difficulty,
                    groups=groups,
                    player_ids=player_ids,
                )

    return None


def generate_puzzle(
    game_date: date,
    difficulty: Difficulty = "normal",
    conn: sqlite3.Connection | None = None,
) -> Puzzle | None:
    from .db import get_conn
    conn = conn or get_conn()
    return _generate(game_date, difficulty, conn)
