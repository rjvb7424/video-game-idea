from core.math_utils import clamp


TRAITS = {
    "forgiving":  {"name": "Forgiving",  "opposites": {"vengeful"}, "desc": "Lets go of slights and seeks reconciliation."},
    "vengeful":   {"name": "Vengeful",   "opposites": {"forgiving"}, "desc": "Remembers wrongs and pursues retribution."},

    "humble":     {"name": "Humble",     "opposites": {"proud"}, "desc": "Avoids vanity; accepts limitations."},
    "proud":      {"name": "Proud",      "opposites": {"humble"}, "desc": "Seeks glory; easily offended by disrespect."},

    "charitable": {"name": "Charitable", "opposites": {"greedy"}, "desc": "Gives freely; values mercy over wealth."},
    "greedy":     {"name": "Greedy",     "opposites": {"charitable"}, "desc": "Hoarder; values wealth and gain."},

    "patient":    {"name": "Patient",    "opposites": {"wrathful"}, "desc": "Slow to anger; endures hardship calmly."},
    "wrathful":   {"name": "Wrathful",   "opposites": {"patient"}, "desc": "Quick to anger; escalates conflict."},

    "chaste":     {"name": "Chaste",     "opposites": {"lustful"}, "desc": "Restrained desires."},
    "lustful":    {"name": "Lustful",    "opposites": {"chaste"}, "desc": "Indulgent desires."},

    "temperate":  {"name": "Temperate",  "opposites": {"gluttonous"}, "desc": "Moderation in appetite."},
    "gluttonous": {"name": "Gluttonous", "opposites": {"temperate"}, "desc": "Overindulgence in appetite."},

    "diligent":   {"name": "Diligent",   "opposites": {"lazy"}, "desc": "Hard-working and disciplined."},
    "lazy":       {"name": "Lazy",       "opposites": {"diligent"}, "desc": "Avoids effort; procrastinates."},
}

# Stats keys must match your character["stats"] tuples
STAT_KEYS = ["Diplomacy", "Martial", "Stewardship", "Intrigue", "Learning", "Prowess"]

# Per-trait stat modifiers
TRAIT_EFFECTS = {
    "forgiving":  {"Diplomacy": +2, "Martial": -1},
    "vengeful":   {"Martial": +2, "Diplomacy": -1},

    "humble":     {"Learning": +1, "Diplomacy": +1, "Prowess": -1},
    "proud":      {"Prowess": +2, "Diplomacy": -1},

    "charitable": {"Diplomacy": +2, "Stewardship": +1, "Intrigue": -1},
    "greedy":     {"Stewardship": +2, "Diplomacy": -1},

    "patient":    {"Learning": +1, "Stewardship": +1, "Martial": -1},
    "wrathful":   {"Martial": +2, "Prowess": +1, "Diplomacy": -1},

    "chaste":     {"Learning": +1, "Intrigue": -1},
    "lustful":    {"Intrigue": +2, "Diplomacy": +1, "Learning": -1},

    "temperate":  {"Stewardship": +1, "Learning": +1, "Prowess": -1},
    "gluttonous": {"Prowess": +1, "Stewardship": -1},

    "diligent":   {"Stewardship": +2, "Learning": +1, "Intrigue": -1},
    "lazy":       {"Stewardship": -2, "Martial": -1, "Intrigue": +1},
}


def _stats_list_to_dict(stats_list):
    return {k: int(v) for (k, v) in stats_list}


def _stats_dict_to_list(stats_dict):
    return [(k, int(stats_dict.get(k, 0))) for k in STAT_KEYS]


def apply_trait_effects(character: dict, lo=0, hi=20):
    """
    Recomputes character["stats"] from character["base_stats"] + trait modifiers.
    Creates base_stats if missing.
    """
    if "base_stats" not in character:
        character["base_stats"] = _stats_list_to_dict(character.get("stats", []))

    base = dict(character["base_stats"])
    out = dict(base)

    for t in character.get("traits", []):
        mods = TRAIT_EFFECTS.get(t, {})
        for stat, delta in mods.items():
            out[stat] = out.get(stat, 0) + delta

    for k in STAT_KEYS:
        out[k] = clamp(out.get(k, 0), lo, hi)

    character["stats"] = _stats_dict_to_list(out)
    return character


def trait_name(trait_id: str) -> str:
    return TRAITS.get(trait_id, {}).get("name", trait_id)


def normalize_traits(traits: list[str], max_traits: int = 3) -> list[str]:
    """Ensures no opposites coexist. Keeps the first encountered trait. Caps to max_traits."""
    out: list[str] = []
    have: set[str] = set()
    for t in traits:
        if t in have:
            continue
        opp = TRAITS.get(t, {}).get("opposites", set())
        if any(o in have for o in opp):
            continue
        out.append(t)
        have.add(t)
        if len(out) >= max_traits:
            break
    return out


def add_trait(character: dict, trait_id: str) -> tuple[bool, str]:
    """
    Adds a trait; if it has opposites, those are removed.
    Enforces a max of 3 traits total.
    Also applies stat effects after change.
    Returns (changed, message)
    """
    if trait_id not in TRAITS:
        return (False, f"Unknown trait '{trait_id}'.")

    character.setdefault("traits", [])
    character["traits"] = normalize_traits(character["traits"], max_traits=3)

    if trait_id in character["traits"]:
        return (False, f"{character.get('name','Character')} already has {trait_name(trait_id)}.")

    opposites = TRAITS[trait_id]["opposites"]
    removed = [t for t in character["traits"] if t in opposites]

    # Remove opposites first
    if removed:
        character["traits"] = [t for t in character["traits"] if t not in opposites]

    if len(character["traits"]) >= 3:
        if not removed:
            return (False, f"{character.get('name','Character')} already has 3 traits.")

    character["traits"].append(trait_id)
    character["traits"] = normalize_traits(character["traits"], max_traits=3)

    apply_trait_effects(character)

    if removed:
        return (True, f"Gained {trait_name(trait_id)} (removed {', '.join(trait_name(x) for x in removed)}).")
    return (True, f"Gained {trait_name(trait_id)}.")


FAITH_RULES = {
    "Catholic": {
        "virtues": {"forgiving", "humble", "charitable", "patient", "chaste", "temperate", "diligent"},
        "sins":    {"vengeful", "proud", "greedy", "wrathful", "lustful", "gluttonous", "lazy"},
        "base_piety_rate": 0,
    },
    "Orthodox": {
        "virtues": {"forgiving", "humble", "charitable", "patient", "temperate", "diligent"},
        "sins":    {"vengeful", "proud", "greedy", "wrathful", "gluttonous", "lazy"},
        "base_piety_rate": 0,
    },
    "Sunni": {
        "virtues": {"charitable", "patient", "temperate", "diligent"},
        "sins":    {"greedy", "wrathful", "gluttonous", "lazy"},
        "base_piety_rate": 0,
    },
    "Pagan": {
        "virtues": {"vengeful", "wrathful", "diligent"},
        "sins":    {"forgiving", "lazy"},
        "base_piety_rate": 0,
    },
    "Nordfolken Mythology": {
        "virtues": {"vengeful", "wrathful", "diligent", "proud"},
        "sins":    {"forgiving", "lazy", "humble", "patient"},
        "base_piety_rate": 0,
    },
    "Mozarabic": {
        "virtues": {"forgiving", "humble", "charitable", "patient", "temperate"},
        "sins":    {"vengeful", "proud", "greedy", "wrathful", "gluttonous"},
        "base_piety_rate": 0,
    },
}


def trait_alignment(character: dict) -> tuple[list[str], list[str], list[str]]:
    faith = character.get("faith", "Catholic")
    rules = FAITH_RULES.get(faith, {"virtues": set(), "sins": set(), "base_piety_rate": 0})

    virtues, sins, neutral = [], [], []
    for t in character.get("traits", []):
        if t in rules["virtues"]:
            virtues.append(t)
        elif t in rules["sins"]:
            sins.append(t)
        else:
            neutral.append(t)
    return virtues, sins, neutral


def compute_piety_rate(character: dict) -> tuple[int, dict]:
    faith = character.get("faith", "Catholic")
    rules = FAITH_RULES.get(faith, {"virtues": set(), "sins": set(), "base_piety_rate": 0})

    virtues, sins, neutral = trait_alignment(character)

    virtue_bonus = 1
    sin_penalty = 1

    rate = int(rules.get("base_piety_rate", 0))
    rate += virtue_bonus * len(virtues)
    rate -= sin_penalty * len(sins)

    breakdown = {
        "faith": faith,
        "base": int(rules.get("base_piety_rate", 0)),
        "virtues": virtues,
        "sins": sins,
        "neutral": neutral,
        "virtue_bonus": virtue_bonus * len(virtues),
        "sin_penalty": sin_penalty * len(sins),
    }
    return rate, breakdown
