import pygame

from ui.theme import (
    BODY_FONT,
    BUTTON_BORDER_RADIUS,
    BUTTON_BG,
    BUTTON_BG_HOVER,
    BUTTON_TEXT_COLOR,
    BUTTON_BORDER_COLOR,
    SECONDARY_BG,
    SECONDARY_BG_HOVER,
    SECONDARY_TEXT_COLOR,
    SECONDARY_BORDER_COLOR,
    ACCEPT_BG,
    ACCEPT_BG_HOVER,
    ACCEPT_TEXT_COLOR,
    ACCEPT_BORDER_COLOR,
    DENY_BG,
    DENY_BG_HOVER,
    DENY_TEXT_COLOR,
    DENY_BORDER_COLOR,
)


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
