from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from random import Random, SystemRandom
from typing import Any, Literal
from uuid import uuid4

from .game_engine import Board, Direction, has_won, highest_tile, is_game_over, new_board
from .domain import Strategy
from .metrics import Metrics

GameStatus = Literal["playing", "paused", "won", "game_over"]
GameMode = Literal["manual", "jev"]


@dataclass
class HistoryEntry:
    number: int
    move: Direction
    score: int
    score_gained: int
    origin: Literal["jev", "forced", "manual"]
    latency_ms: float | None = None
    confidence: float | None = None
    strategy: Strategy | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DecisionSnapshot:
    move: Direction
    origin: Literal["jev", "forced"]
    probabilities: dict[str, float]
    confidence: float | None
    latency_ms: float | None
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    strategy: Strategy = "basic"
    legal_move_count: int = 0
    request_bytes: int = 0
    move_analysis: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    seed: int = field(default_factory=lambda: SystemRandom().randrange(1, 2**31))
    board: Board = field(init=False)
    rng: Random = field(init=False, repr=False)
    score: int = 0
    best_score: int = 0
    total_moves: int = 0
    status: GameStatus = "playing"
    mode: GameMode = "manual"
    strategy: Strategy = "basic"
    won_once: bool = False
    generation: int = 1
    state_version: int = 1
    control_token: int = 1
    decision_pending: bool = False
    pending_request_id: str | None = field(default=None, repr=False)
    history: list[HistoryEntry] = field(default_factory=list)
    decision: DecisionSnapshot | None = None
    metrics: Metrics = field(default_factory=Metrics)
    last_error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    spawned_at: tuple[int, int] | None = None
    merged_positions: list[tuple[int, int]] = field(default_factory=list)
    last_direction: Direction | None = None
    strategy_transitions: list[dict[str, Any]] = field(default_factory=list)
    result_saved: bool = False

    def __post_init__(self) -> None:
        self.rng = Random(self.seed)
        self.board = new_board(self.rng)

    def reset_round(self) -> None:
        self.best_score = max(self.best_score, self.score)
        self.seed = SystemRandom().randrange(1, 2**31)
        self.rng = Random(self.seed)
        self.board = new_board(self.rng)
        self.score = 0
        self.total_moves = 0
        self.status = "playing"
        self.mode = "manual"
        self.won_once = False
        self.generation += 1
        self.state_version += 1
        self.control_token += 1
        self.decision_pending = False
        self.pending_request_id = None
        self.history.clear()
        self.decision = None
        self.metrics = Metrics()
        self.last_error = None
        self.started_at = datetime.now(UTC)
        self.spawned_at = None
        self.merged_positions = []
        self.last_direction = None
        self.strategy_transitions.clear()
        self.result_saved = False

    def refresh_status(self) -> None:
        if is_game_over(self.board):
            self.status = "game_over"
        elif has_won(self.board) and not self.won_once:
            self.won_once = True
            self.status = "won"

    def elapsed_seconds(self) -> int:
        return max(0, int((datetime.now(UTC) - self.started_at).total_seconds()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "board": self.board,
            "score": self.score,
            "best_score": self.best_score,
            "highest_tile": highest_tile(self.board),
            "empty_cells": sum(value == 0 for row in self.board for value in row),
            "total_moves": self.total_moves,
            "status": self.status,
            "mode": self.mode,
            "strategy": self.strategy,
            "seed": self.seed,
            "won_once": self.won_once,
            "generation": self.generation,
            "state_version": self.state_version,
            "decision_pending": self.decision_pending,
            "elapsed_seconds": self.elapsed_seconds(),
            "last_error": self.last_error,
            "spawned_at": list(self.spawned_at) if self.spawned_at else None,
            "merged_positions": [list(position) for position in self.merged_positions],
            "last_direction": self.last_direction,
            "decision": None if self.decision is None else {
                "move": self.decision.move,
                "origin": self.decision.origin,
                "probabilities": self.decision.probabilities,
                "confidence": self.decision.confidence,
                "latency_ms": self.decision.latency_ms,
                "model": self.decision.model,
                "input_tokens": self.decision.input_tokens,
                "output_tokens": self.decision.output_tokens,
                "strategy": self.decision.strategy,
                "legal_move_count": self.decision.legal_move_count,
                "request_bytes": self.decision.request_bytes,
                "move_analysis": self.decision.move_analysis,
            },
            "history": [
                {
                    "number": item.number,
                    "move": item.move,
                    "score": item.score,
                    "score_gained": item.score_gained,
                    "origin": item.origin,
                    "latency_ms": item.latency_ms,
                    "confidence": item.confidence,
                    "strategy": item.strategy,
                    "created_at": item.created_at.isoformat(),
                }
                for item in reversed(self.history[-100:])
            ],
            "metrics": {
                "total_jev_calls": self.metrics.total_jev_calls,
                "successful_moves": self.metrics.successful_moves,
                "api_errors": self.metrics.api_errors,
                "average_latency_ms": self.metrics.average_latency_ms,
                "total_input_tokens": self.metrics.total_input_tokens,
                "total_output_tokens": self.metrics.total_output_tokens,
                "average_request_bytes": self.metrics.average_request_bytes,
            },
            "strategy_transitions": self.strategy_transitions[-20:],
        }

