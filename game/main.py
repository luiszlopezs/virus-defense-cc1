"""
Virus Defense — Main Game Loop
================================
Integrates the Python game engine, algorithms, renderer, and JSON bridge
into a cohesive Pygame application.

When the C++ engine is running, this client communicates via shared/state.json
and shared/input.json. When the C++ engine is NOT running, this file uses a
built-in Python engine to simulate the same game logic standalone.

Controls:
    Click         → Patch a HEALTHY node (1 budget)
    Shift+Click   → Reinforce node + neighbors (3 budget)
    G             → Apply Greedy suggestion (variable cost)
    B             → Toggle/Apply Backtracking perimeter
    N             → Pass turn (no action)
    R             → Restart game
    ESC           → Quit

Author: Alicia Pineda Quiroga (UI Developer)
"""

import pygame
import sys
import os
import time
import math
import copy
import random

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.renderer import Renderer
from algorithms.grid_utils import (
    GRID_SIZE, HEALTHY, INFECTED, PATCHED,
    get_neighbors, get_degree, get_healthy_degree,
    get_boundary_nodes, is_infected_cluster_empty, count_infected,
    is_virus_contained
)
from algorithms.greedy import get_greedy_suggestion
from algorithms.backtracking import get_quarantine_perimeter
from bridge.json_bridge import read_state, write_input, SHARED_PATH


# ─── Python-native Game Engine (mirrors C++ engine logic) ───

class PythonEngine:
    """
    Self-contained game engine that runs when the C++ engine is not available.
    Mirrors the exact same game rules defined in the plan.
    """

    def __init__(self):
        self.grid = [[HEALTHY] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.turn = 0
        self.score = 0
        self.budget = 5
        self.greedy_cost = 1
        self.backtracking_cooldown = 0
        self.reinforce_cooldown = 0
        self.infection_history = []
        self.greedy_suggestion = (-1, -1)
        self.backtracking_perimeter = []

        # Place initial infection at a random position
        start_r = random.randint(0, GRID_SIZE - 1)
        start_c = random.randint(0, GRID_SIZE - 1)
        self.grid[start_r][start_c] = INFECTED
        self.infection_history.append({
            "row": start_r, "col": start_c, "turn": 0, "cause": "initial"
        })
        self.score = self.calculate_score()

    def calculate_score(self):
        """Score: +10 for HEALTHY, -5 for INFECTED, +5 for PATCHED."""
        s = 0
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == HEALTHY:
                    s += 10
                elif self.grid[r][c] == INFECTED:
                    s -= 5
                elif self.grid[r][c] == PATCHED:
                    s += 5
        self.score = s
        return s

    SPREAD_CHANCE = 0.50  # 50% chance per neighbor per turn

    def spread_virus(self):
        """Spread virus from all infected nodes to their healthy neighbors probabilistically."""
        new_infections = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == INFECTED:
                    for nr, nc in get_neighbors(self.grid, r, c):
                        if self.grid[nr][nc] == HEALTHY and random.random() < self.SPREAD_CHANCE:
                            new_infections.append((nr, nc))

        for nr, nc in new_infections:
            if self.grid[nr][nc] == HEALTHY:
                self.grid[nr][nc] = INFECTED
                self.infection_history.append({
                    "row": nr, "col": nc, "turn": self.turn, "cause": "spread"
                })

    def apply_patch(self, row, col):
        """Patch a HEALTHY node (cost: 1 budget)."""
        if (self.budget >= 1 and 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE
                and self.grid[row][col] == HEALTHY):
            self.grid[row][col] = PATCHED
            self.budget -= 1
            return True
        return False

    def apply_reinforce(self, row, col):
        """Reinforce a HEALTHY node + patch all healthy neighbors (cost: 3 budget, 3 turn cooldown)."""
        if (self.reinforce_cooldown == 0
                and 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE
                and self.grid[row][col] == HEALTHY):
            patched = []
            self.grid[row][col] = PATCHED
            patched.append((row, col))
            for nr, nc in get_neighbors(self.grid, row, col):
                if self.grid[nr][nc] == HEALTHY:
                    self.grid[nr][nc] = PATCHED
                    patched.append((nr, nc))
            self.budget -= 3
            self.reinforce_cooldown = 3
            return True, patched
        return False, []

    def apply_greedy(self, row, col):
        """Apply greedy suggestion (cost: greedy_cost, then increment cost)."""
        if (self.budget >= self.greedy_cost and 0 <= row < GRID_SIZE
                and 0 <= col < GRID_SIZE and self.grid[row][col] == HEALTHY):
            self.grid[row][col] = PATCHED
            self.budget -= self.greedy_cost
            self.greedy_cost += 1
            return True
        return False

    def apply_backtracking(self, perimeter):
        """Apply backtracking perimeter (cost: len(perimeter), then cooldown=3)."""
        cost = len(perimeter)
        if self.backtracking_cooldown == 0 and self.budget >= cost and cost > 0:
            for r, c in perimeter:
                if self.grid[r][c] == HEALTHY:
                    self.grid[r][c] = PATCHED
            self.budget -= cost
            self.backtracking_cooldown = 3
            return True
        return False

    def advance_turn(self):
        """Progress one turn: decrement cooldowns, spread virus, add budget."""
        if self.backtracking_cooldown > 0:
            self.backtracking_cooldown -= 1
        if self.reinforce_cooldown > 0:
            self.reinforce_cooldown -= 1

        self.spread_virus()

        self.turn += 1
        self.budget += 4
        self.calculate_score()

    def get_state_dict(self):
        return {
            "turn": self.turn,
            "score": self.score,
            "budget": self.budget,
            "greedy_cost": self.greedy_cost,
            "backtracking_cooldown": self.backtracking_cooldown,
            "reinforce_cooldown": self.reinforce_cooldown,
            "grid": [row[:] for row in self.grid],
            "infection_history": self.infection_history[:],
            "greedy_suggestion": {"row": self.greedy_suggestion[0], "col": self.greedy_suggestion[1]},
            "backtracking_perimeter": [{"row": r, "col": c} for r, c in self.backtracking_perimeter]
        }


# ─── Game State Enum ───

STATE_START = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_VICTORY = 3


# ─── Detect C++ Engine ───

def is_cpp_engine_running():
    """Check if the C++ engine is updating state.json (modified in last 2s)."""
    state_path = os.path.join(SHARED_PATH, "state.json")
    try:
        mtime = os.path.getmtime(state_path)
        return (time.time() - mtime) < 2.0
    except OSError:
        return False


# ─── Main Application ───

def main():
    pygame.init()
    screen = pygame.display.set_mode((810, 620))
    pygame.display.set_caption("Virus Defense — Grid 12×12")
    clock = pygame.time.Clock()
    renderer = Renderer(screen)

    game_state = STATE_START
    engine = None
    bt_preview_active = False
    bt_perimeter_cache = []
    current_pos = (5, 5)  # Player's current position (center)
    hover_node = None

    def reset_game():
        nonlocal engine, game_state, bt_preview_active, bt_perimeter_cache, current_pos
        engine = PythonEngine()
        game_state = STATE_PLAYING
        bt_preview_active = False
        bt_perimeter_cache = []
        current_pos = (5, 5)

    running = True
    while running:
        tick = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    break

                if game_state == STATE_START:
                    reset_game()
                    continue

                if game_state in (STATE_GAME_OVER, STATE_VICTORY):
                    if event.key == pygame.K_r:
                        reset_game()
                    continue

                if game_state == STATE_PLAYING and engine:
                    # ── G: Greedy ──
                    if event.key == pygame.K_g:
                        suggestion = get_greedy_suggestion(engine.grid, current_pos)
                        if suggestion and engine.budget >= engine.greedy_cost:
                            r, c = suggestion
                            if engine.apply_greedy(r, c):
                                renderer.trigger_flash(r, c)
                                current_pos = (r, c)
                                engine.advance_turn()
                                bt_preview_active = False
                                bt_perimeter_cache = []

                    # ── B: Backtracking toggle/apply ──
                    elif event.key == pygame.K_b:
                        if engine.backtracking_cooldown > 0:
                            pass  # Can't use while on cooldown
                        elif not bt_preview_active:
                            # Compute and show preview
                            bt_perimeter_cache = get_quarantine_perimeter(engine.grid)
                            bt_preview_active = True
                        else:
                            # Confirm and apply
                            if bt_perimeter_cache:
                                if engine.apply_backtracking(bt_perimeter_cache):
                                    for pr, pc in bt_perimeter_cache:
                                        renderer.trigger_flash(pr, pc)
                                    engine.advance_turn()
                            bt_preview_active = False
                            bt_perimeter_cache = []

                    # ── N: Pass turn ──
                    elif event.key == pygame.K_n:
                        engine.advance_turn()
                        bt_preview_active = False
                        bt_perimeter_cache = []

                    # ── R: Restart ──
                    elif event.key == pygame.K_r:
                        reset_game()

            # ── Mouse Click ──
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == STATE_START:
                    reset_game()
                    continue

                if game_state == STATE_PLAYING and engine:
                    # Cancel backtracking preview if active
                    if bt_preview_active:
                        bt_preview_active = False
                        bt_perimeter_cache = []
                        continue

                    clicked = renderer.get_clicked_node(event.pos)
                    if clicked:
                        r, c = clicked
                        mods = pygame.key.get_mods()

                        if mods & pygame.KMOD_SHIFT:
                            # Reinforce (3 budget, 3 turn cooldown)
                            if engine.reinforce_cooldown == 0:
                                success, patched_cells = engine.apply_reinforce(r, c)
                                if success:
                                    for pr, pc in patched_cells:
                                        renderer.trigger_flash(pr, pc)
                                    current_pos = (r, c)
                                    engine.advance_turn()
                        else:
                            # Patch (1 budget)
                            if engine.apply_patch(r, c):
                                renderer.trigger_flash(r, c)
                                current_pos = (r, c)
                                engine.advance_turn()

            # ── Mouse Motion (hover) ──
            if event.type == pygame.MOUSEMOTION:
                if game_state == STATE_PLAYING:
                    hover_node = renderer.get_clicked_node(event.pos)

        # ─── Rendering ───
        renderer.clear()

        if game_state == STATE_START:
            renderer.draw_start_screen()

        elif game_state == STATE_PLAYING and engine:
            grid = engine.grid

            # Compute current suggestions
            greedy_suggestion = get_greedy_suggestion(grid, current_pos)
            infected_n = count_infected(grid)
            danger = infected_n / (GRID_SIZE * GRID_SIZE)

            # Draw grid and effects
            renderer.draw_grid(grid)
            renderer.draw_infected_pulse(grid, tick)

            # Draw greedy hint
            if greedy_suggestion:
                renderer.draw_greedy_hint(greedy_suggestion[0], greedy_suggestion[1])

            # Draw backtracking preview
            if bt_preview_active and bt_perimeter_cache:
                bt_nodes = [{"row": r, "col": c} for r, c in bt_perimeter_cache]
                renderer.draw_backtracking_preview(bt_nodes)

            # Draw player selection
            renderer.draw_selection_ring(current_pos[0], current_pos[1])

            # Draw flashes
            renderer.update_flashes()
            renderer.draw_flashes()

            # Draw tooltip on hover
            if hover_node:
                hr, hc = hover_node
                deg = get_healthy_degree(grid, hr, hc)
                renderer.draw_tooltip(hr, hc, deg)

            # Draw HUD
            bt_size = len(bt_perimeter_cache) if bt_preview_active else len(get_boundary_nodes(grid))
            renderer.draw_hud(
                turn=engine.turn,
                budget=engine.budget,
                score=engine.score,
                danger_level=danger,
                greedy_hint=greedy_suggestion,
                greedy_cost=engine.greedy_cost,
                bt_size=bt_size,
                bt_cooldown=engine.backtracking_cooldown,
                infected_count=infected_n,
                bt_preview_active=bt_preview_active,
                reinforce_cooldown=engine.reinforce_cooldown
            )

            # ── Check Game Over / Victory ──
            if engine.score <= -300 or engine.turn > 45:
                game_state = STATE_GAME_OVER
            elif infected_n > 0 and is_virus_contained(grid) and engine.turn > 0:
                game_state = STATE_VICTORY
            elif infected_n == 0 and engine.turn > 0:
                game_state = STATE_VICTORY

        elif game_state == STATE_GAME_OVER and engine:
            renderer.draw_grid(engine.grid)
            renderer.draw_game_over(engine.score)

        elif game_state == STATE_VICTORY and engine:
            renderer.draw_grid(engine.grid)
            renderer.draw_victory(engine.turn)

        pygame.display.flip()
        clock.tick(10)  # 10 FPS as specified

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
