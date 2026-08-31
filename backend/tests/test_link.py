import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import link as link_mod  # noqa: E402
from app.db import get_conn  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    return get_conn()


def _all_ids(p):
    return [p.mystery_player["id"]] + [t["id"] for t in p.teammates]


def _debuts(conn, ids):
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT player_id, dob FROM players WHERE player_id IN ({ph})", ids
    ).fetchall()
    out = {}
    for pid, dob in rows:
        if dob and not dob[:4].isalpha():
            year = int(dob[:4])
            out[pid] = year + 18  # debut estimado
    return out


def test_link_determinista(conn):
    hoy = date(2026, 8, 28)
    for diff in ["facil", "normal", "dificil"]:
        p1 = link_mod.generate_link_puzzle(hoy, diff, conn)
        p2 = link_mod.generate_link_puzzle(hoy, diff, conn)
        assert p1 is not None
        assert p1.mystery_player["id"] == p2.mystery_player["id"]
        assert [t["id"] for t in p1.teammates] == [t["id"] for t in p2.teammates]


def test_link_cantidad_y_fotos(conn):
    p = link_mod.generate_link_puzzle(date(2026, 8, 20), "normal", conn)
    assert p is not None
    assert len(p.teammates) == 5
    assert p.mystery_player["image_url"]
    for t in p.teammates:
        assert t["image_url"] and "default.jpg" not in t["image_url"]


def test_link_brecha_facil(conn):
    """facil: todos los debuts dentro de [año_actual-5, año_actual]."""
    cur = 2026
    for d in range(1, 15, 2):
        p = link_mod.generate_link_puzzle(date(2026, 8, d), "facil", conn)
        if p is None:
            continue
        debuts = _debuts(conn, _all_ids(p))
        for pid, debut in debuts.items():
            assert cur - 5 <= debut <= cur, f"debut {debut} fuera de ventana (jugador {pid})"


def test_link_brecha_normal(conn):
    """normal: debuts dentro de [año_actual-10, año_actual]."""
    cur = 2026
    for d in range(1, 15, 2):
        p = link_mod.generate_link_puzzle(date(2026, 8, d), "normal", conn)
        if p is None:
            continue
        debuts = _debuts(conn, _all_ids(p))
        for pid, debut in debuts.items():
            assert cur - 10 <= debut <= cur, f"debut {debut} fuera de ventana (jugador {pid})"


def test_link_brecha_dificil_sin_restriccion(conn):
    """dificil: sin ventana; en la muestra debe aparecer algún jugador viejo
    (debut hace >10 años), que facil/normal excluyen."""
    cur = 2026
    encontro_viejo = False
    total = 0
    for d in range(1, 31):
        p = link_mod.generate_link_puzzle(date(2026, 8, d), "dificil", conn)
        if p is None:
            continue
        total += 1
        debuts = _debuts(conn, _all_ids(p))
        if any(debut <= cur - 10 for debut in debuts.values()):
            encontro_viejo = True
            break
    assert total > 0, "no se generó ningún puzzle dificil"
    assert encontro_viejo, "dificil debería incluir jugadores de hace >10 años"
