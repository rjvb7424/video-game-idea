from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingDef:
    id: str
    name: str
    food_bonus: float = 0.0
    gold_upkeep: float = 0.0
    gold_rate_bonus: float = 0.0
    piety_rate_bonus: float = 0.0
    prestige_rate_bonus: float = 0.0
    levy_mult_bonus: float = 0.0
    stress_monthly_relief: float = 0.0
    build_cost_gold: int = 0
    upgrade_cost_gold: int = 0
    max_level: int = 5


BUILDINGS = {
    "farm": BuildingDef(
        id="farm",
        name="Farm",
        food_bonus=387.5,
        gold_upkeep=1.0,
        build_cost_gold=40,
        upgrade_cost_gold=30,
        max_level=5,
    ),
    "tradeport": BuildingDef(
        id="tradeport",
        name="Tradeport",
        gold_upkeep=1.5,
        gold_rate_bonus=2.2,
        prestige_rate_bonus=0.3,
        build_cost_gold=85,
        upgrade_cost_gold=55,
        max_level=4,
    ),
    "temple": BuildingDef(
        id="temple",
        name="Temple",
        gold_upkeep=0.8,
        piety_rate_bonus=1.8,
        stress_monthly_relief=0.8,
        build_cost_gold=65,
        upgrade_cost_gold=45,
        max_level=4,
    ),
    "barracks": BuildingDef(
        id="barracks",
        name="Barracks",
        gold_upkeep=1.2,
        levy_mult_bonus=0.045,
        prestige_rate_bonus=0.15,
        build_cost_gold=75,
        upgrade_cost_gold=50,
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


def _building_scaled_value(entry, attr):
    bid = get_building_id(entry)
    if not bid:
        return 0.0
    bdef = BUILDINGS.get(bid)
    if not bdef:
        return 0.0
    level = get_building_level(entry)
    return float(getattr(bdef, attr, 0.0)) * level


def building_gold_rate_bonus(entry):
    return _building_scaled_value(entry, "gold_rate_bonus")


def building_piety_rate_bonus(entry):
    return _building_scaled_value(entry, "piety_rate_bonus")


def building_prestige_rate_bonus(entry):
    return _building_scaled_value(entry, "prestige_rate_bonus")


def building_levy_mult_bonus(entry):
    return _building_scaled_value(entry, "levy_mult_bonus")


def building_stress_monthly_relief(entry):
    return _building_scaled_value(entry, "stress_monthly_relief")
