<<<<<<< HEAD
"""
Utilities for the Virus Defense grid.

The UI works with a plain 12x12 list of lists because the C++ engine will
exchange the board through JSON. These helpers also accept the older Grid class
used by the first console prototype, so the existing algorithm code remains
compatible.
"""

from __future__ import annotations

from typing import Iterable

GRID_SIZE = 12
HEALTHY = 0
INFECTED = 1
VIRUS = INFECTED  # Alias kept for compatibility with the first prototype.
PATCHED = 2

Position = tuple[int, int]


def normalize_grid(grid: object | None, size: int = GRID_SIZE) -> list[list[int]]:
    """
    Return a valid square matrix.

    If the JSON state is missing, malformed, or has the wrong dimensions, this
    function creates a default 12x12 board with one infected node in the center.
    """
    if isinstance(grid, list) and len(grid) == size:
        normalized: list[list[int]] = []
        for row in grid:
            if not isinstance(row, list) or len(row) != size:
                break
            normalized.append([_safe_cell(value) for value in row])
        if len(normalized) == size:
            return normalized

    matrix = [[HEALTHY for _ in range(size)] for _ in range(size)]
    center = size // 2 - 1 if size % 2 == 0 else size // 2
    matrix[center][center] = INFECTED
    return matrix


def _safe_cell(value: object) -> int:
    try:
        cell = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return HEALTHY
    return cell if cell in (HEALTHY, INFECTED, PATCHED) else HEALTHY


def rows_cols(grid: object) -> tuple[int, int]:
    if hasattr(grid, "rows") and hasattr(grid, "cols"):
        return int(getattr(grid, "rows")), int(getattr(grid, "cols"))
    matrix = grid  # type: ignore[assignment]
    rows = len(matrix) if isinstance(matrix, list) else GRID_SIZE
    cols = len(matrix[0]) if rows and isinstance(matrix, list) and isinstance(matrix[0], list) else GRID_SIZE
    return rows, cols


def is_inside(grid: object, row: int, col: int) -> bool:
    rows, cols = rows_cols(grid)
    return 0 <= row < rows and 0 <= col < cols


def get_cell(grid: object, row: int, col: int) -> int:
    if not is_inside(grid, row, col):
        return -1
    if hasattr(grid, "get_cell"):
        return int(grid.get_cell(row, col))  # type: ignore[attr-defined]
    return int(grid[row][col])  # type: ignore[index]


def set_cell(grid: object, row: int, col: int, value: int) -> None:
    if not is_inside(grid, row, col):
        return
    if hasattr(grid, "set_cell"):
        grid.set_cell(row, col, value)  # type: ignore[attr-defined]
    else:
        grid[row][col] = value  # type: ignore[index]


def get_neighbors(grid: object, row: int, col: int) -> list[Position]:
    """Return valid orthogonal neighbors: up, down, left, right."""
    candidates = ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1))
    return [(r, c) for r, c in candidates if is_inside(grid, r, c)]


def get_degree(row: int, col: int, size: int = GRID_SIZE) -> int:
    """Return the geometric degree of a node in a square grid."""
    degree = 4
    if row in (0, size - 1):
        degree -= 1
    if col in (0, size - 1):
        degree -= 1
    return degree


def get_boundary_nodes(grid: object) -> list[Position]:
    """Return HEALTHY nodes that are adjacent to at least one infected node."""
    rows, cols = rows_cols(grid)
    boundary: list[Position] = []

    for row in range(rows):
        for col in range(cols):
            if get_cell(grid, row, col) != HEALTHY:
                continue
            if any(get_cell(grid, nr, nc) == INFECTED for nr, nc in get_neighbors(grid, row, col)):
                boundary.append((row, col))

    return boundary


def is_infected_cluster_empty(grid: object) -> bool:
    rows, cols = rows_cols(grid)
    return all(get_cell(grid, row, col) != INFECTED for row in range(rows) for col in range(cols))


def count_infected(grid: object) -> int:
    rows, cols = rows_cols(grid)
    return sum(1 for row in range(rows) for col in range(cols) if get_cell(grid, row, col) == INFECTED)


def count_patched(grid: object) -> int:
    rows, cols = rows_cols(grid)
    return sum(1 for row in range(rows) for col in range(cols) if get_cell(grid, row, col) == PATCHED)


def find_first_healthy(grid: object, preferred: Position | None = None) -> Position:
    """Find a safe node for the current player marker."""
    if preferred and is_inside(grid, *preferred) and get_cell(grid, *preferred) == HEALTHY:
        return preferred

    rows, cols = rows_cols(grid)
    for row in range(rows):
        for col in range(cols):
            if get_cell(grid, row, col) == HEALTHY:
                return (row, col)
    return (0, 0)


def positions_to_json(nodes: Iterable[Position]) -> list[dict[str, int]]:
    return [{"row": row, "col": col} for row, col in nodes]
=======
from algorithms.grid import VIRUS, HEALTHY

def get_boundary_nodes(grid):
    """
    Returns a list of boundary nodes.

    A boundary node is a HEALTHY node that is adjacent
    to at least one VIRUS node.

    These nodes represent the frontier between infection
    and safe zones.
    """
    boundary = []

    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.get_cell(r, c) == HEALTHY:
                neighbors = grid.get_neighbors(r, c)

                for nr, nc in neighbors:
                    if grid.get_cell(nr, nc) == VIRUS:
                        boundary.append((r, c))
                        break

    return boundary
>>>>>>> f5ca04229a493488b64acb04988893146be396e1
