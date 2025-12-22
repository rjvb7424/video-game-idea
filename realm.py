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

class Culture:
    id: str = uuid4().hex
    name: str
    description: str
    # TODO: expand with modifiers, traditions

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
