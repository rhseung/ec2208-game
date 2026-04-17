from __future__ import annotations
import random
from components.map import DungeonMap, Room, Tile

MIN_ROOM_SIZE = 5
MAX_ROOM_SIZE = 12
MIN_PARTITION_SIZE = 8


class _BSPNode:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.left: _BSPNode | None = None
        self.right: _BSPNode | None = None
        self.room: Room | None = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def split(self) -> bool:
        if not self.is_leaf():
            return False

        # 비율에 따라 분할 방향 결정
        split_horizontal = random.random() > 0.5
        if self.w > self.h and self.w / self.h >= 1.25:
            split_horizontal = False
        elif self.h > self.w and self.h / self.w >= 1.25:
            split_horizontal = True

        max_pos = (self.h if split_horizontal else self.w) - MIN_PARTITION_SIZE
        if max_pos <= MIN_PARTITION_SIZE:
            return False

        pos = random.randint(MIN_PARTITION_SIZE, max_pos)
        if split_horizontal:
            self.left = _BSPNode(self.x, self.y, self.w, pos)
            self.right = _BSPNode(self.x, self.y + pos, self.w, self.h - pos)
        else:
            self.left = _BSPNode(self.x, self.y, pos, self.h)
            self.right = _BSPNode(self.x + pos, self.y, self.w - pos, self.h)
        return True


def _split_recursive(root: _BSPNode) -> None:
    stack = [root]
    while stack:
        node = stack.pop()
        if node.split():
            assert node.left and node.right
            stack.append(node.left)
            stack.append(node.right)


def _place_rooms(node: _BSPNode, dungeon: DungeonMap, rooms: list[Room]) -> None:
    if node.is_leaf():
        rw = random.randint(MIN_ROOM_SIZE, min(MAX_ROOM_SIZE, node.w - 2))
        rh = random.randint(MIN_ROOM_SIZE, min(MAX_ROOM_SIZE, node.h - 2))
        rx = node.x + random.randint(1, node.w - rw - 1)
        ry = node.y + random.randint(1, node.h - rh - 1)
        room = Room(rx, ry, rw, rh)
        node.room = room
        rooms.append(room)
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                dungeon.set_tile(x, y, Tile.FLOOR)
        return

    if node.left:
        _place_rooms(node.left, dungeon, rooms)
    if node.right:
        _place_rooms(node.right, dungeon, rooms)


def _nearest_room(node: _BSPNode) -> Room | None:
    if node.is_leaf():
        return node.room
    left = _nearest_room(node.left) if node.left else None
    right = _nearest_room(node.right) if node.right else None
    return left or right


def _connect_siblings(node: _BSPNode, dungeon: DungeonMap) -> None:
    if node.is_leaf():
        return
    if node.left:
        _connect_siblings(node.left, dungeon)
    if node.right:
        _connect_siblings(node.right, dungeon)

    a = _nearest_room(node.left) if node.left else None
    b = _nearest_room(node.right) if node.right else None
    if a and b:
        _carve_tunnel(dungeon, a.center(), b.center())


def _carve_tunnel(dungeon: DungeonMap, a: tuple[int, int], b: tuple[int, int]) -> None:
    x1, y1 = a
    x2, y2 = b
    if random.random() > 0.5:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            dungeon.set_tile(x, y1, Tile.FLOOR)
        for y in range(min(y1, y2), max(y1, y2) + 1):
            dungeon.set_tile(x2, y, Tile.FLOOR)
    else:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            dungeon.set_tile(x1, y, Tile.FLOOR)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            dungeon.set_tile(x, y2, Tile.FLOOR)


def _build_graph(rooms: list[Room]) -> dict[int, list[int]]:
    graph: dict[int, list[int]] = {i: [] for i in range(len(rooms))}
    for i in range(len(rooms) - 1):
        graph[i].append(i + 1)
        graph[i + 1].append(i)
    return graph


def generate_bsp(dungeon: DungeonMap) -> None:
    root = _BSPNode(0, 0, dungeon.width, dungeon.height)
    _split_recursive(root)

    rooms: list[Room] = []
    _place_rooms(root, dungeon, rooms)
    dungeon.rooms = rooms

    _connect_siblings(root, dungeon)
    dungeon.room_graph = _build_graph(rooms)

    if len(rooms) >= 2:
        sx, sy = rooms[0].center()
        dungeon.set_tile(sx, sy, Tile.STAIRS_UP)
        ex, ey = rooms[-1].center()
        dungeon.set_tile(ex, ey, Tile.STAIRS_DOWN)
