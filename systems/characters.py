import random

from core.math_utils import clamp
from systems.traits import TRAITS, normalize_traits, apply_trait_effects, _stats_list_to_dict


NORSE_MALE_NAMES = [
    "Harald", "Olav", "Eirik", "Leif", "Bjorn", "Ivar", "Sven", "Knut", "Sigurd", "Ragnar",
    "Hakon", "Halfdan", "Ulf", "Torstein", "Arne", "Gunnar", "Sten", "Trygve", "Asbjorn", "Ketil",
    "Rolf", "Vidar", "Styrbjorn", "Torvald", "Einar",
]

NORSE_FEMALE_NAMES = [
    "Astrid", "Ingrid", "Sigrid", "Freydis", "Gudrun", "Helga", "Ragnhild", "Thyra", "Solveig", "Gunnhild",
    "Tove", "Hilde", "Kari", "Liv", "Ylva", "Alfhild", "Ase", "Signe", "Brynhild", "Eira",
]

NORSE_HOUSES = [
    "Yngling", "Fairhair", "Skjold", "Ragnarsson", "Hrafn", "Hvitserk", "Lodbrok", "Hardrada",
    "Ulfsson", "Eiriksson", "Sigurdsson", "Haraldsson", "Gunnarsen", "Olafsson", "Ketilsson",
    "Sturlung", "Ragnvaldsson", "Torberg", "Hauksson", "Skallagrimsson",
]

CULTURE_FIRST_NAMES = {
    "Iberian":  ["Sancho", "Fernando", "Alfonso", "Ramiro", "García", "Rodrigo", "Diego", "Enrique"],
    "Frankish": ["Hugh", "Louis", "Charles", "Philippe", "Robert", "Henri", "Gaston", "Guillaume"],
    "Occitan":  ["Raymond", "Bernat", "Pons", "Arnaut", "Guilhem", "Peire", "Bertran", "Roger"],
    "Germanic": ["Heinrich", "Otto", "Konrad", "Friedrich", "Lothar", "Siegfried", "Arnulf", "Albrecht"],
    "Slavic":   ["Mieszko", "Bolesław", "Vladimir", "Sviatoslav", "Jaromir", "Radovan", "Milan", "Dragomir"],
    "Nordfolken": {"male": NORSE_MALE_NAMES, "female": NORSE_FEMALE_NAMES},
}

CULTURE_HOUSES = {
    "Iberian":  ["de Aragón", "de León", "de Navarra", "de Castela", "de Coimbra", "de Porto"],
    "Frankish": ["de Valois", "de Blois", "de Anjou", "de Normandie", "de Champagne"],
    "Occitan":  ["de Toulouse", "de Foix", "de Provence", "de Béarn", "de Carcassonne"],
    "Germanic": ["von Habsburg", "von Bayern", "von Saxen", "von Schwaben", "von Thuringen"],
    "Slavic":   ["Piast", "Rurikid", "Přemyslid", "Nemanjić", "Arpad"],
    "Nordfolken": NORSE_HOUSES,
}


def _realm_core_name(realm_name: str) -> str:
    if " of " in realm_name:
        return realm_name.split(" of ", 1)[1]
    return realm_name


def _normalize_gender(rnd: random.Random, gender=None) -> str:
    if gender in ("male", "female"):
        return gender
    return rnd.choice(["male", "female"])


def _pick_first_name(rnd: random.Random, gender: str, culture: str) -> str:
    pool = CULTURE_FIRST_NAMES.get(culture)
    names = None
    if isinstance(pool, dict):
        names = pool.get(gender) or pool.get("male") or pool.get("female")
    elif isinstance(pool, list):
        names = pool
    if not names:
        names = NORSE_FEMALE_NAMES if gender == "female" else NORSE_MALE_NAMES
    return rnd.choice(names)


def _pick_house(rnd: random.Random, culture: str) -> str:
    houses = CULTURE_HOUSES.get(culture) or NORSE_HOUSES
    return rnd.choice(houses)


def _rank_for_realm_size(sz: int, gender: str) -> str:
    if sz >= 3:
        return "King" if gender == "male" else "Queen"
    if sz == 2:
        return "Duke" if gender == "male" else "Duchess"
    return "Count" if gender == "male" else "Countess"


def _roll_age(rnd: random.Random, role: str) -> int:
    if role == "heir":
        return rnd.randint(0, 16)
    if role == "spouse":
        return rnd.randint(18, 55)
    return rnd.randint(18, 60)


def _starting_spouse_chance(age: int) -> float:
    if age < 20:
        return 0.20
    if age < 25:
        return 0.45
    if age < 35:
        return 0.70
    if age < 45:
        return 0.75
    return 0.55


def _starting_heir_chance(age: int, has_spouse: bool) -> float:
    if age < 20:
        return 0.05
    if age < 25:
        return 0.20 if has_spouse else 0.10
    if age < 35:
        return 0.50 if has_spouse else 0.25
    if age < 45:
        return 0.65 if has_spouse else 0.40
    return 0.60 if has_spouse else 0.35


def _heir_title(realm_size: int, gender: str) -> str:
    if realm_size >= 3:
        return "Prince" if gender == "male" else "Princess"
    return "Heir"


def _roll_stat(rnd: random.Random, lo=3, hi=14) -> int:
    v = int(round(rnd.gauss(8.5, 2.2)))
    return clamp(v, lo, hi)


def generate_random_traits(rnd: random.Random, min_n=3, max_n=3) -> list[str]:
    keys = list(TRAITS.keys())
    target = 3
    chosen: list[str] = []
    tries = 0
    while len(chosen) < target and tries < 400:
        tries += 1
        t = rnd.choice(keys)
        if t in chosen:
            continue
        opp = TRAITS.get(t, {}).get("opposites", set())
        if any(o in chosen for o in opp):
            continue
        chosen.append(t)
    return normalize_traits(chosen, max_traits=3)


def generate_spouse(
    rnd: random.Random,
    *,
    realm_name: str,
    realm_size: int,
    culture: str,
    faith: str,
    house: str,
    ruler_gender: str,
) -> dict:
    gender = "female" if ruler_gender == "male" else "male"
    first = _pick_first_name(rnd, gender, culture)
    rank = _rank_for_realm_size(realm_size, gender)
    core = _realm_core_name(realm_name)
    return {
        "name": f"{rank} {first}",
        "title": f"{rank} of {core}",
        "house": house,
        "culture": culture,
        "faith": faith,
        "gender": gender,
        "age": _roll_age(rnd, "spouse"),
    }


def generate_heir(
    rnd: random.Random,
    *,
    realm_name: str,
    realm_size: int,
    culture: str,
    faith: str,
    house: str,
) -> dict:
    gender = rnd.choice(["male", "female"])
    first = _pick_first_name(rnd, gender, culture)
    title = _heir_title(realm_size, gender)
    core = _realm_core_name(realm_name)
    display_name = f"{title} {first}" if title != "Heir" else first
    display_title = f"{title} of {core}" if title != "Heir" else f"Heir of {core}"
    return {
        "name": display_name,
        "title": display_title,
        "house": house,
        "culture": culture,
        "faith": faith,
        "gender": gender,
        "age": _roll_age(rnd, "heir"),
    }


def ensure_ruler_identity(
    rnd: random.Random,
    ruler: dict,
    *,
    culture: str,
) -> dict:
    if ruler.get("gender") not in ("male", "female"):
        ruler["gender"] = _normalize_gender(rnd, ruler.get("gender"))
    if not isinstance(ruler.get("age"), int):
        ruler["age"] = _roll_age(rnd, "ruler")
    if not ruler.get("house"):
        ruler["house"] = f"House {_pick_house(rnd, culture)}"
    return ruler


def generate_ruler(rnd: random.Random, realm_name: str, realm_size: int, culture: str, faith: str) -> dict:
    gender = _normalize_gender(rnd, None)
    age = _roll_age(rnd, "ruler")
    first = _pick_first_name(rnd, gender, culture)
    house = _pick_house(rnd, culture)
    rank = _rank_for_realm_size(realm_size, gender)
    core = _realm_core_name(realm_name)

    stats = [
        ("Diplomacy",  _roll_stat(rnd)),
        ("Martial",    _roll_stat(rnd)),
        ("Stewardship", _roll_stat(rnd)),
        ("Intrigue",   _roll_stat(rnd)),
        ("Learning",   _roll_stat(rnd)),
        ("Prowess",    _roll_stat(rnd)),
    ]

    traits = generate_random_traits(rnd, 2, 4)

    character = {
        "name": f"{rank} {first}",
        "title": f"{rank} of {core}",
        "house": f"House {house}",
        "culture": culture,
        "faith": faith,
        "gender": gender,
        "age": age,
        "traits": traits,
        "stats": stats,
    }

    if rnd.random() < _starting_spouse_chance(age):
        character["spouse"] = generate_spouse(
            rnd,
            realm_name=realm_name,
            realm_size=realm_size,
            culture=culture,
            faith=faith,
            house=character["house"],
            ruler_gender=gender,
        )
    if rnd.random() < _starting_heir_chance(age, "spouse" in character):
        character["heir"] = generate_heir(
            rnd,
            realm_name=realm_name,
            realm_size=realm_size,
            culture=culture,
            faith=faith,
            house=character["house"],
        )

    character["base_stats"] = _stats_list_to_dict(character["stats"])
    apply_trait_effects(character)

    return character
