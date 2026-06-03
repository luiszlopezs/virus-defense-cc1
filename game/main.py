"""
Virus Defense — Main Game Loop
==============================
Integrates the Python game engine, algorithms, renderer, and JSON bridge
into a cohesive Pygame application.

New mechanic: The player starts at a random border position and must reach
a goal at another border position. The virus spreads each turn. The player
moves with arrow keys and can use Greedy (G) and Backtracking (B) abilities.

Controls:
    Arrow Keys  → Move player 1 cell
    G           → Apply Greedy suggestion (patches 1 cell, variable cost)
    B           → Show safe path via Backtracking (cooldown 3 turns)
    N           → Pass turn (no action)
    R           → Restart game
    ESC         → Quit

Win/Lose:
    Victory: Player reaches the goal
    Defeat:  Player steps on virus / Virus reaches player / Virus reaches goal

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
    count_infected, find_safe_path
)
from algorithms.greedy import get_greedy_suggestion
from algorithms.backtracking import get_quarantine_perimeter
from bridge.json_bridge import read_state, write_input, SHARED_PATH


# ─── Helper: Manhattan distance ───

def manhattan(r1, c1, r2, c2):
    return abs(r1 - r2) + abs(c1 - c2)


def is_border_not_corner(r, c):
    on_border = (r == 0 or r == GRID_SIZE - 1 or c == 0 or c == GRID_SIZE - 1)
    is_corner = (r == 0 or r == GRID_SIZE - 1) and (c == 0 or c == GRID_SIZE - 1)
    return on_border and not is_corner


# ─── Python-native Game Engine ───

class PythonEngine:
    """
    Self-contained game engine that runs when the C++ engine is not available.
    Mirrors the exact same game rules defined in the plan.
    """

    SPREAD_CHANCE = 0.15  # 15% chance per neighbor per infected node per turn
    MAX_INFECTIONS_PER_NODE = 1

    def __init__(self):
        self.grid = [[HEALTHY] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.turn = 0
        self.score = 0
        self.budget = 5
        self.greedy_cost = 1
        self.backtracking_cooldown = 0
        self.infection_history = []
        self.greedy_suggestion = (-1, -1)
        self.backtracking_perimeter = []

        # Flags for game over conditions
        self.player_infected = False
        self.goal_infected = False

        # ── Generate random positions with distance constraints ──

        # Player: random border position (not corner)
        border_positions = [
            (r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
            if is_border_not_corner(r, c)
        ]
        self.player_row, self.player_col = random.choice(border_positions)

        # Goal: border position with Manhattan >= 10 from player
        self.goal_row = -1
        self.goal_col = -1
        for _ in range(200):
            gr, gc = random.choice(border_positions)
            if manhattan(self.player_row, self.player_col, gr, gc) >= 10:
                self.goal_row, self.goal_col = gr, gc
                break
        if self.goal_row == -1:
            # Fallback: far corner
            self.goal_row = GRID_SIZE - 1 if self.player_row <= 5 else 0
            self.goal_col = GRID_SIZE - 1 if self.player_col <= 5 else 0

        # Virus: interior position with Manhattan >= 6 from both player and goal
        self.virus_row = -1
        self.virus_col = -1
        for _ in range(500):
            vr = random.randint(2, GRID_SIZE - 3)
            vc = random.randint(2, GRID_SIZE - 3)
            if (manhattan(vr, vc, self.player_row, self.player_col) >= 6 and
                    manhattan(vr, vc, self.goal_row, self.goal_col) >= 6):
                self.virus_row, self.virus_col = vr, vc
                break
        if self.virus_row == -1:
            self.virus_row = GRID_SIZE // 2
            self.virus_col = GRID_SIZE // 2

        self.grid[self.virus_row][self.virus_col] = INFECTED
        self.infection_history.append({
            "row": self.virus_row, "col": self.virus_col,
            "turn": 0, "cause": "initial"
        })

        # ── Add 2 small outbreaks in different parts of the map ──
        outbreak_positions = [(self.virus_row, self.virus_col)]
        for _ in range(2):  # 2 additional outbreaks
            for attempt in range(200):
                br = random.randint(2, GRID_SIZE - 3)
                bc = random.randint(2, GRID_SIZE - 3)
                # Must be far from player, goal, and other outbreaks
                if (manhattan(br, bc, self.player_row, self.player_col) >= 5 and
                        manhattan(br, bc, self.goal_row, self.goal_col) >= 5 and
                        all(manhattan(br, bc, or_, oc) >= 5 for or_, oc in outbreak_positions)):
                    # Infect this cell + 1 random healthy neighbor
                    self.grid[br][bc] = INFECTED
                    self.infection_history.append({
                        "row": br, "col": bc, "turn": 0, "cause": "outbreak"
                    })
                    outbreak_positions.append((br, bc))
                    # Try to infect one neighbor of this outbreak
                    nbrs = get_neighbors(self.grid, br, bc)
                    random.shuffle(nbrs)
                    for nr, nc in nbrs:
                        if self.grid[nr][nc] == HEALTHY:
                            self.grid[nr][nc] = INFECTED
                            self.infection_history.append({
                                "row": nr, "col": nc, "turn": 0, "cause": "outbreak"
                            })
                            break
                    break

        self.score = self.calculate_score()

    def calculate_score(self):
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

    def spread_virus(self):
        """Spread virus from all infected nodes. Each node can infect up to 2 neighbors."""
        new_infections = []
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] == INFECTED:
                    infections_this_node = 0
                    for nr, nc in get_neighbors(self.grid, r, c):
                        if infections_this_node >= self.MAX_INFECTIONS_PER_NODE:
                            break
                        if self.grid[nr][nc] == HEALTHY and random.random() < self.SPREAD_CHANCE:
                            new_infections.append((nr, nc))
                            infections_this_node += 1

        for nr, nc in new_infections:
            if self.grid[nr][nc] == HEALTHY:
                self.grid[nr][nc] = INFECTED
                self.infection_history.append({
                    "row": nr, "col": nc, "turn": self.turn, "cause": "spread"
                })

        # Check if virus reached player or goal
        if self.grid[self.player_row][self.player_col] == INFECTED:
            self.player_infected = True
        if self.grid[self.goal_row][self.goal_col] == INFECTED:
            self.goal_infected = True

    def apply_patch(self, row, col):
        if (self.budget >= 1 and 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE
                and self.grid[row][col] == HEALTHY):
            self.grid[row][col] = PATCHED
            self.budget -= 1
            return True
        return False

    def apply_greedy(self, row, col):
        if (self.budget >= self.greedy_cost and 0 <= row < GRID_SIZE
                and 0 <= col < GRID_SIZE and self.grid[row][col] == HEALTHY):
            self.grid[row][col] = PATCHED
            self.budget -= self.greedy_cost
            self.greedy_cost += 1
            return True
        return False

    def apply_backtracking(self, perimeter):
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
        if self.backtracking_cooldown > 0:
            self.backtracking_cooldown -= 1

        self.spread_virus()

        self.turn += 1
        self.budget += 2
        self.calculate_score()

    def get_state_dict(self):
        return {
            "turn": self.turn,
            "score": self.score,
            "budget": self.budget,
            "greedy_cost": self.greedy_cost,
            "backtracking_cooldown": self.backtracking_cooldown,
            "player_pos": {"row": self.player_row, "col": self.player_col},
            "goal_pos": {"row": self.goal_row, "col": self.goal_col},
            "player_infected": self.player_infected,
            "goal_infected": self.goal_infected,
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
    safe_path_active = False
    safe_path_cache = []
    hover_node = None

    def reset_game():
        nonlocal engine, game_state, bt_preview_active, bt_perimeter_cache
        nonlocal safe_path_active, safe_path_cache
        engine = PythonEngine()
        game_state = STATE_PLAYING
        bt_preview_active = False
        bt_perimeter_cache = []
        safe_path_active = False
        safe_path_cache = []

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
                    # ── Arrow Keys: Move player ──
                    if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                        new_r, new_c = engine.player_row, engine.player_col
                        if event.key == pygame.K_UP:
                            new_r -= 1
                        elif event.key == pygame.K_DOWN:
                            new_r += 1
                        elif event.key == pygame.K_LEFT:
                            new_c -= 1
                        elif event.key == pygame.K_RIGHT:
                            new_c += 1

                        if 0 <= new_r < GRID_SIZE and 0 <= new_c < GRID_SIZE:
                            engine.player_row, engine.player_col = new_r, new_c
                            engine.advance_turn()
                            bt_preview_active = False
                            bt_perimeter_cache = []
                            safe_path_active = False
                            safe_path_cache = []

                    # ── G: Greedy ──
                    elif event.key == pygame.K_g:
                        suggestion = get_greedy_suggestion(engine.grid,
                                                           (engine.player_row, engine.player_col))
                        if suggestion and engine.budget >= engine.greedy_cost:
                            r, c = suggestion
                            if engine.apply_greedy(r, c):
                                renderer.trigger_flash(r, c)
                                engine.advance_turn()
                                bt_preview_active = False
                                bt_perimeter_cache = []
                                safe_path_active = False
                                safe_path_cache = []

                    # ── B: Backtracking — single press shows perimeter, cooldown applies ──
                    elif event.key == pygame.K_b:
                        if engine.backtracking_cooldown > 0:
                            pass  # On cooldown
                        else:
                            bt_perimeter_cache = get_quarantine_perimeter(engine.grid)
                            if bt_perimeter_cache:
                                engine.backtracking_cooldown = 3
                                bt_preview_active = True
                                safe_path_active = False
                                safe_path_cache = []

                    # ── H: Show safe path from player to goal ──
                    elif event.key == pygame.K_h:
                        path = find_safe_path(engine.grid,
                                              (engine.player_row, engine.player_col),
                                              (engine.goal_row, engine.goal_col))
                        if path:
                            safe_path_cache = path
                            safe_path_active = True
                            bt_preview_active = False
                            bt_perimeter_cache = []

                    # ── N: Pass turn ──
                    elif event.key == pygame.K_n:
                        engine.advance_turn()
                        bt_preview_active = False
                        bt_perimeter_cache = []
                        safe_path_active = False
                        safe_path_cache = []

                    # ── R: Restart ──
                    elif event.key == pygame.K_r:
                        reset_game()

            # ── Mouse Click: Patch a cell ──
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_state == STATE_START:
                    reset_game()
                    continue

                if game_state == STATE_PLAYING and engine:
                    # Cancel previews if active
                    if bt_preview_active or safe_path_active:
                        bt_preview_active = False
                        bt_perimeter_cache = []
                        safe_path_active = False
                        safe_path_cache = []
                        continue

                    clicked = renderer.get_clicked_node(event.pos)
                    if clicked:
                        r, c = clicked
                        # Check if clicking on infected cell = game over
                        if engine.grid[r][c] == INFECTED:
                            game_state = STATE_GAME_OVER
                        elif engine.grid[r][c] == HEALTHY:
                            if engine.apply_patch(r, c):
                                renderer.trigger_flash(r, c)
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

            infected_n = count_infected(grid)
            danger = infected_n / (GRID_SIZE * GRID_SIZE)

            # Draw grid and effects
            renderer.draw_grid(grid)
            renderer.draw_infected_pulse(grid, tick)

            # Draw backtracking preview (perimeter)
            if bt_preview_active and bt_perimeter_cache:
                bt_nodes = [{"row": r, "col": c} for r, c in bt_perimeter_cache]
                renderer.draw_backtracking_preview(bt_nodes)

            # Draw safe path
            if safe_path_active and safe_path_cache:
                sp_nodes = [{"row": r, "col": c} for r, c in safe_path_cache]
                renderer.draw_safe_path(sp_nodes)

            # Draw player marker
            renderer.draw_selection_ring(engine.player_row, engine.player_col)

            # Draw goal marker
            renderer.draw_goal_marker(engine.goal_row, engine.goal_col)

            # Draw flashes
            renderer.update_flashes()
            renderer.draw_flashes()

            # Draw tooltip on hover
            if hover_node:
                hr, hc = hover_node
                deg = get_healthy_degree(grid, hr, hc)
                renderer.draw_tooltip(hr, hc, deg)

            # Draw HUD
            renderer.draw_hud(
                turn=engine.turn,
                budget=engine.budget,
                danger_level=danger,
                greedy_cost=engine.greedy_cost,
                bt_cooldown=engine.backtracking_cooldown,
                infected_count=infected_n,
            )

            # ── Check Win/Lose ──
            # Victory: player reaches goal
            if (engine.player_row, engine.player_col) == (engine.goal_row, engine.goal_col):
                game_state = STATE_VICTORY
            # Defeat: virus reached player
            elif engine.player_infected:
                game_state = STATE_GAME_OVER
            # Defeat: virus reached goal
            elif engine.goal_infected:
                game_state = STATE_GAME_OVER

        elif game_state == STATE_GAME_OVER and engine:
            renderer.draw_grid(engine.grid)
            renderer.draw_selection_ring(engine.player_row, engine.player_col)
            renderer.draw_goal_marker(engine.goal_row, engine.goal_col)
            renderer.draw_game_over(engine.turn)

        elif game_state == STATE_VICTORY and engine:
            renderer.draw_grid(engine.grid)
            renderer.draw_selection_ring(engine.player_row, engine.player_col)
            renderer.draw_goal_marker(engine.goal_row, engine.goal_col)
            renderer.draw_victory(engine.turn)

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
