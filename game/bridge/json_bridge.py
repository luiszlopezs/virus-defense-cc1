"""JSON bridge between the Python UI and the C++ engine."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

try:
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, normalize_grid
except ImportError:  # pragma: no cover
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, normalize_grid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_PATH = PROJECT_ROOT / "shared"
STATE_FILE = SHARED_PATH / "state.json"
INPUT_FILE = SHARED_PATH / "input.json"

VALID_ACTIONS = {"patch", "reinforce", "greedy", "backtracking", "none", "quit", "reset", "move"}
Position = tuple[int, int]


def create_initial_state() -> dict[str, Any]:
    """Create a playable fallback state when the C++ engine is not running."""
    grid = [[HEALTHY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    grid[5][5] = INFECTED

    return {
        "turn": 0,
        "score": calculate_score(grid),
        "budget": 6,
        "greedy_cost": 1,
        "backtracking_cooldown": 0,
        "grid": grid,
        "player": {"row": 0, "col": 0},
        "goal": {"row": GRID_SIZE - 1, "col": GRID_SIZE - 1},
        "infection_history": [{"row": 5, "col": 5, "turn": 0, "cause": "initial_seed"}],
        "greedy_suggestion": {"row": -1, "col": -1, "infected_neighbors": 0},
        "backtracking_path": [],
        "backtracking_perimeter": [],  # Kept for compatibility with older builds.
        "status": "ui_fallback",
        "engine": "python_fallback",
        "message": "Python fallback state active",
    }


def calculate_score(grid: list[list[int]]) -> int:
    """Fallback score. The C++ engine provides the official score when active."""
    score = 0
    for row in grid:
        for cell in row:
            if cell == HEALTHY:
                score += 10
            elif cell == INFECTED:
                score -= 5
    return score


def _normalize_position(value: Any, default: Position) -> dict[str, int]:
    if not isinstance(value, dict):
        return {"row": default[0], "col": default[1]}
    try:
        row = int(value.get("row", default[0]))
        col = int(value.get("col", default[1]))
    except (TypeError, ValueError):
        row, col = default
    row = max(0, min(GRID_SIZE - 1, row))
    col = max(0, min(GRID_SIZE - 1, col))
    return {"row": row, "col": col}


def _normalize_position_list(value: Any) -> list[dict[str, int]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, int]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            row = int(item.get("row", -1))
            col = int(item.get("col", -1))
        except (TypeError, ValueError):
            continue
        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            out.append({"row": row, "col": col})
    return out


def normalize_state(raw_state: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure every required field exists and has a safe type."""
    state = create_initial_state()
    if isinstance(raw_state, dict):
        state.update(raw_state)

    state["grid"] = normalize_grid(state.get("grid"), GRID_SIZE)

    for key, default_value in (
        ("turn", 0),
        ("score", calculate_score(state["grid"])),
        ("budget", 6),
        ("greedy_cost", 1),
        ("backtracking_cooldown", 0),
    ):
        try:
            state[key] = int(state.get(key, default_value))
        except (TypeError, ValueError):
            state[key] = default_value

    state["player"] = _normalize_position(state.get("player"), (0, 0))
    state["goal"] = _normalize_position(state.get("goal"), (GRID_SIZE - 1, GRID_SIZE - 1))

    if not isinstance(state.get("infection_history"), list):
        state["infection_history"] = []
    if not isinstance(state.get("greedy_suggestion"), dict):
        state["greedy_suggestion"] = {"row": -1, "col": -1, "infected_neighbors": 0}

    state["backtracking_path"] = _normalize_position_list(state.get("backtracking_path"))
    state["backtracking_perimeter"] = _normalize_position_list(state.get("backtracking_perimeter"))

    if not isinstance(state.get("status"), str):
        state["status"] = "ui_fallback"
    if not isinstance(state.get("engine"), str):
        state["engine"] = "python_fallback"
    if not isinstance(state.get("message"), str):
        state["message"] = ""

    return state


def read_state() -> dict[str, Any]:
    """Read shared/state.json, returning a safe fallback if the file is missing."""
    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            raw_state = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return create_initial_state()

    return normalize_state(raw_state)


def write_state(state: dict[str, Any]) -> None:
    """Write a normalized fallback state to shared/state.json."""
    SHARED_PATH.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state(deepcopy(state))
    tmp = STATE_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=2, ensure_ascii=False)
    tmp.replace(STATE_FILE)


def _serialize_positions(nodes: Iterable[Position] | None) -> list[dict[str, int]]:
    if nodes is None:
        return []
    return [{"row": int(row), "col": int(col)} for row, col in nodes]


def write_input(
    action: str,
    target: Position = (-1, -1),
    budget_spent: int = 0,
    perimeter: Iterable[Position] | None = None,
    path: Iterable[Position] | None = None,
) -> None:
    """
    Write shared/input.json using the C++ engine schema.

    Greedy sends a target node to patch.
    Backtracking sends a safe path and a target step so the engine can validate
    the movement and update the official player position.
    """
    if action not in VALID_ACTIONS:
        action = "none"

    row, col = target
    payload = {
        "action": action,
        "target": {"row": int(row), "col": int(col)},
        "budget_spent": int(budget_spent),
        "path": _serialize_positions(path),
        "perimeter": _serialize_positions(perimeter),
    }

    SHARED_PATH.mkdir(parents=True, exist_ok=True)
    tmp = INPUT_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    tmp.replace(INPUT_FILE)


def reset_shared_state() -> dict[str, Any]:
    """Reset both JSON files for Python fallback mode."""
    state = create_initial_state()
    write_state(state)
    write_input("none", (-1, -1), 0)
    return state
