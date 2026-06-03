"""
greedy.py — Global Greedy patch-suggestion algorithm for Virus Defense.

Strategy
────────
Scans ALL boundary nodes (HEALTHY cells adjacent to at least one INFECTED
cell) and recommends the single best cell to patch. This gives the player
a useful suggestion regardless of where their current position is.

Selection criteria (in priority order):

1. **Highest healthy_degree** — the candidate whose own neighbourhood
   contains the most HEALTHY cells. Patching such a node maximises the
   "shielding" effect: it blocks the most potential future infection
   paths in one move.

2. **Closest to centre (5, 5)** — among ties, the candidate whose
   Manhattan distance to the grid centre is smallest is preferred.

3. **First found** — if candidates are still tied after both criteria
   the one encountered first is returned.

Complexity
─────────
O(GRID_SIZE^2) — scans the full grid for boundary nodes, then evaluates
each candidate's healthy_degree (O(1) per candidate).
"""

from __future__ import annotations

from .grid_utils import (
    GRID_SIZE,
    HEALTHY,
    INFECTED,
    get_healthy_degree,
    get_neighbors,
    get_boundary_nodes,
)

_CENTER: tuple[int, int] = (5, 5)


def _manhattan_to_center(row: int, col: int) -> int:
    return abs(row - _CENTER[0]) + abs(col - _CENTER[1])


def get_greedy_suggestion(
    grid: list[list[int]],
    current_pos: tuple[int, int],
) -> tuple[int, int] | None:
    """Suggest the best HEALTHY boundary node to patch globally.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12x12 game grid.
    current_pos : tuple[int, int]
        Current player position (unused in global mode, kept for API compat).

    Returns
    -------
    tuple[int, int] | None
        (row, col) of the recommended cell, or None if no boundary exists.
    """
    boundary = get_boundary_nodes(grid)

    if not boundary:
        return None

    best: tuple[int, int] | None = None
    best_hdeg: int = -1
    best_dist: int = GRID_SIZE * 2

    for r, c in boundary:
        hdeg = get_healthy_degree(grid, r, c)
        dist = _manhattan_to_center(r, c)

        if hdeg > best_hdeg or (hdeg == best_hdeg and dist < best_dist):
            best = (r, c)
            best_hdeg = hdeg
            best_dist = dist

    return best
