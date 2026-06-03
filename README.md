# Virus Defense — Team 10, Variant 10

**Course:** Computer Sciences I — Universidad Distrital Francisco José de Caldas, 2026-I  
**Professor:** Eng. Carlos Andrés Sierra

## Team

| Role                | Name                      | Language(s)      |
|---------------------|---------------------------|------------------|
| Engine Developer    | Luis Fernando Lopez Pardo | C++              |
| Algorithm Developer | Maria Jose Polanco Charry | Python           |
| UI Developer        | Alicia Pineda Quiroga     | Python + Pygame  |

Virus Defense is a strategy game project where players contain infections on a grid-based map under a limited budget each turn, while the C++ engine handles core game state and data structures and the Python side provides algorithmic decision support and rendering.

## Architecture

```text
+--------------------+           +------------------------+
|  C++ Engine        |  writes   | shared/state.json      |
|  (game state,      +---------->+ shared/input.json      |
|   LinkedList, BST) |<----------+ (bridge files)         |
+--------------------+  reads    +------------------------+
           ^                                  ^
           |                                  |
           |                                  |
+--------------------+           +------------------------+
| Python + Pygame    |  reads/   | Local same-machine     |
| (greedy,           |  writes   | file-based integration |
| backtracking, UI)  |           | (no sockets)           |
+--------------------+           +------------------------+
```

## Prerequisites

- **C++ Engine**: CMake 3.16+, C++17 compiler (GCC 7+, Clang 5+, or MSVC 2017+)
- **Python Client**: Python 3.8+, Pygame 2.5+
- **nlohmann/json**: Already bundled at `engine/include/json.hpp`

## Build (C++)

### Option A: CMake (recommended)

```bash
cd engine
cmake -S . -B build
cmake --build build
```

The executable will be at `engine/build/virus_engine`.

### Option B: GCC/Clang directly

```bash
cd engine
g++ -std=c++17 -O2 -Iinclude -Isrc \
    src/main.cpp src/GameEngine.cpp src/LinkedList.cpp src/BST.cpp \
    -o ../virus_engine
```

### Option C: MSVC (Windows)

```bash
cd engine
cl /std:c++17 /EHsc /I include /I src ^
    src\main.cpp src\GameEngine.cpp src\LinkedList.cpp src\BST.cpp
```

## Run (Python)

```bash
cd game
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Run both (IPC mode)

```bash
# Terminal 1 — C++ engine
cd engine/build && ./virus_engine

# Terminal 2 — Python client
cd game && python main.py
```

The Python client auto-detects the C++ engine by checking `shared/state.json` modification time. When the engine is not running, a built-in Python engine is used instead.

## Run Tests & Benchmarks

```bash
# Unit tests for algorithms
python experiments/test_algorithms.py

# JSON bridge validation
python experiments/test_bridge.py

# Python algorithm performance benchmark
python experiments/algorithm_benchmark.py

# C++ engine benchmark (requires compilation)
cd engine && g++ -std=c++17 -O2 -Iinclude -Isrc \
    ../experiments/engine_benchmark.cpp src/GameEngine.cpp \
    src/LinkedList.cpp src/BST.cpp -o ../experiments/engine_benchmark
../experiments/engine_benchmark
```

Results are written to `results/`.

## Folder structure

- `engine/`: C++ engine and data structures.
  - `src/`: Source files (GameEngine, LinkedList, BST, main).
  - `include/json.hpp`: nlohmann JSON header-only library.
  - `CMakeLists.txt`: Build configuration.
- `game/`: Python algorithms and Pygame UI.
  - `algorithms/`: greedy.py, backtracking.py, grid_utils.py.
  - `bridge/`: json_bridge.py (file-based IPC).
  - `ui/`: renderer.py (premium Pygame interface).
- `shared/`: JSON files used as the bridge between C++ and Python.
- `experiments/`: Tests and benchmarks.
- `results/`: Benchmark output files.
- `.gitignore`: ignores build, cache, and editor artifacts.

## Game Controls

| Input | Action |
|-------|--------|
| Click | Patch a HEALTHY node (cost: 1) |
| Shift+Click | Reinforce a HEALTHY node (cost: 2) |
| G | Apply Greedy suggestion (variable cost) |
| B | Toggle/Apply Backtracking perimeter |
| N | Pass turn |
| R | Restart |
| ESC | Quit |
