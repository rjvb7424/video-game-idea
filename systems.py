# systems.py
import random
from buildings import BUILDINGS
from domain import BuildingInstance

class GameSystems:
    def __init__(self, rng_seed: int = 12345):
        self.rng = random.Random(rng_seed)

    def on_day(self, realm, characters, date, counties=None):
        for ch in characters:
            ch.gold = getattr(ch, "gold", 0.0) + 0.1
            ch.xp = getattr(ch, "xp", 0) + 1

        # realm base income
        realm.gold = getattr(realm, "gold", 0.0) + self._realm_daily_income(realm)

        # construction tick
        if counties:
            for c in counties:
                self._tick_construction(c)

    def on_year(self, realm, characters, date):
        for ch in characters:
            ch.age = getattr(ch, "age", 0) + 1

    def _realm_daily_income(self, realm) -> float:
        if hasattr(realm, "daily_income") and callable(realm.daily_income):
            return float(realm.daily_income())
        dev = getattr(realm, "development", 0)
        return 0.05 * dev

    def _tick_construction(self, county):
        h = county.holding
        if not h.construction:
            return
        h.construction.days_left -= 1
        if h.construction.days_left <= 0:
            # finish
            bid = h.construction.building_id
            slot = h.construction.slot_index
            h.buildings[slot] = BuildingInstance(building_id=bid, level=1)
            h.construction = None
