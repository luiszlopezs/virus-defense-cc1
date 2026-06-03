"""
test_bridge.py — JSON schema validation and read/write tests for the IPC bridge.

Validates that shared/state.json and shared/input.json follow the expected
schemas and that the bridge functions work correctly.

Run with: python experiments/test_bridge.py
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))

from game.bridge.json_bridge import (
    read_state, write_input, SHARED_PATH, _default_state,
)

GRID_SIZE = 12

# Required fields in state.json
STATE_FIELDS = {
    "turn": int,
    "score": int,
    "budget": int,
    "greedy_cost": int,
    "backtracking_cooldown": int,
    "grid": list,
    "infection_history": list,
    "greedy_suggestion": dict,
    "backtracking_perimeter": list,
}

# Required fields in input.json
INPUT_FIELDS = {
    "action": str,
    "target": dict,
    "budget_spent": int,
}


class TestDefaultState(unittest.TestCase):

    def test_has_all_fields(self):
        state = _default_state()
        for field, expected_type in STATE_FIELDS.items():
            self.assertIn(field, state, f"Missing field: {field}")
            self.assertIsInstance(state[field], expected_type)

    def test_grid_dimensions(self):
        state = _default_state()
        self.assertEqual(len(state["grid"]), GRID_SIZE)
        for row in state["grid"]:
            self.assertEqual(len(row), GRID_SIZE)

    def test_greedy_suggestion_has_row_col(self):
        state = _default_state()
        self.assertIn("row", state["greedy_suggestion"])
        self.assertIn("col", state["greedy_suggestion"])


class TestReadState(unittest.TestCase):

    def test_returns_defaults_when_missing(self):
        state = read_state()
        self.assertIsInstance(state, dict)
        self.assertIn("turn", state)
        self.assertIn("grid", state)

    def test_returns_dict(self):
        state = read_state()
        self.assertIsInstance(state, dict)

    def test_has_core_fields(self):
        state = read_state()
        for field in ["turn", "score", "budget", "grid", "infection_history",
                       "greedy_suggestion", "backtracking_perimeter"]:
            self.assertIn(field, state, f"Missing field: {field}")

    def test_state_matches_defaults_fill(self):
        defaults = _default_state()
        state = read_state()
        merged = {**defaults, **state}
        for field, expected_type in STATE_FIELDS.items():
            self.assertIn(field, merged, f"Missing field: {field}")
            self.assertIsInstance(merged[field], expected_type)


class TestWriteInput(unittest.TestCase):

    def test_creates_valid_json(self):
        write_input("patch", (3, 7), 1)
        input_path = os.path.join(SHARED_PATH, "input.json")
        self.assertTrue(os.path.exists(input_path))
        with open(input_path, "r") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_schema_has_required_fields(self):
        write_input("greedy", (5, 5), 2)
        input_path = os.path.join(SHARED_PATH, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        for field in INPUT_FIELDS:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_target_has_row_col(self):
        write_input("patch", (10, 2), 1)
        input_path = os.path.join(SHARED_PATH, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        self.assertIn("row", data["target"])
        self.assertIn("col", data["target"])
        self.assertEqual(data["target"]["row"], 10)
        self.assertEqual(data["target"]["col"], 2)

    def test_action_and_budget_spent(self):
        write_input("backtracking", (5, 5), 5)
        input_path = os.path.join(SHARED_PATH, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["action"], "backtracking")
        self.assertEqual(data["budget_spent"], 5)


class TestRoundTrip(unittest.TestCase):

    def test_write_then_read(self):
        write_input("reinforce", (8, 3), 2)
        input_path = os.path.join(SHARED_PATH, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["action"], "reinforce")
        self.assertEqual(data["target"]["row"], 8)
        self.assertEqual(data["target"]["col"], 3)
        self.assertEqual(data["budget_spent"], 2)


class TestCorruptedJsonFallback(unittest.TestCase):

    def test_malformed_json_returns_defaults(self):
        input_path = os.path.join(SHARED_PATH, "input.json")
        backup = None
        if os.path.exists(input_path):
            with open(input_path, "r") as f:
                backup = f.read()
        try:
            with open(input_path, "w") as f:
                f.write("{not valid json!!!")
            state = read_state()
            self.assertIsInstance(state, dict)
            self.assertIn("turn", state)
        finally:
            if backup is not None:
                with open(input_path, "w") as f:
                    f.write(backup)


if __name__ == "__main__":
    unittest.main()
