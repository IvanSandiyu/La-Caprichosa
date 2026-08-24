from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import grid as grid_mod
from .config import GAME_NAME
from .db import get_conn
from .schemas import CellInfo, GuessRequest, GuessResponse, GridLabel, SearchHit

app = FastAPI(title=GAME_NAME)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_grid_cache: dict[str, grid_mod.Grid] = {}


def get_grid(game_date: date) -> grid_mod.Grid:
    key = game_date.isoformat()
    if key not in _grid_cache:
        _grid_cache.clear()  # solo nos interesa el día corriente
        _grid_cache[key] = grid_mod.generate_grid(game_date)
    return _grid_cache[key]


def label_out(lb) -> GridLabel:
    return GridLabel(kind=lb.kind, id=lb.id, name=lb.name)


@app.get("/api/grid")
def today_grid():
    g = get_grid(date.today())
    return {
        "date": g.game_date.isoformat(),
        "rows": [label_out(r).model_dump() for r in g.rows],
        "cols": [label_out(c).model_dump() for c in g.cols],
    }


@app.post("/api/guess", response_model=GuessResponse)
def guess(req: GuessRequest):
    conn = get_conn()
    player = conn.execute(
        "SELECT player_id FROM players WHERE player_id = ?", (req.player_id,)
    ).fetchone()
    if not player:
        raise HTTPException(status_code=404, detail="Jugador inexistente")
    g = get_grid(date.today())
    result = grid_mod.validate_player(conn, req.player_id, g)
    return GuessResponse(ok=bool(result["cells"]), cells=result["cells"])


@app.get("/api/search", response_model=list[SearchHit])
def search(q: str = "", limit: int = 12):
    return [
        SearchHit(**hit).model_dump() for hit in grid_mod.search_players(q, min(limit, 25))
    ]


@app.get("/api/players/index")
def players_index():
    """Índice completo para búsqueda local en el cliente (comprimido con gzip)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT player_id, name, position, citizenship FROM players ORDER BY name"
    ).fetchall()
    return [
        {"id": r[0], "name": r[1], "position": r[2], "citizenship": r[3]}
        for r in rows
    ]


@app.get("/api/player/{player_id}", response_model=SearchHit)
def player_detail(player_id: int):
    """Ficha completa (imagen incluida) para un jugador elegido del índice."""
    conn = get_conn()
    row = conn.execute(
        "SELECT player_id, name, position, dob, citizenship, image_url "
        "FROM players WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Jugador inexistente")
    return SearchHit(
        player_id=row[0],
        name=row[1],
        position=row[2],
        dob=row[3],
        citizenship=row[4],
        image_url=row[5],
    )
