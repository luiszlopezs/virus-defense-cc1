/**
 * engine_benchmark.cpp — Performance benchmark for the C++ virus engine.
 *
 * Measures the time of 100 runs of spreadVirus() on a fresh 12x12 grid
 * and writes results to results/engine_times.txt.
 *
 * Build (from project root):
 *   cd engine && g++ -std=c++17 -O2 -Iinclude -Isrc
 *       ../experiments/engine_benchmark.cpp src/GameEngine.cpp
 *       src/LinkedList.cpp src/BST.cpp -o ../experiments/engine_benchmark
 *
 * Run:
 *   ./experiments/engine_benchmark
 */

#include "GameEngine.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <vector>
#include <algorithm>
#include <numeric>

static const int RUNS = 100;

int main() {
    std::cout << "=== Virus Engine Benchmark ===" << std::endl;
    std::cout << "Running spreadVirus() " << RUNS << " times on 12x12 grid..." << std::endl;

    std::vector<double> times_us;
    times_us.reserve(RUNS);

    for (int i = 0; i < RUNS; ++i) {
        GameEngine engine;
        engine.initGrid();

        auto t0 = std::chrono::high_resolution_clock::now();
        engine.spreadVirus();
        auto t1 = std::chrono::high_resolution_clock::now();

        double us = std::chrono::duration_cast<std::chrono::microseconds>(t1 - t0).count();
        times_us.push_back(us);
    }

    // Statistics
    double total = std::accumulate(times_us.begin(), times_us.end(), 0.0);
    double avg = total / RUNS;
    double min_t = *std::min_element(times_us.begin(), times_us.end());
    double max_t = *std::max_element(times_us.begin(), times_us.end());

    std::cout << std::fixed << std::setprecision(2);
    std::cout << "\nResults:" << std::endl;
    std::cout << "  Total : " << total << " us" << std::endl;
    std::cout << "  Average: " << avg << " us" << std::endl;
    std::cout << "  Min   : " << min_t << " us" << std::endl;
    std::cout << "  Max   : " << max_t << " us" << std::endl;

    // Write to file
    std::ofstream out("results/engine_times.txt");
    if (out.is_open()) {
        out << "=== Virus Engine Benchmark ===" << std::endl;
        out << "Runs: " << RUNS << std::endl;
        out << "Grid: 12x12" << std::endl;
        out << std::fixed << std::setprecision(2);
        out << "Total (us): " << total << std::endl;
        out << "Average (us): " << avg << std::endl;
        out << "Min (us): " << min_t << std::endl;
        out << "Max (us): " << max_t << std::endl;
        out << "\nPer-run times (us):" << std::endl;
        for (int i = 0; i < RUNS; ++i) {
            out << "  Run " << i + 1 << ": " << times_us[i] << std::endl;
        }
        out.close();
        std::cout << "\nResults written to results/engine_times.txt" << std::endl;
    } else {
        std::cerr << "Warning: Could not write results file." << std::endl;
    }

    std::cout << "\nBENCHMARK COMPLETE" << std::endl;
    return 0;
}
