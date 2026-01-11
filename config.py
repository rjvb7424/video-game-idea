import pygame

BG_COLOR = (18, 18, 22)
PANEL_COLOR = (28, 28, 34)
TEXT_COLOR = (230, 230, 235)
MUTED_COLOR = (170, 170, 180)
ACCENT = (90, 160, 255)

DEFAULT_WINDOW_SIZE = (1280, 720)

# Map rendering
MAP_BG = (20, 20, 26)
COUNTY_BORDER = (35, 35, 45)
COUNTY_BORDER_HOVER = (110, 110, 130)
COUNTY_BORDER_SELECTED = (230, 230, 250)

def draw_panel(surface: pygame.Surface, rect: pygame.Rect):
    pygame.draw.rect(surface, PANEL_COLOR, rect, border_radius=10)
