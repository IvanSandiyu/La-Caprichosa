"""Generación determinista de puzzles tipo Impostor.

Cada día produce un puzzle: una categoría (algo en común entre jugadores)
y un tablero de jugadores donde algunos cumplen la categoría y otros
son impostores. El reto es seleccionar a los correctos sin tocar un impostor.
"""

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .config import EXCLUDED_CLUBS, MIN_SEASON

Difficulty = Literal["facil", "normal", "dificil"]

BOARD_SIZE = 9

# cantidad de impostores por dificultad (el resto son correctos)
IMPOSTORS: dict[Difficulty, int] = {
    "facil": 3,
    "normal": 4,
    "dificil": 5,
}

MAX_TRIES = 300


@dataclass
class ImpostorPlayer:
    id: int
    name: str
    image_url: str | None
    is_impostor: bool = False


@dataclass
class ImpostorPuzzle:
    game_date: date
    difficulty: Difficulty
    category: str          # texto visible, ej: "Jugó en Boca Juniors"
    category_type: str     # club | youth_club | position | nationality | birth_year | last_name | ...
    players: list[ImpostorPlayer] = field(default_factory=list)

    @property
    def correct(self) -> list[ImpostorPlayer]:
        return [p for p in self.players if not p.is_impostor]


def _img(prefix: str = "") -> str:
    pre = (prefix + ".") if prefix else ""
    return (
        f"{pre}image_url IS NOT NULL AND {pre}image_url != '' "
        f"AND {pre}image_url NOT LIKE '%default.jpg%'"
    )


def _recent(prefix: str = "") -> str:
    """Filtra al pool reciente (última temporada >= MIN_SEASON)."""
    pre = (prefix + ".") if prefix else ""
    return f" AND {pre}last_season >= {MIN_SEASON}"


def _last_name(name: str) -> str:
    parts = name.strip().split()
    return " ".join(parts[1:]) if len(parts) > 1 else name


# ── consultas de jugadores correctos por categoría ──────────────────────

def _club_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_clubs pc
        JOIN players p ON p.player_id = pc.player_id
        WHERE pc.club_id = ? AND {_img('p')}{_recent('p') if recent_only else ''}
        """,
        (info["id"],),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _position_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players WHERE position = ? AND {_img()}{_recent() if recent_only else ''}
        """,
        (info["label"],),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _nationality_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_countries pc
        JOIN players p ON p.player_id = pc.player_id
        WHERE pc.norm = ? AND {_img('p')}{_recent('p') if recent_only else ''}
        """,
        (info["label"],),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _birth_year_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE substr(dob,1,4) = ? AND {_img()}{_recent() if recent_only else ''}
        """,
        (str(info["label"]),),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _last_name_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE name LIKE '%' || ? || '%' AND {_img()}{_recent() if recent_only else ''}
        """,
        (info["label"],),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _two_clubs_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Jugadores que jugaron en AMBOS clubes (intersección)."""
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_clubs pc1
        JOIN player_clubs pc2 ON pc2.player_id = pc1.player_id
        JOIN players p ON p.player_id = pc1.player_id
        WHERE pc1.club_id = ? AND pc2.club_id = ?
          AND {_img('p')}{_recent('p') if recent_only else ''}
        """,
        (info["id1"], info["id2"]),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _club_country_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Jugadores que jugaron en el club Y en la selección del país."""
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_clubs pc
        JOIN players p ON p.player_id = pc.player_id
        JOIN player_countries pcnt ON pcnt.player_id = p.player_id
        WHERE pc.club_id = ? AND pcnt.norm = ?
          AND {_img('p')}{_recent('p') if recent_only else ''}
        """,
        (info["id"], info["country"]),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _born_before_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Jugadores nacidos antes del año límite."""
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE substr(dob,1,4) IS NOT NULL
          AND substr(dob,1,4) NOT GLOB '*[a-z]*'
          AND CAST(substr(dob,1,4) AS INTEGER) < ?
          AND {_img()}{_recent() if recent_only else ''}
        """,
        (info["year"],),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _youth_club_players(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Jugadores formados (divisiones juveniles) en el club X."""
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM player_youth py
        JOIN players p ON p.player_id = py.player_id
        WHERE py.club_id = ? AND {_img('p')}{_recent('p') if recent_only else ''}
        """,
        (info["id"],),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


CATEGORY_QUERY = {
    "club": _club_players,
    "position": _position_players,
    "nationality": _nationality_players,
    "birth_year": _birth_year_players,
    "last_name": _last_name_players,
    "two_clubs": _two_clubs_players,
    "club_country": _club_country_players,
    "born_before": _born_before_players,
    "youth_club": _youth_club_players,
}


# ── consultas de impostores (jugadores que NO cumplen la categoría) ──────

def _club_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM players p
        WHERE {_img('p')}{_recent('p') if recent_only else ''}
          AND p.player_id NOT IN (
              SELECT player_id FROM player_clubs WHERE club_id = ?
          )
        ORDER BY p.player_id LIMIT ?
        """,
        (info["id"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _position_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE {_img()}{_recent() if recent_only else ''} AND position IS NOT NULL AND position != ?
        ORDER BY player_id LIMIT ?
        """,
        (info["label"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _nationality_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM players p
        WHERE {_img('p')}{_recent('p') if recent_only else ''}
          AND p.player_id NOT IN (
              SELECT player_id FROM player_countries WHERE norm = ?
          )
        ORDER BY p.player_id LIMIT ?
        """,
        (info["label"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _birth_year_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE {_img()}{_recent() if recent_only else ''} AND substr(dob,1,4) != ?
        ORDER BY player_id LIMIT ?
        """,
        (str(info["label"]), limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _last_name_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE {_img()}{_recent() if recent_only else ''} AND name NOT LIKE '%' || ? || '%'
        ORDER BY player_id LIMIT ?
        """,
        (info["label"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _two_clubs_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Impostores: jugadores que NO jugaron en ambos clubes (no en la intersección)."""
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM players p
        WHERE {_img('p')}{_recent('p') if recent_only else ''}
          AND p.player_id NOT IN (
              SELECT pa.player_id FROM player_clubs pa
              JOIN player_clubs pb ON pb.player_id = pa.player_id
              WHERE pa.club_id = ? AND pb.club_id = ?
          )
        ORDER BY p.player_id LIMIT ?
        """,
        (info["id1"], info["id2"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _club_country_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Impostores: jugadores que NO jugaron en el club Y en la selección del país."""
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM players p
        WHERE {_img('p')}{_recent('p') if recent_only else ''}
          AND p.player_id NOT IN (
              SELECT pc.player_id FROM player_clubs pc
              JOIN player_countries pcnt ON pcnt.player_id = pc.player_id
              WHERE pc.club_id = ? AND pcnt.norm = ?
          )
        ORDER BY p.player_id LIMIT ?
        """,
        (info["id"], info["country"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _born_before_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Impostores: jugadores Nacidos en el año límite o después."""
    rows = conn.execute(
        f"""
        SELECT player_id, name, image_url
        FROM players
        WHERE {_img()}{_recent() if recent_only else ''}
          AND substr(dob,1,4) IS NOT NULL
          AND substr(dob,1,4) NOT GLOB '*[a-z]*'
          AND CAST(substr(dob,1,4) AS INTEGER) >= ?
        ORDER BY player_id LIMIT ?
        """,
        (info["year"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


def _youth_club_impostors(conn: sqlite3.Connection, info: dict, limit: int, recent_only: bool = False) -> list[dict]:
    """Impostores: jugadores que NO se formaron en el club X."""
    rows = conn.execute(
        f"""
        SELECT DISTINCT p.player_id, p.name, p.image_url
        FROM players p
        WHERE {_img('p')}{_recent('p') if recent_only else ''}
          AND p.player_id NOT IN (
              SELECT player_id FROM player_youth WHERE club_id = ?
          )
        ORDER BY p.player_id LIMIT ?
        """,
        (info["id"], limit),
    ).fetchall()
    return [{"id": r[0], "name": r[1], "image_url": r[2]} for r in rows]


IMPOSTOR_QUERY = {
    "club": _club_impostors,
    "position": _position_impostors,
    "nationality": _nationality_impostors,
    "birth_year": _birth_year_impostors,
    "last_name": _last_name_impostors,
    "two_clubs": _two_clubs_impostors,
    "club_country": _club_country_impostors,
    "born_before": _born_before_impostors,
    "youth_club": _youth_club_impostors,
}


# ── catálogo de categorías disponibles ───────────────────────────────────

def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _available_clubs(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT c.club_id, c.name, COUNT(DISTINCT pc.player_id) AS n
        FROM clubs c JOIN player_clubs pc ON pc.club_id = c.club_id
        JOIN players p ON p.player_id = pc.player_id
        WHERE {_img('p')}
          AND c.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
        GROUP BY c.club_id HAVING n >= ?
        """,
        (*EXCLUDED_CLUBS, min_match),
    ).fetchall()
    out = [{"type": "club", "label": r[1], "id": r[0]} for r in rows]
    rng.shuffle(out)
    return out


def _available_youth_clubs(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    if not _has_table(conn, "player_youth"):
        return []
    rows = conn.execute(
        f"""
        SELECT c.club_id, c.name, COUNT(DISTINCT py.player_id) AS n
        FROM player_youth py
        JOIN clubs c ON c.club_id = py.club_id
        JOIN players p ON p.player_id = py.player_id
        WHERE {_img('p')}
          AND c.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
        GROUP BY c.club_id HAVING n >= ?
        """,
        (*EXCLUDED_CLUBS, min_match),
    ).fetchall()
    out = [{"type": "youth_club", "label": r[1], "id": r[0]} for r in rows]
    rng.shuffle(out)
    return out


def _available_positions(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT position, COUNT(*) AS n FROM players
        WHERE position IS NOT NULL AND {_img()}
        GROUP BY position HAVING n >= ?
        """,
        (min_match,),
    ).fetchall()
    out = [{"type": "position", "label": r[0]} for r in rows]
    rng.shuffle(out)
    return out


def _available_nationalities(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT pc.norm, COUNT(DISTINCT pc.player_id) AS n
        FROM player_countries pc JOIN players p ON p.player_id = pc.player_id
        WHERE {_img('p')} AND pc.norm NOT GLOB '*[0-9]*'
        GROUP BY pc.norm HAVING n >= ?
        """,
        (min_match,),
    ).fetchall()
    out = [{"type": "nationality", "label": r[0]} for r in rows]
    rng.shuffle(out)
    return out


def _available_birth_years(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    # solo años "reconocibles" (1970 en adelante) para que la categoría tenga sentido
    rows = conn.execute(
        f"""
        SELECT substr(dob,1,4) AS y, COUNT(*) AS n FROM players
        WHERE dob IS NOT NULL AND substr(dob,1,4) IS NOT NULL
          AND substr(dob,1,4) NOT GLOB '*[a-z]*'
          AND CAST(substr(dob,1,4) AS INTEGER) >= 1970
          AND {_img()}
        GROUP BY substr(dob,1,4) HAVING n >= ?
        """,
        (min_match,),
    ).fetchall()
    out = [{"type": "birth_year", "label": r[0]} for r in rows]
    rng.shuffle(out)
    return out


def _available_last_names(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT name, COUNT(*) AS n FROM players
        WHERE {_img()}
        GROUP BY name HAVING n >= ? AND n <= 25
        """,
        (min_match,),
    ).fetchall()
    # group by apellido (sobrenombre del nombre completo)
    by_last: dict[str, list] = {}
    seen: dict[str, list] = {}
    for full, n in rows:
        last = _last_name(full)
        by_last.setdefault(last, []).append((full, n))
    out = []
    for last, members in by_last.items():
        total = sum(n for _, n in members)
        if total >= min_match and total <= 25:
            rep = members[0][0]
            out.append({"type": "last_name", "label": last, "display": rep})
    rng.shuffle(out)
    return out


def _available_two_clubs(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT a.club_id, a.name, b.club_id, b.name, COUNT(DISTINCT p.player_id) AS n
        FROM player_clubs pa
        JOIN player_clubs pb ON pb.player_id = pa.player_id AND pb.club_id > pa.club_id
        JOIN clubs a ON a.club_id = pa.club_id
        JOIN clubs b ON b.club_id = pb.club_id
        JOIN players p ON p.player_id = pa.player_id
        WHERE {_img('p')}
          AND a.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
          AND b.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
        GROUP BY pa.club_id, pb.club_id HAVING n >= ?
        ORDER BY n DESC LIMIT 60
        """,
        (*EXCLUDED_CLUBS, *EXCLUDED_CLUBS, min_match),
    ).fetchall()
    out = [
        {"type": "two_clubs", "id1": r[0], "name1": r[1], "id2": r[2], "name2": r[3]}
        for r in rows
    ]
    rng.shuffle(out)
    return out


def _available_club_country(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT c.club_id, c.name, pcnt.norm, COUNT(DISTINCT p.player_id) AS n
        FROM player_clubs pc
        JOIN clubs c ON c.club_id = pc.club_id
        JOIN players p ON p.player_id = pc.player_id
        JOIN player_countries pcnt ON pcnt.player_id = p.player_id
        WHERE {_img('p')} AND pcnt.norm = 'argentina'
          AND c.club_id NOT IN ({",".join("?" for _ in EXCLUDED_CLUBS)})
        GROUP BY c.club_id HAVING n >= ?
        ORDER BY n DESC LIMIT 40
        """,
        (*EXCLUDED_CLUBS, min_match),
    ).fetchall()
    out = [
        {"type": "club_country", "id": r[0], "club": r[1], "country": r[2]}
        for r in rows
    ]
    rng.shuffle(out)
    return out


def _available_born_before(conn: sqlite3.Connection, rng: random.Random, min_match: int) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT CAST(substr(dob,1,4) AS INTEGER) AS y, COUNT(*) AS n
        FROM players
        WHERE dob IS NOT NULL
          AND substr(dob,1,4) IS NOT NULL
          AND substr(dob,1,4) NOT GLOB '*[a-z]*'
          AND {_img()}
        GROUP BY y
        """
    ).fetchall()
    total = sum(n for _, n in rows)
    # solo años donde AMBOS lados (antes y después) tengan jugadores suficientes:
    # el año debe dejar al menos ~30% de la población de cada lado
    cumulative = 0
    out = []
    for y, n in rows:
        if not (1950 <= y <= 2008):
            continue
        cumulative += n
        before = cumulative
        after = total - before
        if before >= min_match and after >= min_match and 0.25 <= before / total <= 0.75:
            out.append({"type": "born_before", "year": y, "label": str(y)})
    rng.shuffle(out)
    return out


def _category_catalog(conn: sqlite3.Connection, rng: random.Random, difficulty: Difficulty) -> list[dict]:
    impostors_needed = IMPOSTORS[difficulty]
    min_match = BOARD_SIZE - impostors_needed
    catalog = (
        _available_clubs(conn, rng, min_match)
        + _available_youth_clubs(conn, rng, min_match)
        + _available_positions(conn, rng, min_match)
        + _available_nationalities(conn, rng, min_match)
        + _available_birth_years(conn, rng, min_match)
        + _available_last_names(conn, rng, min_match)
        + _available_two_clubs(conn, rng, min_match)
        + _available_club_country(conn, rng, min_match)
        + _available_born_before(conn, rng, min_match)
    )
    # mezclar TODO el catálogo para que ningún tipo de categoría domine
    rng.shuffle(catalog)
    return catalog


def _category_text(info: dict) -> str:
    t = info["type"]
    if t == "club":
        return f"Jugó en {info['label']}"
    if t == "youth_club":
        return f"Se formó en las inferiores de {info['label']}"
    if t == "position":
        pos = {"Attack": "delantero", "Midfield": "mediocampista", "Defender": "defensor", "Goalkeeper": "arquero"}.get(info["label"], info["label"].lower())
        return f"Jugó como {pos}"
    if t == "nationality":
        return f"Jugó en la selección de {info['label'].capitalize()}"
    if t == "birth_year":
        return f"Nació en {info['label']}"
    if t == "last_name":
        return f"Su apellido es {info['label']}"
    if t == "two_clubs":
        return f"Jugó en {info['name1']} y en {info['name2']}"
    if t == "club_country":
        return f"Jugó en {info['club']} y en la selección de {info['country'].capitalize()}"
    if t == "born_before":
        return f"Nació antes de {info['label']}"
    return info.get("label", info.get("name", ""))


# ── generador ────────────────────────────────────────────────────────────

def _generate(
    game_date: date,
    difficulty: Difficulty,
    conn: sqlite3.Connection,
) -> ImpostorPuzzle | None:
    rng = random.Random(f"impostor-{game_date.isoformat()}-{difficulty}")
    # en modo fácil, todos los jugadores salen del pool reciente (>= MIN_SEASON)
    recent_only = difficulty == "facil"
    catalog = _category_catalog(conn, rng, difficulty)
    impostors_needed = IMPOSTORS[difficulty]
    correct_needed = BOARD_SIZE - impostors_needed

    for info in catalog:
        ctype = info["type"]
        query_fn = CATEGORY_QUERY[ctype]
        impostor_fn = IMPOSTOR_QUERY[ctype]

        correct_pool = query_fn(conn, info, BOARD_SIZE, recent_only)

        if len(correct_pool) < correct_needed:
            continue

        rng.shuffle(correct_pool)
        chosen_correct = correct_pool[:correct_needed]
        correct_ids = {p["id"] for p in chosen_correct}

        # pool candidato a impostor: mucho más grande, filtramos después
        pool_limit = (impostors_needed + correct_needed) * 8
        impostor_pool = impostor_fn(conn, info, pool_limit, recent_only)

        # filtrar los que ya son correctos y son impostores válidos
        candidates_imp = [p for p in impostor_pool if p["id"] not in correct_ids]
        rng.shuffle(candidates_imp)
        chosen_impostors = candidates_imp[:impostors_needed]

        if len(chosen_impostors) < impostors_needed:
            continue

        candidates = [
            *(ImpostorPlayer(id=p["id"], name=p["name"], image_url=p.get("image_url"), is_impostor=False) for p in chosen_correct),
            *(ImpostorPlayer(id=p["id"], name=p["name"], image_url=p.get("image_url"), is_impostor=True) for p in chosen_impostors),
        ]
        rng.shuffle(candidates)

        return ImpostorPuzzle(
            game_date=game_date,
            difficulty=difficulty,
            category=_category_text(info),
            category_type=ctype,
            players=candidates,
        )

    return None


def generate_impostor_puzzle(
    game_date: date,
    difficulty: Difficulty = "normal",
    conn: sqlite3.Connection | None = None,
) -> ImpostorPuzzle | None:
    from .db import get_conn
    conn = conn or get_conn()
    return _generate(game_date, difficulty, conn)
