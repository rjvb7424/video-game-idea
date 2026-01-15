# domain.py
from dataclasses import dataclass, field
from typing import Dict, Optional, List

@dataclass
class Character:
    fname: str
    lname: str
    age: int
    gold: float = 0.0
    xp: int = 0
    inventory: list[str] = field(default_factory=list)

    loyalty: int = 50
    opinion_of_player: int = 0
    intrigue: int = 10
    role: str = "Courtier"

    @property
    def name(self) -> str:
        return f"{self.fname} {self.lname}".strip()

@dataclass
class Realm:
    name: str
    ruler: Character
    gold: float = 120.0
    prestige: int = 80
    piety: int = 35
    development: int = 12

    def daily_income(self) -> float:
        return 0.05 * self.development

@dataclass
class BuildingInstance:
    building_id: str
    level: int = 1

@dataclass
class Construction:
    building_id: str
    days_left: int
    slot_index: int

@dataclass
class Holding:
    name: str = "Castle"
    slots: int = 3
    buildings: List[Optional[BuildingInstance]] = field(default_factory=list)
    construction: Optional[Construction] = None

    def __post_init__(self):
        if not self.buildings:
            self.buildings = [None for _ in range(self.slots)]

@dataclass
class County:
    id: int
    name: str
    realm: Realm

    # map: province id is also the "id"
    holding: Holding = field(default_factory=Holding)

    # basic terrain for flavor/effects later
    terrain: str = "plains"  # plains/forest/hills/mountain/water
