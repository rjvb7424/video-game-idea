# external imports
from dataclasses import dataclass, field
from uuid import uuid4
import random

@dataclass 
class Skills:
    """A class which holds the main skills of a character."""
    @staticmethod
    def _generate_skill_value() -> int:
        """Returns a skill value based on a Gaussian distribution."""
        value = random.gauss(5, 3)
        value = round(value)
        value = max(0, min(20, value))
        return int(value)
    
    diplomacy: int = field(default_factory=lambda: Skills._generate_skill_value())
    martial: int = field(default_factory=lambda: Skills._generate_skill_value())
    stewardship: int = field(default_factory=lambda: Skills._generate_skill_value())
    intrigue: int = field(default_factory=lambda: Skills._generate_skill_value())
    learning: int = field(default_factory=lambda: Skills._generate_skill_value())
    prowess: int = field(default_factory=lambda: Skills._generate_skill_value())

    def get(self, name: str) -> int:
        return getattr(self, name)

    def set(self, name: str, value: int) -> None:
        setattr(self, name, value)

class Character:
    """A character in the game world."""
    def __init__(self, fname: str, lname: str, age: int):
        # unique identifier
        self.id: str = uuid4().hex
        # basic identity
        self.fname: str = fname
        self.lname: str = lname
        self.age: int = age
        # extended identity
        self.dynasty: str = None
        self.culture: str = None
        self.faith: str = None
        # skills
        self.skills = Skills()
        # character states
        self.health: float = 1.0
        self.fertility: float = 0.5
        self.stress: float = 0.0
        self.dread: float = 0.0
        # currencies
        self.gold: int = 0
        self.prestige: int = 0
        self.piety: int = 0