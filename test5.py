import math
import random
from collections import deque, defaultdict
from array import array

# ============================================================
# Provided UI Toolkit (MANDATORY BASE) - DO NOT MODIFY
# ============================================================

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

def _draw_text(surface, text, x, y, font, color):
    """Internal helper for drawing text and returning the new y position."""
    text_surf = font.render(text, True, color)
    surface.blit(text_surf, (x, y))
    return y + text_surf.get_height() + 4

def draw_title_text(surface, text, x, y, color=COLOR):
    """Draws title text on the given surface and returns the new y position."""
    return _draw_text(surface, text, x, y, TITLE_FONT, color)

def draw_header_text(surface, text, x, y, color=COLOR):
    """Draws header text on the given surface and returns the new y position."""
    return _draw_text(surface, text, x, y, HEADER_FONT, color)

def draw_body_text(surface, text, x, y, color=COLOR):
    """Draws body text on the given surface and returns the new y position."""
    return _draw_text(surface, text, x, y, BODY_FONT, color)

def draw_footer_text(surface, text, x, y, color=COLOR):
    """Draws footer text on the given surface and returns the new y position."""
    return _draw_text(surface, text, x, y, FOOTER_FONT, color)

def _draw_button(surface, text, x, y, width, height, bg_color, hover_color, text_color, border_color):
    """Internal helper used by all button types."""
    # draw button rectangle
    rect = pygame.Rect(x, y, width, height)
    # detect hover
    mx, my = pygame.mouse.get_pos()
    is_hovered = rect.collidepoint(mx, my)
    current_bg = hover_color if is_hovered else bg_color
    # draw button background
    pygame.draw.rect(surface, current_bg, rect, border_radius=BUTTON_BORDER_RADIUS)
    # draw button border
    pygame.draw.rect(surface, border_color, rect, width=1, border_radius=BUTTON_BORDER_RADIUS)
    # draw button text
    text_surf = BODY_FONT.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)
    # return the button rectangle for event handling
    return rect

def draw_primary_button(surface, text, x, y, width, height):
    """Primary action button."""
    return _draw_button(surface, text, x, y, width, height, BUTTON_BG, BUTTON_BG_HOVER, BUTTON_TEXT_COLOR, BUTTON_BORDER_COLOR,)

def draw_secondary_button(surface, text, x, y, width, height):
    """Secondary or neutral button."""
    return _draw_button(surface, text, x, y, width, height, SECONDARY_BG, SECONDARY_BG_HOVER, SECONDARY_TEXT_COLOR, SECONDARY_BORDER_COLOR,)

def draw_accept_button(surface, text, x, y, width, height):
    """Confirm action button."""
    return _draw_button(surface, text, x, y, width, height, ACCEPT_BG, ACCEPT_BG_HOVER, ACCEPT_TEXT_COLOR, ACCEPT_BORDER_COLOR,)

def draw_deny_button(surface, text, x, y, width, height):
    """Cancel action button."""
    return _draw_button(surface, text, x, y, width, height, DENY_BG, DENY_BG_HOVER, DENY_TEXT_COLOR, DENY_BORDER_COLOR,)

# ============================================================
# Helpers
# ============================================================

def clamp(v, a, b):
    return a if v < a else b if v > b else v

def lerp(a, b, t):
    return a + (b - a) * t

def exp_smooth(current, target, smoothing, dt):
    # smoothing: 0..1-ish; dt: seconds
    # Convert smoothing into a stable exponential blend factor.
    # Larger dt increases catch-up.
    k = 1.0 - math.pow(1.0 - smoothing, dt * 60.0)
    return current + (target - current) * k

def hsl_to_rgb(h, s, l):
    # h: 0..1, s: 0..1, l: 0..1
    def hue2rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hue2rgb(p, q, h + 1/3)
        g = hue2rgb(p, q, h)
        b = hue2rgb(p, q, h - 1/3)
    return (int(r * 255), int(g * 255), int(b * 255))

def mul_color(rgb, m):
    return (int(rgb[0] * m), int(rgb[1] * m), int(rgb[2] * m))

def add_color(rgb, a):
    return (clamp(rgb[0] + a[0], 0, 255), clamp(rgb[1] + a[1], 0, 255), clamp(rgb[2] + a[2], 0, 255))

# ============================================================
# Value Noise (fast enough for textures)
# ============================================================

class ValueNoise2D:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def make_grid(self, gw, gh):
        # grid values 0..255 ints for speed
        g = [[self.rng.randrange(0, 256) for _ in range(gw + 1)] for __ in range(gh + 1)]
        return g

    @staticmethod
    def _smoothstep(t):
        return t * t * (3 - 2 * t)

    def sample_grid(self, grid, w, h, step, x, y):
        # step: cell size in pixels
        gx = x // step
        gy = y // step
        fx = (x - gx * step) / step
        fy = (y - gy * step) / step
        fx = self._smoothstep(fx)
        fy = self._smoothstep(fy)

        # safe indexing (grid built with +1)
        v00 = grid[gy][gx]
        v10 = grid[gy][gx + 1]
        v01 = grid[gy + 1][gx]
        v11 = grid[gy + 1][gx + 1]

        vx0 = v00 + (v10 - v00) * fx
        vx1 = v01 + (v11 - v01) * fx
        v = vx0 + (vx1 - vx0) * fy
        return v / 255.0

    def fbm(self, grids_steps, x, y):
        # grids_steps: list of (grid, step, amp)
        s = 0.0
        a = 0.0
        for grid, step, amp in grids_steps:
            s += self.sample_grid(grid, 0, 0, step, x, y) * amp
            a += amp
        return s / a if a > 0 else 0.0

# ============================================================
# Camera (weighty, damped)
# ============================================================

class Camera:
    def __init__(self, world_w, world_h, viewport_rect):
        self.world_w = world_w
        self.world_h = world_h
        self.viewport = viewport_rect

        self.target_x = world_w * 0.5
        self.target_y = world_h * 0.5
        self.x = self.target_x
        self.y = self.target_y

        self.target_zoom = 0.85
        self.zoom = self.target_zoom

        self.min_zoom = 0.35
        self.max_zoom = 2.25

        self.dragging = False
        self.drag_last = (0, 0)

    def world_to_screen(self, wx, wy):
        vx, vy, vw, vh = self.viewport
        sx = vx + (wx - self.x) * self.zoom + vw * 0.5
        sy = vy + (wy - self.y) * self.zoom + vh * 0.5
        return sx, sy

    def screen_to_world(self, sx, sy):
        vx, vy, vw, vh = self.viewport
        wx = self.x + (sx - (vx + vw * 0.5)) / self.zoom
        wy = self.y + (sy - (vy + vh * 0.5)) / self.zoom
        return wx, wy

    def clamp_target(self):
        # keep camera centered in bounds (loose, allows some ocean)
        pad = 60
        self.target_x = clamp(self.target_x, -pad, self.world_w + pad)
        self.target_y = clamp(self.target_y, -pad, self.world_h + pad)

    def update(self, dt):
        self.clamp_target()
        self.x = exp_smooth(self.x, self.target_x, 0.12, dt)
        self.y = exp_smooth(self.y, self.target_y, 0.12, dt)
        self.zoom = exp_smooth(self.zoom, self.target_zoom, 0.12, dt)

    def start_drag(self, mouse_pos):
        self.dragging = True
        self.drag_last = mouse_pos

    def end_drag(self):
        self.dragging = False

    def drag(self, mouse_pos):
        if not self.dragging:
            return
        mx, my = mouse_pos
        lx, ly = self.drag_last
        dx = mx - lx
        dy = my - ly
        self.drag_last = mouse_pos

        # weighty feel: drag moves target, not current; also scaled by zoom
        self.target_x -= dx / self.zoom
        self.target_y -= dy / self.zoom

    def pan_keys(self, dt, speed):
        keys = pygame.key.get_pressed()
        vx = 0
        vy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            vx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            vx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            vy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            vy += 1
        if vx != 0 or vy != 0:
            # speed in world units per second
            mag = math.sqrt(vx * vx + vy * vy)
            vx /= mag
            vy /= mag
            # slower when zoomed in, faster when zoomed out (feels deliberate)
            z_factor = 1.0 / max(0.6, self.zoom)
            self.target_x += vx * speed * dt * z_factor
            self.target_y += vy * speed * dt * z_factor

    def zoom_at(self, mouse_pos, delta):
        # delta: +1 zoom in, -1 zoom out
        mx, my = mouse_pos
        before = self.screen_to_world(mx, my)

        z = self.target_zoom
        # gentle mousewheel response
        z *= (1.0 + 0.10 * delta)
        z = clamp(z, self.min_zoom, self.max_zoom)
        self.target_zoom = z

        after = self.screen_to_world(mx, my)

        # keep point under cursor stable by nudging target center
        self.target_x += (before[0] - after[0])
        self.target_y += (before[1] - after[1])

# ============================================================
# Map / World Generation
# ============================================================

class ProvinceCutout:
    __slots__ = ("pid", "rect", "full", "seen", "fog", "kingdom")
    def __init__(self, pid, rect, full, seen, fog, kingdom):
        self.pid = pid
        self.rect = rect
        self.full = full
        self.seen = seen
        self.fog = fog
        self.kingdom = kingdom

class World:
    def __init__(self, seed=1):
        self.seed = seed
        self.rng = random.Random(seed)

        # World resolution (the actual political map texture)
        self.W = 1400
        self.H = 900

        # counts
        self.num_provinces = 120
        self.num_kingdoms = 8

        # main data
        self.land = bytearray(self.W * self.H)         # 0 water, 1 land
        self.pid_map = array('H', [0]) * (self.W * self.H)  # 0 water, 1..P province id

        self.province_kingdom = [0] * (self.num_provinces + 1)  # pid -> kingdom
        self.province_centroid = [(0.0, 0.0)] * (self.num_provinces + 1)
        self.province_bounds = [(0, 0, -1, -1)] * (self.num_provinces + 1)
        self.adj = [set() for _ in range(self.num_provinces + 1)]  # pid adjacency

        # rendering surfaces
        self.water_surface = None
        self.borders_surface = None
        self.visible_surface = None

        # province cutouts
        self.cutouts = {}  # pid -> ProvinceCutout

        # player kingdom
        self.player_kingdom = 0
        self.selected_pid = 0
        self.hover_pid = 0

        self.kingdom_names = []
        self.kingdom_colors = []
        self.province_colors = [(0, 0, 0)] * (self.num_provinces + 1)

        self.generate()

    # -----------------------------
    # Generation pipeline
    # -----------------------------

    def generate(self):
        self.rng.seed(self.seed)

        self._gen_continent_mask()
        self._place_province_seeds_and_assign()
        self._smooth_province_map(iterations=2)
        self._build_province_stats_and_adjacency()
        self._assign_kingdoms()
        self._build_color_palettes()
        self._render_water_and_borders()
        self._build_province_cutouts()
        self.player_kingdom = 0
        self.selected_pid = 0
        self.hover_pid = 0
        self._rebuild_visibility_surface()

    # -----------------------------
    # 1) Single continent mask
    # -----------------------------

    def _gen_continent_mask(self):
        W, H = self.W, self.H
        self.land = bytearray(W * H)

        vn = ValueNoise2D(self.seed ^ 0xA53)
        # build a few grids for FBM
        grids_steps = []
        for step, amp in [(220, 1.00), (120, 0.75), (70, 0.55), (40, 0.40)]:
            gw = W // step + 2
            gh = H // step + 2
            grid = vn.make_grid(gw, gh)
            grids_steps.append((grid, step, amp))

        cx = W * 0.52 + self.rng.uniform(-W * 0.05, W * 0.05)
        cy = H * 0.50 + self.rng.uniform(-H * 0.05, H * 0.05)

        # radial falloff ensures "continent surrounded by water"
        maxr = min(W, H) * 0.52
        inv_maxr = 1.0 / maxr

        # threshold tuned for one big landmass; we’ll still keep largest component
        thr = 0.54 + self.rng.uniform(-0.03, 0.03)

        for y in range(H):
            oy = y - cy
            for x in range(W):
                ox = x - cx
                r = math.sqrt(ox * ox + oy * oy) * inv_maxr
                falloff = clamp(1.0 - r, 0.0, 1.0)
                # sculpt the edge a bit
                edge = falloff * falloff * (1.1 - 0.25 * r)

                n = vn.fbm(grids_steps, x, y)
                # blend: more influence of falloff towards edges
                e = (n * 0.75 + edge * 0.85)
                # add slight coastal ragging
                e += (vn.sample_grid(grids_steps[-1][0], 0, 0, grids_steps[-1][1], x, y) - 0.5) * 0.07

                idx = y * W + x
                self.land[idx] = 1 if e > thr else 0

        # keep only largest connected land component (guarantees a single continent)
        self._keep_largest_land_component()

    def _keep_largest_land_component(self):
        W, H = self.W, self.H
        land = self.land
        visited = bytearray(W * H)

        best_start = -1
        best_size = 0

        for i in range(W * H):
            if land[i] and not visited[i]:
                # flood fill
                q = [i]
                visited[i] = 1
                size = 0
                while q:
                    p = q.pop()
                    size += 1
                    x = p % W
                    y = p // W
                    # 4-neighbor
                    if x > 0:
                        n = p - 1
                        if land[n] and not visited[n]:
                            visited[n] = 1
                            q.append(n)
                    if x < W - 1:
                        n = p + 1
                        if land[n] and not visited[n]:
                            visited[n] = 1
                            q.append(n)
                    if y > 0:
                        n = p - W
                        if land[n] and not visited[n]:
                            visited[n] = 1
                            q.append(n)
                    if y < H - 1:
                        n = p + W
                        if land[n] and not visited[n]:
                            visited[n] = 1
                            q.append(n)
                if size > best_size:
                    best_size = size
                    best_start = i

        # if somehow no land, force a fallback blob
        if best_start < 0:
            cx = W // 2
            cy = H // 2
            for y in range(H):
                for x in range(W):
                    dx = x - cx
                    dy = y - cy
                    if dx * dx + dy * dy < (min(W, H) * 0.22) ** 2:
                        land[y * W + x] = 1
            return

        # second flood fill to mark best component only
        keep = bytearray(W * H)
        q = [best_start]
        keep[best_start] = 1
        while q:
            p = q.pop()
            x = p % W
            y = p // W
            if x > 0:
                n = p - 1
                if land[n] and not keep[n]:
                    keep[n] = 1
                    q.append(n)
            if x < W - 1:
                n = p + 1
                if land[n] and not keep[n]:
                    keep[n] = 1
                    q.append(n)
            if y > 0:
                n = p - W
                if land[n] and not keep[n]:
                    keep[n] = 1
                    q.append(n)
            if y < H - 1:
                n = p + W
                if land[n] and not keep[n]:
                    keep[n] = 1
                    q.append(n)

        for i in range(W * H):
            land[i] = 1 if keep[i] else 0

    # -----------------------------
    # 2) Provinces (organic, bordered)
    # -----------------------------

    def _place_province_seeds_and_assign(self):
        W, H = self.W, self.H
        land = self.land

        # jitter noise field for boundary warping
        vn = ValueNoise2D(self.seed ^ 0x51F00D)
        step = 64
        grid = vn.make_grid(W // step + 2, H // step + 2)

        # Poisson-ish seed placement
        seeds = []
        min_dist2 = (min(W, H) * 0.055) ** 2  # tuned for ~120 provinces on this map
        attempts = 0
        max_attempts = 200000

        # pre-sample some land indices for quicker selection
        land_indices = [i for i in range(W * H) if land[i]]
        if not land_indices:
            land_indices = [W * (H // 2) + (W // 2)]

        while len(seeds) < self.num_provinces and attempts < max_attempts:
            attempts += 1
            idx = land_indices[self.rng.randrange(0, len(land_indices))]
            x = idx % W
            y = idx // W
            ok = True
            for sx, sy in seeds:
                dx = x - sx
                dy = y - sy
                if dx * dx + dy * dy < min_dist2:
                    ok = False
                    break
            if ok:
                seeds.append((x, y))

        # if failed, pad with random land
        while len(seeds) < self.num_provinces:
            idx = land_indices[self.rng.randrange(0, len(land_indices))]
            seeds.append((idx % W, idx // W))

        # build spatial grid for fast nearest
        cell = 80
        grid_w = W // cell + 2
        grid_h = H // cell + 2
        buckets = [[[] for _ in range(grid_w)] for __ in range(grid_h)]
        for i, (sx, sy) in enumerate(seeds):
            cx = sx // cell
            cy = sy // cell
            buckets[cy][cx].append((i + 1, sx, sy))  # pid is 1..P

        pid_map = array('H', [0]) * (W * H)
        jitter_strength = 260.0  # higher -> more organic edges

        for y in range(H):
            cy = y // cell
            for x in range(W):
                idx = y * W + x
                if not land[idx]:
                    continue
                cx = x // cell

                # gather candidate seeds from neighboring buckets
                candidates = []
                for by in (cy - 1, cy, cy + 1):
                    if 0 <= by < grid_h:
                        row = buckets[by]
                        for bx in (cx - 1, cx, cx + 1):
                            if 0 <= bx < grid_w:
                                candidates.extend(row[bx])

                # fallback (shouldn't happen)
                if not candidates:
                    candidates = [(1, seeds[0][0], seeds[0][1])]

                # noise-based jitter (0..1)
                n = vn.sample_grid(grid, 0, 0, step, x, y)

                best_pid = 1
                best_d = 10**18
                for pid, sx, sy in candidates:
                    dx = x - sx
                    dy = y - sy
                    d = dx * dx + dy * dy
                    # boundary warping with deterministic jitter
                    d = d + jitter_strength * (n - 0.5)
                    if d < best_d:
                        best_d = d
                        best_pid = pid

                pid_map[idx] = best_pid

        self.pid_map = pid_map

    def _smooth_province_map(self, iterations=2):
        # majority filter over 4-neighbors to remove jagged pixel teeth
        W, H = self.W, self.H
        land = self.land
        pid = self.pid_map

        for _ in range(iterations):
            new_pid = array('H', pid)  # copy
            for y in range(1, H - 1):
                row = y * W
                for x in range(1, W - 1):
                    idx = row + x
                    if not land[idx]:
                        continue
                    a = pid[idx]
                    b = pid[idx - 1]
                    c = pid[idx + 1]
                    d = pid[idx - W]
                    e = pid[idx + W]
                    # count votes (small fixed set, manual)
                    # prefer keeping current if tie
                    if b == c == d or b == c == e or b == d == e or c == d == e:
                        # pick the triple
                        if b == c == d or b == c == e or b == d == e:
                            new_pid[idx] = b
                        else:
                            new_pid[idx] = c
                    else:
                        # if any neighbor matches current, keep it
                        if a == b or a == c or a == d or a == e:
                            new_pid[idx] = a
                        else:
                            # otherwise choose a neighbor deterministically
                            new_pid[idx] = b
            pid = new_pid

        self.pid_map = pid

    # -----------------------------
    # 3) Province stats + adjacency
    # -----------------------------

    def _build_province_stats_and_adjacency(self):
        W, H = self.W, self.H
        land = self.land
        pid_map = self.pid_map

        P = self.num_provinces

        minx = [10**9] * (P + 1)
        miny = [10**9] * (P + 1)
        maxx = [-1] * (P + 1)
        maxy = [-1] * (P + 1)

        sx = [0] * (P + 1)
        sy = [0] * (P + 1)
        cnt = [0] * (P + 1)

        adj = [set() for _ in range(P + 1)]

        for y in range(H):
            base = y * W
            for x in range(W):
                idx = base + x
                if not land[idx]:
                    continue
                p = pid_map[idx]
                if p == 0:
                    continue
                # bounds + centroid sums
                if x < minx[p]: minx[p] = x
                if y < miny[p]: miny[p] = y
                if x > maxx[p]: maxx[p] = x
                if y > maxy[p]: maxy[p] = y
                sx[p] += x
                sy[p] += y
                cnt[p] += 1

                # adjacency (right, down)
                if x < W - 1:
                    q = pid_map[idx + 1]
                    if q != 0 and q != p:
                        adj[p].add(q)
                        adj[q].add(p)
                if y < H - 1:
                    q = pid_map[idx + W]
                    if q != 0 and q != p:
                        adj[p].add(q)
                        adj[q].add(p)

        bounds = [(0, 0, -1, -1)] * (P + 1)
        centroids = [(0.0, 0.0)] * (P + 1)
        for p in range(1, P + 1):
            if cnt[p] <= 0:
                bounds[p] = (0, 0, 0, 0)
                centroids[p] = (W * 0.5, H * 0.5)
            else:
                bounds[p] = (minx[p], miny[p], maxx[p], maxy[p])
                centroids[p] = (sx[p] / cnt[p], sy[p] / cnt[p])

        self.province_bounds = bounds
        self.province_centroid = centroids
        self.adj = adj

    # -----------------------------
    # 4) Kingdom assignment (group provinces)
    # -----------------------------

    def _assign_kingdoms(self):
        P = self.num_provinces
        K = self.num_kingdoms

        # names (CK1-ish vibe)
        syll_a = ["Al", "Bar", "Cen", "Dor", "Eld", "Fjor", "Gal", "Har", "Ith", "Jar", "Kar", "Lor", "Mor", "Nor", "Or", "Pra", "Quel", "Rav", "Sar", "Tor", "Ul", "Var", "Wes", "Yor", "Zan"]
        syll_b = ["dun", "mark", "fell", "heim", "ford", "gate", "mere", "hold", "crest", "ward", "strand", "keep", "shire", "brough", "land", "reach", "moor", "havn", "brook", "holm"]
        self.kingdom_names = []
        used = set()
        for _ in range(K):
            for __ in range(200):
                name = f"{self.rng.choice(syll_a)}{self.rng.choice(syll_b)}"
                if name not in used:
                    used.add(name)
                    self.kingdom_names.append(name)
                    break
            else:
                self.kingdom_names.append(f"Realm{len(self.kingdom_names)+1}")

        # choose capital provinces via farthest-point sampling
        cent = self.province_centroid
        start = self.rng.randrange(1, P + 1)
        capitals = [start]
        while len(capitals) < K:
            best_p = 1
            best_d = -1
            for p in range(1, P + 1):
                # distance to nearest existing capital
                px, py = cent[p]
                mind = 10**18
                for c in capitals:
                    cx, cy = cent[c]
                    dx = px - cx
                    dy = py - cy
                    d = dx * dx + dy * dy
                    if d < mind:
                        mind = d
                if mind > best_d:
                    best_d = mind
                    best_p = p
            capitals.append(best_p)

        # assign each province to nearest capital
        province_kingdom = [0] * (P + 1)
        for p in range(1, P + 1):
            px, py = cent[p]
            best_k = 0
            best_d = 10**18
            for k, c in enumerate(capitals):
                cx, cy = cent[c]
                dx = px - cx
                dy = py - cy
                d = dx * dx + dy * dy
                if d < best_d:
                    best_d = d
                    best_k = k
            province_kingdom[p] = best_k

        # ensure each kingdom has multiple provinces (soft fix: reassign smallest to nearest non-small)
        counts = [0] * K
        for p in range(1, P + 1):
            counts[province_kingdom[p]] += 1

        # if any kingdom too small, steal nearest provinces from largest
        for _ in range(6):
            smallest = min(range(K), key=lambda k: counts[k])
            largest = max(range(K), key=lambda k: counts[k])
            if counts[smallest] >= max(6, P // (K * 2)):
                break
            # move one border-adjacent province from largest to smallest if close
            moved = False
            for p in range(1, P + 1):
                if province_kingdom[p] != largest:
                    continue
                px, py = cent[p]
                # choose if close to smallest capital centroid
                sc = capitals[smallest]
                sx, sy = cent[sc]
                lx, ly = cent[capitals[largest]]
                ds = (px - sx) ** 2 + (py - sy) ** 2
                dl = (px - lx) ** 2 + (py - ly) ** 2
                if ds < dl * 0.85:
                    province_kingdom[p] = smallest
                    counts[largest] -= 1
                    counts[smallest] += 1
                    moved = True
                    break
            if not moved:
                break

        self.province_kingdom = province_kingdom

    # -----------------------------
    # 5) Colors (muted medieval)
    # -----------------------------

    def _build_color_palettes(self):
        K = self.num_kingdoms
        P = self.num_provinces

        # Muted medieval tones: low saturation, moderate lightness.
        # Spread hues, but keep them subdued.
        base_hues = []
        h0 = self.rng.random()
        for i in range(K):
            base_hues.append((h0 + i / K + self.rng.uniform(-0.03, 0.03)) % 1.0)

        kingdom_colors = []
        for h in base_hues:
            s = 0.32 + self.rng.uniform(-0.05, 0.05)
            l = 0.42 + self.rng.uniform(-0.05, 0.05)
            kingdom_colors.append(hsl_to_rgb(h, clamp(s, 0.18, 0.40), clamp(l, 0.33, 0.50)))

        self.kingdom_colors = kingdom_colors

        # Province colors: slight lightness variation but same family
        province_colors = [(0, 0, 0)] * (P + 1)
        for p in range(1, P + 1):
            k = self.province_kingdom[p]
            base = kingdom_colors[k]
            # subtle per-province drift; keep kingdom cohesion
            drift = self.rng.uniform(-0.08, 0.08)
            m = clamp(1.0 + drift, 0.78, 1.10)
            # a tiny warm tint for medieval parchment feel
            warm = (4, 2, 0)
            c = add_color(mul_color(base, m), warm)
            province_colors[p] = c

        self.province_colors = province_colors

    # -----------------------------
    # 6) Render water texture + borders
    # -----------------------------

    def _render_water_and_borders(self):
        W, H = self.W, self.H
        land = self.land
        pid_map = self.pid_map

        # water texture using fbm noise
        vn = ValueNoise2D(self.seed ^ 0xBEE)
        grids_steps = []
        for step, amp in [(220, 1.0), (120, 0.7), (60, 0.45)]:
            grid = vn.make_grid(W // step + 2, H // step + 2)
            grids_steps.append((grid, step, amp))

        # Create RGBA buffer for water base
        buf = bytearray(W * H * 4)

        # ocean base colors (dark, muted)
        deep = (18, 28, 38)
        mid = (26, 40, 52)

        cx = W * 0.5
        cy = H * 0.5
        maxr = math.sqrt((W*0.55)**2 + (H*0.55)**2)

        for y in range(H):
            for x in range(W):
                idx = y * W + x
                n = vn.fbm(grids_steps, x, y)
                # vignette for mood
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx*dx + dy*dy) / maxr
                v = clamp(1.0 - r * 0.55, 0.55, 1.0)

                # mix deep->mid based on noise
                t = clamp(n * 0.95, 0.0, 1.0)
                rr = int(lerp(deep[0], mid[0], t) * v)
                gg = int(lerp(deep[1], mid[1], t) * v)
                bb = int(lerp(deep[2], mid[2], t) * v)

                o = idx * 4
                buf[o+0] = rr
                buf[o+1] = gg
                buf[o+2] = bb
                buf[o+3] = 255

        # Overlay land provinces onto a separate pass later (visibility surface),
        # but we keep water as a stable base surface.
        self.water_surface = pygame.image.frombuffer(bytes(buf), (W, H), "RGBA").convert_alpha()

        # Borders surface (RGBA)
        bbuf = bytearray(W * H * 4)
        border_col = (14, 14, 14)
        coast_col = (20, 20, 20)

        for y in range(1, H - 1):
            for x in range(1, W - 1):
                idx = y * W + x
                p = pid_map[idx]
                if p == 0:
                    continue

                # province border if any neighbor is different province
                # coastline if neighbor water
                left = pid_map[idx - 1]
                right = pid_map[idx + 1]
                up = pid_map[idx - W]
                down = pid_map[idx + W]

                is_coast = (left == 0 or right == 0 or up == 0 or down == 0)
                is_border = (left != 0 and left != p) or (right != 0 and right != p) or (up != 0 and up != p) or (down != 0 and down != p)

                if is_border or is_coast:
                    o = idx * 4
                    if is_border:
                        bbuf[o+0] = border_col[0]
                        bbuf[o+1] = border_col[1]
                        bbuf[o+2] = border_col[2]
                        bbuf[o+3] = 255
                    else:
                        # coastline slightly softer
                        bbuf[o+0] = coast_col[0]
                        bbuf[o+1] = coast_col[1]
                        bbuf[o+2] = coast_col[2]
                        bbuf[o+3] = 170

        self.borders_surface = pygame.image.frombuffer(bytes(bbuf), (W, H), "RGBA").convert_alpha()

    # -----------------------------
    # 7) Province cutouts (full/seen/fog)
    # -----------------------------

    def _build_province_cutouts(self):
        W, H = self.W, self.H
        land = self.land
        pid_map = self.pid_map
        colors = self.province_colors
        bounds = self.province_bounds
        prov_king = self.province_kingdom

        self.cutouts = {}

        # multipliers (adjacent slightly muted but readable, fog heavily dark)
        seen_mult = (215, 215, 215, 255)  # ~0.84
        fog_mult  = (70, 70, 70, 255)     # ~0.27

        # For speed: precompute per province rect buffers in one scan line pass
        for pid in range(1, self.num_provinces + 1):
            x0, y0, x1, y1 = bounds[pid]
            if x1 < x0 or y1 < y0:
                continue
            rw = x1 - x0 + 1
            rh = y1 - y0 + 1
            buf = bytearray(rw * rh * 4)

            r, g, b = colors[pid]
            for yy in range(y0, y1 + 1):
                base = yy * W
                out_row = (yy - y0) * rw
                for xx in range(x0, x1 + 1):
                    idx = base + xx
                    if land[idx] and pid_map[idx] == pid:
                        o = (out_row + (xx - x0)) * 4
                        buf[o+0] = r
                        buf[o+1] = g
                        buf[o+2] = b
                        buf[o+3] = 255

            full = pygame.image.frombuffer(bytes(buf), (rw, rh), "RGBA").convert_alpha()

            # seen and fog variants
            seen = full.copy()
            fog = full.copy()
            seen.fill(seen_mult, special_flags=pygame.BLEND_RGBA_MULT)
            fog.fill(fog_mult, special_flags=pygame.BLEND_RGBA_MULT)

            rect = pygame.Rect(x0, y0, rw, rh)
            self.cutouts[pid] = ProvinceCutout(pid, rect, full, seen, fog, prov_king[pid])

    # -----------------------------
    # 8) Fog of War compositing (rebuild on player change)
    # -----------------------------

    def _rebuild_visibility_surface(self):
        # Compose: water base + each province in full/seen/fog + borders
        W, H = self.W, self.H
        base = self.water_surface.copy()

        player_k = self.player_kingdom

        owned = set()
        for pid in range(1, self.num_provinces + 1):
            if self.province_kingdom[pid] == player_k:
                owned.add(pid)

        revealed = set()
        for pid in owned:
            for nb in self.adj[pid]:
                if nb not in owned:
                    revealed.add(nb)

        for pid, cut in self.cutouts.items():
            if cut.kingdom == player_k:
                base.blit(cut.full, cut.rect.topleft)
            elif pid in revealed:
                base.blit(cut.seen, cut.rect.topleft)
            else:
                base.blit(cut.fog, cut.rect.topleft)

        # borders always on top (keeps province separation clear even under fog)
        base.blit(self.borders_surface, (0, 0))
        self.visible_surface = base

    # ============================================================
    # Interaction helpers
    # ============================================================

    def pid_at_world(self, wx, wy):
        x = int(wx)
        y = int(wy)
        if x < 0 or y < 0 or x >= self.W or y >= self.H:
            return 0
        return self.pid_map[y * self.W + x]

    def cycle_player(self):
        self.player_kingdom = (self.player_kingdom + 1) % self.num_kingdoms
        self._rebuild_visibility_surface()

    def set_player(self, k):
        self.player_kingdom = k % self.num_kingdoms
        self._rebuild_visibility_surface()

# ============================================================
# UI framing (CK1-ish utilitarian)
# ============================================================

def draw_panel(surface, rect, fill=(32, 30, 28), border=(110, 104, 92), inner=(55, 52, 46), title=None):
    pygame.draw.rect(surface, fill, rect, border_radius=6)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=6)
    inset = rect.inflate(-8, -8)
    pygame.draw.rect(surface, inner, inset, width=1, border_radius=4)
    if title:
        y = rect.y + 8
        draw_header_text(surface, title, rect.x + 10, y, color=(235, 228, 210))

def draw_divider(surface, x, y, w):
    pygame.draw.line(surface, (90, 85, 76), (x, y), (x + w, y), 1)

# ============================================================
# Main App
# ============================================================

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Regnal Atlas (Procedural Political Map)")
        self.screen = pygame.display.set_mode((1280, 720))
        self.clock = pygame.time.Clock()

        # layout
        self.top_h = 56
        self.left_w = 260
        self.right_w = 260
        self.bottom_h = 62

        self.map_rect = pygame.Rect(
            self.left_w + 8,
            self.top_h + 8,
            self.screen.get_width() - self.left_w - self.right_w - 16,
            self.screen.get_height() - self.top_h - self.bottom_h - 16
        )

        self.left_panel = pygame.Rect(8, self.top_h + 8, self.left_w - 16, self.screen.get_height() - self.top_h - self.bottom_h - 16)
        self.right_panel = pygame.Rect(self.screen.get_width() - self.right_w + 8, self.top_h + 8, self.right_w - 16, self.screen.get_height() - self.top_h - self.bottom_h - 16)

        self.top_bar = pygame.Rect(0, 0, self.screen.get_width(), self.top_h)
        self.bottom_bar = pygame.Rect(0, self.screen.get_height() - self.bottom_h, self.screen.get_width(), self.bottom_h)

        self.seed = random.randrange(1, 10_000_000)
        self.world = World(self.seed)

        self.camera = Camera(self.world.W, self.world.H, self.map_rect)

        # cached map render
        self._cached_view = None
        self._cached_params = None

        # buttons
        self.btn_cycle = None
        self.btn_regen = None
        self.btn_center = None
        self.btn_quit = None

        # in-world date for vibe
        self.day = 1
        self.month = 3
        self.year = 1066
        self.time_acc = 0.0

    def regen_world(self):
        self.seed = random.randrange(1, 10_000_000)
        self.world = World(self.seed)
        self.camera.world_w = self.world.W
        self.camera.world_h = self.world.H
        self.camera.target_x = self.world.W * 0.5
        self.camera.target_y = self.world.H * 0.5
        self.camera.x = self.camera.target_x
        self.camera.y = self.camera.target_y
        self.camera.target_zoom = 0.85
        self.camera.zoom = self.camera.target_zoom
        self._cached_view = None
        self._cached_params = None

    def center_camera(self):
        self.camera.target_x = self.world.W * 0.5
        self.camera.target_y = self.world.H * 0.5
        self.camera.target_zoom = 0.85

    def _advance_date(self, dt):
        self.time_acc += dt
        if self.time_acc > 1.1:
            self.time_acc = 0.0
            self.day += 1
            if self.day > 30:
                self.day = 1
                self.month += 1
                if self.month > 12:
                    self.month = 1
                    self.year += 1

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            self._advance_date(dt)

            # hover pid
            mx, my = pygame.mouse.get_pos()
            if self.map_rect.collidepoint(mx, my):
                wx, wy = self.camera.screen_to_world(mx, my)
                self.world.hover_pid = self.world.pid_at_world(wx, wy)
            else:
                self.world.hover_pid = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.btn_cycle and self.btn_cycle.collidepoint(event.pos):
                            self.world.cycle_player()
                            self._cached_view = None
                        elif self.btn_regen and self.btn_regen.collidepoint(event.pos):
                            self.regen_world()
                        elif self.btn_center and self.btn_center.collidepoint(event.pos):
                            self.center_camera()
                        elif self.btn_quit and self.btn_quit.collidepoint(event.pos):
                            running = False
                        else:
                            # map dragging / selecting
                            if self.map_rect.collidepoint(event.pos):
                                # click selects province
                                wx, wy = self.camera.screen_to_world(*event.pos)
                                pid = self.world.pid_at_world(wx, wy)
                                if pid != 0:
                                    self.world.selected_pid = pid
                                self.camera.start_drag(event.pos)

                    elif event.button == 4:  # wheel up
                        if self.map_rect.collidepoint(event.pos):
                            self.camera.zoom_at(event.pos, +1)
                    elif event.button == 5:  # wheel down
                        if self.map_rect.collidepoint(event.pos):
                            self.camera.zoom_at(event.pos, -1)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.camera.end_drag()

                elif event.type == pygame.MOUSEMOTION:
                    if self.camera.dragging:
                        self.camera.drag(event.pos)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB:
                        self.world.cycle_player()
                        self._cached_view = None
                    elif event.key == pygame.K_r:
                        self.regen_world()
                    elif event.key == pygame.K_SPACE:
                        self.center_camera()

            self.camera.pan_keys(dt, speed=520.0)
            self.camera.update(dt)

            self.draw()

        pygame.quit()

    # ============================================================
    # Rendering
    # ============================================================

    def _render_map_view(self):
        # Cache render of visible_surface into viewport with current camera
        # Params for caching: camera center, zoom rounded to avoid thrashing
        cx = round(self.camera.x, 2)
        cy = round(self.camera.y, 2)
        z  = round(self.camera.zoom, 3)
        params = (cx, cy, z, self.map_rect.size)

        if self._cached_view is not None and self._cached_params == params:
            return self._cached_view

        vx, vy, vw, vh = self.map_rect
        view_w = vw / self.camera.zoom
        view_h = vh / self.camera.zoom

        x0 = int(self.camera.x - view_w * 0.5)
        y0 = int(self.camera.y - view_h * 0.5)

        # clamp to world, but allow slight overscan for edge smoothness
        x0 = clamp(x0, 0, self.world.W - 1)
        y0 = clamp(y0, 0, self.world.H - 1)

        x1 = int(x0 + view_w) + 2
        y1 = int(y0 + view_h) + 2
        x1 = clamp(x1, 1, self.world.W)
        y1 = clamp(y1, 1, self.world.H)

        sub = self.world.visible_surface.subsurface(pygame.Rect(x0, y0, x1 - x0, y1 - y0))
        # smoothscale for nicer zoom
        scaled = pygame.transform.smoothscale(sub, (vw, vh))

        self._cached_view = scaled
        self._cached_params = params
        return scaled

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Top bar
        pygame.draw.rect(self.screen, (30, 28, 26), self.top_bar)
        pygame.draw.line(self.screen, (105, 98, 86), (0, self.top_h - 1), (self.screen.get_width(), self.top_h - 1), 2)

        tx = 12
        ty = 10
        draw_title_text(self.screen, "REGNAL ATLAS", tx, ty, color=(240, 232, 210))
        date_txt = f"{self.day:02d}/{self.month:02d}/{self.year}"
        draw_body_text(self.screen, f"Date: {date_txt}", 260, 18, color=(210, 200, 180))
        draw_body_text(self.screen, "LMB Drag: Pan   Wheel: Zoom   TAB: Cycle Player   R: Regenerate   SPACE: Recenter", 420, 18, color=(200, 192, 175))

        # Panels
        draw_panel(self.screen, self.left_panel, title="Realm Ledger")
        draw_panel(self.screen, self.right_panel, title="Province Dossier")
        draw_panel(self.screen, self.bottom_bar.inflate(-16, -10), title=None)

        # Map frame
        frame = self.map_rect.inflate(10, 10)
        pygame.draw.rect(self.screen, (26, 24, 22), frame, border_radius=8)
        pygame.draw.rect(self.screen, (120, 112, 98), frame, width=2, border_radius=8)
        pygame.draw.rect(self.screen, (60, 56, 49), self.map_rect, width=1, border_radius=6)

        # Map render
        view = self._render_map_view()
        self.screen.blit(view, self.map_rect.topleft)

        # Hover highlight (thin bright outline sampled in screen space)
        if self.world.hover_pid != 0:
            # draw a small label near cursor
            pid = self.world.hover_pid
            k = self.world.province_kingdom[pid]
            name = self.world.kingdom_names[k]
            label = f"Prov {pid:03d} — {name}"
            text = FOOTER_FONT.render(label, True, (240, 235, 220))
            pad = 6
            box = pygame.Rect(pygame.mouse.get_pos()[0] + 16, pygame.mouse.get_pos()[1] + 10, text.get_width() + pad*2, text.get_height() + pad*2)
            pygame.draw.rect(self.screen, (20, 20, 20), box, border_radius=6)
            pygame.draw.rect(self.screen, (140, 132, 118), box, width=1, border_radius=6)
            self.screen.blit(text, (box.x + pad, box.y + pad))

        # Bottom buttons
        bb = self.bottom_bar.inflate(-16, -10)
        bx = bb.x + 12
        by = bb.y + 10
        self.btn_cycle = draw_primary_button(self.screen, "Cycle Player (TAB)", bx, by, 160, 38)
        bx += 172
        self.btn_regen = draw_secondary_button(self.screen, "Regenerate (R)", bx, by, 140, 38)
        bx += 152
        self.btn_center = draw_secondary_button(self.screen, "Recenter (SPACE)", bx, by, 160, 38)
        bx += 172
        self.btn_quit = draw_deny_button(self.screen, "Quit", bx, by, 90, 38)

        # Left panel content (player realm)
        lp = self.left_panel
        x = lp.x + 12
        y = lp.y + 44

        pk = self.world.player_kingdom
        pname = self.world.kingdom_names[pk]
        pcol = self.world.kingdom_colors[pk]
        y = draw_body_text(self.screen, f"Player Realm: {pname}", x, y, color=(235, 228, 210))
        y = draw_body_text(self.screen, f"Kingdom Color: {pcol}", x, y, color=(205, 200, 190))

        draw_divider(self.screen, x, y + 6, lp.width - 24)
        y += 16

        # counts
        counts = [0] * self.world.num_kingdoms
        for pid in range(1, self.world.num_provinces + 1):
            counts[self.world.province_kingdom[pid]] += 1

        y = draw_body_text(self.screen, "Holdings (Provinces):", x, y, color=(225, 220, 205))
        y += 2
        y = draw_body_text(self.screen, f"{counts[pk]} provinces under the crown.", x, y, color=(205, 200, 190))

        # list a few neighbor realms by border contact
        neighbor_realms = defaultdict(int)
        owned = [pid for pid in range(1, self.world.num_provinces + 1) if self.world.province_kingdom[pid] == pk]
        for pid in owned:
            for nb in self.world.adj[pid]:
                kb = self.world.province_kingdom[nb]
                if kb != pk:
                    neighbor_realms[kb] += 1

        y += 8
        y = draw_body_text(self.screen, "Border Realms:", x, y, color=(225, 220, 205))
        if neighbor_realms:
            for kb, n in sorted(neighbor_realms.items(), key=lambda kv: -kv[1])[:6]:
                nm = self.world.kingdom_names[kb]
                y = draw_body_text(self.screen, f"• {nm} (contacts: {n})", x, y, color=(200, 192, 175))
        else:
            y = draw_body_text(self.screen, "• None (isolated)", x, y, color=(200, 192, 175))

        # Right panel content (selected/hover province)
        rp = self.right_panel
        x = rp.x + 12
        y = rp.y + 44

        pid = self.world.selected_pid if self.world.selected_pid != 0 else self.world.hover_pid
        if pid != 0:
            k = self.world.province_kingdom[pid]
            kname = self.world.kingdom_names[k]
            kcol = self.world.kingdom_colors[k]
            c = self.world.province_colors[pid]
            cx, cy = self.world.province_centroid[pid]
            y = draw_body_text(self.screen, f"Province: {pid:03d}", x, y, color=(235, 228, 210))
            y = draw_body_text(self.screen, f"Realm: {kname}", x, y, color=(225, 220, 205))
            y = draw_body_text(self.screen, f"Prov Color: {c}", x, y, color=(205, 200, 190))
            y = draw_body_text(self.screen, f"Realm Color: {kcol}", x, y, color=(205, 200, 190))
            y += 6
            draw_divider(self.screen, x, y, rp.width - 24)
            y += 12
            y = draw_body_text(self.screen, f"Centroid: ({cx:.1f}, {cy:.1f})", x, y, color=(200, 192, 175))
            y = draw_body_text(self.screen, f"Adjacency: {len(self.world.adj[pid])} neighboring provinces", x, y, color=(200, 192, 175))

            # fog status of this province under current player
            pk = self.world.player_kingdom
            owned = (self.world.province_kingdom[pid] == pk)
            if owned:
                vis = "Visible (Owned)"
            else:
                # adjacent?
                adj_owned = False
                for nb in self.world.adj[pid]:
                    if self.world.province_kingdom[nb] == pk:
                        adj_owned = True
                        break
                vis = "Revealed (Adjacent)" if adj_owned else "Fogged (Unseen)"
            y += 6
            y = draw_body_text(self.screen, f"Visibility: {vis}", x, y, color=(235, 228, 210))
        else:
            y = draw_body_text(self.screen, "Click a province to inspect it.", x, y, color=(210, 200, 180))
            y = draw_body_text(self.screen, "Fog-of-war updates with TAB.", x, y, color=(200, 192, 175))

        # Small crosshair marker for selected province centroid
        if self.world.selected_pid != 0:
            pid = self.world.selected_pid
            cx, cy = self.world.province_centroid[pid]
            sx, sy = self.camera.world_to_screen(cx, cy)
            if self.map_rect.collidepoint(sx, sy):
                pygame.draw.circle(self.screen, (245, 238, 220), (int(sx), int(sy)), 6, 1)
                pygame.draw.line(self.screen, (245, 238, 220), (int(sx) - 10, int(sy)), (int(sx) + 10, int(sy)), 1)
                pygame.draw.line(self.screen, (245, 238, 220), (int(sx), int(sy) - 10), (int(sx), int(sy) + 10), 1)

        pygame.display.flip()

if __name__ == "__main__":
    App().run()