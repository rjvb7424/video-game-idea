# buildings.py
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class BuildingDef:
    id: str
    name: str
    cost: int
    build_days: int
    # Effects are simple numbers for now; you can expand later.
    income_bonus: float = 0.0         # added to county daily income
    development_bonus: int = 0        # added to realm dev (or county dev later)

BUILDINGS: Dict[str, BuildingDef] = {
    "farm_1": BuildingDef(
        id="farm_1",
        name="Farms & Fields I",
        cost=60,
        build_days=90,
        income_bonus=0.20,
        development_bonus=1,
    ),
    "lumber_1": BuildingDef(
        id="lumber_1",
        name="Logging Camps I",
        cost=55,
        build_days=75,
        income_bonus=0.15,
        development_bonus=1,
    ),
    "quarry_1": BuildingDef(
        id="quarry_1",
        name="Quarries I",
        cost=70,
        build_days=110,
        income_bonus=0.25,
        development_bonus=0,
    ),
    "barracks_1": BuildingDef(
        id="barracks_1",
        name="Barracks I",
        cost=80,
        build_days=120,
        income_bonus=0.05,
        development_bonus=0,
    ),
}

def terrain_allowed(building_id: str, terrain: str) -> bool:
    # Keep it simple; expand later.
    if building_id == "lumber_1":
        return terrain in ("forest", "hills")
    if building_id == "farm_1":
        return terrain in ("plains", "hills")
    if building_id == "quarry_1":
        return terrain in ("hills", "mountain")
    return terrain != "water"
