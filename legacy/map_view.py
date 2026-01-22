# map_view.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Optional

from domain import County, Realm
from config import (
    BIOME_COLORS, RIVER_COLOR,
    FOG_UNDISCOVERED, FOG_DISCOVERED,
    BORDER_THICK, BORDER_THIN,
    COUNTY_BORDER_SELECTED,
)

@dataclass
class MapSelection:
    county: Optional[County] = None
    hover: Optional[County] = None

class MapView:
    def __init__(self, counties: list[County], grid_size: tuple[int, int], player_realm: Realm, river_points: list[tuple[int,int]]):
        self.counties = counties
        self.grid_w, self.grid_h = grid_size
        self.player_realm = player_realm
        self.river_points = river_points
        self.selection = MapSelection()

        # stable realm colors
        self._realm_colors: dict[int, tuple[int, int, int]] = {}
        # cache irregular polygons per cell size
        self._poly_cache: dict[tuple[int,int,int,int], list[tuple[int,int]]] = {}

    def _color_for_realm(self, realm: Realm) -> tuple[int,int,int]:
        key = id(realm)
        if key in self._realm_colors:
            return self._realm_colors[key]
        h = abs(hash(realm.name))
        r = 80 + (h % 130)
        g = 80 + ((h // 7) % 130)
        b = 80 + ((h // 13) % 130)
        self._realm_colors[key] = (r, g, b)
        return (r, g, b)

    def _dull(self, col: tuple[int,int,int], factor: float) -> tuple[int,int,int]:
        # factor < 1 => duller/darker
        return (int(col[0]*factor), int(col[1]*factor), int(col[2]*factor))

    def _county_index(self) -> dict[tuple[int,int], County]:
        return {(c.grid_x, c.grid_y): c for c in self.counties}

    def _cell_rect(self, map_rect: pygame.Rect, gx: int, gy: int) -> pygame.Rect:
        cell_w = map_rect.w / self.grid_w
        cell_h = map_rect.h / self.grid_h
        x = map_rect.x + int(gx * cell_w)
        y = map_rect.y + int(gy * cell_h)
        return pygame.Rect(x, y, int(cell_w)+1, int(cell_h)+1)

    def _irregular_poly(self, rect: pygame.Rect, gx: int, gy: int) -> list[tuple[int,int]]:
        """
        Creates a jittered quad-ish polygon so borders don't look like a grid.
        Cached per (rect.w, rect.h, gx, gy).
        """
        key = (rect.w, rect.h, gx, gy)
        if key in self._poly_cache:
            return self._poly_cache[key]

        # deterministic jitter based on cell coords
        seed = (gx * 73856093) ^ (gy * 19349663) ^ rect.w ^ (rect.h << 1)
        rng = (seed & 0xFFFFFFFF)

        def j(v, amt):
            nonlocal rng
            rng = (1103515245 * rng + 12345) & 0x7FFFFFFF
            return v + int((rng % (amt*2+1)) - amt)

        pad = 2
        x0, y0 = rect.x + pad, rect.y + pad
        x1, y1 = rect.right - pad, rect.bottom - pad

        amt = max(2, min(10, rect.w // 10, rect.h // 10))

        pts = [
            (j(x0, amt), j(y0, amt)),
            (j(x1, amt), j(y0, amt)),
            (j(x1, amt), j(y1, amt)),
            (j(x0, amt), j(y1, amt)),
        ]
        self._poly_cache[key] = pts
        return pts

    def county_at_point(self, map_rect: pygame.Rect, mx: int, my: int) -> Optional[County]:
        if not map_rect.collidepoint(mx, my):
            return None
        cell_w = map_rect.w / self.grid_w
        cell_h = map_rect.h / self.grid_h
        gx = int((mx - map_rect.x) / cell_w)
        gy = int((my - map_rect.y) / cell_h)
        idx = self._county_index()
        return idx.get((gx, gy))

    def _update_fog_discovery(self):
        """
        CK-ish: reveal player realm and adjacent counties (radius 1).
        """
        idx = self._county_index()
        # mark player realm discovered
        for c in self.counties:
            if c.realm is self.player_realm:
                c.discovered = True

        # reveal neighbors around player counties
        for c in list(self.counties):
            if c.realm is self.player_realm:
                for nx, ny in ((c.grid_x+1, c.grid_y), (c.grid_x-1, c.grid_y), (c.grid_x, c.grid_y+1), (c.grid_x, c.grid_y-1)):
                    n = idx.get((nx, ny))
                    if n:
                        n.discovered = True

    def handle_event(self, event: pygame.event.Event, map_rect: pygame.Rect) -> bool:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.selection.hover = self.county_at_point(map_rect, mx, my)
            return map_rect.collidepoint(mx, my)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            c = self.county_at_point(map_rect, mx, my)
            if c:
                self.selection.county = c
                return True
        return False

    def draw(self, screen: pygame.Surface, map_rect: pygame.Rect):
        self._update_fog_discovery()
        idx = self._county_index()

        # draw biome provinces (irregular polygons)
        for c in self.counties:
            rect = self._cell_rect(map_rect, c.grid_x, c.grid_y)
            poly = self._irregular_poly(rect, c.grid_x, c.grid_y)

            biome_col = BIOME_COLORS.get(c.biome, BIOME_COLORS["plains"])
            pygame.draw.polygon(screen, biome_col, poly)

        # rivers (polyline through cell centers)
        if self.river_points:
            pts = []
            for gx, gy in self.river_points:
                rect = self._cell_rect(map_rect, gx, gy)
                pts.append(rect.center)
            if len(pts) >= 2:
                pygame.draw.lines(screen, RIVER_COLOR, False, pts, 3)

        # Civ6-style borders between different realms
        # Draw borders along edges where neighbor realm differs
        for c in self.counties:
            rect = self._cell_rect(map_rect, c.grid_x, c.grid_y)
            # use rect edges (simple + stable); irregular fill already breaks the grid feel visually
            x0, y0 = rect.x, rect.y
            x1, y1 = rect.right, rect.bottom

            # choose border color based on c.realm (player bright, others dull)
            base = self._color_for_realm(c.realm)
            if c.realm is self.player_realm:
                border_col = base
                thick = BORDER_THICK
            else:
                border_col = self._dull(base, 0.55)
                thick = BORDER_THIN

            # top edge
            n = idx.get((c.grid_x, c.grid_y-1))
            if n and n.realm != c.realm:
                pygame.draw.line(screen, border_col, (x0, y0), (x1, y0), thick)

            # bottom
            n = idx.get((c.grid_x, c.grid_y+1))
            if n and n.realm != c.realm:
                pygame.draw.line(screen, border_col, (x0, y1), (x1, y1), thick)

            # left
            n = idx.get((c.grid_x-1, c.grid_y))
            if n and n.realm != c.realm:
                pygame.draw.line(screen, border_col, (x0, y0), (x0, y1), thick)

            # right
            n = idx.get((c.grid_x+1, c.grid_y))
            if n and n.realm != c.realm:
                pygame.draw.line(screen, border_col, (x1, y0), (x1, y1), thick)

        # selection outline (clear player feedback)
        if self.selection.county:
            rect = self._cell_rect(map_rect, self.selection.county.grid_x, self.selection.county.grid_y)
            pygame.draw.rect(screen, COUNTY_BORDER_SELECTED, rect.inflate(-3, -3), 3, border_radius=6)

        # fog-of-war overlay
        for c in self.counties:
            rect = self._cell_rect(map_rect, c.grid_x, c.grid_y)
            fog = None

            if c.realm is self.player_realm:
                fog = None
            else:
                fog = FOG_DISCOVERED if c.discovered else FOG_UNDISCOVERED

            if fog:
                overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                overlay.fill(fog)
                screen.blit(overlay, rect.topleft)
