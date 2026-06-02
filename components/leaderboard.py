from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class ScoreEntry:
    name: str
    score: int
    time_seconds: int
    undo_used: int
    floors_cleared: int


class Leaderboard:
    """배열과 전체 정렬로 관리하는 점수표."""

    MAX_ENTRIES = 10
    SAVE_PATH = Path("data/leaderboard.json")

    def __init__(self, save_path: Path | str | None = None):
        self.save_path = Path(save_path) if save_path is not None else self.SAVE_PATH
        self.entries: list[ScoreEntry] = []
        self.load()

    def add(self, entry: ScoreEntry) -> int:
        self.entries.append(entry)
        self._sort()
        self.entries = self.entries[: self.MAX_ENTRIES]
        return self.get_rank(entry.score)

    def _sort(self) -> None:
        # 전체 정렬은 O(n log n)이다. 데이터가 아주 많다면 heap으로 top-k만
        # O(n log k)에 유지할 수 있지만, 여기서는 상위 10개라 명확성을 우선했다.
        self.entries.sort(key=lambda entry: entry.score, reverse=True)

    def get_rank(self, score: int) -> int:
        for index, entry in enumerate(self.entries, start=1):
            if score >= entry.score:
                return index
        return len(self.entries) + 1

    def save(self) -> None:
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(entry) for entry in self.entries]
        self.save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.save_path.exists():
            self.entries = []
            return
        try:
            payload = json.loads(self.save_path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            self.entries = []
            return
        self.entries = [ScoreEntry(**entry) for entry in payload]
        self._sort()
        self.entries = self.entries[: self.MAX_ENTRIES]

    def display_lines(self) -> list[str]:
        if not self.entries:
            return ["아직 기록이 없습니다."]
        return [
            f"{rank:>2}. {entry.name:<8} {entry.score:>6}  "
            f"클리어층={entry.floors_cleared} undo={entry.undo_used} 시간={entry.time_seconds}s"
            for rank, entry in enumerate(self.entries, start=1)
        ]

    @staticmethod
    def calculate_score(
        kill_xp: int,
        floors_cleared: int,
        undo_remaining: int,
        elapsed_seconds: int,
    ) -> int:
        return (
            kill_xp * 10
            + floors_cleared * 500
            + undo_remaining * 50
            + max(0, 3000 - elapsed_seconds) * 10
        )
