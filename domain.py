# domain.py
from dataclasses import dataclass, field

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
class County:
    id: str
    name: str
    realm: Realm
    grid_x: int
    grid_y: int

    biome: str = "plains"      # plains, forest, mountain, water, hills, desert...
    discovered: bool = False   # fog-of-war support
