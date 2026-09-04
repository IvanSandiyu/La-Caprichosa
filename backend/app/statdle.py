"""Juego diario tipo Statdle sobre el fútbol argentino.

Cada día se elige (determinista por fecha) un jugador y una temporada de
su carrera en Primera División. Se muestran pistas de esa temporada
(equipo, nacionalidad, posición, edad, apariciones, goles, promedio de gol,
debut, clubes) y el jugador debe adivinar quién es en pocos intentos.

Modos:
  - normal : 9 pistas, se revelan en orden aleatorio.
  - dificil: 7 pistas; las de Club y País quedan bloqueadas (locked).

Las pistas salen de player_career (temporadas limpias: un solo año) unidas
a players (foto, nacimiento, ciudadanía, posición).
"""

import random
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .config import EXCLUDED_CLUBS

Difficulty = Literal["normal", "dificil"]

POSITION_ES = {
    "Goalkeeper": "Arquero",
    "Defender": "Defensor",
    "Midfield": "Mediocampista",
    "Attack": "Delantero",
}

# pistas que en modo difícil quedan bloqueadas
LOCKED_KINDS = {"club", "country"}

# temporadas con PJ dentro de este rango (entran en el pool de puzzles)
MIN_PJ = 3
MAX_PJ = 45

# cantidad de pistas visibles (el resto queda bloqueada en modo dificil)
TOTAL_CLUES = 9


@dataclass
class StatdleClue:
    kind: str
    label: str
    value: str | None      # None cuando la pista está bloqueada
    locked: bool = False


@dataclass
class StatdlePuzzle:
    game_date: date
    difficulty: Difficulty
    league: str = "Primera División"
    season: int | None = None
    target: dict = field(default_factory=dict)   # {id, name, image_url}
    slots: list[StatdleClue] = field(default_factory=list)


def _clean_season_rows(conn: sqlite3.Connection) -> list[tuple]:
    """Filas 'temporada limpia' (un solo año) de Primera, listas para clue."""
    excluded = ",".join(str(c) for c in EXCLUDED_CLUBS) or "NULL"
    return conn.execute(
        f"""
        SELECT pc.player_id,
               pc.year_from,
               pc.club_name,
               pc.pj,
               pc.goals,
               p.name,
               p.image_url,
               p.dob,
               p.citizenship,
               p.position
        FROM player_career pc
        JOIN players p ON p.player_id = pc.player_id
        WHERE pc.section = 'Primera División'
          AND pc.pj > ? AND pc.pj <= ?
          AND pc.year_from = pc.year_to
          AND pc.year_from IS NOT NULL
          AND pc.club_name IS NOT NULL
          AND pc.club_id IS NOT NULL
          AND pc.club_id NOT IN ({excluded})
          AND p.image_url IS NOT NULL AND p.image_url != ''
          AND p.image_url NOT LIKE '%default.jpg%'
          AND p.dob IS NOT NULL
          AND p.citizenship IS NOT NULL
          AND p.position IN ('Goalkeeper','Defender','Midfield','Attack')
        """,
        (MIN_PJ, MAX_PJ),
    ).fetchall()


def _birth_year(dob: str) -> int | None:
    try:
        return int(str(dob)[:4])
    except (TypeError, ValueError):
        return None


def _career_context(conn: sqlite3.Connection, player_id: int) -> dict:
    """Datos de la carrera completa en Primera: debut y cantidad de clubes."""
    rows = conn.execute(
        "SELECT MIN(year_from), COUNT(DISTINCT club_id) "
        "FROM player_career WHERE player_id = ? AND section='Primera División'",
        (player_id,),
    ).fetchone()
    return {"debut": rows[0], "clubs": rows[1]}


def _build_slots(
    row: tuple, ctx: dict, difficulty: Difficulty, rng: random.Random
) -> list[StatdleClue]:
    (
        _pid, season, club_name, pj, goals,
        _name, _img, dob, citizenship, position,
    ) = row
    byear = _birth_year(dob) or season
    age = max(season - byear, 0)
    avg = (goals / pj) if pj else 0.0

    clues = [
        StatdleClue(kind="club", label="Equipo", value=club_name),
        StatdleClue(kind="country", label="Nacionalidad", value=citizenship),
        StatdleClue(kind="position", label="Posición", value=POSITION_ES.get(position, position)),
        StatdleClue(kind="age", label=f"Edad en {season}", value=f"{age} años"),
        StatdleClue(kind="apps", label="Apariciones", value=str(pj)),
        StatdleClue(kind="goals", label="Goles", value=str(goals)),
        StatdleClue(kind="avg", label="Gol por partido", value=f"{avg:.2f}"),
        StatdleClue(kind="debut", label="Debut en 1ª", value=str(ctx["debut"]) if ctx["debut"] else None),
        StatdleClue(kind="clubs", label="Clubes en 1ª", value=str(ctx["clubs"]) if ctx["clubs"] else None),
    ]

    if difficulty == "dificil":
        for c in clues:
            if c.kind in LOCKED_KINDS:
                c.locked = True
                c.value = None

    rng.shuffle(clues)
    return clues


def _generate(
    game_date: date,
    difficulty: Difficulty,
    conn: sqlite3.Connection,
) -> StatdlePuzzle | None:
    rng = random.Random(f"statdle-{game_date.isoformat()}-{difficulty}")
    rows = _clean_season_rows(conn)
    if not rows:
        return None

    row = rows[rng.randrange(len(rows))]
    ctx = _career_context(conn, row[0])
    if ctx["clubs"] is None or ctx["debut"] is None:
        ctx = {"debut": row[1], "clubs": 1}

    slots = _build_slots(row, ctx, difficulty, rng)
    return StatdlePuzzle(
        game_date=game_date,
        difficulty=difficulty,
        season=row[1],
        target={"id": row[0], "name": row[5], "image_url": row[6]},
        slots=slots,
    )


def generate_statdle(
    game_date: date,
    difficulty: Difficulty = "normal",
    conn: sqlite3.Connection | None = None,
) -> StatdlePuzzle | None:
    from .db import get_conn
    conn = conn or get_conn()
    return _generate(game_date, difficulty, conn)