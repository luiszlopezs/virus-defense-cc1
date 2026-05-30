from game.algorithms.grid_utils import get_boundary_nodes
from game.algorithms.grid import VIRUS, HEALTHY

# =========================
# CHECK IF -CLUSTER- IS CONTAINED
# =========================
def is_cluster_contained(grid, perimeter: set) -> bool:
    """
    Determines whether the infection is fully contained by a given perimeter.

    CLUSTER:
    A cluster is defined as a group of connected infected nodes (VIRUS)
    that behave as a single unit in the grid. Two nodes belong to the same
    cluster if they are connected through adjacent positions
    (up, down, left, right).

    A cluster is considered contained if no infected node has a neighboring
    healthy node (HEALTHY) that is NOT included in the perimeter.

    Parameters:
    grid (Grid): The game grid.
    perimeter (set): Set of nodes (row, col) representing the quarantine boundary.

    Returns:
    bool: True if the infection is contained, False otherwise.
    """
    for r in range(grid.rows):
        for c in range(grid.cols):
            if grid.get_cell(r, c) == VIRUS:
                for nr, nc in grid.get_neighbors(r, c):
                    if grid.get_cell(nr, nc) == HEALTHY and (nr, nc) not in perimeter:
                        return False
    return True


# =========================
# BACKTRACKING (BOUNDED)
# =========================
def get_quarantine_perimeter(grid) -> list[tuple]:
    """
    Computes the MINIMUM set of boundary nodes required to contain
    an infected cluster using a bounded backtracking approach.

    This algorithm uses Depth-First Search (DFS) over a decision tree
    of subsets (NOT over the grid itself).

    Strategy:
    ---------
    1. Obtain boundary nodes (candidates for the perimeter).
    2. Apply a SAFEGUARD:
       - If there are more than 12 nodes, limit the search space.
    3. Use recursive backtracking:
       - Include node
       - Exclude node
    4. Apply PRUNING:
       - Stop if current solution is worse than best found.
    5. Validate with is_cluster_contained().
    6. Keep the smallest valid solution.

    Performance:
    ------------
    - Problem is NP-hard (combinatorial).
    - Limited to at most 12 nodes → max 4096 subsets.

    Gameplay Note:
    --------------
    - A cooldown (e.g., 3 turns) can be applied externally
      to prevent overuse of this optimal strategy.

    Returns:
    --------
    list[tuple]: Minimal perimeter nodes (row, col).
                 Returns empty list if no infection exists.
    """

    boundary_nodes = get_boundary_nodes(grid)

    if not boundary_nodes:
        return []

    # SAFEGUARD
    if len(boundary_nodes) > 12:
        boundary_nodes = boundary_nodes[:12]

    best_solution = None

    def backtrack(index, current_set):
        nonlocal best_solution

        # PRUNING
        if best_solution is not None and len(current_set) >= len(best_solution):
            return

        # CHECK
        if is_cluster_contained(grid, current_set):
            best_solution = current_set.copy()
            return

        if index >= len(boundary_nodes):
            return

        node = boundary_nodes[index]

        # INCLUDE
        current_set.add(node)
        backtrack(index + 1, current_set)

        # EXCLUDE
        current_set.remove(node)
        backtrack(index + 1, current_set)

    backtrack(0, set())

    return list(best_solution) if best_solution else []