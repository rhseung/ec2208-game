from __future__ import annotations

from collections import deque
from typing import Generic, TypeVar


Actor = TypeVar("Actor")


class TurnManager(Generic[Actor]):
    """턴 순서를 관리하는 FIFO 큐.

    이 게임은 각 행위자가 라운드마다 한 번씩 행동하므로 일반 큐로 충분하다.
    캐릭터별 속도 차이를 추가한다면 이 파일에서 우선순위 큐로 확장하면 된다.
    """

    def __init__(self):
        self._queue: deque[Actor] = deque()

    def enqueue(self, actor: Actor) -> None:
        self._queue.append(actor)

    def dequeue(self) -> Actor:
        return self._queue.popleft()

    def remove(self, actor: Actor) -> None:
        self._queue = deque(item for item in self._queue if item != actor)

    def current(self) -> Actor:
        return self._queue[0]

    def advance(self) -> Actor:
        actor = self._queue.popleft()
        self._queue.append(actor)
        return self._queue[0]

    def reset(self, actors: list[Actor]) -> None:
        self._queue = deque(actors)

    def to_list(self) -> list[Actor]:
        return list(self._queue)
