# mapgen.py
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict

@dataclass
class ProvinceRaster:
    w: int
    h: int
    # province_id per pixel as a flat list (len = w*h)
    ids: List[int]
    # province centers in raster coords
    centers: Dict[int, Tuple[int, int]]

def _idx(x: int, y: int, w: int) -> int:
    return y * w + x

def generate_province_raster(seed: int, w: int, h: int, province_count: int, relax_steps: int = 1) -> ProvinceRaster:
    """
    Creates organic provinces:
    - scatter sites
    - assign each pixel to nearest site (Voronoi-like)
    - optional Lloyd relaxation to smooth shapes
    """
    rng = random.Random(seed)

    sites = []
    for i in range(province_count):
        sx = rng.randrange(0, w)
        sy = rng.randrange(0, h)
        sites.append((sx, sy))

    def assign(sites_local):
        ids = [0] * (w * h)
        centers = {}
        for i, (sx, sy) in enumerate(sites_local):
            centers[i] = (sx, sy)

        for y in range(h):
            for x in range(w):
                best_i = 0
                best_d = 10**18
                for i, (sx, sy) in enumerate(sites_local):
                    dx = x - sx
                    dy = y - sy
                    d = dx*dx + dy*dy
                    if d < best_d:
                        best_d = d
                        best_i = i
                ids[_idx(x, y, w)] = best_i
        return ids

    # Relaxation: recompute centroid of each region and move sites there
    for _ in range(relax_steps):
        ids = assign(sites)

        sums = [(0,0,0) for _ in range(province_count)]  # sx, sy, n
        for y in range(h):
            for x in range(w):
                pid = ids[_idx(x, y, w)]
                sx, sy, n = sums[pid]
                sums[pid] = (sx + x, sy + y, n + 1)

        new_sites = []
        for i, (sx, sy) in enumerate(sites):
            ax, ay, n = sums[i]
            if n > 0:
                new_sites.append((ax // n, ay // n))
            else:
                new_sites.append((sx, sy))
        sites = new_sites

    ids = assign(sites)
    centers = {i: sites[i] for i in range(province_count)}
    return ProvinceRaster(w=w, h=h, ids=ids, centers=centers)

def province_adjacency(r: ProvinceRaster) -> Dict[int, set]:
    adj: Dict[int, set] = {}
    w, h = r.w, r.h
    ids = r.ids
    for y in range(h):
        for x in range(w):
            a = ids[_idx(x, y, w)]
            adj.setdefault(a, set())
            if x + 1 < w:
                b = ids[_idx(x+1, y, w)]
                if b != a:
                    adj[a].add(b)
                    adj.setdefault(b, set()).add(a)
            if y + 1 < h:
                b = ids[_idx(x, y+1, w)]
                if b != a:
                    adj[a].add(b)
                    adj.setdefault(b, set()).add(a)
    return adj
