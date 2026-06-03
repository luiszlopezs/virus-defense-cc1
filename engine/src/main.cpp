#include "GameEngine.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <chrono>
#include <thread>

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

int main() {
    GameEngine engine;
    engine.initGrid();
    engine.writeStateJSON();

    std::cout << "Virus Engine started. Waiting for actions in shared/input.json..." << std::endl;

    while (true) {
        std::ifstream file("shared/input.json");
        if (file.is_open()) {
            std::string content((std::istreambuf_iterator<char>(file)),
                                 std::istreambuf_iterator<char>());
            file.close();

            std::string action = extractField(content, "action");
            int row = extractInt(content, "row");
            int col = extractInt(content, "col");

            if (action.empty()) action = "idle";

            if (action == "quit") {
                std::cout << "Quit action received. Exiting engine." << std::endl;
                break;
            }

            if (action != "idle" && (action == "patch" || action == "greedy" ||
                                     action == "backtracking" || action == "none")) {

                std::cout << "Processing action: " << action
                          << " on target (" << row << ", " << col << ")" << std::endl;

                // 1. Decrement cooldowns
                if (engine.backtracking_cooldown > 0) {
                    engine.backtracking_cooldown--;
                }

                // 2. Map action to code and apply
                int action_code = 0;
                if (action == "patch") action_code = 1;
                else if (action == "greedy") action_code = 3;
                else if (action == "backtracking") action_code = 4;

                if (action_code > 0) {
                    engine.applyAction(row, col, action_code);
                }

                // 3. Spread the virus
                engine.spreadVirus();

                // 4. Progress turn and increment budget
                engine.turn++;
                engine.budget += 2;

                // 5. Update score and save state
                engine.calculateScore();
                engine.writeStateJSON();

                // 6. Reset input.json to "idle"
                std::ofstream out("shared/input.json");
                if (out.is_open()) {
                    out << "{\n"
                        << "  \"action\": \"idle\",\n"
                        << "  \"target\": { \"row\": -1, \"col\": -1 },\n"
                        << "  \"budget_spent\": 0\n"
                        << "}";
                    out.close();
                }
            }
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(300));
    }

    return 0;
}
