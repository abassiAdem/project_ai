from __future__ import annotations

from typing import Dict, List


class ConversationMemory:
    def __init__(self) -> None:
        self._store: Dict[str, List[dict]] = {}

    def get(self, session_id: str) -> List[dict]:
        return self._store.get(session_id, []).copy()

    def append(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].append({"role": role, "content": content})


memory_store = ConversationMemory()
