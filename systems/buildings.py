from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingDef:
    id: str
    name: str
    food_bonus: float = 0.0


BUILDINGS = {
    "farm": BuildingDef(
        id="farm",
        name="Farm",
        food_bonus=300.0,
    ),
}
