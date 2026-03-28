import math

import pygame

from core.geometry import shield_points
from core.surfaces import draw_drop_shadow, draw_vignette
from ui.manager import BannerPainter
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
        self._banner_painter = BannerPainter()

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

    def _draw_flag_banner(
        self,
        surf,
        center,
        dynasty_key,
        realm_color,
        size,
        alpha=220,
    ):
        """Capital banner: tall rectangle with swallowtail (two triangular tails) at the bottom."""
        banner = self._banner_painter.get_banner(dynasty_key, realm_color, size)
        if banner is None:
            fallback = pygame.Surface(size, pygame.SRCALPHA)
            fallback.fill((220, 210, 190))
            banner = fallback

        w, h = banner.get_size()
        rect = banner.get_rect(center=(int(center[0]), int(center[1])))

        split_y = int(h * 0.62)
        notch_y = split_y + int((h - split_y) * 0.38)
        l_tip_x = int(w * 0.22)
        r_tip_x = int(w * 0.78)

        # swallowtail shape in local coords
        local_pts = [
            (0, 0),
            (w, 0),
            (w, split_y),
            (r_tip_x, h),
            (w // 2, notch_y),
            (l_tip_x, h),
            (0, split_y),
        ]

        # drop shadow
        shadow_pts = [(rect.x + x + 2, rect.y + y + 2) for x, y in local_pts]
        pygame.draw.polygon(surf, (0, 0, 0, int(alpha * 0.28)), shadow_pts)

        # mask banner texture into swallowtail
        banner_surf = banner.copy()
        shape = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.polygon(shape, (255, 255, 255, 255), local_pts)
        banner_surf.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        banner_surf.set_alpha(alpha)
        surf.blit(banner_surf, rect.topleft)

        # outline
        world_pts = [(rect.x + x, rect.y + y) for x, y in local_pts]
        pygame.draw.polygon(surf, (20, 16, 10, int(alpha * 0.85)), world_pts, 1)

    def _draw_nameplate(
        self,
        surf,
        center,
        text,
        alpha=220,
    ):
        text_surf = FOOTER_FONT.render(text, True, (0, 0, 0))
        pad_x, pad_y = 12, 5
        w = text_surf.get_width() + pad_x * 2
        h = text_surf.get_height() + pad_y * 2
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(center[0]), int(center[1]))

        shadow = rect.move(2, 2)
        pygame.draw.rect(surf, (0, 0, 0, int(alpha * 0.25)), shadow, border_radius=6)
        pygame.draw.rect(surf, (255, 255, 255, alpha), rect, border_radius=6)
        pygame.draw.rect(surf, (0, 0, 0, int(alpha * 0.9)), rect, 1, border_radius=6)

        text_surf.set_alpha(alpha)
        surf.blit(text_surf, text_surf.get_rect(center=rect.center))
        return rect.size

    def _draw_province_label_marker(self, surf, center, prov, vis):
        base = self.world.realm_colors[prov.realm_id]
        a = 235 if vis > 0.95 else 190

        rulers = getattr(self.world, "realm_rulers", None)
        character = None
        if isinstance(rulers, (list, tuple)) and 0 <= prov.realm_id < len(rulers):
            character = rulers[prov.realm_id]
        dynasty_key = BannerPainter.dynasty_key(character)

        label = prov.name
        pad_x, pad_y = 12, 5
        text_surf = FOOTER_FONT.render(label, True, (0, 0, 0))
        name_h = text_surf.get_height() + pad_y * 2

        flag_h = max(40, int(name_h * 2.6))
        flag_w = max(22, int(flag_h * 0.58))
        gap = 5

        flag_center = (center[0], center[1] + 4)
        # bottom of banner = flag_center_y + flag_h/2, but swallowtail tips go to flag_h below rect top
        banner_bottom = int(flag_center[1]) + flag_h // 2
        name_center = (center[0], banner_bottom + gap + name_h // 2)

        self._draw_flag_banner(surf, flag_center, dynasty_key, base, (flag_w, flag_h), alpha=a)
        self._draw_nameplate(surf, name_center, label, alpha=a)

    def _draw_minor_banner(self, surf, center, name, alpha=220):
        """Minor landmark banner: square shape with a single small point at the bottom + white nameplate."""
        cx, cy = int(center[0]), int(center[1])

        bw, bh = 34, 34   # square
        tip   = 10         # single small point at bottom

        fill      = (195, 158, 55, alpha)
        dark_line = (80, 58, 12, int(alpha * 0.9))
        light     = (240, 225, 180, int(alpha * 0.88))

        top_y = cy - bh // 2

        # swallowtail-lite shape: square top, single small V at bottom
        pts = [
            (cx - bw // 2, top_y),
            (cx + bw // 2, top_y),
            (cx + bw // 2, top_y + bh),
            (cx,           top_y + bh + tip),
            (cx - bw // 2, top_y + bh),
        ]

        # shadow
        shadow_pts = [(x + 2, y + 2) for x, y in pts]
        pygame.draw.polygon(surf, (0, 0, 0, int(alpha * 0.25)), shadow_pts)

        pygame.draw.polygon(surf, fill, pts)
        pygame.draw.polygon(surf, dark_line, pts, 1)

        # simple cross in centre
        cross_cx, cross_cy = cx, top_y + bh // 2
        arm = max(7, bw // 4)
        pygame.draw.line(surf, light, (cross_cx - arm, cross_cy), (cross_cx + arm, cross_cy), 2)
        pygame.draw.line(surf, light, (cross_cx, cross_cy - arm), (cross_cx, cross_cy + arm), 2)

        # white nameplate below
        name_h = FOOTER_FONT.get_height()
        pad_y  = 5
        name_center_y = top_y + bh + tip + pad_y + (name_h + pad_y * 2) // 2
        self._draw_nameplate(surf, (cx, name_center_y), name, alpha=alpha)

    def _draw_tower_marker(self, surf, center, show_text=True):
        self._draw_minor_banner(surf, center, "Tower of Heaven", alpha=225)

    def draw(self, surface, map_rect, overlay_surfaces=None, overlay_key=None):
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
        render_scale = max(1, int(getattr(self.world, "render_scale", 1)))

        z = self.camera.zoom
        show_minimal = z >= 0.75
        render_version = getattr(self.world, "render_version", 0)
        if overlay_surfaces is None:
            overlay_surfaces = []
        if overlay_key is None and overlay_surfaces:
            overlay_key = tuple(id(s) for s in overlay_surfaces)
        elif overlay_key is not None and not isinstance(overlay_key, (tuple, int, float, str)):
            try:
                overlay_key = tuple(overlay_key)
            except TypeError:
                overlay_key = str(overlay_key)

        cache_key = (
            map_rect.size,
            vrect.x, vrect.y, vrect.w, vrect.h,
            round(z, 3),
            render_version,
            show_minimal,
            overlay_key,
        )
        if cache_key == self._cache_key:
            surface.blit(view, map_rect.topleft)
            return
        self._cache_key = cache_key

        view.fill(SEA_DEEP)

        if inter.w > 0 and inter.h > 0:
            render_rect = pygame.Rect(
                inter.x * render_scale,
                inter.y * render_scale,
                inter.w * render_scale,
                inter.h * render_scale,
            )
            subs = self.world.surface.subsurface(render_rect)

            # Scale to screen portion
            scaled_w = max(1, int(round(inter.w * z)))
            scaled_h = max(1, int(round(inter.h * z)))
            dx = int(round((inter.left - vrect.left) * z))
            dy = int(round((inter.top - vrect.top) * z))
            direct_blit = (
                render_scale == 1
                and inter.size == map_rect.size
                and abs(z - 1.0) < 0.001
            )

            if direct_blit:
                view.blit(subs, (0, 0))
            else:
                scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))
                view.blit(scaled, (dx, dy))

        # Fog of war overlay (world-space, blitted before screen labels)
        fog_surf = getattr(self.world, "fog_surface", None)
        if fog_surf is not None and inter.w > 0 and inter.h > 0:
            # fog_surface is at world resolution (world_w × world_h), no render_scale factor
            fog_rect = pygame.Rect(inter.x, inter.y, inter.w, inter.h).clip(fog_surf.get_rect())
            if fog_rect.w > 0 and fog_rect.h > 0:
                fog_sub = fog_surf.subsurface(fog_rect)
                if direct_blit and fog_rect.size == map_rect.size:
                    view.blit(fog_sub, (dx, dy))
                else:
                    scaled_fog = pygame.transform.smoothscale(fog_sub, (scaled_w, scaled_h))
                    view.blit(scaled_fog, (dx, dy))

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

        # Optional world-space overlays (e.g. war borders)
        if overlay_surfaces and inter.w > 0 and inter.h > 0:
            for layer in overlay_surfaces:
                if layer is None:
                    continue
                subs = layer.subsurface(render_rect)
                if direct_blit:
                    view.blit(subs, (0, 0))
                else:
                    scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))
                    view.blit(scaled, (dx, dy))

        # blit the final view
        surface.blit(view, map_rect.topleft)
