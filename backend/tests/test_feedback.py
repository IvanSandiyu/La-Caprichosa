import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import feedback_store  # noqa: E402
from app.schemas import FeedbackRequest  # noqa: E402


@pytest.fixture(scope="module")
def conn():
    feedback_store.ensure_feedback_table(remote=False)
    return feedback_store.get_conn()


def test_feedback_tabla_existe(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='players_feedback'"
    ).fetchall()
    assert rows, "Falta la tabla players_feedback"


def test_feedback_insert_y_select(conn):
    conn.execute("DELETE FROM players_feedback WHERE player_name = 'Test Feedback'")
    conn.commit()
    fid = feedback_store.add_feedback(
        issue="clubes_incompletos",
        player_id=-100392,
        player_name="Test Feedback",
        game="futbol-link",
        message="jugó también en Boca",
        remote=False,
    )
    assert isinstance(fid, int) and fid > 0
    row = conn.execute(
        "SELECT issue, player_id, player_name, game, message FROM players_feedback "
        "WHERE id = ?",
        (fid,),
    ).fetchone()
    assert row["issue"] == "clubes_incompletos"
    assert row["player_id"] == -100392
    assert row["player_name"] == "Test Feedback"
    assert row["game"] == "futbol-link"
    assert row["message"] == "jugó también en Boca"
    conn.execute("DELETE FROM players_feedback WHERE id = ?", (fid,))
    conn.commit()


def test_feedback_list_local():
    feedback_store.ensure_feedback_table(remote=False)
    assert isinstance(feedback_store.list_feedback(limit=5, remote=False), list)


def test_feedback_schema_valido():
    req = FeedbackRequest(
        issue="jugador_faltante",
        player_name="  Alfredo Di Stéfano  ",
        game="grid",
        message="no figura en la base",
    )
    assert req.player_name == "  Alfredo Di Stéfano  "
    assert req.issue == "jugador_faltante"
    assert req.player_id is None


def test_feedback_schema_rechaza_issue_desconocido():
    with pytest.raises(Exception):
        FeedbackRequest(issue="otra_cosa", player_name="X")


def test_feedback_schema_rechaza_sin_nombre():
    with pytest.raises(Exception):
        FeedbackRequest(issue="clubes_incompletos", player_name="")