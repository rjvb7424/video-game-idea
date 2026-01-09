# systems.py
import random

class GameSystems:
    """
    Your 'place to run checks'.
    Keep this as the only module that knows what happens on day/month/year.
    """
    def __init__(self, rng_seed: int = 12345):
        self.rng = random.Random(rng_seed)

    # ---- DAILY ----
    def on_day(self, realm, characters, date):
        # Example: passive income + XP drip
        for ch in characters:
            # You can customize these however you want
            ch.gold += 0.1  # e.g. personal allowance
            ch.xp = getattr(ch, "xp", 0) + 1

        # Realm income (very simple placeholder)
        realm.gold += self._realm_daily_income(realm)

        # Example: daily random micro-check (small chance)
        # (Better: do most RNG monthly, but daily is okay for light stuff)
        if self.rng.random() < 0.002:
            self.character_gets_cat(realm.ruler)

    # ---- MONTHLY ----
    def on_month(self, realm, characters, date):
        # Larger systems: control drift, development growth, vassal opinions, etc.
        # Random events feel better monthly (CK3 vibe)
        self.roll_random_event(realm, characters, date)

    # ---- YEARLY ----
    def on_year(self, realm, characters, date):
        # Taxes, age up, big maintenance ticks
        for ch in characters:
            ch.age += 1

    # --------------------------
    # Helpers / Examples
    # --------------------------
    def _realm_daily_income(self, realm) -> float:
        # Example: base income from development
        # (Replace with your real economy later)
        dev = realm.total_development(include_vassals=False)
        return 0.05 * dev  # 0.05 gold per dev per day

    def character_gets_cat(self, character):
        # Example event function you wanted
        inv = getattr(character, "inventory", [])
        inv.append("Cat 🐈")
        character.inventory = inv

    def roll_random_event(self, realm, characters, date):
        """
        Simple weighted random event table.
        Extend with triggers/conditions for CK3-like flavor.
        """
        ruler = realm.ruler
        if ruler is None:
            return

        candidates = []

        # Event: cat (if ruler doesn't already have one)
        has_cat = "Cat 🐈" in getattr(ruler, "inventory", [])
        if not has_cat:
            candidates.append(("cat_event", 3))

        # Event: small gold windfall
        candidates.append(("gold_windfall", 5))

        # Event: skill practice (xp boost)
        candidates.append(("training", 7))

        if not candidates:
            return

        total_w = sum(w for _, w in candidates)
        pick = self.rng.uniform(0, total_w)
        upto = 0.0
        chosen = None
        for name, w in candidates:
            upto += w
            if pick <= upto:
                chosen = name
                break

        if chosen == "cat_event":
            self.character_gets_cat(ruler)

        elif chosen == "gold_windfall":
            realm.gold += 15

        elif chosen == "training":
            ruler.xp = getattr(ruler, "xp", 0) + 50
