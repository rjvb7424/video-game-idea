from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingDef:
    id: str
    name: str
    food_bonus: float = 0.0
    gold_upkeep: float = 0.0
    max_level: int = 5


BUILDINGS = {
    "farm": BuildingDef(
        id="farm",
        name="Farm",
        food_bonus=387.5,
        gold_upkeep=1.0,
        max_level=5,
    ),
}


def make_building(building_id, level=1):
    return {"id": building_id, "level": int(max(1, level))}


def get_building_id(entry):
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry.get("id")
    return entry


def get_building_level(entry):
    if entry is None:
        return 0
    if isinstance(entry, dict):
        return int(entry.get("level", 1))
    return 1


def normalize_building(entry):
    if entry is None:
        return None
    if isinstance(entry, dict):
        if "id" not in entry:
            return None
        entry.setdefault("level", 1)
        return entry
    return {"id": entry, "level": 1}


def building_food_output(entry):
    bid = get_building_id(entry)
    if not bid:
        return 0.0
    bdef = BUILDINGS.get(bid)
    if not bdef:
        return 0.0
    level = get_building_level(entry)
    return bdef.food_bonus * level


def building_gold_upkeep(entry):
    bid = get_building_id(entry)
    if not bid:
        return 0.0
    bdef = BUILDINGS.get(bid)
    if not bdef:
        return 0.0
    level = get_building_level(entry)
    return bdef.gold_upkeep * level


def building_max_level(entry):
    bid = get_building_id(entry)
    if not bid:
        return 0
    bdef = BUILDINGS.get(bid)
    if not bdef:
        return 0
    return max(1, int(bdef.max_level))
