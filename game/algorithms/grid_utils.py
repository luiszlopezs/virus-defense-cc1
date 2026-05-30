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