"""
grid_utils.py — Core grid utilities for Virus Defense.

Provides constants, neighbour queries, boundary detection, and infection
counting on a **12×12** grid whose cells are in one of three states:

    HEALTHY  (0) — unaffected cell
    INFECTED (1) — cell carrying the virus
    PATCHED  (2) — cell immunised by the player

Adjacency is **4-connected** (up / down / left / right); diagonals are
never considered neighbours.

Complexity notes
────────────────
All helper functions run in O(1) per call (at most 4 neighbours) except
``get_boundary_nodes`` and ``count_infected`` which scan the full grid
in O(GRID_SIZE²).
"""

from __future__ import annotations

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
GRID_SIZE: int = 12
"""Side length of the square grid (12×12 = 144 cells)."""

HEALTHY: int = 0
"""Cell state: healthy / unaffected."""

INFECTED: int = 1
"""Cell state: carrying the virus."""

PATCHED: int = 2
"""Cell state: immunised by the player."""

# 4-connected direction offsets (row_delta, col_delta)
_DIRECTIONS: list[tuple[int, int]] = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# ──────────────────────────────────────────────
# Neighbour helpers
# ──────────────────────────────────────────────
def get_neighbors(grid: list[list[int]], row: int, col: int) -> list[tuple[int, int]]:
    """Return the valid 4-connected neighbour coordinates of *(row, col)*.

    Parameters
    ----------
    grid : list[list[int]]
        The 12×12 game grid (used only for bounds validation).
    row, col : int
        Coordinates of the query cell.

    Returns
    -------
    list[tuple[int, int]]
        List of ``(r, c)`` pairs for each in-bounds neighbour.  The list
        contains between 2 (corner) and 4 (interior) entries.  Order is
        deterministic: up, down, left, right.

    Examples
    --------
    >>> grid = [[0]*12 for _ in range(12)]
    >>> get_neighbors(grid, 0, 0)
    [(1, 0), (0, 1)]
    """
    neighbors: list[tuple[int, int]] = []
    for dr, dc in _DIRECTIONS:
        nr, nc = row + dr, col + dc
        if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
            neighbors.append((nr, nc))
    return neighbors


def get_degree(row: int, col: int) -> int:
    """Return the structural degree of *(row, col)* — i.e. how many valid
    neighbours it has regardless of their state.

    * **Corner** cells (e.g. (0,0)): degree = 2
    * **Edge** cells (e.g. (0,3)):   degree = 3
    * **Interior** cells:            degree = 4

    Parameters
    ----------
    row, col : int
        Coordinates of the query cell.

    Returns
    -------
    int
        Number of in-bounds neighbours (2, 3, or 4).

    Complexity
    ----------
    O(1).
    """
    degree = 4
    if row == 0 or row == GRID_SIZE - 1:
        degree -= 1
    if col == 0 or col == GRID_SIZE - 1:
        degree -= 1
    return degree


def get_healthy_degree(grid: list[list[int]], row: int, col: int) -> int:
    """Return the number of **HEALTHY** neighbours of *(row, col)*.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.
    row, col : int
        Coordinates of the query cell.

    Returns
    -------
    int
        Count of adjacent cells whose state equals ``HEALTHY`` (0).

    Complexity
    ----------
    O(1) — examines at most 4 neighbours.
    """
    count = 0
    for nr, nc in get_neighbors(grid, row, col):
        if grid[nr][nc] == HEALTHY:
            count += 1
    return count


# ──────────────────────────────────────────────
# Boundary / infection queries
# ──────────────────────────────────────────────
def get_boundary_nodes(grid: list[list[int]]) -> list[tuple[int, int]]:
    """Return all **HEALTHY** cells that have at least one **INFECTED**
    neighbour — i.e. the *infection boundary*.

    These are the cells the virus will try to spread into on the next
    turn, and therefore the prime candidates for patching.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.

    Returns
    -------
    list[tuple[int, int]]
        Sorted list of ``(row, col)`` boundary nodes.

    Complexity
    ----------
    O(GRID_SIZE²) — full grid scan, constant work per cell.
    """
    boundary: list[tuple[int, int]] = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] != HEALTHY:
                continue
            for nr, nc in get_neighbors(grid, r, c):
                if grid[nr][nc] == INFECTED:
                    boundary.append((r, c))
                    break  # one infected neighbour is enough
    return boundary


def is_infected_cluster_empty(grid: list[list[int]]) -> bool:
    """Return ``True`` if **no** cell in *grid* is INFECTED.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.

    Returns
    -------
    bool
        ``True`` when every cell is either HEALTHY or PATCHED.

    Complexity
    ----------
    O(GRID_SIZE²) worst-case; short-circuits on the first INFECTED cell.
    """
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == INFECTED:
                return False
    return True


def is_virus_contained(grid: list[list[int]]) -> bool:
    """Return ``True`` if no INFECTED cell has a HEALTHY neighbor.

    The virus is "contained" when every infected node is surrounded
    only by other infected or patched nodes, meaning it cannot spread
    any further.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.

    Returns
    -------
    bool
        ``True`` when no INFECTED cell can spread to a HEALTHY cell.

    Complexity
    ----------
    O(GRID_SIZE²) — checks each INFECTED cell's neighbors.
    """
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == INFECTED:
                for nr, nc in get_neighbors(grid, r, c):
                    if grid[nr][nc] == HEALTHY:
                        return False
    return True


def count_infected(grid: list[list[int]]) -> int:
    """Return the total number of INFECTED cells in *grid*.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.

    Returns
    -------
    int
        Count of cells whose state equals ``INFECTED`` (1).

    Complexity
    ----------
    O(GRID_SIZE²).
    """
    total = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == INFECTED:
                total += 1
    return total


# ──────────────────────────────────────────────
# Pathfinding
# ──────────────────────────────────────────────
def find_safe_path(
    grid: list[list[int]],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """Find the shortest safe path from *start* to *goal* using BFS.

    The path avoids INFECTED cells and only traverses HEALTHY or PATCHED
    cells.  Returns an empty list when no path exists.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.
    start : tuple[int, int]
        ``(row, col)`` of the starting cell (player position).
    goal : tuple[int, int]
        ``(row, col)`` of the destination cell (goal position).

    Returns
    -------
    list[tuple[int, int]]
        Ordered list of ``(row, col)`` from *start* to *goal* inclusive.
        Empty list if no safe path exists.

    Complexity
    ----------
    O(GRID_SIZE²) — BFS visits each cell at most once.
    """
    from collections import deque

    sr, sc = start
    gr, gc = goal

    if start == goal:
        return [start]

    visited: set[tuple[int, int]] = {start}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue: deque[tuple[int, int]] = deque([start])

    while queue:
        r, c = queue.popleft()
        for nr, nc in get_neighbors(grid, r, c):
            if (nr, nc) in visited:
                continue
            if grid[nr][nc] == INFECTED:
                continue
            visited.add((nr, nc))
            parent[(nr, nc)] = (r, c)
            if (nr, nc) == goal:
                # Reconstruct path
                path = []
                cur = goal
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            queue.append((nr, nc))

    return []  # No path found


# ──────────────────────────────────────────────
# Quick smoke-test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # Build a small test scenario
    test_grid: list[list[int]] = [[HEALTHY] * GRID_SIZE for _ in range(GRID_SIZE)]

    # Infect a 2×2 block near the centre
    test_grid[5][5] = INFECTED
    test_grid[5][6] = INFECTED
    test_grid[6][5] = INFECTED
    test_grid[6][6] = INFECTED

    # Patch one cell on the boundary
    test_grid[4][5] = PATCHED

    print("=== Grid Utils — Test Examples ===\n")
    print(f"Grid size         : {GRID_SIZE}x{GRID_SIZE}")
    print(f"Infected count    : {count_infected(test_grid)}")
    print(f"Cluster empty?    : {is_infected_cluster_empty(test_grid)}")

    print(f"\nNeighbours of (0,0)  : {get_neighbors(test_grid, 0, 0)}")
    print(f"Neighbours of (5,5)  : {get_neighbors(test_grid, 5, 5)}")

    print(f"\nDegree of (0,0)      : {get_degree(0, 0)}   (corner)")
    print(f"Degree of (0,3)      : {get_degree(0, 3)}   (edge)")
    print(f"Degree of (5,5)      : {get_degree(5, 5)}   (interior)")

    print(f"\nHealthy degree (4,5) : {get_healthy_degree(test_grid, 4, 5)}  (patched cell)")
    print(f"Healthy degree (5,4) : {get_healthy_degree(test_grid, 5, 4)}  (next to infection)")

    boundary = get_boundary_nodes(test_grid)
    print(f"\nBoundary nodes ({len(boundary)}): {boundary}")
