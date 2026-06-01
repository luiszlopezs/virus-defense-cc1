"""Virus Defense — Python/Pygame UI connected to the C++ engine."""

from __future__ import annotations

import os
import subprocess
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

from algorithms.backtracking import find_safe_path, next_step_from_path
from algorithms.greedy import count_infected_neighbors, describe_greedy_suggestion, get_greedy_patch_suggestion
from algorithms.grid_utils import (
    GRID_SIZE,
    HEALTHY,
    INFECTED,
    PATCHED,
    count_infected,
    find_first_healthy,
    get_cell,
    get_degree,
    is_infected_cluster_empty,
    normalize_grid,
    positions_to_json,
    set_cell,
)
from bridge.json_bridge import calculate_score, read_state, reset_shared_state, write_input, write_state
from ui.intro_screen import IntroScreen
from ui.renderer import Renderer

FPS = 30
PATCH_COST = 1
REINFORCE_COST = 2
MAX_TURNS = 45
MIN_SCORE_BEFORE_GAME_OVER = -200
Position = tuple[int, int]


def infected_nodes(grid: list[list[int]]) -> list[Position]:
    return [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if grid[r][c] == INFECTED]


def is_engine_state(state: dict[str, Any]) -> bool:
    return state.get("engine") == "cpp" or str(state.get("status", "")).startswith("engine")


def state_position(state: dict[str, Any], key: str, default: Position) -> Position:
    value = state.get(key)
    if isinstance(value, dict):
        try:
            row = int(value.get("row", default[0]))
            col = int(value.get("col", default[1]))
            if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                return (row, col)
        except (TypeError, ValueError):
            pass
    return default


def put_state_position(state: dict[str, Any], key: str, node: Position) -> None:
    state[key] = {"row": int(node[0]), "col": int(node[1])}


def find_engine_executable() -> Path | None:
    """Return the compiled C++ engine executable if it exists."""
    build_dir = PROJECT_ROOT / "engine" / "build"
    names = ["virus_engine.exe", "virus_engine"]
    for name in names:
        direct = build_dir / name
        if direct.exists():
            return direct
    if build_dir.exists():
        for candidate in build_dir.rglob("virus_engine*"):
            if candidate.is_file() and (candidate.suffix == ".exe" or os.access(candidate, os.X_OK)):
                return candidate
    return None


def start_cpp_engine() -> subprocess.Popen[bytes] | None:
    """Start the C++ engine if a compiled executable is available."""
    executable = find_engine_executable()
    if executable is None:
        return None

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    try:
        return subprocess.Popen(
            [str(executable)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except OSError:
        return None


def stop_cpp_engine(process: subprocess.Popen[bytes] | None) -> None:
    if process is None:
        return
    try:
        write_input("quit", (-1, -1), 0)
        process.wait(timeout=1.5)
    except Exception:
        try:
            process.terminate()
        except Exception:
            pass


def apply_local_action(
    state: dict[str, Any],
    action: str,
    target: Position,
    budget_spent: int,
    path: list[Position] | None = None,
) -> tuple[dict[str, Any], str]:
    """Fallback simulation used only when the C++ engine is not available."""
    grid = normalize_grid(state.get("grid"))
    budget = int(state.get("budget", 0))
    current_node = state_position(state, "player", (0, 0))
    goal_node = state_position(state, "goal", (GRID_SIZE - 1, GRID_SIZE - 1))

    if budget_spent > budget:
        return state, "Not enough budget"

    row, col = target

    if action in {"patch", "reinforce", "greedy"}:
        if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
            return state, "Invalid target node"
        if get_cell(grid, row, col) != HEALTHY:
            return state, "Only healthy nodes can be patched"

        set_cell(grid, row, col, PATCHED)
        budget -= budget_spent
        message = f"{action.title()} patch applied at ({row}, {col})"

        if action == "greedy":
            state["greedy_cost"] = int(state.get("greedy_cost", 1)) + 1

    elif action == "backtracking":
        if int(state.get("backtracking_cooldown", 0)) > 0:
            return state, "Backtracking is on cooldown"

        safe_path = path if path is not None else find_safe_path(grid, current_node, goal_node)
        next_step = next_step_from_path(safe_path)
        if next_step is None:
            return state, "No safe route available"
        if next_step != target:
            return state, "Invalid Backtracking step"
        if get_cell(grid, next_step[0], next_step[1]) == INFECTED:
            return state, "Backtracking path is no longer safe"

        current_node = next_step
        put_state_position(state, "player", current_node)
        state["backtracking_path"] = positions_to_json(safe_path)
        state["backtracking_cooldown"] = 3
        budget_spent = 0
        message = f"Backtracking moved safely to {current_node}"
    else:
        return state, "Unknown action"

    if action in {"patch", "reinforce", "greedy", "backtracking"}:
        state["turn"] = int(state.get("turn", 0)) + 1

    if int(state.get("backtracking_cooldown", 0)) > 0 and action != "backtracking":
        state["backtracking_cooldown"] = max(0, int(state.get("backtracking_cooldown", 0)) - 1)

    # Fallback mode recovers one budget point per accepted turn, matching the C++ engine.
    if action in {"patch", "reinforce", "greedy", "backtracking"}:
        budget = max(0, budget)
        state["budget"] = min(12, budget + 1)

    state["grid"] = grid
    state["score"] = calculate_score(grid)
    
    if action in {"patch", "reinforce", "greedy", "backtracking"}:
        from algorithms.grid import Grid
        temp_grid = Grid(GRID_SIZE, GRID_SIZE)
        temp_grid.matrix = grid
        
        # Advance the outbreak step-by-step with a (%) probability per action
        temp_grid.expand_virus(infection_chance=0.10)
        grid = temp_grid.matrix
        state["grid"] = grid
        
        # Verify if the virus managed to collapse the player's current position
        if get_cell(grid, current_node[0], current_node[1]) == INFECTED:
            state["status"] = "game_over"
            message = "Game Over: The virus collapsed your current node!"
        else:
            message = f"{action.title()} action processed. Virus expansion updated."


    if state["status"] != "game_over":
        state["status"] = "ui_fallback"
        state["engine"] = "python_fallback"
        state["message"] = message
        if current_node == goal_node:
            state["status"] = "victory"
            state["message"] = "Goal reached"
    else:
        state["message"] = message

    write_input(action, target, budget_spent, path=path if action == "backtracking" else None)
    write_state(state)
    return state, message

def send_action(
    state: dict[str, Any],
    action: str,
    target: Position,
    budget_spent: int,
    path: list[Position] | None = None,
) -> tuple[dict[str, Any], str]:
    """Send actions to C++ when active, otherwise simulate locally."""
    if is_engine_state(state):
        write_input(action, target, budget_spent, path=path if action == "backtracking" else None)
        if action == "backtracking" and path is not None:
            return state, f"Safe-path step sent to C++ engine ({len(path)} path nodes)"
        return state, f"{action.title()} sent to C++ engine"
    return apply_local_action(state, action, target, budget_spent, path)


def should_block_regular_play(state: dict[str, Any]) -> str | None:
    status = str(state.get("status", ""))
    if status == "victory":
        return "victory"
    if status == "game_over":
        return "game_over"

    grid = state["grid"]
    player = state_position(state, "player", (0, 0))
    goal = state_position(state, "goal", (GRID_SIZE - 1, GRID_SIZE - 1))
    if player == goal:
        return "victory"
    if get_cell(grid, goal[0], goal[1]) == INFECTED:
        return "game_over"
    if not is_engine_state(state) and is_infected_cluster_empty(grid):
        return "victory"
    if int(state.get("score", 0)) < MIN_SCORE_BEFORE_GAME_OVER or int(state.get("turn", 0)) > MAX_TURNS:
        return "game_over"
    return None


def ensure_valid_current_node(grid: list[list[int]], current_node: Position) -> Position:
    row, col = current_node
    if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE and get_cell(grid, row, col) != INFECTED:
        return current_node
    return find_first_healthy(grid, preferred=(0, 0))


def toggle_fullscreen(screen: pygame.Surface, renderer: Renderer) -> pygame.Surface:
    renderer.is_fullscreen = not renderer.is_fullscreen
    if renderer.is_fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
    else:
        screen = pygame.display.set_mode(Renderer.WINDOW_SIZE, pygame.RESIZABLE)
    renderer.configure(screen)
    return screen


def main() -> None:
    engine_process = start_cpp_engine()
    if engine_process is not None:
        time.sleep(0.25)

    pygame.init()
    pygame.display.set_caption("Virus Defense")
    screen = pygame.display.set_mode(Renderer.WINDOW_SIZE, pygame.RESIZABLE)
    clock = pygame.time.Clock()
    renderer = Renderer(screen)
    intro_screen = IntroScreen(screen)

    # Show intro screen
    show_intro = True
    while show_intro:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.VIDEORESIZE:
                width = max(Renderer.MIN_WINDOW_SIZE[0], event.w)
                height = max(Renderer.MIN_WINDOW_SIZE[1], event.h)
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                intro_screen.setup_layout()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if intro_screen.handle_click(event.pos):
                    show_intro = False

        intro_screen.draw()
        pygame.display.flip()
        clock.tick(FPS)

    # Game starts here
    state = read_state()
    state["grid"] = normalize_grid(state.get("grid"))
    current_node = state_position(state, "player", (0, 0))
    goal_node = state_position(state, "goal", (GRID_SIZE - 1, GRID_SIZE - 1))
    preview_backtracking = False
    last_flash: tuple[Position, float] | None = None

    if is_engine_state(state):
        message = str(state.get("message") or "C++ engine connected")
    else:
        message = "C++ engine executable not found; Python fallback mode is active"

    running = True

    while running:
        state = read_state()
        state["grid"] = normalize_grid(state.get("grid"))
        grid = state["grid"]
        current_node = ensure_valid_current_node(grid, state_position(state, "player", current_node))
        goal_node = state_position(state, "goal", goal_node)
        put_state_position(state, "player", current_node)
        put_state_position(state, "goal", goal_node)

        if is_engine_state(state) and state.get("message"):
            message = str(state.get("message"))

        greedy_hint = get_greedy_patch_suggestion(grid, current_node)
        greedy_risk = count_infected_neighbors(grid, greedy_hint[0], greedy_hint[1]) if greedy_hint else 0
        safe_path = find_safe_path(grid, current_node, goal_node) if preview_backtracking and int(state.get("backtracking_cooldown", 0)) == 0 else []
        state["greedy_suggestion"] = (
            {"row": greedy_hint[0], "col": greedy_hint[1], "infected_neighbors": greedy_risk}
            if greedy_hint
            else {"row": -1, "col": -1, "infected_neighbors": 0}
        )
        state["backtracking_path"] = positions_to_json(safe_path)

        game_status = should_block_regular_play(state)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                write_input("quit", (-1, -1), 0)
                running = False

            elif event.type == pygame.VIDEORESIZE:
                if not renderer.is_fullscreen:
                    width = max(Renderer.MIN_WINDOW_SIZE[0], event.w)
                    height = max(Renderer.MIN_WINDOW_SIZE[1], event.h)
                    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                    renderer.configure(screen)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    write_input("quit", (-1, -1), 0)
                    running = False

                elif event.key == pygame.K_F11:
                    screen = toggle_fullscreen(screen, renderer)

                elif event.key == pygame.K_r:
                    if is_engine_state(state):
                        write_input("reset", (-1, -1), 0)
                        message = "Reset sent to C++ engine"
                    else:
                        state = reset_shared_state()
                        message = "Fallback state reset"
                    current_node = state_position(state, "player", (0, 0))
                    goal_node = state_position(state, "goal", (GRID_SIZE - 1, GRID_SIZE - 1))
                    preview_backtracking = False

                elif game_status is None and event.key == pygame.K_g:
                    if greedy_hint is None:
                        message = "Greedy found no healthy node adjacent to the virus"
                    else:
                        cost = int(state.get("greedy_cost", 1))
                        state, message = send_action(state, "greedy", greedy_hint, cost)
                        preview_backtracking = False
                        last_flash = (greedy_hint, time.time())

                elif game_status is None and event.key == pygame.K_b:
                    cooldown = int(state.get("backtracking_cooldown", 0))
                    if cooldown > 0:
                        message = f"Backtracking is locked for {cooldown} turns"
                    elif not preview_backtracking:
                        preview_backtracking = True
                        candidate_path = find_safe_path(grid, current_node, goal_node)
                        if candidate_path:
                            message = "Safe path preview enabled. Press B again to advance one step."
                        else:
                            message = "No safe path to the goal is currently available"
                    else:
                        current_path = find_safe_path(grid, current_node, goal_node)
                        step = next_step_from_path(current_path)
                        if step is None:
                            message = "No safe path to advance"
                        else:
                            state, message = send_action(state, "backtracking", step, 0, current_path)
                            current_node = step
                            put_state_position(state, "player", current_node)
                            preview_backtracking = False
                            last_flash = (current_node, time.time())
                elif game_status is None and event.key in {pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT}:
                    # Calculate target coordinates based on the arrow key pressed
                    row, col = current_node
                    if event.key == pygame.K_UP:
                        target_node = (row - 1, col)
                    elif event.key == pygame.K_DOWN:
                        target_node = (row + 1, col)
                    elif event.key == pygame.K_LEFT:
                        target_node = (row, col - 1)
                    elif event.key == pygame.K_RIGHT:
                        target_node = (row, col + 1)

                    # Validate if the move is within boundaries and to a walkable node (not INFECTED)
                    if not (0 <= target_node[0] < GRID_SIZE and 0 <= target_node[1] < GRID_SIZE):
                        message = "Move rejected: Out of grid boundaries."
                    elif get_cell(grid, target_node[0], target_node[1]) == INFECTED:
                        message = "Move rejected: Cannot step into an infected node!"
                    else:
                        # FIXED: Consume a turn and trigger virus expansion WITHOUT placing a patch
                        state["turn"] = int(state.get("turn", 0)) + 1
                        
                        # Move the player to the new safe coordinate
                        current_node = target_node
                        put_state_position(state, "player", current_node)
                        preview_backtracking = False
                        last_flash = (current_node, time.time())
                        
                        # Trigger the virus expansion algorithm for this turn
                        from algorithms.grid import Grid
                        temp_grid = Grid(GRID_SIZE, GRID_SIZE)
                        temp_grid.matrix = grid
                        temp_grid.expand_virus(infection_chance=0.10) #probability of virus expansion on manual move
                        grid = temp_grid.matrix
                        state["grid"] = grid
                        
                        # Check if the virus expanded into the player's new position
                        if get_cell(grid, current_node[0], current_node[1]) == INFECTED:
                            state["status"] = "game_over"
                            message = "Game Over: The virus collapsed your current node!"
                        else:
                            message = f"Manual move: Advanced safely to {current_node}."
                            
                        write_state(state)

                elif game_status is None and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                    # Movement through protected nodes using arrow keys
                    direction_map = {
                        pygame.K_UP: (-1, 0),
                        pygame.K_DOWN: (1, 0),
                        pygame.K_LEFT: (0, -1),
                        pygame.K_RIGHT: (0, 1),
                    }
                    dr, dc = direction_map[event.key]
                    new_row = current_node[0] + dr
                    new_col = current_node[1] + dc

                    # Check if new position is within bounds
                    if 0 <= new_row < GRID_SIZE and 0 <= new_col < GRID_SIZE:
                        cell_state = get_cell(grid, new_row, new_col)
                        # Allow movement only through patched nodes
                        if cell_state == PATCHED:
                            current_node = (new_row, new_col)
                            put_state_position(state, "player", current_node)
                            preview_backtracking = False
                            last_flash = (current_node, time.time())
                            message = f"Moved to protected node ({new_row}, {new_col})"
                        elif cell_state == INFECTED:
                            message = "Cannot move to infected node"
                        else:
                            message = "Can only move through protected nodes"
                    else:
                        message = "Cannot move outside the grid"

            elif game_status is None and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = renderer.get_clicked_node(event.pos)
                if clicked is None:
                    message = "Click outside the grid"
                    continue

                shift_pressed = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)

                if shift_pressed:
                    if get_cell(grid, clicked[0], clicked[1]) != HEALTHY:
                        message = "Reinforce requires a healthy node"
                    else:
                        state, message = send_action(state, "reinforce", clicked, REINFORCE_COST)
                        preview_backtracking = False
                        last_flash = (clicked, time.time())
                else:
                    if get_cell(grid, clicked[0], clicked[1]) != HEALTHY:
                        message = "Patch requires a healthy node"
                    else:
                        state, message = send_action(state, "patch", clicked, PATCH_COST)
                        preview_backtracking = False
                        last_flash = (clicked, time.time())

        grid = state["grid"]
        current_node = ensure_valid_current_node(grid, state_position(state, "player", current_node))
        goal_node = state_position(state, "goal", goal_node)
        greedy_hint = get_greedy_patch_suggestion(grid, current_node)
        greedy_risk = count_infected_neighbors(grid, greedy_hint[0], greedy_hint[1]) if greedy_hint else 0
        safe_path = find_safe_path(grid, current_node, goal_node) if preview_backtracking and int(state.get("backtracking_cooldown", 0)) == 0 else []
        danger_level = count_infected(grid) / float(GRID_SIZE * GRID_SIZE)

        renderer.clear()
        renderer.draw_grid(grid)
        renderer.draw_infected_pulse(infected_nodes(grid), pygame.time.get_ticks())
        renderer.draw_goal(*goal_node)
        if safe_path:
            renderer.draw_safe_path(safe_path)
        renderer.draw_current_node(*current_node)

        if greedy_hint:
            renderer.draw_greedy_hint(*greedy_hint)

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

        game_status = should_block_regular_play(state)
        renderer.draw_hud(
            turn=int(state.get("turn", 0)),
            budget=int(state.get("budget", 0)),
            score=int(state.get("score", 0)),
            danger_level=danger_level,
            greedy_hint=greedy_hint,
            greedy_risk=greedy_risk,
            greedy_cost=int(state.get("greedy_cost", 1)),
            path_length=len(safe_path),
            bt_cooldown=int(state.get("backtracking_cooldown", 0)),
            current_action=message,
            current_node=current_node,
            goal_node=goal_node,
            status=str(state.get("status", "playing")),
            engine_label="C++" if is_engine_state(state) else "Python fallback",
        )

        if game_status == "victory":
            renderer.draw_victory(int(state.get("turn", 0)))
        elif game_status == "game_over":
            renderer.draw_game_over(int(state.get("score", 0)))

        pygame.display.flip()
        clock.tick(FPS)

    stop_cpp_engine(engine_process)
    pygame.quit()


if __name__ == "__main__":
    main()