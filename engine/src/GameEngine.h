#ifndef GAMEENGINE_H
#define GAMEENGINE_H

#include "LinkedList.h"
#include "BST.h"

// Constants defining the grid size and cell states.
const int GRID_SIZE = 12;
const int HEALTHY = 0;
const int INFECTED = 1;
const int PATCHED = 2;

// Node represents a single cell in the grid.
struct Node {
    int row;
    int col;
    int degree; // Number of healthy neighbors
    int state;  // HEALTHY, INFECTED, or PATCHED
};

// Point helper struct for coordinating positions.
struct Point {
    int r, c;
};

// GameEngine handles the core simulation rules, including virus spreading and action applications.
class GameEngine {
public:
    Node grid[GRID_SIZE][GRID_SIZE];
    int turn;
    int score;
    int budget;
    int greedy_cost;
    int backtracking_cooldown;
    LinkedList infection_history;
    BST bst;

    // Player and goal positions
    int player_row, player_col;
    int goal_row, goal_col;

    // Flags set after virus spreads
    bool player_infected;
    bool goal_infected;

    // Cache for the backtracking perimeter so it can be written to state.json
    Point backtracking_perimeter[144];
    int backtracking_perimeter_size;

    GameEngine();
    
    void initGrid();
    void spreadVirus();
    void applyAction(int row, int col, int action_code);
    void writeStateJSON();
    void readInputJSON();
    int calculateScore();

    // Helper to run C++ backtracking and update the backtracking_perimeter cache
    void computeBacktrackingPerimeter();

private:
    int calculateNodeDegree(int r, int c) const;
    void updateConnectivityDegrees(int row, int col);
    bool isClusterContained(Point* perimeter, int size) const;
    void backtrackSearch(int index, Point* current_perimeter, int current_size, Point* boundary, int boundary_count);
};

#endif // GAMEENGINE_H
