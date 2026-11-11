import asyncio
from pathlib import Path

from app.benchmark import BenchmarkManager
from app.game_engine import Direction
from app.jev_service import JevDecision
from app.result_store import ResultStore


class FakeJev:
    async def choose(self, board, score, legal_moves, recent_moves, strategy):
        direction: Direction = legal_moves[0]
        return JevDecision(
            direction, {direction: 1.0}, 1.0, 1.5, "fake-jev", 5, 1,
            strategy, len(legal_moves), 300 if strategy == "basic" else 700, {},
        )


def test_benchmark_uses_paired_seeds_and_preserves_metrics(tmp_path: Path):
    async def scenario():
        store = ResultStore(tmp_path / "results.json")
        manager = BenchmarkManager(FakeJev(), store)
        job = await manager.start(1, max_moves=3, max_calls=3, max_seconds=30)
        await manager.tasks[job.id]
        data = store.snapshot()
        games = [row for row in data["games"] if row["benchmark_id"] == job.id]
        assert job.status == "completed"
        assert len(games) == 2
        assert {row["strategy"] for row in games} == {"basic", "strategic"}
        assert {row["seed"] for row in games} == {job.seeds[0]}
        assert all(row["moves"] <= 3 and row["jev_calls"] <= 3 for row in games)
        assert all(row["average_request_bytes"] > 0 for row in games)

    asyncio.run(scenario())


def test_benchmark_can_be_cancelled_without_fallback_move(tmp_path: Path):
    class SlowJev(FakeJev):
        async def choose(self, *args, **kwargs):
            await asyncio.sleep(0.03)
            return await super().choose(*args, **kwargs)

    async def scenario():
        store = ResultStore(tmp_path / "results.json")
        manager = BenchmarkManager(SlowJev(), store)
        job = await manager.start(1, max_moves=100, max_calls=100, max_seconds=30)
        await asyncio.sleep(0)
        await manager.cancel(job.id)
        await manager.tasks[job.id]
        assert job.status == "cancelled"
        assert job.completed_games < job.total_games

    asyncio.run(scenario())

