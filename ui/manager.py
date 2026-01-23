import pygame

from core.geometry import shield_points
from core.surfaces import make_noise_tile, tile_fill
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
    UI_GUTTER,
)


class UIManager:
    def __init__(self, seed=11):
        header_color = (70, 0, 18)
        # Textures used across panels (precomputed)
        self.panel_tile = make_noise_tile((96, 96), (44, 44, 46), variance=10, alpha=255, seed=seed)
        self.top_tile = make_noise_tile((128, 64), header_color, variance=10, alpha=255, seed=seed + 1)
        self.bottom_tile = make_noise_tile((96, 96), (26, 26, 28), variance=10, alpha=255, seed=seed + 2)
        self.left_tile = make_noise_tile((96, 96), (52, 36, 26), variance=12, alpha=255, seed=seed + 3)

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

        # ---------- RIGHT SIDE: Speed plate + time buttons ----------
        sp = state["speed_level"]
        sp_label = "Paused" if sp == 0 else f"Speed {sp}"

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

        right_edge = x_time - gap

        # ---------- LEFT SIDE: Date ----------
        date_text = str(state["date"])
        date_w = max(220, HEADER_FONT.size(date_text)[0] + 44)

        x_left = rect.left + pad
        date_block = pygame.Rect(x_left, y, date_w, bh)
        pygame.draw.rect(surface, (22, 22, 22), date_block, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), date_block, 2, border_radius=8)

        date_surf = HEADER_FONT.render(date_text, True, (230, 224, 208))
        surface.blit(date_surf, date_surf.get_rect(center=date_block.center))

        x_left = date_block.right + gap

        # ---------- MIDDLE: Resources fill the remaining space ----------
        res = state["resources"]
        avail = max(0, right_edge - x_left)

        min_pill = 150
        max_pill = 190

        def pill_rect(x, w):
            return pygame.Rect(x, y, w, bh)

        if avail >= (3 * min_pill + 2 * gap):
            per_w = min(max_pill, (avail - 2 * gap) // 3)
            r1 = pill_rect(x_left, per_w)
            r2 = pill_rect(r1.right + gap, per_w)
            r3 = pill_rect(r2.right + gap, per_w)

            self._draw_resource(surface, r1, "Gold", res["gold"], res.get("gold_rate", 0), icon_color=(190, 165, 90))
            self._draw_resource(surface, r2, "Prestige", res["prestige"], res.get("prestige_rate", 0), icon_color=(150, 150, 165))
            self._draw_resource(surface, r3, "Piety", res["piety"], res.get("piety_rate", 0), icon_color=(165, 150, 110))

        elif avail >= (2 * min_pill + gap):
            per_w = min(max_pill, (avail - gap) // 2)
            r1 = pill_rect(x_left, per_w)
            r2 = pill_rect(r1.right + gap, per_w)

            self._draw_resource(surface, r1, "Gold", res["gold"], res.get("gold_rate", 0), icon_color=(190, 165, 90))
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
            rate_surf = None

        surface.blit(main_surf, (text_x, main_y))
        if rate_surf is not None:
            surface.blit(rate_surf, (text_x + main_surf.get_width(), rate_y))

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
        content = draw_framed_panel(surface, rect, title="Province / Realm", title_color=INK, tile=self.panel_tile)

        sel = state["selected_province"]

        # Reserve bottom space so nothing overlaps buttons
        btn_bar_y = rect.bottom - 56
        btn_h = 34
        gap = 8
        y_limit = btn_bar_y - 10

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
            if sel.landmark and y + 18 < y_limit:
                y += 8
                safe_header("Landmarks")
                safe_body(f"• {sel.landmark}", color=(235, 220, 185))

            # Realm + ruler
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

        # Buttons at bottom
        btns = []
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
