from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from random import Random, SystemRandom
from time import monotonic
from typing import Any, Literal
from uuid import uuid4

from .domain import Strategy
from .game_engine import apply_move, has_won, highest_tile, legal_moves, new_board
from .jev_service import JevDecisionService, JevServiceError, jev_service
from .result_store import ResultStore, result_store

BenchmarkStatus = Literal["queued", "running", "cancelling", "cancelled", "completed", "failed"]


@dataclass
class BenchmarkJob:
    id: str
    games_per_mode: int
    seeds: list[int]
    max_moves: int
    max_calls: int
    max_seconds: int
    status: BenchmarkStatus = "queued"
    completed_games: int = 0
    total_games: int = 0
    current_strategy: Strategy | None = None
    current_seed: int | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "games_per_mode": self.games_per_mode,
            "seeds": self.seeds,
            "max_moves": self.max_moves,
            "max_calls": self.max_calls,
            "max_seconds": self.max_seconds,
            "status": self.status,
            "completed_games": self.completed_games,
            "total_games": self.total_games,
            "current_strategy": self.current_strategy,
            "current_seed": self.current_seed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class BenchmarkManager:
    def __init__(self, service: JevDecisionService = jev_service, store: ResultStore = result_store) -> None:
        self.service = service
        self.store = store
        self.jobs: dict[str, BenchmarkJob] = {}
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.lock = asyncio.Lock()
        self.max_games = int(os.getenv("BENCHMARK_MAX_GAMES_PER_MODE", "10"))
        self.default_max_moves = int(os.getenv("BENCHMARK_MAX_MOVES", "1000"))
        self.default_max_calls = int(os.getenv("BENCHMARK_MAX_CALLS", "1000"))
        self.default_max_seconds = int(os.getenv("BENCHMARK_MAX_SECONDS", "1800"))

    async def start(
        self,
        games_per_mode: int,
        max_moves: int | None = None,
        max_calls: int | None = None,
        max_seconds: int | None = None,
    ) -> BenchmarkJob:
        if games_per_mode not in {1, 5, 10} or games_per_mode > self.max_games:
            raise ValueError(f"games_per_mode must be 1, 5, or 10 and no more than {self.max_games}")
        async with self.lock:
            if any(job.status in {"queued", "running", "cancelling"} for job in self.jobs.values()):
                raise RuntimeError("Já existe um benchmark em andamento.")
            seeds = [SystemRandom().randrange(1, 2**31) for _ in range(games_per_mode)]
            job = BenchmarkJob(
                id=str(uuid4()),
                games_per_mode=games_per_mode,
                seeds=seeds,
                max_moves=min(max_moves or self.default_max_moves, self.default_max_moves),
                max_calls=min(max_calls or self.default_max_calls, self.default_max_calls),
                max_seconds=min(max_seconds or self.default_max_seconds, self.default_max_seconds),
                total_games=games_per_mode * 2,
            )
            self.jobs[job.id] = job
            self.tasks[job.id] = asyncio.create_task(self.run(job))
            return job

    async def cancel(self, job_id: str) -> BenchmarkJob | None:
        job = self.jobs.get(job_id)
        if job and job.status in {"queued", "running"}:
            job.status = "cancelling"
            job.cancel_event.set()
        return job

    async def run(self, job: BenchmarkJob) -> None:
        job.status = "running"
        job.started_at = datetime.now(UTC).isoformat()
        deadline = monotonic() + job.max_seconds
        try:
            for seed in job.seeds:
                for strategy in ("basic", "strategic"):
                    if job.cancel_event.is_set() or monotonic() >= deadline:
                        job.status = "cancelled"
                        return
                    job.current_seed = seed
                    job.current_strategy = strategy
                    await self._run_game(job, seed, strategy, deadline)
                    job.completed_games += 1
            job.status = "completed"
        except Exception as error:  # defensive boundary for the background task
            job.status = "failed"
            job.error = str(error)
        finally:
            job.finished_at = datetime.now(UTC).isoformat()
            job.current_seed = None
            job.current_strategy = None
            self.store.append("benchmarks", job.as_dict())

    async def _run_game(
        self,
        job: BenchmarkJob,
        seed: int,
        strategy: Strategy,
        deadline: float,
    ) -> None:
        rng = Random(seed)
        board = new_board(rng)
        score = 0
        moves_count = 0
        calls = 0
        errors = 0
        total_latency = 0.0
        input_tokens = 0
        output_tokens = 0
        request_bytes = 0
        recent_moves: list[str] = []
        started = monotonic()
        result = "game_over"
        interruption: str | None = None

        while legal_moves(board):
            if job.cancel_event.is_set():
                result, interruption = "interrupted", "cancelled"
                break
            if monotonic() >= deadline:
                result, interruption = "interrupted", "time_limit"
                break
            if moves_count >= job.max_moves:
                result = "move_limit"
                break
            legal = legal_moves(board)
            if len(legal) == 1:
                direction = legal[0]
            else:
                if calls >= job.max_calls:
                    result, interruption = "interrupted", "call_limit"
                    break
                try:
                    decision = await self.service.choose(board, score, legal, recent_moves, strategy)
                except JevServiceError as error:
                    errors += 1
                    if error.attempted:
                        calls += 1
                        self.store.append(
                            "calls",
                            {
                                "game_id": f"benchmark:{job.id}:{strategy}:{seed}",
                                "benchmark_id": job.id,
                                "strategy": strategy,
                                "legal_move_count": len(legal),
                                "error": str(error),
                                "attempted": True,
                                "created_at": datetime.now(UTC).isoformat(),
                            },
                        )
                    result, interruption = "interrupted", str(error)
                    break
                direction = decision.move
                calls += 1
                total_latency += decision.latency_ms
                input_tokens += decision.input_tokens or 0
                output_tokens += decision.output_tokens or 0
                request_bytes += decision.request_bytes
                self.store.append(
                    "calls",
                    {
                        "game_id": f"benchmark:{job.id}:{strategy}:{seed}",
                        "benchmark_id": job.id,
                        "strategy": strategy,
                        "direction": direction,
                        "legal_move_count": decision.legal_move_count,
                        "latency_ms": decision.latency_ms,
                        "confidence": decision.confidence,
                        "probabilities": decision.probabilities,
                        "input_tokens": decision.input_tokens,
                        "output_tokens": decision.output_tokens,
                        "model": decision.model,
                        "request_bytes": decision.request_bytes,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                )
                if job.cancel_event.is_set():
                    result, interruption = "interrupted", "cancelled"
                    break
            applied, _ = apply_move(board, direction, rng)
            if not applied.changed:
                result, interruption = "interrupted", "JEV returned a move that was no longer legal"
                errors += 1
                break
            board = applied.board
            score += applied.score_gained
            moves_count += 1
            recent_moves.append(direction)

        duration = round(monotonic() - started, 2)
        self.store.append(
            "games",
            {
                "game_id": f"benchmark:{job.id}:{strategy}:{seed}",
                "benchmark_id": job.id,
                "source": "benchmark",
                "strategy": strategy,
                "result": result,
                "score": score,
                "highest_tile": highest_tile(board),
                "moves": moves_count,
                "jev_calls": calls,
                "average_latency_ms": round(total_latency / calls, 1) if calls else None,
                "duration_seconds": duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "average_request_bytes": round(request_bytes / calls, 1) if calls else 0,
                "seed": seed,
                "reached_2048": has_won(board),
                "api_errors": errors,
                "interruption": interruption,
                "finished_at": datetime.now(UTC).isoformat(),
            },
        )


benchmark_manager = BenchmarkManager()

