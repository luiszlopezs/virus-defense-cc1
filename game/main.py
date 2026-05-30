"""
Virus Defense — Pygame UI build.

This version is intentionally standalone: it reads/writes shared JSON files and
also simulates minimal state changes while the C++ engine is still pending.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import pygame

# Allow execution from both the project root and the game/ folder.
GAME_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = GAME_DIR.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from algorithms.backtracking import get_quarantine_perimeter
from algorithms.greedy import get_greedy_suggestion
from algorithms.grid_utils import (
    GRID_SIZE,
    HEALTHY,
    INFECTED,
    PATCHED,
    count_infected,
    find_first_healthy,
    get_cell,
    get_degree,
    get_neighbors,
    is_infected_cluster_empty,
    normalize_grid,
    positions_to_json,
    set_cell,
)
from bridge.json_bridge import calculate_score, read_state, reset_shared_state, write_input, write_state
from ui.renderer import Renderer

FPS = 10
PATCH_COST = 1
REINFORCE_COST = 2
MAX_TURNS = 45
MIN_SCORE_BEFORE_GAME_OVER = -200


def infected_nodes(grid: list[list[int]]) -> list[tuple[int, int]]:
    return [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if grid[r][c] == INFECTED]


def apply_local_action(
    state: dict[str, Any],
    action: str,
    target: tuple[int, int],
    budget_spent: int,
) -> tuple[dict[str, Any], str]:
    """
    Apply a lightweight local simulation until the C++ engine is available.

    The UI still writes every action to shared/input.json, so the integration
    contract remains ready for the future engine.
    """
    grid = normalize_grid(state.get("grid"))
    budget = int(state.get("budget", 0))
    message = "Acción enviada"

    if budget_spent > budget:
        return state, "Presupuesto insuficiente"

    row, col = target

    if action in {"patch", "reinforce", "greedy"}:
        if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
            return state, "Nodo objetivo inválido"
        if get_cell(grid, row, col) != HEALTHY:
            return state, "Solo se pueden proteger nodos sanos"

        set_cell(grid, row, col, PATCHED)
        budget -= budget_spent
        message = f"{action} aplicado en ({row}, {col})"

        if action == "greedy":
            state["greedy_cost"] = int(state.get("greedy_cost", 1)) + 1

    elif action == "backtracking":
        if int(state.get("backtracking_cooldown", 0)) > 0:
            return state, "Backtracking está en cooldown"

        perimeter = get_quarantine_perimeter(grid)
        cost = len(perimeter)
        if cost == 0:
            return state, "No hay perímetro disponible"
        if cost > budget:
            return state, "Presupuesto insuficiente para el perímetro"

        for pr, pc in perimeter:
            if get_cell(grid, pr, pc) == HEALTHY:
                set_cell(grid, pr, pc, PATCHED)

        budget -= cost
        budget_spent = cost
        state["backtracking_perimeter"] = positions_to_json(perimeter)
        state["backtracking_cooldown"] = 3
        message = f"Backtracking aplicado: {cost} nodos"

    state["grid"] = grid
    state["budget"] = max(0, budget)
    state["turn"] = int(state.get("turn", 0)) + 1

    if int(state.get("backtracking_cooldown", 0)) > 0 and action != "backtracking":
        state["backtracking_cooldown"] = max(0, int(state.get("backtracking_cooldown", 0)) - 1)

    # Small budget recovery for the standalone UI prototype.
    if action in {"patch", "reinforce", "greedy", "backtracking"}:
        state["budget"] = min(12, int(state["budget"]) + 1)

    state["score"] = calculate_score(grid)
    state["status"] = "simulated"
    write_input(action, target, budget_spent)
    write_state(state)
    return state, message


def should_block_regular_play(state: dict[str, Any]) -> str | None:
    if is_infected_cluster_empty(state["grid"]):
        return "victory"
    if int(state.get("score", 0)) < MIN_SCORE_BEFORE_GAME_OVER or int(state.get("turn", 0)) > MAX_TURNS:
        return "game_over"
    return None


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Virus Defense (Grilla 12x12)")
    screen = pygame.display.set_mode(Renderer.WINDOW_SIZE)
    clock = pygame.time.Clock()
    renderer = Renderer(screen)

    state = read_state()
    state["grid"] = normalize_grid(state.get("grid"))
    current_node = find_first_healthy(state["grid"], preferred=(5, 6))
    preview_backtracking = False
    last_flash: tuple[tuple[int, int], float] | None = None
    message = "UI lista: estado simulado activo"
    running = True

    while running:
        state = read_state()
        state["grid"] = normalize_grid(state.get("grid"))
        current_node = find_first_healthy(state["grid"], preferred=current_node)

        grid = state["grid"]
        greedy_hint = get_greedy_suggestion(grid, current_node)
        perimeter = get_quarantine_perimeter(grid) if preview_backtracking and int(state.get("backtracking_cooldown", 0)) == 0 else []
        state["greedy_suggestion"] = {"row": greedy_hint[0], "col": greedy_hint[1]} if greedy_hint else {"row": -1, "col": -1}
        state["backtracking_perimeter"] = positions_to_json(perimeter)

        game_status = should_block_regular_play(state)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                write_input("quit", (-1, -1), 0)
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    write_input("quit", (-1, -1), 0)
                    running = False

                elif event.key == pygame.K_r:
                    state = reset_shared_state()
                    current_node = find_first_healthy(state["grid"], preferred=(5, 6))
                    preview_backtracking = False
                    message = "Estado reiniciado"

                elif game_status is None and event.key == pygame.K_g:
                    if greedy_hint is None:
                        message = "Greedy no tiene nodo sano vecino"
                    else:
                        cost = int(state.get("greedy_cost", 1))
                        state, message = apply_local_action(state, "greedy", greedy_hint, cost)
                        current_node = greedy_hint
                        last_flash = (greedy_hint, time.time())

                elif game_status is None and event.key == pygame.K_b:
                    cooldown = int(state.get("backtracking_cooldown", 0))
                    if cooldown > 0:
                        message = f"Backtracking bloqueado por {cooldown} turnos"
                    elif not preview_backtracking:
                        preview_backtracking = True
                        message = "Preview Backtracking activo. Presiona B otra vez para confirmar"
                    else:
                        state, message = apply_local_action(state, "backtracking", (-1, -1), len(perimeter))
                        preview_backtracking = False
                        last_flash = (current_node, time.time())

            elif game_status is None and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = renderer.get_clicked_node(event.pos)
                if clicked is None:
                    message = "Click fuera de la grilla"
                    continue

                shift_pressed = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
                row, col = clicked

                if shift_pressed:
                    state, message = apply_local_action(state, "reinforce", clicked, REINFORCE_COST)
                    last_flash = (clicked, time.time())
                else:
                    if clicked not in get_neighbors(grid, current_node[0], current_node[1]):
                        message = "Solo puedes hacer patch en un vecino del nodo actual"
                    else:
                        state, message = apply_local_action(state, "patch", clicked, PATCH_COST)
                        current_node = clicked
                        last_flash = (clicked, time.time())

        grid = state["grid"]
        greedy_hint = get_greedy_suggestion(grid, current_node)
        perimeter = get_quarantine_perimeter(grid) if preview_backtracking and int(state.get("backtracking_cooldown", 0)) == 0 else []
        danger_level = count_infected(grid) / float(GRID_SIZE * GRID_SIZE)

        renderer.clear()
        renderer.draw_grid(grid)
        renderer.draw_infected_pulse(infected_nodes(grid), pygame.time.get_ticks())
        renderer.draw_current_node(*current_node)

        if greedy_hint:
            renderer.draw_greedy_hint(*greedy_hint)
        if perimeter:
            renderer.draw_backtracking_preview(perimeter)

        mouse_node = renderer.get_clicked_node(pygame.mouse.get_pos())
        if mouse_node:
            renderer.draw_tooltip(mouse_node[0], mouse_node[1], get_degree(mouse_node[0], mouse_node[1]))

        if last_flash is not None:
            flash_node, flash_time = last_flash
            elapsed = time.time() - flash_time
            if elapsed <= 0.15:
                renderer.draw_flash(*flash_node, alpha=max(0, int(180 * (1 - elapsed / 0.15))))
            else:
                last_flash = None

        renderer.draw_hud(
            turn=int(state.get("turn", 0)),
            budget=int(state.get("budget", 0)),
            score=int(state.get("score", 0)),
            danger_level=danger_level,
            greedy_hint=greedy_hint,
            greedy_cost=int(state.get("greedy_cost", 1)),
            bt_size=len(perimeter),
            bt_cooldown=int(state.get("backtracking_cooldown", 0)),
            current_action=message,
            current_node=current_node,
        )

        game_status = should_block_regular_play(state)
        if game_status == "victory":
            renderer.draw_victory(int(state.get("turn", 0)))
        elif game_status == "game_over":
            renderer.draw_game_over(int(state.get("score", 0)))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
