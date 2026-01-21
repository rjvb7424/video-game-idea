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

def clip_draw(surface, rect, draw_fn):
    prev = surface.get_clip()
    surface.set_clip(rect)
    draw_fn()
    surface.set_clip(prev)

UI_GUTTER = 0
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
    draw_drop_shadow(surface, rect, strength=120, inflate=4, radius=10)
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
    def __init__(self, pid, name, is_capital=False):
        self.id = pid
        self.name = name
        self.realm_id = 0
        self.is_capital = is_capital
        self.center = pygame.Vector2(0, 0)
        self.bounds_cells = pygame.Rect(0, 0, 1, 1)
        self.cell_count = 0
        self.biome = "Plains"
        self.biome_color = LAND_GREEN

        self.income = 1 + (pid % 5)
        self.levy = 120 + (pid * 9) % 520
        self.control = 55 + (pid * 3) % 45
        self.culture = "Nordfolken"
        self.faith = "Nordfolken Mythology"


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

# =========================
# Character / Ruler Generation (GLOBAL)
# =========================

CULTURE_FIRST_NAMES = {
    "Iberian":  ["Sancho", "Fernando", "Alfonso", "Ramiro", "García", "Rodrigo", "Diego", "Enrique"],
    "Frankish": ["Hugh", "Louis", "Charles", "Philippe", "Robert", "Henri", "Gaston", "Guillaume"],
    "Occitan":  ["Raymond", "Bernat", "Pons", "Arnaut", "Guilhem", "Peire", "Bertran", "Roger"],
    "Germanic": ["Heinrich", "Otto", "Konrad", "Friedrich", "Lothar", "Siegfried", "Arnulf", "Albrecht"],
    "Slavic":   ["Mieszko", "Bolesław", "Vladimir", "Sviatoslav", "Jaromir", "Radovan", "Milan", "Dragomir"],
}

CULTURE_HOUSES = {
    "Iberian":  ["de Aragón", "de León", "de Navarra", "de Castela", "de Coimbra", "de Porto"],
    "Frankish": ["de Valois", "de Blois", "de Anjou", "de Normandie", "de Champagne"],
    "Occitan":  ["de Toulouse", "de Foix", "de Provence", "de Béarn", "de Carcassonne"],
    "Germanic": ["von Habsburg", "von Bayern", "von Saxen", "von Schwaben", "von Thuringen"],
    "Slavic":   ["Piast", "Rurikid", "Přemyslid", "Nemanjić", "Arpad"],
}

def _realm_core_name(realm_name: str) -> str:
    # "Kingdom of X" -> "X"
    if " of " in realm_name:
        return realm_name.split(" of ", 1)[1]
    return realm_name

def _rank_for_realm_size(sz: int) -> str:
    if sz >= 3:
        return "King"
    if sz == 2:
        return "Duke"
    return "Count"

def _roll_stat(rnd: random.Random, lo=3, hi=14) -> int:
    # slightly bell-shaped
    v = int(round(rnd.gauss(8.5, 2.2)))
    return clamp(v, lo, hi)

def generate_random_traits(rnd: random.Random, min_n=3, max_n=3) -> list[str]:
    keys = list(TRAITS.keys())
    target = 3  # CK3-style cap
    chosen: list[str] = []
    tries = 0
    while len(chosen) < target and tries < 400:
        tries += 1
        t = rnd.choice(keys)
        if t in chosen:
            continue
        opp = TRAITS.get(t, {}).get("opposites", set())
        if any(o in chosen for o in opp):
            continue
        chosen.append(t)
    return normalize_traits(chosen, max_traits=3)

def generate_ruler(rnd: random.Random, realm_name: str, realm_size: int, culture: str, faith: str) -> dict:
    first = rnd.choice(CULTURE_FIRST_NAMES.get(culture, ["Aurelian", "Marcus", "Cassius"]))
    house = rnd.choice(CULTURE_HOUSES.get(culture, ["de Terra"]))
    rank = _rank_for_realm_size(realm_size)
    core = _realm_core_name(realm_name)

    stats = [
        ("Diplomacy",  _roll_stat(rnd)),
        ("Martial",    _roll_stat(rnd)),
        ("Stewardship",_roll_stat(rnd)),
        ("Intrigue",   _roll_stat(rnd)),
        ("Learning",   _roll_stat(rnd)),
        ("Prowess",    _roll_stat(rnd)),
    ]

    traits = generate_random_traits(rnd, 2, 4)

    character = {
        "name": f"{rank} {first}",
        "title": f"{rank} of {core}",
        "house": f"House {house}",
        "culture": culture,
        "faith": faith,
        "traits": traits,
        "stats": stats,  # temp; will become modified after apply_trait_effects
    }

    # Store base stats and apply trait effects
    character["base_stats"] = _stats_list_to_dict(character["stats"])
    apply_trait_effects(character)

    return character

def hash2(x, y, seed):
    return (x * 73856093 ^ y * 19349663 ^ seed * 83492791) & 0xFFFFFFFF

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

    def _assign_biomes_per_province(self):
        """Assign a single biome per province based on average height + a macro noise field."""
        w, h = self.gw, self.gh
        prov_n = len(self.provinces)

        # macro noise: big shapes (NOT per-cell speckle)
        macro = _value_noise_2d(w, h, cell_w=18, cell_h=18, seed=self.seed + 4242)

        sum_h = [0.0] * prov_n
        sum_n = [0.0] * prov_n
        cnt = [0] * prov_n

        for y in range(h):
            for x in range(w):
                if not self.land[y][x]:
                    continue
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue
                sum_h[pid] += self.height[y][x]
                sum_n[pid] += macro[y][x]
                cnt[pid] += 1

        for pid in range(prov_n):
            if cnt[pid] <= 0:
                continue

            ah = sum_h[pid] / cnt[pid]   # avg height
            an = sum_n[pid] / cnt[pid]   # avg macro noise

            # Deterministic province variation (so it doesn't look uniform)
            pr = random.Random(self.seed * 99991 + pid * 31)
            jitter = (pr.random() - 0.5) * 0.08

            # Biome rules (province-wide)
            if ah > 0.82:
                biome = "Mountains"
                col = MOUNTAIN
            elif ah > 0.74:
                biome = "Hills"
                col = HILLS
            else:
                # Forest vs plains vs dryland using macro noise + slight jitter
                forestiness = an * 0.75 + ah * 0.25 + jitter
                dryness = (1.0 - ah) * 0.55 + (an - 0.5) * 0.35 - jitter

                if forestiness > 0.63:
                    biome = "Forest"
                    col = FOREST
                elif dryness > 0.58:
                    biome = "Drylands"
                    col = LAND_DRY
                else:
                    biome = "Fertile" if ah > 0.60 else "Plains"
                    col = LAND_RICH if ah > 0.60 else LAND_GREEN

            self.provinces[pid].biome = biome
            self.provinces[pid].biome_color = col

    def _generate_realm_rulers(self):
        self.realm_rulers = [None] * len(self.realm_names)

        for rid in range(len(self.realm_names)):
            cap_pid = self.realm_capitals[rid]
            cap_prov = self.provinces[cap_pid]

            culture = cap_prov.culture
            faith = cap_prov.faith

            rr = random.Random(self.seed * 7777 + rid * 131)
            ruler = generate_ruler(
                rr,
                realm_name=self.realm_names[rid],
                realm_size=self.realm_sizes[rid],
                culture=culture,
                faith=faith,
            )
            self.realm_rulers[rid] = ruler

    def _name(self):
        a = ["Skal", "Hrafn", "Eir", "Fjall", "Vik", "Bjorn", "Ulf", "Sigr", "Thor", "As", "Hald", "Rim", "Storm", "Frost", "Var"]
        b = ["a", "e", "i", "o", "u", "y", "ei", "au"]
        c = ["vik", "heim", "fjord", "gard", "holt", "ness", "mark", "borg", "dal", "lund", "skar", "holm", "fell"]
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
        threshold = 0.65
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
        min_dist = max(7, int(math.sqrt((len(land_cells) / max(1, target_count))) * 0.75))
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
        # province count scales with land area (MORE provinces)
        scale_factor = (self.cell_scale / 8.0) ** 2
        # province count scales with land area (BIGGER provinces)
        # NOTE: land_n is in grid-cells, not pixels.
        target = clamp(int(land_n // 1200), 40, 110)

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
        small_threshold = 18
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

        rnd = random.Random(self.seed + 1337)

        # Mostly 2–3 provinces, some 1, very rare 4
        # 4: 5%  |  3: 35%  |  2: 45%  |  1: 15%
        # Bigger realms: mostly 4–6 provinces
        def pick_target_size():
            r = rnd.random()
            if r < 0.10:
                return 7
            if r < 0.30:
                return 6
            if r < 0.60:
                return 5
            if r < 0.85:
                return 4
            return 3

        realm_of = [-1] * prov_n
        realm_capitals = []
        realm_sizes = []

        order = list(range(prov_n))
        rnd.shuffle(order)

        rid = 0
        for seed_pid in order:
            if realm_of[seed_pid] != -1:
                continue

            target = pick_target_size()

            realm_of[seed_pid] = rid
            members = [seed_pid]

            # Grow this tiny kingdom by adding adjacent unassigned provinces
            while len(members) < target:
                candidates = []
                for p in members:
                    for nb in adj[p]:
                        if realm_of[nb] == -1:
                            candidates.append(nb)

                if not candidates:
                    break

                nb = rnd.choice(candidates)
                realm_of[nb] = rid
                members.append(nb)

            realm_capitals.append(seed_pid)
            realm_sizes.append(len(members))
            rid += 1

        realm_n = rid

        # Generate MANY distinct-but-muted colors (deterministic)
        import colorsys

        # Nordfolken-style: all realms are "kingdom-blue" variants (CK3-ish),
        # still distinct via hue/sat/value jitter.
        BASE_BLUE_H = 0.60      # ~216° (deep CK-like blue)
        H_JITTER    = 0.05      # how wide the blue range is (bigger = more variety)
        S_MIN, S_MAX = 0.25, 0.42
        V_MIN, V_MAX = 0.42, 0.62

        self.realm_colors = []
        for i in range(realm_n):
            rr = random.Random(self.seed * 10007 + i * 97 + 555)

            # keep hue within a blue band
            h = clamp(BASE_BLUE_H + (rr.random() - 0.5) * 2.0 * H_JITTER, 0.0, 1.0)
            s = S_MIN + rr.random() * (S_MAX - S_MIN)
            v = V_MIN + rr.random() * (V_MAX - V_MIN)

            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            self.realm_colors.append((int(r * 255), int(g * 255), int(b * 255)))

        self.realm_names = [f"Kingdom of {self._name()}" for _ in range(realm_n)]
        self.realm_capitals = realm_capitals[:]
        self.realm_sizes = realm_sizes[:]

        # Apply to provinces
        for pid, prov in enumerate(self.provinces):
            prov.realm_id = realm_of[pid]
            prov.is_capital = False

        # Player realm: realm containing province closest to map center
        cx, cy = self.world_w * 0.52, self.world_h * 0.52
        near = min(
            range(prov_n),
            key=lambda i: (self.provinces[i].center.x - cx) ** 2 + (self.provinces[i].center.y - cy) ** 2
        )
        self.player_realm_id = realm_of[near]

        # Mark capitals (one per realm)
        for cap_pid in self.realm_capitals:
            if 0 <= cap_pid < prov_n:
                self.provinces[cap_pid].is_capital = True

        # Store player capital province id (handy for label logic)
        if 0 <= self.player_realm_id < len(self.realm_capitals):
            self.player_capital_pid = self.realm_capitals[self.player_realm_id]
        else:
            self.player_capital_pid = near



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

        # Terrain texture overlay (grayscale multipliers)
        tex = pygame.Surface((w, h)).convert()
        tpx = pygame.PixelArray(tex)

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
                    tpx[x, y] = (255, 255, 255)  # neutral multiplier for sea
                    continue
                pid = self.prov_id[y][x]
                if pid < 0:
                    px[x, y] = SEA_DEEP
                    tpx[x, y] = (255, 255, 255)
                    continue

                prov = self.provinces[pid]
                rid = prov.realm_id
                realm_col = self.realm_colors[rid]

                # --- Biome texture (multiplier) ---
                hval = hash2(x, y, self.seed)
                biome = prov.biome

                # default subtle grain
                darken = (hval % 9)  # 0..8

                if biome == "Forest":
                    # "trees": frequent darker specks + occasional deeper blobs
                    if (hval % 13) == 0:
                        darken = 42
                    elif (hval % 5) == 0:
                        darken = 18
                    else:
                        darken = 10

                elif biome == "Mountains":
                    # ridge lines: diagonal-ish banding + noise
                    if ((x + y + (hval % 7)) % 6) == 0:
                        darken = 38
                    else:
                        darken = 14 + (hval % 10)

                elif biome == "Hills":
                    # softer banding
                    if ((x * 2 + y + (hval % 11)) % 8) == 0:
                        darken = 22
                    else:
                        darken = 10 + (hval % 8)

                elif biome == "Drylands":
                    # stipple and cracks
                    if (hval % 17) == 0:
                        darken = 28
                    else:
                        darken = 12 + (hval % 10)

                elif biome in ("Fertile", "Plains"):
                    # gentle grain only
                    darken = 4 + (hval % 8)

                # apply fog to texture strength too (so unknown land is less detailed)
                vis = self.visibility_by_prov.get(pid, 0.45)
                fog_scale = 0.55 if vis < 0.78 else 1.0
                darken = int(darken * fog_scale)

                mul = 255 - clamp(darken, 0, 80)
                tpx[x, y] = (mul, mul, mul)

                # Base fill: purely realm color
                col = realm_col

                # micro shading
                dv = int((ntex[y][x] - 0.5) * 10)
                col = (clamp(col[0] + dv, 0, 255), clamp(col[1] + dv, 0, 255), clamp(col[2] + dv, 0, 255))

                # fog of war
                vis = self.visibility_by_prov.get(pid, 0.45)
                col = _apply_fog(col, vis)
                px[x, y] = col

        # scale up (keep provinces solid), then add subtle paper/noise veil
        del px
        del tpx

        # scale base color fill
        self.base_surface = pygame.transform.smoothscale(low, (self.world_w, self.world_h)).convert()

        # scale and apply texture (darkens base color to create biome detail)
        tex_big = pygame.transform.smoothscale(tex, (self.world_w, self.world_h)).convert()
        self.base_surface.blit(tex_big, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

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
        many_realms = len(self.realm_colors) > 20
        mask_realm = make_mask(realm_thick2, alpha=110 if many_realms else 200)
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
        # Store draw items (rendered later in screen-space so no pixelation on zoom)
        self.capital_label_items = []
        self.minimal_label_items = []
        self.army_markers = []

        capitals = set(getattr(self, "realm_capitals", []))

        # Labels only for seen + border provinces (same fog rules as before)
        for prov in self.provinces:
            vis = self.visibility_by_prov.get(prov.id, 0.45)
            if vis < 0.78:
                continue

            # Capitals always get the big label (even if a bit smaller)
            if prov.id in capitals:
                self.capital_label_items.append(prov.id)
                continue

            # Non-capitals: only show minimal labels for larger provinces (reduce clutter)
            if prov.cell_count < 320:
                continue
            self.minimal_label_items.append(prov.id)

        # a few army markers on player/adjacent provinces (keep as-is)
        candidates = [p for p in self.provinces if self.visibility_by_prov.get(p.id, 0.45) >= 0.78 and p.cell_count > 220]
        for i in range(min(9, len(candidates))):
            p = self.rnd.choice(candidates)
            x = int(p.center.x + self.rnd.randint(-32, 32))
            y = int(p.center.y + self.rnd.randint(-32, 32))
            self.army_markers.append((x, y))

        # IMPORTANT: only bake terrain + borders (no labels/markers)
        self.surface = self.base_surface.copy()
        self.surface.blit(self.border_surface, (0, 0))

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
        self._generate_realm_rulers()

        # NEW
        self._assign_biomes_per_province()

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

        # FLUSH to edges, and start immediately below top bar
        self.left = pygame.Rect(
            0,
            TOP_BAR_H,
            SIDE_W_L,
            h - TOP_BAR_H - BOTTOM_BAR_H
        )

        self.right = pygame.Rect(
            w - SIDE_W_R,
            TOP_BAR_H,
            SIDE_W_R,
            h - TOP_BAR_H - BOTTOM_BAR_H
        )

        # Map fills the space between panels, also flush vertically
        mx = self.left.right
        my = TOP_BAR_H
        mw = self.right.left - mx
        mh = self.bottom.top - my
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

# =========================
# Trait / Faith System (GLOBAL)
# =========================

TRAITS = {
    "forgiving":  {"name": "Forgiving",  "opposites": {"vengeful"}, "desc": "Lets go of slights and seeks reconciliation."},
    "vengeful":   {"name": "Vengeful",   "opposites": {"forgiving"}, "desc": "Remembers wrongs and pursues retribution."},

    "humble":     {"name": "Humble",     "opposites": {"proud"}, "desc": "Avoids vanity; accepts limitations."},
    "proud":      {"name": "Proud",      "opposites": {"humble"}, "desc": "Seeks glory; easily offended by disrespect."},

    "charitable": {"name": "Charitable", "opposites": {"greedy"}, "desc": "Gives freely; values mercy over wealth."},
    "greedy":     {"name": "Greedy",     "opposites": {"charitable"}, "desc": "Hoarder; values wealth and gain."},

    "patient":    {"name": "Patient",    "opposites": {"wrathful"}, "desc": "Slow to anger; endures hardship calmly."},
    "wrathful":   {"name": "Wrathful",   "opposites": {"patient"}, "desc": "Quick to anger; escalates conflict."},

    "chaste":     {"name": "Chaste",     "opposites": {"lustful"}, "desc": "Restrained desires."},
    "lustful":    {"name": "Lustful",    "opposites": {"chaste"}, "desc": "Indulgent desires."},

    "temperate":  {"name": "Temperate",  "opposites": {"gluttonous"}, "desc": "Moderation in appetite."},
    "gluttonous": {"name": "Gluttonous", "opposites": {"temperate"}, "desc": "Overindulgence in appetite."},

    "diligent":   {"name": "Diligent",   "opposites": {"lazy"}, "desc": "Hard-working and disciplined."},
    "lazy":       {"name": "Lazy",       "opposites": {"diligent"}, "desc": "Avoids effort; procrastinates."},
}

# Stats keys must match your character["stats"] tuples
STAT_KEYS = ["Diplomacy", "Martial", "Stewardship", "Intrigue", "Learning", "Prowess"]

# Per-trait stat modifiers (tweak numbers freely)
TRAIT_EFFECTS = {
    "forgiving":  {"Diplomacy": +2, "Martial": -1},
    "vengeful":   {"Martial": +2, "Diplomacy": -1},

    "humble":     {"Learning": +1, "Diplomacy": +1, "Prowess": -1},
    "proud":      {"Prowess": +2, "Diplomacy": -1},

    "charitable": {"Diplomacy": +2, "Stewardship": +1, "Intrigue": -1},
    "greedy":     {"Stewardship": +2, "Diplomacy": -1},

    "patient":    {"Learning": +1, "Stewardship": +1, "Martial": -1},
    "wrathful":   {"Martial": +2, "Prowess": +1, "Diplomacy": -1},

    "chaste":     {"Learning": +1, "Intrigue": -1},
    "lustful":    {"Intrigue": +2, "Diplomacy": +1, "Learning": -1},

    "temperate":  {"Stewardship": +1, "Learning": +1, "Prowess": -1},
    "gluttonous": {"Prowess": +1, "Stewardship": -1},

    "diligent":   {"Stewardship": +2, "Learning": +1, "Intrigue": -1},
    "lazy":       {"Stewardship": -2, "Martial": -1, "Intrigue": +1},
}

def _stats_list_to_dict(stats_list):
    return {k: int(v) for (k, v) in stats_list}

def _stats_dict_to_list(stats_dict):
    return [(k, int(stats_dict.get(k, 0))) for k in STAT_KEYS]

def apply_trait_effects(character: dict, lo=0, hi=20):
    """
    Recomputes character["stats"] from character["base_stats"] + trait modifiers.
    Creates base_stats if missing.
    """
    # Ensure base_stats exists
    if "base_stats" not in character:
        character["base_stats"] = _stats_list_to_dict(character.get("stats", []))

    base = dict(character["base_stats"])
    out = dict(base)

    for t in character.get("traits", []):
        mods = TRAIT_EFFECTS.get(t, {})
        for stat, delta in mods.items():
            out[stat] = out.get(stat, 0) + delta

    # Clamp
    for k in STAT_KEYS:
        out[k] = clamp(out.get(k, 0), lo, hi)

    character["stats"] = _stats_dict_to_list(out)
    return character

def trait_name(trait_id: str) -> str:
    return TRAITS.get(trait_id, {}).get("name", trait_id)

def normalize_traits(traits: list[str], max_traits: int = 3) -> list[str]:
    """Ensures no opposites coexist. Keeps the first encountered trait. Caps to max_traits."""
    out: list[str] = []
    have: set[str] = set()
    for t in traits:
        if t in have:
            continue
        opp = TRAITS.get(t, {}).get("opposites", set())
        if any(o in have for o in opp):
            continue
        out.append(t)
        have.add(t)
        if len(out) >= max_traits:
            break
    return out

def add_trait(character: dict, trait_id: str) -> tuple[bool, str]:
    """
    Adds a trait; if it has opposites, those are removed.
    Enforces a max of 3 traits total.
    Also applies stat effects after change.
    Returns (changed, message)
    """
    if trait_id not in TRAITS:
        return (False, f"Unknown trait '{trait_id}'.")

    character.setdefault("traits", [])
    character["traits"] = normalize_traits(character["traits"], max_traits=3)

    if trait_id in character["traits"]:
        return (False, f"{character.get('name','Character')} already has {trait_name(trait_id)}.")

    opposites = TRAITS[trait_id]["opposites"]
    removed = [t for t in character["traits"] if t in opposites]

    # Remove opposites first
    if removed:
        character["traits"] = [t for t in character["traits"] if t not in opposites]

    # Enforce cap (after removals)
    if len(character["traits"]) >= 3:
        # put them back? (we already removed opposites; but in CK3 gaining a new trait replaces an opposite)
        # Since we removed opposites only if relevant, this situation happens when there's no opposite removed.
        # So just reject cleanly:
        if removed:
            # If we removed opposites, we should allow the new trait because it's a replacement
            pass
        else:
            return (False, f"{character.get('name','Character')} already has 3 traits.")

    # Add and normalize again (cap + opposites)
    character["traits"].append(trait_id)
    character["traits"] = normalize_traits(character["traits"], max_traits=3)

    # Apply trait stat effects
    apply_trait_effects(character)

    if removed:
        return (True, f"Gained {trait_name(trait_id)} (removed {', '.join(trait_name(x) for x in removed)}).")
    return (True, f"Gained {trait_name(trait_id)}.")

FAITH_RULES = {
    "Catholic": {
        "virtues": {"forgiving", "humble", "charitable", "patient", "chaste", "temperate", "diligent"},
        "sins":    {"vengeful", "proud", "greedy", "wrathful", "lustful", "gluttonous", "lazy"},
        "base_piety_rate": 0,
    },
    "Orthodox": {
        "virtues": {"forgiving", "humble", "charitable", "patient", "temperate", "diligent"},
        "sins":    {"vengeful", "proud", "greedy", "wrathful", "gluttonous", "lazy"},
        "base_piety_rate": 0,
    },
    "Sunni": {
        "virtues": {"charitable", "patient", "temperate", "diligent"},
        "sins":    {"greedy", "wrathful", "gluttonous", "lazy"},
        "base_piety_rate": 0,
    },
    # Example: warrior ethos
    "Pagan": {
        "virtues": {"vengeful", "wrathful", "diligent"},
        "sins":    {"forgiving", "lazy"},
        "base_piety_rate": 0,
    },
    "Mozarabic": {
        "virtues": {"forgiving", "humble", "charitable", "patient", "temperate"},
        "sins":    {"vengeful", "proud", "greedy", "wrathful", "gluttonous"},
        "base_piety_rate": 0,
    },
}

def trait_alignment(character: dict) -> tuple[list[str], list[str], list[str]]:
    faith = character.get("faith", "Catholic")
    rules = FAITH_RULES.get(faith, {"virtues": set(), "sins": set(), "base_piety_rate": 0})

    virtues, sins, neutral = [], [], []
    for t in character.get("traits", []):
        if t in rules["virtues"]:
            virtues.append(t)
        elif t in rules["sins"]:
            sins.append(t)
        else:
            neutral.append(t)
    return virtues, sins, neutral

def compute_piety_rate(character: dict) -> tuple[int, dict]:
    faith = character.get("faith", "Catholic")
    rules = FAITH_RULES.get(faith, {"virtues": set(), "sins": set(), "base_piety_rate": 0})

    virtues, sins, neutral = trait_alignment(character)

    VIRTUE_BONUS = 1   # +1 piety/month per virtuous trait
    SIN_PENALTY  = 1   # -1 piety/month per sinful trait

    rate = int(rules.get("base_piety_rate", 0))
    rate += VIRTUE_BONUS * len(virtues)
    rate -= SIN_PENALTY  * len(sins)

    breakdown = {
        "faith": faith,
        "base": int(rules.get("base_piety_rate", 0)),
        "virtues": virtues,
        "sins": sins,
        "neutral": neutral,
        "virtue_bonus": VIRTUE_BONUS * len(virtues),
        "sin_penalty": SIN_PENALTY * len(sins),
    }
    return rate, breakdown

class UIManager:
    def __init__(self, seed=11):
        HEADER_COLOR = (70, 0, 18)
        # Textures used across panels (precomputed)
        self.panel_tile = make_noise_tile((96, 96), (44, 44, 46), variance=10, alpha=255, seed=seed)
        self.top_tile = make_noise_tile((128, 64), HEADER_COLOR, variance=10, alpha=255, seed=seed + 1)
        self.bottom_tile = make_noise_tile((96, 96), (26, 26, 28), variance=10, alpha=255, seed=seed + 2)
        self.left_tile = make_noise_tile((96, 96), (52, 36, 26), variance=12, alpha=255, seed=seed + 3)

    def draw_top_bar(self, surface, rect, state):
        btns = []

        # --- Responsive sizing ---
        PAD = max(10, rect.w // 120)
        GAP = max(10, rect.w // 140)
        BH  = max(34, int(rect.h * 0.62))
        y   = rect.centery - BH // 2

        TOP_RED = (90, 0, 22)  # deep royal-ish red

        # --- Background ---
        pygame.draw.rect(surface, TOP_RED, rect)
        tile_fill(surface, rect, self.top_tile)
        pygame.draw.line(surface, (90, 86, 78), (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1))
        pygame.draw.line(surface, (0, 0, 0), (rect.left, rect.bottom - 2), (rect.right, rect.bottom - 2))

        # ---------- RIGHT SIDE: Menu ----------
        menu_label = "Menu"
        menu_w = max(92, BODY_FONT.size(menu_label)[0] + 28)
        menu_rect = pygame.Rect(rect.right - PAD - menu_w, y, menu_w, BH)
        b_menu = draw_secondary_button(surface, menu_label, menu_rect.x, menu_rect.y, menu_rect.w, menu_rect.h)
        btns.append((b_menu, "open_menu"))

        right_edge = menu_rect.left - GAP

        # ---------- RIGHT SIDE: Speed plate + time buttons ----------
        sp = state["speed_level"]
        sp_label = "Paused" if sp == 0 else f"Speed {sp}"

        plate_w = max(120, BODY_FONT.size(sp_label)[0] + 36)
        bw = BH
        bgap = max(8, bw // 6)

        time_cluster_w = plate_w + GAP + (4 * bw + 3 * bgap)
        x_time = right_edge - time_cluster_w

        # speed plate
        plate = pygame.Rect(x_time, y, plate_w, BH)
        pygame.draw.rect(surface, (22, 22, 22), plate, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), plate, 2, border_radius=8)

        sp_surf = BODY_FONT.render(sp_label, True, (220, 214, 198))
        surface.blit(sp_surf, sp_surf.get_rect(center=plate.center))  # true center

        # time buttons
        bx = plate.right + GAP
        by = y
        b_pause = draw_secondary_button(surface, "II",  bx,                 by, bw, BH)
        b_slow  = draw_secondary_button(surface, ">",   bx + (bw + bgap),   by, bw, BH)
        b_fast  = draw_secondary_button(surface, ">>",  bx + 2*(bw + bgap), by, bw, BH)
        b_ultra = draw_secondary_button(surface, ">>>", bx + 3*(bw + bgap), by, bw, BH)

        btns.append((b_pause, "toggle_pause"))
        btns.append((b_slow,  "speed_1"))
        btns.append((b_fast,  "speed_2"))
        btns.append((b_ultra, "speed_3"))

        right_edge = x_time - GAP

        # ---------- LEFT SIDE: Date ----------
        date_text = str(state["date"])
        date_w = max(220, HEADER_FONT.size(date_text)[0] + 44)

        x_left = rect.left + PAD
        date_block = pygame.Rect(x_left, y, date_w, BH)
        pygame.draw.rect(surface, (22, 22, 22), date_block, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), date_block, 2, border_radius=8)

        date_surf = HEADER_FONT.render(date_text, True, (230, 224, 208))
        surface.blit(date_surf, date_surf.get_rect(center=date_block.center))  # true center

        x_left = date_block.right + GAP

        # ---------- MIDDLE: Resources fill the remaining space ----------
        res = state["resources"]
        avail = max(0, right_edge - x_left)

        min_pill = 150
        max_pill = 190

        def pill_rect(x, w):
            return pygame.Rect(x, y, w, BH)

        # Decide how many pills can fit without overlap
        # 3 pills need: 3*min + 2*GAP
        # 2 pills need: 2*min + 1*GAP
        if avail >= (3 * min_pill + 2 * GAP):
            per_w = min(max_pill, (avail - 2 * GAP) // 3)
            r1 = pill_rect(x_left, per_w)
            r2 = pill_rect(r1.right + GAP, per_w)
            r3 = pill_rect(r2.right + GAP, per_w)

            self._draw_resource(surface, r1, "Gold",     res["gold"],     res.get("gold_rate", 0),     icon_color=(190, 165, 90))
            self._draw_resource(surface, r2, "Prestige", res["prestige"], res.get("prestige_rate", 0), icon_color=(150, 150, 165))
            self._draw_resource(surface, r3, "Piety",    res["piety"],    res.get("piety_rate", 0),    icon_color=(165, 150, 110))

        elif avail >= (2 * min_pill + GAP):
            per_w = min(max_pill, (avail - GAP) // 2)
            r1 = pill_rect(x_left, per_w)
            r2 = pill_rect(r1.right + GAP, per_w)

            self._draw_resource(surface, r1, "Gold",     res["gold"],     res.get("gold_rate", 0),     icon_color=(190, 165, 90))
            self._draw_resource(surface, r2, "Prestige", res["prestige"], res.get("prestige_rate", 0), icon_color=(150, 150, 165))

        elif avail >= 120:
            r1 = pill_rect(x_left, min(avail, max_pill))
            self._draw_resource(surface, r1, "Gold", res["gold"], res.get("gold_rate", 0), icon_color=(190, 165, 90))

        return btns

    def _draw_resource(self, surface, rect, label, value, rate=0, icon_color=(200, 200, 200)):
        pygame.draw.rect(surface, (22, 22, 22), rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=8)

        # icon
        icon_r = 7
        icon_cx = rect.left + 18
        icon_cy = rect.centery
        pygame.draw.circle(surface, icon_color, (icon_cx, icon_cy), icon_r)
        pygame.draw.circle(surface, (0, 0, 0), (icon_cx, icon_cy), icon_r, 1)

        main_text = f"{label}: {value}"
        main_surf = BODY_FONT.render(main_text, True, (235, 228, 210))

        rate_text = f" ({rate:+d})"
        rate_surf = FOOTER_FONT.render(rate_text, True, (160, 155, 145))

        text_x = icon_cx + 16

        main_y = rect.centery - main_surf.get_height() // 2
        rate_y = rect.centery - rate_surf.get_height() // 2

        max_x = rect.right - 10
        if text_x + main_surf.get_width() + rate_surf.get_width() > max_x:
            # drop rate first if tight
            rate_surf = None

        surface.blit(main_surf, (text_x, main_y))
        if rate_surf is not None:
            surface.blit(rate_surf, (text_x + main_surf.get_width(), rate_y))

    def draw_left_panel(self, surface, rect, state):
        # Brown/tinted ruler panel
        content = draw_framed_panel(surface, rect, title="Ruler", title_color=INK, tile=self.left_tile)

        # extra warm tint over the inner area for stronger brown vibe
        tint = pygame.Surface((rect.w - 28, rect.h - 28), pygame.SRCALPHA)  # approx inner area
        tint.fill((70, 45, 28, 28))
        surface.blit(tint, (rect.left + 14, rect.top + 14))

        y = content.top

        # Portrait frame
        pf = pygame.Rect(content.left, y, content.w, 90)
        self._draw_portrait(surface, pf, state)
        y = pf.bottom + 10

        c = state["character"]

        # Name + titles
        y = draw_header_text(surface, c["name"], content.left, y, color=(235, 228, 210))
        y = draw_body_text(surface, c["title"], content.left, y, color=(185, 175, 160))
        y = draw_footer_text(surface, c["house"], content.left, y, color=(170, 160, 145))
        y += 8

        # Identity: Faith + Culture
        y = draw_header_text(surface, "Identity", content.left, y, color=(230, 224, 208))
        y = draw_body_text(surface, f"Faith: {c.get('faith','—')}", content.left, y, color=(220, 214, 198))
        y = draw_body_text(surface, f"Culture: {c.get('culture','—')}", content.left, y, color=(220, 214, 198))
        y += 6

        # Trait alignment + piety rate
        virtues, sins, neutral = trait_alignment(c)
        p_rate, breakdown = compute_piety_rate(c)

        y = draw_body_text(surface, f"Piety from traits: {p_rate:+d} / mo", content.left, y, color=(220, 214, 198))

        if virtues:
            y = draw_footer_text(surface, "Virtues: " + ", ".join(trait_name(t) for t in virtues),
                                content.left, y, color=(155, 190, 155))
        if sins:
            y = draw_footer_text(surface, "Sins: " + ", ".join(trait_name(t) for t in sins),
                                content.left, y, color=(200, 150, 150))
        y += 6

        # Stats (CK-like columns)
        y = draw_header_text(surface, "Attributes", content.left, y, color=(230, 224, 208))
        stats = c["stats"]
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

        # Traits list (all traits, including neutral)
        y = draw_header_text(surface, "Traits", content.left, y, color=(230, 224, 208))
        traits = c.get("traits", [])
        if not traits:
            y = draw_body_text(surface, "None", content.left, y, color=(185, 175, 160))
        else:
            # wrap the trait string to fit panel width
            trait_text = " • " + " • ".join(trait_name(t) for t in traits)
            for ln in wrap_text(trait_text.strip(), BODY_FONT, content.w - 10):
                y = draw_body_text(surface, ln, content.left, y, color=(205, 198, 180))
        y += 6

        # Army block
        y = draw_header_text(surface, "Levy & Army", content.left, y, color=(230, 224, 208))
        y = draw_body_text(surface, f"Raised: {state['army']['raised']}", content.left, y, color=(205, 198, 180))
        y = draw_body_text(surface, f"Max: {state['army']['max']}", content.left, y, color=(205, 198, 180))
        y = draw_body_text(surface, f"Morale: {state['army']['morale']}%", content.left, y, color=(205, 198, 180))
        y += 6

        # Buttons at bottom (unchanged)
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
        # Heraldry plate (NO avatar/head)
        frame = pygame.Rect(rect.left, rect.top, rect.w, rect.h)
        pygame.draw.rect(surface, (18, 18, 18), frame, border_radius=10)
        pygame.draw.rect(surface, (0, 0, 0), frame, 2, border_radius=10)

        inner = frame.inflate(-12, -12)
        pygame.draw.rect(surface, (40, 36, 32), inner, border_radius=8)

        tile_fill(surface, inner, self.panel_tile)
        veil = pygame.Surface(inner.size, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 45))
        surface.blit(veil, inner.topleft)

        # Deterministic-ish house color (stable)
        house = state["character"].get("house", "House")
        s = sum((i + 1) * ord(ch) for i, ch in enumerate(house))
        palette = [(150, 40, 40), (40, 120, 90), (120, 90, 40), (90, 60, 120), (150, 120, 50)]
        base = palette[s % len(palette)]

        # Big shield centered
        pts = shield_points((inner.centerx, inner.centery - 2), 62)
        pygame.draw.polygon(surface, base, pts)
        pygame.draw.polygon(surface, (235, 228, 210), pts, 1)

        # Simple charge (vertical stripes)
        pygame.draw.line(surface, (235, 228, 210), (inner.centerx - 10, inner.top + 14), (inner.centerx - 10, inner.bottom - 14), 5)
        pygame.draw.line(surface, (235, 228, 210), (inner.centerx + 10, inner.top + 14), (inner.centerx + 10, inner.bottom - 14), 5)

        # House label
        draw_footer_text(surface, house, inner.left + 10, inner.bottom - 18, color=(200, 190, 175))


    def draw_right_panel(self, surface, rect, state):
        content = draw_framed_panel(surface, rect, title="Province / Realm", title_color=INK, tile=self.panel_tile)

        sel = state["selected_province"]
        hov = state["hover_province"]

        # --- Reserve bottom space so nothing overlaps buttons/hover ---
        BTN_BAR_Y = rect.bottom - 56
        BTN_H = 34
        HOVER_H = 62
        GAP = 8

        show_hover = hov is not None
        hover_y = BTN_BAR_Y - GAP - HOVER_H if show_hover else BTN_BAR_Y
        y_limit = hover_y - 10  # content must stop before this

        y = content.top

        def safe_body(text, color=(205, 198, 180)):
            nonlocal y
            if y + BODY_FONT.get_height() + 6 > y_limit:
                return False
            y = draw_body_text(surface, text, content.left, y, color=color)
            return True

        def safe_header(text, color=(230, 224, 208)):
            nonlocal y
            if y + HEADER_FONT.get_height() + 8 > y_limit:
                return False
            y = draw_header_text(surface, text, content.left, y, color=color)
            return True

        def safe_footer(text, color=(155, 150, 140)):
            nonlocal y
            if y + FOOTER_FONT.get_height() + 6 > y_limit:
                return False
            y = draw_footer_text(surface, text, content.left, y, color=color)
            return True

        if sel is None:
            safe_body("No province selected.")
            safe_footer("Click a province on the map to inspect it.")
        else:
            # Province info
            safe_header(sel.name, color=(235, 228, 210))
            safe_body(f"Culture: {sel.culture}")
            safe_body(f"Faith: {sel.faith}")

            if y + 18 < y_limit:
                y += 6
                pygame.draw.line(surface, (0, 0, 0), (content.left, y), (content.right, y))
                pygame.draw.line(surface, (80, 74, 66), (content.left, y + 1), (content.right, y + 1))
                y += 10

            safe_body(f"Income: {sel.income} / mo", color=(220, 214, 198))
            safe_body(f"Levies: {sel.levy}", color=(220, 214, 198))
            safe_body(f"Control: {sel.control}%", color=(220, 214, 198))

            if y + 18 < y_limit:
                y += 10

            # Holdings
            safe_header("Holdings")
            for i, hname in enumerate(["Castle", "City", "Temple"]):
                tag = " (capital)" if i == 0 else ""
                if not safe_body(f"• {hname}{tag}"):
                    break

            # --- Realm + ruler (THIS is the part you were confused about) ---
            # Only do this when sel != None.
            rid = sel.realm_id
            realm_name = state["realm_names"][rid]
            ruler = state["realm_rulers"][rid]

            if y + 18 < y_limit:
                y += 8
                pygame.draw.line(surface, (0, 0, 0), (content.left, y), (content.right, y))
                pygame.draw.line(surface, (80, 74, 66), (content.left, y + 1), (content.right, y + 1))
                y += 10

            safe_header("Realm")
            safe_body(realm_name, color=(235, 228, 210))

            if y + 10 < y_limit:
                y += 6

            safe_header("Ruler")
            safe_body(ruler["name"], color=(235, 228, 210))
            safe_footer(ruler["title"], color=(185, 175, 160))
            safe_body(f"Faith: {ruler.get('faith','—')}")
            safe_body(f"Culture: {ruler.get('culture','—')}")

            pr, _ = compute_piety_rate(ruler)
            safe_body(f"Piety from traits: {pr:+d} / mo")

            traits = ruler.get("traits", [])
            if traits and y + 10 < y_limit:
                trait_text = " • " + " • ".join(trait_name(t) for t in traits)
                for ln in wrap_text(trait_text.strip(), BODY_FONT, content.w - 10):
                    if not safe_body(ln):
                        break

        # --- Hover box ABOVE the buttons (no overlap) ---
        show_hover = False
        hover_y = BTN_BAR_Y
        y_limit = hover_y - 10

        # Buttons at bottom (unchanged positioning)
        btns = []
        bx = content.left
        by = BTN_BAR_Y
        b1 = draw_secondary_button(surface, "View Realm", bx, by, 120, BTN_H)
        b2 = draw_primary_button(surface, "Set Rally", bx + 130, by, 120, BTN_H)
        b3 = draw_secondary_button(surface, "Council", bx + 260, by, 120, BTN_H)
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

        self.resources = {
    "gold": 513, "gold_rate": +1,
    "prestige": 100, "prestige_rate": 0,
    "piety": 100, "piety_rate": -2
}

        # Player character = ruler of player realm
        self.player_realm_id = self.world.player_realm_id
        self.character = dict(self.world.realm_rulers[self.player_realm_id])  # copy

        # Make sure base stats exist and trait effects are applied
        if "base_stats" not in self.character:
            self.character["base_stats"] = _stats_list_to_dict(self.character.get("stats", []))
        apply_trait_effects(self.character)

        # enforce opposites cleanly + update piety rate
        self.character["traits"] = normalize_traits(self.character.get("traits", []))
        p_rate, _ = compute_piety_rate(self.character)
        self.resources["piety_rate"] = p_rate

        self.character["traits"] = normalize_traits(self.character.get("traits", []))

        p_rate, _ = compute_piety_rate(self.character)
        self.resources["piety_rate"] = p_rate

        # (optional but useful if you want rates to accumulate smoothly later)
        self._res_accum = {"gold": 0.0, "prestige": 0.0, "piety": 0.0}


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

    def _draw_minimal_province_label(self, surf, center, prov, vis):
        # Minimal: outlined text only (no banner, no shield)
        a = 220 if vis > 0.95 else 180 if vis > 0.80 else 150

        text = prov.name
        main = FOOTER_FONT.render(text, True, (235, 228, 210))
        shadow = FOOTER_FONT.render(text, True, (0, 0, 0))

        main.set_alpha(a)
        shadow.set_alpha(int(a * 0.75))

        r = main.get_rect(center=(int(center[0]), int(center[1])))

        # outline (cheap + readable)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
            surf.blit(shadow, (r.x + dx, r.y + dy))

        surf.blit(main, r)


    def _draw_shield_icon(self, surf, center, base_rgb, alpha=220):
        cx, cy = center
        pts = shield_points((int(cx), int(cy)), 26)

        # shield fill
        pygame.draw.polygon(surf, (base_rgb[0], base_rgb[1], base_rgb[2], alpha), pts)

        # simple highlight stripe (optional, helps it read as a coat-of-arms)
        pygame.draw.line(surf, (235, 228, 210, int(alpha * 0.85)),
                         (int(cx) - 7, int(cy) - 16), (int(cx) - 7, int(cy) + 16), 3)
        pygame.draw.line(surf, (235, 228, 210, int(alpha * 0.85)),
                         (int(cx) + 7, int(cy) - 16), (int(cx) + 7, int(cy) + 16), 3)

        # outline
        pygame.draw.polygon(surf, (10, 10, 10, int(alpha * 0.9)), pts, 1)

    def _draw_banner_with_text(self, surf, center, text, alpha=220, text_color=(20, 20, 20)):
        # text surface
        text_surf = FOOTER_FONT.render(text, True, text_color)
        pad_x, pad_y = 14, 6

        w = text_surf.get_width() + pad_x * 2
        h = text_surf.get_height() + pad_y * 2

        rect = pygame.Rect(0, 0, w, h)
        rect.center = (int(center[0]), int(center[1]))

        # shadow
        shadow = rect.move(2, 2)
        pygame.draw.rect(surf, (0, 0, 0, int(alpha * 0.35)), shadow, border_radius=8)

        # banner fill
        pygame.draw.rect(surf, (220, 210, 190, alpha), rect, border_radius=8)

        # banner border
        pygame.draw.rect(surf, (40, 36, 32, int(alpha * 0.9)), rect, width=1, border_radius=8)

        # OPTIONAL: outline for readability (helps gold a lot)
        outline = FOOTER_FONT.render(text, True, (0, 0, 0))
        outline.set_alpha(int(alpha * 0.7))
        tr = text_surf.get_rect(center=rect.center)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            surf.blit(outline, (tr.x + dx, tr.y + dy))

        # text
        text_surf.set_alpha(alpha)
        surf.blit(text_surf, tr)

    def _draw_province_label_marker(self, surf, center, prov, vis):
        base = self.world.realm_colors[prov.realm_id]
        a = 235 if vis > 0.95 else 190

        # 1) coat of arms (back)
        shield_center = (center[0], center[1] - 10)
        self._draw_shield_icon(surf, shield_center, base, alpha=int(a * 0.95))

        # gold text ONLY for the player's capital
        is_player_capital = (prov.id == getattr(self.world, "player_capital_pid", -1))
        gold = (210, 175, 70)     # tweak if you want warmer/cooler
        black = (20, 20, 20)

        banner_center = (center[0], center[1] + 14)
        self._draw_banner_with_text(
            surf,
            banner_center,
            prov.name,
            alpha=a,
            text_color=(gold if is_player_capital else black)
        )

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
                # Supersample when zooming in to reduce visible pixel steps
                if z > 1.02:
                    big = pygame.transform.smoothscale(subs, (scaled_w * 2, scaled_h * 2))
                    scaled = pygame.transform.smoothscale(big, (scaled_w, scaled_h))
                else:
                    scaled = pygame.transform.smoothscale(subs, (scaled_w, scaled_h))

            dx = int(round((inter.left - vrect.left) * z))
            dy = int(round((inter.top - vrect.top) * z))
            view.blit(scaled, (dx, dy))

        # Subtle map overlay/vignette
        draw_vignette(view, view.get_rect(), strength=85)

        # --------------------------
        # Screen-space overlays (CRISP at any zoom) — FIXED ORDER
        # shield (back) -> banner -> text (front)
        # Also drawn on an SRCALPHA overlay so alpha behaves correctly.
        # --------------------------

        # ---- overlays ----
        overlay = pygame.Surface(map_rect.size, pygame.SRCALPHA).convert_alpha()
        overlay.fill((0, 0, 0, 0))

        capital_set = set(getattr(self.world, "capital_label_items", []))
        minimal_set = set(getattr(self.world, "minimal_label_items", []))

        # OPTIONAL: only show minimal labels when zoomed in enough (big clutter reduction)
        MIN_LABEL_ZOOM = 0.75
        show_minimal = self.camera.zoom >= MIN_LABEL_ZOOM

        draw_set = set(capital_set)
        if show_minimal:
            draw_set |= minimal_set

        for pid in sorted(draw_set):
            prov = self.world.provinces[pid]
            vis = self.world.visibility_by_prov.get(pid, 0.45)

            sp = self.camera.world_to_screen(prov.center, map_rect, use_target=False)
            lx = int(sp.x - map_rect.left)
            ly = int(sp.y - map_rect.top)

            if not (0 <= lx < map_rect.w and 0 <= ly < map_rect.h):
                continue

            if pid in capital_set:
                # full marker only for kingdom capital
                self._draw_province_label_marker(overlay, (lx, ly), prov, vis)
            else:
                # minimal label for non-capitals
                self._draw_minimal_province_label(overlay, (lx, ly), prov, vis)

        # blend onto the map view
        view.blit(overlay, (0, 0))

        # NOW blit the final view once
        surface.blit(view, map_rect.topleft)

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
                    if event.button == 1 and not self.modal.open:
                        if self.layout.map.collidepoint(event.pos):
                            self._mouse_down_in_map = True
                            self._mouse_down_pos = event.pos
                            self._drag_started = False

                    # fallback wheel (old style)
                    if not self.modal.open and self.layout.map.collidepoint(event.pos):
                        if event.button == 4:
                            self.camera.zoom_at(1.12, event.pos, self.layout.map)
                        elif event.button == 5:
                            self.camera.zoom_at(0.89, event.pos, self.layout.map)

                elif event.type == pygame.MOUSEMOTION:
                    if not self.modal.open and self._mouse_down_in_map:
                        dx = abs(event.pos[0] - self._mouse_down_pos[0])
                        dy = abs(event.pos[1] - self._mouse_down_pos[1])
                        if not self._drag_started and (dx + dy) > self._mouse_drag_threshold:
                            self._drag_started = True
                            self.camera.begin_drag(self._mouse_down_pos)

                        if self._drag_started:
                            self.camera.drag_to(event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self._mouse_down_in_map:
                            if self._drag_started:
                                self.camera.end_drag()
                            else:
                                if self.layout.map.collidepoint(event.pos):
                                    wp = self.camera.screen_to_world(event.pos, self.layout.map, use_target=False)
                                    prov = self.world.province_at_world(wp)
                                    if prov is not None:
                                        self.selected_province = prov
                                        self.push_log(f"{self.date}: Selected {prov.name}.")
                            self._mouse_down_in_map = False
                            self._drag_started = False
                            
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

                # ADD THESE:
                "realm_names": self.world.realm_names,
                "realm_rulers": self.world.realm_rulers,
            }

            clickables = []

            clip_draw(self.screen, self.layout.top,    lambda: clickables.extend(self.ui.draw_top_bar(self.screen, self.layout.top, state)))
            clip_draw(self.screen, self.layout.left,   lambda: clickables.extend(self.ui.draw_left_panel(self.screen, self.layout.left, state)))
            clip_draw(self.screen, self.layout.right,  lambda: clickables.extend(self.ui.draw_right_panel(self.screen, self.layout.right, state)))
            clip_draw(self.screen, self.layout.bottom, lambda: clickables.extend(self.ui.draw_bottom_bar(self.screen, self.layout.bottom, state)))

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