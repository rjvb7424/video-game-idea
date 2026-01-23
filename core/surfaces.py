import math
import random

import pygame

from core.math_utils import clamp

_DROP_SHADOW_CACHE = {}
_VIGNETTE_CACHE = {}


def make_noise_tile(size, base_rgb, variance=12, alpha=255, seed=1):
    rnd = random.Random(seed)
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    br, bg, bb = base_rgb
    for y in range(h):
        for x in range(w):
            dv = rnd.randint(-variance, variance)
            r = clamp(br + dv, 0, 255)
            g = clamp(bg + dv, 0, 255)
            b = clamp(bb + dv, 0, 255)
            surf.set_at((x, y), (r, g, b, alpha))
    return surf


def tile_fill(dst, rect, tile):
    tw, th = tile.get_size()
    for y in range(rect.top, rect.bottom, th):
        for x in range(rect.left, rect.right, tw):
            dst.blit(tile, (x, y))


def _get_drop_shadow_surface(w, h, strength, inflate, radius):
    key = (w, h, strength, inflate, radius)
    surf = _DROP_SHADOW_CACHE.get(key)
    if surf is None:
        surf = pygame.Surface((w + inflate * 2, h + inflate * 2), pygame.SRCALPHA)
        pygame.draw.rect(surf, (0, 0, 0, strength), surf.get_rect(), border_radius=radius)
        _DROP_SHADOW_CACHE[key] = surf
    return surf


def draw_drop_shadow(surface, rect, strength=110, inflate=6, radius=8):
    shadow = _get_drop_shadow_surface(rect.w, rect.h, strength, inflate, radius)
    surface.blit(shadow, (rect.x - inflate, rect.y - inflate))


def _get_vignette_overlay(size, strength):
    key = (size, strength)
    overlay = _VIGNETTE_CACHE.get(key)
    if overlay is None:
        overlay = pygame.Surface(size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 0))
        cx, cy = size[0] / 2, size[1] / 2
        max_d = math.hypot(cx, cy)
        step = 16
        for r in range(0, int(max_d), step):
            a = int(clamp((r / max_d) ** 1.8 * strength, 0, strength))
            pygame.draw.circle(overlay, (0, 0, 0, a), (int(cx), int(cy)), r, width=step)
        _VIGNETTE_CACHE[key] = overlay
    return overlay


def draw_vignette(surface, rect, strength=85):
    overlay = _get_vignette_overlay(rect.size, strength)
    surface.blit(overlay, rect.topleft)
