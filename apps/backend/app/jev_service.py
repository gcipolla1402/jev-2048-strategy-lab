from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Mapping

from .domain import Strategy
from .game_engine import Board, Direction, empty_cells, highest_tile
from .move_analyzer import analyze_legal_moves

try:
    from typesafe_sdk import AsyncTypeSafeClient, Choice
except ImportError:  # pragma: no cover - exercised when dependencies are absent
    AsyncTypeSafeClient = None  # type: ignore[assignment]
    Choice = None  # type: ignore[assignment]


class JevServiceError(RuntimeError):
    def __init__(self, message: str, *, attempted: bool = False) -> None:
        super().__init__(message)
        self.attempted = attempted


@dataclass(frozen=True)
class JevDecision:
    move: Direction
    probabilities: dict[str, float]
    confidence: float | None
    latency_ms: float
    model: str
    input_tokens: int | None
    output_tokens: int | None
    strategy: Strategy
    legal_move_count: int
    request_bytes: int
    move_analysis: dict[str, Any]


def validate_decision_payload(
    choice: object,
    probabilities: Mapping[str, object] | None,
    confidence: object,
    legal_moves: list[Direction],
) -> tuple[Direction, dict[str, float], float | None]:
    if not isinstance(choice, str) or choice not in legal_moves:
        raise JevServiceError("O JEV retornou um movimento inválido para o tabuleiro atual.")

    normalized: dict[str, float] = {}
    for direction, value in (probabilities or {}).items():
        if direction not in legal_moves or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if math.isfinite(number) and 0 <= number <= 1:
            normalized[direction] = number

    normalized_confidence: float | None = None
    if isinstance(confidence, (int, float)):
        number = float(confidence)
        if math.isfinite(number) and 0 <= number <= 1:
            normalized_confidence = number

    return choice, normalized, normalized_confidence  # type: ignore[return-value]


BASIC_INSTRUCTIONS = (
    "You are controlling a 2048 game. Choose the most promising legal movement to reach tile 2048, "
    "maximize score, and avoid game over. Choose only from the supplied legal directions."
)

STRATEGIC_INSTRUCTIONS = (
    "You are controlling a 2048 game. Your objective is to reach tile 2048 while maximizing score "
    "and avoiding game over. You are given the current board and the simulated immediate consequences "
    "of every legal movement. Consider preserving available empty cells, creating useful merges, keeping "
    "high-value tiles organized, avoiding positions that restrict future movement, and preserving long-term "
    "opportunities. The future random tile spawn is unknown. Use the available factual information to choose "
    "the most promising legal movement. Return your choice among the legal directions."
)


def build_jev_request(
    board: Board,
    score: int,
    legal_moves: list[Direction],
    strategy: Strategy,
) -> tuple[dict[str, Any], dict[str, str], str, dict[str, Any], int]:
    if strategy not in {"basic", "strategic"}:
        raise ValueError(f"Unknown JEV strategy: {strategy}")
    criteria = {direction: f"Move all tiles {direction}" for direction in legal_moves}
    state: dict[str, Any] = {
        "board": [row[:] for row in board],
        "score": score,
        "highest_tile": highest_tile(board),
        "legal_moves": list(legal_moves),
    }
    analysis: dict[str, Any] = {}
    instructions = BASIC_INSTRUCTIONS
    if strategy == "strategic":
        analysis = analyze_legal_moves(board)
        state.update(
            {
                "empty_cells": len(empty_cells(board)),
                "move_analysis": analysis,
                "analysis_note": (
                    "Every alternative is simulated before the unknown random tile spawn. "
                    "These are calculated facts, not a ranking."
                ),
            }
        )
        instructions = STRATEGIC_INSTRUCTIONS
    request_bytes = len(
        json.dumps(
            {"state": state, "questions": {"next_move": {"instructions": instructions, "criteria": criteria}}},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return state, criteria, instructions, analysis, request_bytes


def _friendly_error(error: Exception) -> str:
    name = error.__class__.__name__.lower()
    message = str(error).lower()
    if "authentication" in name or "401" in message:
        return "A chave da API TypeSafe foi recusada (401). Verifique TYPESAFE_API_KEY."
    if "ratelimit" in name or "429" in message:
        return "O limite de chamadas da TypeSafe foi atingido (429). Aguarde e tente novamente."
    if "timeout" in name or "timed out" in message:
        return "A chamada ao JEV excedeu o tempo limite. Tente novamente."
    if "connection" in name:
        return "Não foi possível conectar à API TypeSafe. Verifique a rede e tente novamente."
    if "responsevalidation" in name:
        return "A API TypeSafe retornou uma resposta fora do formato esperado."
    return "A chamada ao JEV falhou temporariamente. Tente novamente."


class JevDecisionService:
    def __init__(self) -> None:
        self.model = os.getenv("TYPESAFE_MODEL", "jev-latest")
        self.timeout = float(os.getenv("TYPESAFE_TIMEOUT_SECONDS", "20"))

    async def choose(
        self,
        board: Board,
        score: int,
        legal_moves: list[Direction],
        recent_moves: list[str],
        strategy: Strategy = "basic",
    ) -> JevDecision:
        if not os.getenv("TYPESAFE_API_KEY"):
            raise JevServiceError(
                "TYPESAFE_API_KEY não está configurada. O modo manual continua disponível."
            )
        if AsyncTypeSafeClient is None or Choice is None:
            raise JevServiceError("O pacote typesafe-sdk não está instalado no backend.")
        if not legal_moves:
            raise JevServiceError("Não existem movimentos legais para o JEV escolher.")

        state, criteria, instructions, analysis, request_bytes = build_jev_request(
            board, score, legal_moves, strategy
        )
        started = perf_counter()
        try:
            async with AsyncTypeSafeClient(model=self.model, timeout=self.timeout) as client:
                response = await client.system_one(
                    state=state,
                    questions={
                        "next_move": Choice(
                            instructions=instructions,
                            criteria=criteria,
                        )
                    },
                )
        except JevServiceError:
            raise
        except Exception as error:
            raise JevServiceError(_friendly_error(error), attempted=True) from error

        latency_ms = round((perf_counter() - started) * 1000, 1)
        answer = response.choices["next_move"]
        try:
            move, probabilities, confidence = validate_decision_payload(
                answer.choice, answer.probabilities, answer.confidence, legal_moves
            )
        except JevServiceError as error:
            raise JevServiceError(str(error), attempted=True) from error
        usage = getattr(response, "usage", None)
        return JevDecision(
            move=move,
            probabilities=probabilities,
            confidence=confidence,
            latency_ms=latency_ms,
            model=str(getattr(response, "model", self.model)),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            strategy=strategy,
            legal_move_count=len(legal_moves),
            request_bytes=request_bytes,
            move_analysis=analysis,
        )


jev_service = JevDecisionService()

