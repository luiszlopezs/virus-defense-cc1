from algorithms.grid import VIRUS

def greedy_suggestion(grid, player: tuple) -> tuple[int, int] | None:
    """
    Suggests the next move using a greedy strategy based on connectivity.

    This implementation follows the idea:
    "patch the most connected vulnerable node first",
    adapted to a grid-based interactive game.

    Strategy:
    - Evaluate only neighboring cells (local decision).
    - Avoid virus cells (unsafe nodes).
    - For each valid neighbor, count how many SAFE connections it has.
    - Select the neighbor with the highest number of safe connections.
    - If there is a tie, return the first encountered.
    - Return None if no safe moves are available.

    Instead of selecting a global node, we adapted the greedy strategy to 
    a local decision-making process, selecting the most connected neighboring 
    node to maintain interactivity.

    Parameters:
    grid (Grid): The game board.
    player (tuple): Current position of the player (row, col).

    Returns:
    tuple[int, int] | None: Suggested next move or None if no valid move exists.
    """

    # Get neighboring positions (possible moves)
    neighbors = grid.get_neighbors(player[0], player[1])

    best_move = None
    max_connections = -1

    for (r, c) in neighbors:

        # Skip virus cells (unsafe)
        if grid.get_cell(r, c) == VIRUS:
            continue

        # Count SAFE connections (non-virus neighbors)
        safe_connections = 0
        for (nr, nc) in grid.get_neighbors(r, c):
            if grid.get_cell(nr, nc) != VIRUS:
                safe_connections += 1

        # Select the node with the highest connectivity
        if safe_connections > max_connections:
            max_connections = safe_connections
            best_move = (r, c)

    return best_move