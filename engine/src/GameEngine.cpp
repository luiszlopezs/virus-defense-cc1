#include "GameEngine.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <cmath>
#include <cstdlib>
#include <ctime>

// ── Helpers for manual JSON parsing ──

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

static int extractInt(const std::string& json, const std::string& key) {
    std::string val = extractField(json, key);
    if (val.empty()) return -1;
    try { return std::stoi(val); } catch (...) { return -1; }
}

// Manhattan distance helper
static int manhattan(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

// Check if position is on border (not corner)
static bool isBorderNotCorner(int r, int c) {
    bool onBorder = (r == 0 || r == GRID_SIZE - 1 || c == 0 || c == GRID_SIZE - 1);
    bool isCorner = (r == 0 || r == GRID_SIZE - 1) && (c == 0 || c == GRID_SIZE - 1);
    return onBorder && !isCorner;
}

// ── Constructor ──

GameEngine::GameEngine() {
    turn = 0;
    score = 0;
    budget = 5;
    greedy_cost = 1;
    backtracking_cooldown = 0;
    player_row = 0;
    player_col = 0;
    goal_row = 0;
    goal_col = 0;
    player_infected = false;
    goal_infected = false;
    backtracking_perimeter_size = 0;
}

// initGrid: Initialise grid with random player, goal, and virus positions
void GameEngine::initGrid() {
    srand(time(NULL));
    player_infected = false;
    goal_infected = false;

    // 1. Initialise all nodes as healthy
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            grid[r][c].row = r;
            grid[r][c].col = c;
            grid[r][c].state = HEALTHY;
            grid[r][c].degree = 0;
        }
    }

    // 2. Compute structural degrees
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            grid[r][c].degree = calculateNodeDegree(r, c);
        }
    }

    // 3. Generate player position on border (not corner)
    int border_positions[40][2];
    int border_count = 0;
    for (int r = 0; r < GRID_SIZE; r++) {
        for (int c = 0; c < GRID_SIZE; c++) {
            if (isBorderNotCorner(r, c)) {
                border_positions[border_count][0] = r;
                border_positions[border_count][1] = c;
                border_count++;
            }
        }
    }
    int pidx = rand() % border_count;
    player_row = border_positions[pidx][0];
    player_col = border_positions[pidx][1];

    // 4. Generate goal position on border, Manhattan >= 10 from player
    goal_row = -1;
    goal_col = -1;
    for (int attempt = 0; attempt < 200; attempt++) {
        int gidx = rand() % border_count;
        int gr = border_positions[gidx][0];
        int gc = border_positions[gidx][1];
        if (manhattan(player_row, player_col, gr, gc) >= 10) {
            goal_row = gr;
            goal_col = gc;
            break;
        }
    }
    // Fallback: use far corner
    if (goal_row == -1) {
        if (player_row <= 5) goal_row = GRID_SIZE - 1; else goal_row = 0;
        if (player_col <= 5) goal_col = GRID_SIZE - 1; else goal_col = 0;
    }

    // 5. Generate virus position in interior, Manhattan >= 6 from both player and goal
    int virus_row = -1;
    virus_row = -1;
    int virus_col = -1;
    for (int attempt = 0; attempt < 500; attempt++) {
        int vr = 2 + rand() % (GRID_SIZE - 4); // rows 2-9
        int vc = 2 + rand() % (GRID_SIZE - 4); // cols 2-9
        if (manhattan(vr, vc, player_row, player_col) >= 6 &&
            manhattan(vr, vc, goal_row, goal_col) >= 6) {
            virus_row = vr;
            virus_col = vc;
            break;
        }
    }
    // Fallback: center
    if (virus_row == -1) {
        virus_row = GRID_SIZE / 2;
        virus_col = GRID_SIZE / 2;
    }

    grid[virus_row][virus_col].state = INFECTED;
    infection_history.append(virus_row, virus_col, 0, "initial");

    // 5b. Add 2 small outbreaks in different parts of the map
    int outbreak_rows[3] = {virus_row, 0, 0};
    int outbreak_cols[3] = {virus_col, 0, 0};
    int outbreak_count = 1;

    for (int b = 0; b < 2; b++) {
        for (int attempt = 0; attempt < 200; attempt++) {
            int br = 2 + rand() % (GRID_SIZE - 4);
            int bc = 2 + rand() % (GRID_SIZE - 4);

            // Must be far from player, goal, and other outbreaks
            bool too_close = false;
            if (manhattan(br, bc, player_row, player_col) < 5) too_close = true;
            if (manhattan(br, bc, goal_row, goal_col) < 5) too_close = true;
            for (int o = 0; o < outbreak_count; o++) {
                if (manhattan(br, bc, outbreak_rows[o], outbreak_cols[o]) < 5) {
                    too_close = true;
                    break;
                }
            }
            if (too_close) continue;

            // Infect this cell
            grid[br][bc].state = INFECTED;
            infection_history.append(br, bc, 0, "outbreak");
            outbreak_rows[outbreak_count] = br;
            outbreak_cols[outbreak_count] = bc;
            outbreak_count++;

            // Try to infect one healthy neighbor
            int dr4[] = {-1, 1, 0, 0};
            int dc4[] = {0, 0, -1, 1};
            // Shuffle directions
            for (int i = 3; i > 0; i--) {
                int j = rand() % (i + 1);
                int tr = dr4[i]; dr4[i] = dr4[j]; dr4[j] = tr;
                int tc = dc4[i]; dc4[i] = dc4[j]; dc4[j] = tc;
            }
            for (int d = 0; d < 4; d++) {
                int nr = br + dr4[d];
                int nc = bc + dc4[d];
                if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE &&
                    grid[nr][nc].state == HEALTHY) {
                    grid[nr][nc].state = INFECTED;
                    infection_history.append(nr, nc, 0, "outbreak");
                    break;
                }
            }
            break;
        }
    }

    // 6. Update connectivity degrees for all infected nodes
    for (int o = 0; o < outbreak_count; o++) {
        updateConnectivityDegrees(outbreak_rows[o], outbreak_cols[o]);
    }

    // 7. Populate BST with all healthy nodes
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
}

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

// spreadVirus: Each infected node can infect up to 2 healthy neighbors per turn (50% each)
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
        int infections_this_node = 0;
        for (int j = 0; j < 4; j++) {
            if (infections_this_node >= 1) break; // max 1 per node per turn
            int nr = r + dr[j];
            int nc = c + dc[j];
            if (nr >= 0 && nr < GRID_SIZE && nc >= 0 && nc < GRID_SIZE) {
                if (grid[nr][nc].state == HEALTHY) {
                    double roll = (double)rand() / (double)RAND_MAX;
                    if (roll < 0.20) {
                        grid[nr][nc].state = INFECTED;
                        infection_history.append(nr, nc, turn, "spread");
                        bst.remove(nr * GRID_SIZE + nc, grid[nr][nc].degree);
                        grid[nr][nc].degree = 0;
                        updateConnectivityDegrees(nr, nc);
                        infections_this_node++;
                    }
                }
            }
        }
    }

    // Check if virus reached player or goal
    if (grid[player_row][player_col].state == INFECTED) {
        player_infected = true;
    }
    if (grid[goal_row][goal_col].state == INFECTED) {
        goal_infected = true;
    }
}

// applyAction: Dispatches actions based on input commands
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
    else if (action == "greedy") action_code = 3;
    else if (action == "backtracking") action_code = 4;
    else if (action == "quit") action_code = -1;

    if (action_code > 0) {
        applyAction(row, col, action_code);
    }

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

void GameEngine::writeStateJSON() {
    computeBacktrackingPerimeter();

    std::stringstream ss;
    ss << "{\n";
    ss << "  \"turn\": " << turn << ",\n";
    ss << "  \"score\": " << score << ",\n";
    ss << "  \"budget\": " << budget << ",\n";
    ss << "  \"greedy_cost\": " << greedy_cost << ",\n";
    ss << "  \"backtracking_cooldown\": " << backtracking_cooldown << ",\n";

    // Player and goal positions
    ss << "  \"player_pos\": {\"row\": " << player_row << ", \"col\": " << player_col << "},\n";
    ss << "  \"goal_pos\": {\"row\": " << goal_row << ", \"col\": " << goal_col << "},\n";
    ss << "  \"player_infected\": " << (player_infected ? "true" : "false") << ",\n";
    ss << "  \"goal_infected\": " << (goal_infected ? "true" : "false") << ",\n";

    // Grid
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
