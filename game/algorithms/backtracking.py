"""Backtracking safe-path search for Virus Defense."""

from __future__ import annotations

try:  # Supports both: python game/main.py and python -m game.main
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, PATCHED, get_boundary_nodes, get_cell, get_neighbors, is_inside, rows_cols
except ImportError:  # pragma: no cover
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, PATCHED, get_boundary_nodes, get_cell, get_neighbors, is_inside, rows_cols

Position = tuple[int, int]


def is_walkable(grid: object, row: int, col: int) -> bool:
    """A safe route may pass through healthy or patched nodes, but never infected nodes."""
    return is_inside(grid, row, col) and get_cell(grid, row, col) in (HEALTHY, PATCHED)


def _ordered_neighbors(grid: object, current: Position, goal: Position) -> list[Position]:
    """Return valid neighbors ordered by proximity to the goal to reduce branching.
    Instead of exploring random or fixed paths (like always going left first even 
    if the goal is to the right), the algorithm prioritizes the nodes that essentially 
    bring you closer to the objective."""
    neighbors = [node for node in get_neighbors(grid, current[0], current[1]) if is_walkable(grid, node[0], node[1])]
    neighbors.sort(key=lambda node: abs(node[0] - goal[0]) + abs(node[1] - goal[1]))
    return neighbors


def find_safe_path(grid: object, start: Position, goal: Position) -> list[Position]:
    """
    Find a safe route from the player's current node to the goal using Backtracking.

    The algorithm recursively explores possible movements. If a branch reaches a
    dead end, it removes the last node from the partial path and returns to the
    previous decision point to try another neighbor. This is the core
    backtracking behavior.

    Rules:
    - Movement is orthogonal only: up, down, left, right.
    - INFECTED nodes are forbidden.
    - HEALTHY and PATCHED nodes are walkable.
    - Each node is visited at most once in the current search path to avoid
      cycles.

    Returns a list including start and goal when a route exists, or an empty
    list when the board is blocked.
    """
    rows, cols = rows_cols(grid)
    if not (0 <= start[0] < rows and 0 <= start[1] < cols):
        return []
    if not (0 <= goal[0] < rows and 0 <= goal[1] < cols):
        return []
    if not is_walkable(grid, start[0], start[1]) or not is_walkable(grid, goal[0], goal[1]):
        return []

    visited: set[Position] = set()
    path: list[Position] = []

    def dfs(node: Position) -> bool:
        if node in visited:
            return False
        if not is_walkable(grid, node[0], node[1]):
            return False

        visited.add(node)
        path.append(node)

        if node == goal:
            return True

        for nxt in _ordered_neighbors(grid, node, goal):
            if dfs(nxt):
                return True

        # Dead end: remove the node and return to the previous branch.
        path.pop() #If a path encounters a virus wall (INFECTED), it pops the last node from the stack and cleanly returns to the previous decision point to try another path.
        return False

    if dfs(start):
        return path.copy()
    return []


def next_step_from_path(path: list[Position]) -> Position | None:
    """Return the immediate movement suggested by a safe path."""
    if len(path) < 2:
        return None
    return path[1]


# Legacy quarantine helpers kept for compatibility with earlier reports/tests.
def is_cluster_contained(grid: object, perimeter: set[Position]) -> bool:
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            if get_cell(grid, row, col) != INFECTED:
                continue
            for nr, nc in get_neighbors(grid, row, col):
                if get_cell(grid, nr, nc) == HEALTHY and (nr, nc) not in perimeter:
                    return False
    return True


def get_quarantine_perimeter(grid: object, limit: int = 12) -> list[Position]:
    """
    Compatibility function from the previous design.

    The current game logic uses find_safe_path() for Backtracking. This perimeter
    function remains available so older tests or documentation examples do not
    crash, but the UI no longer uses it as the main Backtracking behavior.
    """
    boundary_nodes = get_boundary_nodes(grid)[:limit]
    if not boundary_nodes:
        return []

    best: set[Position] | None = None

    def search(index: int, current: set[Position]) -> None:
        nonlocal best
        if best is not None and len(current) >= len(best):
            return
        if is_cluster_contained(grid, current):
            best = set(current)
            return
        if index >= len(boundary_nodes):
            return

        current.add(boundary_nodes[index])
        search(index + 1, current)
        current.remove(boundary_nodes[index])
        search(index + 1, current)

    search(0, set())
    return list(best) if best is not None else []


# Backward-compatible console name.
def backtracking_suggestion(grid: object, player: Position, goal: Position | None = None) -> list[Position]:
    return find_safe_path(grid, player, goal or (GRID_SIZE - 1, GRID_SIZE - 1))