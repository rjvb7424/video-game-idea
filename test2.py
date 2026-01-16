import math
import random
import pygame

# =========================
# Provided UI Toolkit (Mandatory Base) - DO NOT MODIFY
# =========================

# external imports
import pygame

# initialize pygame font module
pygame.font.init()

# background constant
BG_COLOR = (24, 24, 24)

# font constants
COLOR = (255, 255, 255)
FONT_PATH = pygame.font.match_font("arial")
TITLE_FONT  = pygame.font.Font(FONT_PATH, 24)
HEADER_FONT = pygame.font.Font(FONT_PATH, 20)
BODY_FONT   = pygame.font.Font(FONT_PATH, 16)
FOOTER_FONT = pygame.font.Font(FONT_PATH, 14)

# button constants
BUTTON_BORDER_RADIUS = 4

# primary button colours
BUTTON_BG = (50, 50, 70)
BUTTON_BG_HOVER = (80, 80, 120)
BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_BORDER_COLOR = (255, 255, 255)

# secondary button colours
SECONDARY_BG = (40, 40, 40)
SECONDARY_BG_HOVER = (70, 70, 70)
SECONDARY_TEXT_COLOR = (255, 255, 255)
SECONDARY_BORDER_COLOR = (255, 255, 255)

# confirm action button colours
ACCEPT_BG = (40, 90, 40)
ACCEPT_BG_HOVER = (60, 130, 60)
ACCEPT_TEXT_COLOR = (255, 255, 255)
ACCEPT_BORDER_COLOR = (120, 200, 120)

# cancel action button colours
DENY_BG = (110, 40, 40)
DENY_BG_HOVER = (150, 60, 60)
DENY_TEXT_COLOR = (255, 255, 255)
DENY_BORDER_COLOR = (210, 140, 140)

# text helpers
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

# button helpers
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
    return _draw_button(surface, text, x, y, width, height, BUTTON_BG, BUTTON_BG_HOVER, BUTTON_TEXT_COLOR, BUTTON_BORDER_COLOR)

def draw_secondary_button(surface, text, x, y, width, height):
    return _draw_button(surface, text, x, y, width, height, SECONDARY_BG, SECONDARY_BG_HOVER, SECONDARY_TEXT_COLOR, SECONDARY_BORDER_COLOR)

def draw_accept_button(surface, text, x, y, width, height):
    return _draw_button(surface, text, x, y, width, height, ACCEPT_BG, ACCEPT_BG_HOVER, ACCEPT_TEXT_COLOR, ACCEPT_BORDER_COLOR)

def draw_deny_button(surface, text, x, y, width, height):
    return _draw_button(surface, text, x, y, width, height, DENY_BG, DENY_BG_HOVER, DENY_TEXT_COLOR, DENY_BORDER_COLOR)


# =========================
# Grand Strategy UI + Map Systems
# =========================

UI_GUTTER = 10
TOP_BAR_H = 60
BOTTOM_BAR_H = 98
SIDE_W_L = 310
SIDE_W_R = 310

# UI palette (kept subdued / medieval)
PANEL_OUTER = (18, 18, 19)
PANEL_INNER = (34, 34, 36)
PANEL_INNER_2 = (41, 41, 43)
BEVEL_LIGHT = (86, 86, 92)
BEVEL_DARK = (10, 10, 10)
INK = (222, 218, 206)
MUTED = (170, 170, 170)
ACCENT_GOLD = (160, 140, 90)
ACCENT_RED = (110, 40, 40)

# Map palette
SEA_DEEP = (14, 26, 44)
SEA_SHALLOWS = (18, 38, 64)
LAND_BASE = (66, 76, 54)
LAND_DRY = (86, 82, 56)
LAND_HIGHLIGHT = (94, 104, 70)
MOUNTAIN = (78, 76, 74)
FOREST = (50, 66, 42)
BORDER_RED = (118, 26, 26)
BORDER_RED_DIM = (90, 22, 22)

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

def exp_smooth_t(sharpness, dt):
    # dt-aware smoothing factor: stable across framerates
    # t = 1 - exp(-k*dt)
    return 1.0 - math.exp(-sharpness * dt)

def wrap_text(text, font, max_width):
    words = text.split()
    if not words:
        return [""]
    lines = []
    cur = words[0]
    for w in words[1:]:
        test = cur + " " + w
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

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

def draw_drop_shadow(surface, rect, strength=110, inflate=6, radius=8):
    shadow = pygame.Surface((rect.w + inflate * 2, rect.h + inflate * 2), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, strength), shadow.get_rect(), border_radius=radius)
    surface.blit(shadow, (rect.x - inflate, rect.y - inflate))

def draw_framed_panel(surface, rect, title=None, title_color=INK, tile=None):
    # Shadow + outer plate
    draw_drop_shadow(surface, rect, strength=120, inflate=7, radius=10)
    pygame.draw.rect(surface, PANEL_OUTER, rect, border_radius=10)

    # Bevel frame
    pygame.draw.rect(surface, BEVEL_DARK, rect, width=2, border_radius=10)
    pygame.draw.line(surface, BEVEL_LIGHT, (rect.left+2, rect.top+2), (rect.right-3, rect.top+2))
    pygame.draw.line(surface, BEVEL_LIGHT, (rect.left+2, rect.top+2), (rect.left+2, rect.bottom-3))
    pygame.draw.line(surface, BEVEL_DARK, (rect.left+2, rect.bottom-3), (rect.right-3, rect.bottom-3))
    pygame.draw.line(surface, BEVEL_DARK, (rect.right-3, rect.top+2), (rect.right-3, rect.bottom-3))

    # Inner area
    inner = rect.inflate(-14, -14)
    pygame.draw.rect(surface, PANEL_INNER, inner, border_radius=8)
    if tile is not None:
        tile_fill(surface, inner, tile)
        # gentle darken to unify
        veil = pygame.Surface(inner.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 22))
        surface.blit(veil, inner.topleft)

    pygame.draw.rect(surface, (12, 12, 12), inner, width=1, border_radius=8)

    # Rivets
    rivet_col = (66, 62, 56)
    for px, py in [(rect.left+14, rect.top+14), (rect.right-14, rect.top+14), (rect.left+14, rect.bottom-14), (rect.right-14, rect.bottom-14)]:
        pygame.draw.circle(surface, rivet_col, (px, py), 3)
        pygame.draw.circle(surface, (18, 18, 18), (px+1, py+1), 3, 1)

    # Title bar strip
    content = inner
    if title:
        strip_h = 28
        strip = pygame.Rect(inner.left+6, inner.top+6, inner.w-12, strip_h)
        pygame.draw.rect(surface, PANEL_INNER_2, strip, border_radius=6)
        pygame.draw.rect(surface, (14, 14, 14), strip, width=1, border_radius=6)
        y = strip.top + 4
        draw_header_text(surface, title, strip.left + 8, y, color=title_color)
        content = pygame.Rect(inner.left+8, strip.bottom+6, inner.w-16, inner.h - strip_h - 14)

    return content

def draw_vignette(surface, rect, strength=95):
    # subtle darkening towards edges (old-screen / framed feeling)
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    cx, cy = rect.w / 2, rect.h / 2
    max_d = math.hypot(cx, cy)
    step = 16
    for r in range(0, int(max_d), step):
        a = int(clamp((r / max_d) ** 1.8 * strength, 0, strength))
        pygame.draw.circle(overlay, (0, 0, 0, a), (int(cx), int(cy)), r, width=step)
    surface.blit(overlay, rect.topleft)

def shield_points(center, size):
    cx, cy = center
    w = size
    h = int(size * 1.25)
    return [
        (cx - w//2, cy - h//2),
        (cx + w//2, cy - h//2),
        (cx + int(w*0.45), cy + int(h*0.08)),
        (cx, cy + h//2),
        (cx - int(w*0.45), cy + int(h*0.08)),
    ]


class GameDate:
    MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    MONTH_LEN = [31,28,31,30,31,30,31,31,30,31,30,31]

    def __init__(self, year=1067, month=1, day=21):
        self.year = year
        self.month = month
        self.day = day

    def advance_days(self, n):
        for _ in range(n):
            self.day += 1
            ml = self.MONTH_LEN[self.month-1]
            if self.day > ml:
                self.day = 1
                self.month += 1
                if self.month > 12:
                    self.month = 1
                    self.year += 1

    def __str__(self):
        return f"{self.MONTHS[self.month-1]} {self.day}, {self.year}"


class Camera:
    def __init__(self, world_size, viewport_size):
        self.world_w, self.world_h = world_size
        self.vp_w, self.vp_h = viewport_size

        self.center = pygame.Vector2(self.world_w * 0.52, self.world_h * 0.52)
        self.target_center = self.center.copy()

        self.zoom = 1.0
        self.target_zoom = 1.0

        self.min_zoom = 0.55
        self.max_zoom = 2.40

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
        # screen delta -> world delta
        self.target_center = self._drag_anchor_target - (delta / max(self.target_zoom, 0.001))
        self._clamp_target()

    def pan(self, dx, dy):
        self.target_center.x += dx
        self.target_center.y += dy
        self._clamp_target()

    def zoom_at(self, factor, mouse_in_map, map_rect):
        # Keep world point under cursor stable (target-based, feels weighty once easing catches up)
        mx, my = mouse_in_map
        before = self.screen_to_world((mx, my), map_rect, use_target=True)

        self.target_zoom = clamp(self.target_zoom * factor, self.min_zoom, self.max_zoom)

        after = self.screen_to_world((mx, my), map_rect, use_target=True)
        shift = before - after
        self.target_center += shift
        self._clamp_target()

    def update(self, dt):
        t = exp_smooth_t(10.0, dt)  # weighty smoothing
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
        # sx, sy are absolute screen coords; convert to coords relative to map rect:
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
        # clamp target center so the view stays within world bounds
        half_w = (self.vp_w / max(self.target_zoom, 0.001)) / 2
        half_h = (self.vp_h / max(self.target_zoom, 0.001)) / 2
        if self.world_w <= 2 * half_w:
            self.target_center.x = self.world_w / 2
        else:
            self.target_center.x = clamp(self.target_center.x, half_w, self.world_w - half_w)
        if self.world_h <= 2 * half_h:
            self.target_center.y = self.world_h / 2
        else:
            self.target_center.y = clamp(self.target_center.y, half_h, self.world_h - half_h)

    def _clamp_actual(self):
        # keep actual close too (prevents wobble at borders)
        half_w = (self.vp_w / max(self.zoom, 0.001)) / 2
        half_h = (self.vp_h / max(self.zoom, 0.001)) / 2
        if self.world_w <= 2 * half_w:
            self.center.x = self.world_w / 2
        else:
            self.center.x = clamp(self.center.x, half_w, self.world_w - half_w)
        if self.world_h <= 2 * half_h:
            self.center.y = self.world_h / 2
        else:
            self.center.y = clamp(self.center.y, half_h, self.world_h - half_h)


class Province:
    def __init__(self, pid, name, cell_xy, poly, realm_id, is_water=False):
        self.id = pid
        self.name = name
        self.cell = cell_xy
        self.poly = poly  # list[(x,y)] in world coords
        self.realm_id = realm_id
        self.is_water = is_water

        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        self.bounds = pygame.Rect(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))

        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        self.center = pygame.Vector2(cx, cy)

        # Placeholder stats
        self.income = 1 + (pid % 5)
        self.levy = 120 + (pid * 7) % 400
        self.control = 55 + (pid * 3) % 45

        # Flavor
        self.culture = ["Frankish", "Occitan", "Iberian", "Germanic", "Slavic"][pid % 5]
        self.faith = ["Catholic", "Orthodox", "Pagan", "Sunni", "Mozarabic"][pid % 5]


class MapWorld:
    def __init__(self, seed=7, size=(3200, 2200), cols=18, rows=12):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.size = size
        self.cols = cols
        self.rows = rows

        self.surface = pygame.Surface(size).convert()
        self._base = pygame.Surface(size).convert()
        self._overlay = pygame.Surface(size, pygame.SRCALPHA)

        # Procedural content
        self.provinces = []
        self.prov_grid = [[None for _ in range(rows)] for _ in range(cols)]
        self.realm_colors = [
            (54, 64, 92),
            (74, 54, 84),
            (66, 78, 56),
            (88, 66, 50),
            (56, 78, 78),
        ]

        # Tiles for texture
        self.sea_tile = make_noise_tile((96, 96), SEA_DEEP, variance=10, alpha=255, seed=seed + 100)
        self.land_tile = make_noise_tile((96, 96), LAND_BASE, variance=10, alpha=255, seed=seed + 200)
        self.paper_tile = make_noise_tile((64, 64), (52, 52, 54), variance=10, alpha=255, seed=seed + 300)

        self._generate()

    def _name(self):
        a = ["Al", "Bel", "Car", "Dor", "Er", "Fen", "Gar", "Hal", "Ish", "Jar", "Kor", "Lor", "Mor", "Nor", "Or", "Pra", "Quel", "Ros", "San", "Tor", "Ul", "Var"]
        b = ["a", "e", "i", "o", "u", "ae", "ia", "oa"]
        c = ["don", "bar", "mont", "ford", "wick", "mere", "gard", "heim", "hold", "grad", "port", "cester", "vale", "mark", "burg"]
        return self.rnd.choice(a) + self.rnd.choice(b) + self.rnd.choice(c)

    def _generate(self):
        w, h = self.size

        # --- Sea base (tiled noise + subtle horizontal banding) ---
        self._base.fill(SEA_DEEP)
        tile_fill(self._base, self._base.get_rect(), self.sea_tile)

        band = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, 6):
            a = 10 if (y // 6) % 2 == 0 else 0
            pygame.draw.line(band, (0, 0, 0, a), (0, y), (w, y))
        self._base.blit(band, (0, 0))

        # --- Land masses: blob stamping ---
        land_centers = []
        for _ in range(9):
            cx = self.rnd.randint(int(w * 0.15), int(w * 0.85))
            cy = self.rnd.randint(int(h * 0.18), int(h * 0.82))
            r = self.rnd.randint(220, 420)
            land_centers.append((cx, cy, r))

        # Stamp main blobs
        for (cx, cy, r) in land_centers:
            for k in range(10):
                rr = int(r * self.rnd.uniform(0.55, 1.08))
                ox = int(self.rnd.uniform(-0.55, 0.55) * r)
                oy = int(self.rnd.uniform(-0.55, 0.55) * r)
                col = self.rnd.choice([LAND_BASE, LAND_DRY, LAND_HIGHLIGHT])
                pygame.draw.circle(self._base, col, (cx + ox, cy + oy), rr)

        # Coast "shallows" hint: soft circles around land blobs
        for (cx, cy, r) in land_centers:
            for _ in range(20):
                rr = int(r * self.rnd.uniform(0.75, 1.18))
                ox = int(self.rnd.uniform(-0.7, 0.7) * r)
                oy = int(self.rnd.uniform(-0.7, 0.7) * r)
                pygame.draw.circle(self._base, SEA_SHALLOWS, (cx + ox, cy + oy), rr, width=3)

        # Terrain detail: forests + mountains speckles
        for _ in range(2600):
            x = self.rnd.randint(0, w - 1)
            y = self.rnd.randint(0, h - 1)
            r, g, b = self._base.get_at((x, y))[:3]
            is_land = (g >= b) and (g > 40)
            if not is_land:
                continue
            roll = self.rnd.random()
            if roll < 0.55:
                # grass speckle
                col = (clamp(r + self.rnd.randint(-6, 6), 0, 255),
                       clamp(g + self.rnd.randint(-8, 8), 0, 255),
                       clamp(b + self.rnd.randint(-6, 6), 0, 255))
                self._base.set_at((x, y), col)
            elif roll < 0.82:
                # forest dot
                pygame.draw.circle(self._base, FOREST, (x, y), 1)
            else:
                # mountain dot
                pygame.draw.circle(self._base, MOUNTAIN, (x, y), 1)

        # Rivers (simple "inked" bezier-ish lines)
        for _ in range(5):
            x0 = self.rnd.randint(int(w * 0.2), int(w * 0.8))
            y0 = self.rnd.randint(int(h * 0.2), int(h * 0.8))
            x1 = clamp(x0 + self.rnd.randint(-520, 520), 0, w)
            y1 = clamp(y0 + self.rnd.randint(-520, 520), 0, h)
            x2 = clamp(x1 + self.rnd.randint(-520, 520), 0, w)
            y2 = clamp(y1 + self.rnd.randint(-520, 520), 0, h)

            pts = []
            steps = 70
            for i in range(steps + 1):
                t = i / steps
                # quadratic bezier
                xa = lerp(x0, x1, t)
                ya = lerp(y0, y1, t)
                xb = lerp(x1, x2, t)
                yb = lerp(y1, y2, t)
                x = lerp(xa, xb, t)
                y = lerp(ya, yb, t)
                pts.append((int(x), int(y)))
            pygame.draw.lines(self._base, (40, 90, 120), False, pts, width=4)
            pygame.draw.lines(self._base, (110, 160, 180), False, pts, width=1)

        # --- Provinces: grid-based polygons with jitter (CK1-style red borders) ---
        self._overlay.fill((0, 0, 0, 0))
        cell_w = w / self.cols
        cell_h = h / self.rows

        pid = 0
        for cx in range(self.cols):
            for cy in range(self.rows):
                x0 = cx * cell_w
                y0 = cy * cell_h
                x1 = (cx + 1) * cell_w
                y1 = (cy + 1) * cell_h

                jx = cell_w * 0.10
                jy = cell_h * 0.10

                poly = [
                    (int(x0 + self.rnd.uniform(0, jx)), int(y0 + self.rnd.uniform(0, jy))),
                    (int(x1 - self.rnd.uniform(0, jx)), int(y0 + self.rnd.uniform(0, jy))),
                    (int(x1 - self.rnd.uniform(0, jx)), int(y1 - self.rnd.uniform(0, jy))),
                    (int(x0 + self.rnd.uniform(0, jx)), int(y1 - self.rnd.uniform(0, jy))),
                ]

                # Determine land/water by sampling center
                midx = int((x0 + x1) / 2)
                midy = int((y0 + y1) / 2)
                sr, sg, sb = self._base.get_at((midx, midy))[:3]
                is_water = (sb > sg + 10) or (sg < 45)

                realm_id = (cx // 4 + cy // 3) % len(self.realm_colors)

                name = self._name() if not is_water else ("Sea Zone " + str((pid % 9) + 1))
                prov = Province(pid, name, (cx, cy), poly, realm_id, is_water=is_water)
                self.provinces.append(prov)
                self.prov_grid[cx][cy] = prov

                # Province fill tint (very subtle)
                tint = self.realm_colors[realm_id]
                fill_a = 34 if not is_water else 18
                pygame.draw.polygon(self._overlay, (tint[0], tint[1], tint[2], fill_a), poly)

                # Borders
                pygame.draw.lines(self._overlay, (*BORDER_RED_DIM, 220), True, poly, width=2)
                pygame.draw.lines(self._overlay, (*BORDER_RED, 110), True, poly, width=1)

                # Province labels (sparse, avoid clutter on water)
                if (pid % 3 == 0) and (not is_water):
                    label = FOOTER_FONT.render(prov.name, True, (210, 205, 190))
                    label.set_alpha(140)
                    lrect = label.get_rect(center=(int(prov.center.x), int(prov.center.y)))
                    self._overlay.blit(label, lrect)

                # Shields (realm markers)
                if (pid % 4 == 0) and (not is_water):
                    sp = shield_points((int(prov.center.x), int(prov.center.y)), size=22)
                    base = self.realm_colors[realm_id]
                    pygame.draw.polygon(self._overlay, (*base, 200), sp)
                    pygame.draw.polygon(self._overlay, (240, 230, 210, 130), sp, width=1)

                # Town/castle glyphs
                if (pid % 5 == 0) and (not is_water):
                    self._draw_castle(self._overlay, (int(prov.center.x + 22), int(prov.center.y - 12)))

                pid += 1

        # --- Armies (little figurine markers) ---
        for _ in range(10):
            # find a land province
            prov = self.rnd.choice([p for p in self.provinces if not p.is_water])
            px = int(prov.center.x + self.rnd.randint(-30, 30))
            py = int(prov.center.y + self.rnd.randint(-30, 30))
            self._draw_army(self._overlay, (px, py), color=(190, 190, 200, 210))

        # Compose final map surface
        self.surface.blit(self._base, (0, 0))
        self.surface.blit(self._overlay, (0, 0))

        # Old-map ink veil
        ink = pygame.Surface(self.size, pygame.SRCALPHA)
        tile_fill(ink, ink.get_rect(), self.paper_tile)
        ink.fill((0, 0, 0, 25), special_flags=pygame.BLEND_RGBA_MULT)
        self.surface.blit(ink, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_castle(self, surf, pos):
        x, y = pos
        col = (210, 205, 190, 160)
        pygame.draw.rect(surf, col, pygame.Rect(x, y, 10, 8))
        pygame.draw.rect(surf, (30, 20, 20, 160), pygame.Rect(x, y, 10, 8), 1)
        pygame.draw.rect(surf, col, pygame.Rect(x+2, y-4, 6, 4))
        pygame.draw.rect(surf, (30, 20, 20, 160), pygame.Rect(x+2, y-4, 6, 4), 1)
        pygame.draw.rect(surf, (40, 25, 25, 160), pygame.Rect(x+4, y+3, 2, 5))

    def _draw_army(self, surf, pos, color=(200, 200, 210, 200)):
        x, y = pos
        # small banner + knight-ish dot
        pygame.draw.circle(surf, color, (x, y), 4)
        pygame.draw.line(surf, color, (x, y+4), (x, y+14), 2)
        pygame.draw.polygon(surf, color, [(x, y+6), (x+10, y+8), (x, y+10)])
        pygame.draw.polygon(surf, (25, 20, 18, 160), [(x, y+6), (x+10, y+8), (x, y+10)], 1)

    def province_at_world(self, world_pos):
        x, y = world_pos
        if x < 0 or y < 0 or x >= self.size[0] or y >= self.size[1]:
            return None
        cx = int(x / (self.size[0] / self.cols))
        cy = int(y / (self.size[1] / self.rows))
        cx = clamp(cx, 0, self.cols - 1)
        cy = clamp(cy, 0, self.rows - 1)
        return self.prov_grid[cx][cy]


class Layout:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.top = pygame.Rect(0, 0, w, TOP_BAR_H)
        self.bottom = pygame.Rect(0, h - BOTTOM_BAR_H, w, BOTTOM_BAR_H)
        self.left = pygame.Rect(UI_GUTTER, TOP_BAR_H + UI_GUTTER, SIDE_W_L, h - TOP_BAR_H - BOTTOM_BAR_H - UI_GUTTER * 2)
        self.right = pygame.Rect(w - SIDE_W_R - UI_GUTTER, TOP_BAR_H + UI_GUTTER, SIDE_W_R, h - TOP_BAR_H - BOTTOM_BAR_H - UI_GUTTER * 2)

        mx = self.left.right + UI_GUTTER
        my = TOP_BAR_H + UI_GUTTER
        mw = self.right.left - UI_GUTTER - mx
        mh = self.bottom.top - UI_GUTTER - my
        self.map = pygame.Rect(mx, my, mw, mh)

    def update(self, w, h):
        self.__init__(w, h)


class Modal:
    def __init__(self):
        self.open = False
        self.title = "Menu"
        self.lines = []
        self.actions = []  # list[(label, kind, callback)] kind in {"primary","secondary","accept","deny"}

    def show(self, title, lines, actions):
        self.open = True
        self.title = title
        self.lines = lines[:]
        self.actions = actions[:]

    def close(self):
        self.open = False

    def draw(self, surface, panel_tile):
        if not self.open:
            return []

        w, h = surface.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        rect = pygame.Rect(0, 0, 520, 300)
        rect.center = (w // 2, h // 2)

        content = draw_framed_panel(surface, rect, title=self.title, title_color=INK, tile=panel_tile)

        y = content.top
        for ln in self.lines:
            for wrapped in wrap_text(ln, BODY_FONT, content.w - 10):
                y = draw_body_text(surface, wrapped, content.left, y, color=(230, 225, 210))
            y += 2

        # Buttons row
        btns = []
        btn_w = 140
        btn_h = 36
        gap = 10
        total = len(self.actions) * btn_w + (len(self.actions) - 1) * gap
        x = content.centerx - total // 2
        yb = rect.bottom - 58

        for label, kind, cb in self.actions:
            if kind == "primary":
                r = draw_primary_button(surface, label, x, yb, btn_w, btn_h)
            elif kind == "secondary":
                r = draw_secondary_button(surface, label, x, yb, btn_w, btn_h)
            elif kind == "accept":
                r = draw_accept_button(surface, label, x, yb, btn_w, btn_h)
            else:
                r = draw_deny_button(surface, label, x, yb, btn_w, btn_h)
            btns.append((r, cb))
            x += btn_w + gap

        return btns


class UIManager:
    def __init__(self, seed=11):
        # Textures used across panels (precomputed)
        self.panel_tile = make_noise_tile((96, 96), (44, 44, 46), variance=10, alpha=255, seed=seed)
        self.top_tile = make_noise_tile((128, 64), (28, 28, 30), variance=10, alpha=255, seed=seed + 1)
        self.bottom_tile = make_noise_tile((96, 96), (26, 26, 28), variance=10, alpha=255, seed=seed + 2)

    def draw_top_bar(self, surface, rect, state):
        # Background
        pygame.draw.rect(surface, (16, 16, 16), rect)
        tile_fill(surface, rect, self.top_tile)
        pygame.draw.line(surface, (90, 86, 78), (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1))
        pygame.draw.line(surface, (0, 0, 0), (rect.left, rect.bottom - 2), (rect.right, rect.bottom - 2))

        # Title plaque
        plaque = pygame.Rect(rect.left + UI_GUTTER, rect.top + 10, 360, rect.h - 20)
        pygame.draw.rect(surface, (22, 22, 22), plaque, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), plaque, 2, border_radius=8)
        pygame.draw.line(surface, (120, 110, 92), (plaque.left + 2, plaque.top + 2), (plaque.right - 3, plaque.top + 2))

        draw_title_text(surface, "DOMINION: GRAND STRATEGY", plaque.left + 12, plaque.top + 6, color=(235, 228, 210))
        draw_footer_text(surface, "Early-era Paradox-inspired interface prototype", plaque.left + 12, plaque.top + 32, color=(170, 165, 155))

        # Date block
        date_block = pygame.Rect(plaque.right + 10, plaque.top, 240, plaque.h)
        pygame.draw.rect(surface, (22, 22, 22), date_block, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), date_block, 2, border_radius=8)
        draw_header_text(surface, str(state["date"]), date_block.left + 12, date_block.top + 10, color=(230, 224, 208))

        # Resources
        rx = date_block.right + 14
        ry = rect.top + 18
        res = state["resources"]
        self._draw_resource(surface, (rx, ry), "Gold", res["gold"], icon_color=(190, 165, 90))
        self._draw_resource(surface, (rx + 140, ry), "Prestige", res["prestige"], icon_color=(150, 150, 165))
        self._draw_resource(surface, (rx + 290, ry), "Piety", res["piety"], icon_color=(165, 150, 110))

        # Time controls (right)
        btns = []
        bx = rect.right - UI_GUTTER - 300
        by = rect.top + 12
        bw = 60
        bh = 36

        # speed indicator plate
        plate = pygame.Rect(bx - 130, by, 120, bh)
        pygame.draw.rect(surface, (22, 22, 22), plate, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), plate, 2, border_radius=8)
        sp = state["speed_level"]
        sp_label = "Paused" if sp == 0 else f"Speed {sp}"
        draw_body_text(surface, sp_label, plate.left + 10, plate.top + 8, color=(220, 214, 198))

        # Buttons
        b_pause = draw_secondary_button(surface, "II", bx, by, bw, bh)
        b_slow = draw_secondary_button(surface, ">", bx + 70, by, bw, bh)
        b_fast = draw_secondary_button(surface, ">>", bx + 140, by, bw, bh)
        b_ultra = draw_secondary_button(surface, ">>>", bx + 210, by, bw, bh)
        btns.append((b_pause, "toggle_pause"))
        btns.append((b_slow, "speed_1"))
        btns.append((b_fast, "speed_2"))
        btns.append((b_ultra, "speed_3"))

        # Control hint
        hint = "Drag map / WASD or Arrows to pan • Wheel or +/- to zoom • Click province to select"
        draw_footer_text(surface, hint, rect.left + 10, rect.bottom - 20, color=(150, 145, 138))

        return btns

    def _draw_resource(self, surface, pos, label, value, icon_color):
        x, y = pos
        icon = pygame.Rect(x, y + 4, 18, 18)
        pygame.draw.rect(surface, (22, 22, 22), pygame.Rect(x - 6, y - 6, 130, 34), border_radius=8)
        pygame.draw.circle(surface, icon_color, icon.center, 7)
        pygame.draw.circle(surface, (0, 0, 0), icon.center, 7, 1)
        draw_body_text(surface, f"{value}", x + 24, y, color=(235, 228, 210))
        draw_footer_text(surface, label, x + 24, y + 18, color=(165, 160, 150))

    def draw_left_panel(self, surface, rect, state):
        content = draw_framed_panel(surface, rect, title="Character", title_color=INK, tile=self.panel_tile)
        y = content.top

        # Portrait frame
        pf = pygame.Rect(content.left, y, content.w, 120)
        self._draw_portrait(surface, pf, state)
        y = pf.bottom + 10

        # Name + titles
        y = draw_header_text(surface, state["character"]["name"], content.left, y, color=(235, 228, 210))
        y = draw_body_text(surface, state["character"]["title"], content.left, y, color=(185, 175, 160))
        y += 6

        # Stats (CK-like columns)
        stats = state["character"]["stats"]
        left_x = content.left
        mid_x = content.left + content.w // 2
        for i, (k, v) in enumerate(stats):
            tx = left_x if i % 2 == 0 else mid_x
            if i % 2 == 0 and i > 0:
                y += 2
            yy = y if i % 2 == 0 else y - (BODY_FONT.get_height() + 4)
            draw_body_text(surface, f"{k}: {v}", tx, yy, color=(220, 214, 198))
            if i % 2 == 1:
                y += BODY_FONT.get_height() + 6

        y += 10
        pygame.draw.line(surface, (0, 0, 0), (content.left, y), (content.right, y))
        pygame.draw.line(surface, (80, 74, 66), (content.left, y + 1), (content.right, y + 1))
        y += 10

        # Army block
        y = draw_header_text(surface, "Levy & Army", content.left, y, color=(230, 224, 208))
        y = draw_body_text(surface, f"Raised: {state['army']['raised']}", content.left, y, color=(205, 198, 180))
        y = draw_body_text(surface, f"Max: {state['army']['max']}", content.left, y, color=(205, 198, 180))
        y = draw_body_text(surface, f"Morale: {state['army']['morale']}%", content.left, y, color=(205, 198, 180))
        y += 6

        # Small action buttons
        btns = []
        bx = content.left
        by = rect.bottom - 56
        b1 = draw_primary_button(surface, "Raise", bx, by, 90, 34)
        b2 = draw_secondary_button(surface, "Rally", bx + 100, by, 90, 34)
        b3 = draw_deny_button(surface, "Disband", bx + 200, by, 90, 34)
        btns.append((b1, "raise_army"))
        btns.append((b2, "rally"))
        btns.append((b3, "disband"))
        return btns

    def _draw_portrait(self, surface, rect, state):
        # Framed portrait with a “painted” feel (procedural shapes)
        frame = pygame.Rect(rect.left, rect.top, rect.w, rect.h)
        pygame.draw.rect(surface, (18, 18, 18), frame, border_radius=10)
        pygame.draw.rect(surface, (0, 0, 0), frame, 2, border_radius=10)

        inner = frame.inflate(-12, -12)
        pygame.draw.rect(surface, (40, 36, 32), inner, border_radius=8)

        # Faux canvas noise overlay
        tile = self.panel_tile
        tile_fill(surface, inner, tile)
        veil = pygame.Surface(inner.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 45))
        surface.blit(veil, inner.topleft)

        # Head silhouette
        cx = inner.left + 60
        cy = inner.centery
        pygame.draw.circle(surface, (205, 185, 160), (cx, cy - 6), 26)
        pygame.draw.circle(surface, (55, 40, 30), (cx + 4, cy - 18), 24)  # hair
        pygame.draw.rect(surface, (90, 76, 62), pygame.Rect(cx - 20, cy + 12, 40, 26), border_radius=8)  # tunic
        pygame.draw.circle(surface, (18, 18, 18), (cx - 8, cy - 8), 2)  # eye
        pygame.draw.circle(surface, (18, 18, 18), (cx + 6, cy - 8), 2)
        pygame.draw.line(surface, (120, 90, 70), (cx - 6, cy + 4), (cx + 8, cy + 4), 2)  # mouth

        # Banner/shield
        sp = shield_points((inner.right - 52, inner.centery), 34)
        pygame.draw.polygon(surface, (150, 40, 40), sp)
        pygame.draw.polygon(surface, (235, 228, 210), sp, 1)
        pygame.draw.line(surface, (235, 228, 210), (inner.right - 62, inner.centery - 22), (inner.right - 62, inner.centery + 22), 4)
        pygame.draw.line(surface, (235, 228, 210), (inner.right - 42, inner.centery - 22), (inner.right - 42, inner.centery + 22), 4)

        draw_footer_text(surface, state["character"]["house"], inner.left + 10, inner.bottom - 18, color=(200, 190, 175))

    def draw_right_panel(self, surface, rect, state):
        content = draw_framed_panel(surface, rect, title="Province / Realm", title_color=INK, tile=self.panel_tile)
        y = content.top

        sel = state["selected_province"]
        hov = state["hover_province"]

        if sel is None:
            y = draw_body_text(surface, "No province selected.", content.left, y, color=(205, 198, 180))
            y = draw_footer_text(surface, "Click a province on the map to inspect it.", content.left, y, color=(155, 150, 140))
            y += 10
        else:
            name = sel.name
            y = draw_header_text(surface, name, content.left, y, color=(235, 228, 210))
            y = draw_body_text(surface, f"Culture: {sel.culture}", content.left, y, color=(205, 198, 180))
            y = draw_body_text(surface, f"Faith: {sel.faith}", content.left, y, color=(205, 198, 180))
            y += 6

            pygame.draw.line(surface, (0, 0, 0), (content.left, y), (content.right, y))
            pygame.draw.line(surface, (80, 74, 66), (content.left, y + 1), (content.right, y + 1))
            y += 10

            y = draw_body_text(surface, f"Income: {sel.income} / mo", content.left, y, color=(220, 214, 198))
            y = draw_body_text(surface, f"Levies: {sel.levy}", content.left, y, color=(220, 214, 198))
            y = draw_body_text(surface, f"Control: {sel.control}%", content.left, y, color=(220, 214, 198))
            y += 10

            y = draw_header_text(surface, "Holdings", content.left, y, color=(230, 224, 208))
            holdings = ["Castle", "City", "Temple"] if not sel.is_water else ["Harbor", "Anchorage"]
            for i, hname in enumerate(holdings):
                tag = " (capital)" if i == 0 and not sel.is_water else ""
                y = draw_body_text(surface, f"• {hname}{tag}", content.left, y, color=(205, 198, 180))

            y += 10
            y = draw_header_text(surface, "Actions", content.left, y, color=(230, 224, 208))
            y = draw_footer_text(surface, "These are placeholders; wiring them is game-specific.", content.left, y, color=(150, 145, 138))
            y += 6

        # Quick hover readout
        if hov is not None:
            y2 = rect.bottom - 78
            box = pygame.Rect(content.left, y2, content.w, 62)
            pygame.draw.rect(surface, (20, 20, 20), box, border_radius=8)
            pygame.draw.rect(surface, (0, 0, 0), box, 2, border_radius=8)
            draw_footer_text(surface, "Hover", box.left + 10, box.top + 8, color=(165, 160, 150))
            draw_body_text(surface, hov.name, box.left + 10, box.top + 24, color=(235, 228, 210))

        # Buttons at bottom
        btns = []
        bx = content.left
        by = rect.bottom - 56
        b1 = draw_secondary_button(surface, "View Realm", bx, by, 120, 34)
        b2 = draw_primary_button(surface, "Set Rally", bx + 130, by, 120, 34)
        b3 = draw_secondary_button(surface, "Council", bx + 260, by, 120, 34)
        btns.append((b1, "view_realm"))
        btns.append((b2, "set_rally"))
        btns.append((b3, "council"))
        return btns

    def draw_bottom_bar(self, surface, rect, state):
        pygame.draw.rect(surface, (14, 14, 14), rect)
        tile_fill(surface, rect, self.bottom_tile)
        pygame.draw.line(surface, (90, 86, 78), (rect.left, rect.top), (rect.right, rect.top))
        pygame.draw.line(surface, (0, 0, 0), (rect.left, rect.top + 1), (rect.right, rect.top + 1))

        # Corner buttons (CK-like menu strip)
        btns = []
        x = rect.left + UI_GUTTER
        y = rect.top + 12
        bw = 96
        bh = 34
        for label, action in [("Menu", "open_menu"), ("Ledger", "ledger"), ("Realm", "realm"), ("Military", "military")]:
            r = draw_secondary_button(surface, label, x, y, bw, bh)
            btns.append((r, action))
            x += bw + 10

        x2 = rect.right - UI_GUTTER - (bw + 10) * 2
        for label, action in [("Decisions", "decisions"), ("Court", "court")]:
            r = draw_secondary_button(surface, label, x2, y, bw + 20, bh)
            btns.append((r, action))
            x2 += bw + 30

        # Message log window
        log_rect = pygame.Rect(rect.left + UI_GUTTER, rect.top + 54, rect.w - UI_GUTTER * 2, rect.h - 62)
        pygame.draw.rect(surface, (20, 20, 20), log_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), log_rect, 2, border_radius=8)

        lx = log_rect.left + 10
        ly = log_rect.top + 8
        for line in state["log"][-3:]:
            ly = draw_footer_text(surface, line, lx, ly, color=(205, 198, 180))

        return btns


class GameApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.ui = UIManager(seed=11)
        self.layout = Layout(*self.screen.get_size())

        self.world = MapWorld(seed=7, size=(3200, 2200), cols=18, rows=12)
        self.camera = Camera(self.world.size, self.layout.map.size)

        self.modal = Modal()

        self.date = GameDate(1067, 1, 21)
        self.speed_level = 0  # 0 paused, 1..3 speeds
        self.speed_days_per_sec = {0: 0, 1: 1, 2: 3, 3: 7}
        self._time_accum = 0.0

        self.selected_province = None
        self.hover_province = None

        self.resources = {"gold": 489, "prestige": 100, "piety": 100}
        self.character = {
            "name": "King Sancho II",
            "title": "King of Aragon • Defender of the Pyrenees",
            "house": "House de Aragón",
            "stats": [
                ("Diplomacy", 7), ("Martial", 11),
                ("Stewardship", 8), ("Intrigue", 6),
                ("Learning", 9), ("Prowess", 10),
            ],
        }
        self.army = {"raised": 928, "max": 1712, "morale": 77}

        self.log = [
            "January 8, 1067: Rumors of usurpation spread in Carinthia.",
            "January 11, 1067: A distant court recognizes new claims.",
            "January 18, 1067: A master of arms returns from pilgrimage.",
        ]

        # map interaction
        self._mouse_down_in_map = False
        self._mouse_down_pos = (0, 0)
        self._mouse_drag_threshold = 5

        self.running = True

    def push_log(self, text):
        self.log.append(text)
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def toggle_pause(self):
        if self.speed_level == 0:
            self.speed_level = 1
            self.push_log("Time resumes.")
        else:
            self.speed_level = 0
            self.push_log("Time paused.")

    def set_speed(self, level):
        self.speed_level = level
        if level == 0:
            self.push_log("Time paused.")
        else:
            self.push_log(f"Time speed set to {level}.")

    def open_menu(self):
        self.modal.show(
            "Game Menu",
            [
                "This is a functional UI modal (no assets) to demonstrate real flow.",
                "Exit cleanly to desktop, or close to return to the map."
            ],
            [
                ("Close", "secondary", lambda: self.modal.close()),
                ("Exit", "deny", lambda: self._exit_game()),
            ]
        )

    def _exit_game(self):
        self.running = False

    def _handle_action(self, action):
        if action == "toggle_pause":
            self.toggle_pause()
        elif action == "speed_1":
            self.set_speed(1)
        elif action == "speed_2":
            self.set_speed(2)
        elif action == "speed_3":
            self.set_speed(3)
        elif action == "open_menu":
            self.open_menu()
        elif action in ("ledger", "realm", "military", "decisions", "court", "council", "view_realm", "set_rally", "raise_army", "rally", "disband"):
            self.modal.show(
                "Not Implemented",
                [
                    f"'{action}' is a placeholder action.",
                    "The UI is fully functional; game logic can be connected here."
                ],
                [
                    ("OK", "accept", lambda: self.modal.close())
                ]
            )

    def _update_time(self, dt):
        days_per_sec = self.speed_days_per_sec.get(self.speed_level, 0)
        if days_per_sec <= 0:
            return
        self._time_accum += dt * days_per_sec
        whole = int(self._time_accum)
        if whole > 0:
            self.date.advance_days(whole)
            self._time_accum -= whole
            # small, gentle resource drift for life
            self.resources["gold"] += 1 if (self.date.day % 3 == 0) else 0

    def _map_controls(self, dt):
        keys = pygame.key.get_pressed()
        if self.modal.open:
            return

        # Keyboard panning (weighty due to camera smoothing)
        pan_speed = 720.0 / max(self.camera.target_zoom, 0.001)
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= pan_speed * dt
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += pan_speed * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= pan_speed * dt
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += pan_speed * dt
        if dx != 0.0 or dy != 0.0:
            self.camera.pan(dx, dy)

        # +/- zoom
        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            mx, my = pygame.mouse.get_pos()
            if self.layout.map.collidepoint((mx, my)):
                self.camera.zoom_at(1.03, (mx, my), self.layout.map)
        if keys[pygame.K_MINUS]:
            mx, my = pygame.mouse.get_pos()
            if self.layout.map.collidepoint((mx, my)):
                self.camera.zoom_at(0.97, (mx, my), self.layout.map)

    def _draw_map(self, surface):
        map_rect = self.layout.map

        # Map frame
        frame_rect = map_rect.inflate(12, 12)
        draw_drop_shadow(surface, frame_rect, strength=140, inflate=8, radius=12)
        pygame.draw.rect(surface, PANEL_OUTER, frame_rect, border_radius=12)
        pygame.draw.rect(surface, (0, 0, 0), frame_rect, 2, border_radius=12)
        pygame.draw.line(surface, BEVEL_LIGHT, (frame_rect.left+2, frame_rect.top+2), (frame_rect.right-3, frame_rect.top+2))
        pygame.draw.line(surface, BEVEL_LIGHT, (frame_rect.left+2, frame_rect.top+2), (frame_rect.left+2, frame_rect.bottom-3))
        pygame.draw.line(surface, BEVEL_DARK, (frame_rect.left+2, frame_rect.bottom-3), (frame_rect.right-3, frame_rect.bottom-3))
        pygame.draw.line(surface, BEVEL_DARK, (frame_rect.right-3, frame_rect.top+2), (frame_rect.right-3, frame_rect.bottom-3))

        # View render
        view = pygame.Surface(map_rect.size).convert()
        view.fill(SEA_DEEP)

        self.camera.set_viewport(map_rect.size)
        vrect = self.camera.view_rect(use_target=False)

        world_rect = pygame.Rect(0, 0, self.world.size[0], self.world.size[1])
        inter = vrect.clip(world_rect)

        if inter.w > 0 and inter.h > 0:
            subs = self.world.surface.subsurface(inter).copy()

            # Scale to screen portion
            z = self.camera.zoom
            scaled_w = max(1, int(round(inter.w * z)))
            scaled_h = max(1, int(round(inter.h * z)))

            if inter.size == map_rect.size and abs(z - 1.0) < 0.001:
                scaled = subs
            else:
                # smoothscale for polish
                scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))

            dx = int(round((inter.left - vrect.left) * z))
            dy = int(round((inter.top - vrect.top) * z))
            view.blit(scaled, (dx, dy))

        # Subtle map overlay/vignette
        draw_vignette(view, view.get_rect(), strength=85)

        # Province highlights
        def draw_highlight(prov, fill_alpha, border_alpha):
            if prov is None:
                return
            pts = []
            for (wx, wy) in prov.poly:
                sp = self.camera.world_to_screen((wx, wy), map_rect, use_target=False)
                pts.append((int(sp.x - map_rect.left), int(sp.y - map_rect.top)))
            # fill
            fill = pygame.Surface(map_rect.size, pygame.SRCALPHA)
            col = (200, 190, 160, fill_alpha) if not prov.is_water else (150, 170, 210, fill_alpha)
            pygame.draw.polygon(fill, col, pts)
            view.blit(fill, (0, 0))
            # border
            pygame.draw.lines(view, (235, 228, 210, border_alpha), True, pts, width=2)

        draw_highlight(self.selected_province, fill_alpha=55, border_alpha=210)
        if self.hover_province is not None and self.hover_province != self.selected_province:
            draw_highlight(self.hover_province, fill_alpha=30, border_alpha=140)

        # Tooltip plate (in-map)
        if self.hover_province is not None:
            tip = self.hover_province.name
            tip2 = "Sea Zone" if self.hover_province.is_water else f"Income {self.hover_province.income} • Levies {self.hover_province.levy}"
            plate = pygame.Rect(10, 10, min(420, map_rect.w - 20), 52)
            pygame.draw.rect(view, (18, 18, 18), plate, border_radius=10)
            pygame.draw.rect(view, (0, 0, 0), plate, 2, border_radius=10)
            draw_body_text(view, tip, plate.left + 12, plate.top + 8, color=(235, 228, 210))
            draw_footer_text(view, tip2, plate.left + 12, plate.top + 28, color=(180, 175, 165))

        surface.blit(view, map_rect.topleft)

        # Map corner compass (purely aesthetic)
        cx, cy = map_rect.right - 46, map_rect.bottom - 46
        pygame.draw.circle(surface, (18, 18, 18), (cx, cy), 20)
        pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 20, 2)
        pygame.draw.line(surface, (220, 214, 198), (cx, cy - 14), (cx, cy + 14), 1)
        pygame.draw.line(surface, (220, 214, 198), (cx - 14, cy), (cx + 14, cy), 1)
        draw_footer_text(surface, "N", cx - 5, cy - 32, color=(220, 214, 198))

    def _update_hover(self):
        mx, my = pygame.mouse.get_pos()
        if self.layout.map.collidepoint((mx, my)):
            wp = self.camera.screen_to_world((mx, my), self.layout.map, use_target=False)
            self.hover_province = self.world.province_at_world(wp)
        else:
            self.hover_province = None

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                elif event.type == pygame.VIDEORESIZE:
                    w = max(1024, event.w)
                    h = max(640, event.h)
                    self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                    self.layout.update(w, h)
                    self.camera.set_viewport(self.layout.map.size)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.modal.open:
                            self.modal.close()
                        else:
                            self.open_menu()
                    elif event.key == pygame.K_SPACE:
                        if not self.modal.open:
                            self.toggle_pause()

                # Mouse wheel zoom (pygame 2)
                elif event.type == pygame.MOUSEWHEEL and not self.modal.open:
                    mx, my = pygame.mouse.get_pos()
                    if self.layout.map.collidepoint((mx, my)):
                        factor = 1.12 if event.y > 0 else 0.89
                        self.camera.zoom_at(factor, (mx, my), self.layout.map)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.modal.open:
                            # modal button handling happens via returned button list on draw
                            pass
                        else:
                            if self.layout.map.collidepoint(event.pos):
                                self._mouse_down_in_map = True
                                self._mouse_down_pos = event.pos
                                self.camera.begin_drag(event.pos)

                    # Fallback wheel events (older style 4/5)
                    if not self.modal.open and self.layout.map.collidepoint(event.pos):
                        if event.button == 4:
                            self.camera.zoom_at(1.12, event.pos, self.layout.map)
                        elif event.button == 5:
                            self.camera.zoom_at(0.89, event.pos, self.layout.map)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        # Click dispatch (modal has priority)
                        if self.modal.open:
                            # modal clicks resolved after draw; store event and resolve immediately by redrawing buttons
                            pass
                        else:
                            if self._mouse_down_in_map:
                                self.camera.end_drag()
                                moved = (abs(event.pos[0] - self._mouse_down_pos[0]) + abs(event.pos[1] - self._mouse_down_pos[1]))
                                if moved <= self._mouse_drag_threshold and self.layout.map.collidepoint(event.pos):
                                    wp = self.camera.screen_to_world(event.pos, self.layout.map, use_target=False)
                                    prov = self.world.province_at_world(wp)
                                    if prov is not None:
                                        self.selected_province = prov
                                        self.push_log(f"{self.date}: Selected {prov.name}.")
                                self._mouse_down_in_map = False

                elif event.type == pygame.MOUSEMOTION:
                    if not self.modal.open and self._mouse_down_in_map:
                        self.camera.drag_to(event.pos)

            # Continuous controls
            self._map_controls(dt)

            # Time + camera easing
            self._update_time(dt)
            self.camera.update(dt)

            # Hover detection
            self._update_hover()

            # Draw
            self.screen.fill(BG_COLOR)

            # Decorative background panels behind everything
            bg = pygame.Surface(self.screen.get_size())
            bg.fill(BG_COLOR)
            # subtle mottled noise
            tile = self.ui.bottom_tile
            tile_fill(bg, bg.get_rect(), tile)
            bg.set_alpha(70)
            self.screen.blit(bg, (0, 0))

            # Map
            self._draw_map(self.screen)

            # UI panels
            state = {
                "date": self.date,
                "resources": self.resources,
                "speed_level": self.speed_level,
                "character": self.character,
                "army": self.army,
                "selected_province": self.selected_province,
                "hover_province": self.hover_province,
                "log": self.log,
            }

            clickables = []
            clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state))
            clickables.extend(self.ui.draw_left_panel(self.screen, self.layout.left, state))
            clickables.extend(self.ui.draw_right_panel(self.screen, self.layout.right, state))
            clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state))

            # Modal on top
            modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)

            # Resolve clicks (simple immediate dispatch based on current mouse state)
            if pygame.mouse.get_pressed(num_buttons=3)[0]:
                # wait for release to avoid repeat
                pass
            else:
                # Consume click on MOUSEBUTTONUP by checking if we released recently:
                # We'll approximate by checking event queue is empty and mouse was released;
                # actual dispatch uses MOUSEBUTTONUP events, but modal needs immediate list.
                # So we read the last MOUSEBUTTONUP in the queue would have already been handled.
                # To keep deterministic, we instead bind dispatch to current "just released" is hard
                # without a state flag; we keep robust behavior by using pygame.event.peek.
                pass

            # If a left-click release happened, handle it here using event queue peek is unreliable;
            # Instead, implement a small edge-triggered detector:
            # We'll do it using pygame.mouse.get_pressed and a stored previous state.
            if not hasattr(self, "_prev_mouse_down"):
                self._prev_mouse_down = False
            now_down = pygame.mouse.get_pressed(num_buttons=3)[0]
            if self._prev_mouse_down and (not now_down):
                mx, my = pygame.mouse.get_pos()
                if self.modal.open:
                    for r, cb in modal_clickables:
                        if r.collidepoint((mx, my)):
                            cb()
                            break
                else:
                    for r, action in clickables:
                        if r.collidepoint((mx, my)):
                            self._handle_action(action)
                            break
            self._prev_mouse_down = now_down

            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    GameApp().run()
