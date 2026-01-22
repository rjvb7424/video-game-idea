# world2.py
import random
from collections import deque
from typing import Dict, List
from domain import Character, Realm, County
from mapgen import ProvinceRaster, province_adjacency

TERRAINS = ["plains", "forest", "hills", "mountain"]

def build_world_from_raster(seed: int, raster: ProvinceRaster):
    rng = random.Random(seed)

    # Player realm
    player = Character("Julio", "Oliveira", 19, role="Ruler")
    player_realm = Realm("Kingdom of Westvale", player)

    # Neighbor realms
    names = ["Greyfen", "Asterhall", "Thornmarch", "Highmere", "Redwater", "Stonegate"]
    realms: List[Realm] = [player_realm]
    for nm in names:
        r = Character(
            fname=rng.choice(["Edric", "Maeve", "Roland", "Selene", "Garrick", "Isolde"]),
            lname=rng.choice(["Thorne", "Ashford", "Blackwood", "Vale", "Wyvern", "Roth"]),
            age=rng.randint(22, 55),
            role="Ruler",
            loyalty=rng.randint(35, 85),
            opinion_of_player=rng.randint(-40, 25),
            intrigue=rng.randint(6, 24),
        )
        realms.append(Realm(f"Kingdom of {nm}", r, gold=80+rng.random()*120, development=rng.randint(8, 18)))

    # Court characters (keep your originals)
    regent = Character("Ana", "Regent", 45, role="Regent", loyalty=75, opinion_of_player=20, intrigue=14)
    spymaster = Character("Vasco", "Silva", 33, role="Spymaster", loyalty=40, opinion_of_player=-15, intrigue=22)
    steward = Character("Ines", "Coelho", 28, role="Steward", loyalty=68, opinion_of_player=10, intrigue=12)
    rival = Character("Duarte", "Mendes", 41, role="Rival Courtier", loyalty=30, opinion_of_player=-30, intrigue=18)
    characters = [player, regent, spymaster, steward, rival]

    # Build counties list
    province_count = len(raster.centers)
    counties: List[County] = []
    for pid in range(province_count):
        cname = f"{rng.choice(['Oak', 'Iron', 'Wolf', 'Mist', 'Sun', 'River'])}{rng.choice(['ford','watch','moor','hold','field','crest'])}"
        terrain = rng.choice(TERRAINS)
        counties.append(County(id=pid, name=cname, realm=player_realm, terrain=terrain))  # temporary realm

    # Adjacency graph (for contiguity assignment)
    adj = province_adjacency(raster)

    # Pick “capital province” near center of raster
    cx, cy = raster.w // 2, raster.h // 2
    best = 0
    best_d = 10**18
    for pid, (px, py) in raster.centers.items():
        d = (px - cx)**2 + (py - cy)**2
        if d < best_d:
            best_d = d
            best = pid
    capital_pid = best
    counties[capital_pid].name = "Westvale (Capital)"
    counties[capital_pid].realm = player_realm

    # Multi-source BFS to assign contiguous blobs to realms (NO EXCLAVES)
    owner: Dict[int, Realm] = {}
    seeds = [(capital_pid, player_realm)]

    used = {capital_pid}
    # choose far-apart seeds for other realms
    for realm in realms:
        if realm is player_realm:
            continue
        # pick a province far from center and unused
        cand = None
        cand_d = -1
        for pid, (px, py) in raster.centers.items():
            if pid in used:
                continue
            d = (px - cx)**2 + (py - cy)**2
            if d > cand_d:
                cand_d = d
                cand = pid
        if cand is None:
            break
        used.add(cand)
        seeds.append((cand, realm))

    q = deque()
    for pid, realm in seeds:
        owner[pid] = realm
        q.append(pid)

    while q:
        pid = q.popleft()
        for nb in adj.get(pid, []):
            if nb not in owner:
                owner[nb] = owner[pid]
                q.append(nb)

    for c in counties:
        c.realm = owner.get(c.id, player_realm)

    world = {
        "player_realm": player_realm,
        "characters": characters,
        "counties": counties,
        "raster": raster,
        "capital_pid": capital_pid,
    }
    return world
