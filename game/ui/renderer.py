"""Pygame renderer for Virus Defense."""

from __future__ import annotations

import math
from typing import Iterable

import pygame

try:
    from algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, PATCHED, get_degree
except ImportError:  # pragma: no cover
    from game.algorithms.grid_utils import GRID_SIZE, HEALTHY, INFECTED, PATCHED, get_degree


class Renderer:
    """Draws the 12x12 board, HUD, highlights and final screens."""

    WINDOW_SIZE = (800, 600)
    GRID_ORIGIN = (30, 30)
    CELL_SIZE = 40
    NODE_RADIUS = 14
    HUD_X = 530
    HUD_WIDTH = 250

    COLORS = {
        HEALTHY: (76, 175, 80),
        INFECTED: (244, 67, 54),
        PATCHED: (255, 152, 0),
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

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 13)
        self.font_title = pygame.font.SysFont("arial", 24, bold=True)
        self.font_hud_title = pygame.font.SysFont("arial", 18, bold=True)

    def clear(self) -> None:
        self.screen.fill(self.BACKGROUND)

    def node_center(self, row: int, col: int) -> tuple[int, int]:
        origin_x, origin_y = self.GRID_ORIGIN
        return (
            origin_x + col * self.CELL_SIZE + self.CELL_SIZE // 2,
            origin_y + row * self.CELL_SIZE + self.CELL_SIZE // 2,
        )

    def draw_grid(self, grid: list[list[int]]) -> None:
        """Draw connections first and then draw the 12x12 node circles."""
        rows = len(grid)
        cols = len(grid[0]) if rows else GRID_SIZE

        for row in range(rows):
            for col in range(cols):
                cx, cy = self.node_center(row, col)
                if col + 1 < cols:
                    nx, ny = self.node_center(row, col + 1)
                    pygame.draw.line(self.screen, self.GRID_LINE, (cx, cy), (nx, ny), 1)
                if row + 1 < rows:
                    nx, ny = self.node_center(row + 1, col)
                    pygame.draw.line(self.screen, self.GRID_LINE, (cx, cy), (nx, ny), 1)

        for row in range(rows):
            for col in range(cols):
                cell = grid[row][col]
                cx, cy = self.node_center(row, col)
                color = self.COLORS.get(cell, self.COLORS[HEALTHY])
                pygame.draw.circle(self.screen, color, (cx, cy), self.NODE_RADIUS)
                pygame.draw.circle(self.screen, self.BACKGROUND, (cx, cy), self.NODE_RADIUS, 2)

    def get_clicked_node(self, mouse_pos: tuple[int, int]) -> tuple[int, int] | None:
        """Convert a mouse coordinate into a grid node, or None if outside."""
        mouse_x, mouse_y = mouse_pos
        origin_x, origin_y = self.GRID_ORIGIN
        grid_px = GRID_SIZE * self.CELL_SIZE

        if not (origin_x <= mouse_x < origin_x + grid_px and origin_y <= mouse_y < origin_y + grid_px):
            return None

        col = (mouse_x - origin_x) // self.CELL_SIZE
        row = (mouse_y - origin_y) // self.CELL_SIZE
        return int(row), int(col)

    def draw_hud(
        self,
        turn: int,
        budget: int,
        score: int,
        danger_level: float,
        greedy_hint: tuple[int, int] | None,
        greedy_cost: int,
        bt_size: int,
        bt_cooldown: int,
        current_action: str,
        current_node: tuple[int, int],
    ) -> None:
        """Draw the right sidebar with game state and controls."""
        panel = pygame.Rect(self.HUD_X, 30, self.HUD_WIDTH, 540)
        pygame.draw.rect(self.screen, self.PANEL, panel, border_radius=12)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, panel, 1, border_radius=12)

        y = 48
        self._text("Virus Defense", self.HUD_X + 18, y, self.font_hud_title, self.TEXT)
        y += 34
        self._text("UI Developer build — Pygame", self.HUD_X + 18, y, self.font_small, self.MUTED)
        y += 32

        y = self._stat("Turno", str(turn), y)
        y = self._stat("Presupuesto", f"{budget} pts", y)
        y = self._stat("Score", str(score), y)
        y = self._stat("Nodo actual", f"{current_node}", y)

        y += 8
        self._text("Nivel de peligro", self.HUD_X + 18, y, self.font_small, self.MUTED)
        y += 18
        bar_rect = pygame.Rect(self.HUD_X + 18, y, 205, 12)
        pygame.draw.rect(self.screen, (38, 45, 58), bar_rect, border_radius=6)
        danger_width = max(0, min(205, int(205 * danger_level)))
        pygame.draw.rect(self.screen, self.RED, pygame.Rect(bar_rect.x, bar_rect.y, danger_width, 12), border_radius=6)
        y += 32

        greedy_text = f"{greedy_hint}" if greedy_hint else "Fuera de alcance"
        y = self._stat("Costo Greedy", f"{greedy_cost} pts", y)
        y = self._stat("Sugerencia Greedy", greedy_text, y)
        y = self._stat("Perímetro BT", f"{bt_size} nodos", y)
        cooldown_text = f"{bt_cooldown} turnos" if bt_cooldown > 0 else "Disponible"
        y = self._stat("Cooldown BT", cooldown_text, y)

        y += 10
        self._text("Acción", self.HUD_X + 18, y, self.font_small, self.MUTED)
        y += 18
        self._text(current_action, self.HUD_X + 18, y, self.font, self.CYAN)
        y += 35

        controls = [
            "Click: patch vecino sano",
            "Shift + Click: reforzar nodo",
            "G: aplicar Greedy",
            "B: preview / confirmar BT",
            "R: reiniciar estado simulado",
            "ESC: salir",
        ]
        self._text("Controles", self.HUD_X + 18, y, self.font_small, self.MUTED)
        y += 20
        for control in controls:
            self._text(control, self.HUD_X + 18, y, self.font_small, self.TEXT)
            y += 21

    def draw_tooltip(self, row: int, col: int, degree: int) -> None:
        """Draw a small tooltip next to a grid node."""
        cx, cy = self.node_center(row, col)
        text = f"({row},{col}) grado={degree}"
        surface = self.font_small.render(text, True, self.TEXT)
        rect = surface.get_rect(topleft=(cx + 16, cy - 20))
        box = rect.inflate(12, 8)
        pygame.draw.rect(self.screen, self.PANEL, box, border_radius=6)
        pygame.draw.rect(self.screen, self.PANEL_BORDER, box, 1, border_radius=6)
        self.screen.blit(surface, rect)

    def draw_greedy_hint(self, row: int, col: int) -> None:
        cx, cy = self.node_center(row, col)
        pygame.draw.circle(self.screen, self.GOLD, (cx, cy), self.NODE_RADIUS + 6, 3)

    def draw_backtracking_preview(self, nodes: Iterable[tuple[int, int]]) -> None:
        for row, col in nodes:
            cx, cy = self.node_center(row, col)
            pygame.draw.circle(self.screen, self.BLUE, (cx, cy), self.NODE_RADIUS + 8, 2)
            pygame.draw.circle(self.screen, self.BLUE, (cx - 8, cy - 8), 2)
            pygame.draw.circle(self.screen, self.BLUE, (cx + 8, cy + 8), 2)

    def draw_infected_pulse(self, infected_nodes: Iterable[tuple[int, int]], tick: int) -> None:
        pulse = int(4 + 3 * math.sin(tick / 220))
        for row, col in infected_nodes:
            cx, cy = self.node_center(row, col)
            pygame.draw.circle(self.screen, self.RED, (cx, cy), self.NODE_RADIUS + 5 + pulse, 2)

    def draw_current_node(self, row: int, col: int) -> None:
        cx, cy = self.node_center(row, col)
        pygame.draw.circle(self.screen, self.WHITE, (cx, cy), self.NODE_RADIUS + 4, 2)
        pygame.draw.circle(self.screen, self.CYAN, (cx, cy), 4)

    def draw_flash(self, row: int, col: int, alpha: int = 180) -> None:
        cx, cy = self.node_center(row, col)
        overlay = pygame.Surface((self.NODE_RADIUS * 4, self.NODE_RADIUS * 4), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (255, 255, 255, alpha), (self.NODE_RADIUS * 2, self.NODE_RADIUS * 2), self.NODE_RADIUS + 8)
        self.screen.blit(overlay, (cx - self.NODE_RADIUS * 2, cy - self.NODE_RADIUS * 2))

    def draw_game_over(self, score: int) -> None:
        self._draw_final_screen("GAME OVER", f"Score final: {score}", self.RED)

    def draw_victory(self, turn: int) -> None:
        self._draw_final_screen("¡Red protegida!", f"Turnos usados: {turn}", self.CYAN)

    def _draw_final_screen(self, title: str, subtitle: str, color: tuple[int, int, int]) -> None:
        overlay = pygame.Surface(self.WINDOW_SIZE, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        title_surf = self.font_title.render(title, True, color)
        subtitle_surf = self.font.render(subtitle, True, self.TEXT)
        help_surf = self.font.render("Presiona R para reiniciar o ESC para salir", True, self.MUTED)
        self.screen.blit(title_surf, title_surf.get_rect(center=(400, 245)))
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(400, 285)))
        self.screen.blit(help_surf, help_surf.get_rect(center=(400, 325)))

    def _stat(self, label: str, value: str, y: int) -> int:
        self._text(label, self.HUD_X + 18, y, self.font_small, self.MUTED)
        self._text(value, self.HUD_X + 135, y, self.font_small, self.TEXT)
        return y + 24

    def _text(self, text: str, x: int, y: int, font: pygame.font.Font, color: tuple[int, int, int]) -> None:
        self.screen.blit(font.render(text, True, color), (x, y))
