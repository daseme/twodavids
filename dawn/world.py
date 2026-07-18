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
    biome: np.ndarray                 # grid of biome indices
    owner: np.ndarray                 # grid of culture ids (-1 unclaimed)
    cultures: dict[int, Culture]
    edges: dict[tuple[int, int], Edge]
    elevation: np.ndarray | None = None  # kept for rendering; never drives culture
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


def _spread_seeds(rng: np.random.Generator, g: int, n: int) -> list[tuple[int, int]]:
    pts = [tuple(rng.integers(0, g, 2))]
    while len(pts) < n:
        cand = [tuple(rng.integers(0, g, 2)) for _ in range(24)]
        best = max(cand, key=lambda c: min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2
                                           for p in pts))
        pts.append(best)
    return [(int(x), int(y)) for x, y in pts]


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


def generate(streams: Streams, p: Params) -> World:
    rng = streams.worldgen
    g = p.grid
    elev = _smooth(rng.random((g, g)), 4)
    rain = _smooth(rng.random((g, g)), 4)
    elev = (elev - elev.min()) / (elev.max() - elev.min() + 1e-9)
    rain = (rain - rain.min()) / (rain.max() - rain.min() + 1e-9)
    biome = _classify(elev, rain)

    seeds = _spread_seeds(rng, g, p.n_cultures)
    owner = np.full((g, g), -1, dtype=int)
    # BFS voronoi from seeds — regions are geography, not identity.
    from collections import deque
    q = deque()
    for cid, (x, y) in enumerate(seeds):
        owner[x, y] = cid
        q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < g and 0 <= ny < g and owner[nx, ny] == -1:
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
                  elevation=elev)
    recompute_edges(world)
    # Contact history predates the record: axes where neighbors differ most
    # are already contested when the chronicle opens.
    for (a, b), e in world.edges.items():
        d = np.abs(cultures[a].mean - cultures[b].mean)
        for c in (cultures[a], cultures[b]):
            c.salience = np.clip(c.salience + 0.25 * (d > 0.6), 0.0, 1.0)
    return world


def recompute_edges(world: World) -> None:
    """Rebuild the contact graph from region adjacency, preserving edge history."""
    old = world.edges
    counts: dict[tuple[int, int], int] = {}
    o = world.owner
    for a, b in ((o[:-1, :], o[1:, :]), (o[:, :-1], o[:, 1:])):
        a, b = a.ravel(), b.ravel()
        mask = (a != b) & (a >= 0) & (b >= 0)
        for x, y in zip(a[mask].tolist(), b[mask].tolist()):
            k = edge_key(x, y)
            counts[k] = counts.get(k, 0) + 1
    edges: dict[tuple[int, int], Edge] = {}
    for k in sorted(counts):
        a, b = k
        if not (world.cultures[a].alive and world.cultures[b].alive):
            continue
        e = old.get(k, Edge(a=a, b=b))
        e.border = counts[k]
        edges[k] = e
    world.edges = edges


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
    return mob / n, farm / n, n
