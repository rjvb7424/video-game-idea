import math
import random

import pygame

from core.math_utils import clamp, lerp
from core.surfaces import make_noise_tile, tile_fill
from systems.characters import generate_ruler
from systems.buildings import make_building, get_building_id
from world.biomes import (
    BIOME_DEFS,
    DEFAULT_TERRAIN,
    get_terrain_color,
    get_terrain_tile_path,
    normalize_terrain_key,
)

# Map palette (subdued, CK1-ish)
SEA_DEEP = (18, 42, 80)
SEA_SHALLOWS = (30, 62, 110)
COAST_FOAM = (90, 110, 120)

LAND_GREEN = (70, 86, 58)
LAND_DRY = (92, 86, 60)
LAND_RICH = (88, 98, 70)
HILLS = (84, 82, 70)
MOUNTAIN = (88, 86, 84)
FOREST = (54, 70, 46)

FOG_DARK = (12, 12, 14)
BORDER_INK_DARK = (12, 12, 12)
BORDER_INK = (32, 30, 28)
BORDER_REALM_INK = (8, 8, 8)
WAR_BORDER_COLOR = (205, 60, 60)


class Province:
    def __init__(self, pid, name, is_capital=False):
        self.id = pid
        self.name = name
        self.realm_id = 0
        self.is_capital = is_capital
        self.landmark = None
        self.center = pygame.Vector2(0, 0)
        self.bounds_cells = pygame.Rect(0, 0, 1, 1)
        self.cell_count = 0
        self.terrain = DEFAULT_TERRAIN
        self.terrain_color = get_terrain_color(self.terrain)
        self.biome = self.terrain
        self.biome_color = self.terrain_color
        self.population = 0
        self.culture = "Nordfolken"
        self.faith = "Nordfolken Mythology"
        self.building_slots = 3
        self.buildings = [None for _ in range(self.building_slots)]

    def set_terrain(self, terrain_key):
        terrain_key = normalize_terrain_key(terrain_key) or DEFAULT_TERRAIN
        self.terrain = terrain_key
        self.terrain_color = get_terrain_color(terrain_key)
        self.biome = terrain_key
        self.biome_color = self.terrain_color

    def add_building(self, building_id):
        for idx, slot in enumerate(self.buildings):
            if slot is None:
                self.buildings[idx] = make_building(building_id, level=1)
                return idx
        return -1


def _value_noise_2d(w, h, cell_w, cell_h, seed):
    rnd = random.Random(seed)
    gw = max(2, int(math.ceil(w / cell_w)) + 1)
    gh = max(2, int(math.ceil(h / cell_h)) + 1)
    grid = [[rnd.random() for _ in range(gw)] for __ in range(gh)]

    out = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        gy = y / cell_h
        y0 = int(gy)
        ty = gy - y0
        y0 = clamp(y0, 0, gh - 2)
        y1 = y0 + 1
        for x in range(w):
            gx = x / cell_w
            x0 = int(gx)
            tx = gx - x0
            x0 = clamp(x0, 0, gw - 2)
            x1 = x0 + 1

            a = grid[y0][x0]
            b = grid[y0][x1]
            c = grid[y1][x0]
            d = grid[y1][x1]
            ab = a + (b - a) * tx
            cd = c + (d - c) * tx
            out[y][x] = ab + (cd - ab) * ty
    return out


def _blur_1d_h(arr, w, h):
    out = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        row = arr[y]
        for x in range(w):
            a = row[max(0, x - 1)]
            b = row[x]
            c = row[min(w - 1, x + 1)]
            out[y][x] = (a + b + c) / 3.0
    return out


def _blur_1d_v(arr, w, h):
    out = [[0.0 for _ in range(w)] for __ in range(h)]
    for y in range(h):
        y0 = max(0, y - 1)
        y1 = y
        y2 = min(h - 1, y + 1)
        for x in range(w):
            out[y][x] = (arr[y0][x] + arr[y1][x] + arr[y2][x]) / 3.0
    return out


def _connected_components(mask, w, h):
    visited = [[False for _ in range(w)] for __ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if visited[y][x] or (not mask[y][x]):
                continue
            q = [(x, y)]
            visited[y][x] = True
            cells = []
            while q:
                cx, cy = q.pop()
                cells.append((cx, cy))
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and (not visited[ny][nx]) and mask[ny][nx]:
                        visited[ny][nx] = True
                        q.append((nx, ny))
            comps.append(cells)
    comps.sort(key=len, reverse=True)
    return comps


def _dilate_points(points, w, h, radius=1):
    out = set()
    for (x, y) in points:
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    out.add((nx, ny))
    return out


def _mix_color(c1, c2, t):
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def _apply_fog(rgb, visibility):
    # visibility: 1.0 (fully visible) -> no fog
    #            0.8 (adjacent)      -> mild fog
    #            0.45 (unknown)      -> heavy fog
    if visibility >= 0.999:
        return rgb
    fog_strength = clamp((1.0 - visibility) * 0.95, 0.0, 0.78)
    return _mix_color(rgb, FOG_DARK, fog_strength)


def hash2(x, y, seed):
    return (x * 73856093 ^ y * 19349663 ^ seed * 83492791) & 0xFFFFFFFF


class MapWorld:
    def __init__(self, seed=7, world_size=(3200, 2200), cell_scale=8, render_scale=1):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.world_w, self.world_h = world_size
        self.cell_scale = cell_scale
        self.render_scale = max(1, int(render_scale))
        self.render_w = self.world_w * self.render_scale
        self.render_h = self.world_h * self.render_scale
        self.render_cell_scale = self.cell_scale * self.render_scale

        # low-res grid resolution
        self.gw = self.world_w // self.cell_scale
        self.gh = self.world_h // self.cell_scale

        self.surface = pygame.Surface((self.render_w, self.render_h)).convert()
        self.base_surface = pygame.Surface((self.render_w, self.render_h)).convert()
        self.border_surface = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA)

        self.land = [[False for _ in range(self.gw)] for __ in range(self.gh)]
        self.height = [[0.0 for _ in range(self.gw)] for __ in range(self.gh)]
        self.prov_id = [[-1 for _ in range(self.gw)] for __ in range(self.gh)]
        self.provinces = []
        self.realm_names = []
        self.realm_colors = []

        self.player_realm_id = 0
        self.visibility_by_prov = {}
        self.extra_visible_provs = set()
        self.render_version = 0
        self.tower_pid = -1
        self._realm_border_cache = {}
        self._realm_border_points = None
        self.fog_surface = None
        self._cached_adj = None

        # UI-ish textures / overlay noise
        self.paper_tile = make_noise_tile((64, 64), (24, 24, 24), variance=10, alpha=255, seed=seed + 555)
        self._terrain_source_tiles = self._load_terrain_source_tiles()
        self._biome_tile_samples = self._load_biome_tile_samples()
        self._biome_render_tiles = self._load_biome_render_tiles()

        self._generate()

    def rebuild_render_assets(self):
        self.surface = pygame.Surface((self.render_w, self.render_h)).convert()
        self.base_surface = pygame.Surface((self.render_w, self.render_h)).convert()
        self.border_surface = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA)
        self._terrain_source_tiles = self._load_terrain_source_tiles()
        self._biome_tile_samples = self._load_biome_tile_samples()
        self._biome_render_tiles = self._load_biome_render_tiles()
        self._realm_border_cache = {}
        self._realm_border_points = None
        self._render_base()
        self._render_borders_and_coast()
        self._render_labels_and_markers()

    def _assign_terrain_per_province(self):
        """Assign deterministic terrain per province so each province gets a matching tile background."""
        if not self.provinces:
            return

        prov_n = len(self.provinces)
        avg_height = [0.0 for _ in range(prov_n)]
        coastal_cells = [0 for _ in range(prov_n)]
        climate = _value_noise_2d(self.gw, self.gh, cell_w=18, cell_h=18, seed=self.seed + 401)
        moisture = _value_noise_2d(self.gw, self.gh, cell_w=14, cell_h=14, seed=self.seed + 707)

        for y in range(self.gh):
            for x in range(self.gw):
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue

                avg_height[pid] += self.height[y][x]

                touches_water = (
                    x == 0
                    or y == 0
                    or x == self.gw - 1
                    or y == self.gh - 1
                    or not self.land[y][x - 1]
                    or not self.land[y][x + 1]
                    or not self.land[y - 1][x]
                    or not self.land[y + 1][x]
                )
                if touches_water:
                    coastal_cells[pid] += 1

        for prov in self.provinces:
            mean_height = avg_height[prov.id] / max(1, prov.cell_count)
            gx = int(clamp(prov.center.x / self.cell_scale, 0, self.gw - 1))
            gy = int(clamp(prov.center.y / self.cell_scale, 0, self.gh - 1))
            latitude = abs(((gy + 0.5) / max(1, self.gh)) - 0.5) * 2.0
            coast_ratio = coastal_cells[prov.id] / max(1, prov.cell_count)
            population_score = clamp((prov.population - 300) / 600.0, 0.0, 1.0)
            coldness = clamp(
                0.14
                + latitude * 0.88
                + max(0.0, mean_height - 0.74) * 1.55
                + (0.5 - climate[gy][gx]) * 0.30,
                0.0,
                1.0,
            )
            wetness = clamp(
                moisture[gy][gx] * 0.72
                + coast_ratio * 1.10
                + max(0.0, 0.78 - mean_height) * 0.18,
                0.0,
                1.0,
            )
            roll = random.Random(self.seed * 2003 + prov.id * 97 + 17).random()

            terrain = DEFAULT_TERRAIN
            if mean_height >= 0.83 or (mean_height >= 0.78 and coldness >= 0.48):
                terrain = "mountain"
            elif coldness >= 0.56:
                terrain = "cold_bog" if wetness >= 0.52 and roll < 0.55 else "tundra"
            elif wetness >= 0.52 and coldness >= 0.42:
                terrain = "cold_bog"
            elif prov.is_capital and mean_height < 0.82 and coldness < 0.72:
                terrain = "village"
            elif (
                population_score >= 0.70
                and mean_height < 0.80
                and coldness < 0.68
                and wetness < 0.78
                and roll < 0.58
            ):
                terrain = "village"
            elif wetness <= 0.38 and coldness < 0.70:
                terrain = "plains"
            elif coast_ratio >= 0.22 and population_score >= 0.48 and coldness < 0.68 and roll < 0.35:
                terrain = "village"
            elif wetness < 0.50 and coldness < 0.72 and roll > 0.70:
                terrain = "plains"

            prov.set_terrain(terrain)

    def _assign_biomes_per_province(self):
        self._assign_terrain_per_province()

    def _load_biome_tile_samples(self, tile_size=None):
        samples = {}
        if tile_size is None:
            tile_size = max(96, int(self.cell_scale * 32))
        tile_size = max(24, int(tile_size))
        for biome_key in BIOME_DEFS:
            path = get_terrain_tile_path(biome_key)
            if not path:
                continue
            try:
                src = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue

            tile = pygame.transform.smoothscale(src, (tile_size, tile_size))
            resolved = pygame.Surface((tile_size, tile_size)).convert()
            resolved.fill(get_terrain_color(biome_key))
            resolved.blit(tile, (0, 0))

            pixels = []
            for y in range(tile_size):
                row = []
                for x in range(tile_size):
                    row.append(resolved.get_at((x, y))[:3])
                pixels.append(tuple(row))
            samples[biome_key] = {"size": tile_size, "pixels": tuple(pixels)}
        return samples

    def _load_terrain_source_tiles(self):
        tiles = {}
        for terrain_key in BIOME_DEFS:
            path = get_terrain_tile_path(terrain_key)
            if not path:
                continue
            try:
                src = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue

            resolved = pygame.Surface(src.get_size(), pygame.SRCALPHA)
            resolved.fill((*get_terrain_color(terrain_key), 255))
            resolved.blit(src, (0, 0))
            tiles[terrain_key] = resolved
        return tiles

    def _sample_biome_tile(self, biome_key, x, y, pid):
        biome_key = normalize_terrain_key(biome_key) or DEFAULT_TERRAIN
        sample = self._biome_tile_samples.get(biome_key)
        if sample is None:
            return get_terrain_color(biome_key)

        size = sample["size"]
        # Sample in world-space so higher-resolution tile detail survives the low-res bake.
        tx = (x * self.cell_scale + pid * 17) % size
        ty = (y * self.cell_scale + pid * 29) % size
        return sample["pixels"][ty][tx]

    def _load_biome_render_tiles(self, tile_size=None):
        tiles = {}
        if tile_size is None:
            tile_size = max(128, int(self.cell_scale * 32))
        tile_size = max(96, int(tile_size))
        for biome_key in BIOME_DEFS:
            path = get_terrain_tile_path(biome_key)
            if not path:
                continue
            try:
                src = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue
            scaled = pygame.transform.smoothscale(src, (tile_size, tile_size))
            # Flatten alpha: composite onto opaque biome-color background so transparent
            # regions in the PNG don't produce invisible holes when tile-filled.
            # Use convert_alpha() so blitting onto SRCALPHA terrain_layer sets alpha=255.
            resolved = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
            resolved.fill((*get_terrain_color(biome_key), 255))
            resolved.blit(scaled, (0, 0))
            tiles[biome_key] = resolved
        return tiles

    @staticmethod
    def _biome_detail_alpha(visibility):
        if visibility >= 0.999:
            return 204
        if visibility >= 0.78:
            return 148
        return 72

    def _build_hd_biome_detail_overlay(self):
        if not self._biome_render_tiles:
            return None

        low_masks = {
            biome_key: pygame.Surface((self.gw, self.gh), pygame.SRCALPHA).convert_alpha()
            for biome_key in self._biome_render_tiles
        }
        for mask in low_masks.values():
            mask.lock()

        for y in range(self.gh):
            for x in range(self.gw):
                if not self.land[y][x]:
                    continue
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue
                prov = self.provinces[pid]
                biome_key = normalize_terrain_key(getattr(prov, "terrain", prov.biome))
                mask = low_masks.get(biome_key)
                if mask is None:
                    continue
                alpha = self._biome_detail_alpha(self.visibility_by_prov.get(pid, 0.45))
                mask.set_at((x, y), (255, 255, 255, alpha))

        for mask in low_masks.values():
            mask.unlock()

        detail = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA).convert_alpha()
        for biome_key, low_mask in low_masks.items():
            if low_mask.get_bounding_rect().w <= 0 or low_mask.get_bounding_rect().h <= 0:
                continue
            mask = pygame.transform.smoothscale(low_mask, (self.render_w, self.render_h)).convert_alpha()
            tiled = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA).convert_alpha()
            tile_fill(tiled, tiled.get_rect(), self._biome_render_tiles[biome_key])
            tiled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            detail.blit(tiled, (0, 0))
        return detail

    def _seed_starting_buildings(self):
        if not self.provinces:
            return

        rnd = random.Random(self.seed * 31337 + 123)
        for prov in self.provinces:
            if prov.buildings.count(None) <= 0:
                continue

            chance = 0.18

            if rnd.random() < chance:
                prov.add_building("farm")

        # Ensure each realm starts with a minimum number of farms for a stronger early food base.
        realm_farms = {rid: 0 for rid in range(len(self.realm_names))}
        for prov in self.provinces:
            realm_farms[prov.realm_id] += sum(1 for b in prov.buildings if get_building_id(b) == "farm")

        for rid in range(len(self.realm_names)):
            required = max(1, (self.realm_sizes[rid] + 1) // 2)
            if realm_farms.get(rid, 0) >= required:
                continue
            candidates = [
                p
                for p in self.provinces
                if p.realm_id == rid
                and p.buildings.count(None) > 0
                and not any(get_building_id(b) == "farm" for b in p.buildings)
            ]
            rnd.shuffle(candidates)
            while realm_farms[rid] < required and candidates:
                candidates.pop().add_building("farm")
                realm_farms[rid] += 1

    def _generate_realm_rulers(self):
        self.realm_rulers = [None] * len(self.realm_names)

        for rid in range(len(self.realm_names)):
            cap_pid = self.realm_capitals[rid]
            cap_prov = self.provinces[cap_pid]

            culture = cap_prov.culture
            faith = cap_prov.faith

            rr = random.Random(self.seed * 7777 + rid * 131)
            ruler = generate_ruler(
                rr,
                realm_name=self.realm_names[rid],
                realm_size=self.realm_sizes[rid],
                culture=culture,
                faith=faith,
            )
            self.realm_rulers[rid] = ruler

    def _assign_tower_of_heaven(self):
        if not self.provinces:
            self.tower_pid = -1
            return

        # Testing: place near player by picking a known province if it exists.
        for p in self.provinces:
            if p.name.strip().lower() == "bjornivik":
                self.tower_pid = p.id
                p.landmark = "Tower of Heaven"
                return

        cap_pid = getattr(self, "player_capital_pid", -1)
        if 0 <= cap_pid < len(self.provinces):
            cap_center = self.provinces[cap_pid].center
        else:
            cap_center = pygame.Vector2(self.world_w / 2, self.world_h / 2)

        candidates = [p for p in self.provinces if p.cell_count > 260 and p.id != cap_pid]
        if not candidates:
            candidates = [p for p in self.provinces if p.id != cap_pid] or self.provinces[:]

        candidates.sort(
            key=lambda p: (p.center.x - cap_center.x) ** 2 + (p.center.y - cap_center.y) ** 2,
            reverse=True,
        )
        top_n = max(1, len(candidates) // 3)
        choice = self.rnd.choice(candidates[:top_n])

        self.tower_pid = choice.id
        choice.landmark = "Tower of Heaven"

    def _name(self):
        a = ["Skal", "Hrafn", "Eir", "Fjall", "Vik", "Bjorn", "Ulf", "Sigr", "Thor", "As", "Hald", "Rim", "Storm", "Frost", "Var"]
        b = ["a", "e", "i", "o", "u", "y", "ei", "au"]
        c = ["vik", "heim", "fjord", "gard", "holt", "ness", "mark", "borg", "dal", "lund", "skar", "holm", "fell"]
        return self.rnd.choice(a) + self.rnd.choice(b) + self.rnd.choice(c)

    def _generate_continent_height(self):
        w, h = self.gw, self.gh
        cx, cy = w * 0.52, h * 0.52

        # Value noise layers
        n1 = _value_noise_2d(w, h, cell_w=26, cell_h=26, seed=self.seed + 10)
        n2 = _value_noise_2d(w, h, cell_w=12, cell_h=12, seed=self.seed + 20)

        # Main continent blobs
        blobs = []
        blobs.append((cx, cy, min(w, h) * 0.34, 1.00))
        for _ in range(7):
            bx = self.rnd.uniform(w * 0.18, w * 0.82)
            by = self.rnd.uniform(h * 0.20, h * 0.80)
            br = self.rnd.uniform(min(w, h) * 0.11, min(w, h) * 0.20)
            ba = self.rnd.uniform(0.45, 0.95)
            blobs.append((bx, by, br, ba))

        # Smaller islands
        islands = []
        for _ in range(10):
            bx = self.rnd.uniform(w * 0.12, w * 0.88)
            by = self.rnd.uniform(h * 0.12, h * 0.88)
            br = self.rnd.uniform(min(w, h) * 0.04, min(w, h) * 0.07)
            ba = self.rnd.uniform(0.25, 0.55)
            islands.append((bx, by, br, ba))

        for y in range(h):
            for x in range(w):
                # radial falloff (forces water edges)
                dx = (x - cx) / (w * 0.56)
                dy = (y - cy) / (h * 0.56)
                radial = 1.0 - math.sqrt(dx * dx + dy * dy)
                radial = clamp(radial, -0.8, 1.0)

                v = radial * 0.78
                # add blobs (gaussian-ish)
                for (bx, by, br, ba) in blobs:
                    d2 = (x - bx) ** 2 + (y - by) ** 2
                    v += ba * math.exp(-d2 / (2.0 * br * br))
                for (bx, by, br, ba) in islands:
                    d2 = (x - bx) ** 2 + (y - by) ** 2
                    v += ba * math.exp(-d2 / (2.0 * br * br))

                # noise
                v += (n1[y][x] - 0.5) * 0.40
                v += (n2[y][x] - 0.5) * 0.22

                self.height[y][x] = v

        # Smooth for organic coastline
        for _ in range(2):
            self.height = _blur_1d_v(_blur_1d_h(self.height, w, h), w, h)

        # Normalize into ~0..1-ish range
        lo = min(min(row) for row in self.height)
        hi = max(max(row) for row in self.height)
        span = max(1e-6, hi - lo)
        for y in range(h):
            for x in range(w):
                self.height[y][x] = (self.height[y][x] - lo) / span

    def _build_land_mask(self):
        w, h = self.gw, self.gh
        # threshold tuned to produce a dominant continent
        threshold = 0.65
        raw = [[self.height[y][x] > threshold for x in range(w)] for y in range(h)]
        comps = _connected_components(raw, w, h)
        if not comps:
            for y in range(h):
                for x in range(w):
                    self.land[y][x] = False
            return

        main = comps[0]

        # keep main continent + a few islands big enough
        keep = set(main)
        for comp in comps[1:]:
            if len(comp) >= 70:  # sizable island
                keep.update(comp)

        for y in range(h):
            for x in range(w):
                self.land[y][x] = (x, y) in keep

    def _pick_province_seeds(self, land_cells, target_count):
        # Poisson-ish spacing in cell coordinates
        min_dist = max(7, int(math.sqrt((len(land_cells) / max(1, target_count))) * 0.75))
        seeds = []
        attempts = 0
        max_attempts = 90000

        while len(seeds) < target_count and attempts < max_attempts:
            attempts += 1
            x, y = land_cells[self.rnd.randrange(len(land_cells))]
            ok = True
            for sx, sy in seeds:
                dx = x - sx
                dy = y - sy
                if dx * dx + dy * dy < min_dist * min_dist:
                    ok = False
                    break
            if ok:
                seeds.append((x, y))

        # If spacing was too strict, fill remaining without spacing
        while len(seeds) < target_count:
            seeds.append(land_cells[self.rnd.randrange(len(land_cells))])
        return seeds

    def _assign_provinces_region_growth(self):
        w, h = self.gw, self.gh

        land_cells = [(x, y) for y in range(h) for x in range(w) if self.land[y][x]]
        land_n = len(land_cells)
        # province count scales with land area
        target = clamp(int(land_n // 1200), 40, 110)

        seeds = self._pick_province_seeds(land_cells, target)
        prov_count = len(seeds)

        # init
        for y in range(h):
            for x in range(w):
                self.prov_id[y][x] = -1

        q = []
        for pid, (sx, sy) in enumerate(seeds):
            self.prov_id[sy][sx] = pid
            q.append((sx, sy))

        # multi-source BFS (4-neigh) for contiguous provinces
        head = 0
        while head < len(q):
            x, y = q[head]
            head += 1
            pid = self.prov_id[y][x]
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h and self.land[ny][nx] and self.prov_id[ny][nx] == -1:
                    self.prov_id[ny][nx] = pid
                    q.append((nx, ny))

        # create province objects
        self.provinces = [Province(pid, self._name()) for pid in range(prov_count)]

        # collect cell lists + bounds + centers
        mins = [(10**9, 10**9) for _ in range(prov_count)]
        maxs = [(-10**9, -10**9) for _ in range(prov_count)]
        sumx = [0 for _ in range(prov_count)]
        sumy = [0 for _ in range(prov_count)]
        cnt = [0 for _ in range(prov_count)]

        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue
                mx, my = mins[pid]
                Mx, My = maxs[pid]
                mins[pid] = (min(mx, x), min(my, y))
                maxs[pid] = (max(Mx, x), max(My, y))
                sumx[pid] += x
                sumy[pid] += y
                cnt[pid] += 1

        # Merge tiny provinces for nicer shapes
        def build_border_contacts():
            contacts = [dict() for _ in range(prov_count)]
            for y in range(h):
                for x in range(w):
                    a = self.prov_id[y][x]
                    if a < 0:
                        continue
                    if x + 1 < w:
                        b = self.prov_id[y][x + 1]
                        if b >= 0 and b != a:
                            contacts[a][b] = contacts[a].get(b, 0) + 1
                            contacts[b][a] = contacts[b].get(a, 0) + 1
                    if y + 1 < h:
                        b = self.prov_id[y + 1][x]
                        if b >= 0 and b != a:
                            contacts[a][b] = contacts[a].get(b, 0) + 1
                            contacts[b][a] = contacts[b].get(a, 0) + 1
            return contacts

        contacts = build_border_contacts()
        small_threshold = 18
        merged_into = [-1 for _ in range(prov_count)]

        for pid in range(prov_count):
            if cnt[pid] >= small_threshold:
                continue
            if not contacts[pid]:
                continue
            # merge into strongest neighbor
            best = max(contacts[pid].items(), key=lambda kv: kv[1])[0]
            merged_into[pid] = best

        # apply merges (single pass; good enough for this aesthetic)
        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid >= 0 and merged_into[pid] != -1:
                    self.prov_id[y][x] = merged_into[pid]

        # remap province IDs to compact range after merges
        used = sorted({self.prov_id[y][x] for y in range(h) for x in range(w) if self.prov_id[y][x] >= 0})
        remap = {old: i for i, old in enumerate(used)}
        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid >= 0:
                    self.prov_id[y][x] = remap[pid]

        # rebuild province list + metrics
        prov_count2 = len(used)
        self.provinces = [Province(pid, self._name()) for pid in range(prov_count2)]
        mins = [(10**9, 10**9) for _ in range(prov_count2)]
        maxs = [(-10**9, -10**9) for _ in range(prov_count2)]
        sumx = [0 for _ in range(prov_count2)]
        sumy = [0 for _ in range(prov_count2)]
        cnt = [0 for _ in range(prov_count2)]

        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue
                mx, my = mins[pid]
                Mx, My = maxs[pid]
                mins[pid] = (min(mx, x), min(my, y))
                maxs[pid] = (max(Mx, x), max(My, y))
                sumx[pid] += x
                sumy[pid] += y
                cnt[pid] += 1

        for pid in range(prov_count2):
            if cnt[pid] <= 0:
                continue
            self.provinces[pid].cell_count = cnt[pid]
            mx, my = mins[pid]
            Mx, My = maxs[pid]
            self.provinces[pid].bounds_cells = pygame.Rect(mx, my, (Mx - mx + 1), (My - my + 1))
            cx = (sumx[pid] / cnt[pid] + 0.5) * self.cell_scale
            cy = (sumy[pid] / cnt[pid] + 0.5) * self.cell_scale
            self.provinces[pid].center = pygame.Vector2(cx, cy)
            pr = random.Random(self.seed * 131071 + pid * 17)
            self.provinces[pid].population = pr.randint(300, 900)

    def _build_province_adjacency(self):
        w, h = self.gw, self.gh
        adj = [set() for _ in range(len(self.provinces))]
        for y in range(h):
            for x in range(w):
                a = self.prov_id[y][x]
                if a < 0:
                    continue
                if x + 1 < w:
                    b = self.prov_id[y][x + 1]
                    if b >= 0 and b != a:
                        adj[a].add(b)
                        adj[b].add(a)
                if y + 1 < h:
                    b = self.prov_id[y + 1][x]
                    if b >= 0 and b != a:
                        adj[a].add(b)
                        adj[b].add(a)
        return adj

    def _assign_realms(self):
        prov_n = len(self.provinces)
        adj = self._build_province_adjacency()

        rnd = random.Random(self.seed + 1337)

        def pick_target_size():
            r = rnd.random()
            if r < 0.10:
                return 7
            if r < 0.30:
                return 6
            if r < 0.60:
                return 5
            if r < 0.85:
                return 4
            return 3

        realm_of = [-1] * prov_n
        realm_capitals = []
        realm_sizes = []

        order = list(range(prov_n))
        rnd.shuffle(order)

        rid = 0
        for seed_pid in order:
            if realm_of[seed_pid] != -1:
                continue

            target = pick_target_size()

            realm_of[seed_pid] = rid
            members = [seed_pid]

            # Grow this tiny kingdom by adding adjacent unassigned provinces
            while len(members) < target:
                candidates = []
                for p in members:
                    for nb in adj[p]:
                        if realm_of[nb] == -1:
                            candidates.append(nb)

                if not candidates:
                    break

                nb = rnd.choice(candidates)
                realm_of[nb] = rid
                members.append(nb)

            realm_capitals.append(seed_pid)
            realm_sizes.append(len(members))
            rid += 1

        realm_n = rid

        # Generate MANY distinct-but-muted colors (deterministic)
        import colorsys

        # Spread hues evenly across the full wheel using golden-ratio steps so
        # neighbouring realm indices land on maximally-different hues.
        GOLDEN = 0.6180339887
        rr0 = random.Random(self.seed * 10007 + 555)
        base_h = rr0.random()  # random starting offset per seed

        self.realm_colors = []
        for i in range(realm_n):
            rr = random.Random(self.seed * 10007 + i * 97 + 555)

            h = (base_h + i * GOLDEN) % 1.0
            # Skip the yellow-green band (0.16-0.22) which looks muddy on maps
            if 0.16 <= h <= 0.22:
                h = (h + 0.08) % 1.0

            s = 0.55 + rr.random() * 0.20   # 0.55-0.75: vivid enough to pop
            v = 0.52 + rr.random() * 0.18   # 0.52-0.70: not too dark, not washed out

            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            self.realm_colors.append((int(r * 255), int(g * 255), int(b * 255)))

        self.realm_names = [f"Kingdom of {self._name()}" for _ in range(realm_n)]
        self.realm_capitals = realm_capitals[:]
        self.realm_sizes = realm_sizes[:]

        # Apply to provinces
        for pid, prov in enumerate(self.provinces):
            prov.realm_id = realm_of[pid]
            prov.is_capital = False

        # Player realm: realm containing province closest to map center
        cx, cy = self.world_w * 0.52, self.world_h * 0.52
        near = min(
            range(prov_n),
            key=lambda i: (self.provinces[i].center.x - cx) ** 2 + (self.provinces[i].center.y - cy) ** 2,
        )
        self.player_realm_id = realm_of[near]

        # Mark capitals (one per realm)
        for cap_pid in self.realm_capitals:
            if 0 <= cap_pid < prov_n:
                self.provinces[cap_pid].is_capital = True

        # Store player capital province id (handy for label logic)
        if 0 <= self.player_realm_id < len(self.realm_capitals):
            self.player_capital_pid = self.realm_capitals[self.player_realm_id]
        else:
            self.player_capital_pid = near

    def _compute_fog_of_war(self):
        if not self.provinces:
            self.visibility_by_prov = {}
            return

        # Cache adjacency — province topology never changes during a session.
        if self._cached_adj is None:
            self._cached_adj = self._build_province_adjacency()
        adj = self._cached_adj

        player_rid = self.player_realm_id
        extra = getattr(self, "extra_visible_provs", set())

        # Player-owned provinces
        player_provs = {p.id for p in self.provinces if p.realm_id == player_rid}

        # Visible = player territory + every province that directly borders it + army vision
        visible = set(player_provs)
        for pid in player_provs:
            if pid < len(adj):
                visible.update(adj[pid])
        visible.update(extra)
        for pid in list(extra):
            if pid < len(adj):
                visible.update(adj[pid])

        vis = {}
        for p in self.provinces:
            vis[p.id] = 1.0 if p.id in visible else 0.0
        self.visibility_by_prov = vis

    def _build_fog_surface(self):
        """Build a fog-of-war overlay at world resolution.

        A low-res (cell-grid) alpha mask is smooth-scaled up to world pixel
        resolution so province edges produce natural gradient fog borders.
        """
        FOG_RGB = (8, 10, 20)
        w, h = self.gw, self.gh

        # One pixel per grid cell; start fully fogged.
        fog_low = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
        fog_low.fill((*FOG_RGB, 200))

        px = pygame.PixelArray(fog_low)
        for y in range(h):
            for x in range(w):
                pid = self.prov_id[y][x]
                if pid < 0:
                    continue  # water stays fogged
                vis = self.visibility_by_prov.get(pid, 0.0)
                if vis >= 0.999:
                    px[x, y] = (0, 0, 0, 0)   # fully transparent — visible province
        del px

        # Smooth-scale to world pixel resolution: the upscale blurs cell edges
        # into soft fog gradients without any extra blur pass.
        self.fog_surface = pygame.transform.smoothscale(
            fog_low, (self.world_w, self.world_h)
        ).convert_alpha()
        self.render_version += 1

    def _render_base(self):
        w, h = self.gw, self.gh
        cs = self.render_cell_scale
        sea_low = pygame.Surface((w, h)).convert()
        px = pygame.PixelArray(sea_low)
        ntex = _value_noise_2d(w, h, cell_w=7, cell_h=7, seed=self.seed + 999)

        for y in range(h):
            for x in range(w):
                if not self.land[y][x]:
                    d = clamp(1.0 - self.height[y][x], 0.0, 1.0)
                    sea = _mix_color(SEA_SHALLOWS, SEA_DEEP, d * 0.85)
                    dv = int((ntex[y][x] - 0.5) * 8)
                    px[x, y] = (
                        clamp(sea[0] + dv, 0, 255),
                        clamp(sea[1] + dv, 0, 255),
                        clamp(sea[2] + dv, 0, 255),
                    )
                    continue

                pid = self.prov_id[y][x]
                if pid < 0:
                    px[x, y] = SEA_DEEP
                    continue

                # Neutral land placeholder below the province terrain pass.
                px[x, y] = (32, 32, 32)

        del px

        self.base_surface = pygame.transform.smoothscale(sea_low, (self.render_w, self.render_h)).convert_alpha()

        for prov in self.provinces:
            biome_key = normalize_terrain_key(getattr(prov, "terrain", prov.biome)) or DEFAULT_TERRAIN
            bounds = prov.bounds_cells
            if bounds.w <= 0 or bounds.h <= 0:
                continue

            world_rect = pygame.Rect(bounds.x * cs, bounds.y * cs, bounds.w * cs, bounds.h * cs)
            if world_rect.w <= 0 or world_rect.h <= 0:
                continue

            render_tile = self._terrain_source_tiles.get(biome_key)
            if render_tile is None:
                render_tile = self._biome_render_tiles.get(biome_key)

            province_tile = pygame.Surface(world_rect.size, pygame.SRCALPHA)
            province_tile.fill((*get_terrain_color(biome_key), 255))

            if render_tile is not None:
                src_w, src_h = render_tile.get_size()
                dst_w, dst_h = province_tile.get_size()
                scale = max(dst_w / max(src_w, 1), dst_h / max(src_h, 1))
                scaled_w = max(1, int(src_w * scale))
                scaled_h = max(1, int(src_h * scale))
                scaled_tile = pygame.transform.smoothscale(render_tile, (scaled_w, scaled_h))
                ox = (dst_w - scaled_w) // 2
                oy = (dst_h - scaled_h) // 2
                province_tile.blit(scaled_tile, (ox, oy))

            # Semi-transparent realm color overlay so provinces are easy to tell apart
            realm_rgb = self.realm_colors[prov.realm_id] if prov.realm_id < len(self.realm_colors) else (128, 128, 128)
            overlay = pygame.Surface(world_rect.size, pygame.SRCALPHA)
            overlay.fill((*realm_rgb, 72))
            province_tile.blit(overlay, (0, 0))

            for gy in range(bounds.h):
                py = bounds.y + gy
                row = self.prov_id[py]
                for gx in range(bounds.w):
                    px = bounds.x + gx
                    if row[px] != prov.id:
                        continue
                    wx = px * cs
                    wy = py * cs
                    src_x = gx * cs
                    src_y = gy * cs
                    self.base_surface.blit(province_tile, (wx, wy), (src_x, src_y, cs, cs))

        self.render_version += 1

    def _apply_biome_tile_overlay(self):
        """Blit HD terrain tiles at full world resolution onto base_surface.
        For each biome, a world-sized tiled surface is created so source and
        destination coordinates are identical — no wrap-around edge cases."""
        if not self._biome_render_tiles:
            return

        w, h = self.gw, self.gh
        cs = self.render_cell_scale

        # Group land cells by biome key (single pass over the grid).
        cells_by_biome = {}
        for gy in range(h):
            for gx in range(w):
                if not self.land[gy][gx]:
                    continue
                pid = self.prov_id[gy][gx]
                if pid < 0:
                    continue
                prov = self.provinces[pid]
                bk = normalize_terrain_key(getattr(prov, "terrain", prov.biome)) or DEFAULT_TERRAIN
                if bk not in cells_by_biome:
                    cells_by_biome[bk] = []
                cells_by_biome[bk].append((gx, gy))

        for bk, cells in cells_by_biome.items():
            render_tile = self._biome_render_tiles.get(bk)
            if render_tile is None:
                continue

            # Build a world-sized opaque surface tiled with this biome's texture.
            tile_surf = pygame.Surface((self.render_w, self.render_h)).convert()
            tile_surf.fill(get_terrain_color(bk))
            tile_fill(tile_surf, tile_surf.get_rect(), render_tile)

            # Copy each cell's cs×cs block from tile_surf into base_surface at the
            # same world coordinates — source rect == destination position, no wrapping.
            for gx, gy in cells:
                wx = gx * cs
                wy = gy * cs
                self.base_surface.blit(tile_surf, (wx, wy), (wx, wy, cs, cs))

    def _render_borders_and_coast(self):
        w, h = self.gw, self.gh

        thin_border = []
        realm_border = []
        coast = []
        realm_border_points = {}
        land = self.land
        prov_id = self.prov_id
        provinces = self.provinces

        # scan edges to build low-res border point sets
        for y in range(h):
            for x in range(w):
                if not land[y][x]:
                    continue
                a = prov_id[y][x]
                if a < 0:
                    continue

                # coastline
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        if not land[ny][nx]:
                            coast.append((x, y))
                            break

                # province borders / realm borders (only check right & down to avoid duplicates)
                a_realm = provinces[a].realm_id
                for nx, ny in ((x + 1, y), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and land[ny][nx]:
                        b = prov_id[ny][nx]
                        if b >= 0 and b != a:
                            thin_border.append((x, y))
                            b_realm = provinces[b].realm_id
                            if a_realm != b_realm:
                                realm_border.append((x, y))
                                realm_border_points.setdefault(a_realm, set()).add((x, y))
                                realm_border_points.setdefault(b_realm, set()).add((nx, ny))

        thin_set = set(thin_border)
        realm_set = set(realm_border)
        coast_set = set(coast)

        # Supersample border masks more aggressively as render_scale increases.
        upscale = max(4, self.render_scale * 2)
        w2, h2 = w * upscale, h * upscale

        def up_points(points):
            out = set()
            for (x, y) in points:
                ox, oy = x * upscale, y * upscale
                for dy in range(upscale):
                    for dx in range(upscale):
                        out.add((ox + dx, oy + dy))
            return out

        thin2 = up_points(thin_set)
        realm2 = up_points(realm_set)
        coast2 = up_points(coast_set)

        # dilate in the upscaled space for smoother thickness
        realm_thick2 = _dilate_points(realm2, w2, h2, radius=1)
        coast_thick2 = _dilate_points(coast2, w2, h2, radius=1)

        def make_mask(points, alpha=255):
            s = pygame.Surface((w2, h2), pygame.SRCALPHA)
            for (x, y) in points:
                s.set_at((x, y), (255, 255, 255, alpha))
            return s

        mask_thin = make_mask(thin2, alpha=190)
        mask_coast = make_mask(coast_thick2, alpha=150)

        # smooth scale masks to world resolution (anti-aliased look)
        ms_thin = pygame.transform.smoothscale(mask_thin, (self.render_w, self.render_h))
        ms_coast = pygame.transform.smoothscale(mask_coast, (self.render_w, self.render_h))

        self.border_surface = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA)

        # coastline foam (keep subtle)
        foam = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA)
        foam.fill((*COAST_FOAM, 255))
        foam.blit(ms_coast, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.border_surface.blit(foam, (0, 0))

        # Province borders: subtle grey ink
        thin_ink = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA)
        thin_ink.fill((*BORDER_INK, 255))
        thin_ink.blit(ms_thin, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Realm borders: each realm drawn in its own color.
        # Paint all realm border points at upscale resolution, smoothscale for AA.
        colored_borders = pygame.Surface((w2, h2), pygame.SRCALPHA)
        for rid, pts in realm_border_points.items():
            if rid >= len(self.realm_colors):
                continue
            rc = self.realm_colors[rid]
            for (x, y) in pts:
                ox, oy = x * upscale, y * upscale
                r = pygame.Rect(ox - 1, oy - 1, upscale + 2, upscale + 2)
                r.clamp_ip(pygame.Rect(0, 0, w2, h2))
                colored_borders.fill((*rc, 230), r)

        ms_realm_colored = pygame.transform.smoothscale(colored_borders, (self.render_w, self.render_h))

        self.border_surface.blit(ms_realm_colored, (0, 0))
        self.border_surface.blit(thin_ink, (0, 0))
        self._realm_border_points = realm_border_points

    def _build_realm_border_points(self, realm_id):
        w, h = self.gw, self.gh
        border = set()
        land = self.land
        prov_id = self.prov_id
        provinces = self.provinces
        for y in range(h):
            row_land = land[y]
            row_pid = prov_id[y]
            for x in range(w):
                if not row_land[x]:
                    continue
                a = row_pid[x]
                if a < 0:
                    continue

                # check right neighbor
                nx = x + 1
                if nx < w and row_land[nx]:
                    b = row_pid[nx]
                    if b >= 0 and b != a:
                        a_realm = provinces[a].realm_id
                        b_realm = provinces[b].realm_id
                        if a_realm == realm_id:
                            border.add((x, y))
                        if b_realm == realm_id:
                            border.add((nx, y))

                # check down neighbor
                ny = y + 1
                if ny < h and land[ny][x]:
                    b = prov_id[ny][x]
                    if b >= 0 and b != a:
                        a_realm = provinces[a].realm_id
                        b_realm = provinces[b].realm_id
                        if a_realm == realm_id:
                            border.add((x, y))
                        if b_realm == realm_id:
                            border.add((x, ny))
        return border

    def get_realm_border_surface(self, realm_id, color=WAR_BORDER_COLOR):
        if realm_id is None or realm_id < 0 or realm_id >= len(self.realm_names):
            return None
        cached = self._realm_border_cache.get(realm_id)
        if cached is not None:
            return cached
        border_points = None
        if isinstance(self._realm_border_points, dict):
            border_points = self._realm_border_points.get(realm_id)
        if border_points is None:
            border_points = self._build_realm_border_points(realm_id)
            if self._realm_border_points is None:
                self._realm_border_points = {}
            self._realm_border_points[realm_id] = border_points
        if not border_points:
            return None

        # Match the main border supersampling so war outlines stay equally smooth.
        upscale = max(4, self.render_scale * 2)
        w2, h2 = self.gw * upscale, self.gh * upscale

        def up_points(points):
            out = set()
            for (x, y) in points:
                ox, oy = x * upscale, y * upscale
                for dy in range(upscale):
                    for dx in range(upscale):
                        out.add((ox + dx, oy + dy))
            return out

        realm2 = up_points(border_points)
        realm_thick2 = _dilate_points(realm2, w2, h2, radius=1)

        mask = pygame.Surface((w2, h2), pygame.SRCALPHA)
        for (x, y) in realm_thick2:
            mask.set_at((x, y), (255, 255, 255, 235))

        ms_realm = pygame.transform.smoothscale(mask, (self.render_w, self.render_h))
        overlay = pygame.Surface((self.render_w, self.render_h), pygame.SRCALPHA)
        overlay.fill((*color, 255))
        overlay.blit(ms_realm, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self._realm_border_cache[realm_id] = overlay
        return overlay

    def _render_labels_and_markers(self):
        if self.base_surface is None:
            self._render_base()
        if self.border_surface is None:
            self._render_borders_and_coast()

        # Store draw items (rendered later in screen-space so no pixelation on zoom)
        self.capital_label_items = []
        self.minimal_label_items = []
        capitals = set(getattr(self, "realm_capitals", []))

        # Labels only for seen + border provinces (same fog rules as before)
        for prov in self.provinces:
            vis = self.visibility_by_prov.get(prov.id, 0.45)
            if vis < 0.78:
                continue

            # Capitals always get the big label (even if a bit smaller)
            if prov.id in capitals:
                self.capital_label_items.append(prov.id)
                continue

            # Non-capitals: only show minimal labels for larger provinces (reduce clutter)
            if prov.cell_count < 320:
                continue
            self.minimal_label_items.append(prov.id)

        # IMPORTANT: only bake terrain + borders (no labels)
        self.surface = self.base_surface.copy()
        self.surface.blit(self.border_surface, (0, 0))
        self.base_surface = None
        self.border_surface = None
        self.render_version += 1

    def _generate(self):
        self._generate_continent_height()
        self._build_land_mask()
        self._assign_provinces_region_growth()
        self._assign_realms()
        self._assign_tower_of_heaven()
        self._compute_fog_of_war()
        self._generate_realm_rulers()

        self._assign_terrain_per_province()
        self._seed_starting_buildings()

        self._render_base()
        self._render_borders_and_coast()
        self._render_labels_and_markers()
        self._build_fog_surface()

    def province_at_world(self, world_pos):
        x, y = int(world_pos[0]), int(world_pos[1])
        if x < 0 or y < 0 or x >= self.world_w or y >= self.world_h:
            return None
        gx = x // self.cell_scale
        gy = y // self.cell_scale
        if gx < 0 or gy < 0 or gx >= self.gw or gy >= self.gh:
            return None
        pid = self.prov_id[gy][gx]
        if pid < 0:
            return None
        return self.provinces[pid]

    def is_border_cell(self, gx, gy, pid):
        # for selection outline (fast local check)
        if pid < 0:
            return False
        for nx, ny in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)):
            if 0 <= nx < self.gw and 0 <= ny < self.gh:
                other = self.prov_id[ny][nx]
                if other != pid:
                    return True
            else:
                return True
        return False

    def total_population_for_realm(self, realm_id):
        return sum(p.population for p in self.provinces if p.realm_id == realm_id)

    def total_population(self):
        return sum(p.population for p in self.provinces)

    def adjust_population_for_realm(self, realm_id, rate):
        if rate == 0:
            return
        for p in self.provinces:
            if p.realm_id != realm_id:
                continue
            new_val = int(round(p.population * (1.0 + rate)))
            p.population = max(1, new_val)

    def count_buildings(self, realm_id=None, building_id=None):
        count = 0
        for p in self.provinces:
            if realm_id is not None and p.realm_id != realm_id:
                continue
            for b in getattr(p, "buildings", []):
                bid = get_building_id(b)
                if bid is None:
                    continue
                if building_id is None or bid == building_id:
                    count += 1
        return count
