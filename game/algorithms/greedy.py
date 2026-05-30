"""Greedy local suggestion for Virus Defense."""

from __future__ import annotations

try:  # Supports both: python game/main.py and python -m game.main
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, get_cell, get_degree, get_neighbors
except ImportError:  # pragma: no cover - fallback for package execution
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, get_cell, get_degree, get_neighbors


def get_greedy_suggestion(grid: object, current_pos: tuple[int, int]) -> tuple[int, int] | None:
    """
    Select the best HEALTHY neighbor using a local Greedy criterion.

    The algorithm only evaluates the current player's immediate neighbors, so it
    is O(1): at most four candidates are inspected in a rectangular grid.

    Priority:
    1. Candidate must be HEALTHY.
    2. Higher geometric degree is better.
    3. Tie-breaker: closest to the center of the 12x12 board.
    4. If the tie persists, the first candidate found is kept.

    This local version keeps the game interactive and avoids letting the player
    jump to a globally optimal but narratively disconnected node.
    """
    center = ((GRID_SIZE - 1) / 2, (GRID_SIZE - 1) / 2)
    best_node: tuple[int, int] | None = None
    best_key: tuple[int, float] | None = None

    for row, col in get_neighbors(grid, current_pos[0], current_pos[1]):
        if get_cell(grid, row, col) != HEALTHY:
            continue

        degree = get_degree(row, col, GRID_SIZE)
        distance_to_center = abs(row - center[0]) + abs(col - center[1])
        candidate_key = (degree, -distance_to_center)

        if best_key is None or candidate_key > best_key:
            best_key = candidate_key
            best_node = (row, col)

    return best_node


# Backward-compatible name used by the original console prototype.
def greedy_suggestion(grid: object, player: tuple[int, int]) -> tuple[int, int] | None:
    return get_greedy_suggestion(grid, player)
