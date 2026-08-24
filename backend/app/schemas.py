from datetime import date

from pydantic import BaseModel


class GridLabel(BaseModel):
    kind: str
    id: str
    name: str


class CellInfo(BaseModel):
    row: int
    col: int
    kind: str


class GuessRequest(BaseModel):
    # acepta IDs negativos: los jugadores curados usan IDs sintéticos
    player_id: int


class GuessResponse(BaseModel):
    ok: bool
    cells: list[CellInfo]


class SearchHit(BaseModel):
    player_id: int
    name: str
    position: str | None = None
    dob: str | None = None
    citizenship: str | None = None
    image_url: str | None = None
