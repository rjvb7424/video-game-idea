# external imports
import pygame

# initialize pygame font module
pygame.font.init() 

# font constants
FONT = "arial"
COLOR = (220, 220, 220)
TITLE_FONT = pygame.font.SysFont(FONT, 24)
HEADER_FONT = pygame.font.SysFont(FONT, 20)
BODY_FONT = pygame.font.SysFont(FONT, 16)
FOOTER_FONT = pygame.font.SysFont(FONT, 14)

# button constants
BUTTON_BORDER_RADIUS = 4

# primary button colours
BUTTON_BG = (50, 50, 70)
BUTTON_BG_HOVER = (80, 80, 120)
BUTTON_TEXT_COLOR = (240, 240, 240)
BUTTON_BORDER_COLOR = (180, 180, 200)

# secondary button colours
SECONDARY_BG = (40, 40, 40)
SECONDARY_BG_HOVER = (70, 70, 70)
SECONDARY_TEXT_COLOR = (230, 230, 230)
SECONDARY_BORDER_COLOR = (160, 160, 160)

# confirm action button colours
ACCEPT_BG = (40, 90, 40)
ACCEPT_BG_HOVER = (60, 130, 60)
ACCEPT_TEXT_COLOR = (230, 255, 230)
ACCEPT_BORDER_COLOR = (120, 200, 120)

# cancel action button colours
DENY_BG = (110, 40, 40)
DENY_BG_HOVER = (150, 60, 60)
DENY_TEXT_COLOR = (255, 230, 230)
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
