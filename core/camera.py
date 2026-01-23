import math

import pygame

from core.math_utils import clamp, lerp, exp_smooth_t


class Camera:
    def __init__(self, world_size, viewport_size):
        self.world_w, self.world_h = world_size
        self.vp_w, self.vp_h = viewport_size

        self.center = pygame.Vector2(self.world_w * 0.52, self.world_h * 0.52)
        self.target_center = self.center.copy()

        self.zoom = 1.0
        self.target_zoom = 1.0

        self.min_zoom = 0.55
        self.max_zoom = 2.60

        self._dragging = False
        self._drag_anchor_mouse = pygame.Vector2(0, 0)
        self._drag_anchor_target = self.target_center.copy()

    def set_viewport(self, viewport_size):
        self.vp_w, self.vp_h = viewport_size
        self._clamp_target()

    def begin_drag(self, mouse_pos):
        self._dragging = True
        self._drag_anchor_mouse = pygame.Vector2(mouse_pos)
        self._drag_anchor_target = self.target_center.copy()

    def end_drag(self):
        self._dragging = False

    def drag_to(self, mouse_pos):
        if not self._dragging:
            return
        mp = pygame.Vector2(mouse_pos)
        delta = mp - self._drag_anchor_mouse
        self.target_center = self._drag_anchor_target - (delta / max(self.target_zoom, 0.001))
        self._clamp_target()

    def pan(self, dx, dy):
        self.target_center.x += dx
        self.target_center.y += dy
        self._clamp_target()

    def zoom_at(self, factor, mouse_in_map, map_rect):
        mx, my = mouse_in_map
        before = self.screen_to_world((mx, my), map_rect, use_target=True)
        self.target_zoom = clamp(self.target_zoom * factor, self.min_zoom, self.max_zoom)
        after = self.screen_to_world((mx, my), map_rect, use_target=True)
        shift = before - after
        self.target_center += shift
        self._clamp_target()

    def update(self, dt):
        t = exp_smooth_t(10.0, dt)
        self.center.x = lerp(self.center.x, self.target_center.x, t)
        self.center.y = lerp(self.center.y, self.target_center.y, t)
        self.zoom = lerp(self.zoom, self.target_zoom, t)
        self._clamp_actual()

    def view_rect(self, use_target=False):
        z = self.target_zoom if use_target else self.zoom
        cx, cy = (self.target_center if use_target else self.center)
        view_w = self.vp_w / max(z, 0.001)
        view_h = self.vp_h / max(z, 0.001)
        x = int(round(cx - view_w / 2))
        y = int(round(cy - view_h / 2))
        w = int(math.ceil(view_w))
        h = int(math.ceil(view_h))
        return pygame.Rect(x, y, w, h)

    def screen_to_world(self, mouse_pos, map_rect, use_target=False):
        vx = self.view_rect(use_target=use_target)
        z = self.target_zoom if use_target else self.zoom
        sx, sy = mouse_pos
        rx = sx - map_rect.left
        ry = sy - map_rect.top
        wx = vx.left + rx / max(z, 0.001)
        wy = vx.top + ry / max(z, 0.001)
        return pygame.Vector2(wx, wy)

    def world_to_screen(self, world_pos, map_rect, use_target=False):
        vx = self.view_rect(use_target=use_target)
        z = self.target_zoom if use_target else self.zoom
        wx, wy = world_pos
        sx = (wx - vx.left) * z + map_rect.left
        sy = (wy - vx.top) * z + map_rect.top
        return pygame.Vector2(sx, sy)

    def _clamp_target(self):
        self._clamp_center(self.target_center, self.target_zoom)

    def _clamp_actual(self):
        self._clamp_center(self.center, self.zoom)

    def _clamp_center(self, center, zoom):
        inv_zoom = 1.0 / max(zoom, 0.001)
        half_w = (self.vp_w * inv_zoom) / 2
        half_h = (self.vp_h * inv_zoom) / 2
        if self.world_w <= 2 * half_w:
            center.x = self.world_w / 2
        else:
            center.x = clamp(center.x, half_w, self.world_w - half_w)
        if self.world_h <= 2 * half_h:
            center.y = self.world_h / 2
        else:
            center.y = clamp(center.y, half_h, self.world_h - half_h)
