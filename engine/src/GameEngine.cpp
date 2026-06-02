#include "GameEngine.h"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <regex>
#include <sstream>
#include <string>

namespace fs = std::filesystem;

static fs::path resolveSharedPath() {
    fs::path cwd = fs::current_path();
    fs::path candidates[] = {
        cwd / "shared",
        cwd / ".." / "shared",
        cwd / ".." / ".." / "shared",
        cwd / ".." / ".." / ".." / "shared"
    };

    for (const fs::path& path : candidates) {
        if (fs::exists(path) && fs::is_directory(path)) {
            return fs::weakly_canonical(path);
        }
    }

    fs::path fallback = cwd / ".." / "shared";
    fs::create_directories(fallback);
    return fs::weakly_canonical(fallback);
}

static fs::path stateFile() {
    return resolveSharedPath() / "state.json";
}

static fs::path inputFile() {
    return resolveSharedPath() / "input.json";
}

static std::string readTextFile(const fs::path& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        return "";
    }
    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

static std::string jsonEscape(const char* text) {
    std::string input = text != nullptr ? text : "";
    std::string out;
    for (char ch : input) {
        switch (ch) {
            case '\\': out += "\\\\"; break;
            case '"': out += "\\\""; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default: out += ch; break;
        }
    }
    return out;
}

static bool extractString(const std::string& text, const std::string& key, std::string& value) {
    std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"");
    std::smatch match;
    if (std::regex_search(text, match, pattern)) {
        value = match[1].str();
        return true;
    }
    return false;
}

static bool extractInt(const std::string& text, const std::string& key, int& value) {
    std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*(-?[0-9]+)");
    std::smatch match;
    if (std::regex_search(text, match, pattern)) {
        value = std::atoi(match[1].str().c_str());
        return true;
    }
    return false;
}

GameEngine::GameEngine() {
    running = true;
    initGrid();
}

void GameEngine::setMessage(const char* text) {
    std::snprintf(message, sizeof(message), "%s", text != nullptr ? text : "");
}

void GameEngine::setStatus(const char* text) {
    std::snprintf(status, sizeof(status), "%s", text != nullptr ? text : "playing");
}

void GameEngine::clearLastPath() {
    last_path_count = 0;
    for (int i = 0; i < MAX_NODES; ++i) {
        last_path_rows[i] = -1;
        last_path_cols[i] = -1;
    }
}

void GameEngine::storePath(const EngineInput& input) {
    clearLastPath();
    int count = input.path_count;
    if (count > MAX_NODES) count = MAX_NODES;
    for (int i = 0; i < count; ++i) {
        last_path_rows[i] = input.path_rows[i];
        last_path_cols[i] = input.path_cols[i];
    }
    last_path_count = count;
}

void GameEngine::initGrid() {
    degreeIndex.clear();
    infectionHistory.clear();
    clearLastPath();

    turn = 0;
    budget = INITIAL_BUDGET;
    greedy_cost = 1;
    backtracking_cooldown = 0;
    player_row = 0;
    player_col = 0;
    goal_row = GRID_SIZE - 1;
    goal_col = GRID_SIZE - 1;
    running = true;
    setStatus("engine_running");
    setMessage("C++ engine ready");

    for (int row = 0; row < GRID_SIZE; ++row) {
        for (int col = 0; col < GRID_SIZE; ++col) {
            grid[row][col].row = row;
            grid[row][col].col = col;
            grid[row][col].degree = getDegree(row, col);
            grid[row][col].state = HEALTHY;
            degreeIndex.insert(nodeId(row, col), grid[row][col].degree);
        }
    }

    grid[5][5].state = INFECTED;
    infectionHistory.append(5, 5, 0, "initial_seed");
    score = calculateScore();
    updateGameStatus();
}

bool GameEngine::isRunning() const {
    return running;
}

int GameEngine::getDegree(int row, int col) const {
    int degree = 4;
    if (row == 0 || row == GRID_SIZE - 1) degree--;
    if (col == 0 || col == GRID_SIZE - 1) degree--;
    return degree;
}

int GameEngine::nodeId(int row, int col) const {
    return row * GRID_SIZE + col;
}

bool GameEngine::inside(int row, int col) const {
    return row >= 0 && row < GRID_SIZE && col >= 0 && col < GRID_SIZE;
}

bool GameEngine::isHealthy(int row, int col) const {
    return inside(row, col) && grid[row][col].state == HEALTHY;
}

bool GameEngine::isWalkable(int row, int col) const {
    return inside(row, col) && grid[row][col].state != INFECTED;
}

bool GameEngine::setPatched(int row, int col) {
    if (!isHealthy(row, col)) {
        return false;
    }
    grid[row][col].state = PATCHED;
    return true;
}

bool GameEngine::areAdjacent(int r1, int c1, int r2, int c2) const {
    int d = std::abs(r1 - r2) + std::abs(c1 - c2);
    return d == 1;
}

int GameEngine::countInfected() const {
    int count = 0;
    for (int row = 0; row < GRID_SIZE; ++row) {
        for (int col = 0; col < GRID_SIZE; ++col) {
            if (grid[row][col].state == INFECTED) count++;
        }
    }
    return count;
}

int GameEngine::countHealthy() const {
    int count = 0;
    for (int row = 0; row < GRID_SIZE; ++row) {
        for (int col = 0; col < GRID_SIZE; ++col) {
            if (grid[row][col].state == HEALTHY) count++;
        }
    }
    return count;
}

int GameEngine::calculateScore() {
    int value = 0;
    for (int row = 0; row < GRID_SIZE; ++row) {
        for (int col = 0; col < GRID_SIZE; ++col) {
            if (grid[row][col].state == HEALTHY) value += 10;
            else if (grid[row][col].state == INFECTED) value -= 5;
        }
    }
    score = value;
    return score;
}

void GameEngine::updateGameStatus() {
    if (player_row == goal_row && player_col == goal_col) {
        setStatus("victory");
        setMessage("Goal reached");
        return;
    }

    if (grid[goal_row][goal_col].state == INFECTED) {
        setStatus("game_over");
        setMessage("The goal node was infected");
        return;
    }

    if (countInfected() == 0) {
        setStatus("victory");
        setMessage("Network protected");
        return;
    }

    if (countInfected() >= GAME_OVER_INFECTED_LIMIT || turn >= MAX_TURNS || score < -200) {
        setStatus("game_over");
        return;
    }

    setStatus("engine_running");
}

EngineInput GameEngine::readInputJSON() const {
    EngineInput input;
    std::snprintf(input.action, sizeof(input.action), "none");
    input.row = -1;
    input.col = -1;
    input.budget_spent = 0;
    input.path_count = 0;
    for (int i = 0; i < MAX_NODES; ++i) {
        input.path_rows[i] = -1;
        input.path_cols[i] = -1;
    }

    std::string text = readTextFile(inputFile());
    if (text.empty()) {
        return input;
    }

    std::string action;
    if (extractString(text, "action", action)) {
        std::snprintf(input.action, sizeof(input.action), "%s", action.c_str());
    }

    int spent = 0;
    if (extractInt(text, "budget_spent", spent)) {
        input.budget_spent = spent;
    }

    std::regex target_pattern("\\\"target\\\"\\s*:\\s*\\{[^\\}]*\\\"row\\\"\\s*:\\s*(-?[0-9]+)[^\\}]*\\\"col\\\"\\s*:\\s*(-?[0-9]+)");
    std::smatch target_match;
    if (std::regex_search(text, target_match, target_pattern)) {
        input.row = std::atoi(target_match[1].str().c_str());
        input.col = std::atoi(target_match[2].str().c_str());
    }

    std::size_t path_pos = text.find("\"path\"");
    if (path_pos != std::string::npos) {
        std::size_t start = text.find('[', path_pos);
        std::size_t end = text.find(']', start);
        if (start != std::string::npos && end != std::string::npos && end > start) {
            std::string body = text.substr(start, end - start + 1);
            std::regex node_pattern("\\{[^\\}]*\\\"row\\\"\\s*:\\s*(-?[0-9]+)[^\\}]*\\\"col\\\"\\s*:\\s*(-?[0-9]+)[^\\}]*\\}");
            auto begin = std::sregex_iterator(body.begin(), body.end(), node_pattern);
            auto finish = std::sregex_iterator();
            for (auto it = begin; it != finish && input.path_count < MAX_NODES; ++it) {
                input.path_rows[input.path_count] = std::atoi((*it)[1].str().c_str());
                input.path_cols[input.path_count] = std::atoi((*it)[2].str().c_str());
                input.path_count++;
            }
        }
    }

    return input;
}

void GameEngine::writeInputNone() const {
    fs::create_directories(resolveSharedPath());
    fs::path file = inputFile();
    fs::path tmp = file;
    tmp += ".tmp";
    std::ofstream out(tmp);
    out << "{\n";
    out << "  \"action\": \"none\",\n";
    out << "  \"target\": {\"row\": -1, \"col\": -1},\n";
    out << "  \"budget_spent\": 0,\n";
    out << "  \"path\": [],\n";
    out << "  \"perimeter\": []\n";
    out << "}\n";
    out.close();
    std::error_code ec;
    fs::remove(file, ec);
    fs::rename(tmp, file, ec);
}

bool GameEngine::applyPatchLikeAction(const char* action, int row, int col, int cost) {
    if (!inside(row, col)) {
        setMessage("Invalid target node");
        return false;
    }
    if (!isHealthy(row, col)) {
        setMessage("Only healthy nodes can be patched");
        return false;
    }
    if (cost > budget) {
        setMessage("Not enough budget");
        return false;
    }

    setPatched(row, col);
    budget -= cost;

    char buffer[180];
    std::snprintf(buffer, sizeof(buffer), "%s applied at (%d, %d)", action, row, col);
    setMessage(buffer);
    return true;
}

void GameEngine::applyBudgetRecovery() {
    if (budget < MAX_BUDGET) {
        budget++;
    }
}

bool GameEngine::validatePath(const EngineInput& input) const {
    if (input.path_count < 2) {
        return false;
    }
    if (input.path_rows[0] != player_row || input.path_cols[0] != player_col) {
        return false;
    }
    for (int i = 0; i < input.path_count; ++i) {
        int row = input.path_rows[i];
        int col = input.path_cols[i];
        if (!isWalkable(row, col)) {
            return false;
        }
        if (i > 0 && !areAdjacent(input.path_rows[i - 1], input.path_cols[i - 1], row, col)) {
            return false;
        }
    }
    return true;
}

bool GameEngine::applyInput(const EngineInput& input) {
    const char* action = input.action;

    if (std::strcmp(action, "none") == 0 || std::strlen(action) == 0) {
        return false;
    }

    if (std::strcmp(action, "quit") == 0) {
        running = false;
        setStatus("stopped");
        setMessage("Engine stopped by UI");
        return true;
    }

    if (std::strcmp(action, "reset") == 0) {
        initGrid();
        setMessage("Game reset by UI");
        return true;
    }

    if (std::strcmp(status, "game_over") == 0 || std::strcmp(status, "victory") == 0) {
        setMessage("The game is finished. Press R to reset.");
        return false;
    }

    bool action_applied = false;

    if (std::strcmp(action, "patch") == 0) {
        if (backtracking_cooldown > 0) backtracking_cooldown--;
        action_applied = applyPatchLikeAction("Patch", input.row, input.col, 1);
    } else if (std::strcmp(action, "reinforce") == 0) {
        if (backtracking_cooldown > 0) backtracking_cooldown--;
        action_applied = applyPatchLikeAction("Reinforce", input.row, input.col, 2);
    } else if (std::strcmp(action, "greedy") == 0) {
        if (backtracking_cooldown > 0) backtracking_cooldown--;
        action_applied = applyPatchLikeAction("Greedy emergency patch", input.row, input.col, greedy_cost);
        if (action_applied) {
            greedy_cost++;
        }
    } else if (std::strcmp(action, "backtracking") == 0) {
        if (backtracking_cooldown > 0) {
            setMessage("Backtracking is on cooldown");
            return false;
        }
        if (!inside(input.row, input.col) || !isWalkable(input.row, input.col)) {
            setMessage("Invalid safe-path target");
            return false;
        }
        if (!areAdjacent(player_row, player_col, input.row, input.col)) {
            setMessage("Backtracking can advance only one safe step");
            return false;
        }
        if (!validatePath(input)) {
            setMessage("Invalid or unsafe Backtracking path");
            return false;
        }

        player_row = input.row;
        player_col = input.col;
        storePath(input);
        backtracking_cooldown = 3;
        action_applied = true;

        char buffer[180];
        std::snprintf(buffer, sizeof(buffer), "Backtracking safe step moved player to (%d, %d)", player_row, player_col);
        setMessage(buffer);
    } else {
        setMessage("Unknown action received");
        return false;
    }

    if (!action_applied) {
        return false;
    }

    turn++;
    spreadVirus();
    applyBudgetRecovery();
    calculateScore();
    updateGameStatus();
    return true;
}

void GameEngine::spreadVirus() {
    int infected_rows[MAX_NODES];
    int infected_cols[MAX_NODES];
    int infected_count = 0;

    for (int row = 0; row < GRID_SIZE; ++row) {
        for (int col = 0; col < GRID_SIZE; ++col) {
            if (grid[row][col].state == INFECTED && infected_count < MAX_NODES) {
                infected_rows[infected_count] = row;
                infected_cols[infected_count] = col;
                infected_count++;
            }
        }
    }

    const int dr[4] = {-1, 1, 0, 0};
    const int dc[4] = {0, 0, -1, 1};

    for (int i = 0; i < infected_count; ++i) {
        int row = infected_rows[i];
        int col = infected_cols[i];
        int offset = (turn + row + col) % 4;

        for (int attempt = 0; attempt < 4; ++attempt) {
            int k = (offset + attempt) % 4;
            int nr = row + dr[k];
            int nc = col + dc[k];
            if (!inside(nr, nc)) continue;
            if (nr == player_row && nc == player_col) continue; // Keep the player marker playable.
            if (grid[nr][nc].state == HEALTHY) {
                grid[nr][nc].state = INFECTED;
                infectionHistory.append(nr, nc, turn, "spread");
                break; // One new infection attempt per infected node per turn keeps the game playable.
            }
        }
    }
}

void GameEngine::writeStateJSON() const {
    fs::create_directories(resolveSharedPath());
    fs::path file = stateFile();
    fs::path tmp = file;
    tmp += ".tmp";

    std::ofstream out(tmp);
    out << "{\n";
    out << "  \"turn\": " << turn << ",\n";
    out << "  \"score\": " << score << ",\n";
    out << "  \"budget\": " << budget << ",\n";
    out << "  \"greedy_cost\": " << greedy_cost << ",\n";
    out << "  \"backtracking_cooldown\": " << backtracking_cooldown << ",\n";
    out << "  \"player\": {\"row\": " << player_row << ", \"col\": " << player_col << "},\n";
    out << "  \"goal\": {\"row\": " << goal_row << ", \"col\": " << goal_col << "},\n";
    out << "  \"grid\": [\n";
    for (int row = 0; row < GRID_SIZE; ++row) {
        out << "    [";
        for (int col = 0; col < GRID_SIZE; ++col) {
            out << grid[row][col].state;
            if (col + 1 < GRID_SIZE) out << ", ";
        }
        out << "]";
        if (row + 1 < GRID_SIZE) out << ",";
        out << "\n";
    }
    out << "  ],\n";

    InfectionEvent events[MAX_NODES * MAX_NODES];
    int event_count = 0;
    infectionHistory.toArray(events, event_count);
    out << "  \"infection_history\": [\n";
    for (int i = 0; i < event_count; ++i) {
        out << "    {\"row\": " << events[i].row
            << ", \"col\": " << events[i].col
            << ", \"turn\": " << events[i].turn
            << ", \"cause\": \"" << jsonEscape(events[i].cause) << "\"}";
        if (i + 1 < event_count) out << ",";
        out << "\n";
    }
    out << "  ],\n";

    out << "  \"greedy_suggestion\": {\"row\": -1, \"col\": -1, \"infected_neighbors\": 0},\n";
    out << "  \"backtracking_path\": [";
    for (int i = 0; i < last_path_count; ++i) {
        out << "{\"row\": " << last_path_rows[i] << ", \"col\": " << last_path_cols[i] << "}";
        if (i + 1 < last_path_count) out << ", ";
    }
    out << "],\n";
    out << "  \"backtracking_perimeter\": [],\n";
    out << "  \"status\": \"" << jsonEscape(status) << "\",\n";
    out << "  \"engine\": \"cpp\",\n";
    out << "  \"message\": \"" << jsonEscape(message) << "\"\n";
    out << "}\n";
    out.close();

    std::error_code ec;
    fs::remove(file, ec);
    fs::rename(tmp, file, ec);
}
