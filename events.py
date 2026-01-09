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
    """
    An event "template" that can be rolled and then built into EventData.
    """
    event_id: str
    weight: int
    can_fire: Callable[[Any], bool]                 # ctx -> bool
    build: Callable[[Any], EventData]               # ctx -> EventData


class EventRegistry:
    def __init__(self, seed: int = 123):
        self.rng = random.Random(seed)
        self._events: List[EventFactory] = []

    def register(self, factory: EventFactory):
        self._events.append(factory)

    def roll(self, ctx: Any) -> Optional[EventData]:
        """
        Returns an EventData or None.
        Only includes events whose can_fire(ctx) is True.
        """
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
# Example events (add more here)
# ----------------------------

def build_stray_cat(ctx) -> EventData:
    realm = ctx["realm"]
    ruler = ctx["ruler"]
    status = ctx["status"]

    def adopt(c):
        inv = getattr(ruler, "inventory", [])
        if "Cat 🐈" not in inv:
            inv.append("Cat 🐈")
        ruler.inventory = inv
        status["text"] = "You adopted a cat 🐈"

    def pay_for_food(c):
        # This costs 10 gold. Button must be disabled if not affordable.
        realm.gold -= 10
        status["text"] = "You pay for food and supplies. (-10 gold)"

    def ignore(c):
        status["text"] = "You ignore the strange visitor."

    def can_adopt(c):
        return "Cat 🐈" not in getattr(ruler, "inventory", [])

    def can_pay(c):
        return realm.gold >= 10

    return EventData(
        title="A Stray Cat Appears",
        subtitle="A Curious Visitor",
        body=lambda c: (
            f"A small cat follows {ruler.fname} through the halls. "
            "The servants whisper it may be an omen."
        ),
        options=[
            EventOption("Adopt the cat 🐈", on_choose=adopt, enabled=can_adopt),
            EventOption("Buy food for it (-10 gold)", on_choose=pay_for_food, enabled=can_pay),
            EventOption("Ignore it.", on_choose=ignore),
        ],
        event_id="stray_cat_001",
        allow_close=False,     # must choose
        allow_esc_close=False,
    )


def build_training(ctx) -> EventData:
    realm = ctx["realm"]
    ruler = ctx["ruler"]
    status = ctx["status"]

    def study(c):
        ruler.xp += 75
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
    realm = ctx["realm"]
    ruler = ctx["ruler"]
    status = ctx["status"]

    def buy_relic(c):
        realm.gold -= 30
        inv = getattr(ruler, "inventory", [])
        inv.append("Curious Relic ✨")
        ruler.inventory = inv
        status["text"] = "You purchase a curious relic. (-30 gold)"

    def negotiate(c):
        ruler.xp += 25
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
    realm = ctx["realm"]
    ruler = ctx["ruler"]
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


def default_registry(seed: int = 123) -> EventRegistry:
    reg = EventRegistry(seed=seed)

    reg.register(EventFactory(
        event_id="stray_cat_001",
        weight=6,
        can_fire=lambda ctx: True,
        build=build_stray_cat
    ))

    reg.register(EventFactory(
        event_id="evening_decision_001",
        weight=6,
        can_fire=lambda ctx: True,
        build=build_training
    ))

    reg.register(EventFactory(
        event_id="merchant_001",
        weight=3,
        can_fire=lambda ctx: True,
        build=build_wandering_merchant
    ))

    reg.register(EventFactory(
        event_id="omens_001",
        weight=4,
        can_fire=lambda ctx: True,
        build=build_bad_omens
    ))

    return reg
