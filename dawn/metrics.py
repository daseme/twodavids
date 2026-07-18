"""Acceptance tests from the handover doc, §5 — run unattended, report honestly.

The thresholds marked PROVISIONAL are first guesses to be argued with, but the
*criteria* are commitments: if culture is predictable from ecology, the core
mechanic has failed, and this module must say so.
"""

from __future__ import annotations

import numpy as np

from .values import NOMADISM


def nmi_culture_terrain(world) -> float:
    """Normalized mutual information between culture and biome over claimed cells."""
    mask = world.owner >= 0
    if mask.sum() == 0:
        return 0.0
    c = world.owner[mask].ravel()
    b = world.biome[mask].ravel()
    cs, bs = np.unique(c), np.unique(b)
    joint = np.zeros((len(cs), len(bs)))
    ci = {v: i for i, v in enumerate(cs)}
    bi = {v: i for i, v in enumerate(bs)}
    for x, y in zip(c.tolist(), b.tolist()):
        joint[ci[x], bi[y]] += 1
    p = joint / joint.sum()
    px, py = p.sum(1), p.sum(0)
    nz = p > 0
    mi = float((p[nz] * np.log(p[nz] / np.outer(px, py)[nz])).sum())
    hx = float(-(px[px > 0] * np.log(px[px > 0])).sum())
    hy = float(-(py[py > 0] * np.log(py[py > 0])).sum())
    if min(hx, hy) <= 0:
        return 0.0
    return mi / min(hx, hy)


def evaluate(engine) -> dict:  # engine: dawn.engine.Engine (untyped to avoid a cycle)
    w, p = engine.world, engine.params
    records = engine.journal.records
    ticks = w.tick
    generations = max(1, ticks // p.generation_ticks)
    living = w.living()

    # 1. Culture borders decorrelate from terrain (PROVISIONAL threshold 0.30).
    nmi = nmi_culture_terrain(w)

    # 2. A culture area: shared trade/subsistence, inverted values.
    culture_areas = 0
    for key in sorted(w.edges):
        e = w.edges[key]
        A, B = w.cultures[e.a], w.cultures[e.b]
        if not (A.alive and B.alive) or e.exchange_until < 0:
            continue
        same_mode = np.sign(A.mean[NOMADISM]) == np.sign(B.mean[NOMADISM])
        joint_sal = (A.salience + B.salience) * np.abs(A.mean - B.mean)
        top = np.argsort(-joint_sal)[:3]
        inverted = sum(1 for k in top
                       if np.sign(A.mean[k]) != np.sign(B.mean[k])
                       and abs(A.mean[k]) > 0.15 and abs(B.mean[k]) > 0.15)
        if same_mode and inverted >= 2:
            culture_areas += 1

    # 3. Some lineages still switch seasonally; others have ratcheted.
    switching = sum(1 for c in living if c.is_switching())
    ratchets = [r for r in records if r.get("type") == "ratchet"]
    ratcheted_now = sum(1 for c in living if c.config().ratcheted)

    # 4. Fusion: never early, always a small minority, usually partial where
    # domination exists at all. (A world of mostly-free bands is not a failure
    # of this claim; a world of mostly-fused kingdoms is.)
    fusions = [r for r in records if r.get("type") == "fusion"]
    unfusions = [r for r in records if r.get("type") == "unfusion"]
    # 'Early' means an early fusion that then *lasts*: a brief conjunction that
    # comes apart again is the book's world, not its counterexample.
    early_fusion = any(
        r["tick"] < ticks * 0.25
        and not any(u["culture"] == r["culture"] and u["tick"] > r["tick"]
                    for u in unfusions)
        for r in fusions)
    held_counts = [int((c.domination > 0.55).sum()) for c in living]
    fused_share = sum(1 for h in held_counts if h == 3) / max(1, len(held_counts))
    holders = [h for h in held_counts if h >= 1]
    partial = (sum(1 for h in holders if h in (1, 2)) / len(holders)) if holders else 1.0

    # 5. Liberation: rare, costly, possible.
    libs = engine.liberations
    ever = len(w.cultures)  # every culture that ever lived shares the denominator
    lib_rate = len(libs) / max(1, ever) / generations

    # 6. Chronicle cadence: a legible entry at a steady rate.
    surviving = [e for e in engine.chronicle.entries if e.surviving]
    eras = max(1, ticks // p.era_ticks)
    entries_per_era = len(surviving) / eras

    # 7. Long-run sanity.
    pops = [c.pop for c in living]
    means_ok = all(np.isfinite(c.mean).all() and (np.abs(c.mean) <= 1.0).all()
                   for c in living)
    sane = (len(living) >= 2 and means_ok and pops
            and 200 < sum(pops) < 5e7)

    checks = {
        "terrain_decorrelation": {"pass": nmi < 0.30, "nmi": round(nmi, 3),
                                  "threshold": 0.30},
        "culture_area_inverted": {"pass": culture_areas >= 1, "count": culture_areas},
        "seasonal_vs_ratcheted": {"pass": switching >= 1 and len(ratchets) >= 1,
                                  "switching_now": switching,
                                  "ratchet_events": len(ratchets),
                                  "ratcheted_now": ratcheted_now},
        "fusion_contingent": {"pass": (not early_fusion) and partial >= 0.6
                                      and fused_share <= 0.2,
                              "fusions": len(fusions), "unfusions": len(unfusions),
                              "early_fusion": early_fusion,
                              "partial_among_holders": round(partial, 2),
                              "fused_share": round(fused_share, 2),
                              "held_counts": held_counts},
        "liberation_rare_possible": {"pass": len(libs) >= 1 and lib_rate <= 0.5,
                                     "events": len(libs),
                                     "rate_per_culture_gen": round(lib_rate, 4),
                                     "mechanisms": _mech_counts(libs)},
        "chronicle_cadence": {"pass": entries_per_era >= 1.0,
                              "surviving_entries": len(surviving),
                              "per_era": round(entries_per_era, 2)},
        "sanity_bounds": {"pass": bool(sane), "living": len(living),
                          "total_pop": round(sum(pops)) if pops else 0},
    }
    checks["all_pass"] = all(v["pass"] for k, v in checks.items() if isinstance(v, dict))
    return checks


def _mech_counts(libs: list[dict]) -> dict:
    out: dict[str, int] = {}
    for l in libs:
        out[l["mechanism"]] = out.get(l["mechanism"], 0) + 1
    return out
