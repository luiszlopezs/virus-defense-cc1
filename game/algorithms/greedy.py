"""Greedy emergency patch recommendation for Virus Defense."""

from __future__ import annotations

try:  # Supports both: python game/main.py and python -m game.main
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, get_cell, get_neighbors, rows_cols
except ImportError:  # pragma: no cover - fallback for package execution
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, get_cell, get_neighbors, rows_cols

Position = tuple[int, int]


def count_infected_neighbors(grid: object, row: int, col: int) -> int:
    """Return how many orthogonal neighbors of a node are infected."""
    return sum(1 for nr, nc in get_neighbors(grid, row, col) if get_cell(grid, nr, nc) == INFECTED)


def count_healthy_neighbors(grid: object, row: int, col: int) -> int:
    """Return how many orthogonal neighbors of a node are still healthy."""
    return sum(1 for nr, nc in get_neighbors(grid, row, col) if get_cell(grid, nr, nc) == HEALTHY)


def _distance(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_greedy_patch_suggestion(
    grid: object,
    current_pos: Position | None = None,
) -> Position | None:
    """
    Select the healthiest node that is under the highest immediate infection risk.

    Greedy is used as an emergency patch decision. It does not search future
    turns. It evaluates the current board and chooses the HEALTHY node with the
    largest number of infected neighbors right now.

    Priority:
    1. Candidate must be HEALTHY.
    2. Higher infected-neighbor count is better.
    3. Higher number of healthy exits is better, because the node is more
       strategically connected.
    4. If a current player position exists, prefer the closest candidate.
    5. If the tie persists, keep the first candidate found.

    Complexity: O(n), where n is the number of cells in the board. In the 12x12
    game n = 144, so it is still fast enough for real-time UI feedback.

    Avoid ties: compare the tuples element by element from left to right. If there
    is a tie in the first criterion (infected_neighbors), it automatically jumps to 
    evaluate the second (healthy_exits), and if it persists, it evaluates the distance.
    """
    rows, cols = rows_cols(grid)
    best_node: Position | None = None
    best_key: tuple[int, int, int] | None = None

    for row in range(rows):
        for col in range(cols):
            if get_cell(grid, row, col) != HEALTHY:
                continue

            infected_neighbors = count_infected_neighbors(grid, row, col)
            if infected_neighbors <= 0:
                continue

            healthy_exits = count_healthy_neighbors(grid, row, col)
            distance_score = 0
            if current_pos is not None:
                # Larger is better, so negate the Manhattan distance.
                distance_score = -_distance((row, col), current_pos)

            candidate_key = (infected_neighbors, healthy_exits, distance_score)
            if best_key is None or candidate_key > best_key:
                best_key = candidate_key
                best_node = (row, col)

    return best_node


def describe_greedy_suggestion(grid: object, node: Position | None) -> str:
    """Return a small English explanation for the HUD/action feedback."""
    if node is None:
        return "No emergency patch found"
    risk = count_infected_neighbors(grid, node[0], node[1])
    return f"Patch ({node[0]}, {node[1]}) now: {risk} infected neighbor(s)"


# Backward-compatible names used by previous prototypes.
def get_greedy_suggestion(grid: object, current_pos: Position | None = None) -> Position | None:
    return get_greedy_patch_suggestion(grid, current_pos)


def greedy_suggestion(grid: object, player: Position | None = None) -> Position | None:
    return get_greedy_patch_suggestion(grid, player)