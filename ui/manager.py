import os
import pygame

from core.geometry import shield_points
from core.surfaces import make_noise_tile, tile_fill
from systems.buildings import BUILDINGS
from systems.traits import trait_alignment, compute_piety_rate, trait_name
from ui.buttons import (
    draw_primary_button,
    draw_secondary_button,
    draw_deny_button,
)
from ui.panels import draw_framed_panel
from ui.text import draw_header_text, draw_body_text, draw_footer_text, wrap_text
from ui.theme import (
    BODY_FONT,
    FOOTER_FONT,
    HEADER_FONT,
    INK,
)


class UIManager:
    def __init__(self, seed=11):
        header_color = (70, 0, 18)
        # Textures used across panels (precomputed)
        self.panel_tile = make_noise_tile((96, 96), (44, 44, 46), variance=10, alpha=255, seed=seed)
        self.top_tile = make_noise_tile((128, 64), header_color, variance=10, alpha=255, seed=seed + 1)
        self.bottom_tile = make_noise_tile((96, 96), (26, 26, 28), variance=10, alpha=255, seed=seed + 2)
        self.left_tile = make_noise_tile((96, 96), (52, 36, 26), variance=12, alpha=255, seed=seed + 3)
        self.biome_images = {}
        self._biome_image_cache = {}
        self._load_biome_images()

    def _load_biome_images(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
        path = os.path.join(base_dir, "boreal_forest.png")
        if os.path.exists(path):
            self.biome_images["boreal_forest"] = pygame.image.load(path).convert_alpha()

    @staticmethod
    def _biome_key(biome):
        if not biome:
            return None
        key = str(biome).strip().lower().replace(" ", "_")
        if key == "forest":
            key = "boreal_forest"
        return key

    @staticmethod
    def _biome_label(biome):
        if not biome:
            return "Unknown"
        key = str(biome).strip().lower().replace(" ", "_")
        if key in ("forest", "boreal_forest"):
            return "Boreal Forest"
        return str(biome).replace("_", " ").title()

    def _get_biome_thumb(self, biome_key, max_w, max_h):
        if not biome_key:
            return None
        img = self.biome_images.get(biome_key)
        if img is None:
            return None
        max_w = max(1, int(max_w))
        max_h = max(1, int(max_h))
        cache_key = (biome_key, max_w, max_h)
        cached = self._biome_image_cache.get(cache_key)
        if cached is not None:
            return cached
        w, h = img.get_size()
        scale = min(max_w / w, max_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        thumb = pygame.transform.smoothscale(img, (new_w, new_h))
        self._biome_image_cache[cache_key] = thumb
        return thumb

    def _draw_biome_image(self, surface, x, y, max_w, y_limit, biome_key):
        thumb = self._get_biome_thumb(biome_key, max_w, 96)
        if thumb is None:
            return y
        img_rect = thumb.get_rect(topleft=(x, y))
        if img_rect.bottom + 8 > y_limit:
            return y
        frame = img_rect.inflate(6, 6)
        pygame.draw.rect(surface, (18, 18, 18), frame, border_radius=6)
        pygame.draw.rect(surface, (0, 0, 0), frame, 1, border_radius=6)
        surface.blit(thumb, img_rect.topleft)
        return img_rect.bottom + 8

    def draw_top_bar(self, surface, rect, state):
        btns = []

        # --- Responsive sizing ---
        pad = max(10, rect.w // 120)
        gap = max(10, rect.w // 140)
        bh = max(34, int(rect.h * 0.62))
        y = rect.centery - bh // 2

        top_red = (90, 0, 22)

        # --- Background ---
        pygame.draw.rect(surface, top_red, rect)
        tile_fill(surface, rect, self.top_tile)
        pygame.draw.line(surface, (90, 86, 78), (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1))
        pygame.draw.line(surface, (0, 0, 0), (rect.left, rect.bottom - 2), (rect.right, rect.bottom - 2))

        # ---------- RIGHT SIDE: Menu ----------
        menu_label = "Menu"
        menu_w = max(92, BODY_FONT.size(menu_label)[0] + 28)
        menu_rect = pygame.Rect(rect.right - pad - menu_w, y, menu_w, bh)
        b_menu = draw_secondary_button(surface, menu_label, menu_rect.x, menu_rect.y, menu_rect.w, menu_rect.h)
        btns.append((b_menu, "open_menu"))

        right_edge = menu_rect.left - gap

        # ---------- RIGHT SIDE: Population ----------
        pop_value = state.get("population")
        if pop_value is not None:
            pop_text = self._format_population(pop_value)
            pop_w = max(190, BODY_FONT.size(f"Population: {pop_text}")[0] + 36)
            pop_rect = pygame.Rect(right_edge - pop_w, y, pop_w, bh)
            self._draw_resource(surface, pop_rect, "Population", pop_text, rate=None, icon_color=(120, 160, 120))
            right_edge = pop_rect.left - gap

        # ---------- RIGHT SIDE: Food / Threat bars ----------
        food = state.get("food")
        threat = state.get("threat")
        if food is not None:
            bar_w = 160
            food_rect = pygame.Rect(right_edge - bar_w, y, bar_w, bh)
            food_color = (190, 140, 70)  # balanced (orange)
            if isinstance(food, (tuple, list)) and len(food) == 2:
                produced, consumed = float(food[0]), float(food[1])
                if consumed <= 0:
                    if produced > 0:
                        food_color = (100, 170, 100)  # surplus
                else:
                    ratio = produced / consumed
                    if ratio >= 1.02:
                        food_color = (100, 170, 100)  # surplus
                    elif ratio <= 0.98:
                        food_color = (170, 80, 80)  # deficit
            self._draw_meter(surface, food_rect, "Food", food, fill_color=food_color)
            right_edge = food_rect.left - gap
        if threat is not None:
            bar_w = 160
            threat_rect = pygame.Rect(right_edge - bar_w, y, bar_w, bh)
            self._draw_meter(surface, threat_rect, "Threat", threat, fill_color=(170, 90, 90))
            right_edge = threat_rect.left - gap

        # ---------- MIDDLE: Resources fill the remaining space ----------
        res = state["resources"]
        x_left = rect.left + pad
        avail = max(0, right_edge - x_left)

        min_pill = 150
        max_pill = 190

        def pill_rect(x, w):
            return pygame.Rect(x, y, w, bh)

        if avail >= (2 * min_pill + gap):
            per_w = min(max_pill, (avail - gap) // 2)
            r1 = pill_rect(x_left, per_w)
            r2 = pill_rect(r1.right + gap, per_w)

            self._draw_resource(surface, r1, "Gold", res["gold"], res.get("gold_rate", 0), icon_color=(190, 165, 90))
            self._draw_resource(surface, r2, "Piety", res["piety"], res.get("piety_rate", 0), icon_color=(165, 150, 110))

        elif avail >= 120:
            r1 = pill_rect(x_left, min(avail, max_pill))
            self._draw_resource(surface, r1, "Gold", res["gold"], res.get("gold_rate", 0), icon_color=(190, 165, 90))

        return btns

    def _draw_resource(self, surface, rect, label, value, rate=None, icon_color=(200, 200, 200)):
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

        if rate is None:
            rate_surf = None
        else:
            rate_text = f" ({rate:+d})"
            rate_surf = FOOTER_FONT.render(rate_text, True, (160, 155, 145))

        text_x = icon_cx + 16

        main_y = rect.centery - main_surf.get_height() // 2
        rate_y = rect.centery - (rate_surf.get_height() // 2 if rate_surf is not None else 0)

        max_x = rect.right - 10
        if rate_surf is not None and (text_x + main_surf.get_width() + rate_surf.get_width() > max_x):
            rate_surf = None

        surface.blit(main_surf, (text_x, main_y))
        if rate_surf is not None:
            surface.blit(rate_surf, (text_x + main_surf.get_width(), rate_y))

    def _draw_meter(self, surface, rect, label, value, fill_color=(120, 160, 120)):
        pygame.draw.rect(surface, (22, 22, 22), rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=8)

        if isinstance(value, (tuple, list)) and len(value) == 2:
            produced = max(0, int(round(value[0])))
            consumed = max(0, int(round(value[1])))
            label_text = f"{label}: {produced:,}/{consumed:,}"
            if consumed <= 0:
                ratio = 2.0 if produced > 0 else 0.0
            else:
                ratio = produced / consumed
            # Centered meter: 1.0 ratio sits at 50%
            value = int(max(0.0, min(2.0, ratio)) * 50.0)
        else:
            value = max(0, min(100, int(value)))
            label_text = f"{label}: {value}%"
        label_surf = FOOTER_FONT.render(label_text, True, (235, 228, 210))
        surface.blit(label_surf, (rect.left + 10, rect.top + 6))

        bar_h = 6
        bar_rect = pygame.Rect(rect.left + 10, rect.bottom - 10 - bar_h, rect.w - 20, bar_h)
        pygame.draw.rect(surface, (45, 45, 45), bar_rect, border_radius=4)
        fill_w = int(bar_rect.w * (value / 100.0))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_rect.h)
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=4)

    def draw_left_panel(self, surface, rect, state):
        content = draw_framed_panel(surface, rect, title="Ruler", title_color=INK, tile=self.left_tile)

        # extra warm tint over the inner area for stronger brown vibe
        tint = pygame.Surface((rect.w - 28, rect.h - 28), pygame.SRCALPHA)
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
        virtues, sins, _ = trait_alignment(c)
        p_rate, _breakdown = compute_piety_rate(c)

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

        # Buttons at bottom
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
        sel = state["selected_province"]
        title = sel.name if sel is not None else "Province"
        content = draw_framed_panel(surface, rect, title=title, title_color=INK, tile=self.panel_tile)

        # Reserve bottom space so nothing overlaps buttons
        btn_bar_y = rect.bottom - 56
        btn_h = 34
        gap = 8
        y_limit = btn_bar_y - 10

        y = content.top
        btns = []

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
            biome_key = self._biome_key(sel.biome)
            biome_label = self._biome_label(sel.biome)
            safe_header("Biome", color=(235, 228, 210))
            y = self._draw_biome_image(surface, content.left, y, content.w - 6, y_limit, biome_key)
            safe_body(biome_label, color=(220, 214, 198))
            safe_body(f"Culture: {sel.culture}")
            safe_body(f"Faith: {sel.faith}")

            if y + 18 < y_limit:
                y += 6
                pygame.draw.line(surface, (0, 0, 0), (content.left, y), (content.right, y))
                pygame.draw.line(surface, (80, 74, 66), (content.left, y + 1), (content.right, y + 1))
                y += 10

            # Buildings + realm + ruler
            rid = sel.realm_id
            realm_name = state["realm_names"][rid]
            ruler = state["realm_rulers"][rid]

            # Buildings
            safe_header("Buildings")
            buildings = getattr(sel, "buildings", [])
            if buildings:
                for i, bid in enumerate(buildings):
                    if bid is None:
                        label = f"• Slot {i + 1}: Empty"
                    else:
                        bdef = BUILDINGS.get(bid)
                        bname = bdef.name if bdef else bid
                        label = f"• Slot {i + 1}: {bname}"
                    if not safe_body(label):
                        break
            else:
                safe_body("No building slots.")

            if buildings:
                in_player_realm = rid == state.get("player_realm_id")
                has_empty = any(b is None for b in buildings)
                build_btn_h = 28
                build_btn_w = min(140, content.w)
                if in_player_realm and has_empty and (y + build_btn_h <= y_limit):
                    btn_rect = draw_primary_button(surface, "Build Farm", content.left, y, build_btn_w, build_btn_h)
                    btns.append((btn_rect, "build_farm"))
                    y = btn_rect.bottom + 6
                elif in_player_realm and not has_empty:
                    safe_footer("Building slots full.")

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

        # Buttons at bottom
        bx = content.left
        by = btn_bar_y
        b1 = draw_secondary_button(surface, "View Realm", bx, by, 120, btn_h)
        b2 = draw_primary_button(surface, "Set Rally", bx + 130, by, 120, btn_h)
        b3 = draw_secondary_button(surface, "Council", bx + 260, by, 120, btn_h)
        btns.append((b1, "view_realm"))
        btns.append((b2, "set_rally"))
        btns.append((b3, "council"))
        return btns

    def draw_bottom_bar(self, surface, rect, state):
        pygame.draw.rect(surface, (14, 14, 14), rect)
        tile_fill(surface, rect, self.bottom_tile)
        pygame.draw.line(surface, (90, 86, 78), (rect.left, rect.top), (rect.right, rect.top))
        pygame.draw.line(surface, (0, 0, 0), (rect.left, rect.top + 1), (rect.right, rect.top + 1))

        pad = max(10, rect.w // 120)
        gap = max(10, rect.w // 140)
        bh = max(34, int(rect.h * 0.62))
        y = rect.centery - bh // 2

        # Time controls on bottom-right corner
        time_btns, time_left_edge = self._draw_time_controls(surface, rect.right - pad, y, bh, state)

        # Date block just to the left of time controls
        date_text = str(state["date"])
        date_w = max(220, HEADER_FONT.size(date_text)[0] + 44)
        date_x = max(rect.left + pad, time_left_edge - gap - date_w)
        date_block = pygame.Rect(date_x, y, date_w, bh)
        pygame.draw.rect(surface, (22, 22, 22), date_block, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), date_block, 2, border_radius=8)
        date_surf = HEADER_FONT.render(date_text, True, (230, 224, 208))
        surface.blit(date_surf, date_surf.get_rect(center=date_block.center))

        btns = []
        btns.extend(time_btns)
        return btns

    @staticmethod
    def _format_population(value):
        return f"{value:,}"

    def _draw_time_controls(self, surface, right_edge, y, bh, state):
        btns = []
        sp = state["speed_level"]
        sp_label = "Paused" if sp == 0 else f"Speed {sp}"

        gap = 10
        plate_w = max(120, BODY_FONT.size(sp_label)[0] + 36)
        bw = bh
        bgap = max(8, bw // 6)

        time_cluster_w = plate_w + gap + (4 * bw + 3 * bgap)
        x_time = right_edge - time_cluster_w

        # speed plate
        plate = pygame.Rect(x_time, y, plate_w, bh)
        pygame.draw.rect(surface, (22, 22, 22), plate, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), plate, 2, border_radius=8)

        sp_surf = BODY_FONT.render(sp_label, True, (220, 214, 198))
        surface.blit(sp_surf, sp_surf.get_rect(center=plate.center))

        # time buttons
        bx = plate.right + gap
        by = y
        b_pause = draw_secondary_button(surface, "II", bx, by, bw, bh)
        b_slow = draw_secondary_button(surface, ">", bx + (bw + bgap), by, bw, bh)
        b_fast = draw_secondary_button(surface, ">>", bx + 2 * (bw + bgap), by, bw, bh)
        b_ultra = draw_secondary_button(surface, ">>>", bx + 3 * (bw + bgap), by, bw, bh)

        btns.append((b_pause, "toggle_pause"))
        btns.append((b_slow, "speed_1"))
        btns.append((b_fast, "speed_2"))
        btns.append((b_ultra, "speed_3"))

        return btns, x_time
