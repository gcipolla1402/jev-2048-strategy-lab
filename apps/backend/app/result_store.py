from __future__ import annotations

import csv
import io
import json
import os
import threading
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "results.json"


class ResultStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()

    def _empty(self) -> dict[str, list[dict[str, Any]]]:
        return {"games": [], "calls": [], "benchmarks": []}

    def _read_unlocked(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        return {
            "games": list(data.get("games", [])),
            "calls": list(data.get("calls", [])),
            "benchmarks": list(data.get("benchmarks", [])),
        }

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def append(self, collection: str, item: dict[str, Any]) -> None:
        if collection not in {"games", "calls", "benchmarks"}:
            raise ValueError(f"Unknown result collection: {collection}")
        with self._lock:
            data = self._read_unlocked()
            data[collection].append(deepcopy(item))
            self._write_unlocked(data)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            return deepcopy(self._read_unlocked())

    def comparison(self) -> dict[str, Any]:
        games = self.snapshot()["games"]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for game in games:
            if game.get("strategy") in {"basic", "strategic"}:
                grouped[game["strategy"]].append(game)

        result: dict[str, Any] = {}
        for strategy in ("basic", "strategic"):
            rows = grouped[strategy]
            completed = [row for row in rows if row.get("result") in {"game_over", "won", "move_limit"}]
            calls = sum(int(row.get("jev_calls", 0)) for row in rows)
            result[strategy] = {
                "games": len(rows),
                "completed_games": len(completed),
                "average_score": round(sum(row.get("score", 0) for row in rows) / len(rows), 1) if rows else 0,
                "max_score": max((row.get("score", 0) for row in rows), default=0),
                "highest_tile": max((row.get("highest_tile", 0) for row in rows), default=0),
                "average_moves": round(sum(row.get("moves", 0) for row in rows) / len(rows), 1) if rows else 0,
                "average_duration_seconds": round(
                    sum(row.get("duration_seconds", 0) for row in rows) / len(rows), 1
                ) if rows else 0,
                "average_latency_ms": round(
                    sum((row.get("average_latency_ms") or 0) * row.get("jev_calls", 0) for row in rows) / calls,
                    1,
                ) if calls else 0,
                "total_calls": calls,
                "total_input_tokens": sum(row.get("input_tokens", 0) for row in rows),
                "reached_2048_rate": round(
                    100 * sum(bool(row.get("reached_2048")) for row in rows) / len(rows), 1
                ) if rows else 0,
                "api_errors": sum(row.get("api_errors", 0) for row in rows),
                "average_request_bytes": round(
                    sum(row.get("average_request_bytes", 0) * row.get("jev_calls", 0) for row in rows) / calls,
                    1,
                ) if calls else 0,
            }
        return {"strategies": result, "recent_games": list(reversed(games[-30:]))}

    def export_json(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2)

    def export_csv(self) -> str:
        output = io.StringIO(newline="")
        fields = [
            "game_id", "source", "benchmark_id", "strategy", "result", "score", "highest_tile",
            "moves", "jev_calls", "average_latency_ms", "duration_seconds", "input_tokens",
            "output_tokens", "average_request_bytes", "seed", "reached_2048", "api_errors",
            "interruption", "finished_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(self.snapshot()["games"])
        return output.getvalue()


result_store = ResultStore()

