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

## Build (C++)

```bash
cd engine
cmake -S . -B build
cmake --build build
```

## Run (Python)

```bash
cd game
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

## Folder structure

- `engine/`: C++ engine and data structures.
- `game/`: Python algorithms and Pygame UI.
- `shared/`: JSON files used as the bridge between C++ and Python.
- `.gitignore`: ignores build, cache, and editor artifacts.
