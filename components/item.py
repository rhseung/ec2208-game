from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ItemType(StrEnum):
    ATK = "ATK"
    DEF = "DEF"
    HEAL = "HEAL"
    RANGE = "RANGE"


@dataclass
class Item:
    id: str
    name: str
    category: str
    value: int
    x: int
    y: int

    def copy(self) -> Item:
        return Item(
            id=self.id,
            name=self.name,
            category=self.category,
            value=self.value,
            x=self.x,
            y=self.y,
        )


class ItemManager:
    """던전 바닥에 놓인 아이템 목록.

    맵 위 오브젝트는 위치 탐색용 단순 리스트로 둔다.
    과제 요구사항인 연결 리스트 인벤토리는 components/inventory.py에 있다.
    """

    def __init__(self):
        self.items: list[Item] = []
        self._next_id = 1

    def spawn(self, x: int, y: int, item_type: ItemType) -> Item:
        item = Item(
            id=f"item-{self._next_id}",
            name=_name_for(item_type),
            category=item_type.value,
            value=_value_for(item_type),
            x=x,
            y=y,
        )
        self._next_id += 1
        self.items.append(item)
        return item

    def get_at(self, x: int, y: int) -> Item | None:
        for item in self.items:
            if item.x == x and item.y == y:
                return item
        return None

    def remove(self, item: Item) -> None:
        if item in self.items:
            self.items.remove(item)

    def get_all(self) -> list[Item]:
        return self.items

    def set_all(self, items: list[Item]) -> None:
        self.items = [item.copy() for item in items]
        self._next_id = _next_id_after(self.items)


def _name_for(item_type: ItemType) -> str:
    if item_type == ItemType.ATK:
        return "공격 부적"
    if item_type == ItemType.DEF:
        return "방어 부적"
    if item_type == ItemType.RANGE:
        return "확산 수정"
    return "회복 약초"


def _value_for(item_type: ItemType) -> int:
    if item_type == ItemType.ATK:
        return 2
    if item_type == ItemType.DEF:
        return 2
    if item_type == ItemType.RANGE:
        return 1
    return 12


def _next_id_after(items: list[Item]) -> int:
    highest = 0
    for item in items:
        try:
            highest = max(highest, int(item.id.rsplit("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return highest + 1
