# external imports
from dataclasses import dataclass, field
from uuid import uuid4
from typing import Literal, Dict
import math

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

@dataclass
class Population:
    population_type = Literal["children", "adults", "elders"]

    id: str = field(default_factory=lambda: uuid4().hex)

    # population buckets
    counts: Dict[population_type, int] = field(default_factory=lambda: {"children": 0, "adults": 0, "elders": 0})

    # births per adult per year (roughly: 0.06 means 6 births per 100 adults per year)
    fertility_per_adult_per_year: float = 0.06

    # age-specific mortality rates per year (hazards)
    mortality_per_year: Dict[population_type, float] = field(
        default_factory=lambda: {
            "children": 0.015,  # 1.5%/year
            "adults": 0.010,    # 1.0%/year
            "elders": 0.050,    # 5.0%/year
        }
    )

    # average time spent in each group (years) -> controls aging flow
    years_in_group: Dict[population_type, float] = field(
        default_factory=lambda: {
            "children": 16.0,   # childhood length
            "adults": 44.0,     # adult years until elder
            "elders": 20.0,     # not used for aging out, but you can keep it
        }
    )

    # --- Simple economic/military contribution weights ---
    workforce_weight: Dict[population_type, float] = field(
        default_factory=lambda: {"children": 0.0, "adults": 1.0, "elders": 0.3}
    )
    tax_weight: Dict[population_type, float] = field(
        default_factory=lambda: {"children": 0.0, "adults": 1.0, "elders": 0.6}
    )
    manpower_weight: Dict[population_type, float] = field(
        default_factory=lambda: {"children": 0.0, "adults": 0.7, "elders": 0.05}
    )

    # ---------- basic getters/setters ----------
    def total(self) -> int:
        return sum(self.counts.values())

    def get(self, pop_type: population_type) -> int:
        return self.counts.get(pop_type, 0)

    def set(self, pop_type: population_type, amount: int) -> None:
        if amount < 0:
            raise ValueError("Population amount cannot be negative.")
        self.counts[pop_type] = amount

    def add(self, pop_type: population_type, delta: int) -> None:
        new_val = self.get(pop_type) + delta
        if new_val < 0:
            raise ValueError(f"Population '{pop_type}' cannot go below 0.")
        self.counts[pop_type] = new_val

    # ---------- contributions ----------
    def contributions(self) -> dict[str, float]:
        """
        Returns gamey outputs you can plug into county taxes/levies/dev growth.
        """
        workforce = sum(self.get(t) * w for t, w in self.workforce_weight.items())
        taxes = sum(self.get(t) * w for t, w in self.tax_weight.items())
        manpower = sum(self.get(t) * w for t, w in self.manpower_weight.items())

        adults = self.get("adults")
        dependents = self.get("children") + self.get("elders")
        dependency_ratio = (dependents / adults) if adults > 0 else float("inf")

        return {
            "workforce": workforce,
            "tax_base": taxes,
            "manpower_base": manpower,
            "dependency_ratio": dependency_ratio,
        }

    # ---------- tick mechanics ----------
    @staticmethod
    def _expected_events(count: int, rate_per_year: float, dt_years: float) -> int:
        """
        Deterministic expectation using continuous-time assumption:
        P(event in dt) = 1 - exp(-rate*dt)
        Expected events = count * P
        """
        if count <= 0 or rate_per_year <= 0 or dt_years <= 0:
            return 0
        p = 1.0 - math.exp(-rate_per_year * dt_years)
        return int(count * p)

    def tick(self, dt_days: float = 30.0) -> dict[str, int]:
        """
        Advance the population by dt_days (default ~monthly).
        Uses continuous rates, which naturally create exponential-like behavior.
        """
        dt_years = dt_days / 365.0

        report = {
            "births": 0,
            "deaths_children": 0,
            "deaths_adults": 0,
            "deaths_elders": 0,
            "aged_children_to_adults": 0,
            "aged_adults_to_elders": 0,
        }

        # 1) Births (from adults)
        adults = self.get("adults")
        births = self._expected_events(adults, self.fertility_per_adult_per_year, dt_years)
        if births > 0:
            self.add("children", births)
        report["births"] = births

        # 2) Aging (flow model: fraction leaves group per dt)
        # approximate hazard for aging out: 1 / years_in_group
        children = self.get("children")
        child_age_rate = 1.0 / max(self.years_in_group["children"], 1e-6)
        aged_c2a = self._expected_events(children, child_age_rate, dt_years)
        if aged_c2a > 0:
            self.add("children", -aged_c2a)
            self.add("adults", aged_c2a)
        report["aged_children_to_adults"] = aged_c2a

        adults = self.get("adults")  # refresh after aging
        adult_age_rate = 1.0 / max(self.years_in_group["adults"], 1e-6)
        aged_a2e = self._expected_events(adults, adult_age_rate, dt_years)
        if aged_a2e > 0:
            self.add("adults", -aged_a2e)
            self.add("elders", aged_a2e)
        report["aged_adults_to_elders"] = aged_a2e

        # 3) Deaths (age-specific)
        for group in ("children", "adults", "elders"):
            n = self.get(group)  # type: ignore[arg-type]
            deaths = self._expected_events(n, self.mortality_per_year[group], dt_years)  # type: ignore[index]
            if deaths > 0:
                self.add(group, -deaths)  # type: ignore[arg-type]
            report[f"deaths_{group}"] = deaths

        return report

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
