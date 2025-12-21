# realm.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Set, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    # Import your Character type for type-checking only (avoids circular imports at runtime)
    from character import Character


def new_id() -> str:
    return uuid4().hex


class GovernmentType(str, Enum):
    FEUDAL = "feudal"
    CLAN = "clan"
    TRIBAL = "tribal"
    REPUBLIC = "republic"
    THEOCRACY = "theocracy"


class SuccessionType(str, Enum):
    PARTITION = "partition"
    CONFEDERATE_PARTITION = "confederate_partition"
    PRIMOGENITURE = "primogeniture"
    ELECTIVE = "elective"


@dataclass(slots=True)
class Faith:
    id: str = field(default_factory=new_id)
    name: str = "No Faith"
    tenets: List[str] = field(default_factory=list)
    doctrines: Dict[str, str] = field(default_factory=dict)

    def is_hostile_to(self, other: "Faith") -> bool:
        # Placeholder rule: different faith names => hostile
        # Replace with real doctrine comparison logic later.
        return self.name != other.name


@dataclass(slots=True)
class Culture:
    id: str = field(default_factory=new_id)
    name: str = "No Culture"
    ethos: str = "neutral"
    traditions: List[str] = field(default_factory=list)
    language: str = "common"
    innovations: Set[str] = field(default_factory=set)

    def has_tradition(self, tradition: str) -> bool:
        return tradition in self.traditions


@dataclass(slots=True)
class County:
    id: str = field(default_factory=new_id)
    name: str = "Unnamed County"

    # “Local” county identity (can differ from realm)
    culture: Culture = field(default_factory=Culture)
    faith: Faith = field(default_factory=Faith)

    # CK3-like stats
    development: int = 1          # economic/tech proxy
    control: float = 100.0        # 0..100 (popular order / admin reach)

    # Who *owns* the county (domain holder). In CK3 terms: county holder / title holder.
    holder: Optional["Character"] = None

    # Optional: which realm it belongs to politically
    realm_id: Optional[str] = None

    def set_holder(self, new_holder: Optional["Character"]) -> None:
        self.holder = new_holder

    def clamp(self) -> None:
        self.development = max(0, int(self.development))
        self.control = max(0.0, min(100.0, float(self.control)))


@dataclass(slots=True)
class RealmLaws:
    # Keep it flexible: you can later expand to richer structures.
    succession: SuccessionType = SuccessionType.PARTITION
    crown_authority: int = 1  # 0..4
    vassal_contracts_enabled: bool = True

    def clamp(self) -> None:
        self.crown_authority = max(0, min(4, int(self.crown_authority)))


@dataclass(slots=True)
class Realm:
    """
    A political entity. A character may:
      - RULE it (legal holder / top liege)
      - CONTROL it (actual decision-maker; could be same as ruler, or a regent, or an occupier)
    """

    id: str = field(default_factory=new_id)
    name: str = "Unnamed Realm"

    government: GovernmentType = GovernmentType.FEUDAL
    laws: RealmLaws = field(default_factory=RealmLaws)

    # “Realm identity” (often matches ruler, but not always)
    faith: Faith = field(default_factory=Faith)
    culture: Culture = field(default_factory=Culture)

    # Core geography
    counties: List[County] = field(default_factory=list)
    capital_county_id: Optional[str] = None

    # Leadership
    ruler: Optional["Character"] = None       # the one who *owns* the realm
    controller: Optional["Character"] = None  # the one who *currently controls* the realm

    # CK3-ish resources (minimal)
    gold: int = 0
    prestige: int = 0
    piety: int = 0

    # Relationships
    liege: Optional["Realm"] = None
    vassals: List["Realm"] = field(default_factory=list)

    # --- Control / ownership rules ---

    def set_ruler(self, character: Optional["Character"]) -> None:
        self.ruler = character
        # default: ruler also controls unless you explicitly set a different controller
        if self.controller is None:
            self.controller = character

    def set_controller(self, character: Optional["Character"]) -> None:
        self.controller = character

    def is_ruled_by(self, character: Optional["Character"]) -> bool:
        return character is not None and self.ruler is character

    def is_controlled_by(self, character: Optional["Character"]) -> bool:
        return character is not None and self.controller is character

    def effective_ruler(self) -> Optional["Character"]:
        """Who makes decisions right now (regent/occupier/etc)."""
        return self.controller or self.ruler

    # --- Counties management ---

    def add_county(self, county: County, make_capital: bool = False) -> None:
        if county.id not in {c.id for c in self.counties}:
            self.counties.append(county)
        county.realm_id = self.id
        if make_capital or self.capital_county_id is None:
            self.capital_county_id = county.id

    def remove_county(self, county_id: str) -> None:
        self.counties = [c for c in self.counties if c.id != county_id]
        # If removing capital, pick a new one if possible
        if self.capital_county_id == county_id:
            self.capital_county_id = self.counties[0].id if self.counties else None

    def get_capital(self) -> Optional[County]:
        if self.capital_county_id is None:
            return None
        for c in self.counties:
            if c.id == self.capital_county_id:
                return c
        return None

    def domain_counties(self) -> List[County]:
        """
        Counties directly held by the realm ruler (domain).
        (If you have baronies/duchies later, you can generalize this.)
        """
        if self.ruler is None:
            return []
        return [c for c in self.counties if c.holder is self.ruler]

    def all_counties(self, include_vassals: bool = True) -> List[County]:
        if not include_vassals:
            return list(self.counties)
        out = list(self.counties)
        for v in self.vassals:
            out.extend(v.all_counties(include_vassals=True))
        return out

    # --- Realm stats helpers ---

    def total_development(self, include_vassals: bool = True) -> int:
        return sum(c.development for c in self.all_counties(include_vassals=include_vassals))

    def average_control(self, include_vassals: bool = True) -> float:
        cs = self.all_counties(include_vassals=include_vassals)
        if not cs:
            return 0.0
        return sum(c.control for c in cs) / len(cs)

    def realm_stability_score(self) -> float:
        """
        A simple proxy you can use for factions/revolts/events.
        You can expand this with opinion, dread, legitimacy, etc.
        """
        self.laws.clamp()
        avg_control = self.average_control(include_vassals=False)  # focus on demesne
        dev = self.total_development(include_vassals=False)
        authority_bonus = self.laws.crown_authority * 2.5
        return (avg_control * 0.6) + (dev * 1.0) + authority_bonus

    # --- Vassal structure ---

    def add_vassal(self, vassal: "Realm") -> None:
        if vassal is self:
            raise ValueError("A realm cannot vassalize itself.")
        if vassal not in self.vassals:
            self.vassals.append(vassal)
        vassal.liege = self

    def remove_vassal(self, vassal_id: str) -> None:
        kept: List[Realm] = []
        for v in self.vassals:
            if v.id == vassal_id:
                v.liege = None
            else:
                kept.append(v)
        self.vassals = kept

    # --- Identity actions (conversion / cultural acceptance placeholders) ---

    def convert_realm_faith(self, new_faith: Faith) -> None:
        """Realm-level faith change (doesn't instantly convert counties)."""
        self.faith = new_faith

    def adopt_realm_culture(self, new_culture: Culture) -> None:
        """Realm-level culture change (doesn't instantly convert counties)."""
        self.culture = new_culture
