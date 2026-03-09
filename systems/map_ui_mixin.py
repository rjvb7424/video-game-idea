import math

import pygame

from core.surfaces import tile_fill
from ui.theme import FOOTER_FONT


class MapUIMixin:
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

    def _draw_army_stack(self, surface, map_rect, pos, raised, max_army, friendly=True, selected=False, marshal=None):
        if max_army <= 0:
            return
        ratio = 0.0 if max_army <= 0 else max(0.0, min(1.0, raised / max_army))
        sp = self.camera.world_to_screen(pos, map_rect, use_target=False)
        x, y = int(sp.x), int(sp.y)
        if not map_rect.collidepoint(x, y):
            return

        body_w, body_h = 80, 24
        bar_w = 7
        body_rect = pygame.Rect(x - body_w // 2, y - 30, body_w, body_h)
        body_bg = (30, 75, 35) if friendly else (90, 35, 35)
        pygame.draw.rect(surface, body_bg, body_rect, border_radius=3)
        pygame.draw.rect(surface, (8, 8, 10), body_rect, 1, border_radius=3)

        bar_rect = pygame.Rect(body_rect.right - bar_w - 2, body_rect.top + 2, bar_w, body_rect.h - 4)
        pygame.draw.rect(surface, (130, 35, 35), bar_rect, border_radius=2)
        fill_h = int(bar_rect.h * ratio)
        if fill_h > 0:
            fill_rect = pygame.Rect(bar_rect.left, bar_rect.bottom - fill_h, bar_rect.w, fill_h)
            pygame.draw.rect(surface, (65, 150, 70), fill_rect, border_radius=2)
        pygame.draw.rect(surface, (0, 0, 0), bar_rect, 1, border_radius=2)

        label_x = body_rect.centerx - bar_w // 2
        if marshal is not None:
            marshal_label = FOOTER_FONT.render(f"M{max(0, int(marshal))}", True, (242, 225, 180))
            marshal_rect = marshal_label.get_rect(midleft=(body_rect.left + 6, body_rect.centery))
            surface.blit(marshal_label, marshal_rect)
            label_x = body_rect.centerx + 8

        raised_text = f"{int(raised):,}"
        label = FOOTER_FONT.render(raised_text, True, (235, 228, 210))
        label_rect = label.get_rect(center=(label_x, body_rect.centery))
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
        marshal = self._realm_marshal_value(self.player_realm_id, default=8)
        self._draw_army_stack(
            surface,
            map_rect,
            self.army_pos,
            raised,
            max_army,
            friendly=True,
            selected=self.army_selected,
            marshal=marshal,
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
            marshal = self._realm_marshal_value(enemy.get("realm_id"), default=8)
            self._draw_army_stack(
                surface,
                map_rect,
                pos,
                raised,
                max_army,
                friendly=False,
                selected=False,
                marshal=marshal,
            )

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
            (
                int(self.camera.world_to_screen(p, map_rect, use_target=False).x),
                int(self.camera.world_to_screen(p, map_rect, use_target=False).y),
            )
            for p in points_world
        ]

        pygame.draw.lines(surface, (230, 230, 230), False, points, 3)
        draw_arrow_head(points[-2], points[-1], (230, 230, 230), width=3)

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

    def _draw_battle_status(self, surface, map_rect):
        if not self._battle_state:
            return
        pid = self._battle_state.get("pid")
        if pid is None or not (0 <= pid < len(self.world.provinces)):
            return
        if not self._is_province_visible(pid):
            return

        prep_days = int(self._battle_state.get("prep_days", 1))
        assault_days = int(self._battle_state.get("assault_days", 1))
        stage = self._battle_state.get("stage", "prep")
        days = int(self._battle_state.get("days", 0))
        total_days = max(1, prep_days + assault_days)
        if stage == "prep":
            elapsed = max(0, min(days, prep_days))
            remaining = max(0, prep_days - days + assault_days)
            stage_label = "Prep"
        else:
            elapsed = prep_days + max(0, min(days, assault_days))
            remaining = max(0, assault_days - days)
            stage_label = "Battle"

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
        return pygame.Rect(x - 40, y - 30, 80, 24)

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
            self._mark_progress_unsaved()
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
        self._mark_progress_unsaved()
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

    def _update_right_panel_anim(self, dt):
        should_show = self.mode == "game" and self.selected_province is not None and self.right_panel_open
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
