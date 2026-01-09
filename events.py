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
