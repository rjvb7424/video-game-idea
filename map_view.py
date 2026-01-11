# map_view.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Optional

from domain import County
from config import MAP_BG, COUNTY_BORDER, COUNTY_BORDER_HOVER, COUNTY_BORDER_SELECTED

@dataclass
class MapSelection:
    county: Optional[County] = None
    hover: Optional[County] = None

class MapView:
    """
    CK3-like interaction (simplified):
      - grid of counties
      - hover highlight
      - click to select county
    """
    def __init__(self, counties: list[County], grid_size: tuple[int, int]):
        self.counties = counties
        self.grid_w, self.grid_h = grid_size
        self.selection = MapSelection()

        # Layout tuning
        self.cell_pad = 2

        # A stable color per realm (generated on first use)
        self._realm_colors: dict[int, tuple[int, int, int]] = {}

    def _color_for_realm(self, realm) -> tuple[int, int, int]:
        key = id(realm)
        if key in self._realm_colors:
            return self._realm_colors[key]

        # Deterministic-ish but visually varied from realm name hash
        h = abs(hash(realm.name))
        r = 70 + (h % 140)
        g = 70 + ((h // 7) % 140)
        b = 70 + ((h // 13) % 140)
        col = (r, g, b)
        self._realm_colors[key] = col
        return col

    def county_at_point(self, rect: pygame.Rect, mx: int, my: int) -> Optional[County]:
        if not rect.collidepoint(mx, my):
            return None

        cell_w = rect.w / self.grid_w
        cell_h = rect.h / self.grid_h

        gx = int((mx - rect.x) / cell_w)
        gy = int((my - rect.y) / cell_h)

        for c in self.counties:
            if c.grid_x == gx and c.grid_y == gy:
                return c
        return None

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

    def draw(self, screen: pygame.Surface, rect: pygame.Rect):
        pygame.draw.rect(screen, MAP_BG, rect, border_radius=10)

        cell_w = rect.w / self.grid_w
        cell_h = rect.h / self.grid_h

        # Draw counties
        for c in self.counties:
            x = rect.x + int(c.grid_x * cell_w)
            y = rect.y + int(c.grid_y * cell_h)
            w = int(cell_w)
            h = int(cell_h)

            cell_rect = pygame.Rect(x, y, w, h).inflate(-self.cell_pad * 2, -self.cell_pad * 2)

            fill = self._color_for_realm(c.realm)
            pygame.draw.rect(screen, fill, cell_rect, border_radius=6)

            # Borders (hover/selected)
            border = COUNTY_BORDER
            if self.selection.hover is c:
                border = COUNTY_BORDER_HOVER
            if self.selection.county is c:
                border = COUNTY_BORDER_SELECTED

            pygame.draw.rect(screen, border, cell_rect, width=2, border_radius=6)
