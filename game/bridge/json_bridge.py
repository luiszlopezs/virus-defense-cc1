"""
json_bridge.py — JSON-based communication bridge for Virus Defense.

This module sits between the Python algorithm layer (``game/``) and
the C++ engine.  Both sides exchange data through two JSON files
stored in the ``shared/`` directory at the project root:

    shared/state.json   — written by C++ engine, read by Python
    shared/input.json   — written by Python, read by C++ engine

File paths are resolved relative to *this* script's location so that
the bridge works regardless of the working directory.
"""

from __future__ import annotations

import json
import os

# ──────────────────────────────────────────────
# Path resolution
# ──────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, os.pardir, os.pardir))
SHARED_PATH: str = os.path.join(_PROJECT_ROOT, "shared")
"""Absolute path to the ``shared/`` directory used for IPC."""


def _default_state() -> dict:
    """Return the canonical initial game state used when ``state.json``
    is missing or cannot be parsed."""
    return {
        "turn": 0,
        "score": 0,
        "budget": 5,
        "greedy_cost": 1,
        "backtracking_cooldown": 0,
        "player_pos": {"row": 0, "col": 6},
        "goal_pos": {"row": 11, "col": 6},
        "player_infected": False,
        "goal_infected": False,
        "grid": [[0] * 12 for _ in range(12)],
        "infection_history": [],
        "greedy_suggestion": {"row": -1, "col": -1},
        "backtracking_perimeter": [],
    }


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────
def read_state() -> dict:
    """Read and return the current game state from ``shared/state.json``.

    If the file does not exist or contains malformed JSON, a safe
    default state is returned instead.
    """
    state_file = os.path.join(SHARED_PATH, "state.json")
    try:
        with open(state_file, "r", encoding="utf-8") as fh:
            data: dict = json.load(fh)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _default_state()


def write_input(action: str, target: tuple[int, int], budget_spent: int) -> None:
    """Write a player action to ``shared/input.json``.

    Parameters
    ----------
    action : str
        The action identifier, e.g. ``"patch"``, ``"greedy"``, or
        ``"backtracking"``.
    target : tuple[int, int]
        ``(row, col)`` coordinates of the target cell.
    budget_spent : int
        Number of budget points consumed by this action.
    """
    payload = {
        "action": action,
        "target": {"row": target[0], "col": target[1]},
        "budget_spent": budget_spent,
    }
    try:
        os.makedirs(SHARED_PATH, exist_ok=True)
        input_file = os.path.join(SHARED_PATH, "input.json")
        with open(input_file, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
    except OSError:
        pass
