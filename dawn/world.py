"""Worldgen. The map constrains and prices; it never selects culture.

The world begins differentiated: initial value vectors are drawn with mutual
repulsion from the worldgen stream and are deliberately NOT a function of
biome. If culture ends up predictable from ecology anyway, the core mechanic
has failed (acceptance test 1) — that must be a *finding*, never an input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import names
from .culture import Culture, Edge, Faction, edge_key
from .params import Params
from .repertoire import (Repertoire, base_lexicon, config_signature,
                         primordial_configurations, primordial_stances)
from .rng import Streams
from .values import N_AXES

BIOMES = ["steppe", "forest", "river_valley", "coast", "mountain", "desert"]
# Caloric yield per biome per mode: mobile (forage/herd) vs farming.
YIELDS = {"steppe": (0.9, 0.35), "forest": (0.75, 0.5), "river_valley": (0.7, 1.1),
          "coast": (0.95, 0.6), "mountain": (0.5, 0.3), "desert": (0.35, 0.15)}


@dataclass
class Scar:
    tick: int
    kind: str        # refusal | abandonment | dead_route | ratchet_mark | liberation
    where: str
    note: str


@dataclass
class World:
    params: Params
    biome: np.ndarray                 # grid of biome indices (land cells)
    owner: np.ndarray                 # grid of culture ids (-1 unclaimed)
    cultures: dict[int, Culture]
    edges: dict[tuple[int, int], Edge]
    elevation: np.ndarray | None = None  # kept for rendering; never drives culture
    water: np.ndarray | None = None      # 0 land, 1 sea, 2 lake — uninhabitable
    water_adj: np.ndarray | None = None  # land cells touching water (incl. rivers)
    river: np.ndarray | None = None      # boolean river mask (land, ownable)
    river_segments: list = field(default_factory=list)   # [[x,y,x2,y2], ...]
    features: list = field(default_factory=list)         # named geography
    home_feature: dict = field(default_factory=dict)     # cid -> feature name
    scars: list[Scar] = field(default_factory=list)
    tick: int = 0

    @property
    def season(self) -> str:
        return ("spring", "summer", "autumn", "winter")[self.tick % 4]

    def living(self) -> list[Culture]:
        return [c for c in self.cultures.values() if c.alive]


def _smooth(a: np.ndarray, passes: int = 3) -> np.ndarray:
    for _ in range(passes):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0)
             + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5.0
    return a


def _classify(elev: np.ndarray, rain: np.ndarray) -> np.ndarray:
    b = np.full(elev.shape, BIOMES.index("steppe"))
    b[(elev > 0.72)] = BIOMES.index("mountain")
    b[(elev <= 0.72) & (rain > 0.62)] = BIOMES.index("forest")
    b[(elev < 0.35) & (rain > 0.45)] = BIOMES.index("river_valley")
    b[(elev < 0.22)] = BIOMES.index("coast")
    b[(rain < 0.28) & (elev <= 0.72)] = BIOMES.index("desert")
    return b


def _spread_seeds(rng: np.random.Generator, g: int, n: int,
                  habitable: np.ndarray) -> list[tuple[int, int]]:
    def draw() -> tuple[int, int]:
        while True:
            c = tuple(rng.integers(0, g, 2))
            if habitable[c]:
                return c
    pts = [draw()]
    while len(pts) < n:
        cand = [draw() for _ in range(24)]
        best = max(cand, key=lambda c: min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2
                                           for p in pts))
        pts.append(best)
    return [(int(x), int(y)) for x, y in pts]


# --- hydrology: the material world made vivid --------------------------------
# Water is where contact concentrates, and contact intensity drives the whole
# engine — the book's showcase schismogenesis cases are maritime. Water is
# affordance and infrastructure here, never a selector of values.

def _ridge(rng: np.random.Generator, g: int, elev: np.ndarray) -> np.ndarray:
    """A legible mountain spine: a gaussian ridge along a random line."""
    theta = rng.uniform(0, np.pi)
    cx, cy = rng.uniform(g * 0.3, g * 0.7, 2)
    xs, ys = np.meshgrid(np.arange(g), np.arange(g), indexing="ij")
    d = np.abs((xs - cx) * np.sin(theta) - (ys - cy) * np.cos(theta))
    return elev + 0.38 * np.exp(-(d / 5.5) ** 2)


def _sea_mask(rng: np.random.Generator, elev: np.ndarray) -> np.ndarray:
    """On a share of seeds, low ground connected to the map edge floods."""
    g = elev.shape[0]
    sea = np.zeros_like(elev, dtype=bool)
    if rng.random() > 0.6:
        return sea
    level = np.quantile(elev, rng.uniform(0.10, 0.22))
    from collections import deque
    q = deque()
    for i in range(g):
        for edge in ((i, 0), (i, g - 1), (0, i), (g - 1, i)):
            if elev[edge] < level and not sea[edge]:
                sea[edge] = True
                q.append(edge)
    while q:
        x, y = q.popleft()
        for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if 0 <= nx < g and 0 <= ny < g and not sea[nx, ny] and elev[nx, ny] < level:
                sea[nx, ny] = True
                q.append((nx, ny))
    return sea


def _flood_fill_depressions(elev: np.ndarray, sea: np.ndarray) -> np.ndarray:
    """Priority-flood: returns the filled surface; (filled - elev) > eps = lake."""
    import heapq
    g = elev.shape[0]
    filled = np.full_like(elev, np.inf)
    heap = []
    for x in range(g):
        for y in range(g):
            if sea[x, y] or x in (0, g - 1) or y in (0, g - 1):
                filled[x, y] = elev[x, y]
                heapq.heappush(heap, (elev[x, y], x, y))
    while heap:
        lvl, x, y = heapq.heappop(heap)
        if lvl > filled[x, y]:
            continue
        for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if 0 <= nx < g and 0 <= ny < g:
                cand = max(elev[nx, ny], lvl)
                if cand < filled[nx, ny]:
                    filled[nx, ny] = cand
                    heapq.heappush(heap, (cand, nx, ny))
    return filled


def _rivers(filled: np.ndarray, water: np.ndarray) -> tuple[np.ndarray, list, np.ndarray]:
    """D8 flow accumulation on the filled surface. Returns (river mask,
    segments for rendering, accumulation grid)."""
    g = filled.shape[0]
    dirs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    down = np.full((g, g, 2), -1, dtype=int)
    for x in range(g):
        for y in range(g):
            best, bh = None, filled[x, y]
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < g and 0 <= ny < g and filled[nx, ny] < bh:
                    bh = filled[nx, ny]
                    best = (nx, ny)
            if best:
                down[x, y] = best
    acc = np.ones((g, g))
    order = np.argsort(-filled.ravel())
    for idx in order:
        x, y = divmod(int(idx), g)
        dx, dy = down[x, y]
        if dx >= 0:
            acc[dx, dy] += acc[x, y]
    threshold = max(24.0, float(np.quantile(acc[water == 0], 0.985)))
    river = (acc >= threshold) & (water == 0)
    if not river.any():  # guarantee one major river
        land_acc = np.where(water == 0, acc, 0)
        top = np.argsort(-land_acc.ravel())[:30]
        for idx in top:
            river[divmod(int(idx), g)] = True
    segments = []
    for x, y in np.argwhere(river):
        dx, dy = down[x, y]
        if dx >= 0 and (river[dx, dy] or water[dx, dy] > 0):
            segments.append([int(x), int(y), int(dx), int(dy)])
    return river, segments, acc


def _repelled_vectors(rng: np.random.Generator, n: int) -> list[np.ndarray]:
    """Already plural, already arguing: sample means, then push them apart."""
    vs = [rng.uniform(-0.6, 0.6, N_AXES) for _ in range(n)]
    for _ in range(40):
        for i in range(n):
            push = np.zeros(N_AXES)
            for j in range(n):
                if i == j:
                    continue
                d = vs[i] - vs[j]
                dist = float(np.linalg.norm(d)) + 1e-6
                if dist < 1.2:
                    push += d / dist * (1.2 - dist) * 0.1
            vs[i] = np.clip(vs[i] + push, -0.85, 0.85)
    return vs


def _name_features(rng: np.random.Generator, world: "World", acc: np.ndarray) -> None:
    """Waters and mountains get names; the chronicle needs its geography."""
    from . import names
    g = world.params.grid

    def anchor(mask: np.ndarray) -> list[int]:
        pts = np.argwhere(mask)
        c = pts.mean(axis=0)
        return [int(c[0]), int(c[1])]

    sea = world.water == 1
    if sea.any():
        world.features.append({"kind": "sea", "name": names.water_name(rng, "sea"),
                               "at": anchor(sea)})
    # Lakes: label connected components, name the largest two.
    from collections import deque
    lake = world.water == 2
    seen = np.zeros_like(lake)
    comps = []
    for x, y in np.argwhere(lake):
        if seen[x, y]:
            continue
        comp, q = [], deque([(x, y)])
        seen[x, y] = True
        while q:
            cx, cy = q.popleft()
            comp.append((cx, cy))
            for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                if 0 <= nx < g and 0 <= ny < g and lake[nx, ny] and not seen[nx, ny]:
                    seen[nx, ny] = True
                    q.append((nx, ny))
        comps.append(comp)
    for comp in sorted(comps, key=len, reverse=True)[:2]:
        if len(comp) >= 3:
            m = np.zeros_like(lake)
            for c in comp:
                m[c] = True
            world.features.append({"kind": "lake", "name": names.water_name(rng, "lake"),
                                   "at": anchor(m)})
    if world.river is not None and world.river.any():
        # The main river is the highest-accumulation reach; a bay where it meets the sea.
        rx, ry = max(map(tuple, np.argwhere(world.river)), key=lambda c: acc[c])
        world.features.append({"kind": "river", "name": names.water_name(rng, "river"),
                               "at": [int(rx), int(ry)]})
        if sea.any():
            for x, y, x2, y2 in world.river_segments:
                if world.water[x2, y2] == 1:
                    world.features.append({"kind": "bay",
                                           "name": names.water_name(rng, "bay"),
                                           "at": [int(x2), int(y2)]})
                    break
    if world.elevation is not None and (world.elevation > 0.8).sum() >= 6:
        world.features.append({"kind": "range", "name": names.water_name(rng, "range"),
                               "at": anchor(world.elevation > 0.8)})


def generate(streams: Streams, p: Params) -> World:
    rng = streams.worldgen
    g = p.grid
    elev = _smooth(rng.random((g, g)), 4)
    elev = _ridge(rng, g, elev)
    rain = _smooth(rng.random((g, g)), 4)
    elev = (elev - elev.min()) / (elev.max() - elev.min() + 1e-9)
    rain = (rain - rain.min()) / (rain.max() - rain.min() + 1e-9)

    sea = _sea_mask(rng, elev)
    filled = _flood_fill_depressions(elev, sea)
    lakes = (filled - elev > 0.004) & ~sea
    water = np.zeros((g, g), dtype=int)
    water[sea] = 1
    water[lakes] = 2
    river, segments, acc = _rivers(filled, water)

    biome = _classify(elev, rain)
    # Land beside the sea is coast, whatever the rainfall said.
    shore = np.zeros_like(sea)
    shore[:-1] |= sea[1:]; shore[1:] |= sea[:-1]
    shore[:, :-1] |= sea[:, 1:]; shore[:, 1:] |= sea[:, :-1]
    biome[shore & (water == 0)] = BIOMES.index("coast")

    wet = (water > 0) | river
    water_adj = np.zeros_like(sea)
    water_adj[:-1] |= wet[1:]; water_adj[1:] |= wet[:-1]
    water_adj[:, :-1] |= wet[:, 1:]; water_adj[:, 1:] |= wet[:, :-1]
    water_adj &= (water == 0)

    habitable = water == 0
    seeds = _spread_seeds(rng, g, p.n_cultures, habitable)
    owner = np.full((g, g), -1, dtype=int)
    # BFS voronoi from seeds — regions are geography, not identity. Water is
    # uninhabited; rivers run through territory.
    from collections import deque
    q = deque()
    for cid, (x, y) in enumerate(seeds):
        owner[x, y] = cid
        q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < g and 0 <= ny < g and owner[nx, ny] == -1 and habitable[nx, ny]:
                owner[nx, ny] = owner[x, y]
                q.append((nx, ny))

    means = _repelled_vectors(rng, p.n_cultures)
    cultures: dict[int, Culture] = {}
    for cid in range(p.n_cultures):
        rep = Repertoire()
        for e in primordial_stances() + base_lexicon():
            rep.add(e)
        configs = primordial_configurations()
        for cfg in configs:
            rep.add(cfg)
        # Dominant = best fit to the culture's values — a choice it has already
        # made before history starts (no Eden, no origin story).
        dom = max(configs, key=lambda c: float(np.dot(config_signature(c), means[cid])))
        nf = int(rng.integers(2, 5))
        w = rng.dirichlet(np.ones(nf) * 3.0)
        factions = [Faction(fid=f"{cid}.{i}", name=names.word(rng, 2),
                            weight=float(w[i]),
                            offset=rng.normal(0, 0.15, N_AXES))
                    for i in range(nf)]
        cultures[cid] = Culture(
            cid=cid, name=names.culture_name(rng), mean=means[cid],
            salience=np.full(N_AXES, 0.1), factions=factions, repertoire=rep,
            pop=float(rng.uniform(800, 2200)), dominant_config=dom.eid)

    world = World(params=p, biome=biome, owner=owner, cultures=cultures, edges={},
                  elevation=elev, water=water, water_adj=water_adj, river=river,
                  river_segments=segments)
    _name_features(rng, world, acc)
    # Each people knows its nearest named water — the chronicle speaks of
    # "the peoples of the Vethmere".
    waters = [f for f in world.features if f["kind"] in ("sea", "lake", "river", "bay")]
    for cid in cultures:
        cells = np.argwhere(owner == cid)
        if len(cells) and waters:
            c = cells.mean(axis=0)
            near = min(waters, key=lambda f: (f["at"][0] - c[0]) ** 2
                                             + (f["at"][1] - c[1]) ** 2)
            if (f_d := (near["at"][0] - c[0]) ** 2 + (near["at"][1] - c[1]) ** 2) < (g * 0.45) ** 2:
                world.home_feature[cid] = near["name"]
    recompute_edges(world)
    # Contact history predates the record: axes where neighbors differ most
    # are already contested when the chronicle opens.
    for (a, b), e in world.edges.items():
        d = np.abs(cultures[a].mean - cultures[b].mean)
        for c in (cultures[a], cultures[b]):
            c.salience = np.clip(c.salience + 0.25 * (d > 0.6), 0.0, 1.0)
    return world


def recompute_edges(world: World) -> None:
    """Rebuild the contact graph from region adjacency, preserving edge history.

    Water is contact infrastructure: borders that run along water carry more
    contact (water_frac), and peoples who share a sea or lake shore meet even
    without a land border (sea routes).
    """
    old = world.edges
    counts: dict[tuple[int, int], int] = {}
    wet_counts: dict[tuple[int, int], int] = {}
    o = world.owner
    wa = world.water_adj if world.water_adj is not None \
        else np.zeros_like(o, dtype=bool)
    for (a, b), (aw, bw) in (((o[:-1, :], o[1:, :]), (wa[:-1, :], wa[1:, :])),
                             ((o[:, :-1], o[:, 1:]), (wa[:, :-1], wa[:, 1:]))):
        a, b = a.ravel(), b.ravel()
        wet = (aw | bw).ravel()
        mask = (a != b) & (a >= 0) & (b >= 0)
        for x, y, w in zip(a[mask].tolist(), b[mask].tolist(), wet[mask].tolist()):
            k = edge_key(x, y)
            counts[k] = counts.get(k, 0) + 1
            if w:
                wet_counts[k] = wet_counts.get(k, 0) + 1

    # Sea routes: cultures with enough shore on the same water body are in
    # contact across it even without a land border.
    p = world.params
    if world.water is not None and (world.water > 0).any():
        shores = _shores_by_body(world)
        for body in sorted(shores):
            holders = sorted(cid for cid, n in shores[body].items()
                             if n >= p.sea_route_min_shore)
            for i, a in enumerate(holders):
                for b in holders[i + 1:]:
                    k = edge_key(a, b)
                    if k not in counts:
                        counts[k] = 0
                        wet_counts[k] = 0

    edges: dict[tuple[int, int], Edge] = {}
    for k in sorted(counts):
        a, b = k
        if not (world.cultures[a].alive and world.cultures[b].alive):
            continue
        e = old.get(k, Edge(a=a, b=b))
        e.border = counts[k]
        e.sea_route = counts[k] == 0
        e.water_frac = (wet_counts.get(k, 0) / counts[k]) if counts[k] else 1.0
        edges[k] = e
    world.edges = edges


def _shores_by_body(world: World) -> dict[int, dict[int, int]]:
    """body id -> {cid: shore cell count} for seas and lakes."""
    from collections import deque
    g = world.params.grid
    w = world.water
    body = np.full((g, g), -1, dtype=int)
    nb = 0
    for x, y in np.argwhere(w > 0):
        if body[x, y] >= 0:
            continue
        q = deque([(x, y)])
        body[x, y] = nb
        while q:
            cx, cy = q.popleft()
            for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                if 0 <= nx < g and 0 <= ny < g and w[nx, ny] > 0 and body[nx, ny] < 0:
                    body[nx, ny] = nb
                    q.append((nx, ny))
        nb += 1
    shores: dict[int, dict[int, int]] = {}
    for x, y in np.argwhere(w > 0):
        for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
            if 0 <= nx < g and 0 <= ny < g and world.owner[nx, ny] >= 0:
                b = int(body[x, y])
                cid = int(world.owner[nx, ny])
                shores.setdefault(b, {})
                shores[b][cid] = shores[b].get(cid, 0) + 1
    return shores


def yields_for(world: World, cid: int) -> tuple[float, float, int]:
    """(mobile_yield, farm_yield, n_cells) over a culture's region."""
    mask = world.owner == cid
    n = int(mask.sum())
    if n == 0:
        return 0.0, 0.0, 0
    mob = farm = 0.0
    for bi, bname in enumerate(BIOMES):
        cnt = int((world.biome[mask] == bi).sum())
        mob += cnt * YIELDS[bname][0]
        farm += cnt * YIELDS[bname][1]
    if world.water_adj is not None:
        # Water is generous: fish and fowl for the mobile, silt for the settled.
        # An affordance with a price elsewhere — never a value selector.
        frac = float(world.water_adj[mask].mean())
        mob += 0.30 * frac
        farm += 0.20 * frac
    return mob / n, farm / n, n
