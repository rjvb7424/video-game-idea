from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
import random

EventText = str | Callable[[dict], str]
EnabledFn = bool | Callable[[dict], bool]

def _ev_text(v: EventText, ctx: dict) -> str:
    return v(ctx) if callable(v) else str(v)

def _ev_bool(v: EnabledFn, ctx: dict) -> bool:
    return bool(v(ctx)) if callable(v) else bool(v)

def date_ordinal(date_obj) -> int:
    """No-leap ordinal for your GameDate (month lengths are fixed)."""
    month_len = getattr(date_obj, "MONTH_LEN", [31,28,31,30,31,30,31,31,30,31,30,31])
    y = int(date_obj.year); m = int(date_obj.month); d = int(date_obj.day)
    days_before_month = sum(month_len[:m-1])
    return y * 365 + days_before_month + d

@dataclass
class EventOption:
    label: EventText
    kind: str = "primary"   # "primary" | "secondary" | "accept" | "deny"
    enabled: EnabledFn = True
    on_choose: Optional[Callable[[dict, "EventAPI"], None]] = None
    close_on_choose: bool = True

@dataclass
class EventData:
    title: EventText
    body: EventText | list[EventText]
    options: list[EventOption] = field(default_factory=list)
    event_id: str = "event"
    allow_close: bool = False  # if False: no Close button, must pick an option

@dataclass
class EventFactory:
    event_id: str
    weight: int
    can_fire: Callable[[dict], bool]
    build: Callable[[dict], EventData]

# -------------------------
# Registry + API
# -------------------------

class EventRegistry:
    def __init__(self, seed: int = 123):
        self.rng = random.Random(seed)
        self._events: list[EventFactory] = []
        self._by_id: dict[str, EventFactory] = {}

    def register(self, factory: EventFactory):
        self._events.append(factory)
        self._by_id[factory.event_id] = factory

    def get(self, event_id: str) -> Optional[EventFactory]:
        return self._by_id.get(event_id)

    def roll(self, ctx: dict) -> Optional[EventData]:
        candidates = [e for e in self._events if e.weight > 0 and e.can_fire(ctx)]
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

class EventAPI:
    """Used inside option callbacks to log/schedule/set flags."""
    def __init__(self, app: Any):
        self.app = app

    def log(self, text: str):
        self.app.push_log(text)

    def schedule(self, event_id: str, days: int = 0):
        due = date_ordinal(self.app.date) + max(0, int(days))
        self.app._event_pending.append((due, event_id))

    def push_now(self, event_id: str):
        self.schedule(event_id, days=0)

    def flag_set(self, key: str, value=True):
        self.app._event_flags[key] = value

    def flag_get(self, key: str, default=False):
        return self.app._event_flags.get(key, default)

# -------------------------
# A tiny builder to reduce boilerplate
# -------------------------

class E:
    """Event builder used by event content files."""
    def __init__(self, event_id: str):
        self.event_id = event_id
        self._title: EventText = event_id
        self._body: EventText | list[EventText] = ""
        self._options: list[EventOption] = []
        self._allow_close = False

    def make(self, title: EventText, body: EventText | list[EventText]):
        self._title = title
        self._body = body
        return self

    def allow_close(self, allow: bool = True):
        self._allow_close = allow
        return self

    def option(
        self,
        label: EventText,
        *,
        kind: str = "primary",
        enabled: EnabledFn = True,
        on_choose: Optional[Callable[[dict, EventAPI], None]] = None,
        close_on_choose: bool = True,
    ):
        self._options.append(EventOption(
            label=label, kind=kind, enabled=enabled,
            on_choose=on_choose, close_on_choose=close_on_choose
        ))
        return self

    def done(self) -> EventData:
        return EventData(
            title=self._title,
            body=self._body,
            options=self._options,
            event_id=self.event_id,
            allow_close=self._allow_close,
        )

def event(event_id: str, *, weight: int, can_fire: Optional[Callable[[dict], bool]] = None):
    """
    Decorator: turns a function into an EventFactory registration.
    The function signature: fn(ctx, E_builder, api?) is NOT needed; just (ctx, E) recommended.
    """
    if can_fire is None:
        can_fire = lambda ctx: True

    def _decorator(fn: Callable[[dict, E], EventData]):
        fn._event_factory = EventFactory(
            event_id=event_id,
            weight=weight,
            can_fire=can_fire,
            build=lambda ctx: fn(ctx, E(event_id)),
        )
        return fn
    return _decorator

def register_all(reg: EventRegistry, module):
    """Register all @event-decorated functions in a module."""
    for name in dir(module):
        obj = getattr(module, name)
        fac = getattr(obj, "_event_factory", None)
        if isinstance(fac, EventFactory):
            reg.register(fac)

# -------------------------
# System (integration with your Modal)
# -------------------------

class EventSystem:
    def __init__(self, app: Any, registry: EventRegistry, daily_chance: float = 0.01, seed: int = 999):
        self.app = app
        self.registry = registry
        self.daily_chance = float(daily_chance)
        self.rng = random.Random(seed)

    def make_ctx(self) -> dict:
        return {
            "date": self.app.date,
            "character": self.app.character,
            "resources": self.app.resources,
            "selected_province": self.app.selected_province,
            "world": self.app.world,
            "flags": self.app._event_flags,
            "rng": self.rng,
        }

    def _open_event(self, ev: EventData):
        ctx = self.make_ctx()
        api = EventAPI(self.app)

        title = _ev_text(ev.title, ctx)

        lines: list[str] = []
        if isinstance(ev.body, list):
            lines.extend(_ev_text(x, ctx) for x in ev.body)
        else:
            lines.append(_ev_text(ev.body, ctx))

        actions = []
        if ev.allow_close:
            actions.append(("Close", "secondary", lambda: self.app.modal.close()))

        for opt in ev.options:
            label = _ev_text(opt.label, ctx)
            enabled = _ev_bool(opt.enabled, ctx)

            def make_cb(_opt: EventOption):
                def _cb():
                    ctx2 = self.make_ctx()
                    api2 = EventAPI(self.app)
                    if _opt.on_choose:
                        _opt.on_choose(ctx2, api2)
                    if _opt.close_on_choose:
                        self.app.modal.close()
                return _cb

            actions.append((label, opt.kind if enabled else "secondary", make_cb(opt) if enabled else (lambda: None)))

        if self.app.speed_level > 0:
            self.app._event_resume_speed = self.app.speed_level
            self.app.set_speed(0)

        def _resume_speed():
            prev = getattr(self.app, "_event_resume_speed", None)
            if prev is not None:
                self.app._event_resume_speed = None
                self.app.set_speed(prev)

        self.app.modal.show(title, lines, actions, on_close=_resume_speed)

    def _try_fire_pending(self) -> bool:
        if self.app.modal.open or not self.app._event_pending:
            return False

        today = date_ordinal(self.app.date)
        self.app._event_pending.sort(key=lambda x: x[0])
        due_day, eid = self.app._event_pending[0]
        if due_day > today:
            return False

        self.app._event_pending.pop(0)
        fac = self.registry.get(eid)
        if not fac:
            self.app.push_log(f"{self.app.date}: Missing event '{eid}'.")
            return False

        ev = fac.build(self.make_ctx())
        self._open_event(ev)
        return True

    def on_day(self):
        if self._try_fire_pending():
            return
        if self.app.modal.open:
            return
        if self.rng.random() >= self.daily_chance:
            return
        ev = self.registry.roll(self.make_ctx())
        if ev:
            self._open_event(ev)