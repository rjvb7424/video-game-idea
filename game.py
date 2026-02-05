import math
import os
import pygame

import event_content
from core.camera import Camera
from core.date import GameDate
from core.math_utils import clamp
from core.surfaces import tile_fill
from events import EventRegistry, EventSystem, register_all, date_ordinal
from rendering.map_view import MapRenderer
from systems.buildings import (
    BUILDINGS,
    make_building,
    get_building_id,
    get_building_level,
    building_food_output,
    building_max_level,
)
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits
from ui.layout import Layout
from ui.manager import UIManager
from ui.modal import Modal
from ui.text import wrap_text
from ui.theme import BG_COLOR, FOOTER_FONT
from ui.utils import clip_draw
from world.map import MapWorld


class GameApp:
    def __init__(self):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "center")
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.windowed_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.mode = "menu"
        self.storyteller = None
        self._storyteller_start_day = None
        self.realm_select_page = 0
        self.realm_candidate_id = None
        self._realm_ui_rects = []
        self.storytellers = [
            {
                "id": "cassius_classic",
                "name": "Cassius Classic",
                "desc": "Vanilla and fair. A steady cadence of events with no strong bias.",
                "event_chance_mult": 1.0,
                "event_chance_ramp_per_year": 0.0,
                "event_chance_max_mult": 1.0,
            },
            {
                "id": "edgar_extinction",
                "name": "Edgar Extinction",
                "desc": "Harsher events and a rising tempo as the years pass.",
                "event_chance_mult": 1.25,
                "event_chance_ramp_per_year": 0.15,
                "event_chance_max_mult": 2.0,
            }
        ]
        self._storyteller_portraits = self._load_storyteller_portraits()
        self._storyteller_portrait_cache = {}

        self._menu_bg = self._load_menu_background()
        self._menu_bg_cache = {}
        font_path = pygame.font.match_font("arial")
        self.menu_title_font = pygame.font.Font(font_path, 72)
        self.menu_header_font = pygame.font.Font(font_path, 40)
        self.menu_subtitle_font = pygame.font.Font(font_path, 24)
        self.menu_button_font = pygame.font.Font(font_path, 22)
        self.menu_caption_font = pygame.font.Font(font_path, 18)

        self.ui = UIManager(seed=11)
        self.layout = Layout(*self.screen.get_size())
        self._game_bg_cache = {}

        self.world = MapWorld(seed=7, world_size=(3200, 2200), cell_scale=4)
        self.camera = Camera(viewport_size=(100, 100), world_size=(self.world.world_w, self.world.world_h))
        self.map_renderer = MapRenderer(self.world, self.camera)
        self.camera.set_viewport(self._get_map_rect().size)
        self._prov_adj = self.world._build_province_adjacency()

        self.modal = Modal()

        self.date = GameDate(1067, 1, 21)
        self.speed_level = 0  # 0 paused, 1..3 speeds
        self.speed_days_per_sec = {0: 0, 1: 1, 2: 3, 3: 7}
        self._time_accum = 0.0

        self.selected_province = None
        self._building_menu_slot = None
        self.right_panel_open = True
        self._right_panel_anim = 0.0
        self.left_panel_open = False
        self._left_panel_anim = 0.0
        self._left_panel_toggle_rect = None
        self._bottom_bar_rect = None

        # --- EVENTS: minimal integration ---
        self._event_flags = {}
        self._event_pending = []
        self._event_resume_speed = None

        self.event_registry = EventRegistry(seed=123)
        register_all(self.event_registry, event_content)
        self.base_event_daily_chance = 0.05
        self.events = EventSystem(self, self.event_registry, daily_chance=self.base_event_daily_chance, seed=999)

        self.resources = {
            "gold": 200,
            "gold_rate": +1,
            "piety": 1000,
        }

        # Player character = ruler of player realm
        self.player_realm_id = self.world.player_realm_id
        self.character = self.world.realm_rulers[self.player_realm_id]

        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]

        # Approximation: able-bodied levy pool (~12% of total population).
        self.army_pop_ratio = 0.12
        self.army_raise_rate = 0.06  # fraction of max raised per day while mustering
        self.army_move_speed = 140  # world units per day
        self.army = {"raised": 0, "max": 0, "morale": 77}
        self.army_raising = False
        self.army_selected = False
        self.army_pos = None
        self.army_prov_id = None
        self.army_route = []
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0
        self.army_step_flash = 0.0
        self.army_last_step = None
        self.food = (0, 0)  # (produced, consumed)
        self.food_consumption_per_pop = 0.39  # monthly consumption per person
        self._rebalance_population_to_farms()
        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()

        self.log = [
            "January 8, 1067: Rumors of usurpation spread in Carinthia.",
            "January 11, 1067: A distant court recognizes new claims.",
            "January 18, 1067: A master of arms returns from pilgrimage.",
        ]

        # map interaction
        self._mouse_down_in_map = False
        self._mouse_down_pos = (0, 0)
        self._mouse_drag_threshold = 5
        self._drag_started = False
        self._prev_mouse_down = False

        self.running = True

        # Start maximized but still resizable.
        self._apply_window_size_desktop()

    def _load_menu_background(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))
        path = os.path.join(base_dir, "boreal_forest.png")
        if os.path.exists(path):
            return pygame.image.load(path).convert()
        return None

    def _load_storyteller_portraits(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "storytellers"))
        portraits = {}
        for st in self.storytellers:
            path = os.path.join(base_dir, f"{st['id']}.png")
            if os.path.exists(path):
                portraits[st["id"]] = pygame.image.load(path).convert_alpha()
        return portraits

    def _get_storyteller_portrait(self, storyteller_id, size):
        src = self._storyteller_portraits.get(storyteller_id)
        if src is None:
            return None
        key = (storyteller_id, int(size[0]), int(size[1]))
        cached = self._storyteller_portrait_cache.get(key)
        if cached is not None:
            return cached
        sw, sh = src.get_size()
        if sw <= 0 or sh <= 0:
            return None
        scale = min(size[0] / sw, size[1] / sh)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        scaled = pygame.transform.smoothscale(src, (new_w, new_h))
        self._storyteller_portrait_cache[key] = scaled
        return scaled

    def _get_menu_bg_scaled(self, size):
        if self._menu_bg is None:
            return None, (0, 0)
        cache_key = (int(size[0]), int(size[1]))
        cached = self._menu_bg_cache.get(cache_key)
        if cached is not None:
            return cached
        bg_w, bg_h = self._menu_bg.get_size()
        scale = max(size[0] / bg_w, size[1] / bg_h)
        new_w = max(1, int(bg_w * scale))
        new_h = max(1, int(bg_h * scale))
        scaled = pygame.transform.smoothscale(self._menu_bg, (new_w, new_h))
        offset = ((size[0] - new_w) // 2, (size[1] - new_h) // 2)
        cached = (scaled, offset)
        self._menu_bg_cache[cache_key] = cached
        return cached

    def _draw_menu_background(self, surface):
        size = surface.get_size()
        if self._menu_bg is None:
            surface.fill(BG_COLOR)
            return
        scaled, offset = self._get_menu_bg_scaled(size)
        if scaled is None:
            surface.fill(BG_COLOR)
            return
        surface.blit(scaled, offset)

    def _get_game_bg(self, size):
        key = (int(size[0]), int(size[1]))
        cached = self._game_bg_cache.get(key)
        if cached is not None:
            return cached
        bg = pygame.Surface(size).convert()
        bg.fill(BG_COLOR)
        tile_fill(bg, bg.get_rect(), self.ui.bottom_tile)
        bg.set_alpha(70)
        self._game_bg_cache[key] = bg
        return bg

    def _get_map_rect(self):
        if self.mode in ("realm_select", "game"):
            w, h = self.screen.get_size()
            return pygame.Rect(0, 0, w, h)
        return self.layout.map

    def _left_panel_draw_rect(self):
        rect = self.layout.left
        offset = -int((1.0 - self._left_panel_anim) * rect.w)
        return rect.move(offset, 0)

    def _point_in_ui(self, pos):
        if self.mode == "realm_select":
            return any(r.collidepoint(pos) for r in self._realm_ui_rects)
        if self.mode == "game":
            if self.layout.top.collidepoint(pos):
                return True
            if self._bottom_bar_rect and self._bottom_bar_rect.collidepoint(pos):
                return True
            if self._left_panel_anim > 0.01 and self._left_panel_draw_rect().collidepoint(pos):
                return True
            if self._left_panel_toggle_rect and self._left_panel_toggle_rect.collidepoint(pos):
                return True
            if self._right_panel_anim > 0.01 and self.layout.right.collidepoint(pos):
                return True
        return False

    def _draw_selected_province_highlight(self, surface, map_rect):
        if self.selected_province is None:
            return
        sp = self.camera.world_to_screen(self.selected_province.center, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return
        t = pygame.time.get_ticks() / 350.0
        pulse = 0.5 + 0.5 * math.sin(t)
        base = 14
        ring = base + int(8 * pulse)
        pygame.draw.circle(surface, (250, 220, 120), (x, y), ring, 3)
        pygame.draw.circle(surface, (255, 245, 230), (x, y), base, 2)

    def _draw_army_muster_marker(self, surface, map_rect):
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            return
        if self.army_pos is None:
            return
        max_army = int(self.army.get("max", 0))
        if max_army <= 0:
            return
        raised = int(self.army.get("raised", 0))
        ratio = 0.0 if max_army <= 0 else max(0.0, min(1.0, raised / max_army))

        if self.army_pos is None:
            return
        sp = self.camera.world_to_screen(self.army_pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return

        # Small pennant + progress bar
        flag_rect = pygame.Rect(x - 6, y - 30, 12, 16)
        pygame.draw.rect(surface, (30, 30, 36), flag_rect, border_radius=2)
        fill_color = (200, 180, 90) if self.army_selected else (140, 160, 210)
        pygame.draw.rect(surface, fill_color, flag_rect.inflate(-2, -2), border_radius=2)
        pygame.draw.rect(surface, (10, 10, 12), flag_rect, 1, border_radius=2)

        if self.army_raising:
            bar_w, bar_h = 64, 7
            bar_rect = pygame.Rect(x - bar_w // 2, y - 12, bar_w, bar_h)
            pygame.draw.rect(surface, (20, 20, 22), bar_rect, border_radius=4)
            fill_w = int(bar_rect.w * ratio)
            if fill_w > 0:
                fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_rect.h)
                pygame.draw.rect(surface, (160, 190, 230), fill_rect, border_radius=4)
            pygame.draw.rect(surface, (0, 0, 0), bar_rect, 1, border_radius=4)

        if self.army_selected:
            pygame.draw.circle(surface, (230, 210, 120), (x, y - 20), 14, 2)

    def _draw_army_route_arrow(self, surface, map_rect):
        def draw_arrow_head(p0, p1, color, width=3):
            vx = p1[0] - p0[0]
            vy = p1[1] - p0[1]
            length = max(1.0, math.hypot(vx, vy))
            ux, uy = vx / length, vy / length
            left = (p1[0] - ux * 10 - uy * 6, p1[1] - uy * 10 + ux * 6)
            right = (p1[0] - ux * 10 + uy * 6, p1[1] - uy * 10 - ux * 6)
            pygame.draw.polygon(surface, color, [p1, left, right])

        if not self.army_route or self.army_pos is None:
            return
        if self.army_step_to is None:
            return

        points_world = [self.army_pos] + [self.world.provinces[pid].center for pid in self.army_route]
        if len(points_world) < 2:
            return

        points = [
            (int(self.camera.world_to_screen(p, map_rect, use_target=False).x),
             int(self.camera.world_to_screen(p, map_rect, use_target=False).y))
            for p in points_world
        ]

        # White base arrow path
        pygame.draw.lines(surface, (230, 230, 230), False, points, 3)
        draw_arrow_head(points[-2], points[-1], (230, 230, 230), width=3)

        # Red fill along the first segment only (progress to next province)
        p0, p1 = points[0], points[1]
        progress = max(0.0, min(1.0, self.army_step_progress))
        mid = (p0[0] + (p1[0] - p0[0]) * progress, p0[1] + (p1[1] - p0[1]) * progress)
        pygame.draw.line(surface, (200, 60, 60), p0, mid, 4)

    def _army_icon_rect(self, map_rect):
        if self.army_pos is None:
            return None
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            return None
        sp = self.camera.world_to_screen(self.army_pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        return pygame.Rect(x - 10, y - 36, 20, 26)

    def _handle_army_click(self, screen_pos, map_rect):
        icon = self._army_icon_rect(map_rect)
        if icon and icon.collidepoint(screen_pos):
            if self.army.get("raised", 0) <= 0 and not self.army_raising:
                return True
            self.army_selected = not self.army_selected
            if self.army_selected:
                self.selected_province = None
                self._building_menu_slot = None
                self.push_log(f"{self.date}: Army selected.")
            return True
        if self.army_selected and self.army_pos is not None:
            if self.army.get("raised", 0) <= 0:
                self.push_log("Army is still mustering.")
                return True
            wp = self.camera.screen_to_world(screen_pos, map_rect, use_target=False)
            prov = self.world.province_at_world(wp)
            if prov is None:
                return True
            self._ensure_army_position()
            start_pid = self.army_prov_id
            if start_pid is None:
                return True
            if prov.id == start_pid:
                self.army_route = []
                self.army_step_from = None
                self.army_step_to = None
                self.army_step_progress = 0.0
                return True
            route = self._find_province_path(start_pid, prov.id)
            if not route:
                self.push_log("No route for the army.")
                return True
            self.army_route = route
            self.army_step_from = start_pid
            self.army_step_to = route[0]
            self.army_step_progress = 0.0
            self.push_log(f"{self.date}: Army marching to {prov.name}.")
            return True
        return False

    def _draw_right_panel_animated(self, surface, state):
        if self._right_panel_anim <= 0.01:
            return []
        rect = self.layout.right
        offset = int((1.0 - self._right_panel_anim) * rect.w)
        draw_rect = rect.move(offset, 0)
        panel_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        btns_local = self.ui.draw_right_panel(panel_layer, panel_layer.get_rect(), state)
        panel_layer.set_alpha(int(255 * self._right_panel_anim))
        surface.blit(panel_layer, draw_rect.topleft)

        btns = []
        for r, action in btns_local:
            btns.append((r.move(draw_rect.left, draw_rect.top), action))
        return btns

    def _draw_left_panel_animated(self, surface, state):
        if self._left_panel_anim <= 0.01:
            self._left_panel_toggle_rect = None
            btns = self.ui.draw_left_panel_toggle(surface, self.layout.left, state)
            if btns:
                self._left_panel_toggle_rect = btns[0][0]
            return btns

        self._left_panel_toggle_rect = None
        rect = self.layout.left
        draw_rect = self._left_panel_draw_rect()

        panel_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        btns_local = self.ui.draw_left_panel(panel_layer, panel_layer.get_rect(), state, show_close=True)
        panel_layer.set_alpha(int(255 * self._left_panel_anim))
        surface.blit(panel_layer, draw_rect.topleft)

        btns = []
        for r, action in btns_local:
            btns.append((r.move(draw_rect.left, draw_rect.top), action))
        return btns

    def _get_desktop_size(self):
        if hasattr(pygame.display, "get_desktop_sizes"):
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                w, h = sizes[0]
                if w > 0 and h > 0:
                    return int(w), int(h)
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return int(info.current_w), int(info.current_h)
        return self.windowed_size

    def _apply_window_size_desktop(self):
        # Let SDL pick the desktop-sized window, but keep it resizable.
        self.screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        w, h = self.screen.get_size()
        if w <= 0 or h <= 0:
            w, h = self._get_desktop_size()
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.windowed_size = (w, h)
        self._center_window()
        self.layout.update(w, h)
        self.camera.set_viewport(self._get_map_rect().size)

    def _apply_window_size(self, size, remember=True):
        w = max(1024, int(size[0]))
        h = max(640, int(size[1]))
        if remember:
            self.windowed_size = (w, h)
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self._center_window()
        self.layout.update(w, h)
        self.camera.set_viewport(self._get_map_rect().size)

    def _center_window(self):
        if not hasattr(pygame.display, "set_window_position"):
            return
        w, h = self.screen.get_size()
        sw, sh = self._get_desktop_size()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        pygame.display.set_window_position(x, y)

    def _draw_menu_button(self, surface, rect, text, enabled=True):
        mx, my = pygame.mouse.get_pos()
        hovered = enabled and rect.collidepoint(mx, my)
        if enabled:
            bg = (55, 55, 60) if not hovered else (80, 80, 90)
            border = (10, 10, 10)
            text_color = (235, 228, 210)
        else:
            bg = (35, 35, 38)
            border = (18, 18, 20)
            text_color = (140, 135, 125)
        pygame.draw.rect(surface, bg, rect, border_radius=6)
        pygame.draw.rect(surface, border, rect, width=2, border_radius=6)
        label = self.menu_button_font.render(text, True, text_color)
        surface.blit(label, label.get_rect(center=rect.center))
        return rect

    @staticmethod
    def _ellipsize(text, font, max_w):
        if font.size(text)[0] <= max_w:
            return text
        ell = "..."
        max_w -= font.size(ell)[0]
        if max_w <= 0:
            return ell
        trimmed = text
        while trimmed and font.size(trimmed)[0] > max_w:
            trimmed = trimmed[:-1]
        return trimmed.rstrip() + ell

    def _draw_main_menu(self, surface):
        self._draw_menu_background(surface)

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 95))
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title = "Ascention"
        subtitle = "northen lords"

        title_surf = self.menu_title_font.render(title, True, (235, 228, 210))
        subtitle_surf = self.menu_subtitle_font.render(subtitle, True, (210, 202, 185))

        title_rect = title_surf.get_rect(center=(w // 2, int(h * 0.18)))
        subtitle_rect = subtitle_surf.get_rect(center=(w // 2, title_rect.bottom + 18))

        shadow = self.menu_title_font.render(title, True, (0, 0, 0))
        surface.blit(shadow, (title_rect.x + 3, title_rect.y + 3))
        surface.blit(title_surf, title_rect)
        surface.blit(subtitle_surf, subtitle_rect)

        btn_w = min(420, int(w * 0.55))
        btn_h = 46
        gap = 12
        start_y = int(h * 0.45)
        left = (w - btn_w) // 2

        labels = [
            ("Start Game", "menu_start"),
            ("Load Game", "menu_load"),
            ("Settings", "menu_settings"),
        ]

        clickables = []
        for i, (label, action) in enumerate(labels):
            rect = pygame.Rect(left, start_y + i * (btn_h + gap), btn_w, btn_h)
            self._draw_menu_button(surface, rect, label)
            clickables.append((rect, action))
        return clickables

    def _draw_storyteller_menu(self, surface):
        self._draw_menu_background(surface)

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        surface.blit(overlay, (0, 0))

        w, h = surface.get_size()
        title_surf = self.menu_header_font.render("Choose Storyteller", True, (235, 228, 210))
        subtitle_surf = self.menu_subtitle_font.render(
            "Storytellers shape how often events appear.",
            True,
            (210, 202, 185),
        )
        surface.blit(title_surf, title_surf.get_rect(center=(w // 2, int(h * 0.16))))
        surface.blit(subtitle_surf, subtitle_surf.get_rect(center=(w // 2, int(h * 0.22))))

        clickables = []
        total = max(1, len(self.storytellers))
        gap = 16
        top = int(h * 0.3)
        bottom_margin = 70
        available_h = max(0, h - top - bottom_margin)
        card_h = int((available_h - gap * (total - 1)) / total) if total > 0 else 180
        card_h = max(140, min(220, card_h))
        card_w = min(720, int(w * 0.82))
        left = (w - card_w) // 2

        for idx, st in enumerate(self.storytellers):
            card_rect = pygame.Rect(left, top + idx * (card_h + gap), card_w, card_h)
            pygame.draw.rect(surface, (26, 26, 30), card_rect, border_radius=10)
            pygame.draw.rect(surface, (8, 8, 8), card_rect, 2, border_radius=10)

            portrait_size = max(60, card_h - 32)
            portrait_rect = pygame.Rect(card_rect.left + 16, card_rect.top + 16, portrait_size, portrait_size)
            pygame.draw.rect(surface, (18, 18, 22), portrait_rect, border_radius=6)
            pygame.draw.rect(surface, (8, 8, 10), portrait_rect, 2, border_radius=6)

            portrait = self._get_storyteller_portrait(st["id"], portrait_rect.size)
            if portrait is not None:
                pr = portrait.get_rect(center=portrait_rect.center)
                surface.blit(portrait, pr)

            text_x = portrait_rect.right + 16
            text_w = card_rect.right - text_x - 16
            name_surf = self.menu_subtitle_font.render(st["name"], True, (235, 228, 210))
            surface.blit(name_surf, (text_x, card_rect.top + 14))

            desc_lines = wrap_text(st["desc"], self.menu_caption_font, text_w)
            y = card_rect.top + 48
            desc_limit = card_rect.bottom - 52
            for line in desc_lines:
                line_surf = self.menu_caption_font.render(line, True, (200, 192, 175))
                if y + line_surf.get_height() > desc_limit:
                    break
                surface.blit(line_surf, (text_x, y))
                y += line_surf.get_height() + 3

            mult = float(st.get("event_chance_mult", 1.0))
            ramp = float(st.get("event_chance_ramp_per_year", 0.0))
            max_mult = float(st.get("event_chance_max_mult", mult))
            if ramp > 0 and max_mult > mult:
                detail = f"Event rate: x{mult:.2f} -> x{max_mult:.2f} over time"
            else:
                detail = f"Event rate: x{mult:.2f}"
            detail_surf = self.menu_caption_font.render(detail, True, (178, 170, 156))
            detail_y = min(desc_limit - 18, card_rect.bottom - 70)
            surface.blit(detail_surf, (text_x, detail_y))

            label = f"Select {st['name']}"
            label_w = self.menu_button_font.size(label)[0] + 24
            btn_w = min(card_rect.w - 40, max(160, label_w))
            btn_rect = pygame.Rect(card_rect.right - btn_w - 16, card_rect.bottom - 40, btn_w, 30)
            self._draw_menu_button(surface, btn_rect, label)
            clickables.append((btn_rect, f"storyteller:{st['id']}"))

        hint = "After choosing a storyteller, pick your starting realm."
        hint_lines = wrap_text(hint, self.menu_caption_font, int(card_w * 0.9))
        hint_y = top + total * (card_h + gap) + 6
        for line in hint_lines:
            if hint_y > h - 70:
                break
            line_surf = self.menu_caption_font.render(line, True, (180, 172, 160))
            surface.blit(line_surf, line_surf.get_rect(center=(w // 2, hint_y)))
            hint_y += line_surf.get_height() + 2

        back_rect = pygame.Rect(20, h - 56, 140, 36)
        self._draw_menu_button(surface, back_rect, "Back")
        clickables.append((back_rect, "storyteller_back"))
        return clickables

    def _draw_realm_menu(self, surface):
        surface.fill(BG_COLOR)

        # Decorative background panels behind everything
        bg = pygame.Surface(surface.get_size())
        bg.fill(BG_COLOR)
        tile_fill(bg, bg.get_rect(), self.ui.bottom_tile)
        bg.set_alpha(60)
        surface.blit(bg, (0, 0))

        # Map (clickable selection)
        map_rect = self._get_map_rect()
        self.map_renderer.draw(surface, map_rect)

        # Left panel with ruler details for selected realm
        if self.realm_candidate_id is not None and 0 <= self.realm_candidate_id < len(self.world.realm_rulers):
            ruler = self.world.realm_rulers[self.realm_candidate_id]
        else:
            ruler = {
                "name": "No Ruler Selected",
                "title": "Select a realm",
                "house": "",
                "faith": "—",
                "culture": "—",
                "gender": "—",
                "age": "—",
                "traits": [],
                "stats": [
                    ("Diplomacy", "—"),
                    ("Martial", "—"),
                    ("Stewardship", "—"),
                    ("Intrigue", "—"),
                    ("Learning", "—"),
                    ("Prowess", "—"),
                ],
            }
        clip_draw(
            surface,
            self.layout.left,
            lambda: self.ui.draw_left_panel(surface, self.layout.left, {"character": ruler}),
        )

        # Highlight selected province / realm capital
        if self.realm_candidate_id is not None and 0 <= self.realm_candidate_id < len(self.world.realm_capitals):
            cap_pid = self.world.realm_capitals[self.realm_candidate_id]
            if 0 <= cap_pid < len(self.world.provinces):
                cap = self.world.provinces[cap_pid]
                sp = self.camera.world_to_screen(cap.center, map_rect, use_target=False)
                pygame.draw.circle(surface, (240, 210, 120), (int(sp.x), int(sp.y)), 18, 3)

        self._draw_selected_province_highlight(surface, map_rect)

        w, h = surface.get_size()
        st_name = self.storyteller["name"] if self.storyteller else "None"

        header_rect = pygame.Rect(int(w * 0.18), 16, int(w * 0.64), 96)
        pygame.draw.rect(surface, (18, 18, 20), header_rect, border_radius=8)
        pygame.draw.rect(surface, (5, 5, 6), header_rect, 2, border_radius=8)
        title_surf = self.menu_subtitle_font.render("Choose Your Realm", True, (235, 228, 210))
        surface.blit(title_surf, (header_rect.left + 16, header_rect.top + 10))
        sub_surf = self.menu_caption_font.render(f"Storyteller: {st_name}", True, (200, 192, 175))
        surface.blit(sub_surf, (header_rect.left + 16, header_rect.top + 40))
        hint = "Click a realm on the map, then confirm to begin."
        for i, line in enumerate(wrap_text(hint, self.menu_caption_font, header_rect.w - 32)):
            line_surf = self.menu_caption_font.render(line, True, (180, 172, 160))
            surface.blit(line_surf, (header_rect.left + 16, header_rect.top + 64 + i * 18))

        info_rect = pygame.Rect(int(w * 0.2), h - 150, int(w * 0.6), 110)
        pygame.draw.rect(surface, (20, 20, 22), info_rect, border_radius=8)
        pygame.draw.rect(surface, (6, 6, 7), info_rect, 2, border_radius=8)
        self._realm_ui_rects = [header_rect, info_rect, self.layout.left]

        clickables = []
        if self.realm_candidate_id is None:
            msg = self.menu_caption_font.render("No realm selected.", True, (190, 182, 168))
            surface.blit(msg, (info_rect.left + 16, info_rect.top + 16))
        else:
            realm_name = self.world.realm_names[self.realm_candidate_id]
            ruler = self.world.realm_rulers[self.realm_candidate_id].get("name", "Ruler")
            r1 = self.menu_caption_font.render(realm_name, True, (235, 228, 210))
            r2 = self.menu_caption_font.render(f"Ruler: {ruler}", True, (200, 192, 175))
            surface.blit(r1, (info_rect.left + 16, info_rect.top + 16))
            surface.blit(r2, (info_rect.left + 16, info_rect.top + 40))

        back_rect = pygame.Rect(info_rect.left + 12, info_rect.bottom - 40, 120, 30)
        self._draw_menu_button(surface, back_rect, "Back")
        clickables.append((back_rect, "realm_back"))

        confirm_rect = pygame.Rect(info_rect.right - 220, info_rect.bottom - 40, 200, 30)
        enabled = self.realm_candidate_id is not None
        self._draw_menu_button(surface, confirm_rect, "Start Game", enabled=enabled)
        if enabled:
            clickables.append((confirm_rect, "realm_confirm"))

        return clickables

    def _apply_storyteller(self, storyteller):
        self.storyteller = storyteller
        self._storyteller_start_day = date_ordinal(self.date)
        self._update_storyteller_event_chance()

    def _update_storyteller_event_chance(self):
        if not self.storyteller:
            self.events.daily_chance = self.base_event_daily_chance
            return
        mult = float(self.storyteller.get("event_chance_mult", 1.0))
        ramp = float(self.storyteller.get("event_chance_ramp_per_year", 0.0))
        max_mult = float(self.storyteller.get("event_chance_max_mult", mult))
        if ramp > 0.0 and self._storyteller_start_day is not None:
            days = max(0, date_ordinal(self.date) - self._storyteller_start_day)
            years = days / 365.0
            mult = min(max_mult, mult + ramp * years)
        else:
            mult = min(mult, max_mult)
        self.events.daily_chance = self.base_event_daily_chance * mult

    def _refresh_fog_visuals(self):
        if hasattr(self.world, "_render_base"):
            self.world._render_base()
        if hasattr(self.world, "_render_labels_and_markers"):
            self.world._render_labels_and_markers()

    def _set_full_visibility(self):
        self.world.visibility_by_prov = {p.id: 1.0 for p in self.world.provinces}
        self._refresh_fog_visuals()

    def _start_game_for_realm(self, rid):
        rid = max(0, min(int(rid), len(self.world.realm_names) - 1))
        self.player_realm_id = rid
        self.world.player_realm_id = rid

        cap_pid = None
        if 0 <= rid < len(self.world.realm_capitals):
            cap_pid = self.world.realm_capitals[rid]
            self.world.player_capital_pid = cap_pid

        if hasattr(self.world, "_compute_fog_of_war"):
            if hasattr(self.world, "extra_visible_provs"):
                self.world.extra_visible_provs = set()
            self.world._compute_fog_of_war()
            self._refresh_fog_visuals()

        self.character = self.world.realm_rulers[rid]
        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()

        if cap_pid is not None and 0 <= cap_pid < len(self.world.provinces):
            self.selected_province = self.world.provinces[cap_pid]
            center = self.selected_province.center
            self.camera.center = center.copy()
            self.camera.target_center = center.copy()
            self.camera.zoom = 1.0
            self.camera.target_zoom = 1.0
            self.camera._clamp_target()
            self.camera._clamp_actual()
        else:
            self.selected_province = None

    def _try_open_tower_event(self, screen_pos):
        tower_pid = getattr(self.world, "tower_pid", -1)
        if not (0 <= tower_pid < len(self.world.provinces)):
            return False

        tprov = self.world.provinces[tower_pid]
        map_rect = self._get_map_rect()
        sp = self.camera.world_to_screen(tprov.center, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)

        label = "Tower of Heaven"
        text = FOOTER_FONT.render(label, True, (0, 0, 0))
        text_rect = text.get_rect(midtop=(x, y + 8))
        icon_rect = pygame.Rect(x - 8, y - 28, 16, 30)
        hit_rect = icon_rect.union(text_rect.inflate(6, 4))

        if hit_rect.collidepoint(screen_pos):
            opened = self.events.open_event_by_id("tower_of_heaven_approach")
            if opened:
                self.selected_province = tprov
                self.right_panel_open = True
                if tprov.realm_id != self.player_realm_id:
                    self.left_panel_open = True
                self._building_menu_slot = None
            return opened
        return False

    def push_log(self, text):
        self.log.append(text)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def toggle_pause(self):
        if self.speed_level == 0:
            self.speed_level = 1
            self.push_log("Time resumes.")
        else:
            self.speed_level = 0
            self.push_log("Time paused.")

    def set_speed(self, level):
        self.speed_level = level
        if level == 0:
            self.push_log("Time paused.")
        else:
            self.push_log(f"Time speed set to {level}.")

    def open_menu(self):
        self.modal.show(
            "Game Menu",
            [
                "This is a functional UI modal (no assets) to demonstrate real flow.",
                "Exit cleanly to desktop, or close to return to the map.",
            ],
            [
                ("Close", "secondary", lambda: self.modal.close()),
                ("Exit", "deny", lambda: self._exit_game()),
            ],
        )

    def _exit_game(self):
        self.running = False

    def _compute_threat(self):
        # Base threat comes from population size; growth adds a slow pressure on top.
        growth_ratio = (self.population - self._baseline_population) / self._baseline_population
        growth_ratio = max(0.0, growth_ratio)
        base_threat = clamp(self.population / 3000.0, 3.0, 15.0)
        growth_threat = growth_ratio * 30.0  # scaled so growth adds slowly
        threat = base_threat + growth_threat
        return int(clamp(round(threat), 0, 100))

    def _update_army_max(self):
        max_army = int(round(self.population * self.army_pop_ratio))
        max_army = max(0, max_army)
        self.army["max"] = max_army
        if self.army["raised"] > max_army:
            self.army["raised"] = max_army
        if max_army == 0:
            self.army_raising = False
            self.army_selected = False
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            self.army_step_progress = 0.0
            self.army_pos = None
            self.army_prov_id = None
            self._update_fog_from_army()

    def _get_player_capital_pid(self):
        pid = getattr(self.world, "player_capital_pid", None)
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            if 0 <= self.player_realm_id < len(self.world.realm_capitals):
                pid = self.world.realm_capitals[self.player_realm_id]
        if pid is not None and 0 <= pid < len(self.world.provinces):
            return pid
        return None

    def _get_player_capital_center(self):
        pid = self._get_player_capital_pid()
        if pid is not None:
            return self.world.provinces[pid].center
        return pygame.Vector2(self.world.world_w * 0.5, self.world.world_h * 0.5)

    def _ensure_army_position(self):
        if self.army_pos is None or self.army_prov_id is None:
            pid = self._get_player_capital_pid()
            if pid is None:
                self.army_pos = self._get_player_capital_center().copy()
                return
            self._set_army_prov(pid)

    def _set_army_prov(self, pid):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return
        self.army_prov_id = pid
        self.army_pos = self.world.provinces[pid].center.copy()

    def _find_province_path(self, start_pid, target_pid):
        if start_pid == target_pid:
            return []
        adj = self._prov_adj
        prev = {start_pid: None}
        queue = [start_pid]
        head = 0
        while head < len(queue):
            cur = queue[head]
            head += 1
            if cur == target_pid:
                break
            for nb in adj[cur]:
                if nb in prev:
                    continue
                prev[nb] = cur
                queue.append(nb)
        if target_pid not in prev:
            return []
        path = []
        cur = target_pid
        while cur is not None and cur != start_pid:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path

    def _update_army_movement(self):
        if not self.army_route or self.army_prov_id is None:
            return
        if self.army.get("raised", 0) <= 0:
            return
        if self.army_step_to is None:
            self.army_step_from = self.army_prov_id
            self.army_step_to = self.army_route[0]
            self.army_step_progress = 0.0
        if self.army_step_to is None:
            return
        start = self.world.provinces[self.army_step_from].center
        end = self.world.provinces[self.army_step_to].center
        dist = max(1.0, (end - start).length())
        self.army_step_progress += self.army_move_speed / dist
        interp = max(0.0, min(1.0, self.army_step_progress))
        self.army_pos = start + (end - start) * interp
        if self.army_step_progress >= 1.0:
            self.army_step_progress = 1.0
            self.army_last_step = (self.army_step_from, self.army_step_to)
            self.army_step_flash = 0.25
            self._set_army_prov(self.army_step_to)
            self.army_route.pop(0)
            if self.army_route:
                self.army_step_from = self.army_prov_id
                self.army_step_to = self.army_route[0]
                self.army_step_progress = 0.0
            else:
                self.army_step_from = None
                self.army_step_to = None
                self.army_step_progress = 0.0
            self._update_fog_from_army()

    def _update_army_raising(self):
        if not self.army_raising:
            return
        self._ensure_army_position()
        self._update_fog_from_army()
        max_army = self.army.get("max", 0)
        if max_army <= 0:
            self.army_raising = False
            return
        if self.army["raised"] >= max_army:
            self.army["raised"] = max_army
            self.army_raising = False
            return
        per_day = max(1, int(round(max_army * self.army_raise_rate)))
        self.army["raised"] = min(max_army, self.army["raised"] + per_day)

    def _update_army_flash(self, dt):
        if self.army_step_flash > 0.0:
            self.army_step_flash = max(0.0, self.army_step_flash - dt)
            if self.army_step_flash <= 0.0:
                self.army_last_step = None

    def _update_fog_from_army(self):
        if not hasattr(self.world, "extra_visible_provs"):
            return
        extra = set()
        if (self.army.get("raised", 0) > 0 or self.army_raising) and self.army_prov_id is not None:
            extra.add(self.army_prov_id)
            if 0 <= self.army_prov_id < len(self._prov_adj):
                extra.update(self._prov_adj[self.army_prov_id])
        if extra == getattr(self.world, "extra_visible_provs", set()):
            return
        self.world.extra_visible_provs = extra
        if hasattr(self.world, "_compute_fog_of_war"):
            self.world._compute_fog_of_war()
            self._refresh_fog_visuals()

    def _update_right_panel_anim(self, dt):
        should_show = (
            self.mode == "game"
            and self.selected_province is not None
            and self.right_panel_open
        )
        target = 1.0 if should_show else 0.0
        speed = 6.0
        step = speed * dt
        if self._right_panel_anim < target:
            self._right_panel_anim = min(target, self._right_panel_anim + step)
        elif self._right_panel_anim > target:
            self._right_panel_anim = max(target, self._right_panel_anim - step)

    def _update_left_panel_anim(self, dt):
        should_show = self.mode == "game" and self.left_panel_open
        target = 1.0 if should_show else 0.0
        speed = 6.0
        step = speed * dt
        if self._left_panel_anim < target:
            self._left_panel_anim = min(target, self._left_panel_anim + step)
        elif self._left_panel_anim > target:
            self._left_panel_anim = max(target, self._left_panel_anim - step)

    def _compute_food_values(self):
        production = 0.0
        for prov in self.world.provinces:
            if prov.realm_id != self.player_realm_id:
                continue
            for b in getattr(prov, "buildings", []):
                production += building_food_output(b)
        consumption = self.population * self.food_consumption_per_pop
        production = int(round(production))
        consumption = int(round(consumption))
        return max(0, production), max(0, consumption)

    def _rebalance_population_to_farms(self, target_ratio=1.0):
        if self.food_consumption_per_pop <= 0:
            return

        realms = {}
        for prov in self.world.provinces:
            rid = prov.realm_id
            data = realms.setdefault(rid, {"provs": [], "current": 0, "food_output": 0.0})
            data["provs"].append(prov)
            data["current"] += prov.population
            for b in getattr(prov, "buildings", []):
                data["food_output"] += building_food_output(b)

        for data in realms.values():
            current = data["current"]
            if current <= 0:
                continue
            capacity = data["food_output"] / self.food_consumption_per_pop
            if capacity <= 0:
                continue
            target = int(capacity * target_ratio)
            if target <= 0 or current == target:
                continue
            scale = target / current
            for prov in data["provs"]:
                prov.population = max(1, int(round(prov.population * scale)))

    def _build_selected_building(self, building_id, slot_idx=None):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        if slot_idx is None:
            slot = prov.add_building(building_id)
            if slot < 0:
                self.push_log(f"{prov.name} has no empty building slots.")
                return
        else:
            if not (0 <= slot_idx < len(prov.buildings)):
                self.push_log("Invalid building slot.")
                return
            if prov.buildings[slot_idx] is not None:
                self.push_log(f"Slot {slot_idx + 1} is already occupied.")
                return
            prov.buildings[slot_idx] = make_building(building_id, level=1)
            slot = slot_idx
        bdef = BUILDINGS.get(building_id)
        bname = bdef.name if bdef else building_id
        self.push_log(f"{self.date}: Built {bname} in {prov.name} (slot {slot + 1}).")
        self.food = self._compute_food_values()
        self._building_menu_slot = None

    def _upgrade_selected_building(self, slot_idx):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        if not (0 <= slot_idx < len(prov.buildings)):
            self.push_log("Invalid building slot.")
            return
        entry = prov.buildings[slot_idx]
        if entry is None:
            self.push_log(f"Slot {slot_idx + 1} is empty.")
            return
        level = get_building_level(entry)
        max_level = building_max_level(entry)
        if max_level and level >= max_level:
            self.push_log("Building is already at max level.")
            return
        new_level = level + 1
        if isinstance(entry, dict):
            entry["level"] = new_level
        else:
            prov.buildings[slot_idx] = make_building(get_building_id(entry), level=new_level)
        bdef = BUILDINGS.get(get_building_id(entry))
        bname = bdef.name if bdef else get_building_id(entry)
        self.push_log(f"{self.date}: Upgraded {bname} in {prov.name} (slot {slot_idx + 1}).")
        self.food = self._compute_food_values()
        self._building_menu_slot = None

    def _demolish_selected_building(self, slot_idx):
        prov = self.selected_province
        if prov is None:
            self.push_log("No province selected.")
            return
        if prov.realm_id != self.player_realm_id:
            self.push_log("Cannot build outside your realm.")
            return
        if not (0 <= slot_idx < len(prov.buildings)):
            self.push_log("Invalid building slot.")
            return
        entry = prov.buildings[slot_idx]
        if entry is None:
            self.push_log(f"Slot {slot_idx + 1} is already empty.")
            return
        bdef = BUILDINGS.get(get_building_id(entry))
        bname = bdef.name if bdef else get_building_id(entry)
        prov.buildings[slot_idx] = None
        self.push_log(f"{self.date}: Demolished {bname} in {prov.name} (slot {slot_idx + 1}).")
        self.food = self._compute_food_values()
        self._building_menu_slot = None

    def _handle_action(self, action):
        if action == "menu_start":
            self.storyteller = None
            self._storyteller_start_day = None
            self.realm_select_page = 0
            self.realm_candidate_id = None
            self.mode = "storyteller"
            self.modal.close()
            return
        if action == "menu_load":
            self.modal.show(
                "Not Implemented",
                [
                    "Load game is a placeholder action.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        if action == "menu_settings":
            self.modal.show(
                "Not Implemented",
                [
                    "Settings is a placeholder action.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )
            return
        if action == "storyteller_back":
            self.realm_candidate_id = None
            self.selected_province = None
            self.right_panel_open = False
            self.mode = "menu"
            return
        if action.startswith("storyteller:"):
            sid = action.split(":", 1)[1]
            st = next((s for s in self.storytellers if s["id"] == sid), None)
            if st:
                self._apply_storyteller(st)
                self.realm_select_page = 0
                self.realm_candidate_id = None
                self.selected_province = None
                self.right_panel_open = False
                self._set_full_visibility()
                self.mode = "realm_select"
            return
        if action == "realm_back":
            self.realm_candidate_id = None
            self.selected_province = None
            self.right_panel_open = False
            self.mode = "storyteller"
            return
        if action == "realm_confirm":
            if self.realm_candidate_id is None:
                return
            self._start_game_for_realm(self.realm_candidate_id)
            self.mode = "game"
            self.camera.set_viewport(self._get_map_rect().size)
            self.left_panel_open = False
            self._left_panel_anim = 0.0
            return
        if action == "right_panel_close":
            self.right_panel_open = False
            return
        if action == "left_panel_close":
            self.left_panel_open = False
            return
        if action == "left_panel_open":
            self.left_panel_open = True
            return
        if action == "raise_army":
            if self.army_raising:
                self.army_raising = False
                if self.army.get("raised", 0) <= 0:
                    self.army_selected = False
                    self.army_route = []
                    self.army_step_from = None
                    self.army_step_to = None
                    self.army_step_progress = 0.0
                    self._update_fog_from_army()
                self.push_log("You halt the muster.")
            else:
                if self.army.get("max", 0) <= 0:
                    self.push_log("No population available to raise an army.")
                elif self.army.get("raised", 0) >= self.army.get("max", 0):
                    self.push_log("Your army is already fully raised.")
                else:
                    self._ensure_army_position()
                    self.army_raising = True
                    self._update_fog_from_army()
                    self.push_log("Your levies begin to muster.")
            return
        if action == "toggle_pause":
            self.toggle_pause()
        elif action == "speed_1":
            self.set_speed(1)
        elif action == "speed_2":
            self.set_speed(2)
        elif action == "speed_3":
            self.set_speed(3)
        elif action == "open_menu":
            self.open_menu()
        elif action == "build_farm":
            self._build_selected_building("farm")
        elif action.startswith("building_slot:"):
            parts = action.split(":")
            if len(parts) >= 3:
                try:
                    slot_idx = int(parts[1])
                except ValueError:
                    return
                verb = parts[2]
                if verb == "toggle":
                    if self._building_menu_slot == slot_idx:
                        self._building_menu_slot = None
                    else:
                        self._building_menu_slot = slot_idx
                elif verb == "build" and len(parts) >= 4:
                    self._build_selected_building(parts[3], slot_idx=slot_idx)
                elif verb == "upgrade":
                    self._upgrade_selected_building(slot_idx)
                elif verb == "demolish":
                    self._demolish_selected_building(slot_idx)
        elif action in (
            "ledger",
            "realm",
            "military",
            "decisions",
            "court",
            "council",
            "view_realm",
            "set_rally",
            "rally",
            "disband",
        ):
            self.modal.show(
                "Not Implemented",
                [
                    f"'{action}' is a placeholder action.",
                    "The UI is fully functional; game logic can be connected here.",
                ],
                [
                    ("OK", "accept", lambda: self.modal.close()),
                ],
            )

    def _update_time(self, dt):
        days_per_sec = self.speed_days_per_sec.get(self.speed_level, 0)
        if days_per_sec <= 0:
            return
        self._time_accum += dt * days_per_sec
        whole = int(self._time_accum)
        if whole > 0:
            for _ in range(whole):
                self.date.advance_days(1)

                # daily tick for events (random + chain)
                self._update_storyteller_event_chance()
                self.events.on_day()
                self._update_army_raising()
                self._update_army_movement()

                if self.date.day == 1:
                    self._apply_monthly_resource_rates()

            self._time_accum -= whole

    def _apply_monthly_resource_rates(self):
        for res in ("gold", "piety"):
            rate = self.resources.get(f"{res}_rate", 0)
            if rate == 0:
                continue
            self.resources[res] += rate
        # Food production comes from farms; consumption scales with population.
        production, consumption = self._compute_food_values()
        self.food = (production, consumption)

        # Population growth/decline based on food surplus/deficit.
        if consumption <= 0:
            food_balance = 1.0
        else:
            food_balance = (production - consumption) / consumption
        food_balance = max(-1.0, min(1.0, food_balance))

        if food_balance >= 0:
            pop_rate = 0.001 + 0.004 * food_balance  # base growth + surplus bonus
        else:
            pop_rate = 0.001 + 0.010 * food_balance  # stronger penalty for deficits

        if abs(pop_rate) > 0.00001:
            self.world.adjust_population_for_realm(self.player_realm_id, pop_rate)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self.threat = self._compute_threat()
        self._update_army_max()

    def _map_controls(self, dt):
        keys = pygame.key.get_pressed()
        if self.modal.open:
            return
        map_rect = self._get_map_rect()
        mx, my = pygame.mouse.get_pos()
        over_ui = self._point_in_ui((mx, my))

        # Keyboard panning (weighty due to camera smoothing)
        pan_speed = 720.0 / max(self.camera.target_zoom, 0.001)
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= pan_speed * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += pan_speed * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= pan_speed * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += pan_speed * dt
        if dx != 0.0 or dy != 0.0:
            self.camera.pan(dx, dy)

        # +/- zoom
        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            if map_rect.collidepoint((mx, my)) and not over_ui:
                self.camera.zoom_at(1.03, (mx, my), map_rect)
        if keys[pygame.K_MINUS]:
            if map_rect.collidepoint((mx, my)) and not over_ui:
                self.camera.zoom_at(0.97, (mx, my), map_rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0

            if self.mode == "game":
                self._bottom_bar_rect = self.ui.compute_bottom_bar_rect(
                    self.layout.bottom,
                    {
                        "date": self.date,
                        "army": self.army,
                        "army_raising": self.army_raising,
                        "speed_level": self.speed_level,
                    },
                )
            else:
                self._bottom_bar_rect = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.VIDEORESIZE:
                    self._apply_window_size((event.w, event.h), remember=True)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.modal.open:
                            self.modal.close()
                        elif self.mode == "game":
                            self.open_menu()
                        elif self.mode == "storyteller":
                            self.mode = "menu"
                        elif self.mode == "realm_select":
                            self.mode = "storyteller"
                    elif event.key == pygame.K_SPACE:
                        if not self.modal.open and self.mode == "game":
                            self.toggle_pause()

                # Mouse wheel zoom (pygame 2)
                elif event.type == pygame.MOUSEWHEEL and not self.modal.open and self.mode in ("game", "realm_select"):
                    mx, my = pygame.mouse.get_pos()
                    map_rect = self._get_map_rect()
                    if map_rect.collidepoint((mx, my)) and not self._point_in_ui((mx, my)):
                        factor = 1.12 if event.y > 0 else 0.89
                        self.camera.zoom_at(factor, (mx, my), map_rect)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and not self.modal.open and self.mode in ("game", "realm_select"):
                        map_rect = self._get_map_rect()
                        if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                            self._mouse_down_in_map = True
                            self._mouse_down_pos = event.pos
                            self._drag_started = False

                    # fallback wheel (old style)
                    if not self.modal.open and self.mode in ("game", "realm_select"):
                        map_rect = self._get_map_rect()
                        if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                            if event.button == 4:
                                self.camera.zoom_at(1.12, event.pos, map_rect)
                            elif event.button == 5:
                                self.camera.zoom_at(0.89, event.pos, map_rect)

                elif event.type == pygame.MOUSEMOTION:
                    if not self.modal.open and self.mode in ("game", "realm_select") and self._mouse_down_in_map:
                        dx = abs(event.pos[0] - self._mouse_down_pos[0])
                        dy = abs(event.pos[1] - self._mouse_down_pos[1])
                        if not self._drag_started and (dx + dy) > self._mouse_drag_threshold:
                            self._drag_started = True
                            self.camera.begin_drag(self._mouse_down_pos)

                        if self._drag_started:
                            self.camera.drag_to(event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.mode in ("game", "realm_select") and self._mouse_down_in_map:
                            if self._drag_started:
                                self.camera.end_drag()
                            else:
                                map_rect = self._get_map_rect()
                                if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                                    if self.mode == "game":
                                        if not self._try_open_tower_event(event.pos):
                                            if self._handle_army_click(event.pos, map_rect):
                                                self._mouse_down_in_map = False
                                                self._drag_started = False
                                                continue
                                            wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                            prov = self.world.province_at_world(wp)
                                            if prov is not None:
                                                self.army_selected = False
                                                self.selected_province = prov
                                                self.right_panel_open = True
                                                if prov.realm_id != self.player_realm_id:
                                                    self.left_panel_open = True
                                                self._building_menu_slot = None
                                                self.push_log(f"{self.date}: Selected {prov.name}.")
                                    elif self.mode == "realm_select":
                                        wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                        prov = self.world.province_at_world(wp)
                                        if prov is not None:
                                            self.selected_province = prov
                                            self.realm_candidate_id = prov.realm_id
                            self._mouse_down_in_map = False
                            self._drag_started = False

            # Continuous controls
            if self.mode in ("game", "realm_select"):
                self._map_controls(dt)

            # Time + camera easing
            if self.mode == "game":
                self._update_time(dt)
            if self.mode in ("game", "realm_select"):
                self.camera.update(dt)
            self._update_right_panel_anim(dt)
            self._update_left_panel_anim(dt)
            if self.mode == "game":
                self._update_army_flash(dt)

            # Draw
            clickables = []
            if self.mode == "menu":
                clickables = self._draw_main_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            elif self.mode == "storyteller":
                clickables = self._draw_storyteller_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            elif self.mode == "realm_select":
                clickables = self._draw_realm_menu(self.screen)
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)
            else:
                self.screen.fill(BG_COLOR)

                # Decorative background panels behind everything
                bg = self._get_game_bg(self.screen.get_size())
                self.screen.blit(bg, (0, 0))

                # Map
                map_rect = self._get_map_rect()
                self.map_renderer.draw(self.screen, map_rect)
                self._draw_selected_province_highlight(self.screen, map_rect)
                self._draw_army_muster_marker(self.screen, map_rect)
                self._draw_army_route_arrow(self.screen, map_rect)

                # UI panels
                state = {
                    "date": self.date,
                    "resources": self.resources,
                    "speed_level": self.speed_level,
                    "character": self.character,
                    "army": self.army,
                    "selected_province": self.selected_province,
                    "log": self.log,
                    "realm_names": self.world.realm_names,
                    "realm_rulers": self.world.realm_rulers,
                    "player_realm_id": self.player_realm_id,
                    "population": self.population,
                    "army_raising": self.army_raising,
                    "food": self.food,
                    "threat": self.threat,
                    "building_menu_slot": self._building_menu_slot,
                }

                clip_draw(self.screen, self.layout.top, lambda: clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state)))
                left_character = self.character
                if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                    rid = self.selected_province.realm_id
                    if 0 <= rid < len(self.world.realm_rulers):
                        left_character = self.world.realm_rulers[rid]
                left_state = dict(state)
                left_state["character"] = left_character

                clickables.extend(self._draw_left_panel_animated(self.screen, left_state))
                clickables.extend(self._draw_right_panel_animated(self.screen, state))
                clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state))

                # Modal on top
                modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)

            # Edge-triggered click dispatch
            now_down = pygame.mouse.get_pressed(num_buttons=3)[0]
            if self._prev_mouse_down and (not now_down):
                mx, my = pygame.mouse.get_pos()
                if self.modal.open:
                    for r, cb in modal_clickables:
                        if r.collidepoint((mx, my)):
                            cb()
                            break
                else:
                    for r, action in clickables:
                        if r.collidepoint((mx, my)):
                            self._handle_action(action)
                            break
            self._prev_mouse_down = now_down

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    GameApp().run()
