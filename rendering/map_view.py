import pygame

from core.geometry import shield_points
from core.surfaces import draw_drop_shadow, draw_vignette
from ui.theme import (
    BEVEL_DARK,
    BEVEL_LIGHT,
    FOOTER_FONT,
    PANEL_OUTER,
)
from world.map import SEA_DEEP


class MapRenderer:
    def __init__(self, world, camera):
        self.world = world
        self.camera = camera
        self._cached_final = None
        self._overlay_surface = None
        self._cached_size = None
        self._cache_key = None
        self._last_viewport = None

    def _draw_minimal_province_label(self, surf, center, prov, vis):
        a = 220 if vis > 0.95 else 180 if vis > 0.80 else 150

        text = prov.name
        main = FOOTER_FONT.render(text, True, (235, 228, 210))
        shadow = FOOTER_FONT.render(text, True, (0, 0, 0))

        main.set_alpha(a)
        shadow.set_alpha(int(a * 0.75))

        r = main.get_rect(center=(int(center[0]), int(center[1])))

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            surf.blit(shadow, (r.x + dx, r.y + dy))

        surf.blit(main, r)

    def _draw_shield_icon(self, surf, center, base_rgb, alpha=220):
        cx, cy = center
        pts = shield_points((int(cx), int(cy)), 26)

        # shield fill
        pygame.draw.polygon(surf, (base_rgb[0], base_rgb[1], base_rgb[2], alpha), pts)

        # simple highlight stripe
        pygame.draw.line(surf, (235, 228, 210, int(alpha * 0.85)),
                         (int(cx) - 7, int(cy) - 16), (int(cx) - 7, int(cy) + 16), 3)
        pygame.draw.line(surf, (235, 228, 210, int(alpha * 0.85)),
                         (int(cx) + 7, int(cy) - 16), (int(cx) + 7, int(cy) + 16), 3)

        # outline
        pygame.draw.polygon(surf, (10, 10, 10, int(alpha * 0.9)), pts, 1)

    def _draw_banner_with_text(
        self,
        surf,
        center,
        text,
        alpha=220,
        text_color=(20, 20, 20),
        banner_fill=(220, 210, 190),
        border_color=(40, 36, 32),
        outline=False,
    ):
        # text surface
        text_surf = FOOTER_FONT.render(text, True, text_color)
        pad_x, pad_y = 14, 6

        w = text_surf.get_width() + pad_x * 2
        h = text_surf.get_height() + pad_y * 2

        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(center[0]), int(center[1]))

        # shadow
        shadow = rect.move(2, 2)
        pygame.draw.rect(surf, (0, 0, 0, int(alpha * 0.35)), shadow, border_radius=8)

        # banner fill
        pygame.draw.rect(surf, (banner_fill[0], banner_fill[1], banner_fill[2], alpha), rect, border_radius=8)

        # banner border
        pygame.draw.rect(surf, (border_color[0], border_color[1], border_color[2], int(alpha * 0.9)), rect, width=1, border_radius=8)

        tr = text_surf.get_rect(center=rect.center)
        shadow_text = FOOTER_FONT.render(text, True, (0, 0, 0))
        shadow_text.set_alpha(int(alpha * 0.35))
        surf.blit(shadow_text, (tr.x + 1, tr.y + 1))

        if outline:
            outline_surf = FOOTER_FONT.render(text, True, (0, 0, 0))
            outline_surf.set_alpha(int(alpha * 0.45))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                surf.blit(outline_surf, (tr.x + dx, tr.y + dy))

        # text
        text_surf.set_alpha(alpha)
        surf.blit(text_surf, tr)

    def _draw_province_label_marker(self, surf, center, prov, vis):
        base = self.world.realm_colors[prov.realm_id]
        a = 235 if vis > 0.95 else 190

        # coat of arms (back)
        shield_center = (center[0], center[1] - 10)
        self._draw_shield_icon(surf, shield_center, base, alpha=int(a * 0.95))

        # gold text ONLY for the player's capital
        is_player_capital = (prov.id == getattr(self.world, "player_capital_pid", -1))
        gold = (230, 195, 85)
        black = (20, 20, 20)
        banner_fill = (200, 185, 155) if is_player_capital else (220, 210, 190)
        border_color = (70, 60, 45) if is_player_capital else (40, 36, 32)

        banner_center = (center[0], center[1] + 14)
        self._draw_banner_with_text(
            surf,
            banner_center,
            prov.name,
            alpha=a,
            text_color=(gold if is_player_capital else black),
            banner_fill=banner_fill,
            border_color=border_color,
            outline=is_player_capital,
        )

    def _draw_tower_marker(self, surf, center, show_text=True):
        x, y = int(center[0]), int(center[1])

        # tower body
        body = pygame.Rect(x - 6, y - 18, 12, 20)
        pygame.draw.rect(surf, (210, 200, 180, 230), body, border_radius=2)
        pygame.draw.rect(surf, (20, 18, 16, 220), body, 1, border_radius=2)

        # spire
        spire = [(x, y - 28), (x - 6, y - 18), (x + 6, y - 18)]
        pygame.draw.polygon(surf, (225, 215, 195, 235), spire)
        pygame.draw.polygon(surf, (20, 18, 16, 210), spire, 1)

        if show_text:
            label = "Tower of Heaven"
            text = FOOTER_FONT.render(label, True, (240, 220, 150))
            shadow = FOOTER_FONT.render(label, True, (0, 0, 0))
            tr = text.get_rect(midtop=(x, y + 8))
            surf.blit(shadow, (tr.x + 1, tr.y + 1))
            surf.blit(text, tr)

    def draw(self, surface, map_rect):
        if self._cached_size != map_rect.size:
            self._cached_size = map_rect.size
            self._cached_final = pygame.Surface(map_rect.size).convert()
            self._overlay_surface = pygame.Surface(map_rect.size, pygame.SRCALPHA).convert_alpha()
            self._cache_key = None

        # Map frame
        frame_rect = map_rect.inflate(12, 12)
        draw_drop_shadow(surface, frame_rect, strength=140, inflate=8, radius=12)
        pygame.draw.rect(surface, PANEL_OUTER, frame_rect, border_radius=12)
        pygame.draw.rect(surface, (0, 0, 0), frame_rect, 2, border_radius=12)
        pygame.draw.line(surface, BEVEL_LIGHT, (frame_rect.left + 2, frame_rect.top + 2), (frame_rect.right - 3, frame_rect.top + 2))
        pygame.draw.line(surface, BEVEL_LIGHT, (frame_rect.left + 2, frame_rect.top + 2), (frame_rect.left + 2, frame_rect.bottom - 3))
        pygame.draw.line(surface, BEVEL_DARK, (frame_rect.left + 2, frame_rect.bottom - 3), (frame_rect.right - 3, frame_rect.bottom - 3))
        pygame.draw.line(surface, BEVEL_DARK, (frame_rect.right - 3, frame_rect.top + 2), (frame_rect.right - 3, frame_rect.bottom - 3))

        # View render
        view = self._cached_final

        if self._last_viewport != map_rect.size:
            self.camera.set_viewport(map_rect.size)
            self._last_viewport = map_rect.size
        vrect = self.camera.view_rect(use_target=False)

        world_rect = pygame.Rect(0, 0, self.world.world_w, self.world.world_h)
        inter = vrect.clip(world_rect)

        z = self.camera.zoom
        show_minimal = z >= 0.75
        render_version = getattr(self.world, "render_version", 0)
        cache_key = (
            map_rect.size,
            vrect.x, vrect.y, vrect.w, vrect.h,
            round(z, 3),
            render_version,
            show_minimal,
        )
        if cache_key == self._cache_key:
            surface.blit(view, map_rect.topleft)
            return
        self._cache_key = cache_key

        view.fill(SEA_DEEP)

        if inter.w > 0 and inter.h > 0:
            subs = self.world.surface.subsurface(inter)

            # Scale to screen portion
            scaled_w = max(1, int(round(inter.w * z)))
            scaled_h = max(1, int(round(inter.h * z)))

            if inter.size == map_rect.size and abs(z - 1.0) < 0.001:
                view.blit(subs, (0, 0))
            else:
                if z > 1.25:
                    scaled = pygame.transform.scale(subs, (scaled_w, scaled_h))
                else:
                    scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))
                dx = int(round((inter.left - vrect.left) * z))
                dy = int(round((inter.top - vrect.top) * z))
                view.blit(scaled, (dx, dy))

        # Subtle map overlay/vignette
        draw_vignette(view, view.get_rect(), strength=85)

        # Screen-space overlays (crisp at any zoom)
        overlay = self._overlay_surface
        overlay.fill((0, 0, 0, 0))

        capital_set = set(getattr(self.world, "capital_label_items", []))
        minimal_set = set(getattr(self.world, "minimal_label_items", []))

        draw_set = set(capital_set)
        if show_minimal:
            draw_set |= minimal_set

        tower_pid = getattr(self.world, "tower_pid", -1)
        if tower_pid in draw_set:
            draw_set.remove(tower_pid)

        for pid in sorted(draw_set):
            prov = self.world.provinces[pid]
            vis = self.world.visibility_by_prov.get(pid, 0.45)

            sp = self.camera.world_to_screen(prov.center, map_rect, use_target=False)
            lx = int(sp.x - map_rect.left)
            ly = int(sp.y - map_rect.top)

            if not (0 <= lx < map_rect.w and 0 <= ly < map_rect.h):
                continue

            if pid in capital_set:
                self._draw_province_label_marker(overlay, (lx, ly), prov, vis)
            else:
                self._draw_minimal_province_label(overlay, (lx, ly), prov, vis)

        # Special landmark marker (always visible, even under fog)
        if 0 <= tower_pid < len(self.world.provinces):
            tprov = self.world.provinces[tower_pid]
            sp = self.camera.world_to_screen(tprov.center, map_rect, use_target=False)
            tx = int(sp.x - map_rect.left)
            ty = int(sp.y - map_rect.top)
            if 0 <= tx < map_rect.w and 0 <= ty < map_rect.h:
                self._draw_tower_marker(overlay, (tx, ty), show_text=True)

        view.blit(overlay, (0, 0))

        # blit the final view
        surface.blit(view, map_rect.topleft)
