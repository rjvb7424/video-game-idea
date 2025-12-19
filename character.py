# external imports
from uuid import uuid4
import random

class Skills:
    """A class which holds the main skills of a character. Also contains methods to manipulate them."""
    def __init__(self, diplomacy: int = None, martial: int = None, stewardship: int = None, intrigue: int = None, learning: int = None, prowess: int = None):
        if diplomacy is None: self.diplomacy = self._generate_skill_value()
        else: self.diplomacy = diplomacy
        if martial is None: self.martial = self._generate_skill_value()
        else: self.martial = martial
        if stewardship is None: self.stewardship = self._generate_skill_value()
        else: self.stewardship = stewardship
        if intrigue is None: self.intrigue = self._generate_skill_value()
        else: self.intrigue = intrigue
        if learning is None: self.learning = self._generate_skill_value()
        else: self.learning = learning
        if prowess is None: self.prowess = self._generate_skill_value()
        else: self.prowess = prowess

    @staticmethod
    def _generate_skill_value() -> int:
        """Returns a skill value based on a Gaussian distribution."""
        value = random.gauss(5, 3)
        value = round(value)
        value = max(0, min(20, value))
        return int(value)
    
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
        self.fname = fname
        self.lname = lname
        self.age = age
        # extended identity
        self.dynasty = None
        self.culture = None
        self.faith = None
        # skills & traits
        self.skills = Skills()

        # Character state
        self.health: float = 5.0
        self.fertility: float = 0.5
        self.stress: float = 0.0
        self.dread: float = 0.0

        # currencies
        self.gold: float = 0.0
        self.prestige: float = 0.0
        self.piety: float = 0.0