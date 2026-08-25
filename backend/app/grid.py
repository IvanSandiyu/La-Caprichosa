"""Generación determinista de la grilla diaria.

La misma fecha produce siempre la misma grilla en cualquier máquina,
usando un RNG con semilla derivada de la fecha.
"""

import random
import sqlite3
from dataclasses import dataclass
from datetime import date

from .db import get_conn
from .text import normalize

MIN_CELL_POOL = 8          # mínimo ideal de jugadores válidos por celda
FLOOR_CELL_POOL = 2        # piso aceptable si no hay nada mejor
MIN_LABEL_POOL = 25        # mínimo de jugadores para que una etiqueta sea elegible
MAX_ATTEMPTS = 300         # combinaciones aleatorias por nivel de exigencia


@dataclass(frozen=True)
class Label:
    kind: str   # "club" | "country"
    id: str     # club_id o nombre normalizado del país
    name: str   # etiqueta visible


@dataclass
class Grid:
    game_date: date
    rows: tuple[Label, Label, Label]
    cols: tuple[Label, Label, Label]


def _load_labels(conn: sqlite3.Connection) -> list[Label]:
    labels: list[Label] = []
    clubs = conn.execute(
        """
        SELECT c.club_id, c.name, COUNT(DISTINCT pc.player_id) AS n
        FROM clubs c JOIN player_clubs pc ON pc.club_id = c.club_id
        GROUP BY c.club_id HAVING n >= ?
        """,
        (MIN_LABEL_POOL,),
    ).fetchall()
    for row in clubs:
        labels.append(Label("club", str(row["club_id"]), row["name"]))

    countries = conn.execute(
        """
        SELECT country, norm, COUNT(DISTINCT player_id) AS n
        FROM player_countries GROUP BY norm HAVING n >= ?
        """,
        (MIN_LABEL_POOL,),
    ).fetchall()
    for row in countries:
        labels.append(Label("country", row["norm"], row["country"]))
    return labels


def _pool_for(conn: sqlite3.Connection, label: Label) -> set[int]:
    if label.kind == "club":
        rows = conn.execute(
            "SELECT player_id FROM player_clubs WHERE club_id = ?", (int(label.id),)
        )
    else:
        rows = conn.execute(
            "SELECT player_id FROM player_countries WHERE norm = ?", (label.id,)
        )
    return {r["player_id"] for r in rows}


def _fits(conn: sqlite3.Connection, player_id: int, label: Label) -> bool:
    if label.kind == "club":
        hit = conn.execute(
            "SELECT 1 FROM player_clubs WHERE player_id = ? AND club_id = ?",
            (player_id, int(label.id)),
        ).fetchone()
    else:
        hit = conn.execute(
            "SELECT 1 FROM player_countries WHERE player_id = ? AND norm = ?",
            (player_id, label.id),
        ).fetchone()
    return hit is not None


def _fits_all(conn: sqlite3.Connection, player_id: int, labels: list[Label]) -> list[Label]:
    return [lb for lb in labels if _fits(conn, player_id, lb)]


def generate_grid(game_date: date, conn: sqlite3.Connection | None = None) -> Grid:
    conn = conn or get_conn()
    rng = random.Random(f"la-caprichosa-{game_date.isoformat()}")

    all_labels = _load_labels(conn)
    if len(all_labels) < 6:
        raise RuntimeError("Dataset insuficiente para armar grillas")

    best: tuple[tuple[int, int], tuple[tuple[Label, ...], tuple[Label, ...]]] | None = None
    pools: dict[str, set[int]] = {}

    def pool(lb: Label) -> set[int]:
        if lb.id not in pools:
            pools[lb.id] = _pool_for(conn, lb)
        return pools[lb.id]

    countries = [lb for lb in all_labels if lb.kind == "country"]
    clubs_lbls = [lb for lb in all_labels if lb.kind == "club"]
    if not countries or len(clubs_lbls) < 5:
        raise RuntimeError("Dataset insuficiente para armar grillas")

    def try_threshold(min_cell: int):
        nonlocal best
        for _ in range(MAX_ATTEMPTS):
            country = rng.choice(countries)
            # muestreo ponderado sin repetición: clubes más grandes aparecen
            # más, pero el seed diario garantiza variedad
            left = list(clubs_lbls)
            chosen = []
            while len(chosen) < 5:
                ws = [len(pool(lb)) for lb in left]
                i = rng.choices(range(len(left)), weights=ws, k=1)[0]
                chosen.append(left.pop(i))
            six = [country, *chosen]
            rng.shuffle(six)
            rows, cols = tuple(six[:3]), tuple(six[3:])
            sizes = [len(pool(r) & pool(c)) for r in rows for c in cols]
            if min(sizes) < min_cell:
                continue
            score = (min(sizes), sum(sizes))
            if best is None or score > best[0]:
                best = (score, (rows, cols))
                return True  # este nivel ya dio una grilla válida
        return False

    # exigente primero; si no hay suerte, relaja hasta el piso
    level = MIN_CELL_POOL
    while level >= FLOOR_CELL_POOL and best is None:
        try_threshold(level)
        level -= 2

    if best is None:
        raise RuntimeError(
            "No se pudo generar una grilla resoluble con el dataset actual"
        )
    rows, cols = best[1]
    return Grid(game_date, rows, cols)


def validate_player(conn: sqlite3.Connection, player_id: int, grid: Grid) -> dict:
    """Devuelve las celdas de la grilla donde el jugador califica.

    Una celda (fila i, columna j) es válida si el jugador califica tanto
    para la etiqueta de la fila como para la de la columna.
    """
    fit_rows = [i for i, lb in enumerate(grid.rows) if _fits(conn, player_id, lb)]
    fit_cols = [j for j, lb in enumerate(grid.cols) if _fits(conn, player_id, lb)]
    cells = [
        {"row": i, "col": j, "kind": grid.cols[j].kind}
        for i in fit_rows
        for j in fit_cols
    ]
    return {"cells": cells}


def reveal_solution(conn: sqlite3.Connection, grid: Grid) -> list[dict]:
    """Devuelve un jugador válido por cada celda (3×3 = 9 entradas).

    Para cada celda (fila i, columna j) toma un jugador de la
    intersección de los pools de ambas etiquetas.
    """
    results: list[dict] = []
    for i, row_label in enumerate(grid.rows):
        for j, col_label in enumerate(grid.cols):
            pool = _pool_for(conn, row_label) & _pool_for(conn, col_label)
            pid = next(iter(pool)) if pool else None
            if pid is None:
                results.append({"row": i, "col": j, "player_id": 0, "name": "—", "image_url": None})
                continue
            r = conn.execute(
                "SELECT player_id, name, image_url FROM players WHERE player_id = ?",
                (pid,),
            ).fetchone()
            results.append({
                "row": i,
                "col": j,
                "player_id": r[0],
                "name": r[1],
                "image_url": r[2],
            })
    return results


def search_players(query: str, limit: int = 12) -> list[dict]:
    conn = get_conn()
    q = normalize(query)
    if not q:
        return []
    cols = "player_id, name, position, dob, citizenship, image_url"
    rows = conn.execute(
        f"SELECT {cols} FROM players WHERE norm LIKE ? || '%' ORDER BY norm LIMIT ?",
        (q, limit),
    ).fetchall()
    if not rows:
        rows = conn.execute(
            f"SELECT {cols} FROM players WHERE norm LIKE '%' || ? || '%' ORDER BY norm LIMIT ?",
            (q, limit),
        ).fetchall()
    return [dict(r) for r in rows]
