# mapview2.py
import pygame
from typing import Optional, Tuple, Dict
from mapgen import ProvinceRaster

TERRAIN_COLORS = {
    "plains":   (88, 104, 66),
    "forest":   (48, 86, 56),
    "hills":    (120, 110, 72),
    "mountain": (120, 120, 132),
    "water":    (40, 70, 110),
}

def _mix(a, b, t: float):
    return (int(a[0]*(1-t) + b[0]*t), int(a[1]*(1-t) + b[1]*t), int(a[2]*(1-t) + b[2]*t))

class MapView2:
    def __init__(self, raster: ProvinceRaster, counties, player_realm):
        self.raster = raster
        self.counties = counties
        self.player_realm = player_realm

        self.selected_pid: Optional[int] = None
        self.hover_pid: Optional[int] = None

        self._realm_colors: Dict[int, Tuple[int,int,int]] = {}
        self._base_surface: Optional[pygame.Surface] = None
        self._border_surface: Optional[pygame.Surface] = None

        # render scaling
        self.scale = 4  # raster -> pixels scale

    def _realm_color(self, realm) -> Tuple[int,int,int]:
        k = id(realm)
        if k in self._realm_colors:
            return self._realm_colors[k]
        h = abs(hash(realm.name))
        col = (70 + (h % 160), 70 + ((h // 7) % 160), 70 + ((h // 13) % 160))
        self._realm_colors[k] = col
        return col

    def rebuild_surfaces(self):
        """
        Create:
        - base terrain+realm tint surface
        - border surface (transparent lines)
        """
        w, h = self.raster.w, self.raster.h
        surf = pygame.Surface((w, h))
        surf.lock()

        for y in range(h):
            row_i = y * w
            for x in range(w):
                pid = self.raster.ids[row_i + x]
                county = self.counties[pid]
                terrain = county.terrain
                base = TERRAIN_COLORS.get(terrain, TERRAIN_COLORS["plains"])

                # subtle realm tint overlay like CK3 map modes
                realm_col = self._realm_color(county.realm)
                t = 0.18 if county.realm is self.player_realm else 0.10
                col = _mix(base, realm_col, t)

                surf.set_at((x, y), col)

        surf.unlock()

        # upscale nicely (still pixel-based but looks like provinces)
        self._base_surface = pygame.transform.smoothscale(surf, (w*self.scale, h*self.scale))

        # Borders: draw lines where province changes
        borders = pygame.Surface((w*self.scale, h*self.scale), pygame.SRCALPHA)
        ids = self.raster.ids

        def pid_at(px, py):
            return ids[py*w + px]

        for y in range(h-1):
            for x in range(w-1):
                a = pid_at(x, y)
                r = pid_at(x+1, y)
                d = pid_at(x, y+1)
                if a != r:
                    pygame.draw.line(borders, (10,10,10,220), (x*self.scale, y*self.scale), (x*self.scale, (y+1)*self.scale), 2)
                if a != d:
                    pygame.draw.line(borders, (10,10,10,220), (x*self.scale, y*self.scale), ((x+1)*self.scale, y*self.scale), 2)

        self._border_surface = borders

    def province_at_screen(self, map_rect: pygame.Rect, mx: int, my: int) -> Optional[int]:
        if not map_rect.collidepoint(mx, my):
            return None
        rx = mx - map_rect.x
        ry = my - map_rect.y
        px = int(rx / self.scale)
        py = int(ry / self.scale)
        if not (0 <= px < self.raster.w and 0 <= py < self.raster.h):
            return None
        return self.raster.ids[py*self.raster.w + px]

    def handle_event(self, event, map_rect: pygame.Rect):
        if event.type == pygame.MOUSEMOTION:
            self.hover_pid = self.province_at_screen(map_rect, *event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pid = self.province_at_screen(map_rect, *event.pos)
            if pid is not None:
                self.selected_pid = pid

    def draw(self, screen: pygame.Surface, map_rect: pygame.Rect):
        if self._base_surface is None or self._border_surface is None:
            self.rebuild_surfaces()

        # Fit the map into map_rect while preserving aspect
        map_surf = self._base_surface
        bw, bh = map_surf.get_size()

        # center in rect
        dx = map_rect.x + (map_rect.w - bw)//2
        dy = map_rect.y + (map_rect.h - bh)//2

        screen.blit(map_surf, (dx, dy))
        screen.blit(self._border_surface, (dx, dy))

        # hover/selection highlight
        def draw_outline(pid, color, thickness):
            if pid is None:
                return
            # cheap highlight: draw a glow rectangle around mouse area (placeholder)
            # (If you want real province outline tracing, we can add it next.)
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(screen, color, (mx, my), 18, thickness)

        draw_outline(self.hover_pid, (255,255,255), 1)
        draw_outline(self.selected_pid, (255,220,120), 2)
