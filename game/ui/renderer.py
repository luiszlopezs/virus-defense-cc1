"""Resizable Pygame renderer for Virus Defense."""

from __future__ import annotations

import math
from typing import Iterable

import pygame

try:
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, PATCHED
except ImportError:  # pragma: no cover
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, PATCHED

Position = tuple[int, int]


class Renderer:
    """Draws the board, HUD, highlights, route previews, and final screens in English."""

    WINDOW_SIZE = (1100, 720)
    MIN_WINDOW_SIZE = (900, 620)

    COLORS = {
        HEALTHY: (76, 175, 80),
        INFECTED: (244, 67, 54),
        PATCHED: (75, 105, 255),  # Blue to match the poster legend.
    }

    BACKGROUND = (10, 12, 16)
    PANEL = (20, 25, 34)
    PANEL_BORDER = (56, 66, 84)
    GRID_LINE = (70, 78, 95)
    TEXT = (235, 238, 245)
    MUTED = (150, 158, 175)
    WHITE = (255, 255, 255)
    GOLD = (255, 215, 0)
    BLUE = (96, 165, 250)
    RED = (239, 68, 68)
    CYAN = (34, 211, 238)
    GREEN = (76, 175, 80)
    PURPLE = (168, 85, 247)

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.is_fullscreen = False
        self.margin = 30
        self.hud_width = 330
        self.grid_origin = (30, 30)
        self.cell_size = 40
        self.node_radius = 14
        self.hud_rect = pygame.Rect(0, 0, 330, 600)
        self._init_fonts()
        self.configure(screen)

    def _init_fonts(self) -> None:
        self.font = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 13)
        self.font_tiny = pygame.font.SysFont("arial", 11)
        self.font_title = pygame.font.SysFont("arial", 28, bold=True)
        self.font_hud_title = pygame.font.SysFont("arial", 20, bold=True)

    def configure(self, screen: pygame.Surface | None = None) -> None:
        """Recalculate layout for the current window size."""
        if screen is not None:
            self.screen = screen

        width, height = self.screen.get_size()
        self.margin = max(18, min(34, width // 36))
        self.hud_width = max(300, min(390, int(width * 0.32)))

        available_grid_width = max(260, width - self.hud_width - self.margin * 3)
        available_grid_height = max(260, height - self.margin * 2)
        grid_pixels = max(240, min(available_grid_width, available_grid_height))
        self.cell_size = max(20, int(grid_pixels // GRID_SIZE))
        actual_grid_pixels = self.cell_size * GRID_SIZE
        self.node_radius = max(6, int(self.cell_size * 0.34))

        origin_x = self.margin
        origin_y = max(self.margin, (height - actual_grid_pixels) // 2)
        self.grid_origin = (origin_x, origin_y)

        hud_x = origin_x + actual_grid_pixels + self.margin
        hud_height = min(height - self.margin * 2, 680)
        self.hud_rect = pygame.Rect(hud_x, self.margin, width - hud_x - self.margin, hud_height)
        if self.hud_rect.width < 260:
            self.hud_rect.width = max(240, width - hud_x - 10)

    def clear(self) -> None:
        self.screen.fill(self.BACKGROUND)

    def node_center(self, row: int, col: int) -> Position:
        origin_x, origin_y = self.grid_origin
        return (
            origin_x + col * self.cell_size + self.cell_size // 2,
            origin_y + row * self.cell_size + self.cell_size // 2,
        )

    def draw_grid(self, grid: list[list[int]]) -> None:
        """Draw connections first and then node circles."""
        rows = len(grid)
        cols = len(grid[0]) if rows else GRID_SIZE

        for row in range(rows):
            for col in range(cols):
                cx, cy = self.node_center(row, col)
                if col + 1 < cols:
                    nx, ny = self.node_center(row, col + 1)
                    pygame.draw.line(self.screen, self.GRID_LINE, (cx, cy), (nx, ny), max(1, self.cell_size // 30))
                if row + 1 < rows:
                    nx, ny = self.node_center(row + 1, col)
                    pygame.draw.line(self.screen, self.GRID_LINE, (cx, cy), (nx, ny), max(1, self.cell_size // 30))

        for row in range(rows):
            for col in range(cols):
                cell = grid[row][col]
                cx, cy = self.node_center(row, col)
                color = self.COLORS.get(cell, self.COLORS[HEALTHY])
                pygame.draw.circle(self.screen, color, (cx, cy), self.node_radius)
                pygame.draw.circle(self.screen, self.BACKGROUND, (cx, cy), self.node_radius, max(1, self.cell_size // 22))

    def get_clicked_node(self, mouse_pos: Position) -> Position | None:
        """Convert a mouse coordinate into a grid node, or None if outside."""
        mouse_x, mouse_y = mouse_pos
        origin_x, origin_y = self.grid_origin
        grid_px = GRID_SIZE * self.cell_size

        if not (origin_x <= mouse_x < origin_x + grid_px and origin_y <= mouse_y < origin_y + grid_px):
            return None

        col = (mouse_x - origin_x) // self.cell_size
        row = (mouse_y - origin_y) // self.cell_size
        return int(row), int(col)

    def draw_hud(
        self,
        turn: int,
        budget: int,
        score: int,
        danger_level: float,
        greedy_hint: Position | None,
        greedy_risk: int,
        greedy_cost: int,
        path_length: int,
        bt_cooldown: int,
        current_action: str,
        current_node: Position,
        goal_node: Position,
        status: str,
        engine_label: str,
    ) -> None:
        """Draw the right sidebar with game state and controls."""
        panel = self.hud_rect
        pygame.draw.rect(self.screen, self.PANEL, panel, border_radius=14)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, panel, 1, border_radius=14)

        x = panel.x + 18
        y = panel.y + 18
        max_width = max(190, panel.width - 36)

        self._text("Virus Defense", x, y, self.font_hud_title, self.TEXT)
        y += 30
        self._text(f"Engine: {engine_label}", x, y, self.font_small, self.MUTED)
        y += 26

        y = self._stat("Turn", str(turn), y)
        y = self._stat("Budget", f"{budget} pts", y)
        y = self._stat("Score", str(score), y)
        y = self._stat("Player", f"{current_node}", y)
        y = self._stat("Goal", f"{goal_node}", y)
        y = self._stat("Status", status.replace("_", " "), y)

        y += 8
        self._text("Danger level", x, y, self.font_small, self.MUTED)
        y += 18
        bar_rect = pygame.Rect(x, y, max_width, 12)
        pygame.draw.rect(self.screen, (38, 45, 58), bar_rect, border_radius=6)
        danger_width = max(0, min(max_width, int(max_width * danger_level)))
        pygame.draw.rect(self.screen, self.RED, pygame.Rect(bar_rect.x, bar_rect.y, danger_width, 12), border_radius=6)
        y += 32

        greedy_text = f"{greedy_hint}" if greedy_hint else "No emergency patch"
        y = self._stat("Greedy patch", greedy_text, y)
        y = self._stat("Infected neighbors", str(greedy_risk), y)
        y = self._stat("Greedy cost", f"{greedy_cost} pts", y)

        path_text = f"{path_length} nodes" if path_length > 0 else "No safe route"
        y = self._stat("Safe path", path_text, y)
        cooldown_text = f"{bt_cooldown} turns" if bt_cooldown > 0 else "Available"
        y = self._stat("BT cooldown", cooldown_text, y)

        y += 10
        self._text("Last action", x, y, self.font_small, self.MUTED)
        y += 18
        y = self._wrapped_text(current_action, x, y, self.font_small, self.CYAN, max_width, 3)
        y += 12

        controls = [
            "Arrows: Manual movement (1 step)",
            "Click: patch a selected healthy node",
            "Shift + Click: reinforce a healthy node",
            "G: patch the highest-risk node",
            "B: preview / advance along safe path",
            "R: reset game",
            "F11: toggle fullscreen",
            "ESC: quit",
        ]
        self._text("Controls", x, y, self.font_small, self.MUTED)
        y += 20
        for control in controls:
            y = self._wrapped_text(control, x, y, self.font_tiny, self.TEXT, max_width, 2)
            y += 4

    def draw_tooltip(self, row: int, col: int, degree: int) -> None:
        """Draw a small tooltip next to a grid node."""
        cx, cy = self.node_center(row, col)
        text = f"({row},{col}) degree={degree}"
        surface = self.font_small.render(text, True, self.TEXT)
        rect = surface.get_rect(topleft=(cx + self.node_radius + 4, cy - self.node_radius))
        box = rect.inflate(12, 8)
        pygame.draw.rect(self.screen, self.PANEL, box, border_radius=6)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, box, 1, border_radius=6)
        self.screen.blit(surface, rect)

    def draw_greedy_hint(self, row: int, col: int) -> None:
        cx, cy = self.node_center(row, col)
        pygame.draw.circle(self.screen, self.GOLD, (cx, cy), self.node_radius + max(4, self.cell_size // 7), max(2, self.cell_size // 14))

    def draw_goal(self, row: int, col: int) -> None:
        cx, cy = self.node_center(row, col)
        size = self.node_radius + max(7, self.cell_size // 5)
        pygame.draw.circle(self.screen, self.PURPLE, (cx, cy), size, max(2, self.cell_size // 16))
        self._text("GOAL", cx - self.node_radius, cy + size + 2, self.font_tiny, self.PURPLE)

    def draw_safe_path(self, nodes: Iterable[Position]) -> None:
        path = list(nodes)
        if len(path) < 2:
            return
        centers = [self.node_center(row, col) for row, col in path]
        pygame.draw.lines(self.screen, self.BLUE, False, centers, max(2, self.cell_size // 10))
        for idx, (row, col) in enumerate(path):
            cx, cy = self.node_center(row, col)
            radius = self.node_radius + max(4, self.cell_size // 8)
            pygame.draw.circle(self.screen, self.BLUE, (cx, cy), radius, max(2, self.cell_size // 18))
            if idx > 0:
                pygame.draw.circle(self.screen, self.CYAN, (cx, cy), max(2, self.cell_size // 12))

    # Compatibility name from the previous perimeter preview design.
    def draw_backtracking_preview(self, nodes: Iterable[Position]) -> None:
        self.draw_safe_path(nodes)

    def draw_infected_pulse(self, infected_nodes: Iterable[Position], tick: int) -> None:
        pulse = int(3 + 3 * math.sin(tick / 220))
        for row, col in infected_nodes:
            cx, cy = self.node_center(row, col)
            pygame.draw.circle(self.screen, self.RED, (cx, cy), self.node_radius + 5 + pulse, max(2, self.cell_size // 18))

    def draw_current_node(self, row: int, col: int) -> None:
        cx, cy = self.node_center(row, col)
        pygame.draw.circle(self.screen, self.WHITE, (cx, cy), self.node_radius + max(4, self.cell_size // 9), max(2, self.cell_size // 18))
        pygame.draw.circle(self.screen, self.CYAN, (cx, cy), max(3, self.cell_size // 10))

    def draw_flash(self, row: int, col: int, alpha: int = 180) -> None:
        cx, cy = self.node_center(row, col)
        size = (self.node_radius + 10) * 2
        overlay = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (255, 255, 255, alpha), (size // 2, size // 2), self.node_radius + 8)
        self.screen.blit(overlay, (cx - size // 2, cy - size // 2))

    def draw_game_over(self, score: int) -> None:
        self._draw_final_screen("GAME OVER", f"Final score: {score}", self.RED)

    def draw_victory(self, turn: int) -> None:
        self._draw_final_screen("MISSION COMPLETE", f"Turns used: {turn}", self.CYAN)

    def _draw_final_screen(self, title: str, subtitle: str, color: tuple[int, int, int]) -> None:
        width, height = self.screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        title_surf = self.font_title.render(title, True, color)
        subtitle_surf = self.font.render(subtitle, True, self.TEXT)
        help_surf = self.font.render("Press R to reset or ESC to quit", True, self.MUTED)
        self.screen.blit(title_surf, title_surf.get_rect(center=(width // 2, height // 2 - 42)))
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(width // 2, height // 2)))
        self.screen.blit(help_surf, help_surf.get_rect(center=(width // 2, height // 2 + 40)))

    def _stat(self, label: str, value: str, y: int) -> int:
        x = self.hud_rect.x + 18
        value_x = x + max(125, min(165, self.hud_rect.width // 2))
        self._text(label, x, y, self.font_small, self.MUTED)
        self._text(value, value_x, y, self.font_small, self.TEXT)
        return y + 23

    def _text(self, text: str, x: int, y: int, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        self.screen.blit(font.render(text, True, color), (x, y))

    def _wrapped_text(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        max_width: int,
        max_lines: int,
    ) -> int:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = word if not current else f"{current} {word}"
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if not lines:
            lines = [""]

        for idx, line in enumerate(lines[:max_lines]):
            if idx == max_lines - 1 and len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
                line = line.rstrip(" .") + "..."
            self._text(line, x, y, font, color)
            y += font.get_height() + 2
        return y
