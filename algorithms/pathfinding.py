import heapq
from components.map import DungeonMap


def astar(
    dungeon: DungeonMap, start: tuple[int, int], goal: tuple[int, int]
) -> list[tuple[int, int]]:
    """최소 힙 기반 열린 집합과 closed set 가지치기를 사용하는 A* 경로 탐색.

    BFS는 모든 방향으로 같은 폭으로 확장하지만, A*는 맨해튼 휴리스틱으로
    플레이어 방향을 우선 탐색하므로 적 추적에 더 잘 맞는다.
    """
    if start == goal:
        return []

    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # (우선순위, 현재 좌표)
    open_set = [(0, start)]
    closed_set: set[tuple[int, int]] = set()
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    g_score: dict[tuple[int, int], int] = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current in closed_set:
            continue
        closed_set.add(current)

        if current == goal:
            path = []
            while current in came_from and current != start:
                path.append(current)
                prev = came_from[current]
                if prev is None:
                    break
                current = prev
            path.reverse()
            return path

        for neighbor in dungeon.get_neighbors(*current):
            if neighbor in closed_set:
                continue
            tentative_g_score = g_score[current] + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                g_score[neighbor] = tentative_g_score
                priority = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (priority, neighbor))
                came_from[neighbor] = current

    return []
