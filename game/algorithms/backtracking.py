"""
backtracking.py — Backtracking Bounded quarantine-perimeter algorithm.

Purpose
───────
Find the **minimum-cardinality** subset of *boundary nodes* (HEALTHY
cells adjacent to at least one INFECTED cell) such that patching those
cells completely **contains** the infection — i.e. no INFECTED cell has
a HEALTHY neighbour that is *not* in the chosen perimeter set.

This is equivalent to a **Minimum Vertex Cut / Separator** on the
sub-graph induced by the infection boundary, which is **NP-hard** in
general.  We therefore use *bounded backtracking* with aggressive
pruning and a hard candidate cap to keep the search tractable within
a real-time game loop.

Safeguard: candidate limit of 12
─────────────────────────────────
When the boundary is larger than 12 nodes the search space (2¹²⁺
subsets) would become prohibitively expensive.  In that case we
pre-filter to the **12 candidates closest to the centre of mass** of
the infected cluster.  This heuristic preserves the nodes most likely
to form a tight perimeter while bounding worst-case runtime to
roughly O(2¹² · B) ≈ 50 000 containment checks — comfortably under
a few hundred milliseconds on modern hardware.

Pruning strategy
────────────────
* **Upper-bound prune** — if the current partial perimeter is already
  as large as the best complete solution found so far, the branch is
  abandoned immediately (``len(current) >= len(best_known)``).
* **Early accept** — as soon as a valid containment is detected the
  branch is recorded and future branches must beat it.

These two rules together cut the effective search space dramatically
for the small clusters typically encountered in early-to-mid game.

Cooldown justification
──────────────────────
Because the algorithm is exponential in the worst case, the game
enforces a **3-turn cooldown** between invocations.  This prevents
the player from spamming the ability every turn and also creates a
strategic tension: use the powerful quarantine ability now, or save
it for a larger outbreak later?

Complexity
──────────
Worst-case O(2^B · B) where B = min(len(boundary), 12).
Typical case is much faster thanks to pruning.
"""

from __future__ import annotations

from .grid_utils import (
    GRID_SIZE,
    HEALTHY,
    INFECTED,
    get_boundary_nodes,
    get_neighbors,
    is_infected_cluster_empty,
)

_MAX_CANDIDATES: int = 12
"""Hard cap on the number of boundary nodes considered."""


# ──────────────────────────────────────────────
# Containment check
# ──────────────────────────────────────────────
def is_cluster_contained(
    grid: list[list[int]],
    perimeter: set[tuple[int, int]],
) -> bool:
    """Check whether *perimeter* fully contains the infection.

    The infection is "contained" when **every INFECTED cell's HEALTHY
    neighbours** are members of *perimeter*.  In other words, if the
    perimeter nodes were patched the virus would have nowhere left to
    spread.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.
    perimeter : set[tuple[int, int]]
        Set of ``(row, col)`` coordinates of HEALTHY cells that would be
        patched.

    Returns
    -------
    bool
        ``True`` if patching exactly the *perimeter* cells prevents all
        further virus spread.

    Complexity
    ----------
    O(GRID_SIZE²) in the worst case (full scan for INFECTED cells, ≤ 4
    neighbours each).
    """
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] != INFECTED:
                continue
            for nr, nc in get_neighbors(grid, r, c):
                if grid[nr][nc] == HEALTHY and (nr, nc) not in perimeter:
                    return False
    return True


# ──────────────────────────────────────────────
# Internal recursive search
# ──────────────────────────────────────────────
def _backtrack(
    grid: list[list[int]],
    candidates: list[tuple[int, int]],
    index: int,
    current: list[tuple[int, int]],
    best: list[list[tuple[int, int]]],
) -> None:
    """Recursively enumerate subsets of *candidates* looking for the
    smallest one that contains the infection.

    Parameters
    ----------
    grid : list[list[int]]
        The game grid (read-only during search).
    candidates : list[tuple[int, int]]
        Boundary nodes eligible for inclusion.
    index : int
        Current position in *candidates* (controls branching).
    current : list[tuple[int, int]]
        Partial perimeter built so far (mutable, backtracked).
    best : list[list[tuple[int, int]]]
        Single-element wrapper holding the best (smallest) complete
        solution found so far, or an empty list if none yet.
    """
    # ── Pruning: current path can't beat best known ──
    if best[0] and len(current) >= len(best[0]):
        return

    # ── Check containment with current partial set ──
    if is_cluster_contained(grid, set(current)):
        best[0] = list(current)
        return

    # ── Exhausted candidates without full containment ──
    if index >= len(candidates):
        return

    # ── Branch: include candidates[index] ──
    current.append(candidates[index])
    _backtrack(grid, candidates, index + 1, current, best)
    current.pop()

    # ── Branch: exclude candidates[index] ──
    _backtrack(grid, candidates, index + 1, current, best)


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def get_quarantine_perimeter(
    grid: list[list[int]],
) -> list[tuple[int, int]]:
    """Find the minimum set of boundary nodes whose patching contains
    the infection.

    Parameters
    ----------
    grid : list[list[int]]
        The current 12×12 game grid.

    Returns
    -------
    list[tuple[int, int]]
        Coordinates of the cells to patch.  An **empty list** is
        returned when there is no infection on the grid.

    Algorithm
    ---------
    1. Compute ``boundary_nodes`` — all HEALTHY cells adjacent to at
       least one INFECTED cell.
    2. If ``len(boundary_nodes) > 12``, keep only the 12 closest to the
       **centre of mass** of all INFECTED cells (Manhattan distance).
    3. Run recursive backtracking over subsets of the candidates:
       * **Prune** any branch where ``len(current) >= len(best_known)``.
       * **Accept** any subset that satisfies ``is_cluster_contained``.
    4. Return the smallest valid subset found.

    Complexity
    ----------
    Worst-case O(2^B · B) where B = min(len(boundary), 12).
    Typical runtime is far lower thanks to pruning.

    See Also
    --------
    is_cluster_contained : the feasibility predicate used during search.
    """
    # No infection → nothing to contain
    if is_infected_cluster_empty(grid):
        return []

    boundary = get_boundary_nodes(grid)

    if not boundary:
        # All INFECTED neighbours are PATCHED or INFECTED — already sealed
        return []

    # ── Optional candidate reduction ──
    candidates: list[tuple[int, int]]
    if len(boundary) > _MAX_CANDIDATES:
        # Compute centre of mass of infected cells
        inf_rows: list[int] = []
        inf_cols: list[int] = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if grid[r][c] == INFECTED:
                    inf_rows.append(r)
                    inf_cols.append(c)
        cm_r = sum(inf_rows) / len(inf_rows)
        cm_c = sum(inf_cols) / len(inf_cols)

        # Sort boundary by Manhattan distance to centre of mass
        boundary.sort(key=lambda n: abs(n[0] - cm_r) + abs(n[1] - cm_c))
        candidates = boundary[:_MAX_CANDIDATES]
    else:
        candidates = boundary

    # ── Backtracking search ──
    best: list[list[tuple[int, int]]] = [list(candidates)]  # worst case: use all
    # Verify that using all candidates actually works; if not, return them anyway
    if not is_cluster_contained(grid, set(candidates)):
        # Cannot fully contain with available candidates — return all as best effort
        return candidates

    _backtrack(grid, candidates, 0, [], best)

    return best[0]
