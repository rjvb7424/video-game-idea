import pygame

from ui.buttons import (
    draw_primary_button,
    draw_secondary_button,
    draw_accept_button,
    draw_deny_button,
)
from ui.panels import draw_framed_panel
from ui.text import draw_body_text, wrap_text
from ui.theme import BODY_FONT, INK


class Modal:
    def __init__(self):
        self.open = False
        self.title = "Menu"
        self.lines = []
        self.actions = []
        self._on_close = None

    def show(self, title, lines, actions, on_close=None):
        self.open = True
        self.title = title
        self.lines = lines[:]
        self.actions = actions[:]
        self._on_close = on_close

    def close(self):
        self.open = False
        if self._on_close:
            cb = self._on_close
            self._on_close = None
            cb()

    def draw(self, surface, panel_tile):
        if not self.open:
            return []

        w, h = surface.get_size()

        rect = pygame.Rect(0, 0, 520, 300)
        rect.center = (w // 2, h // 2)

        content = draw_framed_panel(surface, rect, title=self.title, title_color=INK, tile=panel_tile)

        y = content.top
        for ln in self.lines:
            for wrapped in wrap_text(ln, BODY_FONT, content.w - 10):
                y = draw_body_text(surface, wrapped, content.left, y, color=(230, 225, 210))
            y += 2

        btns = []
        btn_h = 36
        gap = 10
        pad_x = 22
        min_w = 120
        widths = [max(min_w, BODY_FONT.size(label)[0] + pad_x * 2) for label, _, _ in self.actions]
        rows = []
        row = []
        row_width = 0
        max_row_width = max(120, content.w - 10)
        for action, btn_w in zip(self.actions, widths):
            next_width = btn_w if not row else row_width + gap + btn_w
            if row and next_width > max_row_width:
                rows.append((row, row_width))
                row = [(action, btn_w)]
                row_width = btn_w
            else:
                row.append((action, btn_w))
                row_width = next_width
        if row:
            rows.append((row, row_width))

        row_gap = 8
        total_h = len(rows) * btn_h + max(0, len(rows) - 1) * row_gap
        yb = rect.bottom - 22 - total_h

        for row_items, total in rows:
            x = content.centerx - total // 2
            for (label, kind, cb), btn_w in row_items:
                clickable = True
                if kind == "primary":
                    r = draw_primary_button(surface, label, x, yb, btn_w, btn_h)
                elif kind == "secondary":
                    r = draw_secondary_button(surface, label, x, yb, btn_w, btn_h)
                elif kind == "accept":
                    r = draw_accept_button(surface, label, x, yb, btn_w, btn_h)
                elif kind == "disabled":
                    # muted, inactive style distinct from Close
                    r = pygame.Rect(x, yb, btn_w, btn_h)
                    pygame.draw.rect(surface, (60, 60, 60), r, border_radius=8)
                    pygame.draw.rect(surface, (20, 20, 20), r, 2, border_radius=8)
                    txt = BODY_FONT.render(label, True, (150, 150, 150))
                    surface.blit(txt, txt.get_rect(center=r.center))
                    clickable = False
                else:
                    r = draw_deny_button(surface, label, x, yb, btn_w, btn_h)
                if clickable:
                    btns.append((r, cb))
                x += btn_w + gap
            yb += btn_h + row_gap

        return btns
