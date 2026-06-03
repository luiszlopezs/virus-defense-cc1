"""
algorithm_benchmark.py — Performance benchmarks for greedy and backtracking algorithms.

Measures execution time across different cluster sizes and writes results
to results/algorithm_benchmark.csv.

Run with: python experiments/algorithm_benchmark.py
"""

import csv
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from game.algorithms.grid_utils import HEALTHY, INFECTED, GRID_SIZE
from game.algorithms.greedy import get_greedy_suggestion
from game.algorithms.backtracking import get_quarantine_perimeter

RESULTS_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "results")
CSV_PATH = os.path.join(RESULTS_DIR, "algorithm_benchmark.csv")


def _empty_grid():
    return [[HEALTHY] * GRID_SIZE for _ in range(GRID_SIZE)]


def _place_infections(n):
    g = _empty_grid()
    placed = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if placed >= n:
                return g
            g[r][c] = INFECTED
            placed += 1
    return g


def _benchmark_greedy(g, iterations=1000):
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        get_greedy_suggestion(g, (5, 5))
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1_000_000)
    return times


def _benchmark_backtracking(g, iterations=100):
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        get_quarantine_perimeter(g)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1_000_000)
    return times


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    cluster_sizes = [1, 3, 5, 8, 12]
    rows = []

    print(f"{'Cluster':>10} {'Algorithm':<20} {'Avg (us)':>10} {'Max (us)':>10} {'Min (us)':>10} {'Iters':>8} {'Status':<10}")
    print("-" * 80)

    for size in cluster_sizes:
        grid = _place_infections(size)

        # Benchmark greedy
        g_times = _benchmark_greedy(grid)
        g_avg = sum(g_times) / len(g_times)
        g_max = max(g_times)
        g_min = min(g_times)
        g_status = "PASS" if g_max < 100_000 else "FAIL"
        print(f"{size:>10} {'greedy':<20} {g_avg:>10.1f} {g_max:>10.1f} {g_min:>10.1f} {len(g_times):>8} {g_status:<10}")
        rows.append({
            "cluster_size": size,
            "algorithm": "greedy",
            "avg_time_us": round(g_avg, 1),
            "max_time_us": round(g_max, 1),
            "min_time_us": round(g_min, 1),
            "iterations": len(g_times),
            "status": g_status,
        })

        # Benchmark backtracking
        b_times = _benchmark_backtracking(grid)
        b_avg = sum(b_times) / len(b_times)
        b_max = max(b_times)
        b_min = min(b_times)
        b_status = "PASS" if b_max < 100_000 else "FAIL"
        print(f"{size:>10} {'backtracking':<20} {b_avg:>10.1f} {b_max:>10.1f} {b_min:>10.1f} {len(b_times):>8} {b_status:<10}")
        rows.append({
            "cluster_size": size,
            "algorithm": "backtracking",
            "avg_time_us": round(b_avg, 1),
            "max_time_us": round(b_max, 1),
            "min_time_us": round(b_min, 1),
            "iterations": len(b_times),
            "status": b_status,
        })

    # Write CSV
    fieldnames = ["cluster_size", "algorithm", "avg_time_us", "max_time_us", "min_time_us", "iterations", "status"]
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults written to {CSV_PATH}")

    # Validate all passed
    all_pass = all(r["status"] == "PASS" for r in rows)
    if all_pass:
        print("ALL BENCHMARKS PASSED (< 100ms per call)")
    else:
        print("SOME BENCHMARKS FAILED — check results")
        sys.exit(1)


if __name__ == "__main__":
    main()
