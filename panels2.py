# panels2.py
import pygame
from ui_elements import draw_title_text, draw_header_text, draw_body_text, draw_footer_text, draw_primary_button, draw_secondary_button
from config import ACCENT, MUTED_COLOR
from buildings import BUILDINGS, terrain_allowed

def draw_left_panel(screen, rect, time, status_text):
    x = rect.x + 18
    y = rect.y + 16
    y = draw_title_text(screen, "Time", x, y, color=ACCENT)
    y = draw_body_text(screen, f"Date: {time.date}", x, y)
    y = draw_body_text(screen, f"Speed: x{time.speed_multiplier:g}  ({'Paused' if time.paused else 'Running'})", x, y)
    y += 6
    y = draw_footer_text(screen, status_text, x, y, color=MUTED_COLOR)
    y += 14
    y = draw_footer_text(screen, "SPACE pause | 1..4 speed | E event | ESC quit", x, y, color=MUTED_COLOR)

def draw_county_and_buildings(screen, rect, county, player_realm, on_build_request):
    x = rect.x + 18
    y = rect.y + 16

    y = draw_title_text(screen, "County", x, y, color=ACCENT)

    if county is None:
        y = draw_footer_text(screen, "Click a county on the map.", x, y, color=MUTED_COLOR)
        return

    y = draw_body_text(screen, f"{county.name}", x, y)
    y = draw_footer_text(screen, f"Terrain: {county.terrain}", x, y, color=MUTED_COLOR)
    y += 6
    y = draw_body_text(screen, f"Realm: {county.realm.name}", x, y)
    y = draw_body_text(screen, f"Ruler: {county.realm.ruler.name}", x, y)

    holding = county.holding
    y += 10
    y = draw_header_text(screen, f"Holding: {holding.name}", x, y, color=ACCENT)

    # slots
    for i, b in enumerate(holding.buildings):
        label = f"Slot {i+1}: " + (f"{b.building_id} (Lv{b.level})" if b else "Empty")
        y = draw_footer_text(screen, label, x, y, color=MUTED_COLOR)

    if holding.construction:
        c = holding.construction
        y += 6
        y = draw_footer_text(screen, f"Building: {c.building_id} ({c.days_left} days left)", x, y, color=(220, 220, 180))

    # Build options only if player controls the county
    y += 12
    if county.realm is not player_realm:
        y = draw_footer_text(screen, "You do not control this county.", x, y, color=(200, 120, 120))
        return

    y = draw_header_text(screen, "Construct Building", x, y, color=ACCENT)

    # find first empty slot
    empty_slot = None
    for i, b in enumerate(holding.buildings):
        if b is None:
            empty_slot = i
            break

    if empty_slot is None:
        y = draw_footer_text(screen, "No empty building slots.", x, y, color=MUTED_COLOR)
        return

    if holding.construction is not None:
        y = draw_footer_text(screen, "Construction in progress...", x, y, color=MUTED_COLOR)
        return

    # buttons (simple)
    btn_w = rect.w - 36
    btn_h = 36

    for bid, bdef in BUILDINGS.items():
        allowed = terrain_allowed(bid, county.terrain)
        label = f"{bdef.name}  ({bdef.cost}g, {bdef.build_days}d)"
        if allowed:
            r = draw_primary_button(screen, label, x, y, btn_w, btn_h)
            if on_build_request is not None:
                on_build_request.register_button(r, county, bid, empty_slot)
        else:
            draw_secondary_button(screen, label + " [Not suitable]", x, y, btn_w, btn_h)
        y += btn_h + 8


class BuildClickRouter:
    """
    Helps panels register clickable build buttons without coupling UI to input loop.
    """
    def __init__(self):
        self.buttons = []  # (rect, county, building_id, slot)

    def clear(self):
        self.buttons.clear()

    def register_button(self, rect, county, building_id, slot):
        self.buttons.append((rect, county, building_id, slot))

    def handle_click(self, pos):
        mx, my = pos
        for rect, county, bid, slot in self.buttons:
            if rect.collidepoint(mx, my):
                return (county, bid, slot)
        return None
