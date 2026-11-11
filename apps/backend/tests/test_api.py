import asyncio
import threading

from fastapi.testclient import TestClient

from app.jev_service import JevDecision, JevServiceError
from app.main import app


client = TestClient(app)


class FakeStore:
    def __init__(self):
        self.items = []

    def append(self, collection, item):
        self.items.append((collection, item))


def test_create_manual_move_and_restart(monkeypatch):
    monkeypatch.setattr("app.routes.result_store", FakeStore())
    created = client.post("/api/games").json()
    game_id = created["id"]
    assert sum(value != 0 for row in created["board"] for value in row) == 2

    moved = None
    for direction in ("up", "down", "left", "right"):
        response = client.post(f"/api/games/{game_id}/move", json={"direction": direction})
        assert response.status_code == 200
        if response.json()["move_applied"]:
            moved = response.json()
            break
    assert moved is not None
    assert moved["total_moves"] == 1

    restarted = client.post(f"/api/games/{game_id}/restart").json()
    assert restarted["score"] == 0
    assert restarted["total_moves"] == 0
    assert restarted["generation"] == created["generation"] + 1


def test_jev_endpoint_with_fake_service(monkeypatch):
    monkeypatch.setattr("app.routes.result_store", FakeStore())
    created = client.post("/api/games").json()
    game_id = created["id"]

    async def fake_choose(board, score, legal_moves, recent_moves, strategy):
        chosen = legal_moves[0]
        return JevDecision(
            chosen, {chosen: 1.0}, 1.0, 12.5, "fake-test-model", 10, 2,
            strategy, len(legal_moves), 500, {},
        )

    monkeypatch.setattr("app.routes.jev_service.choose", fake_choose)
    client.post(f"/api/games/{game_id}/control", json={"action": "jev"})
    response = client.post(
        f"/api/games/{game_id}/jev/next",
        json={"generation": created["generation"], "state_version": created["state_version"]},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["decision"]["origin"] == "jev"
    assert result["decision"]["model"] == "fake-test-model"
    assert result["metrics"]["total_jev_calls"] == 1
    assert result["total_moves"] == 1


def test_strategy_change_pauses_and_records_transition(monkeypatch):
    monkeypatch.setattr("app.routes.result_store", FakeStore())
    created = client.post("/api/games").json()
    client.post(f"/api/games/{created['id']}/control", json={"action": "jev"})
    changed = client.post(
        f"/api/games/{created['id']}/strategy", json={"strategy": "strategic"}
    ).json()
    assert changed["strategy"] == "strategic"
    assert changed["status"] == "paused"
    assert changed["state_version"] == created["state_version"] + 1
    assert changed["strategy_transitions"][-1]["from"] == "basic"


def test_api_failure_never_creates_fallback_move(monkeypatch):
    monkeypatch.setattr("app.routes.result_store", FakeStore())
    created = client.post("/api/games").json()

    async def failing_choose(*args, **kwargs):
        raise JevServiceError("simulated API failure", attempted=True)

    monkeypatch.setattr("app.routes.jev_service.choose", failing_choose)
    client.post(f"/api/games/{created['id']}/control", json={"action": "jev"})
    response = client.post(
        f"/api/games/{created['id']}/jev/next",
        json={"generation": created["generation"], "state_version": created["state_version"]},
    )
    state = client.get(f"/api/games/{created['id']}").json()
    assert response.status_code == 503
    assert state["total_moves"] == 0
    assert state["status"] == "paused"
    assert state["metrics"]["api_errors"] == 1


def test_restart_discards_delayed_jev_response(monkeypatch):
    monkeypatch.setattr("app.routes.result_store", FakeStore())
    created = client.post("/api/games").json()
    started = threading.Event()
    release = threading.Event()

    async def delayed_choose(board, score, legal_moves, recent_moves, strategy):
        started.set()
        await asyncio.to_thread(release.wait)
        chosen = legal_moves[0]
        return JevDecision(
            chosen, {chosen: 1.0}, 1.0, 10.0, "fake-jev", 5, 1,
            strategy, len(legal_moves), 300, {},
        )

    monkeypatch.setattr("app.routes.jev_service.choose", delayed_choose)
    client.post(f"/api/games/{created['id']}/control", json={"action": "jev"})
    result = {}

    def request_move():
        result["response"] = client.post(
            f"/api/games/{created['id']}/jev/next",
            json={"generation": created["generation"], "state_version": created["state_version"]},
        )

    worker = threading.Thread(target=request_move)
    worker.start()
    assert started.wait(timeout=2)
    restarted = client.post(f"/api/games/{created['id']}/restart").json()
    release.set()
    worker.join(timeout=3)
    state = client.get(f"/api/games/{created['id']}").json()
    assert result["response"].status_code == 409
    assert state["generation"] == restarted["generation"]
    assert state["total_moves"] == 0

