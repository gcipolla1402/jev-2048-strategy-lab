from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MoveRequest(BaseModel):
    direction: Literal["up", "down", "left", "right"]


class JevMoveRequest(BaseModel):
    generation: int = Field(ge=1)
    state_version: int = Field(ge=1)


class ControlRequest(BaseModel):
    action: Literal["pause", "resume", "manual", "jev"]


class StrategyRequest(BaseModel):
    strategy: Literal["basic", "strategic"]


class BenchmarkRequest(BaseModel):
    games_per_mode: Literal[1, 5, 10]
    max_moves: int | None = Field(default=None, ge=1, le=5000)
    max_calls: int | None = Field(default=None, ge=1, le=5000)
    max_seconds: int | None = Field(default=None, ge=10, le=7200)


class ErrorResponse(BaseModel):
    detail: str

