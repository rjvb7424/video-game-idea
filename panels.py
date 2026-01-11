# panels.py
import pygame
from ui_elements import draw_title_text, draw_header_text, draw_body_text, draw_footer_text
from config import ACCENT, MUTED_COLOR

def draw_time_panel(screen: pygame.Surface, rect: pygame.Rect, time, status_text: str):
    x = rect.x + 18
    y = rect.y + 16

    y = draw_title_text(screen, "Time System", x, y, color=ACCENT)
    y = draw_body_text(screen, f"Date: {time.date}", x, y)
    y = draw_body_text(screen, f"Speed: x{time.speed_multiplier:g}  ({'Paused' if time.paused else 'Running'})", x, y)
    y += 6
    y = draw_footer_text(screen, f"Status: {status_text}", x, y, color=MUTED_COLOR)

    y += 14
    y = draw_header_text(screen, "Controls", x, y, color=ACCENT)
    y = draw_footer_text(screen, "SPACE = Pause/Play", x, y, color=MUTED_COLOR)
    y = draw_footer_text(screen, "1 = x1, 2 = x2, 3 = x4, 4 = x8", x, y, color=MUTED_COLOR)
    y = draw_footer_text(screen, "E = Force event from registry", x, y, color=MUTED_COLOR)
    y = draw_footer_text(screen, "ESC = Quit", x, y, color=MUTED_COLOR)

def draw_realm_panel(screen: pygame.Surface, rect: pygame.Rect, player_realm):
    x = rect.x + 18
    y = rect.y + 16
    y = draw_title_text(screen, "Realm", x, y, color=ACCENT)
    y = draw_body_text(screen, f"{player_realm.name}", x, y)
    y = draw_body_text(screen, f"Gold: {player_realm.gold:.2f}", x, y)
    y = draw_footer_text(screen, f"Prestige: {player_realm.prestige}  |  Piety: {player_realm.piety}", x, y, color=MUTED_COLOR)
    y = draw_footer_text(screen, f"Development: {player_realm.development}", x, y, color=MUTED_COLOR)

def draw_county_inspector(screen: pygame.Surface, rect: pygame.Rect, selected_county):
    x = rect.x + 18
    y = rect.y + 16
    y = draw_title_text(screen, "County Inspector", x, y, color=ACCENT)

    if not selected_county:
        y = draw_footer_text(screen, "Click a county to inspect it.", x, y, color=MUTED_COLOR)
        return

    realm = selected_county.realm
    ruler = realm.ruler

    y = draw_body_text(screen, f"County: {selected_county.name}", x, y)
    y = draw_body_text(screen, f"Realm: {realm.name}", x, y)
    y += 4
    y = draw_header_text(screen, "Ruler", x, y, color=ACCENT)
    y = draw_body_text(screen, f"{ruler.name} (Age {ruler.age})", x, y)
    y = draw_footer_text(screen, f"Loyalty {ruler.loyalty} | Opinion {ruler.opinion_of_player} | Intrigue {ruler.intrigue}", x, y, color=MUTED_COLOR)
    y = draw_footer_text(screen, f"Realm Gold {realm.gold:.2f} | Prestige {realm.prestige} | Piety {realm.piety}", x, y, color=MUTED_COLOR)
