import math
import random
import pygame

# =========================
# Provided UI toolkit / constants (use exactly as base)
# =========================
pygame.font.init()

BG_COLOR = (24, 24, 24)

COLOR = (255, 255, 255)
FONT_PATH = pygame.font.match_font("arial")
TITLE_FONT  = pygame.font.Font(FONT_PATH, 24)
HEADER_FONT = pygame.font.Font(FONT_PATH, 20)
BODY_FONT   = pygame.font.Font(FONT_PATH, 16)
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
    return _draw_button(surface, text, x, y, width, height, BUTTON_BG, BUTTON_BG_HOVER, BUTTON_TEXT_COLOR, BUTTON_BORDER_COLOR)

def draw_secondary_button(surface, text, x, y, width, height):
    return _draw_button(surface, text, x, y, width, height, SECONDARY_BG, SECONDARY_BG_HOVER, SECONDARY_TEXT_COLOR, SECONDARY_BORDER_COLOR)

def draw_accept_button(surface, text, x, y, width, height):
    return _draw_button(surface, text, x, y, width, height, ACCEPT_BG, ACCEPT_BG_HOVER, ACCEPT_TEXT_COLOR, ACCEPT_BORDER_COLOR)

def draw_deny_button(surface, text, x, y, width, height):
    return _draw_button(surface, text, x, y, width, height, DENY_BG, DENY_BG_HOVER, DENY_TEXT_COLOR, DENY_BORDER_COLOR)

# =========================
# Helpers / style
# =========================
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))

def create_noise_surface(size, base=(52, 46, 38), variance=22, seed=0):
    rnd = random.Random(seed)
    w, h = size
    surf = pygame.Surface((w, h))
    px = pygame.PixelArray(surf)
    for y in range(h):
        for x in range(w):
            n = rnd.randint(-variance, variance)
            c = (clamp(base[0] + n, 0, 255), clamp(base[1] + n, 0, 255), clamp(base[2] + n, 0, 255))
            px[x, y] = surf.map_rgb(c)
    del px
    return surf.convert()

def draw_bevel_panel(surface, rect, fill, border, inset=2, radius=8, highlight=(120, 110, 95), shadow=(20, 18, 16), alpha=255):
    x, y, w, h = rect
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*fill, alpha), (0, 0, w, h), border_radius=radius)
    pygame.draw.rect(panel, (*border, alpha), (0, 0, w, h), width=2, border_radius=radius)
    pygame.draw.rect(panel, (*highlight, alpha), (inset, inset, w - 2 * inset, h - 2 * inset), width=1, border_radius=max(0, radius - 2))
    pygame.draw.line(panel, (*shadow, alpha), (inset, h - inset - 1), (w - inset - 1, h - inset - 1))
    pygame.draw.line(panel, (*shadow, alpha), (w - inset - 1, inset), (w - inset - 1, h - inset - 1))
    surface.blit(panel, (x, y))

def draw_frame(surface, rect, tone="bronze"):
    if tone == "bronze":
        outer = (120, 98, 58)
        inner = (70, 58, 34)
        glow  = (160, 135, 82)
    else:
        outer = (110, 110, 110)
        inner = (55, 55, 55)
        glow  = (160, 160, 160)

    x, y, w, h = rect
    pygame.draw.rect(surface, outer, rect, width=3, border_radius=10)
    pygame.draw.rect(surface, inner, (x + 3, y + 3, w - 6, h - 6), width=2, border_radius=9)
    pygame.draw.rect(surface, glow, (x + 7, y + 7, w - 14, h - 14), width=1, border_radius=8)

# =========================
# Provinces: irregular, non-overlapping, VERY colorful, guaranteed visible
# =========================
def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)):
            xinters = (x2 - x1) * (y - y1) / ((y2 - y1) + 1e-9) + x1
            if x < xinters:
                inside = not inside
    return inside

class Province:
    def __init__(self, pid, name, poly, bbox, color, liege):
        self.id = pid
        self.name = name
        self.poly = poly
        self.bbox = bbox
        self.color = color
        self.liege = liege
        self.tax = random.randint(1, 9)
        self.levy = random.randint(80, 420)
        self.dev = random.randint(1, 10)

class ProceduralMap:
    def __init__(self, size=(3200, 2000), seed=7):
        self.size = size
        self.seed = seed
        self.rnd = random.Random(seed)
        self.base = pygame.Surface(size).convert()
        self.color_layer = pygame.Surface(size).convert()  # << ALWAYS painted provinces go here
        self.provinces = []
        self._generate()

    def _name_for(self, pid):
        syll1 = ["Bar", "Car", "Mon", "Val", "Tar", "Bel", "San", "Rib", "Cor", "Gra", "Lle", "Cas", "Vil", "Tor", "Pam"]
        syll2 = ["ce", "ra", "gon", "na", "do", "lia", "va", "ça", "lon", "ria", "tes", "bri", "len", "mer", "ros"]
        syll3 = ["na", "ne", "ria", "sa", "go", "da", "ra", "lla", "dor", "tia", "ña", "es", "no", "re", "te"]
        rnd = random.Random(self.seed * 1000 + pid * 13)
        return rnd.choice(syll1) + rnd.choice(syll2) + rnd.choice(syll3)

    def _cell_irregular_poly(self, cell: pygame.Rect, rnd: random.Random):
        # irregular, but guaranteed within cell
        m = 8
        x0, y0 = cell.x + m, cell.y + m
        x1, y1 = cell.right - m, cell.bottom - m
        if x1 <= x0 + 20 or y1 <= y0 + 20:
            return [(cell.x, cell.y), (cell.right, cell.y), (cell.right, cell.bottom), (cell.x, cell.bottom)]

        pts = []
        # 10 points around the perimeter with jitter
        for t in [0.0, 0.18, 0.35, 0.5, 0.68]:
            px = int(lerp(x0, x1, t) + rnd.randint(-10, 10))
            py = int(y0 + rnd.randint(-10, 10))
            pts.append((px, py))
        for t in [0.18, 0.5, 0.82]:
            px = int(x1 + rnd.randint(-10, 10))
            py = int(lerp(y0, y1, t) + rnd.randint(-10, 10))
            pts.append((px, py))
        for t in [0.82, 0.55, 0.25]:
            px = int(lerp(x1, x0, t) + rnd.randint(-10, 10))
            py = int(y1 + rnd.randint(-10, 10))
            pts.append((px, py))
        for t in [0.7, 0.35]:
            px = int(x0 + rnd.randint(-10, 10))
            py = int(lerp(y1, y0, t) + rnd.randint(-10, 10))
            pts.append((px, py))

        # clamp points into cell bounds
        clamped = []
        for (px, py) in pts:
            clamped.append((clamp(px, x0, x1), clamp(py, y0, y1)))
        return clamped

    def _generate(self):
        w, h = self.size

        # --- base terrain (subtle; does NOT kill colors) ---
        self.base.fill((12, 18, 22))
        for y in range(h):
            t = y / (h - 1)
            ocean = mix((8, 16, 22), (12, 34, 46), t)
            pygame.draw.line(self.base, ocean, (0, y), (w, y))

        land = pygame.Surface((w, h), pygame.SRCALPHA)
        land.fill((0, 0, 0, 0))
        for _ in range(40):
            cx = self.rnd.randint(int(w * 0.12), int(w * 0.88))
            cy = self.rnd.randint(int(h * 0.18), int(h * 0.86))
            rx = self.rnd.randint(220, 700)
            ry = self.rnd.randint(160, 460)
            pygame.draw.ellipse(land, (55, 70, 40, 220), (cx - rx, cy - ry, rx * 2, ry * 2))
        self.base.blit(land, (0, 0))

        noise = create_noise_surface((w, h), base=(30, 34, 26), variance=20, seed=self.seed + 99)
        noise.set_alpha(55)
        self.base.blit(noise, (0, 0))

        # --- provinces (HARD COLOR LAYER) ---
        self.color_layer.fill((0, 0, 0))
        self._make_provinces()

        # composite final map surface (base + provinces with strong visibility)
        # NOTE: provinces are blended on top, not darkened.
        self.surface = self.base.copy()
        self.surface.blit(self.color_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # light ink borders on final surface (already in color layer too, but this reinforces at zoomed out)
        for p in self.provinces:
            pygame.draw.polygon(self.surface, (10, 8, 7), p.poly, width=2)
            pygame.draw.polygon(self.surface, (210, 185, 120), p.poly, width=1)

    def _make_provinces(self):
        w, h = self.size
        theatre = pygame.Rect(int(w * 0.10), int(h * 0.38), int(w * 0.80), int(h * 0.52))

        # palettes are BRIGHT on purpose so you cannot get “grey map”
        realm_names = ["Kingdom of Aragon", "Duchy of Aquitaine", "County of Foix", "Emirate of Zaragoza", "Kingdom of Navarra"]
        realm_pal = [
            ((220, 60, 60), (255, 230, 150)),
            ((60, 130, 235), (230, 240, 255)),
            ((200, 120, 55), (255, 220, 160)),
            ((60, 190, 110), (235, 255, 230)),
            ((225, 200, 60), (255, 250, 225)),
        ]

        cols, rows = 13, 7
        cell_w = theatre.w // cols
        cell_h = theatre.h // rows

        self.provinces.clear()
        pid = 1
        # guaranteed dense fill; minimal skipping
        for ry in range(rows):
            for rx in range(cols):
                if self.rnd.random() < 0.05:
                    continue

                cell = pygame.Rect(theatre.x + rx * cell_w, theatre.y + ry * cell_h, cell_w, cell_h)
                if cell.w < 90 or cell.h < 80:
                    continue

                realm_i = (rx // 3 + ry // 2) % len(realm_names)
                base, acc = realm_pal[realm_i]
                t = self.rnd.uniform(0.10, 0.40)
                base_col = mix(base, acc, t)

                local = random.Random(self.seed * 10000 + pid * 37)
                poly = self._cell_irregular_poly(cell, local)
                bbox = pygame.Rect(min(x for x, _ in poly), min(y for _, y in poly),
                                   max(x for x, _ in poly) - min(x for x, _ in poly),
                                   max(y for _, y in poly) - min(y for _, y in poly))

                p = Province(pid, self._name_for(pid), poly, bbox, base_col, realm_names[realm_i])
                self.provinces.append(p)

                # paint province into the COLOR LAYER in a way that cannot be “lost”
                pygame.draw.polygon(self.color_layer, p.color, p.poly)

                # add subtle internal texture that does NOT grey it out
                tex = create_noise_surface((max(1, bbox.w), max(1, bbox.h)), base=(18, 14, 10), variance=18, seed=self.seed + pid * 11)
                tex.set_alpha(18)
                self.color_layer.blit(tex, bbox.topleft)

                # borders: strong dark ink + gold edge
                pygame.draw.polygon(self.color_layer, (8, 6, 5), p.poly, width=3)
                pygame.draw.polygon(self.color_layer, (230, 205, 130), p.poly, width=1)

                pid += 1

        # absolute safety: if something went wrong, draw a big visible test grid so it cannot be “blank”
        if len(self.provinces) < 40:
            for i in range(12):
                for j in range(6):
                    col = (40 + i * 15, 60 + j * 25, 120 + (i * 8) % 90)
                    pygame.draw.rect(self.color_layer, col, pygame.Rect(theatre.x + i * 120, theatre.y + j * 120, 110, 110))

    def provinces_bounds(self):
        if not self.provinces:
            return pygame.Rect(0, 0, *self.size)
        r = self.provinces[0].bbox.copy()
        for p in self.provinces[1:]:
            r.union_ip(p.bbox)
        return r

# =========================
# Camera + MapView
# =========================
class Camera:
    def __init__(self, viewport_rect, world_size):
        self.vp = viewport_rect
        self.world_w, self.world_h = world_size
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.min_zoom = 0.45
        self.max_zoom = 2.25
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.dragging = False
        self.drag_anchor = (0, 0)
        self.offset_anchor = (0.0, 0.0)

    def screen_to_world(self, sx, sy):
        return (self.offset_x + (sx - self.vp.x) / self.zoom,
                self.offset_y + (sy - self.vp.y) / self.zoom)

    def start_drag(self, pos):
        self.dragging = True
        self.drag_anchor = pos
        self.offset_anchor = (self.offset_x, self.offset_y)

    def drag(self, pos):
        if not self.dragging:
            return
        mx, my = pos
        ax, ay = self.drag_anchor
        dx = (mx - ax) / self.zoom
        dy = (my - ay) / self.zoom
        self.offset_x = self.offset_anchor[0] - dx
        self.offset_y = self.offset_anchor[1] - dy
        self._clamp()

    def end_drag(self):
        self.dragging = False

    def zoom_at(self, mouse_pos, delta):
        mx, my = mouse_pos
        wx_before, wy_before = self.screen_to_world(mx, my)
        self.target_zoom = clamp(self.target_zoom * (1.0 + delta), self.min_zoom, self.max_zoom)
        tz = self.target_zoom
        self.offset_x = wx_before - (mx - self.vp.x) / tz
        self.offset_y = wy_before - (my - self.vp.y) / tz
        self._clamp()

    def update(self, dt):
        k = 12.0
        self.zoom = lerp(self.zoom, self.target_zoom, 1.0 - math.exp(-k * dt))
        self._clamp()

    def _clamp(self):
        vpw = self.vp.w / self.zoom
        vph = self.vp.h / self.zoom
        self.offset_x = clamp(self.offset_x, 0, max(0, self.world_w - vpw))
        self.offset_y = clamp(self.offset_y, 0, max(0, self.world_h - vph))

    def viewport_world_rect(self):
        return pygame.Rect(int(self.offset_x), int(self.offset_y),
                           int(self.vp.w / self.zoom), int(self.vp.h / self.zoom))

    def center_on_rect(self, world_rect, zoom=0.95):
        self.zoom = self.target_zoom = clamp(zoom, self.min_zoom, self.max_zoom)
        cx, cy = world_rect.center
        self.offset_x = cx - (self.vp.w / self.zoom) / 2
        self.offset_y = cy - (self.vp.h / self.zoom) / 2
        self._clamp()

class MapView:
    def __init__(self, rect, world_map: ProceduralMap):
        self.rect = rect
        self.map = world_map
        self.camera = Camera(rect, self.map.size)
        self.camera.center_on_rect(self.map.provinces_bounds().inflate(600, 420), zoom=0.95)

        # diagnostic preview cache
        self.preview = pygame.transform.smoothscale(self.map.surface, (260, 160))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in (2, 3) and self.rect.collidepoint(event.pos):
                self.camera.start_drag(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button in (2, 3):
                self.camera.end_drag()
        elif event.type == pygame.MOUSEMOTION:
            if self.camera.dragging:
                self.camera.drag(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint((mx, my)):
                self.camera.zoom_at((mx, my), delta=0.10 * event.y)

    def update(self, dt):
        self.camera.update(dt)

    def draw(self, screen):
        # frame
        draw_bevel_panel(screen, self.rect, fill=(18, 16, 14), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")

        # map pixels
        wr = self.camera.viewport_world_rect()
        sub = self.map.surface.subsurface(wr).copy()
        scaled = pygame.transform.smoothscale(sub, (self.rect.w, self.rect.h))
        screen.blit(scaled, (self.rect.x, self.rect.y))

        # ZERO extra dark overlays here (so colors cannot disappear)

        # ---- DIAGNOSTICS (so we can prove provinces exist + map is colored) ----
        diag = pygame.Rect(self.rect.x + 12, self.rect.y + 12, 290, 200)
        pygame.draw.rect(screen, (0, 0, 0), diag, border_radius=10)
        pygame.draw.rect(screen, (120, 98, 58), diag, width=2, border_radius=10)
        y = diag.y + 10
        y = draw_footer_text(screen, "MAP DIAGNOSTIC (this build)", diag.x + 10, y, color=(240, 230, 210))
        y = draw_footer_text(screen, f"Provinces: {len(self.map.provinces)}", diag.x + 10, y, color=(240, 230, 210))
        y = draw_footer_text(screen, f"Zoom: {self.camera.zoom:.2f}", diag.x + 10, y, color=(220, 210, 190))
        screen.blit(self.preview, (diag.x + 10, diag.y + 70))
        pygame.draw.rect(screen, (230, 205, 130), pygame.Rect(diag.x + 10, diag.y + 70, 260, 160), width=1)

    def pick_province(self, screen_pos):
        if not self.rect.collidepoint(screen_pos):
            return None
        wx, wy = self.camera.screen_to_world(*screen_pos)
        for p in self.map.provinces:
            if p.bbox.collidepoint((wx, wy)) and point_in_poly((wx, wy), p.poly):
                return p
        return None

# =========================
# Panels (same vibe; unchanged)
# =========================
class Tooltip:
    def __init__(self):
        self.text = ""
        self.visible = False
        self.pos = (0, 0)

    def show(self, text, pos):
        self.text = text
        self.pos = pos
        self.visible = True

    def hide(self):
        self.visible = False

    def draw(self, screen):
        if not self.visible or not self.text:
            return
        mx, my = self.pos
        pad = 8
        lines = self.text.split("\n")
        widths = [BODY_FONT.size(l)[0] for l in lines]
        w = max(widths) + pad * 2
        h = (BODY_FONT.get_height() + 2) * len(lines) + pad * 2
        rect = pygame.Rect(mx + 14, my + 14, w, h)

        sw, sh = screen.get_size()
        if rect.right > sw - 8:
            rect.x = mx - rect.width - 14
        if rect.bottom > sh - 8:
            rect.y = my - rect.height - 14

        draw_bevel_panel(screen, rect, fill=(35, 30, 25), border=(130, 110, 70), radius=8, alpha=235)
        y = rect.y + pad
        for l in lines:
            y = draw_body_text(screen, l, rect.x + pad, y, color=(240, 230, 210))

class MessageLog:
    def __init__(self, max_lines=8):
        self.lines = []
        self.max_lines = max_lines
        self.scroll = 0

    def add(self, text):
        self.lines.append(text)
        if len(self.lines) > 200:
            self.lines = self.lines[-200:]
        self.scroll = 0

    def wheel(self, dy):
        if not self.lines:
            return
        self.scroll = clamp(self.scroll + dy, 0, max(0, len(self.lines) - 1))

    def draw(self, screen, rect):
        draw_bevel_panel(screen, rect, fill=(30, 28, 26), border=(120, 98, 58), radius=10, alpha=220)
        draw_frame(screen, rect, tone="bronze")

        pad = 10
        x = rect.x + pad
        y = rect.y + pad
        y = draw_header_text(screen, "Chronicle", x, y, color=(240, 230, 210))
        pygame.draw.line(screen, (110, 90, 55), (x, y), (rect.right - pad, y), 1)
        y += 6

        idx_end = len(self.lines) - self.scroll
        idx_start = max(0, idx_end - self.max_lines)
        for l in self.lines[idx_start:idx_end]:
            y = draw_footer_text(screen, "• " + l, x, y, color=(220, 210, 190))

def make_crest(size, seed=0):
    rnd = random.Random(seed)
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pts = [(w*0.15, h*0.08), (w*0.85, h*0.08), (w*0.92, h*0.35), (w*0.5, h*0.95), (w*0.08, h*0.35)]
    c1 = rnd.choice([(175, 40, 40), (30, 85, 175), (45, 140, 75), (180, 150, 45)])
    c2 = rnd.choice([(245, 235, 210), (230, 230, 235), (28, 28, 28), (200, 110, 35)])
    pygame.draw.polygon(surf, c1, pts)
    pat = rnd.choice(["stripes", "cross"])
    if pat == "stripes":
        for i in range(6):
            x = int((i / 6) * w)
            pygame.draw.rect(surf, c2, (x, 0, max(1, w//10), h))
    else:
        pygame.draw.rect(surf, c2, (w*0.42, 0, w*0.16, h))
        pygame.draw.rect(surf, c2, (0, h*0.42, w, h*0.16))
    pygame.draw.polygon(surf, (18, 14, 10), pts, width=3)
    pygame.draw.polygon(surf, (210, 185, 120), pts, width=1)
    return surf

class SidePanel:
    def __init__(self, rect):
        self.rect = rect
        self.crest = make_crest((56, 68), seed=11)
        self.selected_province = None
        self.selected_title = "Kingdom of Aragon"
        self.selected_ruler = "King Sancho II"
        self.reputation = "Honourable reputation"
        self.portrait = self._portrait()

    def _portrait(self):
        w, h = 140, 170
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        base = create_noise_surface((w, h), base=(92, 82, 66), variance=20, seed=101).convert_alpha()
        s.blit(base, (0, 0))
        pygame.draw.ellipse(s, (30, 25, 22, 220), (36, 40, 70, 86))
        pygame.draw.rect(s, (30, 25, 22, 220), (58, 110, 34, 32), border_radius=8)
        pygame.draw.rect(s, (120, 98, 58), (0, 0, w, h), width=3, border_radius=12)
        return s

    def draw(self, screen):
        draw_bevel_panel(screen, self.rect, fill=(28, 26, 22), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")
        pad = 12
        x = self.rect.x + pad
        y = self.rect.y + pad
        y = draw_title_text(screen, self.selected_title, x, y, color=(240, 230, 210))
        screen.blit(self.portrait, (x, y + 8))
        screen.blit(self.crest, (x + 152, y + 18))
        y += 200
        y = draw_header_text(screen, "Court", x, y, color=(235, 225, 205))
        y = draw_body_text(screen, f"Ruler: {self.selected_ruler}", x, y, color=(220, 210, 190))
        y = draw_body_text(screen, f"Standing: {self.reputation}", x, y, color=(210, 200, 180))
        y += 8
        y = draw_header_text(screen, "Domain", x, y, color=(235, 225, 205))
        if self.selected_province:
            p = self.selected_province
            y = draw_body_text(screen, f"Selected: {p.name}", x, y, color=(245, 235, 215))
            y = draw_body_text(screen, f"Liege: {p.liege}", x, y, color=(220, 210, 190))
            y = draw_body_text(screen, f"Tax: {p.tax}  |  Levy: {p.levy}", x, y, color=(220, 210, 190))
            y = draw_body_text(screen, f"Development: {p.dev}/10", x, y, color=(220, 210, 190))

class TopBar:
    def __init__(self, rect):
        self.rect = rect
        self.crest = make_crest((46, 56), seed=3)
        self.gold = 266
        self.prestige = 57
        self.piety = 106
        self.date_str = "January 24, 1068"
        self.buttons = {k: None for k in ["pause","slow","play","fast","ledger","realm"]}

    def draw(self, screen):
        draw_bevel_panel(screen, self.rect, fill=(32, 28, 24), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")
        pad = 10
        x = self.rect.x + pad
        y0 = self.rect.y + 8
        screen.blit(self.crest, (x, self.rect.y + 8))
        x += 58
        draw_footer_text(screen, "+1", x, y0, color=(200, 190, 170)); x += 34
        pygame.draw.circle(screen, (215, 185, 110), (x + 8, y0 + 10), 6)
        draw_footer_text(screen, f"{self.gold}", x + 18, y0, color=(240, 230, 210)); x += 80
        pygame.draw.circle(screen, (165, 165, 175), (x + 8, y0 + 10), 6)
        draw_footer_text(screen, f"{self.prestige}", x + 18, y0, color=(240, 230, 210)); x += 70
        pygame.draw.circle(screen, (140, 210, 140), (x + 8, y0 + 10), 6)
        draw_footer_text(screen, f"{self.piety}", x + 18, y0, color=(240, 230, 210))
        date_w = HEADER_FONT.size(self.date_str)[0]
        draw_header_text(screen, self.date_str, self.rect.right - pad - date_w, self.rect.y + 10, color=(240, 230, 210))
        bx = self.rect.centerx - 220
        by = self.rect.y + 8
        bw, bh = 62, 30
        self.buttons["pause"] = draw_secondary_button(screen, "||", bx, by, bw, bh)
        self.buttons["slow"]  = draw_secondary_button(screen, "<", bx + 70, by, bw, bh)
        self.buttons["play"]  = draw_primary_button(screen, ">", bx + 140, by, bw, bh)
        self.buttons["fast"]  = draw_secondary_button(screen, ">>", bx + 210, by, bw, bh)
        self.buttons["ledger"] = draw_secondary_button(screen, "Ledger", bx + 290, by, 86, bh)
        self.buttons["realm"]  = draw_secondary_button(screen, "Realm", bx + 386, by, 78, bh)

class RightPanel:
    def __init__(self, rect):
        self.rect = rect
        self.mode = "Council"
        self.crest = make_crest((40, 52), seed=27)
        self.actions = ["Raise Levies", "Grant Title", "Send Gift", "Arrange Marriage", "Declare War", "Offer Peace"]

    def draw(self, screen):
        draw_bevel_panel(screen, self.rect, fill=(28, 26, 22), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")
        pad = 12
        x = self.rect.x + pad
        y = self.rect.y + pad
        screen.blit(self.crest, (x, y - 2))
        draw_header_text(screen, self.mode, x + 52, y + 4, color=(240, 230, 210))
        y += 52
        btn_w = self.rect.w - pad * 2
        btn_h = 30
        for i, a in enumerate(self.actions):
            draw_secondary_button(screen, a, x, y + i * (btn_h + 8), btn_w, btn_h)
        y2 = self.rect.bottom - pad - 40
        draw_accept_button(screen, "Confirm", x, y2, (btn_w // 2) - 6, 34)
        draw_deny_button(screen, "Cancel", x + (btn_w // 2) + 6, y2, (btn_w // 2) - 6, 34)

# =========================
# UI wrapper
# =========================
class GameUI:
    def __init__(self, screen):
        self.screen = screen
        self.log = MessageLog(max_lines=7)
        self.selected_province = None
        self._rebuild()
        self.log.add("If you see MAP DIAGNOSTIC + a colored preview, this file is running.")

    def _rebuild(self):
        w, h = self.screen.get_size()
        self.bg_tex = create_noise_surface((w, h), base=(20, 18, 16), variance=12, seed=2)

        self.world_map = ProceduralMap(size=(3200, 2000), seed=7)

        pad = 10
        top_h = 72
        bottom_h = 130
        left_w = 330
        right_w = 320

        self.top_rect = pygame.Rect(pad, pad, w - pad * 2, top_h)
        self.bottom_rect = pygame.Rect(pad, h - bottom_h - pad, w - pad * 2, bottom_h)
        self.left_rect = pygame.Rect(pad, self.top_rect.bottom + pad, left_w, h - top_h - bottom_h - pad * 4)
        self.right_rect = pygame.Rect(w - right_w - pad, self.top_rect.bottom + pad, right_w, h - top_h - bottom_h - pad * 4)

        map_x = self.left_rect.right + pad
        map_y = self.top_rect.bottom + pad
        map_w = w - (left_w + right_w + pad * 4)
        map_h = h - (top_h + bottom_h + pad * 4)
        self.map_rect = pygame.Rect(map_x, map_y, map_w, map_h)

        self.topbar = TopBar(self.top_rect)
        self.side = SidePanel(self.left_rect)
        self.right = RightPanel(self.right_rect)
        self.map_view = MapView(self.map_rect, self.world_map)

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            self._rebuild()

        self.map_view.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = self.map_view.pick_province(event.pos)
            if p:
                self.selected_province = p
                self.side.selected_province = p
                self.side.selected_title = p.liege
                self.log.add(f"Selected {p.name} ({p.liege}).")

    def update(self, dt):
        self.map_view.update(dt)

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.screen.blit(self.bg_tex, (0, 0))

        self.map_view.draw(self.screen)
        self.topbar.draw(self.screen)
        self.side.draw(self.screen)
        self.right.draw(self.screen)
        self.log.draw(self.screen, self.bottom_rect)

# =========================
# Entry
# =========================
def main():
    pygame.init()
    pygame.display.set_caption("Grand Strategy UI — CK1-inspired (Pygame) — COLOR FIX BUILD")
    screen = pygame.display.set_mode((1360, 820), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    ui = GameUI(screen)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            ui.handle_event(event)
        ui.update(dt)
        ui.draw()
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
