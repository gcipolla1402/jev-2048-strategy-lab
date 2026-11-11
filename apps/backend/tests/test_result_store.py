import json
from pathlib import Path

from app.result_store import ResultStore


def test_safe_json_storage_comparison_and_csv_export(tmp_path: Path):
    path = tmp_path / "results.json"
    store = ResultStore(path)
    row = {
        "id": "game-1", "strategy": "basic", "result": "game_over", "score": 100,
        "highest_tile": 32, "moves": 10, "jev_calls": 8, "average_latency_ms": 20,
        "duration_seconds": 4, "input_tokens": 50, "output_tokens": 10,
        "average_request_bytes": 400, "seed": 42, "reached_2048": False,
        "api_errors": 0, "interruption": None, "finished_at": "2026-01-01T00:00:00Z",
    }
    store.append("games", row)
    assert json.loads(path.read_text(encoding="utf-8"))["games"][0]["seed"] == 42
    assert not path.with_suffix(".tmp").exists()
    comparison = store.comparison()["strategies"]["basic"]
    assert comparison["average_score"] == 100
    assert comparison["total_calls"] == 8
    csv_text = store.export_csv()
    assert "strategy,result,score" in csv_text
    assert "basic,game_over,100" in csv_text

