"""Material causality: stochastic and pricing, never determining.

Environment and weather constrain the option set and price its members.
Positions on the caloric axes carry the heaviest coefficients; a culture can
in principle die of its values. Aleatory materialism: encounters (a run of
bad winters, a rich valley) take hold or don't — they never *select* a value.
"""

from __future__ import annotations

import numpy as np

from .culture import Culture
from .params import Params
from .values import ACCUMULATION, NOMADISM, RANK, COMMAND
from .world import World, yields_for


def extremity_multiplier(v: np.ndarray, p: Params) -> float:
    """Predator 1 on schismogenesis: extremity on caloric axes is priced quadratically."""
    m = 1.0
    for k in (NOMADISM, ACCUMULATION):
        over = max(0.0, abs(float(v[k])) - p.extremity_threshold)
        m *= max(0.2, 1.0 - p.kappa_extremity * over * over * 4.0)
    return m


def promise(sig: np.ndarray) -> float:
    """What the dominant configuration's ideology claims for everyone.

    Grander structures make grander claims — which is exactly what gives the
    contradiction accumulator something to accumulate.
    """
    return 0.55 + 0.25 * max(0.0, float(sig[COMMAND])) + 0.1 * max(0.0, float(sig[RANK]))


def material_tick(world: World, c: Culture, rng: np.random.Generator,
                  p: Params) -> dict:
    """Draw weather, realize calories, allocate across factions, update pop.

    Returns per-faction lived wellbeing plus the ideological promise, for the
    contradiction accumulator downstream.
    """
    mob_y, farm_y, n_cells = yields_for(world, c.cid)
    v = c.mean
    # Subsistence mix follows the nomadism axis (a chosen position, priced here).
    mob_share = float(np.clip(0.5 + 0.5 * v[NOMADISM], 0.0, 1.0))
    base = mob_share * mob_y + (1.0 - mob_share) * farm_y
    season_factor = {"spring": 0.9, "summer": 1.1, "autumn": 1.25, "winter": 0.75}[world.season]
    weather = float(np.clip(rng.normal(1.0, p.weather_sigma), 0.4, 1.6))
    crowding = min(1.0, (n_cells * 55.0) / max(c.pop, 1.0))
    cpc = base * season_factor * weather * crowding * extremity_multiplier(v, p)

    # Storage: accumulation smooths seasons for whoever holds the stores.
    store_bonus = 0.1 * max(0.0, float(v[ACCUMULATION])) if world.season == "winter" else 0.0

    pooling = c.structure(world.tick).pooling
    lived: dict[str, float] = {}
    for f in c.factions:
        rank_pos = float(np.dot(c.values_of(f), np.eye(len(v))[RANK]))
        if pooling == "share":
            share = 1.0
        elif pooling == "redistribute":
            share = 1.0 + 0.15 * rank_pos
        else:  # hoard: strong skew toward the ranked
            share = 1.0 + 0.55 * rank_pos
        f.lived = float(np.clip(cpc * share + store_bonus, 0.0, 1.5))
        lived[f.fid] = f.lived

    wellbeing = sum(f.lived * f.weight for f in c.factions)
    growth = float(np.clip(p.growth_rate * (wellbeing - 0.55), -p.growth_cap, p.growth_cap))
    c.pop = max(0.0, c.pop * (1.0 + growth))

    # Predator 2 on schismogenesis: internal dissent. Hunger drags practice on
    # the caloric axes back toward what feeds — not because the environment
    # selects values, but because hungry people argue with their feet and pots.
    hunger = max(0.0, 0.55 - wellbeing)
    if hunger > 0.0:
        pull = np.zeros_like(v)
        for k in (NOMADISM, ACCUMULATION):
            if abs(float(v[k])) > 0.5:
                pull[k] = -np.sign(v[k]) * 0.02 * hunger * (abs(float(v[k])) - 0.5)
        c.mean = np.clip(c.mean + pull, -1.0, 1.0)

    return {"lived": lived, "wellbeing": wellbeing, "cpc": cpc,
            "promise": promise(c.dominant_signature())}
