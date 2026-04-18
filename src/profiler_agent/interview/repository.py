from __future__ import annotations

import asyncio

from profiler_agent.models import InterviewState


class InterviewRepository:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._states: dict[str, InterviewState] = {}

    async def get(self, task_id: str) -> InterviewState | None:
        async with self._lock:
            return self._states.get(task_id)

    async def save(self, task_id: str, state: InterviewState) -> None:
        async with self._lock:
            self._states[task_id] = state

    async def delete(self, task_id: str) -> None:
        async with self._lock:
            self._states.pop(task_id, None)
