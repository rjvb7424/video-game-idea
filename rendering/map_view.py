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
from world.biomes import BIOME_DEFS, get_biome_tile_path, normalize_biome_key


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
        self._biome_tiles = self._load_biome_tiles()

    def _load_biome_tiles(self):
        tiles = {}
        for biome_key in BIOME_DEFS:
            path = get_biome_tile_path(biome_key)
            if not path:
                continue
            try:
                tiles[biome_key] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue
        return tiles

    @staticmethod
    def _biome_detail_alpha(visibility):
        if visibility >= 0.999:
            return 228
        if visibility >= 0.78:
            return 156
        return 72

    @staticmethod
    def _make_tiled_patch(tile, size, world_offset):
        patch = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()
        tw, th = tile.get_size()
        start_x = -(int(world_offset[0]) % tw)
        start_y = -(int(world_offset[1]) % th)
        for y in range(start_y, size[1], th):
            for x in range(start_x, size[0], tw):
                patch.blit(tile, (x, y))
        return patch

    def _build_hd_biome_masks(self, inter):
        masks = {
            biome_key: pygame.Surface(inter.size, pygame.SRCALPHA).convert_alpha()
            for biome_key in self._biome_tiles
        }
        if not masks:
            return masks

        cs = max(1, int(self.world.cell_scale))
        gx0 = max(0, inter.left // cs)
        gy0 = max(0, inter.top // cs)
        gx1 = min(self.world.gw, (inter.right + cs - 1) // cs)
        gy1 = min(self.world.gh, (inter.bottom + cs - 1) // cs)

        for gy in range(gy0, gy1):
            wy0 = gy * cs
            py0 = max(0, wy0 - inter.top)
            py1 = min(inter.h, (gy + 1) * cs - inter.top)
            if py1 <= py0:
                continue

            row = self.world.prov_id[gy]
            for gx in range(gx0, gx1):
                pid = row[gx]
                if pid < 0:
                    continue

                prov = self.world.provinces[pid]
                biome_key = normalize_biome_key(prov.biome)
                mask = masks.get(biome_key)
                if mask is None:
                    continue

                wx0 = gx * cs
                px0 = max(0, wx0 - inter.left)
                px1 = min(inter.w, (gx + 1) * cs - inter.left)
                if px1 <= px0:
                    continue

                vis = self.world.visibility_by_prov.get(pid, 0.45)
                alpha = self._biome_detail_alpha(vis)
                mask.fill((255, 255, 255, alpha), pygame.Rect(px0, py0, px1 - px0, py1 - py0))

        return masks

    def _draw_hd_biome_overlay(self, view, inter, scaled_size, dest):
        if inter.w <= 0 or inter.h <= 0 or not self._biome_tiles:
            return

        masks = self._build_hd_biome_masks(inter)
        scaled_w, scaled_h = scaled_size
        dx, dy = dest

        for biome_key, mask in masks.items():
            if mask.get_bounding_rect().w <= 0 or mask.get_bounding_rect().h <= 0:
                continue

            tile = self._biome_tiles[biome_key]
            patch = self._make_tiled_patch(tile, inter.size, inter.topleft)
            patch.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            if patch.get_size() != (scaled_w, scaled_h):
                patch = pygame.transform.smoothscale(patch, (scaled_w, scaled_h))
            view.blit(patch, (dx, dy))

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
        banner = self._banner_painter.get_banner(dynasty_key, realm_color, size)
        if banner is None:
            fallback = pygame.Surface(size, pygame.SRCALPHA)
            fallback.fill((220, 210, 190))
            banner = fallback

        w, h = banner.get_size()
        rect = banner.get_rect(center=(int(center[0]), int(center[1])))
        shadow = rect.move(2, 2)
        pygame.draw.rect(surf, (0, 0, 0, int(alpha * 0.25)), shadow, border_radius=8)

        banner_surf = banner.copy()
        notch = max(6, int(h * 0.22))
        shape = pygame.Surface((w, h), pygame.SRCALPHA)
        pts = [(0, 0), (w, 0), (w, h - notch), (w // 2, h), (0, h - notch)]
        pygame.draw.polygon(shape, (255, 255, 255, 255), pts)
        banner_surf.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        banner_surf.set_alpha(alpha)
        surf.blit(banner_surf, rect.topleft)

        if realm_color is not None:
            outline = self._banner_painter.shade_color(realm_color, -0.6)
        else:
            outline = (20, 20, 20)
        outline_alpha = int(alpha * 0.85)
        outline_pts = [(rect.left + x, rect.top + y) for x, y in pts]
        pygame.draw.polygon(surf, (*outline, outline_alpha), outline_pts, 1)

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
        name_w = text_surf.get_width() + pad_x * 2
        name_h = text_surf.get_height() + pad_y * 2

        flag_h = max(26, int(name_h * 2.0))
        flag_w = max(18, int(flag_h * 0.55))
        gap = 6

        flag_center = (center[0], center[1] + 8)
        name_center = (center[0], flag_center[1] + flag_h // 2 + gap + name_h // 2)

        self._draw_flag_banner(surf, flag_center, dynasty_key, base, (flag_w, flag_h), alpha=a)
        self._draw_nameplate(surf, name_center, label, alpha=a)

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
            subs = self.world.surface.subsurface(inter)

            # Scale to screen portion
            scaled_w = max(1, int(round(inter.w * z)))
            scaled_h = max(1, int(round(inter.h * z)))
            dx = int(round((inter.left - vrect.left) * z))
            dy = int(round((inter.top - vrect.top) * z))
            direct_blit = inter.size == map_rect.size and abs(z - 1.0) < 0.001

            if direct_blit:
                view.blit(subs, (0, 0))
            else:
                scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))
                view.blit(scaled, (dx, dy))
            self._draw_hd_biome_overlay(view, inter, (scaled_w, scaled_h), (dx, dy))

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

        # Optional world-space overlays (e.g. war borders)
        if overlay_surfaces and inter.w > 0 and inter.h > 0:
            for layer in overlay_surfaces:
                if layer is None:
                    continue
                subs = layer.subsurface(inter)
                if direct_blit:
                    view.blit(subs, (0, 0))
                else:
                    scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))
                    view.blit(scaled, (dx, dy))

        # blit the final view
        surface.blit(view, map_rect.topleft)
