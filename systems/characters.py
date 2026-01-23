import random

from core.math_utils import clamp
from systems.traits import TRAITS, normalize_traits, apply_trait_effects, _stats_list_to_dict


CULTURE_FIRST_NAMES = {
    "Iberian":  ["Sancho", "Fernando", "Alfonso", "Ramiro", "García", "Rodrigo", "Diego", "Enrique"],
    "Frankish": ["Hugh", "Louis", "Charles", "Philippe", "Robert", "Henri", "Gaston", "Guillaume"],
    "Occitan":  ["Raymond", "Bernat", "Pons", "Arnaut", "Guilhem", "Peire", "Bertran", "Roger"],
    "Germanic": ["Heinrich", "Otto", "Konrad", "Friedrich", "Lothar", "Siegfried", "Arnulf", "Albrecht"],
    "Slavic":   ["Mieszko", "Bolesław", "Vladimir", "Sviatoslav", "Jaromir", "Radovan", "Milan", "Dragomir"],
}

CULTURE_HOUSES = {
    "Iberian":  ["de Aragón", "de León", "de Navarra", "de Castela", "de Coimbra", "de Porto"],
    "Frankish": ["de Valois", "de Blois", "de Anjou", "de Normandie", "de Champagne"],
    "Occitan":  ["de Toulouse", "de Foix", "de Provence", "de Béarn", "de Carcassonne"],
    "Germanic": ["von Habsburg", "von Bayern", "von Saxen", "von Schwaben", "von Thuringen"],
    "Slavic":   ["Piast", "Rurikid", "Přemyslid", "Nemanjić", "Arpad"],
}


def _realm_core_name(realm_name: str) -> str:
    if " of " in realm_name:
        return realm_name.split(" of ", 1)[1]
    return realm_name


def _rank_for_realm_size(sz: int) -> str:
    if sz >= 3:
        return "King"
    if sz == 2:
        return "Duke"
    return "Count"


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


def generate_ruler(rnd: random.Random, realm_name: str, realm_size: int, culture: str, faith: str) -> dict:
    first = rnd.choice(CULTURE_FIRST_NAMES.get(culture, ["Aurelian", "Marcus", "Cassius"]))
    house = rnd.choice(CULTURE_HOUSES.get(culture, ["de Terra"]))
    rank = _rank_for_realm_size(realm_size)
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
        "traits": traits,
        "stats": stats,
    }

    character["base_stats"] = _stats_list_to_dict(character["stats"])
    apply_trait_effects(character)

    return character
