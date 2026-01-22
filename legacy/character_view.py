# internal imports
from ui_elements import draw_body_text, draw_header_text, draw_title_text

def draw_character_view(surface, character, x, y):
    """Draws a character view on the given surface at position (x, y)."""
    y = draw_header_text(surface, f"{character.get("fname").capitalize()} {character.get("lname").capitalize()}", x, y)
    