"""
Virus Defense — Premium Pygame Renderer
========================================
Renders the 12x12 network grid with animated effects, HUD sidebar,
greedy/backtracking visual hints, and game state overlay screens.

Author: Alicia Pineda Quiroga (UI Developer)
"""

import pygame
import math
import time

GRID_SIZE = 12


class Renderer:
    """Handles all visual rendering for the Virus Defense game."""

    GRID_ORIGIN_X = 40
    GRID_ORIGIN_Y = 50
    CELL_SIZE = 42
    NODE_RADIUS = 15
    SIDEBAR_X = 555
    SIDEBAR_WIDTH = 245

    # ── Color Palette ──
    BG_DARK = (8, 10, 16)
    BG_PANEL = (14, 18, 28)
    BG_CARD = (22, 28, 42)
    BG_CARD_HOVER = (28, 36, 54)
    GRID_LINE = (30, 38, 55)

    HEALTHY_CORE = (45, 210, 130)
    HEALTHY_GLOW = (30, 170, 100)
    HEALTHY_INNER = (90, 235, 175)

    INFECTED_CORE = (240, 55, 55)
    INFECTED_GLOW = (180, 25, 25)
    INFECTED_INNER = (255, 110, 90)

    PATCHED_CORE = (245, 165, 40)
    PATCHED_GLOW = (210, 130, 25)
    PATCHED_INNER = (255, 215, 120)

    GREEDY_GOLD = (255, 210, 0)
    BACKTRACK_BLUE = (70, 130, 255)
    SELECTION_WHITE = (255, 255, 255)

    TEXT_PRIMARY = (225, 230, 240)
    TEXT_SECONDARY = (130, 145, 170)
    TEXT_MUTED = (75, 90, 115)
    ACCENT_PURPLE = (110, 95, 240)
    ACCENT_PURPLE_DIM = (75, 65, 160)
    DANGER_RED = (245, 60, 60)
    SUCCESS_GREEN = (45, 200, 140)
    COOLDOWN_CYAN = (70, 190, 230)

    font_title = None
    font_hud = None
    font_small = None
    font_tiny = None
    font_controls_key = None
    font_controls_desc = None
    font_overlay = None
    font_overlay_sub = None

    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()

        pygame.font.init()
        try:
            self.font_title = pygame.font.SysFont("Segoe UI", 20, bold=True)
            self.font_hud = pygame.font.SysFont("Segoe UI", 14)
            self.font_small = pygame.font.SysFont("Segoe UI", 12)
            self.font_tiny = pygame.font.SysFont("Consolas", 10)
            self.font_controls_key = pygame.font.SysFont("Consolas", 9, bold=True)
            self.font_controls_desc = pygame.font.SysFont("Consolas", 9)
            self.font_overlay = pygame.font.SysFont("Segoe UI", 44, bold=True)
            self.font_overlay_sub = pygame.font.SysFont("Segoe UI", 18)
        except Exception:
            self.font_title = pygame.font.Font(None, 24)
            self.font_hud = pygame.font.Font(None, 17)
            self.font_small = pygame.font.Font(None, 15)
            self.font_tiny = pygame.font.Font(None, 13)
            self.font_controls_key = pygame.font.Font(None, 12)
            self.font_controls_desc = pygame.font.Font(None, 12)
            self.font_overlay = pygame.font.Font(None, 48)
            self.font_overlay_sub = pygame.font.Font(None, 22)

        self.flash_nodes = {}
        self.particles = []

    def clear(self):
        self.screen.fill(self.BG_DARK)
        for x in range(0, self.width, 50):
            pygame.draw.line(self.screen, (12, 15, 22), (x, 0), (x, self.height))
        for y in range(0, self.height, 50):
            pygame.draw.line(self.screen, (12, 15, 22), (0, y), (self.width, y))

    def _node_center(self, row, col):
        x = self.GRID_ORIGIN_X + col * self.CELL_SIZE + self.CELL_SIZE // 2
        y = self.GRID_ORIGIN_Y + row * self.CELL_SIZE + self.CELL_SIZE // 2
        return (x, y)

    def _draw_glow(self, cx, cy, color, alpha, radius):
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius)
        self.screen.blit(surf, (cx - radius, cy - radius))

    def _draw_rounded_rect(self, rect, color, alpha=255, border_radius=8, border_color=None):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), border_radius=border_radius)
        self.screen.blit(surf, rect.topleft)
        if border_color:
            pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=border_radius)

    def draw_grid(self, grid):
        grid_size = len(grid)

        for r in range(grid_size):
            for c in range(grid_size):
                cx, cy = self._node_center(r, c)
                if c + 1 < grid_size:
                    nx, ny = self._node_center(r, c + 1)
                    pygame.draw.line(self.screen, self.GRID_LINE, (cx, cy), (nx, ny), 1)
                if r + 1 < grid_size:
                    nx, ny = self._node_center(r + 1, c)
                    pygame.draw.line(self.screen, self.GRID_LINE, (cx, cy), (nx, ny), 1)

        for r in range(grid_size):
            for c in range(grid_size):
                cx, cy = self._node_center(r, c)
                state = grid[r][c]

                if state == 0:
                    self._draw_glow(cx, cy, self.HEALTHY_GLOW, 25, self.NODE_RADIUS + 5)
                    pygame.draw.circle(self.screen, self.HEALTHY_CORE, (cx, cy), self.NODE_RADIUS)
                    pygame.draw.circle(self.screen, self.HEALTHY_INNER, (cx - 3, cy - 3), 4)

                elif state == 1:
                    self._draw_glow(cx, cy, self.INFECTED_GLOW, 40, self.NODE_RADIUS + 8)
                    pygame.draw.circle(self.screen, self.INFECTED_CORE, (cx, cy), self.NODE_RADIUS)
                    pygame.draw.circle(self.screen, self.INFECTED_INNER, (cx - 3, cy - 3), 3)

                elif state == 2:
                    self._draw_glow(cx, cy, self.PATCHED_GLOW, 30, self.NODE_RADIUS + 5)
                    pygame.draw.circle(self.screen, self.PATCHED_CORE, (cx, cy), self.NODE_RADIUS)
                    pygame.draw.line(self.screen, self.PATCHED_INNER, (cx - 5, cy), (cx + 5, cy), 2)
                    pygame.draw.line(self.screen, self.PATCHED_INNER, (cx, cy - 5), (cx, cy + 5), 2)

    def draw_infected_pulse(self, grid, tick):
        grid_size = len(grid)
        pulse = math.sin(tick * 0.005) * 4
        for r in range(grid_size):
            for c in range(grid_size):
                if grid[r][c] == 1:
                    cx, cy = self._node_center(r, c)
                    pulse_radius = self.NODE_RADIUS + int(pulse)
                    alpha = int(70 + 40 * math.sin(tick * 0.005))
                    self._draw_glow(cx, cy, (255, 70, 50), alpha, pulse_radius + 4)

    def draw_greedy_hint(self, row, col):
        if row < 0 or col < 0:
            return
        cx, cy = self._node_center(row, col)
        self._draw_glow(cx, cy, self.GREEDY_GOLD, 50, self.NODE_RADIUS + 12)
        pygame.draw.circle(self.screen, self.GREEDY_GOLD, (cx, cy), self.NODE_RADIUS + 4, 3)
        txt = self.font_tiny.render("*", True, self.GREEDY_GOLD)
        self.screen.blit(txt, (cx - txt.get_width() // 2, cy - self.NODE_RADIUS - 12))

    def draw_backtracking_preview(self, nodes):
        if not nodes:
            return
        tick = pygame.time.get_ticks()
        for node in nodes:
            r, c = node.get("row", -1), node.get("col", -1)
            if r < 0 or c < 0:
                continue
            cx, cy = self._node_center(r, c)
            self._draw_glow(cx, cy, self.BACKTRACK_BLUE, 40, self.NODE_RADIUS + 8)
            segments = 8
            for i in range(segments):
                if i % 2 == 0:
                    start_angle = (i / segments) * 2 * math.pi + (tick * 0.002)
                    end_angle = ((i + 1) / segments) * 2 * math.pi + (tick * 0.002)
                    rect = pygame.Rect(cx - self.NODE_RADIUS - 5, cy - self.NODE_RADIUS - 5,
                                       (self.NODE_RADIUS + 5) * 2, (self.NODE_RADIUS + 5) * 2)
                    pygame.draw.arc(self.screen, self.BACKTRACK_BLUE, rect, start_angle, end_angle, 2)

    def draw_node_flash(self, row, col):
        cx, cy = self._node_center(row, col)
        self._draw_glow(cx, cy, (255, 255, 255), 150, self.NODE_RADIUS + 4)

    def draw_selection_ring(self, row, col):
        if row < 0 or col < 0:
            return
        cx, cy = self._node_center(row, col)
        pygame.draw.circle(self.screen, self.SELECTION_WHITE, (cx, cy), self.NODE_RADIUS + 3, 2)
        tick = pygame.time.get_ticks()
        alpha = int(40 + 30 * math.sin(tick * 0.004))
        self._draw_glow(cx, cy, (255, 255, 255), alpha, self.NODE_RADIUS + 8)

    def draw_hud(self, turn, budget, score, danger_level, greedy_hint,
                 greedy_cost, bt_size, bt_cooldown, infected_count=0,
                 bt_preview_active=False, reinforce_cooldown=0):
        sx = self.SIDEBAR_X
        sw = self.SIDEBAR_WIDTH
        y = 20

        # ── Sidebar Background ──
        panel_rect = pygame.Rect(sx - 8, 10, sw + 16, self.height - 20)
        panel_surf = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (*self.BG_PANEL, 230), panel_surf.get_rect(), border_radius=10)
        self.screen.blit(panel_surf, panel_rect.topleft)
        pygame.draw.rect(self.screen, (35, 45, 65), panel_rect, 1, border_radius=10)

        # ── Accent line at top ──
        accent_rect = pygame.Rect(sx, 10, sw, 3)
        accent_surf = pygame.Surface((sw, 3), pygame.SRCALPHA)
        pygame.draw.rect(accent_surf, (*self.ACCENT_PURPLE, 180), (0, 0, sw, 3), border_radius=2)
        self.screen.blit(accent_surf, (sx, 10))

        # ── Title ──
        y = 22
        title = self.font_title.render("VIRUS DEFENSE", True, self.ACCENT_PURPLE)
        self.screen.blit(title, (sx + (sw - title.get_width()) // 2, y))
        y += 28

        sub = self.font_tiny.render("Red de 12x12", True, self.TEXT_MUTED)
        self.screen.blit(sub, (sx + (sw - sub.get_width()) // 2, y))
        y += 20

        # ── Divider ──
        pygame.draw.line(self.screen, (35, 45, 65), (sx + 10, y), (sx + sw - 10, y))
        y += 10

        # ── Stat card helper ──
        def stat_card(label, value, color, y_pos):
            card_rect = pygame.Rect(sx + 6, y_pos, sw - 12, 30)
            self._draw_rounded_rect(card_rect, self.BG_CARD, 160, 6)
            lbl = self.font_small.render(label, True, self.TEXT_SECONDARY)
            self.screen.blit(lbl, (sx + 14, y_pos + 8))
            val = self.font_hud.render(str(value), True, color)
            self.screen.blit(val, (sx + sw - val.get_width() - 14, y_pos + 7))
            return y_pos + 35

        y = stat_card("Turno", turn, self.TEXT_PRIMARY, y)
        y = stat_card("Presupuesto", f"{budget} pts", self.SUCCESS_GREEN, y)
        y = stat_card("Puntos", score, self.ACCENT_PURPLE, y)
        y = stat_card("Infectados", infected_count, self.DANGER_RED, y)

        # ── Victory Progress ──
        y += 4
        total = GRID_SIZE * GRID_SIZE
        clean = total - infected_count
        pct = clean / total if total > 0 else 1.0
        obj_label = self.font_small.render("Progreso victoria", True, self.TEXT_SECONDARY)
        self.screen.blit(obj_label, (sx + 14, y))
        y += 16
        prog_bg = pygame.Rect(sx + 14, y, sw - 28, 10)
        self._draw_rounded_rect(prog_bg, (25, 30, 45), 255, 5)
        prog_w = int((sw - 28) * pct)
        if prog_w > 0:
            prog_fill = pygame.Rect(sx + 14, y, prog_w, 10)
            if pct >= 1.0:
                prog_color = self.SUCCESS_GREEN
            elif pct >= 0.7:
                prog_color = (80, 200, 120)
            elif pct >= 0.4:
                prog_color = (220, 180, 40)
            else:
                prog_color = self.DANGER_RED
            self._draw_rounded_rect(prog_fill, prog_color, 255, 5)
        y += 14
        pct_text = self.font_tiny.render(f"{clean}/{total} celdas limpias", True, self.TEXT_MUTED)
        self.screen.blit(pct_text, (sx + (sw - pct_text.get_width()) // 2, y))
        y += 14
        if infected_count == 0:
            win_txt = self.font_small.render("Sin virus! Victoria!", True, self.SUCCESS_GREEN)
            self.screen.blit(win_txt, (sx + (sw - win_txt.get_width()) // 2, y))
        else:
            obj_txt = self.font_tiny.render("Contén el virus con parches", True, self.TEXT_MUTED)
            self.screen.blit(obj_txt, (sx + (sw - obj_txt.get_width()) // 2, y))
        y += 16

        # ── Danger Meter ──
        y += 4
        lbl = self.font_small.render("Nivel de Peligro", True, self.TEXT_SECONDARY)
        self.screen.blit(lbl, (sx + 14, y))
        y += 17
        bar_bg = pygame.Rect(sx + 14, y, sw - 28, 12)
        self._draw_rounded_rect(bar_bg, (25, 30, 45), 255, 6)
        danger_w = int((sw - 28) * min(danger_level, 1.0))
        if danger_w > 0:
            bar_fill = pygame.Rect(sx + 14, y, danger_w, 12)
            r_c = min(255, int(190 + 65 * danger_level))
            g_c = max(35, int(190 * (1 - danger_level)))
            self._draw_rounded_rect(bar_fill, (r_c, g_c, 35), 255, 6)
        y += 22

        # ── Divider ──
        pygame.draw.line(self.screen, (35, 45, 65), (sx + 10, y), (sx + sw - 10, y))
        y += 8

        # ── Abilities ──
        abl_title = self.font_small.render("Habilidades", True, self.ACCENT_PURPLE)
        self.screen.blit(abl_title, (sx + 14, y))
        y += 19

        # Greedy
        gc_color = self.SUCCESS_GREEN if budget >= greedy_cost else self.DANGER_RED
        y = stat_card("Greedy", f"{greedy_cost} pts", gc_color, y)

        # Backtracking
        if bt_cooldown > 0:
            bt_text = f"Enfriando ({bt_cooldown})"
            bt_color = self.COOLDOWN_CYAN
        else:
            bt_text = "Listo"
            bt_color = self.SUCCESS_GREEN
        y = stat_card("Backtracking", bt_text, bt_color, y)

        # Reinforce
        if reinforce_cooldown > 0:
            rf_text = f"Enfriando ({reinforce_cooldown})"
            rf_color = self.COOLDOWN_CYAN
        else:
            rf_text = "Listo"
            rf_color = self.SUCCESS_GREEN
        y = stat_card("Reforzar", rf_text, rf_color, y)

        if bt_size > 0:
            y = stat_card("Costo BT", f"{bt_size} pts", self.BACKTRACK_BLUE, y)

        # Greedy hint
        if greedy_hint and greedy_hint[0] >= 0 and greedy_hint[1] >= 0:
            hint_txt = f"({greedy_hint[0]}, {greedy_hint[1]})"
            hint_color = self.GREEDY_GOLD
        else:
            hint_txt = "---"
            hint_color = self.TEXT_MUTED
        y = stat_card("Sugerencia", hint_txt, hint_color, y)

        # ── Divider ──
        y += 4
        pygame.draw.line(self.screen, (35, 45, 65), (sx + 10, y), (sx + sw - 10, y))
        y += 8

        # ── Controls ──
        ctrl_title = self.font_small.render("Controles", True, self.ACCENT_PURPLE)
        self.screen.blit(ctrl_title, (sx + 14, y))
        y += 18

        controls = [
            ("Click", "Parchear (1 pt)"),
            ("Shift+Click", "Reforzar (3 pts)"),
            ("G", f"Greedy ({greedy_cost} pts)"),
            ("B", "Backtracking"),
            ("N", "Pasar turno"),
            ("R", "Reiniciar"),
            ("ESC", "Salir"),
        ]
        for key, desc in controls:
            key_w = 40
            key_rect = pygame.Rect(sx + 14, y, key_w, 15)
            self._draw_rounded_rect(key_rect, (25, 22, 50), 255, 3, (50, 45, 100))
            key_surf = self.font_controls_key.render(key, True, self.ACCENT_PURPLE)
            self.screen.blit(key_surf, (sx + 14 + (key_w - key_surf.get_width()) // 2, y + 1))

            max_desc_w = sw - key_w - 32
            desc_surf = self.font_controls_desc.render(desc, True, self.TEXT_SECONDARY)
            if desc_surf.get_width() > max_desc_w:
                truncated = desc
                while self.font_controls_desc.size(truncated + "...")[0] > max_desc_w and len(truncated) > 3:
                    truncated = truncated[:-1]
                desc_surf = self.font_controls_desc.render(truncated + "...", True, self.TEXT_SECONDARY)
            self.screen.blit(desc_surf, (sx + 14 + key_w + 6, y + 1))
            y += 18

        # ── Backtracking Preview Confirmation ──
        if bt_preview_active:
            y += 4
            pygame.draw.line(self.screen, (35, 45, 65), (sx + 10, y), (sx + sw - 10, y))
            y += 6
            confirm = self.font_small.render("B para confirmar", True, self.GREEDY_GOLD)
            self.screen.blit(confirm, (sx + (sw - confirm.get_width()) // 2, y))
            y += 16
            cancel = self.font_small.render("Click para cancelar", True, self.TEXT_MUTED)
            self.screen.blit(cancel, (sx + (sw - cancel.get_width()) // 2, y))

    def draw_tooltip(self, row, col, degree):
        cx, cy = self._node_center(row, col)
        txt = self.font_tiny.render(f"({row},{col}) d={degree}", True, self.TEXT_PRIMARY)
        bg_rect = pygame.Rect(cx + 18, cy - 12, txt.get_width() + 10, txt.get_height() + 6)
        self._draw_rounded_rect(bg_rect, (18, 22, 36), 230, 5, (50, 60, 90))
        self.screen.blit(txt, (bg_rect.x + 5, bg_rect.y + 3))

    def draw_game_over(self, score):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        vignette = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for i in range(60):
            alpha = max(0, 50 - i * 2)
            pygame.draw.rect(vignette, (200, 0, 0, alpha),
                             (i, i, self.width - i * 2, self.height - i * 2), 2)
        self.screen.blit(vignette, (0, 0))

        title = self.font_overlay.render("GAME OVER", True, self.DANGER_RED)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, self.height // 2 - 65))

        score_txt = self.font_overlay_sub.render(f"Puntos Finales: {score}", True, self.TEXT_PRIMARY)
        self.screen.blit(score_txt, ((self.width - score_txt.get_width()) // 2, self.height // 2))

        inst = self.font_hud.render("R para reiniciar  |  ESC para salir", True, self.TEXT_SECONDARY)
        self.screen.blit(inst, ((self.width - inst.get_width()) // 2, self.height // 2 + 35))

    def draw_victory(self, turn):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        vignette = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for i in range(60):
            alpha = max(0, 35 - i)
            pygame.draw.rect(vignette, (0, 220, 90, alpha),
                             (i, i, self.width - i * 2, self.height - i * 2), 2)
        self.screen.blit(vignette, (0, 0))

        title = self.font_overlay.render("RED PROTEGIDA!", True, self.SUCCESS_GREEN)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, self.height // 2 - 65))

        turn_txt = self.font_overlay_sub.render(f"Completado en {turn} turnos", True, self.TEXT_PRIMARY)
        self.screen.blit(turn_txt, ((self.width - turn_txt.get_width()) // 2, self.height // 2))

        inst = self.font_hud.render("R para reiniciar  |  ESC para salir", True, self.TEXT_SECONDARY)
        self.screen.blit(inst, ((self.width - inst.get_width()) // 2, self.height // 2 + 35))

    def draw_start_screen(self):
        self.clear()

        tick = pygame.time.get_ticks()
        glow_alpha = int(25 + 15 * math.sin(tick * 0.002))
        self._draw_glow(self.width // 2, self.height // 2 - 50, self.ACCENT_PURPLE, glow_alpha, 220)

        title = self.font_overlay.render("VIRUS DEFENSE", True, self.ACCENT_PURPLE)
        self.screen.blit(title, ((self.width - title.get_width()) // 2, self.height // 2 - 95))

        sub = self.font_overlay_sub.render("Equipo 10 - Variante 10 - Grid 12x12", True, self.TEXT_SECONDARY)
        self.screen.blit(sub, ((self.width - sub.get_width()) // 2, self.height // 2 - 38))

        inst = self.font_hud.render("Presiona cualquier tecla para comenzar", True, self.TEXT_MUTED)
        if (tick // 700) % 2 == 0:
            self.screen.blit(inst, ((self.width - inst.get_width()) // 2, self.height // 2 + 25))

        credits = self.font_tiny.render("Universidad Distrital - Computer Sciences I - 2026-I", True, self.TEXT_MUTED)
        self.screen.blit(credits, ((self.width - credits.get_width()) // 2, self.height - 35))

    def get_clicked_node(self, mouse_pos):
        mx, my = mouse_pos
        for r in range(12):
            for c in range(12):
                cx, cy = self._node_center(r, c)
                dist = math.sqrt((mx - cx) ** 2 + (my - cy) ** 2)
                if dist <= self.NODE_RADIUS + 3:
                    return (r, c)
        return None

    def update_flashes(self):
        now = time.time()
        expired = [k for k, v in self.flash_nodes.items() if now - v > 0.15]
        for k in expired:
            del self.flash_nodes[k]

    def draw_flashes(self):
        now = time.time()
        for (r, c), start in self.flash_nodes.items():
            elapsed = now - start
            if elapsed < 0.15:
                alpha = int(180 * (1 - elapsed / 0.15))
                cx, cy = self._node_center(r, c)
                self._draw_glow(cx, cy, (255, 255, 255), alpha, self.NODE_RADIUS + 5)

    def trigger_flash(self, row, col):
        self.flash_nodes[(row, col)] = time.time()
