"""
JSON bridge between the Python UI and the future C++ engine.

Current status:
- If the C++ engine has not written shared/state.json yet, the UI receives a
  safe simulated state.
- Player actions are always written to shared/input.json, preserving the final
  integration contract.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, normalize_grid
except ImportError:  # pragma: no cover
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, normalize_grid

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_PATH = PROJECT_ROOT / "shared"
STATE_FILE = SHARED_PATH / "state.json"
INPUT_FILE = SHARED_PATH / "input.json"

VALID_ACTIONS = {"patch", "reinforce", "greedy", "backtracking", "none", "quit", "reset"}


def create_initial_state() -> dict[str, Any]:
    """Create a valid default state for the standalone Pygame UI."""
    grid = [[HEALTHY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    grid[5][5] = INFECTED
    grid[5][6] = HEALTHY

    return {
        "turn": 0,
        "score": calculate_score(grid),
        "budget": 6,
        "greedy_cost": 1,
        "backtracking_cooldown": 0,
        "grid": grid,
        "infection_history": [{"row": 5, "col": 5, "turn": 0, "cause": "initial_seed"}],
        "greedy_suggestion": {"row": -1, "col": -1},
        "backtracking_perimeter": [],
        "status": "simulated",
    }


def calculate_score(grid: list[list[int]]) -> int:
    """Simple UI score used until the C++ engine provides the official value."""
    score = 0
    for row in grid:
        for cell in row:
            if cell == HEALTHY:
                score += 10
            elif cell == INFECTED:
                score -= 5
    return score


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

    if not isinstance(state.get("infection_history"), list):
        state["infection_history"] = []
    if not isinstance(state.get("greedy_suggestion"), dict):
        state["greedy_suggestion"] = {"row": -1, "col": -1}
    if not isinstance(state.get("backtracking_perimeter"), list):
        state["backtracking_perimeter"] = []

    return state


def read_state() -> dict[str, Any]:
    """
    Read shared/state.json.

    If the file does not exist, is invalid JSON, or is incomplete, a normalized
    fallback state is returned so the UI can keep running independently.
    """
    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            raw_state = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return create_initial_state()

    return normalize_state(raw_state)


def write_state(state: dict[str, Any]) -> None:
    """Write a normalized state to shared/state.json."""
    SHARED_PATH.mkdir(parents=True, exist_ok=True)
    normalized = normalize_state(deepcopy(state))
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=2, ensure_ascii=False)


def write_input(action: str, target: tuple[int, int] = (-1, -1), budget_spent: int = 0) -> None:
    """
    Write shared/input.json using the expected engine schema.

    Schema:
    {
      "action": "patch" | "reinforce" | "greedy" | "backtracking" | "none" | "quit" | "reset",
      "target": {"row": int, "col": int},
      "budget_spent": int
    }
    """
    if action not in VALID_ACTIONS:
        action = "none"

    row, col = target
    payload = {
        "action": action,
        "target": {"row": int(row), "col": int(col)},
        "budget_spent": int(budget_spent),
    }

    SHARED_PATH.mkdir(parents=True, exist_ok=True)
    with INPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def reset_shared_state() -> dict[str, Any]:
    """Reset both JSON files to a playable standalone state."""
    state = create_initial_state()
    write_state(state)
    write_input("none", (-1, -1), 0)
    return state
