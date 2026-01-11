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
        # passive drip
        for ch in characters:
            ch.gold = getattr(ch, "gold", 0.0) + 0.1
            ch.xp = getattr(ch, "xp", 0) + 1

        # Realm income
        realm.gold = getattr(realm, "gold", 0.0) + self._realm_daily_income(realm)

        # tiny daily micro chance
        if self.rng.random() < 0.002:
            self.character_gets_cat(getattr(realm, "ruler", None))

    # ---- MONTHLY ----
    def on_month(self, realm, characters, date):
        self.roll_random_event(realm, characters, date)

    # ---- YEARLY ----
    def on_year(self, realm, characters, date):
        for ch in characters:
            ch.age = getattr(ch, "age", 0) + 1

    # --------------------------
    # Helpers
    # --------------------------
    def _realm_daily_income(self, realm) -> float:
        """
        Compatible income logic:
        - If Realm has daily_income(), use it (matches the modular Realm).
        - Else fallback to realm.development.
        - Else fallback to 0.
        """
        if hasattr(realm, "daily_income") and callable(realm.daily_income):
            return float(realm.daily_income())

        dev = getattr(realm, "development", 0)
        return 0.05 * dev

    def character_gets_cat(self, character):
        if character is None:
            return
        inv = getattr(character, "inventory", [])
        if "Cat 🐈" not in inv:
            inv.append("Cat 🐈")
        character.inventory = inv

    def roll_random_event(self, realm, characters, date):
        ruler = getattr(realm, "ruler", None)
        if ruler is None:
            return

        candidates = []

        has_cat = "Cat 🐈" in getattr(ruler, "inventory", [])
        if not has_cat:
            candidates.append(("cat_event", 3))

        candidates.append(("gold_windfall", 5))
        candidates.append(("training", 7))

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
            realm.gold = getattr(realm, "gold", 0.0) + 15
        elif chosen == "training":
            ruler.xp = getattr(ruler, "xp", 0) + 50
