from datetime import date
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import grid as grid_mod
from . import impostor as impostor_mod
from . import link as link_mod
from . import puzzles as puzzles_mod
from . import statdle as statdle_mod
from .config import GAME_NAME
from .db import get_conn
from .schemas import CellInfo, GuessRequest, GuessResponse, GridLabel, SearchHit

app = FastAPI(title=GAME_NAME)
app.add_middleware(GZipMiddleware, minimum_size=1024)

# API pública y de solo lectura (sin auth): permitimos cualquier origen.
# Si querés acotar, seteá CORS_ORIGINS="https://x.vercel.app,https://y.com".
_cors_raw = os.environ.get("CORS_ORIGINS", "*")
_cors_origins = (
    ["*"]
    if _cors_raw.strip() == "*"
    else [o.strip() for o in _cors_raw.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

_grid_cache: dict[str, grid_mod.Grid] = {}
_puzzle_cache: dict[str, puzzles_mod.Puzzle] = {}
_link_cache: dict[str, link_mod.LinkPuzzle] = {}
_impostor_cache: dict[str, impostor_mod.ImpostorPuzzle] = {}
_statdle_cache: dict[str, statdle_mod.StatdlePuzzle] = {}


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


@app.post("/api/reveal")
def reveal():
    """Devuelve un jugador válido por cada celda de la grilla del día."""
    g = get_grid(date.today())
    conn = get_conn()
    return grid_mod.reveal_solution(conn, g)


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


@app.get("/api/puzzles/today")
def puzzle_today(difficulty: str = "normal"):
    """Devuelve el puzzle de conexiones del día."""
    from fastapi import Query
    key = f"{date.today().isoformat()}-{difficulty}"
    if key not in _puzzle_cache:
        _puzzle_cache.clear()
        p = puzzles_mod.generate_puzzle(date.today(), difficulty)
        if p is None:
            raise HTTPException(status_code=500, detail="No se pudo generar puzzle")
        _puzzle_cache[key] = p
    p = _puzzle_cache[key]
    # validate all players have images
    for g in p.groups:
        for url in g.image_urls:
            if not url:
                _puzzle_cache.clear()
                p = puzzles_mod.generate_puzzle(date.today(), difficulty)
                if p is None:
                    raise HTTPException(status_code=500, detail="No se pudo generar puzzle sin imágenes")
                _puzzle_cache[key] = p
                break
        else:
            continue
        break
    return {
        "date": p.game_date.isoformat(),
        "difficulty": p.difficulty,
        "groups": [
            {
                "name": g.name,
                "group_type": g.group_type,
                "player_ids": g.player_ids,
                "player_names": g.player_names,
                "image_urls": g.image_urls,
            }
            for g in p.groups
        ],
        "player_ids": p.player_ids,
    }


@app.get("/api/link/today")
def link_today(difficulty: str = "normal"):
    """Devuelve el puzzle de Futbol Link del día."""
    key = f"{date.today().isoformat()}-{difficulty}"
    if key not in _link_cache:
        _link_cache.clear()
        p = link_mod.generate_link_puzzle(date.today(), difficulty)
        if p is None:
            raise HTTPException(status_code=500, detail="No se pudo generar puzzle link")
        _link_cache[key] = p
    p = _link_cache[key]
    return {
        "date": p.game_date.isoformat(),
        "difficulty": p.difficulty,
        "mystery_player": p.mystery_player,
        "teammates": p.teammates,
    }


@app.get("/api/statdle/today")
def statdle_today(difficulty: str = "normal"):
    """Devuelve el puzzle de Statdle del día (jugador + pistas de temporada)."""
    if difficulty not in ("normal", "dificil"):
        raise HTTPException(status_code=400, detail="Dificultad inválida")
    key = f"{date.today().isoformat()}-{difficulty}"
    if key not in _statdle_cache:
        _statdle_cache.clear()
        p = statdle_mod.generate_statdle(date.today(), difficulty)
        if p is None:
            raise HTTPException(status_code=500, detail="No se pudo generar puzzle statdle")
        _statdle_cache[key] = p
    p = _statdle_cache[key]
    return {
        "date": p.game_date.isoformat(),
        "difficulty": p.difficulty,
        "league": p.league,
        "season": p.season,
        "target": p.target,
        "slots": [
            {"kind": c.kind, "label": c.label, "value": c.value, "locked": c.locked}
            for c in p.slots
        ],
    }


@app.get("/api/impostor/today")
def impostor_today(difficulty: str = "normal"):
    """Devuelve el puzzle de Impostor del día."""
    key = f"{date.today().isoformat()}-{difficulty}"
    if key not in _impostor_cache:
        _impostor_cache.clear()
        p = impostor_mod.generate_impostor_puzzle(date.today(), difficulty)
        if p is None:
            raise HTTPException(status_code=500, detail="No se pudo generar puzzle impostor")
        _impostor_cache[key] = p
    p = _impostor_cache[key]
    return {
        "date": p.game_date.isoformat(),
        "difficulty": p.difficulty,
        "category": p.category,
        "category_type": p.category_type,
        "players": [
            {
                "id": pl.id,
                "name": pl.name,
                "image_url": pl.image_url,
                "is_impostor": pl.is_impostor,
            }
            for pl in p.players
        ],
    }
