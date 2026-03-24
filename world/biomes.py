import os


DEFAULT_BIOME = "forest"

BIOME_DEFS = {
    "forest": {
        "label": "Forest",
        "color": (68, 94, 62),
        "tile": "forest.png",
    },
    "plains": {
        "label": "Plains",
        "color": (132, 126, 82),
        "tile": "plains.png",
    },
    "tundra": {
        "label": "Tundra",
        "color": (156, 162, 160),
        "tile": "tundra.png",
    },
    "cold_bog": {
        "label": "Cold Bog",
        "color": (78, 98, 82),
        "tile": "cold_bog.png",
    },
    "village": {
        "label": "Village",
        "color": (144, 108, 78),
        "tile": "village.png",
    },
    "mountain": {
        "label": "Mountain",
        "color": (116, 114, 112),
        "tile": "mountain.png",
    },
}

BIOME_ALIASES = {
    "boreal_forest": "forest",
    "forest": "forest",
    "plains": "plains",
    "tundra": "tundra",
    "cold_bog": "cold_bog",
    "village": "village",
    "mountain": "mountain",
    "mountains": "mountain",
    "hill": "mountain",
    "hills": "mountain",
    "drylands": "plains",
    "fertile": "plains",
}

DEFAULT_TERRAIN = DEFAULT_BIOME
TERRAIN_DEFS = BIOME_DEFS
TERRAIN_ALIASES = BIOME_ALIASES

_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
_TILE_DIR = os.path.join(_ASSETS_DIR, "tiles")


def normalize_biome_key(biome):
    if biome is None:
        return None
    key = str(biome).strip().lower().replace(" ", "_")
    if not key:
        return None
    key = BIOME_ALIASES.get(key, key)
    if key in BIOME_DEFS:
        return key
    return None


def normalize_terrain_key(terrain):
    return normalize_biome_key(terrain)


def get_biome_label(biome):
    key = normalize_biome_key(biome)
    if key is None:
        return "Unknown"
    return BIOME_DEFS[key]["label"]


def get_terrain_label(terrain):
    return get_biome_label(terrain)


def get_biome_color(biome):
    key = normalize_biome_key(biome) or DEFAULT_BIOME
    return BIOME_DEFS[key]["color"]


def get_terrain_color(terrain):
    return get_biome_color(terrain)


def get_biome_tile_path(biome):
    key = normalize_biome_key(biome) or DEFAULT_BIOME
    tile_name = BIOME_DEFS[key]["tile"]
    path = os.path.join(_TILE_DIR, tile_name)
    if os.path.exists(path):
        return path
    if key == "forest":
        legacy_path = os.path.join(_ASSETS_DIR, "boreal_forest.png")
        if os.path.exists(legacy_path):
            return legacy_path
    return None


def get_terrain_tile_path(terrain):
    return get_biome_tile_path(terrain)
