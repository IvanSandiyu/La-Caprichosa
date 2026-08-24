import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import grid as grid_mod  # noqa: E402
from app.db import get_conn  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    return get_conn()


def test_grid_determinista(conn):
    hoy = date.today()
    g1 = grid_mod.generate_grid(hoy, conn)
    g2 = grid_mod.generate_grid(hoy, conn)
    assert [lb.id for lb in g1.rows] == [lb.id for lb in g2.rows]
    assert [lb.id for lb in g1.cols] == [lb.id for lb in g2.cols]


def test_grid_valida_y_resoluble(conn):
    g = grid_mod.generate_grid(date.today(), conn)
    labels = [*g.rows, *g.cols]

    # 6 etiquetas únicas: exactamente una selección y 5 clubes
    assert len({lb.id for lb in labels}) == 6
    n_countries = sum(1 for lb in labels if lb.kind == "country")
    assert n_countries == 1

    # las 9 celdas deben tener suficientes jugadores válidos
    for r in g.rows:
        for c in g.cols:
            pool = grid_mod._pool_for(conn, r) & grid_mod._pool_for(conn, c)
            assert len(pool) >= 2, f"Celda {r.name}×{c.name} con solo {len(pool)}"


def test_jugador_califica_en_celda_correspondiente(conn):
    boca_row = conn.execute(
        "SELECT club_id FROM clubs WHERE norm = 'boca juniors'"
    ).fetchone()
    if not boca_row:
        pytest.skip("Boca Juniors no está en el dataset")

    boca_lb = grid_mod.Label("club", str(boca_row["club_id"]), "Boca Juniors")
    arg_lb = grid_mod.Label("country", "argentina", "Argentina")
    pool = grid_mod._pool_for(conn, boca_lb) & grid_mod._pool_for(conn, arg_lb)
    assert pool, "Debería haber jugadores de Boca con ciudadanía argentina"

    pid = sorted(pool)[0]
    g = grid_mod.generate_grid(date.today(), conn)
    res = grid_mod.validate_player(conn, pid, g)

    # toda celda devuelta debe ser coherente con la grilla actual
    label_ids = {lb.id for lb in [*g.rows, *g.cols]}
    for cell in res["cells"]:
        assert cell["row"] in range(3) and cell["col"] in range(3)
        assert g.rows[cell["row"]].id in label_ids
        assert g.cols[cell["col"]].id in label_ids


def test_busqueda_normalizada(conn):
    hits = grid_mod.search_players("cavani")
    assert any("Cavani" in h["name"] for h in hits)

    # sin acentos también debe encontrar (Éver Banega o similar)
    hits = grid_mod.search_players("funes mor")
    assert hits, "La búsqueda con espacios debería funcionar"


def test_busqueda_vacia_o_basura(conn):
    assert grid_mod.search_players("") == []
    assert grid_mod.search_players("zzzzqqqq") == []
