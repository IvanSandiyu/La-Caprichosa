import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import top10 as top10_mod  # noqa: E402
from app.db import get_conn  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    return get_conn()


def test_top10_determinista(conn):
    hoy = date.today()
    p1 = top10_mod.generate_top10(hoy, conn)
    p2 = top10_mod.generate_top10(hoy, conn)
    assert p1 is not None
    assert p1.methodology == p2.methodology
    assert p1.club == p2.club
    assert [a["name"] for a in p1.answers] == [a["name"] for a in p2.answers]


def test_top10_tamano_y_orden(conn):
    p = top10_mod.generate_top10(date.today(), conn)
    assert p is not None
    assert len(p.answers) == 10
    values = [a["value"] for a in p.answers]
    assert values == sorted(values, reverse=True)


def test_top10_consigna_completa(conn):
    p = top10_mod.generate_top10(date.today(), conn)
    assert p is not None
    assert p.methodology["clue"].startswith("Top 10")
    assert "{" not in p.methodology["clue"]
    assert p.club["name"]
    for a in p.answers:
        assert a["name"]
        assert a["value"] >= 0


def test_top10_varios_dias_validos(conn):
    for d in range(1, 15):
        p = top10_mod.generate_top10(date(2026, 1, d), conn)
        assert p is not None, f"falló el día {d}"
        assert len(p.answers) == 10


def test_top10_solo_clubes_destacados(conn):
    from app.top10 import FEATURED_CLUB_IDS

    for d in range(1, 31):
        p = top10_mod.generate_top10(date(2026, 3, d), conn)
        assert p is not None, f"falló el día {d}"
        assert p.club["id"] in FEATURED_CLUB_IDS, f"club fuera del pool: {p.club}"


def test_top10_index_cubre_respuestas(conn):
    idx = {e["name"] for e in top10_mod.build_suggestion_index(conn)}
    assert len(idx) > 5000, "el índice debería incluir todos los jugadores de la BD"
    for d in range(1, 11):
        p = top10_mod.generate_top10(date(2026, 4, d), conn)
        assert p is not None, f"falló el día {d}"
        for a in p.answers:
            assert a["name"] in idx, f"respuesta no tipeable: {a['name']}"