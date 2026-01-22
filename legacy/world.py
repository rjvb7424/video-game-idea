# world.py
import random
from collections import deque
from domain import Character, Realm, County

def _neighbors(x, y, w, h):
    for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h:
            yield nx, ny

def _pick_biome(rng: random.Random, x: int, y: int, w: int, h: int) -> str:
    """
    Lightweight pseudo-noise biome assignment.
    You can replace with real noise later; this already looks decent.
    """
    # latitude-ish: colder north/south edges -> more mountains/hills
    edge = min(x, y, w-1-x, h-1-y)
    edge_factor = 1.0 - min(edge / max(1, min(w, h)/3), 1.0)

    r = rng.random()
    # water strips sometimes
    if r < 0.08:
        return "water"
    if edge_factor > 0.65 and r < 0.35:
        return "mountain"
    if r < 0.22:
        return "forest"
    if r < 0.30:
        return "hills"
    if r < 0.34:
        return "swamp"
    if r < 0.38:
        return "desert"
    return "plains"

def _generate_river(rng: random.Random, w: int, h: int):
    """
    A river as a path of grid points (polyline later).
    Starts near a mountain edge, flows toward opposite edge.
    """
    # Start near top edge
    x = rng.randrange(1, w-1)
    y = 0
    pts = [(x, y)]

    # Bias: generally go downward, with sideways meander
    for _ in range(w*h):
        if y >= h-1:
            break
        moves = []
        moves.append((x, y+1))  # down
        if rng.random() < 0.55:
            moves.append((max(0, x-1), y))
        if rng.random() < 0.55:
            moves.append((min(w-1, x+1), y))
        # pick one
        nx, ny = rng.choice(moves)
        x, y = nx, ny
        if pts[-1] != (x, y):
            pts.append((x, y))
    return pts

def _contiguous_realm_assignment(rng: random.Random, w: int, h: int, realms: list[Realm], player_realm: Realm):
    """
    Multi-source region growth. Each realm gets a single connected region.
    Prevents exclaves.
    """
    # Seed positions: player in center; others spread out
    seeds = []
    center = (w // 2, h // 2)
    seeds.append((center[0], center[1], player_realm))

    used = {center}
    # Other seeds
    for r in realms:
        if r is player_realm:
            continue
        for _ in range(200):
            sx = rng.randrange(w)
            sy = rng.randrange(h)
            if (sx, sy) not in used:
                used.add((sx, sy))
                seeds.append((sx, sy, r))
                break

    owner = [[None for _ in range(w)] for _ in range(h)]
    q = deque()
    for sx, sy, realm in seeds:
        owner[sy][sx] = realm
        q.append((sx, sy))

    # BFS expansion with a little randomness
    while q:
        x, y = q.popleft()
        realm = owner[y][x]
        neighs = list(_neighbors(x, y, w, h))
        rng.shuffle(neighs)
        for nx, ny in neighs:
            if owner[ny][nx] is None:
                owner[ny][nx] = realm
                q.append((nx, ny))

    return owner

def build_demo_world(seed: int = 123):
    rng = random.Random(seed)

    # Player + court
    ruler = Character("Julio", "Oliveira", 19, role="Ruler")
    regent = Character("Ana", "Regent", 45, role="Regent", loyalty=75, opinion_of_player=20, intrigue=14)
    spymaster = Character("Vasco", "Silva", 33, role="Spymaster", loyalty=40, opinion_of_player=-15, intrigue=22)
    steward = Character("Ines", "Coelho", 28, role="Steward", loyalty=68, opinion_of_player=10, intrigue=12)
    rival = Character("Duarte", "Mendes", 41, role="Rival Courtier", loyalty=30, opinion_of_player=-30, intrigue=18)

    characters = [ruler, regent, spymaster, steward, rival]
    player_realm = Realm("Kingdom of Westvale", ruler)

    # Neighbor realms
    neighbor_names = [
        "Duchy of Greyfen",
        "Kingdom of Asterhall",
        "Duchy of Thornmarch",
        "Realm of Highmere",
        "Duchy of Redwater",
        "Kingdom of Stonegate",
    ]
    neighbor_realms: list[Realm] = []
    for rname in neighbor_names:
        rr = Character(
            fname=rng.choice(["Edric", "Maeve", "Roland", "Selene", "Garrick", "Isolde"]),
            lname=rng.choice(["Thorne", "Ashford", "Blackwood", "Vale", "Wyvern", "Roth"]),
            age=rng.randint(22, 55),
            role="Ruler",
            loyalty=rng.randint(35, 85),
            opinion_of_player=rng.randint(-40, 25),
            intrigue=rng.randint(6, 24),
        )
        neighbor_realms.append(
            Realm(
                rname, rr,
                gold=80 + rng.random() * 120,
                prestige=rng.randint(30, 120),
                piety=rng.randint(10, 90),
                development=rng.randint(6, 18),
            )
        )

    # Grid size (logic) — draw will look irregular
    grid_w, grid_h = 12, 8

    # No exclaves: contiguous assignment
    all_realms = [player_realm] + neighbor_realms
    owner = _contiguous_realm_assignment(rng, grid_w, grid_h, all_realms, player_realm)

    # River (grid points)
    river_points = _generate_river(rng, grid_w, grid_h)

    counties: list[County] = []
    for y in range(grid_h):
        for x in range(grid_w):
            realm = owner[y][x]
            cname = f"{rng.choice(['Oak', 'River', 'Iron', 'Sun', 'Wolf', 'Mist'])}{rng.choice(['ford', 'watch', 'moor', 'hold', 'field', 'crest'])}"
            cid = f"c_{x}_{y}"

            biome = _pick_biome(rng, x, y, grid_w, grid_h)
            c = County(id=cid, name=cname, realm=realm, grid_x=x, grid_y=y, biome=biome, discovered=False)
            counties.append(c)

    # Capital clearer
    cx, cy = grid_w // 2, grid_h // 2
    for c in counties:
        if c.grid_x == cx and c.grid_y == cy:
            c.name = "Westvale (Capital)"
            c.id = "westvale_capital"
            c.realm = player_realm

    world = {
        "player_realm": player_realm,
        "characters": characters,
        "neighbor_realms": neighbor_realms,
        "counties": counties,
        "grid_size": (grid_w, grid_h),
        "center": (cx, cy),
        "river_points": river_points,
    }
    return world
