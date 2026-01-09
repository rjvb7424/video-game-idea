# event_ui.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, List, Dict, Tuple

import pygame

from ui_elements import (
    BODY_FONT,
    draw_title_text, draw_header_text, draw_body_text,
    draw_primary_button, draw_secondary_button,
)

# ----------------------------
# Data structures (changeable)
# ----------------------------

EventCallback = Callable[[Any], None]
EnabledFn = Callable[[Any], bool]
TextFn = Callable[[Any], str]


@dataclass
class EventOption:
    label: str | TextFn
    on_choose: EventCallback

    # If False, button is disabled and CANNOT be clicked
    enabled: bool | EnabledFn = True

    # Usually True (CK3 closes after choosing)
    close_on_choose: bool = True

    # Optional (tooltips later)
    hint: Optional[str] = None


@dataclass
class EventData:
    title: str | TextFn
    body: str | TextFn
    options: List[EventOption] = field(default_factory=list)

    subtitle: Optional[str | TextFn] = None
    event_id: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    # NEW: control closing behavior
    # If False -> no X button and ESC will not close. Player must choose an option.
    allow_close: bool = False

    # If True -> allow ESC to close (only matters when allow_close=True)
    allow_esc_close: bool = False

    # If True -> allow clicking outside to close (only matters when allow_close=True)
    allow_outside_click_close: bool = False


# ----------------------------
# Helpers
# ----------------------------
def _resolve_text(value: str | TextFn, ctx: Any) -> str:
    return value(ctx) if callable(value) else value


def _resolve_bool(value: bool | EnabledFn, ctx: Any) -> bool:
    return bool(value(ctx)) if callable(value) else bool(value)


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    if not text:
        return [""]

    words = text.split(" ")
    lines: List[str] = []
    current = ""

    for w in words:
        test = (current + " " + w).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w

    if current:
        lines.append(current)

    return lines


# ----------------------------
# Popup UI
# ----------------------------
class EventPopup:
    def __init__(self):
        self.active: bool = False
        self.event: Optional[EventData] = None
        self.ctx: Any = None

        self._option_rects: List[Tuple[pygame.Rect, EventOption, bool]] = []
        self._close_rect: Optional[pygame.Rect] = None
        self._popup_rect: Optional[pygame.Rect] = None

        # layout
        self.max_width_ratio = 0.62
        self.max_height_ratio = 0.78
        self.padding = 26
        self.button_h = 42
        self.button_gap = 10
        self.corner_radius = 10

        # colors
        self.overlay_color = (0, 0, 0, 160)
        self.panel_color = (34, 34, 38)
        self.panel_border = (90, 90, 100)
        self.close_color = (170, 170, 180)
        self.close_hover = (230, 230, 240)

    def open(self, event: EventData, ctx: Any):
        self.active = True
        self.event = event
        self.ctx = ctx

    def close(self):
        self.active = False
        self.event = None
        self.ctx = None
        self._option_rects.clear()
        self._close_rect = None
        self._popup_rect = None

    def is_open(self) -> bool:
        return self.active and self.event is not None

    def _clicked_outside_popup(self, mx: int, my: int) -> bool:
        if not self._popup_rect:
            return False
        return not self._popup_rect.collidepoint(mx, my)

    def handle_event(self, pg_event: pygame.event.Event) -> bool:
        """
        While open, treat as modal. It consumes input.
        Disabled options do nothing.
        Closing only possible if event.allow_close is True.
        """
        if not self.is_open():
            return False

        assert self.event is not None

        # ESC close only if explicitly allowed
        if pg_event.type == pygame.KEYDOWN:
            if pg_event.key == pygame.K_ESCAPE and self.event.allow_close and self.event.allow_esc_close:
                self.close()
                return True
            return True  # modal: consume key presses

        if pg_event.type == pygame.MOUSEBUTTONDOWN and pg_event.button == 1:
            mx, my = pg_event.pos

            # Outside click close only if allowed
            if self.event.allow_close and self.event.allow_outside_click_close and self._clicked_outside_popup(mx, my):
                self.close()
                return True

            # X close only if allowed (and exists)
            if self.event.allow_close and self._close_rect and self._close_rect.collidepoint(mx, my):
                self.close()
                return True

            # Option buttons: only enabled can trigger
            for rect, opt, enabled in self._option_rects:
                if rect.collidepoint(mx, my):
                    if not enabled:
                        # Disabled: do nothing (and still consume click)
                        return True

                    opt.on_choose(self.ctx)
                    if opt.close_on_choose:
                        self.close()
                    return True

            return True

        # Any mouse move etc is consumed while modal
        if pg_event.type in (pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            return True

        return True

    def draw(self, screen: pygame.Surface):
        if not self.is_open():
            return

        assert self.event is not None

        w, h = screen.get_size()

        # overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill(self.overlay_color)
        screen.blit(overlay, (0, 0))

        # popup rect
        popup_w = int(w * self.max_width_ratio)
        popup_h = int(h * self.max_height_ratio)
        popup_x = (w - popup_w) // 2
        popup_y = (h - popup_h) // 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)
        self._popup_rect = popup_rect

        # panel
        pygame.draw.rect(screen, self.panel_color, popup_rect, border_radius=self.corner_radius)
        pygame.draw.rect(screen, self.panel_border, popup_rect, width=2, border_radius=self.corner_radius)

        # content
        x = popup_rect.x + self.padding
        y = popup_rect.y + self.padding
        content_w = popup_rect.w - self.padding * 2

        # Close "X" ONLY if allowed
        self._close_rect = None
        if self.event.allow_close:
            close_size = 24
            close_rect = pygame.Rect(
                popup_rect.right - self.padding - close_size,
                popup_rect.y + self.padding - 2,
                close_size,
                close_size
            )
            self._close_rect = close_rect

            mx, my = pygame.mouse.get_pos()
            close_col = self.close_hover if close_rect.collidepoint(mx, my) else self.close_color
            pygame.draw.line(screen, close_col, close_rect.topleft, close_rect.bottomright, 2)
            pygame.draw.line(screen, close_col, close_rect.topright, close_rect.bottomleft, 2)

        # resolve text
        title = _resolve_text(self.event.title, self.ctx)
        subtitle = _resolve_text(self.event.subtitle, self.ctx) if self.event.subtitle else None
        body = _resolve_text(self.event.body, self.ctx)

        # Title
        y = draw_title_text(screen, title, x, y)
        if subtitle:
            y = draw_header_text(screen, subtitle, x, y, color=(200, 200, 210))
        y += 6

        # Body wrapped
        for line in _wrap_text(body, BODY_FONT, content_w):
            y = draw_body_text(screen, line, x, y, color=(230, 230, 235))

        # Buttons
        self._option_rects.clear()

        buttons_area_bottom = popup_rect.bottom - self.padding
        buttons_needed_h = len(self.event.options) * self.button_h + max(0, len(self.event.options) - 1) * self.button_gap
        buttons_area_top = max(y + 18, buttons_area_bottom - buttons_needed_h)
        by = buttons_area_top

        for opt in self.event.options:
            enabled = _resolve_bool(opt.enabled, self.ctx)
            label = _resolve_text(opt.label, self.ctx)

            rect_x, rect_y = x, by
            rect_w, rect_h = content_w, self.button_h

            if enabled:
                btn_rect = draw_primary_button(screen, label, rect_x, rect_y, rect_w, rect_h)
            else:
                btn_rect = draw_secondary_button(screen, label, rect_x, rect_y, rect_w, rect_h)
                dim = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 110))
                screen.blit(dim, (rect_x, rect_y))

            self._option_rects.append((btn_rect, opt, enabled))
            by += rect_h + self.button_gap


# ----------------------------
# Event Manager (queue)
# ----------------------------
class EventUIManager:
    def __init__(self):
        self.popup = EventPopup()
        self.queue: List[Tuple[EventData, Any]] = []

    def push(self, event: EventData, ctx: Any):
        if not self.popup.is_open():
            self.popup.open(event, ctx)
        else:
            self.queue.append((event, ctx))

    def update(self):
        if not self.popup.is_open() and self.queue:
            ev, ctx = self.queue.pop(0)
            self.popup.open(ev, ctx)

    def handle_event(self, pg_event: pygame.event.Event) -> bool:
        return self.popup.handle_event(pg_event) if self.popup.is_open() else False

    def draw(self, screen: pygame.Surface):
        self.popup.draw(screen)

    def is_open(self) -> bool:
        return self.popup.is_open()
