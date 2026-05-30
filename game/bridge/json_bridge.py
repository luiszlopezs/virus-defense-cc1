import json
import os

# =========================
# SHARED PATH
# =========================
# Ruta relativa a la carpeta shared/
SHARED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "shared")


# =========================
# READ STATE
# =========================
def read_state() -> dict:
    """
    Reads the current game state from shared/state.json.

    JSON Schema:
    {
        "turn": int,
        "score": int,
        "budget": int,
        "greedy_cost": int,
        "backtracking_cooldown": int,
        "grid": list[list[int]],
        "infection_history": list,
        "greedy_suggestion": {"row": int, "col": int},
        "backtracking_perimeter": list[tuple[int,int]]
    }

    If the file does not exist or is malformed,
    returns a default initial state.
    """

    state_path = os.path.join(SHARED_PATH, "state.json")

    try:
        with open(state_path, "r") as f:
            return json.load(f)

    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        # Estado inicial por defecto
        return {
            "turn": 0,
            "score": 0,
            "budget": 3,
            "greedy_cost": 1,
            "backtracking_cooldown": 0,
            "grid": [[0]*12 for _ in range(12)],
            "infection_history": [],
            "greedy_suggestion": {"row": -1, "col": -1},
            "backtracking_perimeter": []
        }


# =========================
# WRITE INPUT : Write the player's action.
# =========================
def write_input(action: str, target: tuple, budget_spent: int) -> None:
    """
    Writes the player's action into shared/input.json.

    JSON Schema:
    {
        "action": str,
        "target": {"row": int, "col": int},
        "budget_spent": int
    }

    Allowed actions:
    - "patch"
    - "reinforce"
    - "greedy"
    - "backtracking"
    - "none"
    - "quit"
    """

    input_path = os.path.join(SHARED_PATH, "input.json")

    data = {
        "action": action,
        "target": {
            "row": target[0] if target else -1,
            "col": target[1] if target else -1
        },
        "budget_spent": budget_spent
    }

    try:
        with open(input_path, "w") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        print(f"Error writing input.json: {e}")