from dataclasses import dataclass
from typing import Iterator

from components.item import Item, ItemType


@dataclass
class ItemNode:
    item: Item
    next: "ItemNode | None" = None


@dataclass(frozen=True)
class InventoryStack:
    """화면에 표시할 같은 종류 아이템 묶음."""

    item: Item
    count: int


class ItemLinkedList:
    """인벤토리 카테고리 하나를 담당하는 단일 연결 리스트."""

    def __init__(self):
        self.head: ItemNode | None = None

    def append(self, item: Item) -> None:
        node = ItemNode(item.copy())
        if self.head is None:
            self.head = node
            return

        current = self.head
        while current.next is not None:
            current = current.next
        current.next = node

    def remove(self, item_id: str) -> Item | None:
        previous: ItemNode | None = None
        current = self.head
        while current is not None:
            if current.item.id == item_id:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next
                return current.item
            previous = current
            current = current.next
        return None

    def find(self, item_id: str) -> Item | None:
        for item in self:
            if item.id == item_id:
                return item
        return None

    def to_list(self) -> list[Item]:
        return [item.copy() for item in self]

    def __iter__(self) -> Iterator[Item]:
        current = self.head
        while current is not None:
            yield current.item
            current = current.next


class Inventory:
    """카테고리 이름을 연결 리스트에 매핑하는 인벤토리.

    dict는 카테고리 접근을 평균 O(1)에 처리하고, 각 카테고리 내부는
    연결 리스트로 관리해서 EC2208 인벤토리 자료구조 설명이 명확하다.
    """

    def __init__(self):
        self.categories: dict[str, ItemLinkedList] = {
            ItemType.ATK.value: ItemLinkedList(),
            ItemType.DEF.value: ItemLinkedList(),
            ItemType.HEAL.value: ItemLinkedList(),
            ItemType.RANGE.value: ItemLinkedList(),
        }

    def add(self, item: Item) -> None:
        item_copy = item.copy()
        item_copy.x = -1
        item_copy.y = -1
        self.categories.setdefault(item_copy.category, ItemLinkedList()).append(item_copy)

    def use(self, item_id: str) -> Item | None:
        for linked_list in self.categories.values():
            item = linked_list.remove(item_id)
            if item is not None:
                return item
        return None

    def find(self, item_id: str) -> Item | None:
        for linked_list in self.categories.values():
            item = linked_list.find(item_id)
            if item is not None:
                return item
        return None

    def to_list(self) -> list[Item]:
        result: list[Item] = []
        for category in (ItemType.ATK.value, ItemType.DEF.value, ItemType.HEAL.value, ItemType.RANGE.value):
            result.extend(self.categories.get(category, ItemLinkedList()).to_list())
        return result

    def stack_entries(self) -> list[InventoryStack]:
        stacks: dict[tuple[str, str, int], list[Item]] = {}
        for item in self.to_list():
            key = (item.category, item.name, item.value)
            stacks.setdefault(key, []).append(item)

        result: list[InventoryStack] = []
        for category in (ItemType.ATK.value, ItemType.DEF.value, ItemType.HEAL.value, ItemType.RANGE.value):
            for (item_category, _name, _value), items in stacks.items():
                if item_category == category:
                    result.append(InventoryStack(items[0], len(items)))
        return result

    def replace_all(self, items: list[Item]) -> None:
        self.categories = {
            ItemType.ATK.value: ItemLinkedList(),
            ItemType.DEF.value: ItemLinkedList(),
            ItemType.HEAL.value: ItemLinkedList(),
            ItemType.RANGE.value: ItemLinkedList(),
        }
        for item in items:
            self.add(item)

    def display_lines(self) -> list[str]:
        stacks = self.stack_entries()
        if not stacks:
            return ["인벤토리가 비어 있습니다."]
        return [
            f"{index + 1}. {stack.item.name} x{stack.count} [{stack.item.category}] +{stack.item.value}"
            for index, stack in enumerate(stacks)
        ]
