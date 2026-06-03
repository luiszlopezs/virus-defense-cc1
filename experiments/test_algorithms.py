"""
test_algorithms.py — Unit tests for grid_utils, greedy, and backtracking.

Validates correctness of the core algorithmic components used in Virus Defense.
Run with: python experiments/test_algorithms.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from game.algorithms.grid_utils import (
    GRID_SIZE, HEALTHY, INFECTED, PATCHED,
    get_neighbors, get_degree, get_healthy_degree,
    get_boundary_nodes, is_infected_cluster_empty, count_infected,
)
from game.algorithms.greedy import get_greedy_suggestion
from game.algorithms.backtracking import get_quarantine_perimeter, is_cluster_contained


def _empty_grid():
    return [[HEALTHY] * GRID_SIZE for _ in range(GRID_SIZE)]


def _grid_with_infected(coords):
    g = _empty_grid()
    for r, c in coords:
        g[r][c] = INFECTED
    return g


# ─── grid_utils Tests ───────────────────────────────────────

class TestGetNeighbors(unittest.TestCase):

    def test_corner_top_left(self):
        g = _empty_grid()
        self.assertEqual(get_neighbors(g, 0, 0), [(1, 0), (0, 1)])

    def test_corner_bottom_right(self):
        g = _empty_grid()
        self.assertEqual(get_neighbors(g, 11, 11), [(10, 11), (11, 10)])

    def test_edge_top(self):
        g = _empty_grid()
        n = get_neighbors(g, 0, 5)
        self.assertEqual(len(n), 3)
        self.assertIn((1, 5), n)
        self.assertIn((0, 4), n)
        self.assertIn((0, 6), n)

    def test_edge_left(self):
        g = _empty_grid()
        n = get_neighbors(g, 5, 0)
        self.assertEqual(len(n), 3)

    def test_interior(self):
        g = _empty_grid()
        n = get_neighbors(g, 5, 5)
        self.assertEqual(len(n), 4)
        self.assertIn((4, 5), n)
        self.assertIn((6, 5), n)
        self.assertIn((5, 4), n)
        self.assertIn((5, 6), n)

    def test_never_exceeds_4(self):
        g = _empty_grid()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                self.assertLessEqual(len(get_neighbors(g, r, c)), 4)


class TestGetDegree(unittest.TestCase):

    def test_corner(self):
        self.assertEqual(get_degree(0, 0), 2)
        self.assertEqual(get_degree(0, 11), 2)
        self.assertEqual(get_degree(11, 0), 2)
        self.assertEqual(get_degree(11, 11), 2)

    def test_edge(self):
        self.assertEqual(get_degree(0, 5), 3)
        self.assertEqual(get_degree(5, 0), 3)
        self.assertEqual(get_degree(11, 5), 3)
        self.assertEqual(get_degree(5, 11), 3)

    def test_interior(self):
        self.assertEqual(get_degree(5, 5), 4)
        self.assertEqual(get_degree(1, 1), 4)


class TestGetHealthyDegree(unittest.TestCase):

    def test_all_healthy(self):
        g = _empty_grid()
        self.assertEqual(get_healthy_degree(g, 5, 5), 4)

    def test_some_infected(self):
        g = _grid_with_infected([(4, 5), (6, 5)])
        self.assertEqual(get_healthy_degree(g, 5, 5), 2)

    def test_corner_all_healthy(self):
        g = _empty_grid()
        self.assertEqual(get_healthy_degree(g, 0, 0), 2)


class TestGetBoundaryNodes(unittest.TestCase):

    def test_no_infection(self):
        g = _empty_grid()
        self.assertEqual(get_boundary_nodes(g), [])

    def test_single_infection(self):
        g = _grid_with_infected([(5, 5)])
        b = get_boundary_nodes(g)
        self.assertEqual(len(b), 4)
        for cell in [(4, 5), (6, 5), (5, 4), (5, 6)]:
            self.assertIn(cell, b)

    def test_corner_infection(self):
        g = _grid_with_infected([(0, 0)])
        b = get_boundary_nodes(g)
        self.assertEqual(len(b), 2)

    def test_all_infected_no_boundary(self):
        g = [[INFECTED] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.assertEqual(get_boundary_nodes(g), [])

    def test_patched_cells_not_in_boundary(self):
        g = _grid_with_infected([(5, 5)])
        g[4][5] = PATCHED
        b = get_boundary_nodes(g)
        self.assertNotIn((4, 5), b)
        self.assertEqual(len(b), 3)


class TestInfectedClusterEmpty(unittest.TestCase):

    def test_empty_grid(self):
        g = _empty_grid()
        self.assertTrue(is_infected_cluster_empty(g))

    def test_has_infection(self):
        g = _grid_with_infected([(5, 5)])
        self.assertFalse(is_infected_cluster_empty(g))


class TestCountInfected(unittest.TestCase):

    def test_zero(self):
        g = _empty_grid()
        self.assertEqual(count_infected(g), 0)

    def test_one(self):
        g = _grid_with_infected([(5, 5)])
        self.assertEqual(count_infected(g), 1)

    def test_five(self):
        g = _grid_with_infected([(0, 0), (3, 4), (5, 5), (7, 8), (11, 11)])
        self.assertEqual(count_infected(g), 5)


# ─── Greedy Tests ───────────────────────────────────────────

class TestGreedySuggestion(unittest.TestCase):

    def test_single_infection_returns_neighbor(self):
        g = _grid_with_infected([(5, 5)])
        result = get_greedy_suggestion(g, (5, 5))
        self.assertIsNotNone(result)
        self.assertIn(result, [(4, 5), (6, 5), (5, 4), (5, 6)])

    def test_no_healthy_neighbors_returns_none(self):
        g = _grid_with_infected([(5, 5)])
        g[4][5] = PATCHED
        g[6][5] = PATCHED
        g[5][4] = PATCHED
        g[5][6] = PATCHED
        result = get_greedy_suggestion(g, (5, 5))
        self.assertIsNone(result)

    def test_all_neighbors_patched(self):
        g = _empty_grid()
        g[5][5] = INFECTED
        for r, c in [(4, 5), (6, 5), (5, 4), (5, 6)]:
            g[r][c] = PATCHED
        result = get_greedy_suggestion(g, (5, 5))
        self.assertIsNone(result)

    def test_tie_breaking_prefers_closer_to_center(self):
        g = _empty_grid()
        g[5][5] = INFECTED
        g[0][5] = INFECTED
        g[6][5] = HEALTHY
        g[4][5] = HEALTHY
        result = get_greedy_suggestion(g, (5, 5))
        self.assertIsNotNone(result)
        self.assertIn(result, [(4, 5), (6, 5)])

    def test_picks_highest_healthy_degree(self):
        g = _empty_grid()
        g[5][5] = INFECTED
        g[4][4] = HEALTHY
        g[4][5] = HEALTHY
        g[4][6] = HEALTHY
        g[3][5] = INFECTED
        g[5][4] = INFECTED
        result = get_greedy_suggestion(g, (5, 5))
        self.assertIsNotNone(result)

    def test_corner_position(self):
        g = _grid_with_infected([(1, 0)])
        result = get_greedy_suggestion(g, (0, 0))
        self.assertIsNotNone(result)
        self.assertIn(result, [(1, 0), (0, 1)])

    def test_edge_position(self):
        g = _grid_with_infected([(1, 5)])
        result = get_greedy_suggestion(g, (0, 5))
        self.assertIsNotNone(result)


# ─── Backtracking Tests ─────────────────────────────────────

class TestIsClusterContained(unittest.TestCase):

    def test_contained_single_infection(self):
        g = _grid_with_infected([(5, 5)])
        perimeter = {(4, 5), (6, 5), (5, 4), (5, 6)}
        self.assertTrue(is_cluster_contained(g, perimeter))

    def test_not_contained_missing_node(self):
        g = _grid_with_infected([(5, 5)])
        perimeter = {(4, 5), (6, 5), (5, 4)}
        self.assertFalse(is_cluster_contained(g, perimeter))

    def test_empty_perimeter(self):
        g = _grid_with_infected([(5, 5)])
        self.assertFalse(is_cluster_contained(g, set()))

    def test_no_infection_trivially_contained(self):
        g = _empty_grid()
        self.assertTrue(is_cluster_contained(g, set()))


class TestGetQuarantinePerimeter(unittest.TestCase):

    def test_no_infection_returns_empty(self):
        g = _empty_grid()
        self.assertEqual(get_quarantine_perimeter(g), [])

    def test_single_infection_returns_4_cells(self):
        g = _grid_with_infected([(5, 5)])
        p = get_quarantine_perimeter(g)
        self.assertEqual(len(p), 4)
        self.assertTrue(is_cluster_contained(g, set(p)))

    def test_corner_infection_returns_2_cells(self):
        g = _grid_with_infected([(0, 0)])
        p = get_quarantine_perimeter(g)
        self.assertEqual(len(p), 2)
        self.assertTrue(is_cluster_contained(g, set(p)))

    def test_edge_infection_returns_3_cells(self):
        g = _grid_with_infected([(0, 5)])
        p = get_quarantine_perimeter(g)
        self.assertEqual(len(p), 3)
        self.assertTrue(is_cluster_contained(g, set(p)))

    def test_2x2_cluster(self):
        g = _grid_with_infected([(5, 5), (5, 6), (6, 5), (6, 6)])
        p = get_quarantine_perimeter(g)
        self.assertGreater(len(p), 0)
        self.assertTrue(is_cluster_contained(g, set(p)))

    def test_already_patched_boundary(self):
        g = _grid_with_infected([(5, 5)])
        for r, c in [(4, 5), (6, 5), (5, 4), (5, 6)]:
            g[r][c] = PATCHED
        p = get_quarantine_perimeter(g)
        self.assertEqual(p, [])

    def test_result_contains_only_boundary_cells(self):
        g = _grid_with_infected([(5, 5)])
        p = get_quarantine_perimeter(g)
        boundary = get_boundary_nodes(g)
        for cell in p:
            self.assertIn(cell, boundary)


if __name__ == "__main__":
    unittest.main()
