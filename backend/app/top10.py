"""Generación determinista de puzzles "Top 10" (estilo FutbolTop11).

Cada día se elige (de forma determinista por fecha) un club y una metodología
del ##histórico## de BDFA (jugadores con más partidos / más goles en totales,
Primera División, Copa Argentina, Segunda, etc.) y se devuelve el top 10
ordenado por valor. El cliente muestra la consigna y el jugador tipea nombres:
al acertar, el nombre aparece en su posición del ranking.
"""

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

TOP10_COUNT = 10

Category = Literal[
    "TOTALES",
    "PRIMERA DIVISIÓN",
    "COPA ARGENTINA",
    "SEGUNDA DIVISIÓN",
    "REGIONAL A",
    "REGIONAL B",
    "TERCERA DIVISIÓN",
    "CUARTA DIVISIÓN",
    "QUINTA DIVISIÓN",
]

# Refranes de consigna por categoría: sufijo que se le agrega al club.
CATEGORY_SUFFIX: dict[str, str] = {
    "TOTALES": "en la historia de {club}",
    "PRIMERA DIVISIÓN": "en Primera División con {club}",
    "COPA ARGENTINA": "en Copa Argentina con {club}",
    "SEGUNDA DIVISIÓN": "con {club} en la Segunda División",
    "REGIONAL A": "con {club} en el Regional A",
    "REGIONAL B": "con {club} en el Regional B",
    "TERCERA DIVISIÓN": "con {club} en la Tercera División",
    "CUARTA DIVISIÓN": "con {club} en la Cuarta División",
    "QUINTA DIVISIÓN": "con {club} en la Quinta División",
}

METRIC_SUBJECT: dict[str, str] = {
    "PARTIDOS": "más partidos",
    "GOLES": "más goles",
}

# Categorías que preferimos mostrar (las históricas de equipos importantes).
_FAVORITE_ORDER = [
    "TOTALES",
    "PRIMERA DIVISIÓN",
    "COPA ARGENTINA",
    "SEGUNDA DIVISIÓN",
    "REGIONAL A",
    "TERCERA DIVISIÓN",
    "CUARTA DIVISIÓN",
    "QUINTA DIVISIÓN",
    "REGIONAL B",
]

# Clubes destacados: solo salen estos en el sorteo diario (IDs de BDFA).
# Los 5 grandes + Estudiantes de La Plata, Vélez, Rosario Central y Lanús.
FEATURED_CLUB_IDS = {6, 17, 12, 16, 19, 59, 22, 18, 13}


@dataclass
class Top10Puzzle:
    game_date: date
    methodology: dict
    club: dict
    answers: list[dict] = field(default_factory=list)


def _combos(conn: sqlite3.Connection) -> list[tuple]:
    """Combos (club, categoría, métrica) con al menos 10 jugadores

    para armar un top 10 (solo clubes reales de nuestra DB). Se devuelven
    ordenados por preferencia de categoría para que el sorteo favorezca
    las consignas históricas clásicas.
    """
    combos = [
        r
        for r in conn.execute("""
            SELECT h.club_bdfa_id, h.club_name, h.category, h.metric
            FROM club_history h
            WHERE h.club_id IS NOT NULL
              AND h.club_name IS NOT NULL AND h.club_name != ''
              AND h.category IN ({order})
            GROUP BY h.club_bdfa_id, h.category, h.metric
            HAVING COUNT(*) >= {n}
            """.format(order=", ".join(f"'{c}'" for c in _FAVORITE_ORDER), n=TOP10_COUNT),
        ).fetchall()
        if r[0] in FEATURED_CLUB_IDS
    ]
    key = lambda r: _FAVORITE_ORDER.index(r[2]) if r[2] in _FAVORITE_ORDER else 99
    return sorted(combos, key=key)


def _slug(text: str) -> str:
    return (
        text.lower()
        .replace("ó", "o")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ú", "u")
        .replace(" ", "-")
    )


def _clue(category: str, metric: str, club_name: str) -> str:
    subject = METRIC_SUBJECT.get(metric, f"récord {metric.lower()}")
    suffix = CATEGORY_SUFFIX.get(category, f"con {club_name}")
    return f"Top 10 con {subject} {suffix.format(club=club_name)}"


def _generate(
    game_date: date,
    conn: sqlite3.Connection,
) -> Top10Puzzle | None:
    combos = _combos(conn)
    if not combos:
        return None
    rng = random.Random(f"top10-{game_date.isoformat()}")
    club_bdfa_id, club_name, category, metric = rng.choice(combos)

    answers = [
        {"name": r[0], "country": r[1], "value": r[2]}
        for r in conn.execute(
            """SELECT name, country, value FROM club_history
               WHERE club_bdfa_id = ? AND category = ? AND metric = ?
               ORDER BY value DESC, name
               LIMIT ?""",
            (club_bdfa_id, category, metric, TOP10_COUNT),
        ).fetchall()
    ]

    return Top10Puzzle(
        game_date=game_date,
        methodology={
            "id": f"{_slug(category)}-{_slug(metric)}",
            "category": category,
            "metric": _slug(metric),
            "clue": _clue(category, metric, club_name),
        },
        club={"id": club_bdfa_id, "name": club_name},
        answers=answers,
    )


def build_suggestion_index(conn: sqlite3.Connection) -> list[dict]:
    """Índice de nombres para el autocompletar del cliente.

    Combina todos los jugadores de la BD (Transfermarkt) con los nombres del
    histórico de BDFA de los clubes destacados, para que cada respuesta del
    puzzle sea tipeable aunque el jugador histórico no esté en la BD.
    """
    entries: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(name: str, country: str) -> None:
        key = (name.casefold(), country or "")
        if key not in seen:
            seen.add(key)
            entries.append({"name": name, "country": country})

    for name, country in conn.execute(
        "SELECT name, COALESCE(citizenship, '') FROM players ORDER BY name"
    ).fetchall():
        add(name, country)

    ids = ", ".join(str(i) for i in FEATURED_CLUB_IDS)
    for name, country in conn.execute(
        f"""
        SELECT name, COALESCE(country, '')
        FROM club_history
        WHERE club_bdfa_id IN ({ids})
        GROUP BY name, country
        ORDER BY name
        """
    ).fetchall():
        add(name, country)

    return entries


def generate_top10(
    game_date: date,
    conn: sqlite3.Connection | None = None,
) -> Top10Puzzle | None:
    from .db import get_conn
    conn = conn or get_conn()
    return _generate(game_date, conn)