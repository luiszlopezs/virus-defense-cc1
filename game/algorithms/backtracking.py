<<<<<<< HEAD
"""Bounded backtracking quarantine perimeter for Virus Defense."""
=======
from algorithms.grid_utils import get_boundary_nodes
from algorithms.grid import VIRUS, HEALTHY
>>>>>>> f5ca04229a493488b64acb04988893146be396e1

from __future__ import annotations

try:
    from algorithms.grid_utils import HEALTHY, INFECTED, get_boundary_nodes, get_cell, get_neighbors, rows_cols
except ImportError:  # pragma: no cover
    from game.algorithms.grid_utils import HEALTHY, INFECTED, get_boundary_nodes, get_cell, get_neighbors, rows_cols


def is_cluster_contained(grid: object, perimeter: set[tuple[int, int]]) -> bool:
    """
    Return True if infected nodes have no HEALTHY neighbor outside perimeter.
    """
    rows, cols = rows_cols(grid)

    for row in range(rows):
        for col in range(cols):
            if get_cell(grid, row, col) != INFECTED:
                continue
            for nr, nc in get_neighbors(grid, row, col):
                if get_cell(grid, nr, nc) == HEALTHY and (nr, nc) not in perimeter:
                    return False
    return True


def get_quarantine_perimeter(grid: object, limit: int = 12) -> list[tuple[int, int]]:
    """
    Find a small perimeter around the infection using bounded backtracking.

    The exact search over all boundary-node subsets is exponential. To keep the
    UI responsive in a 12x12 board, the candidate list is capped at 12 nodes,
    which means at most 2^12 = 4096 subsets are explored.
    """
    boundary_nodes = get_boundary_nodes(grid)
    if not boundary_nodes:
        return []

    boundary_nodes = boundary_nodes[:limit]
    best_solution: set[tuple[int, int]] | None = None

    def backtrack(index: int, current: set[tuple[int, int]]) -> None:
        nonlocal best_solution

        if best_solution is not None and len(current) >= len(best_solution):
            return

        if is_cluster_contained(grid, current):
            best_solution = set(current)
            return

        if index >= len(boundary_nodes):
            return

        node = boundary_nodes[index]

        current.add(node)
        backtrack(index + 1, current)

        current.remove(node)
        backtrack(index + 1, current)

    backtrack(0, set())
    return list(best_solution) if best_solution else []

<<<<<<< HEAD

# Backward-compatible name used by the original console prototype.
def backtracking_suggestion(grid: object, player: tuple[int, int] | None = None) -> tuple[int, int] | None:
    perimeter = get_quarantine_perimeter(grid)
    return perimeter[0] if perimeter else None
=======
    return list(best_solution) if best_solution else []

# =========================
# SUGGESTION FUNCTION (INTERFACE FOR GAME)
# =========================
def backtracking_suggestion(grid, player):
    """
    Provides the next move suggestion using the backtracking strategy.

    This function acts as the interface between the game loop
    and the backtracking algorithm.

    Steps:
    1. Compute the optimal quarantine perimeter.
    2. Select the closest node from that perimeter to the player.

    The distance used is Manhattan distance.

    Returns:
        tuple[int, int] | None
    """

    perimeter = get_quarantine_perimeter(grid)

    if not perimeter:
        return None

    best_node = None
    min_distance = float("inf")

    for r, c in perimeter:
        distance = abs(r - player[0]) + abs(c - player[1])

        if distance < min_distance:
            min_distance = distance
            best_node = (r, c)

    return best_node
>>>>>>> f5ca04229a493488b64acb04988893146be396e1
