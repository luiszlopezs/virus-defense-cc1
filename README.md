# Virus Defense

Virus Defense is a 12x12 grid-based strategy game that demonstrates two algorithmic ideas:

- **Greedy emergency patching:** the game evaluates the current board and recommends the healthy node with the highest number of infected neighbors. This is a fast immediate-response decision: patch the node under the greatest current danger.
- **Backtracking safe path:** the game searches for a safe route from the player's current position to the goal while avoiding infected nodes. If a branch is blocked, the algorithm backtracks and tries an alternative route.

The project keeps the planned architecture:

```text
C++ Engine  <->  shared JSON files  <->  Python/Pygame UI
```

## Main features

- Functional C++ engine.
- 12x12 official board state.
- Virus propagation by turns.
- Official budget, score, Greedy cost and Backtracking cooldown handled by C++.
- Infection history stored with a custom linked list.
- BST index for node connectivity.
- Python Greedy and Backtracking algorithms used by the UI.
- Pygame visual interface fully in English.
- Resizable window and F11 fullscreen mode.
- Blue patched/protected nodes to match the poster legend.

## Controls

| Control | Action |
|---|---|
| Click | Patch a selected healthy node |
| Shift + Click | Reinforce a healthy node |
| G | Apply the Greedy emergency patch suggestion |
| B | Preview / advance one step along the Backtracking safe path |
| R | Reset game |
| F11 | Toggle fullscreen |
| ESC | Quit |

## How to run the UI only

The UI can run even if the C++ engine is not compiled. In that case, Python fallback mode is used.

```bash
cd game
python -m venv .venv
```

Windows CMD:

```cmd
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Git Bash / Linux / macOS:

```bash
source .venv/Scripts/activate  # Git Bash on Windows
# or: source .venv/bin/activate # Linux/macOS
pip install -r requirements.txt
python main.py
```

## How to compile and run with the C++ engine

Install CMake first. Then:

```bash
cd engine
cmake -S . -B build
cmake --build build
```

After compilation, run the UI:

```bash
cd ../game
python main.py
```

The UI automatically starts the compiled engine if it finds `engine/build/virus_engine` or `engine/build/virus_engine.exe`.

## Algorithm behavior

### Greedy

Greedy scans the board and selects the healthy node with the largest number of infected neighbors. This is an emergency patch decision. It does not forecast future turns.

Tie-breakers:

1. More infected neighbors.
2. More healthy exits.
3. Closer to the player.
4. First node found.

### Backtracking

Backtracking searches for a safe route from the player to the goal `(11, 11)`. It recursively explores orthogonal moves, avoids infected nodes, and backtracks whenever it reaches a dead end.

When the player presses `B`:

1. First press: shows the safe path preview.
2. Second press: advances the player one safe step along that route and activates cooldown.

## Shared JSON schema

`shared/state.json` includes:

```json
{
  "turn": 0,
  "score": 1425,
  "budget": 6,
  "greedy_cost": 1,
  "backtracking_cooldown": 0,
  "player": {"row": 0, "col": 0},
  "goal": {"row": 11, "col": 11},
  "grid": [[0, 0]],
  "infection_history": [],
  "greedy_suggestion": {"row": -1, "col": -1, "infected_neighbors": 0},
  "backtracking_path": [],
  "status": "engine_running",
  "engine": "cpp",
  "message": "C++ engine ready"
}
```

`shared/input.json` includes:

```json
{
  "action": "none",
  "target": {"row": -1, "col": -1},
  "budget_spent": 0,
  "path": []
}
```
