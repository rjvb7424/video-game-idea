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
# Helpers / Style
# =========================

UI_GUTTER = 10
TOP_BAR_H = 60
BOTTOM_BAR_H = 98
SIDE_W_L = 310
SIDE_W_R = 310

PANEL_OUTER = (18, 18, 19)
PANEL_INNER = (34, 34, 36)
PANEL_INNER_2 = (41, 41, 43)
BEVEL_LIGHT = (86, 86, 92)
BEVEL_DARK = (10, 10, 10)

INK = (222, 218, 206)

# Map palette (subdued, CK1-ish)
SEA_DEEP = (10, 22, 40)
SEA_SHALLOWS = (18, 38, 64)
COAST_FOAM = (90, 110, 120)

LAND_GREEN = (70, 86, 58)
LAND_DRY = (92, 86, 60)
LAND_RICH = (88, 98, 70)
HILLS = (84, 82, 70)
MOUNTAIN = (88, 86, 84)
FOREST = (54, 70, 46)

FOG_DARK = (12, 12, 14)
BORDER_INK_DARK = (12, 12, 12)
BORDER_INK = (32, 30, 28)
BORDER_REALM_INK = (8, 8, 8)

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

def exp_smooth_t(sharpness, dt):
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
    draw_drop_shadow(surface, rect, strength=120, inflate=7, radius=10)
    pygame.draw.rect(surface, PANEL_OUTER, rect, border_radius=10)

    pygame.draw.rect(surface, BEVEL_DARK, rect, width=2, border_radius=10)
    pygame.draw.line(surface, BEVEL_LIGHT, (rect.left+2, rect.top+2), (rect.right-3, rect.top+2))
    pygame.draw.line(surface, BEVEL_LIGHT, (rect.left+2, rect.top+2), (rect.left+2, rect.bottom-3))
    pygame.draw.line(surface, BEVEL_DARK, (rect.left+2, rect.bottom-3), (rect.right-3, rect.bottom-3))
    pygame.draw.line(surface, BEVEL_DARK, (rect.right-3, rect.top+2), (rect.right-3, rect.bottom-3))

    inner = rect.inflate(-14, -14)
    pygame.draw.rect(surface, PANEL_INNER, inner, border_radius=8)
    if tile is not None:
        tile_fill(surface, inner, tile)
        veil = pygame.Surface(inner.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 22))
        surface.blit(veil, inner.topleft)

    pygame.draw.rect(surface, (12, 12, 12), inner, width=1, border_radius=8)

    rivet_col = (66, 62, 56)
    for px, py in [(rect.left+14, rect.top+14), (rect.right-14, rect.top+14), (rect.left+14, rect.bottom-14), (rect.right-14, rect.bottom-14)]:
        pygame.draw.circle(surface, rivet_col, (px, py), 3)
        pygame.draw.circle(surface, (18, 18, 18), (px+1, py+1), 3, 1)

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

def draw_vignette(surface, rect, strength=85):
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


# =========================
# Systems: Date / Camera
# =========================

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
        t = exp_smooth_t(10.0, dt)  # deliberate, weighty
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


# =========================
# Map: Organic Continent + Provinces + Realms + Fog-of-War
# =========================

class Province:
    def __init__(self, pid, name):
        self.id = pid
        self.name = name
        self.realm_id = 0
        self.center = pygame.Vector2(0, 0)
        self.bounds_cells = pygame.Rect(0, 0, 1, 1)
        self.cell_count = 0

        self.income = 1 + (pid % 5)
        self.levy = 120 + (pid * 9) % 520
        self.control = 55 + (pid * 3) % 45
        self.culture = ["Frankish", "Occitan", "Iberian", "Germanic", "Slavic"][pid % 5]
        self.faith = ["Catholic", "Orthodox", "Pagan", "Sunni", "Mozarabic"][pid % 5]


def _value_noise_2d(w, h, cell_w, cell_h, seed):
    rnd = random.Random(seed)
    gw = max(2, int(math.ceil(w / cell_w)) + 1)
    gh = max(2, int(math.ceil(h / cell_h)) + 1)
    grid = [[rnd.random() for _ in range(gw)] for __ in range(gh)]

    out = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        gy = y / cell_h
        y0 = int(gy)
        ty = gy - y0
        y0 = clamp(y0, 0, gh - 2)
        y1 = y0 + 1
        for x in range(w):
            gx = x / cell_w
            x0 = int(gx)
            tx = gx - x0
            x0 = clamp(x0, 0, gw - 2)
            x1 = x0 + 1

            a = grid[y0][x0]
            b = grid[y0][x1]
            c = grid[y1][x0]
            d = grid[y1][x1]
            ab = a + (b - a) * tx
            cd = c + (d - c) * tx
            out[y][x] = ab + (cd - ab) * ty
    return out

def _blur_1d_h(arr, w, h):
    out = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        row = arr[y]
        for x in range(w):
            a = row[max(0, x - 1)]
            b = row[x]
            c = row[min(w - 1, x + 1)]
            out[y][x] = (a + b + c) / 3.0
    return out

def _blur_1d_v(arr, w, h):
    out = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        y0 = max(0, y - 1)
        y1 = y
        y2 = min(h - 1, y + 1)
        for x in range(w):
            out[y][x] = (arr[y0][x] + arr[y1][x] + arr[y2][x]) / 3.0
    return out

def _connected_components(mask, w, h):
    visited = [[False for _ in range(w)] for __ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if visited[y][x] or (not mask[y][x]):
                continue
            q = [(x, y)]
            visited[y][x] = True
            cells = []
            while q:
                cx, cy = q.pop()
                cells.append((cx, cy))
                for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                    if 0 <= nx < w and 0 <= ny < h and (not visited[ny][nx]) and mask[ny][nx]:
                        visited[ny][nx] = True
                        q.append((nx, ny))
            comps.append(cells)
    comps.sort(key=len, reverse=True)
    return comps

def _dilate_points(points, w, h, radius=1):
    out = set()
    for (x, y) in points:
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                nx, ny = x+dx, y+dy
                if 0 <= nx < w and 0 <= ny < h:
                    out.add((nx, ny))
    return out

def _mix_color(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )

def _apply_fog(rgb, visibility):
    # visibility: 1.0 (fully visible) -> no fog
    #            0.8 (adjacent)      -> mild fog
    #            0.45 (unknown)      -> heavy fog
    if visibility >= 0.999:
        return rgb
    fog_strength = clamp((1.0 - visibility) * 0.95, 0.0, 0.78)
    return _mix_color(rgb, FOG_DARK, fog_strength)

class MapWorld:
    def __init__(self, seed=7, world_size=(3200, 2200), cell_scale=8):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.world_w, self.world_h = world_size
        self.cell_scale = cell_scale

        # low-res grid resolution
        self.gw = self.world_w // self.cell_scale
        self.gh = self.world_h // self.cell_scale

        self.surface = pygame.Surface((self.world_w, self.world_h)).convert()
        self.base_surface = pygame.Surface((self.world_w, self.world_h)).convert()
        self.border_surface = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)

        self.land = [[False for _ in range(self.gw)] for __ in range(self.gh)]
        self.height = [[0.0 for _ in range(self.gw)] for __ in range(self.gh)]
        self.prov_id = [[-1 for _ in range(self.gw)] for __ in range(self.gh)]
        self.provinces = []
        self.realm_names = []
        self.realm_colors = []

        self.player_realm_id = 0
        self.visibility_by_prov = {}

        # UI-ish textures / overlay noise
        self.paper_tile = make_noise_tile((64, 64), (24, 24, 24), variance=10, alpha=255, seed=seed + 555)

        self._generate()

    def _name(self):
        a = ["Al", "Bel", "Car", "Dor", "Er", "Fen", "Gar", "Hal", "Ish", "Jar", "Kor", "Lor", "Mor", "Nor", "Or", "Pra", "Quel", "Ros", "San", "Tor", "Ul", "Var"]
        b = ["a", "e", "i", "o", "u", "ae", "ia", "oa"]
        c = ["don", "bar", "mont", "ford", "wick", "mere", "gard", "heim", "hold", "grad", "port", "cester", "vale", "mark", "burg"]
        return self.rnd.choice(a) + self.rnd.choice(b) + self.rnd.choice(c)

    def _generate_continent_height(self):
        w, h = self.gw, self.gh
        cx, cy = w * 0.52, h * 0.52

        # Value noise layers
        n1 = _value_noise_2d(w, h, cell_w=26, cell_h=26, seed=self.seed + 10)
        n2 = _value_noise_2d(w, h, cell_w=12, cell_h=12, seed=self.seed + 20)

        # Main continent blobs
        blobs = []
        blobs.append((cx, cy, min(w, h) * 0.34, 1.00))
        for _ in range(7):
            bx = self.rnd.uniform(w * 0.18, w * 0.82)
            by = self.rnd.uniform(h * 0.20, h * 0.80)
            br = self.rnd.uniform(min(w, h) * 0.11, min(w, h) * 0.20)
            ba = self.rnd.uniform(0.45, 0.95)
            blobs.append((bx, by, br, ba))

        # Smaller islands
        islands = []
        for _ in range(10):
            bx = self.rnd.uniform(w * 0.12, w * 0.88)
            by = self.rnd.uniform(h * 0.12, h * 0.88)
            br = self.rnd.uniform(min(w, h) * 0.04, min(w, h) * 0.07)
            ba = self.rnd.uniform(0.25, 0.55)
            islands.append((bx, by, br, ba))

        for y in range(h):
            for x in range(w):
                # radial falloff (forces water edges)
                dx = (x - cx) / (w * 0.56)
                dy = (y - cy) / (h * 0.56)
                radial = 1.0 - math.sqrt(dx*dx + dy*dy)
                radial = clamp(radial, -0.8, 1.0)

                v = radial * 0.78
                # add blobs (gaussian-ish)
                for (bx, by, br, ba) in blobs:
                    d2 = (x - bx) ** 2 + (y - by) ** 2
                    v += ba * math.exp(-d2 / (2.0 * br * br))
                for (bx, by, br, ba) in islands:
                    d2 = (x - bx) ** 2 + (y - by) ** 2
                    v += ba * math.exp(-d2 / (2.0 * br * br))

                # noise
                v += (n1[y][x] - 0.5) * 0.40
                v += (n2[y][x] - 0.5) * 0.22

                self.height[y][x] = v

        # Smooth for organic coastline
        for _ in range(2):
            self.height = _blur_1d_v(_blur_1d_h(self.height, w, h), w, h)

        # Normalize into ~0..1-ish range
        lo = min(min(row) for row in self.height)
        hi = max(max(row) for row in self.height)
        span = max(1e-6, hi - lo)
        for y in range(h):
            for x in range(w):
                self.height[y][x] = (self.height[y][x] - lo) / span

    def _build_land_mask(self):
        w, h = self.gw, self.gh
        # threshold tuned to produce a dominant continent
        threshold = 0.52
        raw = [[self.height[y][x] > threshold for x in range(w)] for y in range(h)]
        comps = _connected_components(raw, w, h)
        if not comps:
            # fallback (shouldn't happen)
            for y in range(h):
                for x in range(w):
                    self.land[y][x] = False
            return

        main = comps[0]
        main_set = set(main)

        # keep main continent + a few islands big enough
        keep = set(main)
        for comp in comps[1:]:
            if len(comp) >= 70:  # sizable island
                keep.update(comp)

        for y in range(h):
            for x in range(w):
                self.land[y][x] = (x, y) in keep

    def _pick_province_seeds(self, land_cells, target_count):
        # Poisson-ish spacing in cell coordinates
        min_dist = max(6, int(math.sqrt((len(land_cells) / max(1, target_count))) * 0.55))
        seeds = []
        attempts = 0
        max_attempts = 90000

        while len(seeds) < target_count and attempts < max_attempts:
            attempts += 1
            x, y = land_cells[self.rnd.randrange(len(land_cells))]
            ok = True
            for sx, sy in seeds:
                dx = x - sx
                dy = y - sy
                if dx*dx + dy*dy < min_dist * min_dist:
                    ok = False
                    break
            if ok:
                seeds.append((x, y))

        # If spacing was too strict, fill remaining without spacing
        while len(seeds) < target_count:
            seeds.append(land_cells[self.rnd.randrange(len(land_cells))])
        return seeds

    def _assign_provinces_region_growth(self):
        w, h = self.gw, self.gh

        land_cells = [(x, y) for y in range(h) for x in range(w) if self.land[y][x]]
        land_n = len(land_cells)
        # province count scales with land area
        scale_factor = (self.cell_scale / 8.0) ** 2   # 1.0 at 8, 0.25 at 4
        target = clamp(int((land_n * scale_factor) // 720), 55, 95)

        seeds = self._pick_province_seeds(land_cells, target)
        prov_count = len(seeds)

        # init
        for y in range(h):
            for x in range(w):
                self.prov_id[y][x] = -1

        q = []
        for pid, (sx, sy) in enumerate(seeds):
            self.prov_id[sy][sx] = pid
            q.append((sx, sy))

        # multi-source BFS (4-neigh) for contiguous provinces
        head = 0
        while head < len(q):
            x, y = q[head]
            head += 1
            pid = self.prov_id[y][x]
            for nx, ny in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):
                if 0 <= nx < w and 0 <= ny < h and self.land[ny][nx] and self.prov_id[ny][nx] == -1:
                    self.prov_id[ny][nx] = pid
                    q.append((nx, ny))

        # create province objects
        self.provinces = [Province(pid, self._name()) for pid in range(prov_count)]

        # collect cell lists + bounds + centers
        cell_lists = [[] for _ in range(prov_count)]
        mins = [(10**9, 10**9) for _ in range(prov_count)]
        maxs = [(-10**9, -10**9) for _ in range(prov_count)]
        sumx = [0 for _ in range(prov_count)]
        sumy = [0 for _ in range(prov_count)]
        cnt = [0 for _ in range(prov_count)]

        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue
                cell_lists[pid].append((x, y))
                mx, my = mins[pid]
                Mx, My = maxs[pid]
                mins[pid] = (min(mx, x), min(my, y))
                maxs[pid] = (max(Mx, x), max(My, y))
                sumx[pid] += x
                sumy[pid] += y
                cnt[pid] += 1

        # Merge tiny provinces for nicer shapes
        # Build adjacency counts on cell edges for small provinces
        def build_border_contacts():
            contacts = [dict() for _ in range(prov_count)]
            for y in range(h):
                for x in range(w):
                    a = self.prov_id[y][x]
                    if a < 0:
                        continue
                    if x + 1 < w:
                        b = self.prov_id[y][x+1]
                        if b >= 0 and b != a:
                            contacts[a][b] = contacts[a].get(b, 0) + 1
                            contacts[b][a] = contacts[b].get(a, 0) + 1
                    if y + 1 < h:
                        b = self.prov_id[y+1][x]
                        if b >= 0 and b != a:
                            contacts[a][b] = contacts[a].get(b, 0) + 1
                            contacts[b][a] = contacts[b].get(a, 0) + 1
            return contacts

        contacts = build_border_contacts()
        small_threshold = 95
        merged_into = [-1 for _ in range(prov_count)]

        for pid in range(prov_count):
            if cnt[pid] >= small_threshold:
                continue
            if not contacts[pid]:
                continue
            # merge into strongest neighbor
            best = max(contacts[pid].items(), key=lambda kv: kv[1])[0]
            merged_into[pid] = best

        # apply merges (single pass; good enough for this aesthetic)
        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid >= 0 and merged_into[pid] != -1:
                    self.prov_id[y][x] = merged_into[pid]

        # remap province IDs to compact range after merges
        used = sorted({self.prov_id[y][x] for y in range(h) for x in range(w) if self.prov_id[y][x] >= 0})
        remap = {old: i for i, old in enumerate(used)}
        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid >= 0:
                    self.prov_id[y][x] = remap[pid]

        # rebuild province list + metrics
        prov_count2 = len(used)
        self.provinces = [Province(pid, self._name()) for pid in range(prov_count2)]
        mins = [(10**9, 10**9) for _ in range(prov_count2)]
        maxs = [(-10**9, -10**9) for _ in range(prov_count2)]
        sumx = [0 for _ in range(prov_count2)]
        sumy = [0 for _ in range(prov_count2)]
        cnt = [0 for _ in range(prov_count2)]

        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue
                mx, my = mins[pid]
                Mx, My = maxs[pid]
                mins[pid] = (min(mx, x), min(my, y))
                maxs[pid] = (max(Mx, x), max(My, y))
                sumx[pid] += x
                sumy[pid] += y
                cnt[pid] += 1

        for pid in range(prov_count2):
            if cnt[pid] <= 0:
                continue
            self.provinces[pid].cell_count = cnt[pid]
            mx, my = mins[pid]
            Mx, My = maxs[pid]
            self.provinces[pid].bounds_cells = pygame.Rect(mx, my, (Mx - mx + 1), (My - my + 1))
            cx = (sumx[pid] / cnt[pid] + 0.5) * self.cell_scale
            cy = (sumy[pid] / cnt[pid] + 0.5) * self.cell_scale
            self.provinces[pid].center = pygame.Vector2(cx, cy)

    def _build_province_adjacency(self):
        w, h = self.gw, self.gh
        adj = [set() for _ in range(len(self.provinces))]
        for y in range(h):
            for x in range(w):
                a = self.prov_id[y][x]
                if a < 0:
                    continue
                if x + 1 < w:
                    b = self.prov_id[y][x+1]
                    if b >= 0 and b != a:
                        adj[a].add(b)
                        adj[b].add(a)
                if y + 1 < h:
                    b = self.prov_id[y+1][x]
                    if b >= 0 and b != a:
                        adj[a].add(b)
                        adj[b].add(a)
        return adj

    def _assign_realms(self):
        prov_n = len(self.provinces)
        adj = self._build_province_adjacency()

        # number of realms
        realm_n = clamp(prov_n // 10, 6, 9)

        # palette (subdued, distinct)
        palette = [
            (64, 80, 120),   # blue
            (92, 66, 102),   # purple
            (78, 96, 66),    # green
            (120, 84, 58),   # brown
            (70, 104, 104),  # teal
            (120, 70, 70),   # maroon
            (110, 110, 70),  # olive
            (86, 86, 110),   # slate
            (120, 92, 120),  # mauve
        ]
        self.realm_colors = palette[:realm_n]
        self.realm_names = [f"Kingdom of {self._name()}" for _ in range(realm_n)]

        # choose realm capitals with farthest sampling (on province centers)
        centers = [p.center for p in self.provinces]
        chosen = []
        # start near center
        wx, wy = self.world_w * 0.52, self.world_h * 0.52
        start = min(range(prov_n), key=lambda i: (centers[i].x-wx)**2 + (centers[i].y-wy)**2)
        chosen.append(start)
        while len(chosen) < realm_n:
            best = None
            best_d = -1
            for i in range(prov_n):
                if i in chosen:
                    continue
                dmin = min((centers[i].x - centers[c].x)**2 + (centers[i].y - centers[c].y)**2 for c in chosen)
                if dmin > best_d:
                    best_d = dmin
                    best = i
            chosen.append(best if best is not None else self.rnd.randrange(prov_n))

        # multi-source BFS on province graph
        realm_of = [-1 for _ in range(prov_n)]
        q = []
        for rid, cap in enumerate(chosen):
            realm_of[cap] = rid
            q.append(cap)

        head = 0
        while head < len(q):
            p = q[head]
            head += 1
            rid = realm_of[p]
            for nb in adj[p]:
                if realm_of[nb] == -1:
                    realm_of[nb] = rid
                    q.append(nb)

        # assign
        for pid, prov in enumerate(self.provinces):
            prov.realm_id = realm_of[pid]

        # player realm = realm whose capital is closest to center
        player_cap = chosen[0]
        self.player_realm_id = realm_of[player_cap]

    def _compute_fog_of_war(self):
        adj = self._build_province_adjacency()
        player_provs = {p.id for p in self.provinces if p.realm_id == self.player_realm_id}
        seen = set(player_provs)
        border = set(player_provs)
        for pid in player_provs:
            for nb in adj[pid]:
                border.add(nb)

        # visibility factors
        self.visibility_by_prov = {}
        for p in self.provinces:
            if p.id in seen:
                self.visibility_by_prov[p.id] = 1.00
            elif p.id in border:
                self.visibility_by_prov[p.id] = 0.80
            else:
                self.visibility_by_prov[p.id] = 0.45

    def _render_base(self):
        w, h = self.gw, self.gh

        # low-res color buffer
        low = pygame.Surface((w, h)).convert()
        px = pygame.PixelArray(low)

        # extra tiny noise for texture variation
        ntex = _value_noise_2d(w, h, cell_w=7, cell_h=7, seed=self.seed + 999)

        for y in range(h):
            for x in range(w):
                if not self.land[y][x]:
                    # sea depth based on height below threshold
                    d = clamp(1.0 - self.height[y][x], 0.0, 1.0)
                    sea = _mix_color(SEA_SHALLOWS, SEA_DEEP, d * 0.85)
                    dv = int((ntex[y][x] - 0.5) * 8)
                    sea = (clamp(sea[0] + dv, 0, 255), clamp(sea[1] + dv, 0, 255), clamp(sea[2] + dv, 0, 255))
                    px[x, y] = sea
                    continue

                pid = self.prov_id[y][x]
                if pid < 0:
                    px[x, y] = SEA_DEEP
                    continue

                prov = self.provinces[pid]
                rid = prov.realm_id
                realm_col = self.realm_colors[rid]

                ht = self.height[y][x]
                # terrain tint
                if ht > 0.82:
                    terrain = MOUNTAIN
                elif ht > 0.74:
                    terrain = HILLS
                else:
                    # forest pockets
                    forestiness = (ntex[y][x] * 0.7 + ht * 0.3)
                    terrain = FOREST if forestiness > 0.68 else (LAND_RICH if ht > 0.60 else (LAND_GREEN if ht > 0.54 else LAND_DRY))

                # mix realm with terrain (so kingdoms read as colored blocks, but not flat-modern)
                col = _mix_color(realm_col, terrain, 0.46)

                # micro shading
                dv = int((ntex[y][x] - 0.5) * 10)
                col = (clamp(col[0] + dv, 0, 255), clamp(col[1] + dv, 0, 255), clamp(col[2] + dv, 0, 255))

                # fog of war
                vis = self.visibility_by_prov.get(pid, 0.45)
                col = _apply_fog(col, vis)
                px[x, y] = col

        del px

        # scale up (keep provinces solid), then add subtle paper/noise veil
        self.base_surface = pygame.transform.smoothscale(low, (self.world_w, self.world_h)).convert()

        veil = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        tile_fill(veil, veil.get_rect(), self.paper_tile)
        veil.fill((0, 0, 0, 22), special_flags=pygame.BLEND_RGBA_MULT)
        self.base_surface.blit(veil, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def _render_borders_and_coast(self):
        w, h = self.gw, self.gh

        thin_border = []
        realm_border = []
        coast = []

        # scan edges to build low-res border point sets
        for y in range(h):
            for x in range(w):
                if not self.land[y][x]:
                    continue
                a = self.prov_id[y][x]
                if a < 0:
                    continue

                # coastline
                for nx, ny in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        if not self.land[ny][nx]:
                            coast.append((x, y))
                            break

                # province borders / realm borders (only check right & down to avoid duplicates)
                for nx, ny in ((x+1,y), (x,y+1)):
                    if 0 <= nx < w and 0 <= ny < h and self.land[ny][nx]:
                        b = self.prov_id[ny][nx]
                        if b >= 0 and b != a:
                            thin_border.append((x, y))
                            if self.provinces[a].realm_id != self.provinces[b].realm_id:
                                realm_border.append((x, y))

        thin_set = set(thin_border)
        realm_set = set(realm_border)
        coast_set = set(coast)

        # --- KEY QUALITY BOOST ---
        # render border masks at 2x the low-res grid, then smoothscale to world
        UPSCALE = 4
        w2, h2 = w * UPSCALE, h * UPSCALE

        def up_points(points):
            out = set()
            for (x, y) in points:
                ox, oy = x * UPSCALE, y * UPSCALE
                # fill the UPSCALE×UPSCALE block so scaling doesn't create gaps
                for dy in range(UPSCALE):
                    for dx in range(UPSCALE):
                        out.add((ox + dx, oy + dy))
            return out

        thin2 = up_points(thin_set)
        realm2 = up_points(realm_set)
        coast2 = up_points(coast_set)

        # dilate in the upscaled space for smoother thickness
        # keep them *thin*
        realm_thick2 = _dilate_points(realm2, w2, h2, radius=1) # tiny emphasis
        coast_thick2 = _dilate_points(coast2, w2, h2, radius=1)

        def make_mask(points, alpha=255):
            s = pygame.Surface((w2, h2), pygame.SRCALPHA)
            for (x, y) in points:
                s.set_at((x, y), (255, 255, 255, alpha))
            return s

        mask_thin = make_mask(thin2, alpha=190)   # was 255
        mask_realm = make_mask(realm_thick2, alpha=200)
        mask_coast = make_mask(coast_thick2, alpha=150)

        # smooth scale masks to world resolution (anti-aliased look)
        ms_thin = pygame.transform.smoothscale(mask_thin, (self.world_w, self.world_h))
        ms_realm = pygame.transform.smoothscale(mask_realm, (self.world_w, self.world_h))
        ms_coast = pygame.transform.smoothscale(mask_coast, (self.world_w, self.world_h))

        self.border_surface = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)

        # coastline foam (keep subtle)
        foam = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        foam.fill((*COAST_FOAM, 255))
        foam.blit(ms_coast, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.border_surface.blit(foam, (0, 0))

        # province borders: subtle ink (NO RED)
        thick_ink = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        thick_ink.fill((*BORDER_INK_DARK, 255))

        thin_ink = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        thin_ink.fill((*BORDER_INK, 255))
        thin_ink.blit(ms_thin, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # realm borders: slightly stronger ink
        realm_ink = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        realm_ink.fill((*BORDER_REALM_INK, 255))
        realm_ink.blit(ms_realm, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self.border_surface.blit(realm_ink, (0, 0))
        self.border_surface.blit(thin_ink, (0, 0))

    def _render_labels_and_markers(self):
        overlay = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)

        # draw realm shields on visible provinces
        for prov in self.provinces:
            vis = self.visibility_by_prov.get(prov.id, 0.45)
            if vis < 0.75:
                continue
            if prov.cell_count < 220:
                continue

            cx, cy = int(prov.center.x), int(prov.center.y)
            sp = shield_points((cx, cy), 26)
            base = self.realm_colors[prov.realm_id]
            a = 210 if vis > 0.95 else 150
            pygame.draw.polygon(overlay, (base[0], base[1], base[2], a), sp)
            pygame.draw.polygon(overlay, (235, 228, 210, 140), sp, 1)

        # labels only for seen + border provinces (no labels in deep fog)
        for prov in self.provinces:
            vis = self.visibility_by_prov.get(prov.id, 0.45)
            if vis < 0.78:
                continue
            if prov.cell_count < 280:
                continue

            label = FOOTER_FONT.render(prov.name, True, (225, 218, 200))
            label.set_alpha(135 if vis > 0.95 else 95)
            r = label.get_rect(center=(int(prov.center.x), int(prov.center.y)))
            overlay.blit(label, r)

        # a few "army" markers on player/adjacent provinces
        candidates = [p for p in self.provinces if self.visibility_by_prov.get(p.id, 0.45) >= 0.78 and p.cell_count > 220]
        for i in range(min(9, len(candidates))):
            p = self.rnd.choice(candidates)
            x = int(p.center.x + self.rnd.randint(-32, 32))
            y = int(p.center.y + self.rnd.randint(-32, 32))
            self._draw_army(overlay, (x, y), color=(200, 200, 210, 210))

        self.surface = self.base_surface.copy()
        self.surface.blit(self.border_surface, (0, 0))
        self.surface.blit(overlay, (0, 0))

    def _draw_army(self, surf, pos, color=(200, 200, 210, 200)):
        x, y = pos
        pygame.draw.circle(surf, color, (x, y), 4)
        pygame.draw.line(surf, color, (x, y+4), (x, y+14), 2)
        pygame.draw.polygon(surf, color, [(x, y+6), (x+10, y+8), (x, y+10)])
        pygame.draw.polygon(surf, (25, 20, 18, 160), [(x, y+6), (x+10, y+8), (x, y+10)], 1)

    def _generate(self):
        self._generate_continent_height()
        self._build_land_mask()
        self._assign_provinces_region_growth()
        self._assign_realms()
        self._compute_fog_of_war()
        self._render_base()
        self._render_borders_and_coast()
        self._render_labels_and_markers()

    def province_at_world(self, world_pos):
        x, y = int(world_pos[0]), int(world_pos[1])
        if x < 0 or y < 0 or x >= self.world_w or y >= self.world_h:
            return None
        gx = x // self.cell_scale
        gy = y // self.cell_scale
        if gx < 0 or gy < 0 or gx >= self.gw or gy >= self.gh:
            return None
        pid = self.prov_id[gy][gx]
        if pid < 0:
            return None
        return self.provinces[pid]

    def is_border_cell(self, gx, gy, pid):
        # for selection outline (fast local check)
        if pid < 0:
            return False
        for nx, ny in ((gx+1,gy), (gx-1,gy), (gx,gy+1), (gx,gy-1)):
            if 0 <= nx < self.gw and 0 <= ny < self.gh:
                other = self.prov_id[ny][nx]
                if other != pid:
                    return True
            else:
                return True
        return False


# =========================
# UI Layout / Modal / UI Manager
# =========================

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
        self.actions = []

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
            holdings = ["Castle", "City", "Temple"]
            for i, hname in enumerate(holdings):
                tag = " (capital)" if i == 0 else ""
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

        self.world = MapWorld(seed=7, world_size=(3200, 2200), cell_scale=4)  # was 8
        self.camera = Camera(viewport_size=(100, 100), world_size=(3200, 2200))

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

        world_rect = pygame.Rect(0, 0, 3200, 2200)
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

        # Tooltip plate (in-map)
        if self.hover_province is not None:
            tip = self.hover_province.name
            plate = pygame.Rect(10, 10, min(420, map_rect.w - 20), 52)
            pygame.draw.rect(view, (18, 18, 18), plate, border_radius=10)
            pygame.draw.rect(view, (0, 0, 0), plate, 2, border_radius=10)
            draw_body_text(view, tip, plate.left + 12, plate.top + 8, color=(235, 228, 210))

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
