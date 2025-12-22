# external imports
from uuid import uuid4
from dataclasses import dataclass, field

# internal imports
from character import Character

@dataclass
class Faith:
    id: str = uuid4().hex
    name: str
    description: str
    # TODO: expand with virtues and sins

@dataclass
class Culture:
    id: str = uuid4().hex
    name: str
    description: str
    # TODO: expand with modifiers, traditions

class Population:
    id: str = uuid4().hex
    # basic demographics tuning (per year, if you tick yearly)
    annual_birth_rate: float = 0.030
    annual_death_rate: float = 0.020
    annual_child_to_adult_rate: float = 0.18

    def total(self) -> int:
        return sum(self.counts.values())

    def get(self, pop_type: PopType) -> int:
        return self.counts.get(pop_type, 0)

    def set(self, pop_type: PopType, amount: int) -> None:
        if amount < 0:
            raise ValueError("Population amount cannot be negative.")
        self.counts[pop_type] = amount

    def add(self, pop_type: PopType, delta: int) -> None:
        new_val = self.get(pop_type) + delta
        if new_val < 0:
            raise ValueError(f"Population '{pop_type}' cannot go below 0.")
        self.counts[pop_type] = new_val

    def move(self, src: PopType, dst: PopType, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot move a negative amount.")
        if self.get(src) < amount:
            raise ValueError(f"Not enough population in '{src}' to move {amount}.")
        self.add(src, -amount)
        self.add(dst, amount)

    def enslave(self, amount: int) -> None:
        """Move freemen into slaves (simple baseline mechanic)."""
        self.move(PopType.FREEMEN, PopType.SLAVES, amount)

    def emancipate(self, amount: int) -> None:
        """Move slaves into freemen."""
        self.move(PopType.SLAVES, PopType.FREEMEN, amount)

    def _apply_deaths_proportionally(self, deaths: int) -> None:
        """
        Remove deaths across pop buckets proportionally.
        You can later customize this (e.g., wars hit freemen more, plagues hit children more).
        """
        total_pop = self.total()
        if deaths <= 0 or total_pop <= 0:
            return

        # proportional removal with rounding; ensure we remove exactly 'deaths'
        buckets = [(t, self.get(t)) for t in PopType if self.get(t) > 0]
        if not buckets:
            return

        removed_total = 0
        removals: dict[PopType, int] = {}

        for t, count in buckets:
            share = count / total_pop
            rem = int(deaths * share)
            removals[t] = rem
            removed_total += rem

        # fix rounding drift
        drift = deaths - removed_total
        if drift > 0:
            # add remaining removals to largest buckets
            buckets_sorted = sorted(buckets, key=lambda x: x[1], reverse=True)
            i = 0
            while drift > 0 and buckets_sorted:
                t = buckets_sorted[i % len(buckets_sorted)][0]
                removals[t] += 1
                drift -= 1
                i += 1
        elif drift < 0:
            # remove extra removals if we overshot
            buckets_sorted = sorted(buckets, key=lambda x: x[1], reverse=True)
            i = 0
            while drift < 0 and buckets_sorted:
                t = buckets_sorted[i % len(buckets_sorted)][0]
                if removals[t] > 0:
                    removals[t] -= 1
                    drift += 1
                i += 1

        # apply
        for t, rem in removals.items():
            if rem > 0:
                self.add(t, -rem)

    def yearly_tick(self) -> dict[str, int]:
        """
        One "year" of demographic change: births, deaths, children aging up.
        Returns a small report you can log or use in UI.
        """
        total_pop = self.total()

        births = int(total_pop * self.annual_birth_rate) if total_pop > 0 else 0
        if births > 0:
            self.add(PopType.CHILDREN, births)

        # age up children -> adults
        children = self.get(PopType.CHILDREN)
        age_up = int(children * self.annual_child_to_adult_rate) if children > 0 else 0
        if age_up > 0:
            self.move(PopType.CHILDREN, self.default_adult_type, age_up)

        # deaths after births/aging (your choice; tweak ordering if you want)
        total_pop_after = self.total()
        deaths = int(total_pop_after * self.annual_death_rate) if total_pop_after > 0 else 0
        self._apply_deaths_proportionally(deaths)

        return {"births": births, "age_up": age_up, "deaths": deaths}

@dataclass
class County:
    id: str = uuid4().hex
    name: str
    # local country identity
    faith: Faith = field(default_factory=Faith())
    # modifiers
    development: int = 1
    control: int = 100
    # ownership
    owner: Character
    # TODO: expand with counties not needing an owner (e.g, unclaimed land)

    def set_holder(self, new_holder: Character) -> None:
        self.holder = new_holder

    def get_holder(self) -> Character:
        return self.holder
