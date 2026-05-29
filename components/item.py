from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto

class ItemType(Enum):
    ATK_UP = auto()  # Red circle
    DEF_UP = auto()  # Yellow circle

@dataclass
class Item:
    x: int
    y: int
    item_type: ItemType

class ItemManager:
    def __init__(self):
        self.items: list[Item] = []

    def spawn(self, x: int, y: int, item_type: ItemType) -> None:
        self.items.append(Item(x, y, item_type))

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
