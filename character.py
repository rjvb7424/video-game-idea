from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Iterable
from uuid import uuid4


# ---------- Enums ----------

class SkillName(str, Enum):
    DIPLOMACY = "diplomacy"
    MARTIAL = "martial"
    STEWARDSHIP = "stewardship"
    INTRIGUE = "intrigue"
    LEARNING = "learning"
    PROWESS = "prowess"


class RelationType(Enum):
    # Family
    PARENT = auto()
    CHILD = auto()
    SPOUSE = auto()

    # Social
    FRIEND = auto()
    RIVAL = auto()
    LOVER = auto()

    # Feudal
    LIEGE = auto()
    VASSAL = auto()

    # Court/education
    GUARDIAN = auto()
    WARD = auto()

    # Misc
    PRISONER = auto()
    JAILER = auto()


class TitleRank(Enum):
    BARONY = auto()
    COUNTY = auto()
    DUCHY = auto()
    KINGDOM = auto()
    EMPIRE = auto()


# ---------- Core data objects ----------

@dataclass(frozen=True)
class Trait:
    """
    CK3-style trait: just a name + modifiers.
    Modifiers can be skills, health, fertility, stress gain, etc.
    """
    name: str
    modifiers: Dict[str, float] = field(default_factory=dict)


@dataclass
class Skills:
    diplomacy: int = 0
    martial: int = 0
    stewardship: int = 0
    intrigue: int = 0
    learning: int = 0
    prowess: int = 0

    def get(self, skill: SkillName) -> int:
        return int(getattr(self, skill.value))

    def add(self, skill: SkillName, delta: int) -> None:
        setattr(self, skill.value, self.get(skill) + int(delta))

    def as_dict(self) -> Dict[str, int]:
        return {
            "diplomacy": self.diplomacy,
            "martial": self.martial,
            "stewardship": self.stewardship,
            "intrigue": self.intrigue,
            "learning": self.learning,
            "prowess": self.prowess,
        }


@dataclass
class Relationship:
    other_id: str
    kind: RelationType
    opinion: int = 0          # CK3-ish opinion number (-100..+100-ish)
    strength: float = 1.0     # useful for "friendship level", "rival intensity", etc.


@dataclass(frozen=True)
class Title:
    name: str
    rank: TitleRank
    # Optional: de jure / de facto structures later


@dataclass(frozen=True)
class Secret:
    name: str
    severity: int = 1   # 1..5
    # Optional: type/category, targets, discovery chance, etc.


@dataclass
class Hook:
    owner_id: str
    target_id: str
    strength: int = 1   # 1 weak, 2 strong


# ---------- Character ----------

class Character:
    def __init__(self, fname: str, lname: str, age: int):
        self.id: str = uuid4().hex

        # Identity
        self.fname = fname
        self.lname = lname
        self.age = int(age)

        # “World” identity tags (expand later into objects)
        self.dynasty: Optional[str] = None
        self.culture: Optional[str] = None
        self.faith: Optional[str] = None

        # Stats
        self.base_skills = Skills()
        self.traits: List[Trait] = []

        # Character state
        self.health: float = 5.0         # simple scale; CK3 uses health mechanics
        self.fertility: float = 0.5      # 0.0..1.0 baseline
        self.stress: float = 0.0         # grows with events; thresholds cause breaks
        self.dread: float = 0.0          # intimidation

        # Economy / meta currencies
        self.gold: float = 0.0
        self.prestige: float = 0.0
        self.piety: float = 0.0
        self.renown: float = 0.0

        # Relationships
        self._relationships: Dict[str, List[Relationship]] = {}  # other_id -> list of relationships
        self.parents: Set[str] = set()
        self.children: Set[str] = set()
        self.spouses: Set[str] = set()

        # Titles / claims
        self.titles: List[Title] = []
        self.claims: List[Title] = []
        self.primary_title: Optional[Title] = None

        # Secrets / hooks
        self.secrets: List[Secret] = []
        self.hooks: List[Hook] = []

        # Lifestyle / perks (placeholders)
        self.lifestyle: Optional[str] = None
        self.perks: Set[str] = set()

    def __repr__(self):
        return f"{self.fname.capitalize()} {self.lname.capitalize()}"

    # ---------- Traits & modifiers ----------

    def add_trait(self, trait: Trait) -> None:
        self.traits.append(trait)

    def _sum_modifiers(self) -> Dict[str, float]:
        total: Dict[str, float] = {}
        for t in self.traits:
            for k, v in t.modifiers.items():
                total[k] = total.get(k, 0.0) + float(v)
        return total

    def skill(self, skill: SkillName) -> int:
        """
        Effective skill = base + trait bonuses (and later: education, perks, artifacts, council, etc.)
        """
        mods = self._sum_modifiers()
        bonus = int(mods.get(skill.value, 0.0))
        return self.base_skills.get(skill) + bonus

    def effective_skills(self) -> Dict[str, int]:
        return {s.value: self.skill(s) for s in SkillName}

    # ---------- Relationships ----------

    def add_relationship(self, other: Character, kind: RelationType, opinion: int = 0, strength: float = 1.0) -> None:
        rel = Relationship(other_id=other.id, kind=kind, opinion=int(opinion), strength=float(strength))
        self._relationships.setdefault(other.id, []).append(rel)

    def remove_relationship(self, other: Character, kind: RelationType) -> None:
        if other.id not in self._relationships:
            return
        self._relationships[other.id] = [r for r in self._relationships[other.id] if r.kind != kind]
        if not self._relationships[other.id]:
            del self._relationships[other.id]

    def relationships_with(self, other: Character) -> List[Relationship]:
        return list(self._relationships.get(other.id, []))

    def opinion_of(self, other: Character) -> int:
        """
        CK3-ish: base from explicit relationship opinions + trait-based drift hooks later.
        """
        rels = self._relationships.get(other.id, [])
        base = sum(r.opinion for r in rels)

        # Example: simple trait interactions (expand however you want)
        mods = self._sum_modifiers()
        base += int(mods.get("general_opinion", 0.0))

        # Clamp to a reasonable range
        return max(-100, min(100, base))

    # ---------- Family helpers ----------

    def marry(self, other: Character, opinion_bonus: int = 20) -> None:
        # Add spouse link both ways
        self.spouses.add(other.id)
        other.spouses.add(self.id)

        self.add_relationship(other, RelationType.SPOUSE, opinion=opinion_bonus, strength=1.0)
        other.add_relationship(self, RelationType.SPOUSE, opinion=opinion_bonus, strength=1.0)

    def add_child(self, child: Character) -> None:
        # Parent <-> child links both ways
        self.children.add(child.id)
        child.parents.add(self.id)

        self.add_relationship(child, RelationType.CHILD, opinion=30, strength=1.0)
        child.add_relationship(self, RelationType.PARENT, opinion=30, strength=1.0)

    # ---------- Feudal helpers ----------

    def set_liege(self, liege: Character) -> None:
        # Clear any previous liege relationship if needed (optional)
        self.add_relationship(liege, RelationType.LIEGE, opinion=0, strength=1.0)
        liege.add_relationship(self, RelationType.VASSAL, opinion=0, strength=1.0)

    # ---------- Titles / claims ----------

    def grant_title(self, title: Title, make_primary: bool = False) -> None:
        self.titles.append(title)
        if make_primary or self.primary_title is None:
            self.primary_title = title

    def add_claim(self, title: Title) -> None:
        self.claims.append(title)

    # ---------- Secrets & hooks ----------

    def add_secret(self, secret: Secret) -> None:
        self.secrets.append(secret)

    def add_hook_on(self, target: Character, strength: int = 1) -> None:
        self.hooks.append(Hook(owner_id=self.id, target_id=target.id, strength=int(strength)))

    # ---------- Time progression (very simple) ----------

    def year_tick(self) -> None:
        """
        Called once per in-game year. Expand with:
        - health changes / disease / aging
        - pregnancy/birth
        - stress decay/growth
        - skill growth (education, lifestyle)
        """
        self.age += 1

        # Example aging: tiny health decline after 40
        if self.age >= 40:
            self.health -= 0.05

        # Example: natural stress decay
        self.stress = max(0.0, self.stress - 0.1)

    def is_alive(self) -> bool:
        return self.health > 0.0


# ---------- Example trait set (you'll build a big library of these) ----------

BRAVE = Trait("brave", {"prowess": 2, "general_opinion": 5})
CRAVEN = Trait("craven", {"prowess": -2, "general_opinion": -5})
DILIGENT = Trait("diligent", {"stewardship": 1, "learning": 1})
DECEITFUL = Trait("deceitful", {"intrigue": 2, "general_opinion": -10})


if __name__ == "__main__":
    a = Character("joao", "silva", 22)
    b = Character("maria", "pereira", 21)

    a.base_skills = Skills(diplomacy=6, martial=4, stewardship=7, intrigue=3, learning=5, prowess=2)
    a.add_trait(DILIGENT)
    a.add_trait(BRAVE)

    b.base_skills = Skills(diplomacy=8, martial=1, stewardship=5, intrigue=6, learning=4, prowess=1)
    b.add_trait(DECEITFUL)

    a.marry(b)
    print(a, "skills:", a.effective_skills())
    print("A opinion of B:", a.opinion_of(b))
