import math
import random
import heapq
import collections
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

SEA_DEEP = (14, 26, 44)
SEA_SHALLOWS = (18, 38, 64)
BORDER_RED = (132, 30, 30)
BORDER_RED_DIM = (92, 22, 22)

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
        draw_header_text(surface, title, strip.left + 8, strip.top + 4, color=title_color)
        content = pygame.Rect(inner.left+8, strip.bottom+6, inner.w-16, inner.h - strip_h - 14)
    return content

def draw_vignette(surface, rect, strength=95):
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 0))
    cx, cy = rect.w / 2, rect.h / 2
    max_d = math.hypot(cx, cy)
    step = 16
    for r in range(0, int(max_d), step):
        a = int(clamp((r / max_d) ** 1.8 * strength, 0, strength))
        pygame.draw.circle(overlay, (0, 0, 0, a), (int(cx), int(cy)), r, width=step)
    surface.blit(overlay, rect.topleft)

def brighten(rgb, factor):
    r, g, b = rgb
    return (clamp(int(r * factor), 0, 255), clamp(int(g * factor), 0, 255), clamp(int(b * factor), 0, 255))

def fogged(rgb, factor=0.35):
    # Darken and bias slightly towards cold/ink
    r, g, b = rgb
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
    r = int(lerp(r, 18, 0.25))
    g = int(lerp(g, 20, 0.25))
    b = int(lerp(b, 28, 0.35))
    return (clamp(r, 0, 255), clamp(g, 0, 255), clamp(b, 0, 255))

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
# Game Date
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


# =========================
# Camera (weighty pan/zoom)
# =========================

class Camera:
    def __init__(self, world_size, viewport_size):
        self.world_w, self.world_h = world_size
        self.vp_w, self.vp_h = viewport_size

        self.center = pygame.Vector2(self.world_w * 0.52, self.world_h * 0.52)
        self.target_center = self.center.copy()

        self.zoom = 1.0
        self.target_zoom = 1.0
        self.min_zoom = 0.60
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
        t = exp_smooth_t(10.5, dt)
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
# Province + World Map Generation (Organic provinces, kingdoms, fog)
# =========================

class Province:
    def __init__(self, pid, name, kingdom_id, center_world, tiles_count):
        self.id = pid
        self.name = name
        self.kingdom_id = kingdom_id
        self.center = pygame.Vector2(center_world)
        self.tiles_count = tiles_count

        # Placeholder stats
        self.income = 1 + (pid % 6)
        self.levy = 120 + (pid * 11) % 600
        self.control = 55 + (pid * 3) % 45
        self.culture = ["Frankish", "Occitan", "Iberian", "Germanic", "Slavic"][pid % 5]
        self.faith = ["Catholic", "Orthodox", "Pagan", "Sunni", "Mozarabic"][pid % 5]


class MapWorld:
    """
    Tile-driven world:
    - Organic continent via blob field + smoothing + largest-component enforcement
    - Provinces via multi-source weighted growth on land tiles
    - Kingdoms via multi-source BFS on province adjacency graph (contiguous realms)
    - Fog of war baked into province color layer (player bright, neighbors visible, rest dark)
    """
    def __init__(self, seed=7, world_size=(3200, 2200), tile_size=10):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.world_w, self.world_h = world_size
        self.tile_size = tile_size

        self.tw = self.world_w // self.tile_size
        self.th = self.world_h // self.tile_size
        self.world_w = self.tw * self.tile_size
        self.world_h = self.th * self.tile_size

        # Small-scale fields
        self.height = [[0.0 for _ in range(self.th)] for _ in range(self.tw)]
        self.land = [[False for _ in range(self.th)] for _ in range(self.tw)]
        self.prov_id = [[-1 for _ in range(self.th)] for _ in range(self.tw)]

        self.provinces = []
        self.adj = {}  # pid -> set(pid)

        self.kingdom_count = 7
        self.kingdom_colors = [
            (60, 72, 112),   # blue
            (116, 70, 58),   # brick
            (72, 106, 78),   # green
            (136, 106, 58),  # gold-ish
            (90, 72, 116),   # purple
            (72, 108, 118),  # teal
            (132, 68, 100),  # wine
        ]

        # Player + fog
        self.player_kingdom = 0
        self.visible_provinces = set()
        self.owned_provinces = set()

        # Rendered surfaces
        self.terrain_world = pygame.Surface((self.world_w, self.world_h)).convert()
        self.province_world = pygame.Surface((self.world_w, self.world_h)).convert()
        self.border_world = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        self.ink_world = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        self.combined_world = pygame.Surface((self.world_w, self.world_h)).convert()

        # Textures
        self.sea_tile = make_noise_tile((96, 96), SEA_DEEP, variance=10, alpha=255, seed=seed + 100)
        self.land_tile = make_noise_tile((96, 96), (66, 76, 54), variance=12, alpha=255, seed=seed + 200)
        self.paper_tile = make_noise_tile((64, 64), (52, 52, 54), variance=10, alpha=255, seed=seed + 300)

        # Per-province cached label surfaces
        self._label_cache = {}

        self._generate()

    # ---------- Generation ----------
    def _generate(self):
        self._generate_continent_height()
        self._derive_landmask()
        self._smooth_land(iterations=5)
        self._keep_largest_landmass()

        land_tiles = sum(1 for x in range(self.tw) for y in range(self.th) if self.land[x][y])
        target_provinces = clamp(int(land_tiles / 560), 70, 160)

        seeds = self._pick_province_seeds(target_provinces)
        self._grow_provinces(seeds)
        self._build_province_objects()

        self._build_adjacency()
        self._assign_kingdoms_contiguous()
        self._pick_player_kingdom()
        self._build_visibility()

        self._render_world_layers()
        self._compose_world()

    def _generate_continent_height(self):
        cx = (self.tw - 1) / 2.0
        cy = (self.th - 1) / 2.0
        maxd = math.hypot(cx, cy)

        # Coarse noise (smoothed random)
        noise = [[self.rnd.random() for _ in range(self.th)] for _ in range(self.tw)]
        for _ in range(3):
            newn = [[0.0 for _ in range(self.th)] for _ in range(self.tw)]
            for x in range(self.tw):
                for y in range(self.th):
                    acc = 0.0
                    cnt = 0
                    for dx, dy in ((0,0), (1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)):
                        xx = x + dx
                        yy = y + dy
                        if 0 <= xx < self.tw and 0 <= yy < self.th:
                            acc += noise[xx][yy]
                            cnt += 1
                    newn[x][y] = acc / cnt
            noise = newn

        # Blob field (multiple gaussians)
        blobs = []
        for _ in range(10):
            bx = self.rnd.uniform(self.tw * 0.22, self.tw * 0.78)
            by = self.rnd.uniform(self.th * 0.24, self.th * 0.76)
            sigma = self.rnd.uniform(self.tw * 0.08, self.tw * 0.18)
            amp = self.rnd.uniform(0.45, 0.90)
            blobs.append((bx, by, sigma, amp))

        for x in range(self.tw):
            for y in range(self.th):
                d = math.hypot(x - cx, y - cy) / maxd
                radial = max(0.0, 1.0 - (d ** 1.35))  # pushes water at edges

                v = 0.55 * radial
                for bx, by, sigma, amp in blobs:
                    dd = math.hypot(x - bx, y - by)
                    v += amp * math.exp(-(dd * dd) / (2 * sigma * sigma))

                v += (noise[x][y] - 0.5) * 0.28
                self.height[x][y] = v

    def _derive_landmask(self):
        # Choose threshold automatically to get a decent continent size
        thresholds = [0.86, 0.80, 0.76, 0.72, 0.68, 0.64, 0.60, 0.56, 0.52, 0.48]
        chosen = thresholds[-1]

        for thv in thresholds:
            land_count = 0
            for x in range(self.tw):
                for y in range(self.th):
                    self.land[x][y] = self.height[x][y] >= thv
                    if self.land[x][y]:
                        land_count += 1
            if land_count >= int(self.tw * self.th * 0.28):
                chosen = thv
                break

        # Re-apply chosen threshold
        for x in range(self.tw):
            for y in range(self.th):
                self.land[x][y] = self.height[x][y] >= chosen

    def _smooth_land(self, iterations=4):
        for _ in range(iterations):
            newm = [[False for _ in range(self.th)] for _ in range(self.tw)]
            for x in range(self.tw):
                for y in range(self.th):
                    cnt = 0
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                        xx = x + dx
                        yy = y + dy
                        if 0 <= xx < self.tw and 0 <= yy < self.th and self.land[xx][yy]:
                            cnt += 1
                    if self.land[x][y]:
                        newm[x][y] = cnt >= 3
                    else:
                        newm[x][y] = cnt >= 6
            self.land = newm

    def _keep_largest_landmass(self):
        visited = [[False for _ in range(self.th)] for _ in range(self.tw)]
        best = []
        for x in range(self.tw):
            for y in range(self.th):
                if self.land[x][y] and not visited[x][y]:
                    comp = []
                    dq = collections.deque()
                    dq.append((x, y))
                    visited[x][y] = True
                    while dq:
                        cx, cy = dq.popleft()
                        comp.append((cx, cy))
                        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < self.tw and 0 <= ny < self.th and self.land[nx][ny] and not visited[nx][ny]:
                                visited[nx][ny] = True
                                dq.append((nx, ny))
                    if len(comp) > len(best):
                        best = comp

        keep = set(best)
        for x in range(self.tw):
            for y in range(self.th):
                if self.land[x][y] and (x, y) not in keep:
                    self.land[x][y] = False

    def _pick_province_seeds(self, n):
        # Rejection sampling to keep seeds spaced (prevents tiny sliver provinces)
        land_positions = [(x, y) for x in range(self.tw) for y in range(self.th) if self.land[x][y]]
        self.rnd.shuffle(land_positions)

        seeds = []
        min_dist = 9
        for (x, y) in land_positions:
            ok = True
            for sx, sy in seeds:
                if abs(x - sx) + abs(y - sy) < min_dist:
                    ok = False
                    break
            if ok:
                seeds.append((x, y))
            if len(seeds) >= n:
                break

        # fallback: if too strict
        while len(seeds) < n and land_positions:
            seeds.append(land_positions[len(seeds) % len(land_positions)])

        return seeds

    def _grow_provinces(self, seeds):
        # Dijkstra-like multi-source growth with tile noise weights for organic borders
        tile_noise = [[self.rnd.random() for _ in range(self.th)] for _ in range(self.tw)]
        for x in range(self.tw):
            for y in range(self.th):
                if not self.land[x][y]:
                    self.prov_id[x][y] = -1

        heap = []
        for pid, (sx, sy) in enumerate(seeds):
            self.prov_id[sx][sy] = pid
            heapq.heappush(heap, (0.0, pid, sx, sy))

        while heap:
            cost, pid, x, y = heapq.heappop(heap)
            if self.prov_id[x][y] != pid:
                continue
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.tw and 0 <= ny < self.th):
                    continue
                if not self.land[nx][ny]:
                    continue
                if self.prov_id[nx][ny] != -1:
                    continue
                # organic growth: base + subtle noise + tiny "ridge" effect from height gradients
                h0 = self.height[x][y]
                h1 = self.height[nx][ny]
                ridge = abs(h1 - h0) * 0.7
                ncost = cost + 1.0 + tile_noise[nx][ny] * 0.85 + ridge
                self.prov_id[nx][ny] = pid
                heapq.heappush(heap, (ncost, pid, nx, ny))

    def _province_name(self):
        a = ["AL", "BEL", "CAR", "DOR", "ER", "FEN", "GAR", "HAL", "ISH", "JAR", "KOR", "LOR", "MOR", "NOR", "OR", "PRA", "QUEL", "ROS", "SAN", "TOR", "UL", "VAR"]
        b = ["A", "E", "I", "O", "U", "AE", "IA", "OA"]
        c = ["DON", "BAR", "MONT", "FORD", "WICK", "MERE", "GARD", "HEIM", "HOLD", "GRAD", "PORT", "CESTER", "VALE", "MARK", "BURG", "RIA", "TARA"]
        return self.rnd.choice(a) + self.rnd.choice(b) + self.rnd.choice(c)

    def _build_province_objects(self):
        prov_tiles = collections.defaultdict(list)
        for x in range(self.tw):
            for y in range(self.th):
                pid = self.prov_id[x][y]
                if pid >= 0:
                    prov_tiles[pid].append((x, y))

        # temp kingdom id 0; will be assigned later
        self.provinces = []
        for pid, tiles in prov_tiles.items():
            sx = sum(t[0] for t in tiles) / len(tiles)
            sy = sum(t[1] for t in tiles) / len(tiles)
            cx = (sx + 0.5) * self.tile_size
            cy = (sy + 0.5) * self.tile_size
            prov = Province(pid, self._province_name(), 0, (cx, cy), len(tiles))
            self.provinces.append(prov)

        self.provinces.sort(key=lambda p: p.id)

    def _build_adjacency(self):
        self.adj = {p.id: set() for p in self.provinces}
        for x in range(self.tw - 1):
            for y in range(self.th - 1):
                a = self.prov_id[x][y]
                if a < 0:
                    continue
                r = self.prov_id[x+1][y]
                d = self.prov_id[x][y+1]
                if r >= 0 and r != a:
                    self.adj[a].add(r)
                    self.adj[r].add(a)
                if d >= 0 and d != a:
                    self.adj[a].add(d)
                    self.adj[d].add(a)

    def _assign_kingdoms_contiguous(self):
        # Multi-source BFS on province graph from K capitals (contiguous territories)
        pids = [p.id for p in self.provinces]
        self.rnd.shuffle(pids)
        capitals = pids[:self.kingdom_count]

        kingdom_of = {pid: -1 for pid in pids}
        q = collections.deque()
        for k, cap in enumerate(capitals):
            kingdom_of[cap] = k
            q.append(cap)

        # BFS expansion ensures contiguity
        while q:
            cur = q.popleft()
            k = kingdom_of[cur]
            neighbors = list(self.adj.get(cur, []))
            self.rnd.shuffle(neighbors)
            for nb in neighbors:
                if kingdom_of[nb] == -1:
                    kingdom_of[nb] = k
                    q.append(nb)

        for p in self.provinces:
            p.kingdom_id = kingdom_of[p.id]

        # Ensure we use available colors count
        self.kingdom_count = max(self.kingdom_count, 1)

    def _pick_player_kingdom(self):
        # Pick the kingdom with the most provinces for a "big realm" feel (more borders visible)
        counts = [0 for _ in range(self.kingdom_count)]
        for p in self.provinces:
            if 0 <= p.kingdom_id < self.kingdom_count:
                counts[p.kingdom_id] += 1
        self.player_kingdom = max(range(self.kingdom_count), key=lambda i: counts[i])
        self.owned_provinces = {p.id for p in self.provinces if p.kingdom_id == self.player_kingdom}

    def _build_visibility(self):
        # Visible: own provinces + 1-ring neighbors
        vis = set(self.owned_provinces)
        for pid in list(self.owned_provinces):
            for nb in self.adj.get(pid, []):
                vis.add(nb)
        self.visible_provinces = vis

    # ---------- Rendering ----------
    def _render_world_layers(self):
        # TERRAIN at tile resolution then scale
        terrain_small = pygame.Surface((self.tw, self.th)).convert()
        terrain_small.fill(SEA_DEEP)

        # Precompute distance-to-coast for nicer shallow seas / beaches
        coast_dist = [[9999 for _ in range(self.th)] for _ in range(self.tw)]
        dq = collections.deque()
        for x in range(self.tw):
            for y in range(self.th):
                if not self.land[x][y]:
                    continue
                # land tile adjacent to water => coast seed
                is_coast = False
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < self.tw and 0 <= ny < self.th and not self.land[nx][ny]:
                        is_coast = True
                        break
                if is_coast:
                    coast_dist[x][y] = 0
                    dq.append((x, y))

        while dq:
            x, y = dq.popleft()
            d = coast_dist[x][y]
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.tw and 0 <= ny < self.th and self.land[nx][ny]:
                    if coast_dist[nx][ny] > d + 1:
                        coast_dist[nx][ny] = d + 1
                        dq.append((nx, ny))

        for x in range(self.tw):
            for y in range(self.th):
                if not self.land[x][y]:
                    # sea: shallows near land (by sampling nearest land in neighborhood cheaply)
                    # we approximate by looking at a small radius for any land
                    near_land = False
                    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2)):
                        nx, ny = x+dx, y+dy
                        if 0 <= nx < self.tw and 0 <= ny < self.th and self.land[nx][ny]:
                            near_land = True
                            break
                    base = SEA_SHALLOWS if near_land else SEA_DEEP
                    # gentle variation from height noise
                    n = self.height[x][y]
                    col = (
                        clamp(base[0] + int((n - 0.6) * 14), 0, 255),
                        clamp(base[1] + int((n - 0.6) * 16), 0, 255),
                        clamp(base[2] + int((n - 0.6) * 18), 0, 255),
                    )
                    terrain_small.set_at((x, y), col)
                else:
                    h = self.height[x][y]
                    # land palette based on "height"
                    if h > 1.55:
                        base = (86, 86, 84)   # mountains
                    elif h > 1.30:
                        base = (74, 82, 58)   # uplands
                    elif h > 1.05:
                        base = (66, 78, 54)   # green
                    else:
                        base = (86, 82, 56)   # dry lowlands

                    # beaches near coast
                    if coast_dist[x][y] <= 2:
                        base = (104, 100, 70)

                    # tiny texture noise
                    dv = int((self.rnd.random() - 0.5) * 10)
                    col = (clamp(base[0] + dv, 0, 255), clamp(base[1] + dv, 0, 255), clamp(base[2] + dv, 0, 255))
                    terrain_small.set_at((x, y), col)

        # Province colors with fog-of-war (tile resolution)
        prov_small = pygame.Surface((self.tw, self.th)).convert()
        prov_small.fill(SEA_DEEP)

        for x in range(self.tw):
            for y in range(self.th):
                pid = self.prov_id[x][y]
                if pid < 0:
                    prov_small.set_at((x, y), (0, 0, 0))  # placeholder; masked later
                    continue
                k = self.provinces[pid].kingdom_id
                base = self.kingdom_colors[k % len(self.kingdom_colors)]

                if pid in self.owned_provinces:
                    col = brighten(base, 1.12)
                elif pid in self.visible_provinces:
                    col = brighten(base, 0.92)
                else:
                    col = fogged(base, 0.36)

                # subtle per-tile variation so provinces don't look flat-plastic
                dv = int((self.height[x][y] - 1.05) * 10)
                col = (clamp(col[0] + dv, 0, 255), clamp(col[1] + dv, 0, 255), clamp(col[2] + dv, 0, 255))
                prov_small.set_at((x, y), col)

        # Scale to world
        self.terrain_world = pygame.transform.smoothscale(terrain_small, (self.world_w, self.world_h))
        self.province_world = pygame.transform.scale(prov_small, (self.world_w, self.world_h))

        # Province layer texture (subtle) to feel like CK1 painted paper
        tile_fill(self.province_world, self.province_world.get_rect(), self.land_tile)
        veil = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 18))
        self.province_world.blit(veil, (0, 0))

        # Borders drawn at world resolution from tile edges
        self.border_world.fill((0, 0, 0, 0))
        ts = self.tile_size
        for x in range(self.tw - 1):
            for y in range(self.th - 1):
                a = self.prov_id[x][y]
                if a < 0:
                    continue
                r = self.prov_id[x+1][y]
                d = self.prov_id[x][y+1]

                wx = x * ts
                wy = y * ts

                if r >= 0 and r != a:
                    # vertical border at (x+1)
                    xx = (x + 1) * ts
                    pygame.draw.line(self.border_world, (*BORDER_RED_DIM, 210), (xx, wy), (xx, wy + ts), 2)
                    pygame.draw.line(self.border_world, (*BORDER_RED, 120), (xx, wy), (xx, wy + ts), 1)

                if d >= 0 and d != a:
                    yy = (y + 1) * ts
                    pygame.draw.line(self.border_world, (*BORDER_RED_DIM, 210), (wx, yy), (wx + ts, yy), 2)
                    pygame.draw.line(self.border_world, (*BORDER_RED, 120), (wx, yy), (wx + ts, yy), 1)

        # Global ink veil
        self.ink_world.fill((0, 0, 0, 0))
        tile_fill(self.ink_world, self.ink_world.get_rect(), self.paper_tile)
        self.ink_world.fill((0, 0, 0, 26), special_flags=pygame.BLEND_RGBA_MULT)

    def _compose_world(self):
        # Combine into final base map (static)
        self.combined_world.blit(self.terrain_world, (0, 0))

        # Province paint sits on top, fairly opaque to read like CK1
        # Still lets terrain/texture peek through.
        tmp = self.province_world.copy()
        tmp.set_alpha(220)
        self.combined_world.blit(tmp, (0, 0))

        self.combined_world.blit(self.border_world, (0, 0))
        self.combined_world.blit(self.ink_world, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Subtle sea banding for “old map” vibe
        band = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        for y in range(0, self.world_h, 6):
            a = 10 if (y // 6) % 2 == 0 else 0
            pygame.draw.line(band, (0, 0, 0, a), (0, y), (self.world_w, y))
        self.combined_world.blit(band, (0, 0))

    # ---------- Queries / Interaction ----------
    def world_to_tile(self, wx, wy):
        tx = int(wx // self.tile_size)
        ty = int(wy // self.tile_size)
        if 0 <= tx < self.tw and 0 <= ty < self.th:
            return tx, ty
        return None

    def province_at_world(self, world_pos):
        x, y = world_pos
        t = self.world_to_tile(x, y)
        if t is None:
            return None
        tx, ty = t
        pid = self.prov_id[tx][ty]
        if pid < 0:
            return None
        return self.provinces[pid]

    def province_outline_overlay(self, pid, fill_alpha=45, border_alpha=220):
        # Build overlay once per selection/hover (tile mask -> world scale)
        mask_small = pygame.Surface((self.tw, self.th), pygame.SRCALPHA)
        # Fill mask
        for x in range(self.tw):
            for y in range(self.th):
                if self.prov_id[x][y] == pid:
                    mask_small.set_at((x, y), (240, 232, 210, fill_alpha))
        fill_world = pygame.transform.scale(mask_small, (self.world_w, self.world_h))

        # Outline: draw borders where neighbor differs
        outline = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        ts = self.tile_size
        for x in range(self.tw - 1):
            for y in range(self.th - 1):
                if self.prov_id[x][y] != pid:
                    continue
                wx = x * ts
                wy = y * ts
                if self.prov_id[x+1][y] != pid:
                    xx = (x + 1) * ts
                    pygame.draw.line(outline, (245, 238, 220, border_alpha), (xx, wy), (xx, wy + ts), 2)
                if self.prov_id[x][y+1] != pid:
                    yy = (y + 1) * ts
                    pygame.draw.line(outline, (245, 238, 220, border_alpha), (wx, yy), (wx + ts, yy), 2)
                # outer edges
                if x == 0 and self.prov_id[x][y] == pid:
                    pygame.draw.line(outline, (245, 238, 220, border_alpha), (wx, wy), (wx, wy + ts), 2)
                if y == 0 and self.prov_id[x][y] == pid:
                    pygame.draw.line(outline, (245, 238, 220, border_alpha), (wx, wy), (wx + ts, wy), 2)
        return fill_world, outline

    def province_label(self, pid):
        if pid in self._label_cache:
            return self._label_cache[pid]
        p = self.provinces[pid]
        surf = FOOTER_FONT.render(p.name, True, (220, 214, 198))
        surf.set_alpha(170)
        self._label_cache[pid] = surf
        return surf


# =========================
# Layout + Modal + UI Manager (unchanged structure)
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
        self.panel_tile = make_noise_tile((96, 96), (44, 44, 46), variance=10, alpha=255, seed=seed)
        self.top_tile = make_noise_tile((128, 64), (28, 28, 30), variance=10, alpha=255, seed=seed + 1)
        self.bottom_tile = make_noise_tile((96, 96), (26, 26, 28), variance=10, alpha=255, seed=seed + 2)

    def _draw_resource(self, surface, pos, label, value, icon_color):
        x, y = pos
        icon = pygame.Rect(x, y + 4, 18, 18)
        pygame.draw.rect(surface, (22, 22, 22), pygame.Rect(x - 6, y - 6, 130, 34), border_radius=8)
        pygame.draw.circle(surface, icon_color, icon.center, 7)
        pygame.draw.circle(surface, (0, 0, 0), icon.center, 7, 1)
        draw_body_text(surface, f"{value}", x + 24, y, color=(235, 228, 210))
        draw_footer_text(surface, label, x + 24, y + 18, color=(165, 160, 150))

    def draw_top_bar(self, surface, rect, state):
        pygame.draw.rect(surface, (16, 16, 16), rect)
        tile_fill(surface, rect, self.top_tile)
        pygame.draw.line(surface, (90, 86, 78), (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1))
        pygame.draw.line(surface, (0, 0, 0), (rect.left, rect.bottom - 2), (rect.right, rect.bottom - 2))

        plaque = pygame.Rect(rect.left + UI_GUTTER, rect.top + 10, 360, rect.h - 20)
        pygame.draw.rect(surface, (22, 22, 22), plaque, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), plaque, 2, border_radius=8)
        pygame.draw.line(surface, (120, 110, 92), (plaque.left + 2, plaque.top + 2), (plaque.right - 3, plaque.top + 2))

        draw_title_text(surface, "DOMINION: GRAND STRATEGY", plaque.left + 12, plaque.top + 6, color=(235, 228, 210))
        draw_footer_text(surface, "CK1-inspired map + fog-of-war provinces", plaque.left + 12, plaque.top + 32, color=(170, 165, 155))

        date_block = pygame.Rect(plaque.right + 10, plaque.top, 240, plaque.h)
        pygame.draw.rect(surface, (22, 22, 22), date_block, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), date_block, 2, border_radius=8)
        draw_header_text(surface, str(state["date"]), date_block.left + 12, date_block.top + 10, color=(230, 224, 208))

        rx = date_block.right + 14
        ry = rect.top + 18
        res = state["resources"]
        self._draw_resource(surface, (rx, ry), "Gold", res["gold"], icon_color=(190, 165, 90))
        self._draw_resource(surface, (rx + 140, ry), "Prestige", res["prestige"], icon_color=(150, 150, 165))
        self._draw_resource(surface, (rx + 290, ry), "Piety", res["piety"], icon_color=(165, 150, 110))

        btns = []
        bx = rect.right - UI_GUTTER - 300
        by = rect.top + 12
        bw = 60
        bh = 36

        plate = pygame.Rect(bx - 130, by, 120, bh)
        pygame.draw.rect(surface, (22, 22, 22), plate, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), plate, 2, border_radius=8)
        sp = state["speed_level"]
        sp_label = "Paused" if sp == 0 else f"Speed {sp}"
        draw_body_text(surface, sp_label, plate.left + 10, plate.top + 8, color=(220, 214, 198))

        b_pause = draw_secondary_button(surface, "II", bx, by, bw, bh)
        b_slow = draw_secondary_button(surface, ">", bx + 70, by, bw, bh)
        b_fast = draw_secondary_button(surface, ">>", bx + 140, by, bw, bh)
        b_ultra = draw_secondary_button(surface, ">>>", bx + 210, by, bw, bh)
        btns.append((b_pause, "toggle_pause"))
        btns.append((b_slow, "speed_1"))
        btns.append((b_fast, "speed_2"))
        btns.append((b_ultra, "speed_3"))

        hint = "Drag map / WASD or Arrows to pan • Wheel or +/- to zoom • Click province to select"
        draw_footer_text(surface, hint, rect.left + 10, rect.bottom - 20, color=(150, 145, 138))

        return btns

    def _draw_portrait(self, surface, rect, state):
        frame = pygame.Rect(rect.left, rect.top, rect.w, rect.h)
        pygame.draw.rect(surface, (18, 18, 18), frame, border_radius=10)
        pygame.draw.rect(surface, (0, 0, 0), frame, 2, border_radius=10)

        inner = frame.inflate(-12, -12)
        pygame.draw.rect(surface, (40, 36, 32), inner, border_radius=8)
        tile_fill(surface, inner, self.panel_tile)
        veil = pygame.Surface(inner.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 45))
        surface.blit(veil, inner.topleft)

        cx = inner.left + 60
        cy = inner.centery
        pygame.draw.circle(surface, (205, 185, 160), (cx, cy - 6), 26)
        pygame.draw.circle(surface, (55, 40, 30), (cx + 4, cy - 18), 24)
        pygame.draw.rect(surface, (90, 76, 62), pygame.Rect(cx - 20, cy + 12, 40, 26), border_radius=8)
        pygame.draw.circle(surface, (18, 18, 18), (cx - 8, cy - 8), 2)
        pygame.draw.circle(surface, (18, 18, 18), (cx + 6, cy - 8), 2)
        pygame.draw.line(surface, (120, 90, 70), (cx - 6, cy + 4), (cx + 8, cy + 4), 2)

        sp = shield_points((inner.right - 52, inner.centery), 34)
        pygame.draw.polygon(surface, (150, 40, 40), sp)
        pygame.draw.polygon(surface, (235, 228, 210), sp, 1)
        pygame.draw.line(surface, (235, 228, 210), (inner.right - 62, inner.centery - 22), (inner.right - 62, inner.centery + 22), 4)
        pygame.draw.line(surface, (235, 228, 210), (inner.right - 42, inner.centery - 22), (inner.right - 42, inner.centery + 22), 4)

        draw_footer_text(surface, state["character"]["house"], inner.left + 10, inner.bottom - 18, color=(200, 190, 175))

    def draw_left_panel(self, surface, rect, state):
        content = draw_framed_panel(surface, rect, title="Character", title_color=INK, tile=self.panel_tile)
        y = content.top

        pf = pygame.Rect(content.left, y, content.w, 120)
        self._draw_portrait(surface, pf, state)
        y = pf.bottom + 10

        y = draw_header_text(surface, state["character"]["name"], content.left, y, color=(235, 228, 210))
        y = draw_body_text(surface, state["character"]["title"], content.left, y, color=(185, 175, 160))
        y += 6

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

        y = draw_header_text(surface, "Levy & Army", content.left, y, color=(230, 224, 208))
        y = draw_body_text(surface, f"Raised: {state['army']['raised']}", content.left, y, color=(205, 198, 180))
        y = draw_body_text(surface, f"Max: {state['army']['max']}", content.left, y, color=(205, 198, 180))
        y = draw_body_text(surface, f"Morale: {state['army']['morale']}%", content.left, y, color=(205, 198, 180))

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

    def draw_right_panel(self, surface, rect, state):
        content = draw_framed_panel(surface, rect, title="Province / Realm", title_color=INK, tile=self.panel_tile)
        y = content.top

        sel = state["selected_province"]
        hov = state["hover_province"]
        world = state["world"]

        if sel is None:
            y = draw_body_text(surface, "No province selected.", content.left, y, color=(205, 198, 180))
            y = draw_footer_text(surface, "Click a province on the map to inspect it.", content.left, y, color=(155, 150, 140))
            y += 10
        else:
            k = sel.kingdom_id
            owner = "Your Realm" if k == world.player_kingdom else f"Kingdom #{k+1}"
            y = draw_header_text(surface, sel.name, content.left, y, color=(235, 228, 210))
            y = draw_body_text(surface, f"Owner: {owner}", content.left, y, color=(205, 198, 180))
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
            for i, hname in enumerate(["Castle", "City", "Temple"]):
                tag = " (capital)" if i == 0 else ""
                y = draw_body_text(surface, f"• {hname}{tag}", content.left, y, color=(205, 198, 180))

        if hov is not None:
            y2 = rect.bottom - 78
            box = pygame.Rect(content.left, y2, content.w, 62)
            pygame.draw.rect(surface, (20, 20, 20), box, border_radius=8)
            pygame.draw.rect(surface, (0, 0, 0), box, 2, border_radius=8)
            draw_footer_text(surface, "Hover", box.left + 10, box.top + 8, color=(165, 160, 150))
            draw_body_text(surface, hov.name, box.left + 10, box.top + 24, color=(235, 228, 210))

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

        log_rect = pygame.Rect(rect.left + UI_GUTTER, rect.top + 54, rect.w - UI_GUTTER * 2, rect.h - 62)
        pygame.draw.rect(surface, (20, 20, 20), log_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), log_rect, 2, border_radius=8)

        lx = log_rect.left + 10
        ly = log_rect.top + 8
        for line in state["log"][-3:]:
            ly = draw_footer_text(surface, line, lx, ly, color=(205, 198, 180))

        return btns


# =========================
# Game App
# =========================

class GameApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("CK1-Inspired Grand Strategy UI (Pygame)")
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()

        self.ui = UIManager(seed=11)
        self.layout = Layout(*self.screen.get_size())

        # NEW: organic continent + provinces + kingdoms + fog-of-war
        self.world = MapWorld(seed=7, world_size=(3200, 2200), tile_size=10)
        self.camera = Camera((self.world.world_w, self.world.world_h), self.layout.map.size)

        self.modal = Modal()
        self.date = GameDate(1067, 1, 21)

        self.speed_level = 0
        self.speed_days_per_sec = {0: 0, 1: 1, 2: 3, 3: 7}
        self._time_accum = 0.0

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
            "January 8, 1067: Envoys report unrest beyond the frontier.",
            "January 11, 1067: Merchants speak of new levies in the east.",
            "January 18, 1067: Scouts map the borderlands (visibility expands).",
        ]

        self.selected_province = None
        self.hover_province = None

        self._mouse_down_in_map = False
        self._mouse_down_pos = (0, 0)
        self._mouse_drag_threshold = 5

        self._prev_mouse_down = False

        # selection overlays (recomputed on selection change)
        self._sel_fill = None
        self._sel_outline = None
        self._hov_fill = None
        self._hov_outline = None

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
                "Map now generates an organic continent with irregular provinces.",
                "Fog of war: your realm is bright, neighbors visible, others dark."
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
        else:
            self.modal.show(
                "Not Implemented",
                [
                    f"'{action}' is a placeholder action.",
                    "The UI flow is wired; connect real systems here."
                ],
                [("OK", "accept", lambda: self.modal.close())]
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
            self.resources["gold"] += 1 if (self.date.day % 3 == 0) else 0

    def _map_controls(self, dt):
        keys = pygame.key.get_pressed()
        if self.modal.open:
            return

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

        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            mx, my = pygame.mouse.get_pos()
            if self.layout.map.collidepoint((mx, my)):
                self.camera.zoom_at(1.03, (mx, my), self.layout.map)
        if keys[pygame.K_MINUS]:
            mx, my = pygame.mouse.get_pos()
            if self.layout.map.collidepoint((mx, my)):
                self.camera.zoom_at(0.97, (mx, my), self.layout.map)

    def _update_hover(self):
        mx, my = pygame.mouse.get_pos()
        if self.layout.map.collidepoint((mx, my)):
            wp = self.camera.screen_to_world((mx, my), self.layout.map, use_target=False)
            self.hover_province = self.world.province_at_world(wp)
        else:
            self.hover_province = None

    def _refresh_overlays(self):
        if self.selected_province is None:
            self._sel_fill = self._sel_outline = None
        else:
            self._sel_fill, self._sel_outline = self.world.province_outline_overlay(self.selected_province.id, fill_alpha=55, border_alpha=235)

        if self.hover_province is None or (self.selected_province and self.hover_province.id == self.selected_province.id):
            self._hov_fill = self._hov_outline = None
        else:
            self._hov_fill, self._hov_outline = self.world.province_outline_overlay(self.hover_province.id, fill_alpha=30, border_alpha=160)

    def _draw_map(self, surface):
        map_rect = self.layout.map

        frame_rect = map_rect.inflate(12, 12)
        draw_drop_shadow(surface, frame_rect, strength=140, inflate=8, radius=12)
        pygame.draw.rect(surface, PANEL_OUTER, frame_rect, border_radius=12)
        pygame.draw.rect(surface, (0, 0, 0), frame_rect, 2, border_radius=12)
        pygame.draw.line(surface, BEVEL_LIGHT, (frame_rect.left+2, frame_rect.top+2), (frame_rect.right-3, frame_rect.top+2))
        pygame.draw.line(surface, BEVEL_LIGHT, (frame_rect.left+2, frame_rect.top+2), (frame_rect.left+2, frame_rect.bottom-3))
        pygame.draw.line(surface, BEVEL_DARK, (frame_rect.left+2, frame_rect.bottom-3), (frame_rect.right-3, frame_rect.bottom-3))
        pygame.draw.line(surface, BEVEL_DARK, (frame_rect.right-3, frame_rect.top+2), (frame_rect.right-3, frame_rect.bottom-3))

        view = pygame.Surface(map_rect.size).convert()
        view.fill(SEA_DEEP)

        self.camera.set_viewport(map_rect.size)
        vrect = self.camera.view_rect(use_target=False)

        world_rect = pygame.Rect(0, 0, self.world.world_w, self.world.world_h)
        inter = vrect.clip(world_rect)
        if inter.w > 0 and inter.h > 0:
            subs = self.world.combined_world.subsurface(inter).copy()
            z = self.camera.zoom
            scaled_w = max(1, int(round(inter.w * z)))
            scaled_h = max(1, int(round(inter.h * z)))
            scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))
            dx = int(round((inter.left - vrect.left) * z))
            dy = int(round((inter.top - vrect.top) * z))
            view.blit(scaled, (dx, dy))

            # Selection / hover overlays (world -> view)
            def blit_overlay(ov_surf):
                if ov_surf is None:
                    return
                ov_sub = ov_surf.subsurface(inter).copy()
                ov_scaled = pygame.transform.scale(ov_sub, (scaled_w, scaled_h))
                view.blit(ov_scaled, (dx, dy))

            blit_overlay(self._sel_fill)
            blit_overlay(self._sel_outline)
            blit_overlay(self._hov_fill)
            blit_overlay(self._hov_outline)

            # Province labels: only for visible provinces and only when zoom is close enough
            if self.camera.zoom >= 0.95:
                # draw a handful per frame to avoid clutter
                for p in self.world.provinces:
                    if p.id not in self.world.visible_provinces and p.id not in self.world.owned_provinces:
                        continue
                    # skip if out of view
                    if not inter.collidepoint((int(p.center.x), int(p.center.y))):
                        continue
                    sx = (p.center.x - inter.left) * z + dx
                    sy = (p.center.y - inter.top) * z + dy
                    label = self.world.province_label(p.id)
                    lr = label.get_rect(center=(int(sx), int(sy)))
                    # tiny shadow
                    sh = label.copy()
                    sh.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    sh.set_alpha(90)
                    view.blit(sh, (lr.x + 1, lr.y + 1))
                    view.blit(label, lr.topleft)

        draw_vignette(view, view.get_rect(), strength=85)

        # Hover tooltip plate
        if self.hover_province is not None:
            tip = self.hover_province.name
            seen = (self.hover_province.id in self.world.visible_provinces) or (self.hover_province.id in self.world.owned_provinces)
            tip2 = "Visible" if seen else "Unknown (fog)"
            plate = pygame.Rect(10, 10, min(420, map_rect.w - 20), 52)
            pygame.draw.rect(view, (18, 18, 18), plate, border_radius=10)
            pygame.draw.rect(view, (0, 0, 0), plate, 2, border_radius=10)
            draw_body_text(view, tip, plate.left + 12, plate.top + 8, color=(235, 228, 210))
            draw_footer_text(view, tip2, plate.left + 12, plate.top + 28, color=(180, 175, 165))

        surface.blit(view, map_rect.topleft)

        # Simple compass
        cx, cy = map_rect.right - 46, map_rect.bottom - 46
        pygame.draw.circle(surface, (18, 18, 18), (cx, cy), 20)
        pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 20, 2)
        pygame.draw.line(surface, (220, 214, 198), (cx, cy - 14), (cx, cy + 14), 1)
        pygame.draw.line(surface, (220, 214, 198), (cx - 14, cy), (cx + 14, cy), 1)
        draw_footer_text(surface, "N", cx - 5, cy - 32, color=(220, 214, 198))

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

                elif event.type == pygame.MOUSEWHEEL and not self.modal.open:
                    mx, my = pygame.mouse.get_pos()
                    if self.layout.map.collidepoint((mx, my)):
                        factor = 1.12 if event.y > 0 else 0.89
                        self.camera.zoom_at(factor, (mx, my), self.layout.map)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and not self.modal.open:
                        if self.layout.map.collidepoint(event.pos):
                            self._mouse_down_in_map = True
                            self._mouse_down_pos = event.pos
                            self.camera.begin_drag(event.pos)

                    if not self.modal.open and self.layout.map.collidepoint(event.pos):
                        if event.button == 4:
                            self.camera.zoom_at(1.12, event.pos, self.layout.map)
                        elif event.button == 5:
                            self.camera.zoom_at(0.89, event.pos, self.layout.map)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and not self.modal.open:
                        if self._mouse_down_in_map:
                            self.camera.end_drag()
                            moved = (abs(event.pos[0] - self._mouse_down_pos[0]) + abs(event.pos[1] - self._mouse_down_pos[1]))
                            if moved <= self._mouse_drag_threshold and self.layout.map.collidepoint(event.pos):
                                wp = self.camera.screen_to_world(event.pos, self.layout.map, use_target=False)
                                prov = self.world.province_at_world(wp)
                                if prov is not None:
                                    self.selected_province = prov
                                    self.push_log(f"{self.date}: Selected {prov.name}.")
                                    self._refresh_overlays()
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
            prev_hover = self.hover_province.id if self.hover_province else None
            self._update_hover()
            now_hover = self.hover_province.id if self.hover_province else None
            if prev_hover != now_hover:
                self._refresh_overlays()

            # Draw background
            self.screen.fill(BG_COLOR)
            bg = pygame.Surface(self.screen.get_size())
            bg.fill(BG_COLOR)
            tile_fill(bg, bg.get_rect(), self.ui.bottom_tile)
            bg.set_alpha(70)
            self.screen.blit(bg, (0, 0))

            # Draw map
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
                "world": self.world,
            }

            clickables = []
            clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state))
            clickables.extend(self.ui.draw_left_panel(self.screen, self.layout.left, state))
            clickables.extend(self.ui.draw_right_panel(self.screen, self.layout.right, state))
            clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state))

            # Modal on top
            modal_clickables = self.modal.draw(self.screen, self.ui.panel_tile)

            # Edge-triggered click dispatch
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