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

    # CK-ish stats used by your events
    loyalty: int = 50              # 0..100
    opinion_of_player: int = 0     # -100..100
    intrigue: int = 10             # 0..30-ish
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
    """A single map province (rectangle for now)."""
    id: str
    name: str
    realm: Realm
    grid_x: int
    grid_y: int
