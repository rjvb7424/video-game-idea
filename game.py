import math
import os
import pygame

import event_content
from core.camera import Camera
from core.date import GameDate
from core.math_utils import clamp
from core.surfaces import tile_fill
from events import EventRegistry, EventSystem, register_all
from rendering.map_view import MapRenderer
from systems.buildings import (
    BUILDINGS,
    make_building,
    get_building_id,
    get_building_level,
    building_food_output,
    building_gold_upkeep,
    building_gold_rate_bonus,
    building_piety_rate_bonus,
    building_prestige_rate_bonus,
    building_levy_mult_bonus,
    building_stress_monthly_relief,
    building_max_level,
)
from systems.army_mixin import ArmyMixin
from systems.menu_mixin import MenuMixin
from systems.persistence_mixin import PersistenceMixin
from systems.politics_mixin import PoliticsMixin
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits
from systems.war_mixin import WarMixin
from ui.layout import Layout
from ui.manager import UIManager
from ui.modal import Modal
from ui.theme import BG_COLOR, FOOTER_FONT
from ui.utils import clip_draw
from world.map import MapWorld


class GameApp(PersistenceMixin, PoliticsMixin, MenuMixin, ArmyMixin, WarMixin):
    def __init__(self):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        os.environ.setdefault("SDL_VIDEO_WINDOW_POS", "center")
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.windowed_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.mode = "menu"
        self.save_dir = os.path.join(os.path.dirname(__file__), "saves")
        self.latest_save_path = os.path.join(self.save_dir, "campaign_latest.json")
        self.autosave_path = os.path.join(self.save_dir, "campaign_autosave.json")
        self._autosave_interval_months = 3
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
        self._war_float_rects = []

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
            "prestige": 350,
            "renown": 120,
            "renown_rate": 1,
        }

        # War state (multiple active wars supported)
        self.wars = []
        self._war_next_id = 1
        self._war_focus_id = None
        self._war_border_overlay = None
        self._war_border_overlay_key = None
        self._pending_war = None
        self._war_goal_selecting = False

        # Siege system (CK-style timing)
        self.siege_prep_days = 7
        self.siege_assault_days = 21
        self._siege_state = None
        self._siege_overlay = None
        self._siege_overlay_key = None
        self._siege_stripe_base = None
        self._siege_stripe_base_key = None

        # Enemy AI + morale / stack wipe tuning
        self.enemy_raise_rate = 0.12
        self.ai_engage_ratio = 1.1
        self.ai_avoid_ratio = 0.85
        self.stack_wipe_attacker_morale = 60
        self.stack_wipe_defender_morale = 15
        self.morale_recovery_per_day = 1.5

        # Player character = ruler of player realm
        self.player_realm_id = self.world.player_realm_id
        self.character = self.world.realm_rulers[self.player_realm_id]

        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

        # CK2-style political layer
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.subjugation_cooldown_days = 0
        self._init_diplomacy_state()

        # CK3-style character systems
        self.active_schemes = []
        self._next_scheme_id = 1
        self.hooks = {}
        self.lifestyle_focuses = ("diplomacy", "martial", "stewardship", "intrigue", "learning")
        self.lifestyle_focus = "stewardship"
        self.lifestyle_xp = {k: 0.0 for k in self.lifestyle_focuses}
        self.lifestyle_perks = {k: 0 for k in self.lifestyle_focuses}
        self._lifestyle_picker_index = self.lifestyle_focuses.index(self.lifestyle_focus)
        self.stress = 12.0
        self._stress_break_level = 0
        self.dread = 0.0
        self.decision_cooldowns = {}
        self._raid_cooldown_days = 45
        self._ai_war_cooldown_days = 120
        self.resources["piety_rate"] = compute_piety_rate(self.character)[0]
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

        # Approximation: able-bodied levy pool (~12% of total population).
        self.army_pop_ratio = 0.12
        self.army_raise_rate = 0.15  # fraction of max raised per day while mustering
        self.army_move_speed = 110  # world units per day
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
        self.enemy_armies = []
        self.food = (0, 0)  # (produced, consumed)
        self.food_consumption_per_pop = 0.39  # monthly consumption per person
        self._rebalance_population_to_farms()
        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()
        self._init_enemy_armies()
        self._campaign_start_provinces = self._player_province_count()
        self._campaign_target_provinces = self._compute_campaign_target_provinces(self._campaign_start_provinces)
        self._insolvency_days = 0
        self._famine_days = 0
        self._crisis_days = 0
        self.campaign_result = None
        self._campaign_over_day = None
        self.last_played_realm_id = self.player_realm_id
        self._recompute_resource_rates()

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


    def _get_map_rect(self):
        if self.mode in ("realm_select", "game"):
            w, h = self.screen.get_size()
            return pygame.Rect(0, 0, w, h)
        return self.layout.map


    def _set_rally_point(self, pid, announce=True):
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return False
        prov = self.world.provinces[pid]
        if prov.realm_id != self.player_realm_id:
            return False
        self.world.player_capital_pid = pid
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            self._set_army_prov(pid)
        if announce:
            self.push_log(f"{self.date}: Rally point moved to {prov.name}.")
        return True

    def _rally_army_to_capital(self):
        rally_pid = self._get_player_capital_pid()
        if rally_pid is None:
            self.push_log("No rally point available.")
            return
        if self.army.get("raised", 0) <= 0:
            self._set_army_prov(rally_pid)
            self.push_log("Army is not raised; rally point updated for future mustering.")
            self._open_military_overview()
            return
        self._ensure_army_position()
        start_pid = self.army_prov_id
        if start_pid is None or start_pid == rally_pid:
            self.push_log("Army already at rally point.")
            self._open_military_overview()
            return
        route = self._find_province_path(start_pid, rally_pid)
        if not route:
            self.push_log("No route to rally point.")
            self._open_military_overview()
            return
        self.army_route = route
        self.army_step_from = start_pid
        self.army_step_to = route[0]
        self.army_step_progress = 0.0
        self.army_selected = True
        self.push_log(f"{self.date}: Army rally ordered.")
        self._open_military_overview()

    def _open_campaign_briefing(self):
        self.modal.show(
            "Realm Briefing",
            [
                "Sandbox mode enabled.",
                "Expand, fight wars, and manage your realm freely.",
            ],
            [
                ("Begin", "accept", lambda: self.modal.close()),
            ],
        )


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
            if self._war_float_rects and any(r.collidepoint(pos) for r in self._war_float_rects):
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

    def _get_siege_stripe_base(self):
        key = (self.world.world_w, self.world.world_h)
        if self._siege_stripe_base is not None and self._siege_stripe_base_key == key:
            return self._siege_stripe_base

        tile_size = 24
        stripe_gap = 6
        stripe = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
        stripe.fill((0, 0, 0, 0))
        stripe_color = (235, 225, 205, 70)
        for x in range(-tile_size, tile_size * 2, stripe_gap):
            pygame.draw.line(stripe, stripe_color, (x, 0), (x + tile_size, tile_size), 2)

        base = pygame.Surface((self.world.world_w, self.world.world_h), pygame.SRCALPHA)
        tile_fill(base, base.get_rect(), stripe)
        self._siege_stripe_base = base
        self._siege_stripe_base_key = key
        return base

    def _build_siege_overlay(self, sieged_set):
        if not sieged_set:
            return None

        mask = pygame.Surface((self.world.gw, self.world.gh), pygame.SRCALPHA)
        for y in range(self.world.gh):
            row = self.world.prov_id[y]
            for x in range(self.world.gw):
                pid = row[x]
                if pid >= 0 and pid in sieged_set:
                    mask.set_at((x, y), (255, 255, 255, 255))

        mask_big = pygame.transform.scale(mask, (self.world.world_w, self.world.world_h))
        overlay = self._get_siege_stripe_base().copy()
        overlay.blit(mask_big, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return overlay

    def _get_siege_overlay(self):
        sieged = self._get_all_sieged_provinces()
        if not sieged:
            self._siege_overlay = None
            self._siege_overlay_key = None
            return None, None

        key = tuple(sorted(sieged))
        if key == self._siege_overlay_key and self._siege_overlay is not None:
            return self._siege_overlay, key

        overlay = self._build_siege_overlay(sieged)
        if overlay is None:
            self._siege_overlay = None
            self._siege_overlay_key = None
            return None, None

        self._siege_overlay = overlay
        self._siege_overlay_key = key
        return overlay, key

    def _draw_army_stack(self, surface, map_rect, pos, raised, max_army, friendly=True, selected=False):
        if max_army <= 0:
            return
        ratio = 0.0 if max_army <= 0 else max(0.0, min(1.0, raised / max_army))
        sp = self.camera.world_to_screen(pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return

        # CK2-style stack icon: number + vertical morale/raise bar
        body_w, body_h = 64, 22
        bar_w = 7
        body_rect = pygame.Rect(x - body_w // 2, y - 30, body_w, body_h)
        body_bg = (30, 75, 35) if friendly else (90, 35, 35)
        pygame.draw.rect(surface, body_bg, body_rect, border_radius=3)
        pygame.draw.rect(surface, (8, 8, 10), body_rect, 1, border_radius=3)

        # right vertical bar (red background + green fill)
        bar_rect = pygame.Rect(body_rect.right - bar_w - 2, body_rect.top + 2, bar_w, body_rect.h - 4)
        pygame.draw.rect(surface, (130, 35, 35), bar_rect, border_radius=2)
        fill_h = int(bar_rect.h * ratio)
        if fill_h > 0:
            fill_rect = pygame.Rect(bar_rect.left, bar_rect.bottom - fill_h, bar_rect.w, fill_h)
            pygame.draw.rect(surface, (65, 150, 70), fill_rect, border_radius=2)
        pygame.draw.rect(surface, (0, 0, 0), bar_rect, 1, border_radius=2)

        # troop count
        raised_text = f"{int(raised):,}"
        label = FOOTER_FONT.render(raised_text, True, (235, 228, 210))
        label_rect = label.get_rect(center=(body_rect.centerx - bar_w // 2, body_rect.centery))
        surface.blit(label, label_rect)

        if selected:
            pygame.draw.rect(surface, (230, 210, 120), body_rect.inflate(6, 6), 2, border_radius=4)

    def _draw_army_muster_marker(self, surface, map_rect):
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            return
        if self.army_pos is None:
            return
        max_army = int(self.army.get("max", 0))
        raised = int(self.army.get("raised", 0))
        friendly = False
        if self.army_prov_id is not None and 0 <= self.army_prov_id < len(self.world.provinces):
            friendly = self.world.provinces[self.army_prov_id].realm_id == self.player_realm_id
        self._draw_army_stack(
            surface,
            map_rect,
            self.army_pos,
            raised,
            max_army,
            friendly=friendly,
            selected=self.army_selected,
        )

    def _draw_enemy_armies(self, surface, map_rect):
        if not self.enemy_armies:
            return
        for enemy in self.enemy_armies:
            army = enemy.get("army", {})
            raised = int(army.get("raised", 0))
            max_army = int(army.get("max", 0))
            if raised <= 0 or max_army <= 0:
                continue
            pid = enemy.get("prov_id")
            if pid is None or not (0 <= pid < len(self.world.provinces)):
                continue
            if not self._is_province_visible(pid):
                continue
            pos = enemy.get("pos")
            if pos is None:
                pos = self.world.provinces[pid].center
            self._draw_army_stack(surface, map_rect, pos, raised, max_army, friendly=False, selected=False)

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

    def _draw_siege_status(self, surface, map_rect):
        if not self._siege_state:
            return
        pid = self._siege_state.get("pid")
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return
        if not self._is_province_visible(pid):
            return

        prep_days = int(self._siege_state.get("prep_days", 1))
        assault_days = int(self._siege_state.get("assault_days", 1))
        stage = self._siege_state.get("stage", "prep")
        days = int(self._siege_state.get("days", 0))
        total_days = max(1, prep_days + assault_days)
        if stage == "prep":
            elapsed = max(0, min(days, prep_days))
            remaining = max(0, prep_days - days + assault_days)
            stage_label = "Prep"
        else:
            elapsed = prep_days + max(0, min(days, assault_days))
            remaining = max(0, assault_days - days)
            stage_label = "Siege"

        progress = max(0.0, min(1.0, elapsed / total_days))

        sp = self.camera.world_to_screen(self.world.provinces[pid].center, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return

        w, h = 110, 34
        panel = pygame.Rect(0, 0, w, h)
        panel.center = (x, y - 42)

        pygame.draw.rect(surface, (20, 18, 16), panel, border_radius=6)
        pygame.draw.rect(surface, (0, 0, 0), panel, 2, border_radius=6)

        bar_pad = 6
        bar_h = 6
        bar = pygame.Rect(panel.left + bar_pad, panel.bottom - bar_pad - bar_h, panel.w - bar_pad * 2, bar_h)
        pygame.draw.rect(surface, (70, 62, 50), bar, border_radius=3)
        fill_w = int(bar.w * progress)
        if fill_w > 0:
            fill = pygame.Rect(bar.left, bar.top, fill_w, bar.h)
            pygame.draw.rect(surface, (180, 120, 60), fill, border_radius=3)

        label = FOOTER_FONT.render(f"{stage_label} {remaining}d", True, (230, 220, 200))
        surface.blit(label, label.get_rect(center=(panel.centerx, panel.centery - 4)))

    def _is_province_visible(self, pid):
        vis = self.world.visibility_by_prov.get(pid, 0.45)
        if vis >= 0.78:
            return True
        return pid in getattr(self.world, "extra_visible_provs", set())

    def _army_icon_rect(self, map_rect):
        if self.army_pos is None:
            return None
        if self.army.get("raised", 0) <= 0 and not self.army_raising:
            return None
        sp = self.camera.world_to_screen(self.army_pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        return pygame.Rect(x - 32, y - 30, 64, 22)

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
        return False

    def _handle_army_move(self, screen_pos, map_rect):
        if not self.army_selected:
            return False
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
                "Pause, review your realm, or return to desktop.",
            ],
            [
                ("Resume", "accept", lambda: self.modal.close()),
                ("Save", "primary", lambda: self._handle_action("save_game")),
                ("Load", "secondary", lambda: self._handle_action("load_game")),
                ("Exit", "deny", lambda: self._exit_game()),
            ],
        )

    def _exit_game(self):
        self.running = False

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

    def _realm_building_effects(self, rid):
        effects = {
            "gold_upkeep": 0.0,
            "gold_rate_bonus": 0.0,
            "piety_rate_bonus": 0.0,
            "prestige_rate_bonus": 0.0,
            "levy_mult_bonus": 0.0,
            "stress_monthly_relief": 0.0,
        }
        for prov in self.world.provinces:
            if prov.realm_id != rid:
                continue
            for b in getattr(prov, "buildings", []):
                if b is None:
                    continue
                effects["gold_upkeep"] += building_gold_upkeep(b)
                effects["gold_rate_bonus"] += building_gold_rate_bonus(b)
                effects["piety_rate_bonus"] += building_piety_rate_bonus(b)
                effects["prestige_rate_bonus"] += building_prestige_rate_bonus(b)
                effects["levy_mult_bonus"] += building_levy_mult_bonus(b)
                effects["stress_monthly_relief"] += building_stress_monthly_relief(b)
        return effects

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
        bdef = BUILDINGS.get(building_id)
        if bdef is None:
            self.push_log("Unknown building type.")
            return
        if slot_idx is None:
            slot = next((idx for idx, entry in enumerate(prov.buildings) if entry is None), -1)
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
            slot = slot_idx
        build_cost = max(0, int(getattr(bdef, "build_cost_gold", 0)))
        if self.resources.get("gold", 0) < build_cost:
            self.push_log(f"Need {build_cost} gold to build {bdef.name}.")
            return
        prov.buildings[slot] = make_building(building_id, level=1)
        bname = bdef.name if bdef else building_id
        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - build_cost)
        self.push_log(
            f"{self.date}: Built {bname} in {prov.name} (slot {slot + 1}) "
            f"for {build_cost} gold."
        )
        self.food = self._compute_food_values()
        self._recompute_resource_rates()
        self._update_army_max()
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
        base_cost = max(0, int(getattr(bdef, "upgrade_cost_gold", 0)))
        upgrade_cost = int(round(base_cost * (1.0 + (0.55 * max(0, level - 1)))))
        if self.resources.get("gold", 0) < upgrade_cost:
            self.push_log(f"Need {upgrade_cost} gold to upgrade {bname}.")
            if isinstance(entry, dict):
                entry["level"] = level
            else:
                prov.buildings[slot_idx] = make_building(get_building_id(entry), level=level)
            return
        self.resources["gold"] = max(0, int(self.resources.get("gold", 0)) - upgrade_cost)
        self.push_log(
            f"{self.date}: Upgraded {bname} in {prov.name} (slot {slot_idx + 1}) "
            f"for {upgrade_cost} gold."
        )
        self.food = self._compute_food_values()
        self._recompute_resource_rates()
        self._update_army_max()
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
        self._recompute_resource_rates()
        self._update_army_max()
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
            self._open_load_game_modal()
            return
        if action == "menu_settings":
            self._open_settings_modal()
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
            self.right_panel_open = True
            self._right_panel_anim = 1.0
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
        if action == "npc_promote_relations":
            self._action_promote_relations()
            return
        if action == "npc_fabricate_claim":
            self._action_fabricate_claim()
            return
        if action == "npc_arrange_marriage":
            self._action_arrange_marriage()
            return
        if action == "npc_plot_murder":
            self._action_plot_murder()
            return
        if action == "npc_declare_war":
            target_rid = None
            if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                target_rid = self.selected_province.realm_id
            if target_rid is None:
                self.modal.show(
                    "No Target Selected",
                    [
                        "Select a foreign realm (click a province) before declaring war.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
            else:
                self._open_war_type_modal(target_rid)
            return
        if action == "open_war_overview":
            self._open_war_overview()
            return
        if action.startswith("war_details:"):
            try:
                war_id = int(action.split(":", 1)[1])
            except ValueError:
                self.push_log("Invalid war action.")
                return
            self._open_war_details(war_id)
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
        if action == "disband":
            action = "disband_army"
        if action == "disband_army":
            if self.army.get("raised", 0) <= 0:
                return
            if self.army_prov_id is None or not (0 <= self.army_prov_id < len(self.world.provinces)):
                return
            prov = self.world.provinces[self.army_prov_id]
            if prov.realm_id != self.player_realm_id:
                self.modal.show(
                    "Cannot Disband",
                    [
                        "You can only disband your army within your own realm.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
                return
            self.army["raised"] = 0
            self.army_raising = False
            self.army_selected = False
            self.army_route = []
            self.army_step_from = None
            self.army_step_to = None
            self.army_step_progress = 0.0
            self.army_pos = None
            self.army_prov_id = None
            self._update_fog_from_army()
            self.push_log("You disband the army.")
            return
        if action == "toggle_pause":
            self.toggle_pause()
            return
        elif action == "speed_1":
            self.set_speed(1)
            return
        elif action == "speed_2":
            self.set_speed(2)
            return
        elif action == "speed_3":
            self.set_speed(3)
            return
        elif action == "open_menu":
            self.open_menu()
            return
        elif action == "save_game":
            self._save_game_to_file(self.latest_save_path, autosave=False)
            return
        elif action == "load_game":
            self._open_load_game_modal()
            return
        elif action in ("realm", "view_realm"):
            self._open_realm_overview()
            return
        elif action == "ledger":
            self._open_ledger_overview()
            return
        elif action == "military":
            self._open_military_overview()
            return
        elif action == "set_rally":
            if self.selected_province is None or self.selected_province.realm_id != self.player_realm_id:
                self.modal.show(
                    "No Valid Rally Point",
                    [
                        "Select one of your own provinces to set a rally point.",
                    ],
                    [
                        ("OK", "accept", lambda: self.modal.close()),
                    ],
                )
            else:
                self._set_rally_point(self.selected_province.id, announce=True)
                self._open_military_overview()
            return
        elif action == "rally":
            self._rally_army_to_capital()
            return
        elif action == "decisions":
            self._open_decisions_modal()
            return
        elif action == "council":
            self._open_scheme_overview()
            return
        elif action == "court":
            self._open_scheme_overview()
            return
        elif action == "build_farm":
            self._build_selected_building("farm")
            return
        elif action.startswith("building_slot:"):
            parts = action.split(":")
            if len(parts) < 3:
                self.push_log("Invalid building action.")
                return
            try:
                slot_idx = int(parts[1])
            except ValueError:
                self.push_log("Invalid building slot action.")
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
            else:
                self.push_log(f"Unknown building action: {verb}")
            return

        self.push_log(f"Unknown UI action: {action}")

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
                self._update_war_tick()
                self._update_army_raising()
                self._update_army_morale_tick()
                self._update_siege_tick()
                self._update_army_movement()
                self._update_enemy_ai_tick()
                self._tick_politics_day()

                if self.date.day == 1:
                    self._apply_monthly_resource_rates()
                    if self._autosave_interval_months > 0 and ((self.date.month - 1) % self._autosave_interval_months == 0):
                        self._save_game_to_file(self.autosave_path, autosave=True)
                    if self.date.month == 1:
                        self._annual_dynasty_tick()

            self._time_accum -= whole

    def _recompute_resource_rates(self):
        effects = self._realm_building_effects(self.player_realm_id)
        stewardship_bonus = self._perk_level("stewardship") // 2
        if self.lifestyle_focus == "stewardship":
            stewardship_bonus += 1
        stress_penalty = 2 if self.stress >= 220 else (1 if self.stress >= 120 else 0)
        building_gold = int(round(float(effects.get("gold_rate_bonus", 0.0))))
        upkeep_penalty = int(round(float(effects.get("gold_upkeep", 0.0)) * 0.45))
        self.resources["gold_rate"] = 1 + stewardship_bonus + building_gold - stress_penalty - upkeep_penalty

        piety_rate = compute_piety_rate(self.character)[0]
        piety_rate += self._perk_level("learning") // 2
        if self.lifestyle_focus == "learning":
            piety_rate += 1
        piety_rate += int(round(float(effects.get("piety_rate_bonus", 0.0))))
        self.resources["piety_rate"] = int(piety_rate)

        prestige_rate = self._compute_prestige_rate(self.character)
        prestige_rate += int(round(float(effects.get("prestige_rate_bonus", 0.0))))
        self.resources["prestige_rate"] = int(prestige_rate)
        renown_rate = 1 + (self._realm_size(self.player_realm_id) // 3)
        renown_rate += len(self.alliances) // 2
        renown_rate += self._perk_level("diplomacy") // 4
        if self.wars:
            renown_rate += 1
        self.resources["renown_rate"] = int(max(0, renown_rate))

    def _apply_monthly_resource_rates(self):
        self._recompute_resource_rates()

        for res in ("gold", "piety", "prestige", "renown"):
            rate = self.resources.get(f"{res}_rate", 0)
            if rate == 0:
                continue
            self.resources[res] += rate

        # Opinions drift slowly toward neutral over time.
        for rid, opinion in list(self.realm_relations.items()):
            if opinion > 0:
                self.realm_relations[rid] = opinion - 1
            elif opinion < 0:
                self.realm_relations[rid] = opinion + 1

        self.dread = clamp(float(self.dread) - 3.5, 0.0, 100.0)
        monthly_stress_relief = -2.0 - (0.5 * self._perk_level("learning"))
        if self.lifestyle_focus == "learning":
            monthly_stress_relief -= 1.0
        effects = self._realm_building_effects(self.player_realm_id)
        monthly_stress_relief -= float(effects.get("stress_monthly_relief", 0.0))
        self._adjust_stress(monthly_stress_relief)

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
                        "wars": self.wars,
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
                        if self.mode == "game":
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
                                        if self._handle_army_click(event.pos, map_rect):
                                            self._mouse_down_in_map = False
                                            self._drag_started = False
                                            continue
                                        if not self._try_open_tower_event(event.pos):
                                            wp = self.camera.screen_to_world(event.pos, map_rect, use_target=False)
                                            prov = self.world.province_at_world(wp)
                                            if prov is not None:
                                                if self._handle_war_goal_click(prov):
                                                    self._mouse_down_in_map = False
                                                    self._drag_started = False
                                                    continue
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
                    elif event.button == 3:
                        if self.mode == "game" and not self.modal.open:
                            map_rect = self._get_map_rect()
                            if map_rect.collidepoint(event.pos) and not self._point_in_ui(event.pos):
                                self._handle_army_move(event.pos, map_rect)

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
                war_overlay, war_overlay_key = self._get_war_border_overlay()
                siege_overlay, siege_overlay_key = self._get_siege_overlay()
                overlays = []
                overlay_key = []
                if siege_overlay is not None:
                    overlays.append(siege_overlay)
                    overlay_key.append(("siege", siege_overlay_key))
                if war_overlay is not None:
                    overlays.append(war_overlay)
                    overlay_key.append(("war", war_overlay_key))
                if not overlays:
                    overlays = None
                    overlay_key = None
                else:
                    overlay_key = tuple(overlay_key)
                self.map_renderer.draw(self.screen, map_rect, overlays, overlay_key)
                self._draw_selected_province_highlight(self.screen, map_rect)
                self._draw_army_muster_marker(self.screen, map_rect)
                self._draw_enemy_armies(self.screen, map_rect)
                self._draw_army_route_arrow(self.screen, map_rect)
                self._draw_siege_status(self.screen, map_rect)

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
                    "realm_colors": self.world.realm_colors,
                    "player_realm_id": self.player_realm_id,
                    "population": self.population,
                    "army_raising": self.army_raising,
                    "food": self.food,
                    "threat": self.threat,
                    "building_menu_slot": self._building_menu_slot,
                    "wars": self.wars,
                    "stress": int(round(self.stress)),
                    "dread": int(round(self.dread)),
                    "lifestyle_focus": self.lifestyle_focus,
                    "lifestyle_perks": dict(self.lifestyle_perks),
                    "active_schemes": list(self.active_schemes),
                    "selected_realm_manpower": (
                        self._realm_total_manpower(self.selected_province.realm_id)
                        if self.selected_province is not None
                        else None
                    ),
                }

                clip_draw(self.screen, self.layout.top, lambda: clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state)))
                war_btns, war_rects = self.ui.draw_war_floating(self.screen, self.layout.top, state)
                clickables.extend(war_btns)
                self._war_float_rects = war_rects
                left_character = self.character
                left_realm_id = self.player_realm_id
                if self.selected_province is not None and self.selected_province.realm_id != self.player_realm_id:
                    rid = self.selected_province.realm_id
                    if 0 <= rid < len(self.world.realm_rulers):
                        left_character = self.world.realm_rulers[rid]
                        left_realm_id = rid
                left_state = dict(state)
                left_state["character"] = left_character
                left_state["character_realm_id"] = left_realm_id
                npc_target = self._get_npc_target()
                left_state["npc_target"] = npc_target
                left_state["npc_actions_enabled"] = True
                left_state["diplomacy"] = self._diplomacy_snapshot(npc_target.get("id")) if npc_target else None
                left_state["character_realm_manpower"] = self._realm_total_manpower(left_realm_id)

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
