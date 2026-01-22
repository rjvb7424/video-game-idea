# events.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any, List, Optional
import random

from event_ui import EventData, EventOption

# ----------------------------
# Registry pattern
# ----------------------------

@dataclass
class EventFactory:
    event_id: str
    weight: int
    can_fire: Callable[[Any], bool]     # ctx -> bool
    build: Callable[[Any], EventData]   # ctx -> EventData


class EventRegistry:
    def __init__(self, seed: int = 123):
        self.rng = random.Random(seed)
        self._events: List[EventFactory] = []

    def register(self, factory: EventFactory):
        self._events.append(factory)

    def roll(self, ctx: Any) -> Optional[EventData]:
        candidates = [e for e in self._events if e.can_fire(ctx)]
        if not candidates:
            return None

        total = sum(e.weight for e in candidates)
        pick = self.rng.uniform(0, total)
        upto = 0.0
        for e in candidates:
            upto += e.weight
            if pick <= upto:
                return e.build(ctx)

        return candidates[-1].build(ctx)


# ----------------------------
# Character compatibility helpers
# (so events can use other characters even if your class is minimal)
# ----------------------------

def ensure_character_fields(ch: Any):
    """
    Adds lightweight fields if they don't exist yet.
    This keeps events code clean even if your Character class is simple.
    """
    if not hasattr(ch, "loyalty"):
        ch.loyalty = 50  # 0..100
    if not hasattr(ch, "opinion_of_player"):
        ch.opinion_of_player = 0  # -100..100
    if not hasattr(ch, "intrigue"):
        ch.intrigue = 10  # 0..30-ish
    if not hasattr(ch, "role"):
        ch.role = "Courtier"


def ensure_ctx(ctx: dict):
    """
    Normalizes required ctx keys.
    Expected keys in your main:
      ctx = {"realm": realm, "player": realm.ruler, "characters": characters, "status": status_ref}
    """
    ctx.setdefault("rng", random.Random())
    ctx.setdefault("characters", [])
    ctx.setdefault("status", {"text": ""})

    if "player" not in ctx and "ruler" in ctx:
        ctx["player"] = ctx["ruler"]

    if "player" in ctx and ctx["player"] is not None:
        ensure_character_fields(ctx["player"])

    for ch in ctx.get("characters", []):
        ensure_character_fields(ch)


def player(ctx) -> Any:
    return ctx["player"]


def pick_non_player(ctx, predicate: Callable[[Any], bool] | None = None) -> Optional[Any]:
    """
    Pick a character that is not the player.
    Optional predicate to filter candidates.
    """
    ensure_ctx(ctx)
    rng = ctx["rng"]
    p = player(ctx)

    candidates = [c for c in ctx["characters"] if c is not p]
    if predicate:
        candidates = [c for c in candidates if predicate(c)]

    if not candidates:
        return None

    return rng.choice(candidates)


def name_of(ch: Any) -> str:
    if hasattr(ch, "name"):
        return ch.name
    fname = getattr(ch, "fname", "Unknown")
    lname = getattr(ch, "lname", "")
    return (fname + " " + lname).strip()


# ----------------------------
# Basic events (player-centric)
# ----------------------------

def build_stray_cat(ctx) -> EventData:
    ensure_ctx(ctx)
    realm = ctx["realm"]
    p = player(ctx)
    status = ctx["status"]

    def adopt(c):
        inv = getattr(p, "inventory", [])
        if "Cat 🐈" not in inv:
            inv.append("Cat 🐈")
        p.inventory = inv
        status["text"] = "You adopted a cat 🐈"

    def buy_for_cat(c):
        realm.gold -= 10
        status["text"] = "You buy food and supplies. (-10 gold)"

    def ignore(c):
        status["text"] = "You ignore the strange visitor."

    def can_adopt(c):
        return "Cat 🐈" not in getattr(p, "inventory", [])

    def can_pay(c):
        return realm.gold >= 10

    return EventData(
        title="A Stray Cat Appears",
        subtitle="A Curious Visitor",
        body=lambda c: (
            f"A small cat follows {getattr(p, 'fname', 'you')} through the halls. "
            "The servants whisper it may be an omen."
        ),
        options=[
            EventOption("Adopt the cat 🐈", on_choose=adopt, enabled=can_adopt),
            EventOption("Buy food for it (-10 gold)", on_choose=buy_for_cat, enabled=can_pay),
            EventOption("Ignore it.", on_choose=ignore),
        ],
        event_id="stray_cat_001",
        allow_close=False,
    )


def build_training(ctx) -> EventData:
    ensure_ctx(ctx)
    realm = ctx["realm"]
    p = player(ctx)
    status = ctx["status"]

    def study(c):
        p.xp += 75
        status["text"] = "You study statecraft. (+75 XP)"

    def feast(c):
        realm.gold -= 15
        status["text"] = "A small feast lifts spirits. (-15 gold)"

    def rest(c):
        status["text"] = "You rest early."

    return EventData(
        title="An Evening Decision",
        subtitle="Time is a resource",
        body=lambda c: f"The day ends in {realm.name}. How will you spend the evening?",
        options=[
            EventOption("Study statecraft (+75 XP)", on_choose=study),
            EventOption("Hold a feast (-15 gold)", on_choose=feast, enabled=lambda c: realm.gold >= 15),
            EventOption("Sleep early.", on_choose=rest),
        ],
        event_id="evening_decision_001",
        allow_close=False,
    )


def build_wandering_merchant(ctx) -> EventData:
    ensure_ctx(ctx)
    realm = ctx["realm"]
    p = player(ctx)
    status = ctx["status"]

    def buy_relic(c):
        realm.gold -= 30
        inv = getattr(p, "inventory", [])
        inv.append("Curious Relic ✨")
        p.inventory = inv
        status["text"] = "You purchase a curious relic. (-30 gold)"

    def negotiate(c):
        p.xp += 25
        status["text"] = "You negotiate terms. (+25 XP)"

    def dismiss(c):
        status["text"] = "You dismiss the merchant."

    return EventData(
        title="A Wandering Merchant",
        subtitle="Opportunity knocks",
        body="A merchant arrives with odd trinkets and bold promises. One item catches your eye.",
        options=[
            EventOption("Buy the relic (-30 gold)", on_choose=buy_relic, enabled=lambda c: realm.gold >= 30),
            EventOption("Negotiate and learn (+25 XP)", on_choose=negotiate),
            EventOption("Dismiss them.", on_choose=dismiss),
        ],
        event_id="merchant_001",
        allow_close=False,
    )


def build_bad_omens(ctx) -> EventData:
    ensure_ctx(ctx)
    realm = ctx["realm"]
    status = ctx["status"]

    def hold_prayer(c):
        realm.piety += 10
        status["text"] = "You hold prayers. (+10 piety)"

    def blame_rival(c):
        realm.prestige += 5
        status["text"] = "You spin the omens against a rival. (+5 prestige)"

    def ignore(c):
        status["text"] = "You ignore the omens."

    return EventData(
        title="Bad Omens",
        subtitle="Whispers spread",
        body=lambda c: f"Unusual signs are reported across {realm.name}. The court watches your reaction.",
        options=[
            EventOption("Hold prayers (+10 piety)", on_choose=hold_prayer),
            EventOption("Blame a rival (+5 prestige)", on_choose=blame_rival),
            EventOption("Ignore it.", on_choose=ignore),
        ],
        event_id="omens_001",
        allow_close=False,
    )


# ----------------------------
# NEW: Multi-character events
# ----------------------------

def build_betrayal_at_court(ctx) -> EventData:
    """
    Someone close to you skims funds / sells secrets.
    The actor is chosen from other characters and stored in ctx["actor"].
    """
    ensure_ctx(ctx)
    realm = ctx["realm"]
    p = player(ctx)
    status = ctx["status"]

    actor = pick_non_player(ctx)
    if actor is None:
        # Fallback to a basic event if no other characters exist
        return build_training(ctx)

    ctx["actor"] = actor  # store for callbacks
    who = name_of(actor)

    # Example: betrayal severity depends on intrigue/loyalty
    severity = max(5, min(40, int(actor.intrigue * 1.5 + (50 - actor.loyalty) * 0.4)))
    stolen = min(int(realm.gold), max(5, severity))

    def punish(c):
        # regain some gold + prestige, but actor opinion/loyalty drops
        regained = int(stolen * 0.6)
        realm.gold += regained
        realm.prestige += 4
        actor.loyalty = max(0, actor.loyalty - 20)
        actor.opinion_of_player = max(-100, actor.opinion_of_player - 25)
        status["text"] = f"You punish {who}. Recovered {regained} gold. (+4 prestige)"

    def forgive(c):
        # lose prestige, but gain loyalty (maybe the actor becomes grateful)
        realm.prestige = max(0, realm.prestige - 3)
        actor.loyalty = min(100, actor.loyalty + 15)
        actor.opinion_of_player = min(100, actor.opinion_of_player + 10)
        status["text"] = f"You forgive {who}. (-3 prestige, +loyalty)"

    def hush_money(c):
        # pay to keep quiet; actor becomes "bought"
        realm.gold -= 15
        actor.loyalty = min(100, actor.loyalty + 10)
        actor.opinion_of_player = min(100, actor.opinion_of_player + 20)
        status["text"] = f"You pay {who} to keep quiet. (-15 gold)"

    def can_hush(c):
        return realm.gold >= 15

    return EventData(
        title="Betrayal at Court",
        subtitle=f"{who} is implicated",
        body=lambda c: (
            f"Your agents bring troubling news: {who} is suspected of skimming funds and feeding rumors. "
            f"The estimated damage is around {stolen} gold."
        ),
        options=[
            EventOption(f"Make an example of {who} (recover some gold, +prestige)", on_choose=punish),
            EventOption(f"Forgive {who} (-prestige, +loyalty)", on_choose=forgive),
            EventOption(f"Pay hush money (-15 gold)", on_choose=hush_money, enabled=can_hush),
        ],
        event_id="betrayal_001",
        allow_close=False,
    )


def build_faithful_steward(ctx) -> EventData:
    """
    A character helps the player (finds missing taxes, improves efficiency).
    """
    ensure_ctx(ctx)
    realm = ctx["realm"]
    status = ctx["status"]

    helper = pick_non_player(ctx)
    if helper is None:
        return build_bad_omens(ctx)

    ctx["helper"] = helper
    who = name_of(helper)

    found = 12 + int(helper.intrigue * 0.6)

    def reward(c):
        # pay them a bit; boosts loyalty/opinion and prestige
        realm.gold -= 8
        realm.prestige += 2
        helper.loyalty = min(100, helper.loyalty + 10)
        helper.opinion_of_player = min(100, helper.opinion_of_player + 10)
        status["text"] = f"You reward {who}. (-8 gold, +2 prestige, +loyalty)"

    def keep_all(c):
        realm.gold += found
        helper.opinion_of_player = max(-100, helper.opinion_of_player - 8)
        status["text"] = f"{who} finds missing taxes (+{found} gold). You keep it all."

    def share(c):
        realm.gold += found
        realm.gold -= 5  # token gift
        helper.loyalty = min(100, helper.loyalty + 8)
        status["text"] = f"{who} finds missing taxes (+{found} gold). You share the credit."

    def can_reward(c):
        return realm.gold >= 8

    return EventData(
        title="A Faithful Steward",
        subtitle=f"{who} brings good news",
        body=lambda c: (
            f"{who} presents corrected ledgers and recovered dues. "
            f"With careful work, they estimate {found} gold can be restored."
        ),
        options=[
            EventOption(f"Keep the recovered gold (+{found} gold)", on_choose=keep_all),
            EventOption("Share the credit (small loyalty gain)", on_choose=share),
            EventOption("Reward your steward (-8 gold, +prestige)", on_choose=reward, enabled=can_reward),
        ],
        event_id="steward_help_001",
        allow_close=False,
    )


def build_rivals_offer(ctx) -> EventData:
    """
    A rival offers help that benefits the player, but creates a dependency.
    """
    ensure_ctx(ctx)
    realm = ctx["realm"]
    p = player(ctx)
    status = ctx["status"]

    rival = pick_non_player(ctx, predicate=lambda c: c.opinion_of_player < 0)
    if rival is None:
        # If no negative-opinion character exists, pick any
        rival = pick_non_player(ctx)

    if rival is None:
        return build_training(ctx)

    ctx["rival"] = rival
    who = name_of(rival)

    aid_gold = 20

    def accept_aid(c):
        realm.gold += aid_gold
        rival.opinion_of_player = min(100, rival.opinion_of_player + 10)
        rival.loyalty = min(100, rival.loyalty + 5)
        # downside: prestige hit for “relying” on them
        realm.prestige = max(0, realm.prestige - 2)
        status["text"] = f"You accept {who}'s aid. (+{aid_gold} gold, -2 prestige)"

    def refuse(c):
        realm.prestige += 1
        rival.opinion_of_player = max(-100, rival.opinion_of_player - 5)
        status["text"] = f"You refuse {who}. (+1 prestige)"

    def outplay(c):
        # attempt to gain without losing prestige: requires xp threshold
        realm.gold += 10
        p.xp += 20
        rival.opinion_of_player = max(-100, rival.opinion_of_player - 12)
        status["text"] = f"You outplay {who}. (+10 gold, +20 XP)"

    return EventData(
        title="A Rival’s Offer",
        subtitle=f"{who} approaches you",
        body=lambda c: (
            f"{who} proposes discreet support: {aid_gold} gold, no questions asked. "
            "Courtiers watch carefully—accepting may appear weak."
        ),
        options=[
            EventOption(f"Accept the aid (+{aid_gold} gold, -2 prestige)", on_choose=accept_aid),
            EventOption("Refuse (+1 prestige)", on_choose=refuse),
            EventOption("Outplay them (+10 gold, +20 XP)", on_choose=outplay),
        ],
        event_id="rival_offer_001",
        allow_close=False,
    )


# ----------------------------
# Registry setup
# ----------------------------

def default_registry(seed: int = 123) -> EventRegistry:
    reg = EventRegistry(seed=seed)

    # Basic events
    reg.register(EventFactory("stray_cat_001", 6, lambda ctx: True, build_stray_cat))
    reg.register(EventFactory("evening_decision_001", 6, lambda ctx: True, build_training))
    reg.register(EventFactory("merchant_001", 3, lambda ctx: True, build_wandering_merchant))
    reg.register(EventFactory("omens_001", 4, lambda ctx: True, build_bad_omens))

    # Multi-character events
    reg.register(EventFactory("betrayal_001", 4, lambda ctx: len(ctx.get("characters", [])) >= 2, build_betrayal_at_court))
    reg.register(EventFactory("steward_help_001", 4, lambda ctx: len(ctx.get("characters", [])) >= 2, build_faithful_steward))
    reg.register(EventFactory("rival_offer_001", 3, lambda ctx: len(ctx.get("characters", [])) >= 2, build_rivals_offer))

    return reg


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
    
    # inside EventPopup.handle_event, when an enabled option is clicked:

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
