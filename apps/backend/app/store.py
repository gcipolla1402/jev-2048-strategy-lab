from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from .game_state import GameSession


@dataclass
class SessionEntry:
    session: GameSession
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class GameStore:
    def __init__(self) -> None:
        self._entries: dict[str, SessionEntry] = {}
        self._lock = asyncio.Lock()

    async def create(self) -> SessionEntry:
        entry = SessionEntry(GameSession())
        async with self._lock:
            self._entries[entry.session.id] = entry
        return entry

    async def get(self, game_id: str) -> SessionEntry | None:
        async with self._lock:
            return self._entries.get(game_id)


store = GameStore()
