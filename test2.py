"""
CK1-Inspired Grand Strategy UI (Pygame) — fully runnable, polished foundation
----------------------------------------------------------------------------
Controls
- Pan map: Right-mouse drag (or hold Space + Left-mouse drag)
- Zoom: Mouse wheel (smooth)
- Select province: Left click on map
- UI buttons: Left click

Run
- pip install pygame
- python ck1_ui_demo.py
"""

import math
import random
import time
from dataclasses import dataclass

import pygame

# =========================
# Provided UI toolkit + constants (USED AS-IS)
# =========================
pygame.font.init()

BG_COLOR = (24, 24, 24)

COLOR = (255, 255, 255)
FONT_PATH = pygame.font.match_font("arial")
TITLE_FONT = pygame.font.Font(FONT_PATH, 24)
HEADER_FONT = pygame.font.Font(FONT_PATH, 20)
BODY_FONT = pygame.font.Font(FONT_PATH, 16)
FOOTER_FONT = pygame.font.Font(FONT_PATH, 14)

BUTTON_BORDER_RADIUS = 4

BUTTON_BG = (50, 50, 70)
BUTTON_BG_HOVER = (80, 80, 120)
BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_BORDER_COLOR = (255, 255, 255)

SECONDARY_BG = (40, 40, 40)
SECONDARY_BG_HOVER = (70, 70, 70)
SECONDARY_TEXT_COLOR = (255, 255, 255)
SECONDARY_BORDER_COLOR = (255, 255, 255)

ACCEPT_BG = (40, 90, 40)
ACCEPT_BG_HOVER = (60, 130, 60)
ACCEPT_TEXT_COLOR = (255, 255, 255)
ACCEPT_BORDER_COLOR = (120, 200, 120)

DENY_BG = (110, 40, 40)
DENY_BG_HOVER = (150, 60, 60)
DENY_TEXT_COLOR = (255, 255, 255)
DENY_BORDER_COLOR = (210, 140, 140)


def _draw_text(surface, text, x, y, font, color):
    text_surf = font.render(text, True, color)
    surface.blit(text_surf, (x, y))
    return y + text_surf.get_height() + 4


def draw_title_text(surface, text, x, y, color=COLOR):
    return _draw_text(surface, text, x, y, TITLE_FONT, color)


def draw_header_text(surface, text, x, y, color=COLOR):
    return _draw_text(surface, text, x, y, HEADER_FONT, color)


def draw_body_text(surface, text, x, y, color=COLOR):
    return _draw_text(surface, text, x, y, BODY_FONT, color)


def draw_footer_text(surface, text, x, y, color=COLOR):
    return _draw_text(surface, text, x, y, FOOTER_FONT, color)


def _draw_button(surface, text, x, y, width, height, bg_color, hover_color, text_color, border_color):
    rect = pygame.Rect(x, y, width, height)
    mx, my = pygame.mouse.get_pos()
    is_hovered = rect.collidepoint(mx, my)
    current_bg = hover_color if is_hovered else bg_color
    pygame.draw.rect(surface, current_bg, rect, border_radius=BUTTON_BORDER_RADIUS)
    pygame.draw.rect(surface, border_color, rect, width=1, border_radius=BUTTON_BORDER_RADIUS)
    text_surf = BODY_FONT.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)
    return rect


def draw_primary_button(surface, text, x, y, width, height):
    return _draw_button(
        surface, text, x, y, width, height,
        BUTTON_BG, BUTTON_BG_HOVER, BUTTON_TEXT_COLOR, BUTTON_BORDER_COLOR
    )


def draw_secondary_button(surface, text, x, y, width, height):
    return _draw_button(
        surface, text, x, y, width, height,
        SECONDARY_BG, SECONDARY_BG_HOVER, SECONDARY_TEXT_COLOR, SECONDARY_BORDER_COLOR
    )


def draw_accept_button(surface, text, x, y, width, height):
    return _draw_button(
        surface, text, x, y, width, height,
        ACCEPT_BG, ACCEPT_BG_HOVER, ACCEPT_TEXT_COLOR, ACCEPT_BORDER_COLOR
    )


def draw_deny_button(surface, text, x, y, width, height):
    return _draw_button(
        surface, text, x, y, width, height,
        DENY_BG, DENY_BG_HOVER, DENY_TEXT_COLOR, DENY_BORDER_COLOR
    )


# =========================
# Extra CK1-esque styling helpers (no external assets required)
# =========================
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def draw_bevel_rect(surface, rect, base, hi, lo, border=(220, 200, 160), border_w=1, radius=6):
    """Soft medieval bevel: top-left highlight, bottom-right shadow, plus a thin border."""
    pygame.draw.rect(surface, base, rect, border_radius=radius)
    # Inner bevel lines
    r = rect.inflate(-2, -2)
    # highlight (top/left)
    pygame.draw.line(surface, hi, (r.left, r.top), (r.right, r.top))
    pygame.draw.line(surface, hi, (r.left, r.top), (r.left, r.bottom))
    # shadow (bottom/right)
    pygame.draw.line(surface, lo, (r.left, r.bottom), (r.right, r.bottom))
    pygame.draw.line(surface, lo, (r.right, r.top), (r.right, r.bottom))
    pygame.draw.rect(surface, border, rect, width=border_w, border_radius=radius)


def draw_panel(surface, rect, title=None, subtitle=None, *,
               fill=(54, 48, 42),  # dark parchment/wood hybrid
               hi=(90, 82, 72),
               lo=(22, 18, 16),
               border=(210, 190, 145),
               radius=8):
    draw_bevel_rect(surface, rect, fill, hi, lo, border=border, border_w=1, radius=radius)

    # Ornamental header strip
    header_h = 34
    header_rect = pygame.Rect(rect.x + 6, rect.y + 6, rect.w - 12, header_h)
    pygame.draw.rect(surface, (70, 60, 52), header_rect, border_radius=6)
    pygame.draw.rect(surface, (150, 130, 95), header_rect, width=1, border_radius=6)

    # Subtle inner texture (speckle) – cheap but effective
    # Keep it light to avoid cost
    rng = random.Random(rect.x * 10007 + rect.y * 97 + rect.w * 11 + rect.h)
    for _ in range(80):
        px = rng.randint(rect.x + 8, rect.right - 9)
        py = rng.randint(rect.y + 8, rect.bottom - 9)
        surface.set_at((px, py), (fill[0] + rng.randint(-8, 8), fill[1] + rng.randint(-8, 8), fill[2] + rng.randint(-8, 8)))

    if title:
        tx = rect.x + 14
        ty = rect.y + 10
        # Shadowed title for weight
        TITLE_FONT.render(title, True, (10, 10, 10))
        shadow = HEADER_FONT.render(title, True, (10, 10, 10))
        surface.blit(shadow, (tx + 1, ty + 1))
        surface.blit(HEADER_FONT.render(title, True, (245, 235, 215)), (tx, ty))

    if subtitle:
        sx = rect.x + 14
        sy = rect.y + 10 + 18
        surface.blit(FOOTER_FONT.render(subtitle, True, (225, 215, 195)), (sx, sy))


def draw_scroll_indicator(surface, x, y, w, h):
    """Little medieval-ish notch bar."""
    r = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, (35, 30, 26), r, border_radius=3)
    pygame.draw.rect(surface, (150, 130, 95), r, width=1, border_radius=3)
    notch = pygame.Rect(r.x + 3, r.y + 3, r.w - 6, max(6, r.h // 3))
    pygame.draw.rect(surface, (85, 75, 63), notch, border_radius=2)


def draw_shield(surface, cx, cy, w, h, primary=(165, 30, 30), secondary=(225, 200, 60), edge=(235, 215, 175)):
    """Simple heraldic shield icon (procedural)."""
    top = cy - h // 2
    left = cx - w // 2
    right = cx + w // 2
    bottom = cy + h // 2

    # Shield silhouette polygon
    pts = [
        (cx, top),
        (right, top + h * 0.18),
        (right - w * 0.12, bottom - h * 0.20),
        (cx, bottom),
        (left + w * 0.12, bottom - h * 0.20),
        (left, top + h * 0.18),
    ]
    pts = [(int(x), int(y)) for x, y in pts]

    pygame.draw.polygon(surface, primary, pts)
    # Vertical stripes
    stripe_w = max(2, w // 7)
    for i in range(0, w, stripe_w * 2):
        pygame.draw.polygon(
            surface, secondary,
            [
                (left + i, top + h * 0.18),
                (left + i + stripe_w, top + h * 0.18),
                (left + i + stripe_w * 0.88, bottom - h * 0.22),
                (left + i + stripe_w * 0.12, bottom - h * 0.22),
            ]
        )

    pygame.draw.polygon(surface, edge, pts, width=2)
    pygame.draw.polygon(surface, (40, 30, 22), pts, width=1)


def draw_round_portrait(surface, center, radius, base=(210, 190, 145)):
    """CK1-ish round portrait frame; inside is a stylized bust silhouette."""
    cx, cy = center
    pygame.draw.circle(surface, (25, 20, 16), (cx + 2, cy + 2), radius + 2)
    pygame.draw.circle(surface, base, (cx, cy), radius + 2)
    pygame.draw.circle(surface, (55, 45, 38), (cx, cy), radius)

    # Silhouette
    head_r = int(radius * 0.38)
    pygame.draw.circle(surface, (120, 105, 90), (cx, cy - int(radius * 0.12)), head_r)
    body = pygame.Rect(cx - int(radius * 0.55), cy - int(radius * 0.02), int(radius * 1.1), int(radius * 0.95))
    pygame.draw.ellipse(surface, (120, 105, 90), body)

    pygame.draw.circle(surface, (240, 230, 210), (cx, cy), radius, width=1)


def draw_tooltip(surface, text, pos):
    mx, my = pos
    padding = 8
    lines = text.split("\n")
    w = 0
    h = 0
    rendered = []
    for ln in lines:
        s = FOOTER_FONT.render(ln, True, (245, 235, 215))
        rendered.append(s)
        w = max(w, s.get_width())
        h += s.get_height() + 2

    rect = pygame.Rect(mx + 14, my + 14, w + padding * 2, h + padding * 2)
    # Keep onscreen
    screen_rect = surface.get_rect()
    if rect.right > screen_rect.right:
        rect.x = mx - rect.w - 14
    if rect.bottom > screen_rect.bottom:
        rect.y = my - rect.h - 14

    pygame.draw.rect(surface, (30, 25, 20), rect, border_radius=6)
    pygame.draw.rect(surface, (180, 160, 120), rect, width=1, border_radius=6)

    y = rect.y + padding
    for s in rendered:
        surface.blit(s, (rect.x + padding, y))
        y += s.get_height() + 2


# =========================
# Data models
# =========================
@dataclass
class Province:
    pid: int
    name: str
    rect: pygame.Rect
    color: tuple[int, int, int]
    border: tuple[int, int, int]
    realm: str


@dataclass
class MessageLogItem:
    t: float
    text: str
    color: tuple[int, int, int] = (230, 220, 200)


# =========================
# Map: procedural CK1-ish political map with borders + labels + water
# =========================
class CK1Map:
    def __init__(self, world_w=4096, world_h=2600, seed=7):
        self.world_w = world_w
        self.world_h = world_h
        self.seed = seed
        self.rng = random.Random(seed)

        self.surface = pygame.Surface((world_w, world_h)).convert()
        self.province_id_at = None  # built as mask (Surface of ints not feasible); use grid lookup

        self.provinces: list[Province] = []
        self._grid = []  # lookup: list of (rect, pid) coarse
        self._selected_pid = None

        self._build_map()

    def _build_map(self):
        self.surface.fill((10, 14, 16))  # deep sea base

        # Water gradient bands
        for y in range(self.world_h):
            t = y / self.world_h
            c = (
                int(8 + 18 * (1 - t)),
                int(22 + 20 * (1 - t)),
                int(30 + 28 * (1 - t)),
            )
            pygame.draw.line(self.surface, c, (0, y), (self.world_w, y))

        # Coastline/landmass: use blobby noise via layered circles
        land = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        land.fill((0, 0, 0, 0))
        for _ in range(140):
            cx = self.rng.randint(200, self.world_w - 200)
            cy = self.rng.randint(200, self.world_h - 200)
            r = self.rng.randint(120, 380)
            pygame.draw.circle(land, (255, 255, 255, 255), (cx, cy), r)

        # Carve some seas
        for _ in range(40):
            cx = self.rng.randint(0, self.world_w)
            cy = self.rng.randint(0, self.world_h)
            r = self.rng.randint(90, 260)
            pygame.draw.circle(land, (0, 0, 0, 0), (cx, cy), r)

        # Convert alpha to a land mask by threshold
        land_mask = pygame.mask.from_surface(land)

        # Draw shallow waters near coasts by blurring edges (cheap: offset land mask)
        shallow = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (2, -2), (-2, 2)]:
            shallow.blit(land, (dx, dy))
        shallow.set_alpha(60)
        self.surface.blit(shallow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Land base texture
        land_base = pygame.Surface((self.world_w, self.world_h)).convert()
        land_base.fill((62, 58, 46))
        # Speckled texture
        self.rng.seed(self.seed + 1000)
        for _ in range(220000):
            x = self.rng.randint(0, self.world_w - 1)
            y = self.rng.randint(0, self.world_h - 1)
            if land_mask.get_at((x, y)):
                base = 62
                jitter = self.rng.randint(-18, 18)
                g = base + jitter
                land_base.set_at((x, y), (g, g - 4, g - 10))

        # Mountains (darker ridges)
        self.rng.seed(self.seed + 222)
        for _ in range(1200):
            x = self.rng.randint(0, self.world_w - 1)
            y = self.rng.randint(0, self.world_h - 1)
            if land_mask.get_at((x, y)) and self.rng.random() < 0.12:
                pygame.draw.circle(land_base, (40, 38, 32), (x, y), self.rng.randint(2, 6))

        # Apply land to world
        self.surface.blit(land_base, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # Now lay provinces: jittered rectangles over land; only keep ones with sufficient land coverage
        realms = [
            ("CROWN LANDS", (180, 40, 40), (160, 30, 30)),
            ("DUCHY", (40, 85, 125), (35, 75, 110)),
            ("MARCHES", (35, 120, 70), (30, 105, 62)),
            ("HOLY ORDER", (120, 110, 35), (110, 100, 30)),
            ("FREE CITY", (90, 70, 130), (78, 62, 112)),
        ]

        self.rng.seed(self.seed + 999)
        pid = 0
        cols = 18
        rows = 11
        cell_w = self.world_w // cols
        cell_h = self.world_h // rows

        name_bits = ["Castel", "Vita", "Arno", "Lyon", "Burg", "Soria", "Narb", "Gasc", "Arel", "Aqua", "Ruth", "Ebro", "Lugo", "Tara", "Oria", "Cair", "Verm", "Raven", "Mont", "Val", "Dun"]
        suffix = ["ia", "um", "en", "ford", "burg", "land", "mere", "grad", "holm", "march", "gate", "shire"]

        def make_name():
            return self.rng.choice(name_bits) + self.rng.choice(suffix)

        provs: list[Province] = []
        for r in range(rows):
            for c in range(cols):
                x = c * cell_w + self.rng.randint(-40, 40)
                y = r * cell_h + self.rng.randint(-30, 30)
                w = cell_w + self.rng.randint(-60, 80)
                h = cell_h + self.rng.randint(-50, 70)
                rect = pygame.Rect(x, y, w, h).clip(pygame.Rect(0, 0, self.world_w, self.world_h))

                # land coverage check
                samples = 80
                hits = 0
                for _ in range(samples):
                    sx = self.rng.randint(rect.left, max(rect.left, rect.right - 1))
                    sy = self.rng.randint(rect.top, max(rect.top, rect.bottom - 1))
                    if land_mask.get_at((sx, sy)):
                        hits += 1
                if hits < samples * 0.35:
                    continue

                realm, (rc, gc, bc), (rb, gb, bb) = self.rng.choice(realms)
                # province fill is realm-tinted but varied
                tint = self.rng.randint(-18, 18)
                col = (clamp(rc + tint, 20, 240), clamp(gc + tint, 20, 240), clamp(bc + tint, 20, 240))
                border = (clamp(rb, 20, 240), clamp(gb, 20, 240), clamp(bb, 20, 240))

                provs.append(Province(pid=pid, name=make_name(), rect=rect, color=col, border=border, realm=realm))
                pid += 1

        # Sort big to small to reduce tiny overlaps
        provs.sort(key=lambda p: p.rect.w * p.rect.h, reverse=True)
        self.provinces = provs

        # Paint provinces with rough edges: use a stippled fill inside rect where land exists
        self.rng.seed(self.seed + 333)
        for p in self.provinces:
            # base fill
            fill_surf = pygame.Surface((p.rect.w, p.rect.h)).convert()
            fill_surf.fill(p.color)

            # subtle noise in province
            for _ in range((p.rect.w * p.rect.h) // 180):
                fx = self.rng.randint(0, p.rect.w - 1)
                fy = self.rng.randint(0, p.rect.h - 1)
                j = self.rng.randint(-15, 15)
                cc = (
                    clamp(p.color[0] + j, 0, 255),
                    clamp(p.color[1] + j, 0, 255),
                    clamp(p.color[2] + j, 0, 255),
                )
                fill_surf.set_at((fx, fy), cc)

            self.surface.blit(fill_surf, (p.rect.x, p.rect.y), special_flags=pygame.BLEND_RGB_ADD)

        # Borders: thick dark + thin bright line to echo CK1
        for p in self.provinces:
            pygame.draw.rect(self.surface, (35, 20, 18), p.rect, width=3)
            pygame.draw.rect(self.surface, p.border, p.rect, width=1)

        # Province labels (sparingly)
        self.rng.seed(self.seed + 444)
        for p in self.provinces:
            if p.rect.w < 160 or p.rect.h < 120:
                continue
            if self.rng.random() < 0.35:
                continue
            label = p.name.upper()
            txt = FOOTER_FONT.render(label, True, (235, 225, 200))
            shadow = FOOTER_FONT.render(label, True, (15, 12, 10))
            pos = (p.rect.centerx - txt.get_width() // 2, p.rect.centery - txt.get_height() // 2)
            self.surface.blit(shadow, (pos[0] + 1, pos[1] + 1))
            self.surface.blit(txt, pos)

        # Decorative compass rose-ish mark
        self._draw_compass()

        # Build coarse grid for hit-testing
        self._grid = [(p.rect, p.pid) for p in self.provinces]

    def _draw_compass(self):
        cx = int(self.world_w * 0.78)
        cy = int(self.world_h * 0.18)
        r = 54
        pygame.draw.circle(self.surface, (30, 25, 20), (cx, cy), r + 4)
        pygame.draw.circle(self.surface, (190, 170, 130), (cx, cy), r + 2)
        pygame.draw.circle(self.surface, (55, 48, 40), (cx, cy), r)

        for ang in [0, 90, 180, 270]:
            a = math.radians(ang)
            x1 = cx + int(math.cos(a) * 10)
            y1 = cy + int(math.sin(a) * 10)
            x2 = cx + int(math.cos(a) * (r - 6))
            y2 = cy + int(math.sin(a) * (r - 6))
            pygame.draw.line(self.surface, (200, 180, 140), (x1, y1), (x2, y2), 2)
        # small diagonals
        for ang in [45, 135, 225, 315]:
            a = math.radians(ang)
            x2 = cx + int(math.cos(a) * (r - 10))
            y2 = cy + int(math.sin(a) * (r - 10))
            pygame.draw.line(self.surface, (140, 120, 90), (cx, cy), (x2, y2), 1)

        n = HEADER_FONT.render("N", True, (235, 225, 200))
        self.surface.blit(n, (cx - n.get_width() // 2, cy - r + 6))

    def province_at_world(self, wx, wy):
        # Fast reject
        if wx < 0 or wy < 0 or wx >= self.world_w or wy >= self.world_h:
            return None
        for rect, pid in self._grid:
            if rect.collidepoint(wx, wy):
                return pid
        return None

    def get_province(self, pid):
        for p in self.provinces:
            if p.pid == pid:
                return p
        return None

    def set_selected(self, pid):
        self._selected_pid = pid

    @property
    def selected_pid(self):
        return self._selected_pid


# =========================
# Camera / MapView (smooth zoom + panning)
# =========================
class MapView:
    def __init__(self, game_map: CK1Map, viewport_rect: pygame.Rect):
        self.map = game_map
        self.viewport = viewport_rect

        self.cam_x = game_map.world_w * 0.48
        self.cam_y = game_map.world_h * 0.50

        self.zoom = 1.00
        self.target_zoom = 1.00
        self.zoom_min = 0.55
        self.zoom_max = 2.35

        self.dragging = False
        self.drag_anchor = (0, 0)
        self.drag_cam_anchor = (self.cam_x, self.cam_y)

        self.hover_pid = None

    def world_to_screen(self, wx, wy):
        sx = (wx - self.cam_x) * self.zoom + self.viewport.centerx
        sy = (wy - self.cam_y) * self.zoom + self.viewport.centery
        return sx, sy

    def screen_to_world(self, sx, sy):
        wx = (sx - self.viewport.centerx) / self.zoom + self.cam_x
        wy = (sy - self.viewport.centery) / self.zoom + self.cam_y
        return wx, wy

    def clamp_camera(self):
        # Keep camera within world bounds (with margin based on viewport size)
        half_w = self.viewport.w / (2 * self.zoom)
        half_h = self.viewport.h / (2 * self.zoom)
        self.cam_x = clamp(self.cam_x, half_w, self.map.world_w - half_w)
        self.cam_y = clamp(self.cam_y, half_h, self.map.world_h - half_h)

    def handle_event(self, e, ui_consumed=False):
        if ui_consumed:
            return

        if e.type == pygame.MOUSEWHEEL:
            # smooth zoom: adjust target, keep cursor anchored in world-space
            mx, my = pygame.mouse.get_pos()
            if not self.viewport.collidepoint(mx, my):
                return

            before = self.screen_to_world(mx, my)
            factor = 1.12 ** e.y
            self.target_zoom = clamp(self.target_zoom * factor, self.zoom_min, self.zoom_max)

            # after zoom will shift; we correct in update by anchoring to cursor
            after = self.screen_to_world(mx, my)
            self.cam_x += (before[0] - after[0])
            self.cam_y += (before[1] - after[1])
            self.clamp_camera()

        elif e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            if not self.viewport.collidepoint(mx, my):
                return

            space_held = pygame.key.get_pressed()[pygame.K_SPACE]
            if e.button == 3 or (space_held and e.button == 1):
                self.dragging = True
                self.drag_anchor = (mx, my)
                self.drag_cam_anchor = (self.cam_x, self.cam_y)

            if e.button == 1 and not space_held:
                wx, wy = self.screen_to_world(mx, my)
                pid = self.map.province_at_world(int(wx), int(wy))
                self.map.set_selected(pid)

        elif e.type == pygame.MOUSEBUTTONUP:
            if e.button == 3 or e.button == 1:
                self.dragging = False

        elif e.type == pygame.MOUSEMOTION:
            mx, my = e.pos
            if self.dragging:
                dx = mx - self.drag_anchor[0]
                dy = my - self.drag_anchor[1]
                self.cam_x = self.drag_cam_anchor[0] - dx / self.zoom
                self.cam_y = self.drag_cam_anchor[1] - dy / self.zoom
                self.clamp_camera()
            else:
                if self.viewport.collidepoint(mx, my):
                    wx, wy = self.screen_to_world(mx, my)
                    self.hover_pid = self.map.province_at_world(int(wx), int(wy))
                else:
                    self.hover_pid = None

    def update(self, dt):
        # Smooth zoom interpolation
        z_before = self.zoom
        self.zoom = lerp(self.zoom, self.target_zoom, 1.0 - math.exp(-dt * 12.0))
        if abs(self.zoom - self.target_zoom) < 0.0006:
            self.zoom = self.target_zoom

        if z_before != self.zoom:
            self.clamp_camera()

    def draw(self, screen):
        # Determine world rect visible
        half_w = self.viewport.w / (2 * self.zoom)
        half_h = self.viewport.h / (2 * self.zoom)
        world_left = int(self.cam_x - half_w)
        world_top = int(self.cam_y - half_h)
        world_w = int(self.viewport.w / self.zoom)
        world_h = int(self.viewport.h / self.zoom)
        src = pygame.Rect(world_left, world_top, world_w, world_h).clip(pygame.Rect(0, 0, self.map.world_w, self.map.world_h))

        # Scale to viewport
        view = pygame.transform.smoothscale(self.map.surface.subsurface(src), (self.viewport.w, self.viewport.h))
        screen.blit(view, self.viewport.topleft)

        # CK1-ish frame over the map
        pygame.draw.rect(screen, (25, 20, 16), self.viewport, width=3)
        pygame.draw.rect(screen, (180, 160, 120), self.viewport, width=1)

        # Hover / selection overlays (screen-space rectangles approximation)
        for pid, col in [(self.map.selected_pid, (240, 220, 180)), (self.hover_pid, (220, 200, 150))]:
            if pid is None:
                continue
            p = self.map.get_province(pid)
            if not p:
                continue
            # Transform province rect corners; draw a subtle highlight box
            tl = self.world_to_screen(p.rect.left, p.rect.top)
            br = self.world_to_screen(p.rect.right, p.rect.bottom)
            r = pygame.Rect(int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1]))
            r = r.clip(self.viewport)
            if r.w > 2 and r.h > 2:
                overlay = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                overlay.fill((col[0], col[1], col[2], 38))
                screen.blit(overlay, r.topleft)
                pygame.draw.rect(screen, (col[0], col[1], col[2]), r, width=2)

        # Mini zoom indicator in corner
        ztxt = f"Zoom: {self.zoom:.2f}x"
        s = FOOTER_FONT.render(ztxt, True, (235, 225, 200))
        pad = 6
        pill = pygame.Rect(self.viewport.right - s.get_width() - pad * 2 - 12, self.viewport.bottom - s.get_height() - pad * 2 - 12,
                           s.get_width() + pad * 2, s.get_height() + pad * 2)
        pygame.draw.rect(screen, (30, 25, 20), pill, border_radius=7)
        pygame.draw.rect(screen, (180, 160, 120), pill, width=1, border_radius=7)
        screen.blit(s, (pill.x + pad, pill.y + pad))


# =========================
# UI: topbar, side panels, minimap, message log
# =========================
class MessageLog:
    def __init__(self, capacity=7):
        self.capacity = capacity
        self.items: list[MessageLogItem] = []

    def push(self, text, color=(230, 220, 200)):
        self.items.append(MessageLogItem(t=time.time(), text=text, color=color))
        if len(self.items) > self.capacity:
            self.items = self.items[-self.capacity :]

    def draw(self, surface, rect: pygame.Rect):
        draw_panel(surface, rect, title="Chronicle", subtitle="Recent events")
        inner = rect.inflate(-14, -52)
        inner.y += 26
        inner.h -= 26

        # Subtle parchment box
        pygame.draw.rect(surface, (45, 40, 34), inner, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), inner, width=1, border_radius=6)

        y = inner.y + 10
        for it in self.items[-self.capacity:]:
            # Fade older lines slightly
            age = time.time() - it.t
            fade = clamp(1.0 - age / 16.0, 0.35, 1.0)
            col = (int(it.color[0] * fade), int(it.color[1] * fade), int(it.color[2] * fade))
            y = draw_footer_text(surface, it.text, inner.x + 10, y, color=col)
            if y > inner.bottom - 18:
                break


class MiniMap:
    def __init__(self, game_map: CK1Map, size=(240, 150)):
        self.map = game_map
        self.size = size
        self.cached = None
        self._build()

    def _build(self):
        thumb = pygame.transform.smoothscale(self.map.surface, self.size)
        # Darken + increase contrast slightly
        overlay = pygame.Surface(self.size).convert()
        overlay.fill((18, 14, 12))
        thumb.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        self.cached = thumb

    def draw(self, surface, rect: pygame.Rect, map_view: MapView):
        draw_panel(surface, rect, title="Miniature", subtitle="Realm overview")
        inner = rect.inflate(-12, -52)
        inner.y += 26
        inner.h -= 26

        pygame.draw.rect(surface, (30, 25, 20), inner, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), inner, width=1, border_radius=6)

        # Fit thumb into inner
        thumb = pygame.transform.smoothscale(self.cached, (inner.w, inner.h))
        surface.blit(thumb, inner.topleft)

        # Camera rectangle on minimap
        # Compute visible world rect
        half_w = map_view.viewport.w / (2 * map_view.zoom)
        half_h = map_view.viewport.h / (2 * map_view.zoom)
        wl = map_view.cam_x - half_w
        wt = map_view.cam_y - half_h
        ww = half_w * 2
        wh = half_h * 2

        sx = inner.x + (wl / self.map.world_w) * inner.w
        sy = inner.y + (wt / self.map.world_h) * inner.h
        sw = (ww / self.map.world_w) * inner.w
        sh = (wh / self.map.world_h) * inner.h

        cam_r = pygame.Rect(int(sx), int(sy), int(sw), int(sh)).clip(inner)
        pygame.draw.rect(surface, (240, 220, 180), cam_r, width=2)
        pygame.draw.rect(surface, (20, 16, 12), cam_r, width=1)


class LeftPanel:
    def __init__(self, log: MessageLog):
        self.log = log
        self.army_name = "Sancho's Army"
        self.regiments = [("Jaca Regiment", 928), ("Huesca Levy", 610), ("Spear Militia", 420)]
        self.selected_reg = 0

        self._btns = {}

    def draw(self, surface, rect: pygame.Rect, selected_province: Province | None):
        draw_panel(surface, rect, title=self.army_name, subtitle="Host & retinue")

        # Portrait + coat of arms
        portrait_center = (rect.x + 64, rect.y + 76)
        draw_round_portrait(surface, portrait_center, 38)
        draw_shield(surface, rect.x + rect.w - 64, rect.y + 76, 54, 62)

        # Regiment list
        list_rect = pygame.Rect(rect.x + 12, rect.y + 126, rect.w - 24, 156)
        pygame.draw.rect(surface, (45, 40, 34), list_rect, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), list_rect, width=1, border_radius=6)

        y = list_rect.y + 10
        for i, (nm, men) in enumerate(self.regiments):
            row = pygame.Rect(list_rect.x + 8, y - 2, list_rect.w - 16, 26)
            if i == self.selected_reg:
                pygame.draw.rect(surface, (80, 72, 60), row, border_radius=4)
                pygame.draw.rect(surface, (200, 180, 140), row, width=1, border_radius=4)
            label = f"{nm}"
            count = f"{men}"
            surface.blit(BODY_FONT.render(label, True, (235, 225, 200)), (row.x + 8, row.y + 4))
            surface.blit(BODY_FONT.render(count, True, (235, 225, 200)), (row.right - 50, row.y + 4))
            y += 28

        # Stats
        stats_rect = pygame.Rect(rect.x + 12, rect.y + 292, rect.w - 24, 150)
        pygame.draw.rect(surface, (45, 40, 34), stats_rect, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), stats_rect, width=1, border_radius=6)

        y = stats_rect.y + 10
        y = draw_body_text(surface, "Strength:", stats_rect.x + 10, y, color=(235, 225, 200))
        y = draw_body_text(surface, "  Men: 1,958", stats_rect.x + 10, y, color=(215, 205, 185))
        y = draw_body_text(surface, "  Morale: Steady", stats_rect.x + 10, y, color=(215, 205, 185))
        y = draw_body_text(surface, "Supplies:", stats_rect.x + 10, y, color=(235, 225, 200))
        y = draw_body_text(surface, "  Forage: 88%", stats_rect.x + 10, y, color=(215, 205, 185))

        if selected_province:
            y = draw_body_text(surface, "Stationed in:", stats_rect.x + 10, y, color=(235, 225, 200))
            y = draw_body_text(surface, f"  {selected_province.name} ({selected_province.realm})", stats_rect.x + 10, y, color=(215, 205, 185))

        # Buttons
        bx = rect.x + 12
        by = rect.bottom - 92
        bw = rect.w - 24
        self._btns["split"] = draw_secondary_button(surface, "Split", bx, by, bw, 28)
        self._btns["disband"] = draw_deny_button(surface, "Disband", bx, by + 34, bw, 28)

        # little scroll indicator to mimic CK1 list UI
        draw_scroll_indicator(surface, rect.right - 22, list_rect.y + 10, 10, list_rect.h - 20)

    def handle_click(self, pos):
        for k, r in self._btns.items():
            if r.collidepoint(pos):
                if k == "split":
                    self.log.push("Army reorganized: detachments formed.", color=(220, 210, 190))
                elif k == "disband":
                    self.log.push("The host disperses. Men return to their fields.", color=(230, 190, 190))
                return True
        return False


class RightPanel:
    def __init__(self, log: MessageLog):
        self.log = log
        self._btns = {}

        # A tiny “realm” model for flavor
        self.ruler_name = "Duke Sancho de Aragon"
        self.titles = ["Duke of Sobrarbe", "Count of Jaca"]
        self.stats = {"Diplomacy": 7, "Martial": 11, "Stewardship": 6, "Intrigue": 5, "Learning": 8}

    def draw(self, surface, rect: pygame.Rect, selected_province: Province | None):
        draw_panel(surface, rect, title="Chamber", subtitle="Realm & holdings")

        # Ruler plate
        plate = pygame.Rect(rect.x + 12, rect.y + 48, rect.w - 24, 118)
        pygame.draw.rect(surface, (45, 40, 34), plate, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), plate, width=1, border_radius=6)

        draw_round_portrait(surface, (plate.x + 54, plate.y + 58), 34)
        draw_shield(surface, plate.right - 54, plate.y + 58, 50, 58)

        x = plate.x + 100
        y = plate.y + 10
        y = draw_body_text(surface, self.ruler_name, x, y, color=(240, 230, 210))
        for t in self.titles:
            y = draw_footer_text(surface, f"• {t}", x, y, color=(220, 210, 190))

        # Attributes
        attr = pygame.Rect(rect.x + 12, rect.y + 174, rect.w - 24, 160)
        pygame.draw.rect(surface, (45, 40, 34), attr, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), attr, width=1, border_radius=6)

        y = attr.y + 10
        y = draw_body_text(surface, "Attributes", attr.x + 10, y, color=(240, 230, 210))
        for k, v in self.stats.items():
            y = draw_footer_text(surface, f"{k:<12} {v}", attr.x + 10, y, color=(220, 210, 190))

        # Province focus
        focus = pygame.Rect(rect.x + 12, rect.y + 342, rect.w - 24, 140)
        pygame.draw.rect(surface, (45, 40, 34), focus, border_radius=6)
        pygame.draw.rect(surface, (160, 140, 105), focus, width=1, border_radius=6)

        y = focus.y + 10
        y = draw_body_text(surface, "Selected Province", focus.x + 10, y, color=(240, 230, 210))
        if selected_province:
            y = draw_footer_text(surface, f"Name: {selected_province.name}", focus.x + 10, y, color=(220, 210, 190))
            y = draw_footer_text(surface, f"Realm: {selected_province.realm}", focus.x + 10, y, color=(220, 210, 190))
            y = draw_footer_text(surface, f"Levies: {selected_province.rect.w * selected_province.rect.h // 2500}", focus.x + 10, y, color=(220, 210, 190))
        else:
            y = draw_footer_text(surface, "None (click the map).", focus.x + 10, y, color=(220, 210, 190))

        # Actions
        bx = rect.x + 12
        by = rect.bottom - 92
        bw = rect.w - 24
        self._btns["council"] = draw_primary_button(surface, "Council", bx, by, bw, 28)
        self._btns["laws"] = draw_secondary_button(surface, "Laws", bx, by + 34, bw, 28)

    def handle_click(self, pos):
        for k, r in self._btns.items():
            if r.collidepoint(pos):
                if k == "council":
                    self.log.push("Council convened: whispers behind oak doors.", color=(220, 210, 190))
                elif k == "laws":
                    self.log.push("Edicts reviewed: parchment cracks in candlelight.", color=(220, 210, 190))
                return True
        return False


class TopBar:
    def __init__(self, log: MessageLog):
        self.log = log
        self._btns = {}
        self.date_str = "January 21, 1067"
        self.resources = {"Gold": 489, "Prestige": 100, "Piety": 100}

    def draw(self, surface, rect: pygame.Rect):
        draw_panel(surface, rect, title=None, subtitle=None, fill=(40, 34, 28), hi=(70, 62, 52), lo=(18, 14, 12), border=(200, 180, 135), radius=10)

        # Decorative corner shields
        draw_shield(surface, rect.x + 32, rect.y + rect.h // 2, 38, 44, primary=(165, 30, 30), secondary=(225, 200, 60))
        draw_shield(surface, rect.right - 32, rect.y + rect.h // 2, 38, 44, primary=(40, 85, 125), secondary=(225, 200, 60))

        # Date (center)
        dt = HEADER_FONT.render(self.date_str, True, (245, 235, 215))
        shadow = HEADER_FONT.render(self.date_str, True, (10, 8, 6))
        cx = rect.centerx - dt.get_width() // 2
        cy = rect.y + 10
        surface.blit(shadow, (cx + 1, cy + 1))
        surface.blit(dt, (cx, cy))

        # Resources (left-center)
        x = rect.x + 90
        y = rect.y + 12
        for k, v in self.resources.items():
            txt = f"{k}: {v}"
            surface.blit(FOOTER_FONT.render(txt, True, (235, 225, 200)), (x, y))
            x += 120

        # Buttons (right)
        bx = rect.right - 290
        by = rect.y + 8
        self._btns["menu"] = draw_secondary_button(surface, "Menu", bx, by, 86, 28)
        self._btns["realm"] = draw_primary_button(surface, "Realm", bx + 92, by, 86, 28)
        self._btns["quit"] = draw_deny_button(surface, "Quit", bx + 184, by, 86, 28)

    def handle_click(self, pos):
        for k, r in self._btns.items():
            if r.collidepoint(pos):
                if k == "menu":
                    self.log.push("Ledger opened: ink stains & old debts.", color=(220, 210, 190))
                elif k == "realm":
                    self.log.push("Realm view: banners flutter in your mind.", color=(220, 210, 190))
                elif k == "quit":
                    return "quit"
                return True
        return False


# =========================
# App
# =========================
class GameUIApp:
    def __init__(self, w=1400, h=900):
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.screen = pygame.display.set_mode((w, h))
        self.clock = pygame.time.Clock()

        # Layout
        self.top_h = 52
        self.bottom_h = 170
        self.left_w = 300
        self.right_w = 300
        self.pad = 10

        self.map_rect = pygame.Rect(
            self.left_w + self.pad,
            self.top_h + self.pad,
            w - self.left_w - self.right_w - self.pad * 2,
            h - self.top_h - self.bottom_h - self.pad * 2,
        )
        self.left_rect = pygame.Rect(self.pad, self.top_h + self.pad, self.left_w - self.pad, h - self.top_h - self.pad * 2)
        self.right_rect = pygame.Rect(w - self.right_w, self.top_h + self.pad, self.right_w - self.pad, h - self.top_h - self.pad * 2)
        self.top_rect = pygame.Rect(self.pad, self.pad, w - self.pad * 2, self.top_h - self.pad)
        self.bottom_rect = pygame.Rect(self.pad, h - self.bottom_h, w - self.pad * 2, self.bottom_h - self.pad)

        # Core modules
        self.log = MessageLog(capacity=8)
        self.log.push("January 8, 1067: Ulrich presses a claim in Carinthia.", color=(220, 210, 190))
        self.log.push("January 11, 1067: Veslav becomes Prince of Vitebsk.", color=(220, 210, 190))
        self.log.push("January 18, 1067: Your spymaster reports a new traitor.", color=(230, 200, 170))
        self.log.push("January 20, 1067: A rival duke rallies banners.", color=(230, 190, 190))

        self.game_map = CK1Map(world_w=4096, world_h=2600, seed=7)
        self.map_view = MapView(self.game_map, self.map_rect)

        self.topbar = TopBar(self.log)
        self.left_panel = LeftPanel(self.log)
        self.right_panel = RightPanel(self.log)
        self.minimap = MiniMap(self.game_map, size=(260, 160))

        self.running = True
        self.tooltip_text = None

        # Bottom layout: chronicle + minimap + instructions
        self.chronicle_rect = pygame.Rect(self.bottom_rect.x, self.bottom_rect.y, int(self.bottom_rect.w * 0.55), self.bottom_rect.h)
        self.mini_rect = pygame.Rect(self.chronicle_rect.right + self.pad, self.bottom_rect.y, 340, self.bottom_rect.h)
        self.help_rect = pygame.Rect(self.mini_rect.right + self.pad, self.bottom_rect.y, self.bottom_rect.right - (self.mini_rect.right + self.pad), self.bottom_rect.h)

    def _draw_background_frame(self):
        self.screen.fill(BG_COLOR)

        # Outer frame
        pygame.draw.rect(self.screen, (10, 8, 7), self.screen.get_rect(), width=10)
        pygame.draw.rect(self.screen, (120, 100, 70), self.screen.get_rect().inflate(-6, -6), width=2)

        # Corner rivets
        for cx, cy in [(30, 30), (self.screen.get_width() - 30, 30), (30, self.screen.get_height() - 30), (self.screen.get_width() - 30, self.screen.get_height() - 30)]:
            pygame.draw.circle(self.screen, (20, 16, 12), (cx + 2, cy + 2), 8)
            pygame.draw.circle(self.screen, (170, 150, 110), (cx, cy), 8)
            pygame.draw.circle(self.screen, (80, 68, 52), (cx, cy), 6)

    def _ui_consumed_at(self, pos):
        # If click is inside any non-map panels, map shouldn't handle it
        x, y = pos
        if self.top_rect.collidepoint(x, y):
            return True
        if self.left_rect.collidepoint(x, y):
            return True
        if self.right_rect.collidepoint(x, y):
            return True
        if self.bottom_rect.collidepoint(x, y):
            return True
        return False

    def _selected_province(self):
        pid = self.game_map.selected_pid
        return self.game_map.get_province(pid) if pid is not None else None

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.tooltip_text = None

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                    break

                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        self.running = False
                        break
                    if e.key == pygame.K_r:
                        self.log.push("A herald arrives: rumors spread through the halls.", color=(220, 210, 190))

                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    # UI clicks
                    res = self.topbar.handle_click(e.pos)
                    if res == "quit":
                        self.running = False
                        break
                    if res:
                        continue
                    if self.left_panel.handle_click(e.pos):
                        continue
                    if self.right_panel.handle_click(e.pos):
                        continue

                # Map input (unless UI consumed)
                self.map_view.handle_event(e, ui_consumed=self._ui_consumed_at(getattr(e, "pos", pygame.mouse.get_pos())))

            self.map_view.update(dt)

            # Draw
            self._draw_background_frame()

            # Top bar
            self.topbar.draw(self.screen, self.top_rect)

            # Map
            self.map_view.draw(self.screen)

            # Side panels
            sel = self._selected_province()
            self.left_panel.draw(self.screen, self.left_rect, sel)
            self.right_panel.draw(self.screen, self.right_rect, sel)

            # Bottom region
            self.log.draw(self.screen, self.chronicle_rect)
            self.minimap.draw(self.screen, self.mini_rect, self.map_view)

            # Help panel
            draw_panel(self.screen, self.help_rect, title="Orders", subtitle="Controls & context")
            inner = self.help_rect.inflate(-14, -52)
            inner.y += 26
            inner.h -= 26
            pygame.draw.rect(self.screen, (45, 40, 34), inner, border_radius=6)
            pygame.draw.rect(self.screen, (160, 140, 105), inner, width=1, border_radius=6)

            y = inner.y + 10
            y = draw_footer_text(self.screen, "Pan: Right-drag (or Space + Left-drag)", inner.x + 10, y, color=(220, 210, 190))
            y = draw_footer_text(self.screen, "Zoom: Mouse wheel (smooth)", inner.x + 10, y, color=(220, 210, 190))
            y = draw_footer_text(self.screen, "Select: Left-click province", inner.x + 10, y, color=(220, 210, 190))
            y = draw_footer_text(self.screen, "Keys: R = add event, Esc = quit", inner.x + 10, y, color=(220, 210, 190))

            # Tooltips (hover province)
            mx, my = pygame.mouse.get_pos()
            if self.map_rect.collidepoint(mx, my) and self.map_view.hover_pid is not None:
                p = self.game_map.get_province(self.map_view.hover_pid)
                if p:
                    self.tooltip_text = f"{p.name}\nRealm: {p.realm}\nLevies: {p.rect.w * p.rect.h // 2500}"

            if self.tooltip_text:
                draw_tooltip(self.screen, self.tooltip_text, (mx, my))

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    GameUIApp(1400, 900).run()
