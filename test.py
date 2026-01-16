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
# CK1-inspired UI foundation (procedural art, fully interactive)
# =========================

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

def mix_color(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )

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

def draw_vignette(surface, strength=70):
    # less heavy than before so map stays colorful
    w, h = surface.get_size()
    vg = pygame.Surface((w, h), pygame.SRCALPHA)
    bands = 18
    for i in range(bands):
        t = i / (bands - 1)
        a = int(lerp(0, strength, t))
        pygame.draw.rect(vg, (0, 0, 0, a), (i * 10, i * 10, w - i * 20, h - i * 20), width=10, border_radius=28)
    surface.blit(vg, (0, 0))

def make_crest(size, seed=0):
    rnd = random.Random(seed)
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    shield = pygame.Surface((w, h), pygame.SRCALPHA)
    pts = [(w*0.15, h*0.08), (w*0.85, h*0.08), (w*0.92, h*0.35), (w*0.5, h*0.95), (w*0.08, h*0.35)]
    c1 = rnd.choice([(165, 35, 35), (30, 80, 160), (45, 130, 70), (170, 140, 40)])
    c2 = rnd.choice([(245, 235, 210), (230, 230, 230), (28, 28, 28), (190, 105, 35)])
    pygame.draw.polygon(shield, c1, pts)

    pat = rnd.choice(["stripes", "cross", "chevron", "quartered"])
    if pat == "stripes":
        for i in range(6):
            x = int((i / 6) * w)
            pygame.draw.rect(shield, c2, (x, 0, max(1, w//10), h))
    elif pat == "cross":
        pygame.draw.rect(shield, c2, (w*0.42, 0, w*0.16, h))
        pygame.draw.rect(shield, c2, (0, h*0.42, w, h*0.16))
    elif pat == "chevron":
        pygame.draw.polygon(shield, c2, [(w*0.1, h*0.2), (w*0.5, h*0.62), (w*0.9, h*0.2), (w*0.9, h*0.34), (w*0.5, h*0.78), (w*0.1, h*0.34)])
    else:
        pygame.draw.rect(shield, c2, (0, 0, w/2, h/2))
        pygame.draw.rect(shield, c2, (w/2, h/2, w/2, h/2))

    pygame.draw.polygon(shield, (18, 14, 10), pts, width=3)
    pygame.draw.polygon(shield, (210, 185, 120), pts, width=1)
    surf.blit(shield, (0, 0))
    return surf

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
        view = self.lines[idx_start:idx_end]

        for l in view:
            y = draw_footer_text(screen, "• " + l, x, y, color=(220, 210, 190))

class Province:
    def __init__(self, pid, name, rect, color, liege):
        self.id = pid
        self.name = name
        self.rect = pygame.Rect(rect)
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
        self.surface = pygame.Surface(size).convert()
        self.provinces = []
        self._generate()

    def _generate(self):
        w, h = self.size

        # Ocean base
        for y in range(h):
            t = y / (h - 1)
            ocean = mix_color((8, 16, 22), (10, 28, 36), t)
            pygame.draw.line(self.surface, ocean, (0, y), (w, y))

        # land blobs
        land = pygame.Surface((w, h), pygame.SRCALPHA)
        land.fill((0, 0, 0, 0))
        for _ in range(38):
            cx = self.rnd.randint(int(w * 0.12), int(w * 0.88))
            cy = self.rnd.randint(int(h * 0.18), int(h * 0.86))
            rx = self.rnd.randint(180, 560)
            ry = self.rnd.randint(140, 420)
            col = (55, 65, 42, 240)
            pygame.draw.ellipse(land, col, (cx - rx, cy - ry, rx * 2, ry * 2))
        self.surface.blit(land, (0, 0))

        # subtle terrain noise
        noise = create_noise_surface((w, h), base=(38, 42, 32), variance=18, seed=self.seed + 33)
        noise.set_alpha(65)
        self.surface.blit(noise, (0, 0))

        self._make_provinces()
        self._post_fx()

    def _name_for(self, pid):
        syll1 = ["Bar", "Car", "Mon", "Val", "Tar", "Bel", "San", "Rib", "Cor", "Gra", "Lle", "Cas", "Vil", "Tor", "Pam"]
        syll2 = ["ce", "ra", "gon", "na", "do", "lia", "va", "ça", "lon", "ria", "tes", "bri", "len", "mer", "ros"]
        syll3 = ["na", "ne", "ria", "sa", "go", "da", "ra", "lla", "dor", "tia", "ña", "es", "no", "re", "te"]
        rnd = random.Random(self.seed * 1000 + pid * 13)
        return rnd.choice(syll1) + rnd.choice(syll2) + rnd.choice(syll3)

    def _make_provinces(self):
        w, h = self.size
        rnd = self.rnd

        realm_names = ["Kingdom of Aragon", "Duchy of Aquitaine", "County of Foix", "Emirate of Zaragoza", "Kingdom of Navarra"]

        # richer, more separated base colors (so provinces are clearly distinct)
        realm_cols = [
            ((170, 35, 35), (250, 230, 160)),
            ((28, 72, 165), (235, 235, 245)),
            ((140, 78, 28), (240, 200, 130)),
            ((35, 120, 70), (235, 235, 200)),
            ((170, 145, 35), (250, 240, 215)),
        ]

        # "theatre" region where provinces exist
        belt = pygame.Rect(int(w * 0.10), int(h * 0.40), int(w * 0.80), int(h * 0.50))

        cols = 14
        rows = 7
        cell_w = belt.w / cols
        cell_h = belt.h / rows

        margin = 10  # ensures NO overlap
        radius = 10

        pid = 1
        self.provinces.clear()

        for ry in range(rows):
            for rx in range(cols):
                if rnd.random() < 0.12:
                    continue  # gaps become wilderness/sea

                cx = belt.x + int(rx * cell_w)
                cy = belt.y + int(ry * cell_h)
                cw = int(cell_w)
                ch = int(cell_h)

                # strictly within cell, shrunk by margin -> cannot overlap
                rect = pygame.Rect(cx + margin, cy + margin, cw - margin * 2, ch - margin * 2)
                if rect.w < 80 or rect.h < 70:
                    continue

                realm_i = (rx // 4 + ry // 2) % len(realm_names)
                base, accent = realm_cols[realm_i]
                v = rnd.uniform(0.05, 0.30)
                c = mix_color(base, accent, v)

                name = self._name_for(pid)
                liege = realm_names[realm_i]
                self.provinces.append(Province(pid, name, rect, c, liege))
                pid += 1

        # paint provinces
        for p in self.provinces:
            pygame.draw.rect(self.surface, p.color, p.rect, border_radius=radius)

            tex = create_noise_surface((p.rect.w, p.rect.h), base=(32, 30, 24), variance=22, seed=self.seed + p.id * 17)
            tex.set_alpha(35)
            self.surface.blit(tex, p.rect.topleft)

            # gentle edge shading (less heavy)
            edge = pygame.Surface((p.rect.w, p.rect.h), pygame.SRCALPHA)
            pygame.draw.rect(edge, (0, 0, 0, 40), (0, 0, p.rect.w, p.rect.h), width=5, border_radius=radius)
            self.surface.blit(edge, p.rect.topleft)

        # borders
        for p in self.provinces:
            pygame.draw.rect(self.surface, (18, 14, 10), p.rect, width=3, border_radius=radius)
            pygame.draw.rect(self.surface, (200, 180, 120), p.rect, width=1, border_radius=radius)

        # labels (baked)
        for p in self.provinces:
            if p.rect.w < 120 or p.rect.h < 90:
                continue
            label = p.name.upper()
            s = FOOTER_FONT.render(label, True, (240, 230, 210))
            sh = FOOTER_FONT.render(label, True, (12, 10, 8))
            r = s.get_rect(center=p.rect.center)
            self.surface.blit(sh, (r.x + 1, r.y + 1))
            self.surface.blit(s, r)

    def _post_fx(self):
        w, h = self.size
        vg = pygame.Surface((w, h), pygame.SRCALPHA)
        bands = 18
        for i in range(bands):
            t = i / (bands - 1)
            a = int(lerp(0, 95, t))
            pygame.draw.rect(vg, (0, 0, 0, a), (i * 14, i * 14, w - i * 28, h - i * 28), width=16, border_radius=90)
        self.surface.blit(vg, (0, 0))

    def provinces_bounds(self):
        if not self.provinces:
            return pygame.Rect(0, 0, *self.size)
        r = self.provinces[0].rect.copy()
        for p in self.provinces[1:]:
            r.union_ip(p.rect)
        return r

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

    def world_to_screen(self, wx, wy):
        sx = self.vp.x + (wx - self.offset_x) * self.zoom
        sy = self.vp.y + (wy - self.offset_y) * self.zoom
        return (sx, sy)

    def screen_to_world(self, sx, sy):
        wx = self.offset_x + (sx - self.vp.x) / self.zoom
        wy = self.offset_y + (sy - self.vp.y) / self.zoom
        return (wx, wy)

    def start_drag(self, mouse_pos):
        self.dragging = True
        self.drag_anchor = mouse_pos
        self.offset_anchor = (self.offset_x, self.offset_y)

    def drag(self, mouse_pos):
        if not self.dragging:
            return
        mx, my = mouse_pos
        ax, ay = self.drag_anchor
        dx = (mx - ax) / self.zoom
        dy = (my - ay) / self.zoom
        self.offset_x = self.offset_anchor[0] - dx
        self.offset_y = self.offset_anchor[1] - dy
        self._clamp()

    def end_drag(self):
        self.dragging = False

    def nudge(self, dx, dy):
        self.offset_x += dx / self.zoom
        self.offset_y += dy / self.zoom
        self._clamp()

    def zoom_at(self, mouse_pos, delta):
        mx, my = mouse_pos
        wx_before, wy_before = self.screen_to_world(mx, my)

        z = self.target_zoom * (1.0 + delta)
        self.target_zoom = clamp(z, self.min_zoom, self.max_zoom)

        temp_zoom = self.target_zoom
        self.offset_x = wx_before - (mx - self.vp.x) / temp_zoom
        self.offset_y = wy_before - (my - self.vp.y) / temp_zoom
        self._clamp()

    def update(self, dt):
        k = 12.0
        self.zoom = lerp(self.zoom, self.target_zoom, 1.0 - math.exp(-k * dt))
        self._clamp()

    def _clamp(self):
        vpw = self.vp.w / self.zoom
        vph = self.vp.h / self.zoom
        max_x = max(0, self.world_w - vpw)
        max_y = max(0, self.world_h - vph)
        self.offset_x = clamp(self.offset_x, 0, max_x)
        self.offset_y = clamp(self.offset_y, 0, max_y)

    def viewport_world_rect(self):
        return pygame.Rect(
            int(self.offset_x),
            int(self.offset_y),
            int(self.vp.w / self.zoom),
            int(self.vp.h / self.zoom),
        )

    def center_on_rect(self, world_rect, zoom=None):
        if zoom is not None:
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

        # IMPORTANT FIX: start centered on the province theatre so map isn't "blank"
        bounds = self.map.provinces_bounds().inflate(500, 360)
        self.camera.center_on_rect(bounds, zoom=0.95)

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
        draw_bevel_panel(screen, self.rect, fill=(18, 16, 14), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")

        wr = self.camera.viewport_world_rect()
        sub = self.map.surface.subsurface(wr).copy()
        scaled = pygame.transform.smoothscale(sub, (self.rect.w, self.rect.h))
        screen.blit(scaled, (self.rect.x, self.rect.y))

        # lighter atmospheric overlay (was too heavy before)
        overlay = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 22), overlay.get_rect(), border_radius=12)
        screen.blit(overlay, (self.rect.x, self.rect.y))

    def pick_province(self, screen_pos):
        if not self.rect.collidepoint(screen_pos):
            return None
        wx, wy = self.camera.screen_to_world(*screen_pos)
        for p in self.map.provinces:
            if p.rect.collidepoint((wx, wy)):
                return p
        return None

class SidePanel:
    def __init__(self, rect):
        self.rect = rect
        self.portrait = self._make_portrait()
        self.crest = make_crest((56, 68), seed=11)
        self.selected_province = None
        self.selected_title = "Kingdom of Aragon"
        self.selected_ruler = "King Sancho II"
        self.reputation = "Honourable reputation"

    def _make_portrait(self):
        w, h = 140, 170
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        base = create_noise_surface((w, h), base=(92, 82, 66), variance=20, seed=101).convert_alpha()
        surf.blit(base, (0, 0))
        pygame.draw.ellipse(surf, (30, 25, 22, 220), (36, 40, 70, 86))
        pygame.draw.rect(surf, (30, 25, 22, 220), (58, 110, 34, 32), border_radius=8)
        pygame.draw.ellipse(surf, (205, 180, 140, 180), (55, 55, 32, 36))
        pygame.draw.rect(surf, (120, 98, 58), (0, 0, w, h), width=3, border_radius=12)
        pygame.draw.rect(surf, (40, 34, 26), (4, 4, w-8, h-8), width=2, border_radius=10)
        return surf.convert_alpha()

    def draw(self, screen):
        draw_bevel_panel(screen, self.rect, fill=(28, 26, 22), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")

        pad = 12
        x = self.rect.x + pad
        y = self.rect.y + pad

        y = draw_title_text(screen, self.selected_title, x, y, color=(240, 230, 210))
        y += 4

        screen.blit(self.portrait, (x, y))
        crest_x = x + 152
        crest_y = y + 10
        screen.blit(self.crest, (crest_x, crest_y))
        y += 182

        y = draw_header_text(screen, "Court", x, y, color=(235, 225, 205))
        pygame.draw.line(screen, (110, 90, 55), (x, y), (self.rect.right - pad, y), 1)
        y += 8

        y = draw_body_text(screen, f"Ruler: {self.selected_ruler}", x, y, color=(220, 210, 190))
        y = draw_body_text(screen, f"Standing: {self.reputation}", x, y, color=(210, 200, 180))
        y += 8

        y = draw_header_text(screen, "Domain", x, y, color=(235, 225, 205))
        pygame.draw.line(screen, (110, 90, 55), (x, y), (self.rect.right - pad, y), 1)
        y += 8

        if self.selected_province:
            p = self.selected_province
            y = draw_body_text(screen, f"Selected: {p.name}", x, y, color=(245, 235, 215))
            y = draw_body_text(screen, f"Liege: {p.liege}", x, y, color=(220, 210, 190))
            y = draw_body_text(screen, f"Tax: {p.tax}  |  Levy: {p.levy}", x, y, color=(220, 210, 190))
            y = draw_body_text(screen, f"Development: {p.dev}/10", x, y, color=(220, 210, 190))
        else:
            y = draw_body_text(screen, "No province selected.", x, y, color=(200, 190, 170))

        draw_footer_text(screen, "Left-click provinces on the map", x, self.rect.bottom - 28, color=(185, 175, 155))

class TopBar:
    def __init__(self, rect):
        self.rect = rect
        self.crest = make_crest((46, 56), seed=3)
        self.gold = 266
        self.prestige = 57
        self.piety = 106
        self.date_str = "January 24, 1068"
        self.speed = 2
        self.buttons = {
            "pause": None, "slow": None, "play": None, "fast": None, "ledger": None, "realm": None
        }

    def draw(self, screen, tooltip: Tooltip):
        draw_bevel_panel(screen, self.rect, fill=(32, 28, 24), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")

        pad = 10
        x = self.rect.x + pad
        y0 = self.rect.y + 8

        screen.blit(self.crest, (x, self.rect.y + 8))
        x += 58

        draw_footer_text(screen, "+1", x, y0, color=(200, 190, 170))
        x += 34

        pygame.draw.circle(screen, (215, 185, 110), (x + 8, y0 + 10), 6)
        draw_footer_text(screen, f"{self.gold}", x + 18, y0, color=(240, 230, 210))
        x += 80

        pygame.draw.circle(screen, (165, 165, 175), (x + 8, y0 + 10), 6)
        draw_footer_text(screen, f"{self.prestige}", x + 18, y0, color=(240, 230, 210))
        x += 70

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

        mx, my = pygame.mouse.get_pos()
        for key, r in self.buttons.items():
            if r and r.collidepoint((mx, my)):
                tooltip.show({
                    "pause": "Pause time",
                    "slow": "Decrease speed",
                    "play": "Run time",
                    "fast": "Increase speed",
                    "ledger": "Open the ledger",
                    "realm": "Realm overview",
                }[key], (mx, my))
                break

    def handle_click(self, pos):
        for key, r in self.buttons.items():
            if r and r.collidepoint(pos):
                if key == "pause":
                    self.speed = 0
                    return "Time paused."
                if key == "slow":
                    self.speed = max(0, self.speed - 1)
                    return f"Speed: {self.speed}"
                if key == "play":
                    self.speed = max(1, self.speed)
                    return f"Speed: {self.speed}"
                if key == "fast":
                    self.speed = min(4, self.speed + 1)
                    return f"Speed: {self.speed}"
                if key == "ledger":
                    return "Ledger opened. (UI foundation ready to expand.)"
                if key == "realm":
                    return "Realm view opened. (UI foundation ready to expand.)"
        return None

class MiniMap:
    def __init__(self, rect, map_view: MapView):
        self.rect = rect
        self.map_view = map_view
        self.cached = None
        self.cached_size = None

    def draw(self, screen):
        draw_bevel_panel(screen, self.rect, fill=(22, 20, 18), border=(120, 98, 58), radius=10, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")

        pad = 8
        inner = pygame.Rect(self.rect.x + pad, self.rect.y + pad, self.rect.w - pad * 2, self.rect.h - pad * 2)

        if self.cached is None or self.cached_size != inner.size:
            self.cached = pygame.transform.smoothscale(self.map_view.map.surface, inner.size)
            self.cached_size = inner.size

        screen.blit(self.cached, inner.topleft)

        cam = self.map_view.camera
        wr = cam.viewport_world_rect()
        mw, mh = self.map_view.map.size
        sx = inner.x + int((wr.x / mw) * inner.w)
        sy = inner.y + int((wr.y / mh) * inner.h)
        sw = int((wr.w / mw) * inner.w)
        sh = int((wr.h / mh) * inner.h)

        pygame.draw.rect(screen, (240, 230, 210), (sx, sy, sw, sh), width=2)
        pygame.draw.rect(screen, (20, 15, 10), (sx, sy, sw, sh), width=1)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            pad = 8
            inner = pygame.Rect(self.rect.x + pad, self.rect.y + pad, self.rect.w - pad * 2, self.rect.h - pad * 2)
            if inner.collidepoint(event.pos):
                mx, my = event.pos
                tx = (mx - inner.x) / inner.w
                ty = (my - inner.y) / inner.h
                mw, mh = self.map_view.map.size
                cam = self.map_view.camera
                cam.offset_x = tx * mw - (cam.vp.w / cam.zoom) / 2
                cam.offset_y = ty * mh - (cam.vp.h / cam.zoom) / 2
                cam._clamp()

class RightPanel:
    def __init__(self, rect):
        self.rect = rect
        self.mode = "Council"
        self.crest = make_crest((40, 52), seed=27)
        self.actions = ["Raise Levies", "Grant Title", "Send Gift", "Arrange Marriage", "Declare War", "Offer Peace"]
        self.hover_action = None

    def draw(self, screen, tooltip: Tooltip):
        draw_bevel_panel(screen, self.rect, fill=(28, 26, 22), border=(120, 98, 58), radius=12, alpha=235)
        draw_frame(screen, self.rect, tone="bronze")

        pad = 12
        x = self.rect.x + pad
        y = self.rect.y + pad

        screen.blit(self.crest, (x, y - 2))
        draw_header_text(screen, self.mode, x + 52, y + 4, color=(240, 230, 210))
        y += 42
        pygame.draw.line(screen, (110, 90, 55), (x, y), (self.rect.right - pad, y), 1)
        y += 10

        btn_w = self.rect.w - pad * 2
        btn_h = 30
        mx, my = pygame.mouse.get_pos()
        self.hover_action = None

        for i, a in enumerate(self.actions[:6]):
            r = draw_secondary_button(screen, a, x, y + i * (btn_h + 8), btn_w, btn_h)
            if r.collidepoint((mx, my)):
                self.hover_action = a

        if self.hover_action:
            tooltip.show(f"{self.hover_action}\n(ready to hook into game logic)", (mx, my))

        y2 = self.rect.bottom - pad - 40
        draw_accept_button(screen, "Confirm", x, y2, (btn_w // 2) - 6, 34)
        draw_deny_button(screen, "Cancel", x + (btn_w // 2) + 6, y2, (btn_w // 2) - 6, 34)

class GameUI:
    def __init__(self, screen):
        self.screen = screen
        self.tooltip = Tooltip()
        self.log = MessageLog(max_lines=7)
        self.selected_province = None

        self._rebuild()

        self.log.add("The realm stirs beneath a cold winter sun.")
        self.log.add("Drag with middle/right mouse to pan the map.")
        self.log.add("Mouse wheel to zoom. Left-click a province to inspect.")

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

        mm_h = 150
        mm_w = self.left_rect.w - 24
        mm_x = self.left_rect.x + 12
        mm_y = self.left_rect.bottom - mm_h - 12
        self.minimap = MiniMap(pygame.Rect(mm_x, mm_y, mm_w, mm_h), self.map_view)

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            self._rebuild()

        self.tooltip.hide()

        self.map_view.handle_event(event)
        self.minimap.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            msg = self.topbar.handle_click(event.pos)
            if msg:
                self.log.add(msg)
                return

            p = self.map_view.pick_province(event.pos)
            if p:
                self.selected_province = p
                self.side.selected_province = p
                self.side.selected_title = p.liege
                self.log.add(f"Selected {p.name} ({p.liege}).")
                return

        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.bottom_rect.collidepoint((mx, my)):
                self.log.wheel(dy=-event.y)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            if event.key == pygame.K_SPACE:
                self.topbar.speed = 0 if self.topbar.speed != 0 else 2
                self.log.add("Time paused." if self.topbar.speed == 0 else f"Speed: {self.topbar.speed}")

    def update(self, dt):
        keys = pygame.key.get_pressed()
        pan_speed = 680 * dt
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.map_view.camera.nudge(-pan_speed, 0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.map_view.camera.nudge(pan_speed, 0)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.map_view.camera.nudge(0, -pan_speed)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.map_view.camera.nudge(0, pan_speed)

        self.map_view.update(dt)

    def draw_background(self):
        self.screen.fill(BG_COLOR)
        self.screen.blit(self.bg_tex, (0, 0))

        w, h = self.screen.get_size()
        grad = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(grad, (0, 0, 0, 35), (0, 0, w, h))
        pygame.draw.circle(grad, (80, 60, 30, 28), (int(w * 0.2), int(h * 0.25)), int(min(w, h) * 0.55))
        pygame.draw.circle(grad, (40, 70, 90, 22), (int(w * 0.85), int(h * 0.30)), int(min(w, h) * 0.50))
        self.screen.blit(grad, (0, 0))

    def _draw_province_overlays(self):
        mx, my = pygame.mouse.get_pos()
        hover = self.map_view.pick_province((mx, my))

        cam = self.map_view.camera

        # hover highlight (SAFE, no filled bright squares)
        if hover:
            self.tooltip.show(f"{hover.name}\n{hover.liege}", (mx, my))
            r = hover.rect
            tl = cam.world_to_screen(r.x, r.y)
            br = cam.world_to_screen(r.right, r.bottom)

            hi = pygame.Rect(int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1])).clip(self.map_rect)

            # only draw if it's actually big enough to look good
            if hi.w >= 16 and hi.h >= 16:
                pygame.draw.rect(self.screen, (240, 230, 210), hi, width=2, border_radius=10)
                pygame.draw.rect(self.screen, (20, 15, 10), hi, width=1, border_radius=10)

        # selection highlight (border only)
        if self.selected_province:
            r = self.selected_province.rect
            tl = cam.world_to_screen(r.x, r.y)
            br = cam.world_to_screen(r.right, r.bottom)
            hi = pygame.Rect(int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1])).clip(self.map_rect)
            if hi.w >= 16 and hi.h >= 16:
                pygame.draw.rect(self.screen, (210, 185, 120), hi, width=3, border_radius=10)
                pygame.draw.rect(self.screen, (0, 0, 0), hi, width=1, border_radius=10)

    def draw(self):
        self.draw_background()

        self.map_view.draw(self.screen)
        self._draw_province_overlays()

        self.topbar.draw(self.screen, self.tooltip)
        self.side.draw(self.screen)
        self.right.draw(self.screen, self.tooltip)
        self.minimap.draw(self.screen)
        self.log.draw(self.screen, self.bottom_rect)

        draw_vignette(self.screen, strength=70)
        self.tooltip.draw(self.screen)

def main():
    pygame.init()
    pygame.display.set_caption("Grand Strategy UI — CK1-inspired (Pygame)")
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
