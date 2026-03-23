import math
import random

import pygame

from core.math_utils import clamp, lerp
from core.surfaces import make_noise_tile, tile_fill
from systems.characters import generate_ruler
from systems.buildings import make_building, get_building_id
from world.biomes import BIOME_DEFS, DEFAULT_BIOME, get_biome_color, get_biome_tile_path, normalize_biome_key

# Map palette (subdued, CK1-ish)
SEA_DEEP = (10, 22, 40)
SEA_SHALLOWS = (18, 38, 64)
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
        self.biome = DEFAULT_BIOME
        self.biome_color = get_biome_color(self.biome)
        self.population = 0
        self.culture = "Nordfolken"
        self.faith = "Nordfolken Mythology"
        self.building_slots = 3
        self.buildings = [None for _ in range(self.building_slots)]

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
    def __init__(self, seed=7, world_size=(3200, 2200), cell_scale=8):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.world_w, self.world_h = world_size
        self.cell_scale = cell_scale

        # low-res grid resolution
        self.gw = self.world_w // self.cell_scale
        self.gh = self.world_h // self.cell_scale

        self.surface = pygame.Surface((self.world_w, self.world_h)).convert()
        self.base_surface = pygame.Surface((self.world_w, self.world_h)).convert()
        self.border_surface = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)

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

        # UI-ish textures / overlay noise
        self.paper_tile = make_noise_tile((64, 64), (24, 24, 24), variance=10, alpha=255, seed=seed + 555)
        self._biome_tile_samples = self._load_biome_tile_samples()

        self._generate()

    def _assign_biomes_per_province(self):
        """Assign a deterministic biome per province so terrain art varies across the map."""
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

            biome = DEFAULT_BIOME
            if mean_height >= 0.83 or (mean_height >= 0.78 and coldness >= 0.48):
                biome = "mountain"
            elif coldness >= 0.56:
                biome = "cold_bog" if wetness >= 0.52 and roll < 0.55 else "tundra"
            elif wetness >= 0.52 and coldness >= 0.42:
                biome = "cold_bog"
            elif prov.is_capital and mean_height < 0.82 and coldness < 0.72:
                biome = "village"
            elif (
                population_score >= 0.70
                and mean_height < 0.80
                and coldness < 0.68
                and wetness < 0.78
                and roll < 0.58
            ):
                biome = "village"
            elif wetness <= 0.38 and coldness < 0.70:
                biome = "plains"
            elif coast_ratio >= 0.22 and population_score >= 0.48 and coldness < 0.68 and roll < 0.35:
                biome = "village"
            elif wetness < 0.50 and coldness < 0.72 and roll > 0.70:
                biome = "plains"

            prov.biome = biome
            prov.biome_color = get_biome_color(biome)

    def _load_biome_tile_samples(self, tile_size=24):
        samples = {}
        tile_size = max(6, int(tile_size))
        for biome_key in BIOME_DEFS:
            path = get_biome_tile_path(biome_key)
            if not path:
                continue
            try:
                src = pygame.image.load(path).convert_alpha()
            except pygame.error:
                continue

            tile = pygame.transform.smoothscale(src, (tile_size, tile_size))
            resolved = pygame.Surface((tile_size, tile_size)).convert()
            resolved.fill(get_biome_color(biome_key))
            resolved.blit(tile, (0, 0))

            pixels = []
            for y in range(tile_size):
                row = []
                for x in range(tile_size):
                    row.append(resolved.get_at((x, y))[:3])
                pixels.append(tuple(row))
            samples[biome_key] = {"size": tile_size, "pixels": tuple(pixels)}
        return samples

    def _sample_biome_tile(self, biome_key, x, y, pid):
        biome_key = normalize_biome_key(biome_key) or DEFAULT_BIOME
        sample = self._biome_tile_samples.get(biome_key)
        if sample is None:
            return get_biome_color(biome_key)

        size = sample["size"]
        tx = (x + pid * 7) % size
        ty = (y + pid * 11) % size
        return sample["pixels"][ty][tx]

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

        # Nordfolken-style: all realms are "kingdom-blue" variants (CK3-ish),
        # still distinct via hue/sat/value jitter.
        base_blue_h = 0.60
        h_jitter = 0.05
        s_min, s_max = 0.25, 0.42
        v_min, v_max = 0.42, 0.62

        self.realm_colors = []
        for i in range(realm_n):
            rr = random.Random(self.seed * 10007 + i * 97 + 555)

            # keep hue within a blue band
            h = clamp(base_blue_h + (rr.random() - 0.5) * 2.0 * h_jitter, 0.0, 1.0)
            s = s_min + rr.random() * (s_max - s_min)
            v = v_min + rr.random() * (v_max - v_min)

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
        adj = self._build_province_adjacency()
        player_provs = {p.id for p in self.provinces if p.realm_id == self.player_realm_id}
        extra = set(getattr(self, "extra_visible_provs", set()))
        seen = set(player_provs) | extra
        border = set(seen)
        for pid in seen:
            for nb in adj[pid]:
                border.add(nb)

        # visibility factors
        self.visibility_by_prov = {}
        for p in self.provinces:
            if p.id in seen:
                self.visibility_by_prov[p.id] = 1.00
            elif p.id in border:
                self.visibility_by_prov[p.id] = 0.80
            else:
                self.visibility_by_prov[p.id] = 0.45

    def _render_base(self):
        w, h = self.gw, self.gh

        # low-res color buffer
        low = pygame.Surface((w, h)).convert()
        px = pygame.PixelArray(low)

        # Terrain texture overlay (grayscale multipliers)
        tex = pygame.Surface((w, h)).convert()
        tpx = pygame.PixelArray(tex)

        # extra tiny noise for texture variation
        ntex = _value_noise_2d(w, h, cell_w=7, cell_h=7, seed=self.seed + 999)

        for y in range(h):
            for x in range(w):
                if not self.land[y][x]:
                    # sea depth based on height below threshold
                    d = clamp(1.0 - self.height[y][x], 0.0, 1.0)
                    sea = _mix_color(SEA_SHALLOWS, SEA_DEEP, d * 0.85)
                    dv = int((ntex[y][x] - 0.5) * 8)
                    sea = (clamp(sea[0] + dv, 0, 255), clamp(sea[1] + dv, 0, 255), clamp(sea[2] + dv, 0, 255))
                    px[x, y] = sea
                    tpx[x, y] = (255, 255, 255)  # neutral multiplier for sea
                    continue
                pid = self.prov_id[y][x]
                if pid < 0:
                    px[x, y] = SEA_DEEP
                    tpx[x, y] = (255, 255, 255)
                    continue

                prov = self.provinces[pid]
                rid = prov.realm_id
                realm_col = self.realm_colors[rid]
                biome_key = normalize_biome_key(prov.biome) or DEFAULT_BIOME

                # --- Biome texture (multiplier) ---
                hval = hash2(x, y, self.seed)

                # default subtle grain
                darken = 2 + (hval % 4)

                if biome_key == "forest":
                    if (hval % 9) == 0:
                        darken = 16
                    else:
                        darken = 7 + (hval % 6)

                elif biome_key == "mountain":
                    if ((x + y + (hval % 5)) % 6) == 0:
                        darken = 18
                    else:
                        darken = 10 + (hval % 10)

                elif biome_key == "cold_bog":
                    darken = 8 + (hval % 7)

                elif biome_key == "tundra":
                    darken = 3 + (hval % 5)

                elif biome_key == "plains":
                    darken = 3 + (hval % 4)

                elif biome_key == "village":
                    darken = 2 + (hval % 3)

                # apply fog to texture strength too (so unknown land is less detailed)
                vis = self.visibility_by_prov.get(pid, 0.45)
                fog_scale = 0.55 if vis < 0.78 else 1.0
                darken = int(darken * fog_scale)

                mul = 255 - clamp(darken, 0, 80)
                tpx[x, y] = (mul, mul, mul)

                # Base fill: biome tile drives the province background with a light realm tint.
                tile_col = self._sample_biome_tile(biome_key, x, y, pid)
                col = _mix_color(tile_col, prov.biome_color, 0.14)
                col = _mix_color(col, realm_col, 0.16)

                # micro shading
                dv = int((ntex[y][x] - 0.5) * 6)
                col = (clamp(col[0] + dv, 0, 255), clamp(col[1] + dv, 0, 255), clamp(col[2] + dv, 0, 255))

                # fog of war
                vis = self.visibility_by_prov.get(pid, 0.45)
                col = _apply_fog(col, vis)
                px[x, y] = col

        del px
        del tpx

        # scale base color fill
        self.base_surface = pygame.transform.smoothscale(low, (self.world_w, self.world_h)).convert()

        # scale and apply texture (darkens base color to create biome detail)
        tex_big = pygame.transform.smoothscale(tex, (self.world_w, self.world_h)).convert()
        self.base_surface.blit(tex_big, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        veil = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        tile_fill(veil, veil.get_rect(), self.paper_tile)
        veil.fill((0, 0, 0, 22), special_flags=pygame.BLEND_RGBA_MULT)
        self.base_surface.blit(veil, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.render_version += 1

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

        # render border masks at 2x the low-res grid, then smoothscale to world
        upscale = 4
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
        many_realms = len(self.realm_colors) > 20
        mask_realm = make_mask(realm_thick2, alpha=110 if many_realms else 200)
        mask_coast = make_mask(coast_thick2, alpha=150)

        # smooth scale masks to world resolution (anti-aliased look)
        ms_thin = pygame.transform.smoothscale(mask_thin, (self.world_w, self.world_h))
        ms_realm = pygame.transform.smoothscale(mask_realm, (self.world_w, self.world_h))
        ms_coast = pygame.transform.smoothscale(mask_coast, (self.world_w, self.world_h))

        self.border_surface = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)

        # coastline foam (keep subtle)
        foam = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        foam.fill((*COAST_FOAM, 255))
        foam.blit(ms_coast, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self.border_surface.blit(foam, (0, 0))

        # province borders: subtle ink
        thick_ink = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        thick_ink.fill((*BORDER_INK_DARK, 255))

        thin_ink = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        thin_ink.fill((*BORDER_INK, 255))
        thin_ink.blit(ms_thin, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # realm borders: slightly stronger ink
        realm_ink = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        realm_ink.fill((*BORDER_REALM_INK, 255))
        realm_ink.blit(ms_realm, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self.border_surface.blit(realm_ink, (0, 0))
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

        # render border mask at 2x the low-res grid, then smoothscale to world
        upscale = 4
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

        ms_realm = pygame.transform.smoothscale(mask, (self.world_w, self.world_h))
        overlay = pygame.Surface((self.world_w, self.world_h), pygame.SRCALPHA)
        overlay.fill((*color, 255))
        overlay.blit(ms_realm, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self._realm_border_cache[realm_id] = overlay
        return overlay

    def _render_labels_and_markers(self):
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
        self.render_version += 1

    def _generate(self):
        self._generate_continent_height()
        self._build_land_mask()
        self._assign_provinces_region_growth()
        self._assign_realms()
        self._assign_tower_of_heaven()
        self._compute_fog_of_war()
        self._generate_realm_rulers()

        self._assign_biomes_per_province()
        self._seed_starting_buildings()

        self._render_base()
        self._render_borders_and_coast()
        self._render_labels_and_markers()

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
