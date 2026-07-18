"""Contact and schismogenetic drift: cultures self-create through mutual differentiation.

Two Batesonian modes, two update rules:
- complementary: divergence into asymmetric pairs — push apart on the axis
- symmetrical: rivalrous escalation — both push toward the same pole

Repulsion acts only along *salient* axes (dimensions contact history has made
contested), and contact itself is what makes an axis salient. The predators:
salience decays without contact (3), and ritualized exchange damps the
repulsion coefficient (4). Success criterion for all of this: culture borders
must decorrelate from terrain.
"""

from __future__ import annotations

import numpy as np

from .culture import Culture, Edge
from .params import Params
from .values import N_AXES, RIVALROUS_AXES, soft_step
from .world import World


def schismogenesis_tick(world: World, rng: np.random.Generator,
                        p: Params) -> list[dict]:
    events: list[dict] = []
    cultures = world.cultures
    total_border = max(1, max((e.border for e in world.edges.values()), default=1))

    for key in sorted(world.edges):
        e = world.edges[key]
        A, B = cultures[e.a], cultures[e.b]
        if not (A.alive and B.alive):
            continue
        # Water concentrates contact: waterside borders carry more of it, and
        # sea routes are contact without any land border at all.
        if e.sea_route:
            w = e.openness(cultures) * p.sea_route_weight
        else:
            w = (e.openness(cultures) * min(1.0, e.border / (0.5 * total_border))
                 * (1.0 + p.water_contact_boost * e.water_frac))
        if w <= 0.01:
            continue

        diff = np.abs(A.mean - B.mean)
        # Interaction on differing dimensions makes them contested ground.
        for c in (A, B):
            c.salience = np.clip(c.salience + p.salience_up * w * diff, 0.0, 1.0)

        gamma = p.gamma_schismo
        if e.exchange_until >= world.tick:
            gamma *= (1.0 - p.rho_exchange)  # predator 4: the feast stands between rivals

        # Drift on the two most contested differing axes.
        contested = np.argsort(-(A.salience + B.salience) * diff)[:2]
        dA = np.zeros(N_AXES)
        dB = np.zeros(N_AXES)
        pop_ratio = max(A.pop, B.pop) / max(min(A.pop, B.pop), 1.0)
        for k in contested:
            k = int(k)
            s = float((A.salience[k] + B.salience[k]) / 2.0)
            if s < 0.05:
                continue
            same_side = np.sign(A.mean[k]) == np.sign(B.mean[k]) != 0
            if (k in RIVALROUS_AXES and pop_ratio < p.symmetric_pop_ratio and same_side):
                # Symmetrical: rivals racing up the same pole.
                direction = np.sign(A.mean[k] + B.mean[k]) or 1.0
                dA[k] += gamma * w * s * direction
                dB[k] += gamma * w * s * direction
                mode = "symmetrical"
            else:
                # Complementary: becoming what the other is not.
                sign = np.sign(A.mean[k] - B.mean[k])
                if sign == 0:
                    sign = 1.0 if A.cid < B.cid else -1.0
                dA[k] += gamma * w * s * sign
                dB[k] -= gamma * w * s * sign
                mode = "complementary"
            if rng.random() < 0.002:  # sampled, not exhaustive — journal hygiene
                events.append({"type": "schismo_drift", "a": A.cid, "b": B.cid,
                               "axis": k, "mode": mode, "salience": round(s, 3)})
        A.mean = soft_step(A.mean, dA)
        B.mean = soft_step(B.mean, dB)

    # Predator 3: what is not argued about is slowly forgotten as a difference.
    for c in world.living():
        c.salience *= (1.0 - p.lambda_salience)
    return events
