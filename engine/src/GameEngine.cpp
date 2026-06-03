#include "GameEngine.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <cmath>
#include <cstdlib>
#include <ctime>

// ── Helpers for manual JSON parsing ──

// extractField: Searches for a JSON string field "key": "value" and returns the value.
static std::string extractField(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\"";
    size_t pos = json.find(needle);
    if (pos == std::string::npos) return "";
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) return "";
    pos++;
    while (pos < json.size() && json[pos] == ' ') pos++;
    if (pos >= json.size()) return "";
    if (json[pos] == '"') {
        pos++;
        size_t end = json.find('"', pos);
        if (end == std::string::npos) return "";
        return json.substr(pos, end - pos);
    }
    size_t end = pos;
    while (end < json.size() && json[end] != ',' && json[end] != '}' && json[end] != ' ') end++;
    return json.substr(pos, end - pos);
}

// extractInt: Searches for a JSON integer field "key": N and returns N.
static int extractInt(const std::string& json, const std::string& key) {
    std::string val = extractField(json, key);
    if (val.empty()) return -1;
    try { return std::stoi(val); } catch (...) { return -1; }
}

// ── Constructor ──

GameEngine::GameEngine() {
    turn = 0;
    score = 0;
    budget = 5;
    greedy_cost = 1;
    backtracking_cooldown = 0;
    reinforce_cooldown = 0;
    backtracking_perimeter_size = 0;
}

// initGrid: Initialise a 12x12 grid, set degrees, infect (5,5), and populate the BST
void GameEngine::initGrid() {
    srand(time(NULL));

    // 1. Initialise all nodes as healthy
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            grid[r][c].row = r;
            grid[r][c].col = c;
            grid[r][c].state = HEALTHY;
            grid[r][c].degree = 0;
        }
    }

    // 2. Compute degrees based on initial healthy neighbors (corners=2, edges=3, others=4)
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            grid[r][c].degree = calculateNodeDegree(r, c);
        }
    }

    // 3. Set a random node to infected
    int sr = rand() % GRID_SIZE;
    int sc = rand() % GRID_SIZE;
    grid[sr][sc].state = INFECTED;
    infection_history.append(sr, sc, 0, "initial");

    // 4. Update the degrees of the neighbors of the initial infected node
    updateConnectivityDegrees(sr, sc);

    // 5. Populate the BST with all healthy nodes and their computed degrees
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c].state == HEALTHY) {
                bst.insert(r * GRID_SIZE + c, grid[r][c].degree);
            }
        }
    }

    turn = 0;
    score = calculateScore();
    budget = 5;
    greedy_cost = 1;
    backtracking_cooldown = 0;
    reinforce_cooldown = 0;
}

// calculateNodeDegree: Returns the number of adjacent healthy cells
int GameEngine::calculateNodeDegree(int r, int c) const {
    int count = 0;
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int i = 0; i < 4; i++) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
            if (grid[nr][nc].state == HEALTHY) {
                count++;
            }
        }
    }
    return count;
}

// updateConnectivityDegrees: Decreases neighbors' connectivity degrees when a node becomes unhealthy
void GameEngine::updateConnectivityDegrees(int row, int col) {
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int i = 0; i < 4; i++) {
        int nr = row + dr[i];
        int nc = col + dc[i];
        if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
            if (grid[nr][nc].state == HEALTHY) {
                int old_deg = grid[nr][nc].degree;
                int new_deg = old_deg - 1;
                if (new_deg < 0) new_deg = 0;
                grid[nr][nc].degree = new_deg;
                bst.update(nr * GRID_SIZE + nc, old_deg, new_deg);
            }
        }
    }
}

// spreadVirus: Infects healthy neighbors of currently infected nodes with 50% probability each
void GameEngine::spreadVirus() {
    Point infected_nodes[144];
    int infected_count = 0;

    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c].state == INFECTED) {
                infected_nodes[infected_count++] = {r, c};
            }
        }
    }

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int i = 0; i < infected_count; i++) {
        int r = infected_nodes[i].r;
        int c = infected_nodes[i].c;
        for (int j = 0; j < 4; j++) {
            int nr = r + dr[j];
            int nc = c + dc[j];
            if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
                if (grid[nr][nc].state == HEALTHY) {
                    double roll = (double)rand() / (double)RAND_MAX;
                    if (roll < 0.50) {
                        grid[nr][nc].state = INFECTED;
                        infection_history.append(nr, nc, turn, "spread");

                        bst.remove(nr * GRID_SIZE + nc, grid[nr][nc].degree);
                        grid[nr][nc].degree = 0;

                        updateConnectivityDegrees(nr, nc);
                    }
                }
            }
        }
    }
}

// applyAction: Dispatches actions based on input JSON commands
void GameEngine::applyAction(int row, int col, int action_code) {
    if (action_code == 1) { // Patch
        if (budget >= 1 && row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE && grid[row][col].state == HEALTHY) {
            grid[row][col].state = PATCHED;
            bst.remove(row * GRID_SIZE + col, grid[row][col].degree);
            grid[row][col].degree = 0;
            updateConnectivityDegrees(row, col);
            budget -= 1;
        }
    }
    else if (action_code == 2) { // Reinforce - patches target + healthy neighbors, costs 3, 3 turn cooldown
        if (reinforce_cooldown == 0 && budget >= 3 && row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE && grid[row][col].state == HEALTHY) {
            grid[row][col].state = PATCHED;
            bst.remove(row * GRID_SIZE + col, grid[row][col].degree);
            grid[row][col].degree = 0;
            updateConnectivityDegrees(row, col);

            int dr[] = {-1, 1, 0, 0};
            int dc[] = {0, 0, -1, 1};
            for (int i = 0; i < 4; i++) {
                int nr = row + dr[i];
                int nc = col + dc[i];
                if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE && grid[nr][nc].state == HEALTHY) {
                    grid[nr][nc].state = PATCHED;
                    bst.remove(nr * GRID_SIZE + nc, grid[nr][nc].degree);
                    grid[nr][nc].degree = 0;
                    updateConnectivityDegrees(nr, nc);
                }
            }
            budget -= 3;
            reinforce_cooldown = 3;
        }
    }
    else if (action_code == 3) { // Greedy suggestion patch
        if (budget >= greedy_cost && row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE && grid[row][col].state == HEALTHY) {
            grid[row][col].state = PATCHED;
            bst.remove(row * GRID_SIZE + col, grid[row][col].degree);
            grid[row][col].degree = 0;
            updateConnectivityDegrees(row, col);
            budget -= greedy_cost;
            greedy_cost += 1;
        }
    }
    else if (action_code == 4) { // Backtracking containment perimeter
        computeBacktrackingPerimeter();
        if (backtracking_cooldown == 0 && budget >= backtracking_perimeter_size && backtracking_perimeter_size > 0) {
            for (int i = 0; i < backtracking_perimeter_size; i++) {
                int pr = backtracking_perimeter[i].r;
                int pc = backtracking_perimeter[i].c;
                if (grid[pr][pc].state == HEALTHY) {
                    grid[pr][pc].state = PATCHED;
                    bst.remove(pr * GRID_SIZE + pc, grid[pr][pc].degree);
                    grid[pr][pc].degree = 0;
                    updateConnectivityDegrees(pr, pc);
                }
            }
            budget -= backtracking_perimeter_size;
            backtracking_cooldown = 3;
        }
    }
}

// calculateScore: +10 for HEALTHY nodes, -5 for INFECTED nodes, +5 for PATCHED nodes
int GameEngine::calculateScore() {
    int healthy = 0;
    int infected = 0;
    int patched = 0;
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c].state == HEALTHY) healthy++;
            else if (grid[r][c].state == INFECTED) infected++;
            else if (grid[r][c].state == PATCHED) patched++;
        }
    }
    score = 10 * healthy - 5 * infected + 5 * patched;
    return score;
}

// isClusterContained: Helper to check if the virus is contained inside a given perimeter
bool GameEngine::isClusterContained(Point* perimeter, int size) const {
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c].state == INFECTED) {
                for (int i = 0; i < 4; i++) {
                    int nr = r + dr[i];
                    int nc = c + dc[i];
                    if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
                        if (grid[nr][nc].state == HEALTHY) {
                            bool found = false;
                            for (int p = 0; p < size; p++) {
                                if (perimeter[p].r == nr && perimeter[p].c == nc) {
                                    found = true;
                                    break;
                                }
                            }
                            if (!found) {
                                return false;
                            }
                        }
                    }
                }
            }
        }
    }
    return true;
}

// backtrackSearch: Recursively searches for the minimum sized perimeter containing the infection
void GameEngine::backtrackSearch(int index, Point* current_perimeter, int current_size, Point* boundary, int boundary_count) {
    if (current_size >= backtracking_perimeter_size) {
        return;
    }

    if (isClusterContained(current_perimeter, current_size)) {
        backtracking_perimeter_size = current_size;
        for (int i = 0; i < current_size; i++) {
            backtracking_perimeter[i] = current_perimeter[i];
        }
        return;
    }

    if (index >= boundary_count) {
        return;
    }

    current_perimeter[current_size] = boundary[index];
    backtrackSearch(index + 1, current_perimeter, current_size + 1, boundary, boundary_count);

    backtrackSearch(index + 1, current_perimeter, current_size, boundary, boundary_count);
}

// computeBacktrackingPerimeter: Locates boundary nodes, filters to top 12 using proximity heuristic, and executes search
void GameEngine::computeBacktrackingPerimeter() {
    Point boundary[144];
    int boundary_count = 0;

    double sum_r = 0, sum_c = 0;
    int infected_count = 0;

    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c].state == INFECTED) {
                sum_r += r;
                sum_c += c;
                infected_count++;
            }
        }
    }

    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (grid[r][c].state == HEALTHY) {
                bool has_infected = false;
                for (int i = 0; i < 4; i++) {
                    int nr = r + dr[i];
                    int nc = c + dc[i];
                    if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
                        if (grid[nr][nc].state == INFECTED) {
                            has_infected = true;
                            break;
                        }
                    }
                }
                if (has_infected) {
                    boundary[boundary_count++] = {r, c};
                }
            }
        }
    }

    if (boundary_count == 0) {
        backtracking_perimeter_size = 0;
        return;
    }

    if (infected_count > 0) {
        double avg_r = sum_r / infected_count;
        double avg_c = sum_c / infected_count;

        for (int i = 0; i < boundary_count - 1; i++) {
            for (int j = i + 1; j < boundary_count; j++) {
                double dist_i = (boundary[i].r - avg_r) * (boundary[i].r - avg_r) + (boundary[i].c - avg_c) * (boundary[i].c - avg_c);
                double dist_j = (boundary[j].r - avg_r) * (boundary[j].r - avg_r) + (boundary[j].c - avg_c) * (boundary[j].c - avg_c);
                if (dist_j < dist_i) {
                    Point temp = boundary[i];
                    boundary[i] = boundary[j];
                    boundary[j] = temp;
                }
            }
        }
    }

    int allowed_boundary_count = (boundary_count > 12) ? 12 : boundary_count;

    backtracking_perimeter_size = 999;
    Point current_perimeter[12];
    backtrackSearch(0, current_perimeter, 0, boundary, allowed_boundary_count);

    if (backtracking_perimeter_size == 999) {
        backtracking_perimeter_size = 0;
    }
}

// readInputJSON: Reads inputs from shared/input.json and updates state
void GameEngine::readInputJSON() {
    std::ifstream file("shared/input.json");
    if (!file.is_open()) return;

    std::string content((std::istreambuf_iterator<char>(file)),
                         std::istreambuf_iterator<char>());
    file.close();

    std::string action = extractField(content, "action");
    int row = extractInt(content, "row");
    int col = extractInt(content, "col");

    int action_code = 0;
    if (action == "patch") action_code = 1;
    else if (action == "reinforce") action_code = 2;
    else if (action == "greedy") action_code = 3;
    else if (action == "backtracking") action_code = 4;
    else if (action == "quit") action_code = -1;

    if (action_code > 0) {
        applyAction(row, col, action_code);
    }

    // Reset input.json immediately after reading to avoid infinite application loops
    std::ofstream out("shared/input.json");
    if (out.is_open()) {
        out << "{\n"
            << "  \"action\": \"none\",\n"
            << "  \"target\": { \"row\": -1, \"col\": -1 },\n"
            << "  \"budget_spent\": 0\n"
            << "}";
        out.close();
    }
}

// writeStateJSON: Outputs the current state to shared/state.json
void GameEngine::writeStateJSON() {
    computeBacktrackingPerimeter();

    std::stringstream ss;
    ss << "{\n";
    ss << "  \"turn\": " << turn << ",\n";
    ss << "  \"score\": " << score << ",\n";
    ss << "  \"budget\": " << budget << ",\n";
    ss << "  \"greedy_cost\": " << greedy_cost << ",\n";
    ss << "  \"backtracking_cooldown\": " << backtracking_cooldown << ",\n";
    ss << "  \"reinforce_cooldown\": " << reinforce_cooldown << ",\n";

    // Grid: 12x12 2D array
    ss << "  \"grid\": [\n";
    for (int r = 0; r < GRID_SIZE; r++) {
        ss << "    [";
        for (int c = 0; c < GRID_SIZE; c++) {
            ss << grid[r][c].state;
            if (c < GRID_SIZE - 1) ss << ", ";
        }
        ss << "]";
        if (r < GRID_SIZE - 1) ss << ",";
        ss << "\n";
    }
    ss << "  ],\n";

    // Infection history
    int histSize = infection_history.getSize();
    InfectionEvent* events = new InfectionEvent[histSize];
    int histCount = 0;
    infection_history.toArray(events, histCount);

    ss << "  \"infection_history\": [\n";
    for (int i = 0; i < histCount; i++) {
        ss << "    {\"row\": " << events[i].row
           << ", \"col\": " << events[i].col
           << ", \"turn\": " << events[i].turn
           << ", \"cause\": \"" << events[i].cause << "\"}";
        if (i < histCount - 1) ss << ",";
        ss << "\n";
    }
    delete[] events;
    ss << "  ],\n";

    // Greedy suggestion from BST max
    int max_id = bst.findMax();
    if (max_id != -1) {
        ss << "  \"greedy_suggestion\": {\"row\": " << max_id / GRID_SIZE
           << ", \"col\": " << max_id % GRID_SIZE << "},\n";
    } else {
        ss << "  \"greedy_suggestion\": {\"row\": -1, \"col\": -1},\n";
    }

    // Backtracking perimeter
    ss << "  \"backtracking_perimeter\": [\n";
    for (int i = 0; i < backtracking_perimeter_size; i++) {
        ss << "    {\"row\": " << backtracking_perimeter[i].r
           << ", \"col\": " << backtracking_perimeter[i].c << "}";
        if (i < backtracking_perimeter_size - 1) ss << ",";
        ss << "\n";
    }
    ss << "  ]\n";
    ss << "}";

    std::ofstream file("shared/state.json");
    if (file.is_open()) {
        file << ss.str();
        file.close();
    }
}
