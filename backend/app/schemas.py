from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


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


class FeedbackRequest(BaseModel):
    issue: Literal["clubes_incompletos", "jugador_faltante"]
    player_id: int | None = None
    player_name: str = Field(..., min_length=1, max_length=200)
    game: str | None = None
    message: str = Field(default="", max_length=2000)
