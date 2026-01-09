# event_ui.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, List, Dict, Tuple

import pygame

from ui_elements import (
    TITLE_FONT, HEADER_FONT, BODY_FONT,
    draw_title_text, draw_header_text, draw_body_text,
    draw_primary_button, draw_secondary_button,
    BG_COLOR, COLOR
)

# ----------------------------
# Data structures (changeable)
# ----------------------------

# Called when an option is clicked
EventCallback = Callable[[Any], None]
# Called to check if option is enabled
EnabledFn = Callable[[Any], bool]
# Called to render dynamic label text
TextFn = Callable[[Any], str]


@dataclass
class EventOption:
    """
    A single choice in an event popup.
    """
    label: str | TextFn
    on_choose: EventCallback
    enabled: bool | EnabledFn = True
    close_on_choose: bool = True
    hint: Optional[str] = None  # optional tooltip text for later


@dataclass
class EventData:
    """
    Full event popup specification.
    """
    title: str | TextFn
    body: str | TextFn
    options: List[EventOption] = field(default_factory=list)

    # Optional: small flavor header (e.g. "A Strange Visitor")
    subtitle: Optional[str | TextFn] = None

    # Optional: tag/metadata
    event_id: Optional[str] = None

    # Optional: audio hooks, etc. (unused for now)
    meta: Dict[str, Any] = field(default_factory=dict)


# ----------------------------
# Small helpers
# ----------------------------
def _resolve_text(value: str | TextFn, ctx: Any) -> str:
    if callable(value):
        return value(ctx)
    return value


def _resolve_bool(value: bool | EnabledFn, ctx: Any) -> bool:
    if callable(value):
        return bool(value(ctx))
    return bool(value)


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    """
    Simple word-wrap. Returns a list of lines that fit in max_width.
    """
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
# The Event Popup UI
# ----------------------------
class EventPopup:
    """
    Renders a CK3-like event pop-up centered on the screen with options.
    """
    def __init__(self):
        self.active: bool = False
        self.event: Optional[EventData] = None
        self.ctx: Any = None

        # for click handling
        self._option_rects: List[Tuple[pygame.Rect, EventOption, bool]] = []
        self._close_rect: Optional[pygame.Rect] = None

        # layout tuning (change freely)
        self.max_width_ratio = 0.62     # popup width vs screen width
        self.max_height_ratio = 0.78    # popup height vs screen height
        self.padding = 26
        self.button_h = 42
        self.button_gap = 10
        self.corner_radius = 10

        # colors (change freely)
        self.overlay_color = (0, 0, 0, 160)   # semi-transparent overlay
        self.panel_color = (34, 34, 38)       # popup background
        self.panel_border = (90, 90, 100)     # border
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

    def is_open(self) -> bool:
        return self.active and self.event is not None

    def handle_event(self, pg_event: pygame.event.Event) -> bool:
        """
        Returns True if the popup consumed the input (so your main UI doesn't also act).
        """
        if not self.is_open():
            return False

        if pg_event.type == pygame.KEYDOWN:
            if pg_event.key == pygame.K_ESCAPE:
                self.close()
                return True

        if pg_event.type == pygame.MOUSEBUTTONDOWN and pg_event.button == 1:
            mx, my = pg_event.pos

            # Close button (X)
            if self._close_rect and self._close_rect.collidepoint(mx, my):
                self.close()
                return True

            # Option buttons
            for rect, opt, enabled in self._option_rects:
                if enabled and rect.collidepoint(mx, my):
                    opt.on_choose(self.ctx)
                    if opt.close_on_choose:
                        self.close()
                    return True

            # Click outside popup? (optional behavior)
            # For CK3 feel, you often *don't* close on outside click.
            return True

        return True  # while open, consume input by default (CK3 modal)

    def draw(self, screen: pygame.Surface):
        if not self.is_open():
            return

        w, h = screen.get_size()

        # overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill(self.overlay_color)
        screen.blit(overlay, (0, 0))

        # popup rect sizing
        popup_w = int(w * self.max_width_ratio)
        popup_h = int(h * self.max_height_ratio)
        popup_x = (w - popup_w) // 2
        popup_y = (h - popup_h) // 2
        popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)

        # panel background + border
        pygame.draw.rect(screen, self.panel_color, popup_rect, border_radius=self.corner_radius)
        pygame.draw.rect(screen, self.panel_border, popup_rect, width=2, border_radius=self.corner_radius)

        # content bounds
        x = popup_rect.x + self.padding
        y = popup_rect.y + self.padding
        content_w = popup_rect.w - self.padding * 2

        # close "X"
        close_size = 24
        close_rect = pygame.Rect(popup_rect.right - self.padding - close_size, popup_rect.y + self.padding - 2, close_size, close_size)
        self._close_rect = close_rect

        mx, my = pygame.mouse.get_pos()
        close_col = self.close_hover if close_rect.collidepoint(mx, my) else self.close_color
        pygame.draw.rect(screen, (0, 0, 0, 0), close_rect, border_radius=6)
        # draw X
        pygame.draw.line(screen, close_col, close_rect.topleft, close_rect.bottomright, 2)
        pygame.draw.line(screen, close_col, close_rect.topright, close_rect.bottomleft, 2)

        # resolve text
        assert self.event is not None
        title = _resolve_text(self.event.title, self.ctx)
        subtitle = _resolve_text(self.event.subtitle, self.ctx) if self.event.subtitle else None
        body = _resolve_text(self.event.body, self.ctx)

        # Title
        y = draw_title_text(screen, title, x, y)
        if subtitle:
            y = draw_header_text(screen, subtitle, x, y, color=(200, 200, 210))

        y += 6

        # Body wrapped
        body_lines = _wrap_text(body, BODY_FONT, content_w)
        for line in body_lines:
            y = draw_body_text(screen, line, x, y, color=(230, 230, 235))

        # Option buttons near bottom
        self._option_rects.clear()

        # Reserve bottom area for buttons
        bottom_pad = 20
        buttons_area_bottom = popup_rect.bottom - self.padding
        buttons_area_top = max(y + 18, buttons_area_bottom - (len(self.event.options) * (self.button_h + self.button_gap)))
        by = buttons_area_top

        for i, opt in enumerate(self.event.options):
            enabled = _resolve_bool(opt.enabled, self.ctx)
            label = _resolve_text(opt.label, self.ctx)

            # Button rect full-width (CK3-like)
            rect_x = x
            rect_y = by
            rect_w = content_w
            rect_h = self.button_h

            # Draw disabled state by switching to secondary style + dim text
            if enabled:
                btn_rect = draw_primary_button(screen, label, rect_x, rect_y, rect_w, rect_h)
            else:
                btn_rect = draw_secondary_button(screen, label, rect_x, rect_y, rect_w, rect_h)
                # dim overlay to make it look disabled
                dim = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 90))
                screen.blit(dim, (rect_x, rect_y))

            self._option_rects.append((btn_rect, opt, enabled))
            by += rect_h + self.button_gap


# ----------------------------
# Event Manager (queue)
# ----------------------------
class EventUIManager:
    """
    Holds a queue of events. Shows one at a time.
    """
    def __init__(self):
        self.popup = EventPopup()
        self.queue: List[Tuple[EventData, Any]] = []

    def push(self, event: EventData, ctx: Any):
        """
        Add an event to queue. If none active, opens immediately.
        """
        if not self.popup.is_open():
            self.popup.open(event, ctx)
        else:
            self.queue.append((event, ctx))

    def update(self):
        """
        Call each frame. If popup closed and queue has events, open next.
        """
        if not self.popup.is_open() and self.queue:
            ev, ctx = self.queue.pop(0)
            self.popup.open(ev, ctx)

    def handle_event(self, pg_event: pygame.event.Event) -> bool:
        """
        Returns True if consumed.
        """
        return self.popup.handle_event(pg_event) if self.popup.is_open() else False

    def draw(self, screen: pygame.Surface):
        self.popup.draw(screen)
