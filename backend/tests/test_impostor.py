import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import impostor as impostor_mod  # noqa: E402
from app.db import get_conn  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    return get_conn()


def test_impostor_determinista(conn):
    hoy = date.today()
    for diff in ["facil", "normal", "dificil"]:
        p1 = impostor_mod.generate_impostor_puzzle(hoy, diff, conn)
        p2 = impostor_mod.generate_impostor_puzzle(hoy, diff, conn)
        assert p1 is not None
        assert [x.id for x in p1.players] == [x.id for x in p2.players]
        assert p1.category == p2.category


def test_impostor_tamano_y_mezcla(conn):
    p = impostor_mod.generate_impostor_puzzle(date.today(), "normal", conn)
    assert p is not None
    assert len(p.players) == 9
    correct = [x for x in p.players if not x.is_impostor]
    impostors = [x for x in p.players if x.is_impostor]
    assert len(impostors) == 4
    assert len(correct) == 5


def test_impostor_fotos(conn):
    p = impostor_mod.generate_impostor_puzzle(date.today(), "normal", conn)
    assert p is not None
    for pl in p.players:
        assert pl.image_url and "default.jpg" not in pl.image_url


def test_impostor_dificultades(conn):
    for diff in ["facil", "normal", "dificil"]:
        p = impostor_mod.generate_impostor_puzzle(date.today(), diff, conn)
        assert p is not None
        assert len(p.players) == 9


def test_youth_club_players_consulta(tmp_path, monkeypatch):
    """Verifica la consulta de cantera con una base mínima en memoria."""
    import sqlite3

    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE players (player_id INTEGER PRIMARY KEY, name TEXT, image_url TEXT, position TEXT, dob TEXT);
        CREATE TABLE clubs (club_id INTEGER PRIMARY KEY, name TEXT, norm TEXT);
        CREATE TABLE player_youth (player_id INTEGER, club_id INTEGER, PRIMARY KEY (player_id, club_id));
        INSERT INTO clubs VALUES (189, 'Boca Juniors', 'boca jrs');
        INSERT INTO players VALUES
            (1, 'Jugador A', 'http://x/a.jpg', 'Attack', '1990-01-01'),
            (2, 'Jugador B', 'http://x/b.jpg', 'Attack', '1991-01-01'),
            (3, 'Jugador C', 'http://x/c.jpg', 'Attack', '1992-01-01'),
            (4, 'Jugador D', 'http://x/d.jpg', 'Attack', '1993-01-01');
        INSERT INTO player_youth VALUES (1, 189), (2, 189);
        """
    )
    info = {"type": "youth_club", "label": "Boca Juniors", "id": 189}
    correcto = impostor_mod._youth_club_players(db, info, 10)
    impostores = impostor_mod._youth_club_impostors(db, info, 10)
    assert {p["id"] for p in correcto} == {1, 2}
    assert {p["id"] for p in impostores} == {3, 4}
