#ifndef VIRUS_DEFENSE_GAME_ENGINE_H
#define VIRUS_DEFENSE_GAME_ENGINE_H

#include "BST.h"
#include "LinkedList.h"

const int GRID_SIZE = 12;
const int MAX_NODES = GRID_SIZE * GRID_SIZE;
const int HEALTHY = 0;
const int INFECTED = 1;
const int PATCHED = 2;
const int INITIAL_BUDGET = 6;
const int MAX_BUDGET = 12;
const int MAX_TURNS = 45;
const int GAME_OVER_INFECTED_LIMIT = 55;

struct Node {
    int row;
    int col;
    int degree;
    int state;
};

struct EngineInput {
    char action[32];
    int row;
    int col;
    int budget_spent;
    int path_count;
    int path_rows[MAX_NODES];
    int path_cols[MAX_NODES];
};

class GameEngine {
private:
    Node grid[GRID_SIZE][GRID_SIZE];
    LinkedList infectionHistory;
    BST degreeIndex;

    int turn;
    int score;
    int budget;
    int greedy_cost;
    int backtracking_cooldown;
    int player_row;
    int player_col;
    int goal_row;
    int goal_col;
    bool running;
    char status[32];
    char message[180];

    int last_path_count;
    int last_path_rows[MAX_NODES];
    int last_path_cols[MAX_NODES];

    int getDegree(int row, int col) const;
    int nodeId(int row, int col) const;
    bool inside(int row, int col) const;
    bool isHealthy(int row, int col) const;
    bool isWalkable(int row, int col) const;
    bool setPatched(int row, int col);
    bool areAdjacent(int r1, int c1, int r2, int c2) const;
    void clearLastPath();
    void storePath(const EngineInput& input);
    void setMessage(const char* text);
    void setStatus(const char* text);
    void updateGameStatus();
    int countInfected() const;
    int countHealthy() const;
    void applyBudgetRecovery();
    bool applyPatchLikeAction(const char* action, int row, int col, int cost);
    bool validatePath(const EngineInput& input) const;

public:
    GameEngine();

    void initGrid();
    bool isRunning() const;
    EngineInput readInputJSON() const;
    void writeInputNone() const;
    bool applyInput(const EngineInput& input);
    void spreadVirus();
    int calculateScore();
    void writeStateJSON() const;
};

#endif
