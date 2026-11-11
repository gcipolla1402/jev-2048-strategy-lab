from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from .benchmark import benchmark_manager
from .game_engine import Direction, apply_move, highest_tile, legal_moves
from .game_state import DecisionSnapshot, HistoryEntry
from .jev_service import JevDecision, JevServiceError, jev_service
from .result_store import result_store
from .schemas import BenchmarkRequest, ControlRequest, JevMoveRequest, MoveRequest, StrategyRequest
from .store import SessionEntry, store

router = APIRouter(prefix="/api")


async def _entry_or_404(game_id: str) -> SessionEntry:
    entry = await store.get(game_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Partida não encontrada.")
    return entry


def _apply(entry: SessionEntry, direction: Direction, origin: str, decision: JevDecision | None = None) -> bool:
    game = entry.session
    result, spawned_at = apply_move(game.board, direction, game.rng)
    if not result.changed:
        return False
    game.status = "playing"
    game.board = result.board
    game.score += result.score_gained
    game.best_score = max(game.best_score, game.score)
    game.total_moves += 1
    game.state_version += 1
    game.metrics.successful_moves += 1
    game.last_direction = direction
    game.spawned_at = spawned_at
    game.merged_positions = result.merged_positions
    game.history.append(
        HistoryEntry(
            number=game.total_moves,
            move=direction,
            score=game.score,
            score_gained=result.score_gained,
            origin=origin,  # type: ignore[arg-type]
            latency_ms=decision.latency_ms if decision else None,
            confidence=decision.confidence if decision else None,
            strategy=game.strategy if origin in {"jev", "forced"} else None,
        )
    )
    game.last_error = None
    game.refresh_status()
    if game.status == "game_over":
        _record_game(game, "game_over")
    return True


def _game_result(game: Any, result: str, interruption: str | None = None, source: str = "live") -> dict[str, Any]:
    strategy = game.strategy
    if game.strategy_transitions and any(item.get("move_number", 0) > 0 for item in game.strategy_transitions):
        strategy = "mixed"
    return {
        "game_id": game.id,
        "source": source,
        "strategy": strategy,
        "result": result,
        "score": game.score,
        "highest_tile": highest_tile(game.board),
        "moves": game.total_moves,
        "jev_calls": game.metrics.total_jev_calls,
        "average_latency_ms": game.metrics.average_latency_ms,
        "duration_seconds": game.elapsed_seconds(),
        "input_tokens": game.metrics.total_input_tokens,
        "output_tokens": game.metrics.total_output_tokens,
        "average_request_bytes": game.metrics.average_request_bytes or 0,
        "seed": game.seed,
        "reached_2048": game.won_once,
        "api_errors": game.metrics.api_errors,
        "interruption": interruption,
        "finished_at": datetime.now(UTC).isoformat(),
    }


def _record_game(game: Any, result: str, interruption: str | None = None) -> None:
    if game.result_saved:
        return
    result_store.append("games", _game_result(game, result, interruption))
    game.result_saved = True


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/results")
async def get_results() -> dict[str, Any]:
    snapshot = result_store.snapshot()
    return {
        "comparison": result_store.comparison(),
        "games": list(reversed(snapshot["games"][-50:])),
        "benchmarks": list(reversed(snapshot["benchmarks"][-20:])),
    }


@router.get("/results/export")
async def export_results(format: str = "json") -> Response:
    if format == "json":
        import json

        body = json.dumps(result_store.snapshot(), ensure_ascii=False, indent=2)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="jev-2048-results.json"'},
        )
    if format == "csv":
        return Response(
            content=result_store.export_csv(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="jev-2048-results.csv"'},
        )
    raise HTTPException(status_code=400, detail="Formato de exportação inválido. Use json ou csv.")


@router.post("/benchmarks", status_code=status.HTTP_202_ACCEPTED)
async def start_benchmark(request: BenchmarkRequest) -> dict[str, Any]:
    try:
        job = await benchmark_manager.start(
            request.games_per_mode,
            request.max_moves,
            request.max_calls,
            request.max_seconds,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return job.as_dict()


@router.get("/benchmarks/{job_id}")
async def get_benchmark(job_id: str) -> dict[str, Any]:
    job = benchmark_manager.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Benchmark não encontrado.")
    return {**job.as_dict(), "comparison": result_store.comparison()}


@router.post("/benchmarks/{job_id}/cancel")
async def cancel_benchmark(job_id: str) -> dict[str, Any]:
    job = await benchmark_manager.cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Benchmark não encontrado.")
    return job.as_dict()


@router.post("/games", status_code=status.HTTP_201_CREATED)
async def create_game() -> dict[str, Any]:
    entry = await store.create()
    return entry.session.as_dict()


@router.get("/games/{game_id}")
async def get_game(game_id: str) -> dict[str, Any]:
    entry = await _entry_or_404(game_id)
    async with entry.lock:
        return entry.session.as_dict()


@router.post("/games/{game_id}/move")
async def manual_move(game_id: str, request: MoveRequest) -> dict[str, Any]:
    entry = await _entry_or_404(game_id)
    async with entry.lock:
        game = entry.session
        if game.mode != "manual":
            raise HTTPException(status_code=409, detail="Ative o modo manual antes de jogar.")
        if game.status == "game_over":
            raise HTTPException(status_code=409, detail="A partida terminou. Reinicie para continuar.")
        changed = _apply(entry, request.direction, "manual")
        if not changed:
            return {**game.as_dict(), "move_applied": False}
        return {**game.as_dict(), "move_applied": True}


@router.post("/games/{game_id}/control")
async def control_game(game_id: str, request: ControlRequest) -> dict[str, Any]:
    entry = await _entry_or_404(game_id)
    async with entry.lock:
        game = entry.session
        if request.action == "pause":
            game.control_token += 1
            game.status = "paused"
        elif request.action == "manual":
            game.control_token += 1
            game.mode = "manual"
            if game.status != "game_over":
                game.status = "playing"
        elif request.action in {"jev", "resume"}:
            game.mode = "jev"
            if game.status != "game_over":
                game.status = "playing"
        return game.as_dict()


@router.post("/games/{game_id}/strategy")
async def change_strategy(game_id: str, request: StrategyRequest) -> dict[str, Any]:
    entry = await _entry_or_404(game_id)
    async with entry.lock:
        game = entry.session
        if game.strategy == request.strategy:
            return game.as_dict()
        previous = game.strategy
        game.control_token += 1
        game.state_version += 1
        if game.status != "game_over":
            game.status = "paused"
        game.strategy = request.strategy
        game.strategy_transitions.append(
            {
                "from": previous,
                "to": request.strategy,
                "move_number": game.total_moves,
                "changed_at": datetime.now(UTC).isoformat(),
            }
        )
        return game.as_dict()


@router.post("/games/{game_id}/restart")
async def restart_game(game_id: str) -> dict[str, Any]:
    entry = await _entry_or_404(game_id)
    async with entry.lock:
        game = entry.session
        if game.total_moves > 0:
            _record_game(game, "interrupted", "restart")
        game.reset_round()
        return game.as_dict()


@router.post("/games/{game_id}/jev/next")
async def jev_next_move(game_id: str, request: JevMoveRequest) -> dict[str, Any]:
    entry = await _entry_or_404(game_id)
    async with entry.lock:
        game = entry.session
        if request.generation != game.generation:
            raise HTTPException(status_code=409, detail="Esta resposta pertence a uma partida anterior.")
        if request.state_version != game.state_version:
            raise HTTPException(status_code=409, detail="O estado da partida mudou antes desta decisão.")
        if game.mode != "jev":
            raise HTTPException(status_code=409, detail="O modo JEV não está ativo.")
        if game.status == "paused":
            raise HTTPException(status_code=409, detail="A partida está pausada.")
        if game.status == "game_over":
            raise HTTPException(status_code=409, detail="A partida terminou.")
        if game.decision_pending:
            raise HTTPException(status_code=409, detail="Já existe uma decisão do JEV em andamento.")

        if request.generation != game.generation:
            raise HTTPException(status_code=409, detail="A partida foi reiniciada. Atualize o estado antes da próxima jogada.")
        moves = legal_moves(game.board)
        if not moves:
            game.status = "game_over"
            return game.as_dict()
        if len(moves) == 1:
            direction = moves[0]
            game.decision = DecisionSnapshot(
                direction,
                "forced",
                {},
                None,
                None,
                "jogada-forçada",
                strategy=game.strategy,
                legal_move_count=1,
            )
            _apply(entry, direction, "forced")
            return game.as_dict()

        game.decision_pending = True
        request_id = str(datetime.now(UTC).timestamp()) + ":" + game.id + ":" + str(game.state_version)
        game.pending_request_id = request_id
        captured_generation = game.generation
        captured_state_version = game.state_version
        captured_token = game.control_token
        board = [row[:] for row in game.board]
        score_value = game.score
        recent_moves = [item.move for item in game.history[-8:]]
        strategy = game.strategy

    try:
        decision = await jev_service.choose(board, score_value, moves, recent_moves, strategy)
    except JevServiceError as error:
        async with entry.lock:
            game = entry.session
            if game.pending_request_id == request_id:
                game.decision_pending = False
                game.pending_request_id = None
            if game.generation == captured_generation:
                game.status = "paused"
                game.last_error = str(error)
                if error.attempted:
                    game.metrics.total_jev_calls += 1
                game.metrics.api_errors += 1
                result_store.append(
                    "calls",
                    {
                        "game_id": game.id,
                        "strategy": strategy,
                        "legal_move_count": len(moves),
                        "error": str(error),
                        "attempted": error.attempted,
                        "created_at": datetime.now(UTC).isoformat(),
                    },
                )
        raise HTTPException(status_code=503, detail=str(error)) from error

    async with entry.lock:
        game = entry.session
        if game.pending_request_id == request_id:
            game.decision_pending = False
            game.pending_request_id = None
        if (
            game.generation != captured_generation
            or game.state_version != captured_state_version
            or game.control_token != captured_token
            or game.strategy != strategy
        ):
            raise HTTPException(status_code=409, detail="A decisão foi descartada porque a partida mudou ou foi pausada.")
        game.metrics.record_call(
            decision.latency_ms,
            decision.input_tokens,
            decision.output_tokens,
            decision.request_bytes,
        )
        game.decision = DecisionSnapshot(
            decision.move,
            "jev",
            decision.probabilities,
            decision.confidence,
            decision.latency_ms,
            decision.model,
            decision.input_tokens,
            decision.output_tokens,
            decision.strategy,
            decision.legal_move_count,
            decision.request_bytes,
            decision.move_analysis,
        )
        result_store.append(
            "calls",
            {
                "game_id": game.id,
                "strategy": decision.strategy,
                "direction": decision.move,
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
        if not _apply(entry, decision.move, "jev", decision):
            game.status = "paused"
            game.last_error = "O movimento escolhido pelo JEV deixou de ser válido."
            game.metrics.api_errors += 1
            raise HTTPException(status_code=409, detail=game.last_error)
        return game.as_dict()

