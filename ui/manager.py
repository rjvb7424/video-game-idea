import os
import pygame

from core.geometry import shield_points
from core.surfaces import make_noise_tile, tile_fill
from systems.buildings import (
    BUILDINGS,
    make_building,
    get_building_id,
    get_building_level,
    building_food_output,
    building_gold_upkeep,
    building_max_level,
)
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

    @staticmethod
    def _roman_numeral(value):
        if value <= 0:
            return ""
        mapping = [
            (1000, "M"),
            (900, "CM"),
            (500, "D"),
            (400, "CD"),
            (100, "C"),
            (90, "XC"),
            (50, "L"),
            (40, "XL"),
            (10, "X"),
            (9, "IX"),
            (5, "V"),
            (4, "IV"),
            (1, "I"),
        ]
        out = []
        n = int(value)
        for val, sym in mapping:
            while n >= val:
                out.append(sym)
                n -= val
        return "".join(out)

    def _draw_building_info(self, surface, x, y, y_limit, entry):
        food = building_food_output(entry)
        gold = building_gold_upkeep(entry)
        lines = [
            f"Food: +{food:,.0f} / mo",
            f"Upkeep: {gold:,.1f}g / mo",
        ]
        for line in lines:
            if y + FOOTER_FONT.get_height() + 6 > y_limit:
                break
            y = draw_footer_text(surface, line, x, y, color=(175, 168, 150))
        return y

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

        # ---------- RIGHT SIDE: Manpower ----------
        army = state.get("army")
        if isinstance(army, dict):
            max_army = int(army.get("max", 0))
            army_text = f"{max_army:,}"
            army_w = max(190, BODY_FONT.size(f"Manpower: {army_text}")[0] + 36)
            army_rect = pygame.Rect(right_edge - army_w, y, army_w, bh)
            self._draw_resource(surface, army_rect, "Manpower", army_text, rate=None, icon_color=(140, 150, 200))
            right_edge = army_rect.left - gap

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

    @staticmethod
    def _ellipsize(text, font, max_w):
        if font.size(text)[0] <= max_w:
            return text
        ell = "..."
        max_w -= font.size(ell)[0]
        if max_w <= 0:
            return ell
        trimmed = text
        while trimmed and font.size(trimmed)[0] > max_w:
            trimmed = trimmed[:-1]
        return trimmed.rstrip() + ell

    @staticmethod
    def _ruler_short_name(character):
        name = character.get("name", "Ruler")
        house = character.get("house", "")
        dynasty = house.replace("House ", "").strip() if isinstance(house, str) else ""
        titles = {"Count", "Countess", "Duke", "Duchess", "King", "Queen", "Prince", "Princess", "Baron", "Baroness"}
        parts = str(name).split()
        if parts and parts[0] in titles:
            first = " ".join(parts[1:]) if len(parts) > 1 else parts[0]
        else:
            first = str(name)
        if dynasty:
            return f"{first} {dynasty}".strip()
        return first

    def draw_left_panel_toggle(self, surface, rect, state):
        label = self._ruler_short_name(state["character"])
        bh = 30
        max_w = max(140, rect.w - 16)
        text = self._ellipsize(label, BODY_FONT, max_w - 28)
        bw = max(120, BODY_FONT.size(text)[0] + 28)
        bw = min(max_w, bw)
        bx = rect.left + 8
        by = rect.top + 8
        b = draw_secondary_button(surface, text, bx, by, bw, bh)
        return [(b, "left_panel_open")]

    def draw_left_panel(self, surface, rect, state, show_close=False):
        c = state["character"]
        house = c.get("house", "")
        dynasty = house.replace("House ", "").strip() if isinstance(house, str) else ""
        title_name = c.get("name", "Ruler")
        if dynasty:
            title_name = f"{title_name} {dynasty}"
        content = draw_framed_panel(
            surface,
            rect,
            title=title_name,
            title_color=INK,
            tile=self.left_tile,
            title_left_pad=(28 if show_close else 0),
        )

        # extra warm tint over the inner area for stronger brown vibe
        tint = pygame.Surface((rect.w - 28, rect.h - 28), pygame.SRCALPHA)
        tint.fill((70, 45, 28, 28))
        surface.blit(tint, (rect.left + 14, rect.top + 14))

        y = content.top
        btns = []

        if show_close:
            inner = rect.inflate(-14, -14)
            strip = pygame.Rect(inner.left + 6, inner.top + 6, inner.w - 12, 28)
            close_rect = pygame.Rect(strip.left + 6, strip.top + 4, 22, strip.h - 8)
            b_close = draw_deny_button(surface, "X", close_rect.x, close_rect.y, close_rect.w, close_rect.h)
            btns.append((b_close, "left_panel_close"))

        # Identity
        y = draw_header_text(surface, "Identity", content.left, y, color=(230, 224, 208))
        y = draw_body_text(surface, f"Title: {c.get('title','—')}", content.left, y, color=(220, 214, 198))
        y = draw_body_text(surface, f"Faith: {c.get('faith','—')}", content.left, y, color=(220, 214, 198))
        y = draw_body_text(surface, f"Culture: {c.get('culture','—')}", content.left, y, color=(220, 214, 198))
        gender_label = c.get("gender", "—")
        if isinstance(gender_label, str):
            gender_label = gender_label.title()
        age_label = c.get("age", "—")
        y = draw_body_text(surface, f"Gender: {gender_label}", content.left, y, color=(220, 214, 198))
        y = draw_body_text(surface, f"Age: {age_label}", content.left, y, color=(220, 214, 198))
        y += 8

        # Traits (colored by virtue/sin)
        virtues, sins, _ = trait_alignment(c)
        y = draw_header_text(surface, "Traits", content.left, y, color=(230, 224, 208))
        traits = c.get("traits", [])
        if not traits:
            y = draw_body_text(surface, "None", content.left, y, color=(185, 175, 160))
        else:
            for t in traits:
                if t in virtues:
                    color = (155, 190, 155)
                elif t in sins:
                    color = (200, 150, 150)
                else:
                    color = (235, 228, 210)
                y = draw_body_text(surface, f"• {trait_name(t)}", content.left, y, color=color)
        y += 6

        # Attributes (CK-like columns)
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
        y += 8

        # Family
        y = draw_header_text(surface, "Family", content.left, y, color=(230, 224, 208))
        spouse = c.get("spouse")
        if isinstance(spouse, dict):
            spouse_gender = spouse.get("gender", "—")
            if isinstance(spouse_gender, str):
                spouse_gender = spouse_gender.title()
            spouse_age = spouse.get("age", "—")
            y = draw_body_text(surface, f"Spouse: {spouse.get('name','—')}", content.left, y, color=(220, 214, 198))
            y = draw_footer_text(surface, f"{spouse_gender}, age {spouse_age}", content.left, y, color=(185, 175, 160))
        else:
            y = draw_body_text(surface, "Spouse: —", content.left, y, color=(185, 175, 160))

        heir = c.get("heir")
        if isinstance(heir, dict):
            heir_gender = heir.get("gender", "—")
            if isinstance(heir_gender, str):
                heir_gender = heir_gender.title()
            heir_age = heir.get("age", "—")
            y = draw_body_text(surface, f"Heir: {heir.get('name','—')}", content.left, y, color=(220, 214, 198))
            y = draw_footer_text(surface, f"{heir_gender}, age {heir_age}", content.left, y, color=(185, 175, 160))
        else:
            y = draw_body_text(surface, "Heir: —", content.left, y, color=(185, 175, 160))
        y += 6

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
        content = draw_framed_panel(surface, rect, title=title, title_color=INK, tile=self.panel_tile, title_left_pad=28)

        # Use full panel height (no bottom action buttons).
        y_limit = content.bottom - 6

        y = content.top
        btns = []

        # Close button (top-left)
        inner = rect.inflate(-14, -14)
        strip = pygame.Rect(inner.left + 6, inner.top + 6, inner.w - 12, 28)
        close_rect = pygame.Rect(strip.left + 6, strip.top + 4, 22, strip.h - 8)
        b_close = draw_deny_button(surface, "X", close_rect.x, close_rect.y, close_rect.w, close_rect.h)
        btns.append((b_close, "right_panel_close"))

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
            if not buildings:
                safe_body("No building slots.")
            else:
                slot_h = 30
                slot_gap = 6
                dropdown_gap = 4
                open_slot = state.get("building_menu_slot")

                for i, entry in enumerate(buildings):
                    if y + slot_h > y_limit:
                        break
                    bid = get_building_id(entry)
                    level = get_building_level(entry)
                    if bid:
                        bdef = BUILDINGS.get(bid)
                        bname = bdef.name if bdef else bid
                        numeral = self._roman_numeral(level)
                        if numeral:
                            label = f"Slot {i + 1}: {bname} {numeral}"
                        else:
                            label = f"Slot {i + 1}: {bname}"
                    else:
                        label = f"Slot {i + 1}: Empty"

                    is_open = open_slot == i
                    if is_open:
                        slot_rect = draw_primary_button(surface, label, content.left, y, content.w, slot_h)
                    else:
                        slot_rect = draw_secondary_button(surface, label, content.left, y, content.w, slot_h)
                    btns.append((slot_rect, f"building_slot:{i}:toggle"))
                    y = slot_rect.bottom + slot_gap

                    if not is_open:
                        continue

                    drop_left = content.left + 12
                    drop_w = max(120, content.w - 12)

                    if entry is None:
                        btn_h = 26
                        if y + btn_h <= y_limit:
                            build_rect = draw_primary_button(surface, "Build Farm", drop_left, y, min(150, drop_w), btn_h)
                            btns.append((build_rect, f"building_slot:{i}:build:farm"))
                            y = build_rect.bottom + dropdown_gap
                        preview = make_building("farm", level=1)
                        y = self._draw_building_info(surface, drop_left, y, y_limit, preview)
                    else:
                        btn_h = 26
                        level = get_building_level(entry)
                        max_level = building_max_level(entry)
                        can_upgrade = (max_level == 0) or (level < max_level)
                        if can_upgrade and y + btn_h <= y_limit:
                            up_rect = draw_secondary_button(surface, "Upgrade", drop_left, y, min(140, drop_w), btn_h)
                            btns.append((up_rect, f"building_slot:{i}:upgrade"))
                            y = up_rect.bottom + dropdown_gap
                        elif not can_upgrade:
                            if y + FOOTER_FONT.get_height() + 6 <= y_limit:
                                y = draw_footer_text(surface, "Max level reached.", drop_left, y, color=(165, 150, 140))

                        if y + btn_h <= y_limit:
                            dem_rect = draw_deny_button(surface, "Demolish", drop_left, y, min(140, drop_w), btn_h)
                            btns.append((dem_rect, f"building_slot:{i}:demolish"))
                            y = dem_rect.bottom + dropdown_gap

                        y = self._draw_building_info(surface, drop_left, y, y_limit, entry)

            safe_header("Realm")
            safe_body(realm_name, color=(235, 228, 210))

            if y + 10 < y_limit:
                y += 6

            safe_header("Ruler")
            safe_body(ruler["name"], color=(235, 228, 210))
            safe_footer(ruler["title"], color=(185, 175, 160))
            safe_body(f"Faith: {ruler.get('faith','—')}")
            safe_body(f"Culture: {ruler.get('culture','—')}")
            r_gender = ruler.get("gender", "—")
            if isinstance(r_gender, str):
                r_gender = r_gender.title()
            safe_body(f"Gender: {r_gender}")
            safe_body(f"Age: {ruler.get('age','—')}")

            spouse = ruler.get("spouse")
            if isinstance(spouse, dict):
                safe_body(f"Spouse: {spouse.get('name','—')}")
            else:
                safe_body("Spouse: —")

            heir = ruler.get("heir")
            if isinstance(heir, dict):
                safe_body(f"Heir: {heir.get('name','—')}")
            else:
                safe_body("Heir: —")

            pr, _ = compute_piety_rate(ruler)
            safe_body(f"Piety from traits: {pr:+d} / mo")

            traits = ruler.get("traits", [])
            if traits and y + 10 < y_limit:
                trait_text = " • " + " • ".join(trait_name(t) for t in traits)
                for ln in wrap_text(trait_text.strip(), BODY_FONT, content.w - 10):
                    if not safe_body(ln):
                        break

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

        btns = []
        right_edge = rect.right - pad

        # Raise army button (before time controls)
        if state.get("army") is not None:
            raising = bool(state.get("army_raising"))
            raise_label = "Raising..." if raising else "Raise Army"
            raise_w = max(132, BODY_FONT.size(raise_label)[0] + 28)
            raise_rect = pygame.Rect(right_edge - raise_w, y, raise_w, bh)
            if raising:
                b_raise = draw_secondary_button(surface, raise_label, raise_rect.x, raise_rect.y, raise_rect.w, raise_rect.h)
            else:
                b_raise = draw_primary_button(surface, raise_label, raise_rect.x, raise_rect.y, raise_rect.w, raise_rect.h)
            btns.append((b_raise, "raise_army"))
            right_edge = raise_rect.left - gap

        # Time controls on bottom-right corner
        time_btns, time_left_edge = self._draw_time_controls(surface, right_edge, y, bh, state)

        # Date block just to the left of time controls
        date_text = str(state["date"])
        date_w = max(220, HEADER_FONT.size(date_text)[0] + 44)
        date_x = max(rect.left + pad, time_left_edge - gap - date_w)
        date_block = pygame.Rect(date_x, y, date_w, bh)
        pygame.draw.rect(surface, (22, 22, 22), date_block, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), date_block, 2, border_radius=8)
        date_surf = HEADER_FONT.render(date_text, True, (230, 224, 208))
        surface.blit(date_surf, date_surf.get_rect(center=date_block.center))

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
