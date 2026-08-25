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


@dataclass
class LinkPuzzle:
    game_date: date
    difficulty: Difficulty
    mystery_player: dict
    teammates: list[dict] = field(default_factory=list)


def _clubmates(conn: sqlite3.Connection, player_id: int) -> list[dict]:
    """Find all players who share at least one club with the given player."""
    rows = conn.execute(
        """
        SELECT DISTINCT p.player_id, p.name, p.image_url, c.name AS club
        FROM player_clubs pc1
        JOIN player_clubs pc2 ON pc1.club_id = pc2.club_id AND pc2.player_id != pc1.player_id
        JOIN players p ON p.player_id = pc2.player_id
        JOIN clubs c ON c.club_id = pc1.club_id
        WHERE pc1.player_id = ?
          AND p.image_url IS NOT NULL AND p.image_url != ''
        """,
        (player_id,),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2], "club": r[3]} for r in rows]


def _mystery_candidates(conn: sqlite3.Connection, difficulty: Difficulty) -> list[dict]:
    """Players with enough clubmates who have photos."""
    min_clubmates = {"facil": 20, "normal": 10, "dificil": 5}.get(difficulty, 10)
    rows = conn.execute(
        """
        SELECT p.player_id, p.name, p.image_url, COUNT(DISTINCT pc2.player_id) AS n
        FROM players p
        JOIN player_clubs pc1 ON pc1.player_id = p.player_id
        JOIN player_clubs pc2 ON pc1.club_id = pc2.club_id AND pc2.player_id != p.player_id
        JOIN players p2 ON p2.player_id = pc2.player_id
          AND p2.image_url IS NOT NULL AND p2.image_url != ''
        WHERE p.image_url IS NOT NULL AND p.image_url != ''
        GROUP BY p.player_id
        HAVING n >= ?
        """,
        (min_clubmates,),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2], "n": r[3]} for r in rows]


def _generate(
    game_date: date,
    difficulty: Difficulty,
    conn: sqlite3.Connection,
) -> LinkPuzzle | None:
    rng = random.Random(f"link-{game_date.isoformat()}-{difficulty}")
    candidates = _mystery_candidates(conn, difficulty)
    if not candidates:
        return None

    rng.shuffle(candidates)

    for mystery in candidates:
        clubmates = _clubmates(conn, mystery["id"])
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
