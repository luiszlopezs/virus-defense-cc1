"""
json_bridge.py — JSON-based communication bridge for Virus Defense.

This module sits between the Python algorithm layer (``game/``) and
the Godot front-end.  Both sides exchange data through two JSON files
stored in the ``shared/`` directory at the project root:

    shared/state.json   — written by Godot, read by Python
    shared/input.json   — written by Python, read by Godot

File paths are resolved relative to *this* script's location so that
the bridge works regardless of the working directory.

JSON Schemas
────────────

**state.json** (Godot → Python)::

    {
        "turn":                   int,        // current turn number
        "score":                  int,        // player's accumulated score
        "budget":                 int,        // remaining action budget this turn
        "greedy_cost":            int,        // budget cost of a greedy patch
        "backtracking_cooldown":  int,        // turns until backtracking is available
        "grid":                   int[][],    // 12×12 array of 0/1/2
        "infection_history":      [int, ...], // infected-count per past turn
        "greedy_suggestion":      {"row": int, "col": int},
        "backtracking_perimeter": [{"row": int, "col": int}, ...]
    }

**input.json** (Python → Godot)::

    {
        "action":       str,          // e.g. "patch", "greedy", "quarantine"
        "target":       {"row": int, "col": int},
        "budget_spent": int
    }
"""

from __future__ import annotations

import json
import os

# ──────────────────────────────────────────────
# Path resolution
# ──────────────────────────────────────────────
# This file lives at  <project>/game/bridge/json_bridge.py
# We need              <project>/shared/
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
        "budget": 3,
        "greedy_cost": 1,
        "backtracking_cooldown": 0,
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
    default state is returned instead (turn 0, empty grid, full budget).

    Returns
    -------
    dict
        A dictionary conforming to the *state.json* schema described in
        the module docstring.

    Raises
    ------
    Never raises — all I/O and parsing errors are caught internally.

    Examples
    --------
    >>> state = read_state()
    >>> len(state["grid"])
    12
    >>> state["budget"]
    3
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
        ``"quarantine"``.
    target : tuple[int, int]
        ``(row, col)`` coordinates of the target cell.
    budget_spent : int
        Number of budget points consumed by this action.

    Raises
    ------
    Never raises — I/O errors are caught and silently ignored so the
    game loop is never interrupted by a write failure.

    Notes
    -----
    The ``shared/`` directory is created automatically if it does not
    already exist.

    Examples
    --------
    >>> write_input("patch", (3, 7), 1)
    # Creates/overwrites shared/input.json with:
    # {"action": "patch", "target": {"row": 3, "col": 7}, "budget_spent": 1}
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
