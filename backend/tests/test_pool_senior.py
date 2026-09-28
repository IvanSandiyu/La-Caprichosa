"""Regresiones del pool senior y de los fixes curados de feedback.

Cubre los bugs reales que sacaron jugadores del pool:
  * `name_matches_senior` debe matchear contra `normalize(name)`, NO contra la
    columna `norm` de la BDD (que en algunos jugadores usa guiones bajos, con
    lo cual el nombre quedaba en un solo token y Pablo Perez no entraba al pool
    de la seleccion).
  * `merge_enrichment` debe dejar ganar el dato curado cuando el dataset base
    trae la MISMA persona con nacionalidad contradictoria.
  * los reportes de feedback (Riquelme -> Argentinos, Fuenzalida -> Boca)
    deben seguir reflejados en la BDD.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_conn  # noqa: E402
from app.text import normalize  # noqa: E402
from pipeline.argentina_senior import name_matches_senior  # noqa: E402

PABLO = -103082
PABLO_NAME = "Pablo Javier Pérez"


@pytest.fixture(scope="module")
def conn():
    return get_conn()


def test_match_ignora_guiones_bajos_de_la_columna_norm(conn):
    """El match debe funcionar aunque la BDD guarde el norm con guiones bajos."""
    senior = [["pablo", "perez"]]
    assert name_matches_senior("pablo javier perez", senior) is True
    # el bug: la columna norm de la fila sintetica venia con "_" y no matcheaba
    assert name_matches_senior("pablo_javier_perez", senior) is False
    # por eso el pipeline matchea contra normalize(name):
    row = conn.execute(
        "SELECT name FROM players WHERE player_id = ?", (PABLO,)
    ).fetchone()
    assert name_matches_senior(normalize(row[0]), senior) is True


def test_pablo_perez_en_el_pool_de_la_seleccion(conn):
    """Pablo Perez (Newell's, Boca, Sarmiento...) debe estar en el pool Argentina."""
    en_pool = conn.execute(
        """SELECT COUNT(*) FROM player_countries
            WHERE player_id = ? AND norm = 'argentina'""",
        (PABLO,),
    ).fetchone()[0]
    assert en_pool == 1, "Pablo Perez quedo fuera del pool de la seleccion"


def test_pablo_perez_tiene_sus_clubes(conn):
    clubes = {
        r[0]
        for r in conn.execute(
            """SELECT cl.norm FROM player_clubs pc
                 JOIN clubs cl ON cl.club_id = pc.club_id
                WHERE pc.player_id = ?""",
            (PABLO,),
        )
    }
    for esperado in (
        "newell s old boys",
        "boca juniors",
        "sarmiento junin",
        "independiente",
        "union sf",
    ):
        assert esperado in clubes, f"falta el club {esperado}"


def test_pablo_perez_no_duplicado(conn):
    """Solo debe existir un Pablo Javier Perez."""
    n = conn.execute(
        "SELECT COUNT(*) FROM players WHERE name = ?", (PABLO_NAME,)
    ).fetchone()[0]
    assert n == 1, f"hay {n} filas de {PABLO_NAME}"


def test_pablo_perez_es_argentino(conn):
    paises = [
        r[0]
        for r in conn.execute(
            "SELECT norm FROM player_countries WHERE player_id = ?", (PABLO,)
        )
    ]
    assert paises == ["argentina"], f"paises inesperados: {paises}"


def test_feedback_riquelme_argentinos(conn):
    """Reporte 'clubes_incompletos' de Riquelme: debe estar en Argentinos Juniors."""
    r = conn.execute(
        """SELECT cl.name FROM player_clubs pc JOIN clubs cl ON cl.club_id = pc.club_id
            WHERE pc.player_id = -100910 AND cl.norm = 'argentinos juniors'"""
    ).fetchall()
    assert r, "Riquelme no esta en Argentinos Juniors"


def test_feedback_fuenzalida_boca(conn):
    """Reporte 'jugador_faltante' de Fuenzalida (chileno que joue en Boca)."""
    r = conn.execute(
        """SELECT cl.name FROM player_clubs pc JOIN clubs cl ON cl.club_id = pc.club_id
            WHERE pc.player_id = -8 AND cl.norm = 'boca juniors'"""
    ).fetchall()
    assert r, "Fuenzalida no esta en Boca Juniors"
