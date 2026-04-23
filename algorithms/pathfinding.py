import heapq
from components.map import DungeonMap

def astar(
    dungeon: DungeonMap,
    start: tuple[int, int],
    goal: tuple[int, int]
) -> list[tuple[int, int]]:
    if start == goal:
        return []

    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # (priority, current_pos)
    open_set = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    g_score: dict[tuple[int, int], int] = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

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
            tentative_g_score = g_score[current] + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                g_score[neighbor] = tentative_g_score
                priority = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (priority, neighbor))
                came_from[neighbor] = current

    return []
