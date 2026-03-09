import os

import pygame

from core.surfaces import tile_fill
from events import date_ordinal
from systems.traits import _stats_list_to_dict, apply_trait_effects, compute_piety_rate, normalize_traits
from ui.text import wrap_text
from ui.theme import BG_COLOR, FOOTER_FONT
from ui.utils import clip_draw


class MenuMixin:
    def _load_menu_background(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
        path = os.path.join(base_dir, "boreal_forest.png")
        if os.path.exists(path):
            return pygame.image.load(path).convert()
        return None
    def _load_storyteller_portraits(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "storytellers"))
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
    def _set_window_preset(self, mode):
        if mode == "desktop":
            self._apply_window_size_desktop()
        elif mode == "1280":
            self._apply_window_size((1280, 720), remember=True)
        elif mode == "1600":
            self._apply_window_size((1600, 900), remember=True)
        self._open_settings_modal()
    def _set_autosave_interval(self, months):
        months = int(months)
        self._autosave_interval_months = max(0, min(12, months))
        if self._autosave_interval_months == 0:
            self.push_log("Autosave disabled.")
        else:
            self.push_log(f"Autosave set to every {self._autosave_interval_months} month(s).")
        self._open_settings_modal()
    def _open_settings_modal(self):
        w, h = self.screen.get_size()
        if self._autosave_interval_months <= 0:
            autosave_line = "Autosave interval: Off."
        else:
            autosave_line = f"Autosave interval: every {self._autosave_interval_months} months."
        self.modal.show(
            "Settings",
            [
                f"Current window: {w}x{h}",
                "Choose a resolution preset for this session.",
                autosave_line,
            ],
            [
                ("1280x720", "primary", lambda: self._set_window_preset("1280")),
                ("1600x900", "secondary", lambda: self._set_window_preset("1600")),
                ("Autosave 1M", "secondary", lambda: self._set_autosave_interval(1)),
                ("Autosave 3M", "secondary", lambda: self._set_autosave_interval(3)),
                ("Autosave Off", "secondary", lambda: self._set_autosave_interval(0)),
                ("Close", "secondary", lambda: self.modal.close()),
            ],
        )
    def _perform_return_to_main_menu(self):
        self.modal.close()
        self.mode = "menu"
        self.speed_level = 0
        self.selected_province = None
        self.left_panel_open = False
        self.right_panel_open = False
        self._left_panel_anim = 0.0
        self._right_panel_anim = 0.0
        self._war_goal_selecting = False
        self._pending_war = None
        self._battle_state = None
        self._mark_progress_saved()
    def _return_to_main_menu(self):
        self._confirm_unsaved_progress("Leave Without Saving", "deny", self._perform_return_to_main_menu)
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
            lambda: self.ui.draw_left_panel(
                surface,
                self.layout.left,
                {
                    "character": ruler,
                    "npc_target": self._get_npc_target(self.realm_candidate_id),
                    "npc_actions_enabled": False,
                    "show_actions": False,
                    "character_realm_manpower": self._realm_total_manpower(self.realm_candidate_id),
                },
            ),
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
        self.resources["gold"] = 200
        self.resources["gold_rate"] = 1
        self.resources["piety"] = 1000
        self.resources["prestige"] = 350
        self.resources["renown"] = 120
        self.resources["renown_rate"] = 1

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
        self.resources["prestige_rate"] = self._compute_prestige_rate(self.character)

        self.population = self.world.total_population_for_realm(self.player_realm_id)
        self._baseline_population = max(1, self.population)
        self.food = self._compute_food_values()
        self.threat = self._compute_threat()
        self._update_army_max()
        self.army["raised"] = 0
        self.army["morale"] = 77
        self.army_raising = False
        self.army_selected = False
        self.army_route = []
        self.army_step_from = None
        self.army_step_to = None
        self.army_step_progress = 0.0
        self.army_pos = None
        self.army_prov_id = None
        self._init_enemy_armies()
        self.realm_relations = {}
        self.realm_claims = set()
        self.realm_truces = {}
        self.claim_fabrication_cooldowns = {}
        self.alliances = set()
        self.subjugation_cooldown_days = 0
        self.active_schemes = []
        self._next_scheme_id = 1
        self.hooks = {}
        self.lifestyle_focus = "stewardship"
        self.lifestyle_xp = {k: 0.0 for k in self.lifestyle_focuses}
        self.lifestyle_perks = {k: 0 for k in self.lifestyle_focuses}
        self._lifestyle_picker_index = self.lifestyle_focuses.index(self.lifestyle_focus)
        self.stress = 0.0
        self._stress_break_level = 0
        self.dread = 0.0
        self.decision_cooldowns = {}
        self._raid_cooldown_days = 0
        self._ai_war_cooldown_days = 0

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

        # Reset war state on new game start.
        self.wars = []
        self._war_next_id = 1
        self._war_focus_id = None
        self._war_border_overlay = None
        self._war_border_overlay_key = None

        # Reset siege state on new game start.
        self._siege_state = None
        self._battle_state = None
        self._siege_overlay = None
        self._siege_overlay_key = None
        self._siege_stripe_base = None
        self._siege_stripe_base_key = None
        self.last_played_realm_id = rid
        self._campaign_start_provinces = self._player_province_count()
        self._campaign_target_provinces = self._compute_campaign_target_provinces(self._campaign_start_provinces)
        self._insolvency_days = 0
        self._famine_days = 0
        self._crisis_days = 0
        self.campaign_result = None
        self._campaign_over_day = None
        self._recompute_resource_rates()
        self._mark_progress_unsaved()
    def _try_open_tower_event(self, screen_pos):
        if self._war_goal_selecting:
            return False
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
