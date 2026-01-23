import pygame

from core.surfaces import draw_drop_shadow, tile_fill
from ui.theme import (
    PANEL_OUTER,
    PANEL_INNER,
    PANEL_INNER_2,
    BEVEL_LIGHT,
    BEVEL_DARK,
    INK,
    HEADER_FONT,
)

_PANEL_VEIL_CACHE = {}
_PANEL_MASK_CACHE = {}


def _get_panel_veil(size):
    veil = _PANEL_VEIL_CACHE.get(size)
    if veil is None:
        veil = pygame.Surface(size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 22))
        _PANEL_VEIL_CACHE[size] = veil
    return veil


def _get_panel_mask(size, radius):
    key = (size, radius)
    mask = _PANEL_MASK_CACHE.get(key)
    if mask is None:
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
        _PANEL_MASK_CACHE[key] = mask
    return mask


def draw_framed_panel(surface, rect, title=None, title_color=INK, tile=None):
    draw_drop_shadow(surface, rect, strength=120, inflate=4, radius=10)
    pygame.draw.rect(surface, PANEL_OUTER, rect, border_radius=10)

    pygame.draw.rect(surface, BEVEL_DARK, rect, width=2, border_radius=10)
    pygame.draw.line(surface, BEVEL_LIGHT, (rect.left + 2, rect.top + 2), (rect.right - 3, rect.top + 2))
    pygame.draw.line(surface, BEVEL_LIGHT, (rect.left + 2, rect.top + 2), (rect.left + 2, rect.bottom - 3))
    pygame.draw.line(surface, BEVEL_DARK, (rect.left + 2, rect.bottom - 3), (rect.right - 3, rect.bottom - 3))
    pygame.draw.line(surface, BEVEL_DARK, (rect.right - 3, rect.top + 2), (rect.right - 3, rect.bottom - 3))

    inner = rect.inflate(-14, -14)
    pygame.draw.rect(surface, PANEL_INNER, inner, border_radius=8)
    if tile is not None:
        tile_surf = pygame.Surface(inner.size, pygame.SRCALPHA)
        tile_fill(tile_surf, tile_surf.get_rect(), tile)
        tile_surf.blit(_get_panel_veil(inner.size), (0, 0))
        tile_surf.blit(_get_panel_mask(inner.size, 8), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(tile_surf, inner.topleft)

    pygame.draw.rect(surface, (12, 12, 12), inner, width=1, border_radius=8)

    rivet_col = (66, 62, 56)
    for px, py in [
        (rect.left + 14, rect.top + 14),
        (rect.right - 14, rect.top + 14),
        (rect.left + 14, rect.bottom - 14),
        (rect.right - 14, rect.bottom - 14),
    ]:
        pygame.draw.circle(surface, rivet_col, (px, py), 3)
        pygame.draw.circle(surface, (18, 18, 18), (px + 1, py + 1), 3, 1)

    content = inner
    if title:
        strip_h = 28
        strip = pygame.Rect(inner.left + 6, inner.top + 6, inner.w - 12, strip_h)
        pygame.draw.rect(surface, PANEL_INNER_2, strip, border_radius=6)
        pygame.draw.rect(surface, (14, 14, 14), strip, width=1, border_radius=6)
        title_surf = HEADER_FONT.render(title, True, title_color)
        title_rect = title_surf.get_rect(midleft=(strip.left + 8, strip.centery))
        surface.blit(title_surf, title_rect)
        content = pygame.Rect(inner.left + 8, strip.bottom + 6, inner.w - 16, inner.h - strip_h - 14)

    return content
