# Post-hydrology baseline: 40 seeds, terrain metric v2 (2026-07-17)

40 worlds, seeds 1–40, 4000 ticks, defaults, after the material-world build
(hydrology, named geography, water-boosted contact, sea routes, waterside
yields). Raw data: `ensemble-40-hydrology-v2.json` (metric v2);
`ensemble-40-hydrology.json` is the same dynamics scored under the old flat
NMI threshold, kept for the record of why the metric changed.

## Headline

**31/40 worlds pass all criteria** — statistically identical to the
pre-hydrology baseline (30/40). Adding water as contact infrastructure did
not move the acceptance behavior: fusion stays contingent and reversible
(326/277 ensemble-wide), the seasonal-extinction tail stays ~12–17%, and
liberation stays rare-costly-possible.

## The metric change (v2), and why

Hydrology raised *raw* culture↔biome NMI (median 0.098 → 0.188; one world at
0.313) — but the rise is **worldgen geometry, not culture reading terrain**:
water constrains region shapes for every people equally, and the coast biome
hugs the sea by construction. Verified on the failing world: NMI was already
0.201 at tick 0, before any culture dynamics existed.

Metric v2 therefore scores the *culture-dynamics increment* over each world's
own tick-0 geometric baseline (`nmi_final − nmi(owner0, biome) ≤ 0.15`).
This is the affordance/determination distinction operationalized: geometry
may shape territories; culture must not become predictable from ecology
beyond what geometry imposes.

Result under v2: **culture adds a median of 0.041 NMI over geometry
(max 0.131) — zero terrain failures in 40 worlds.** The core claim holds
with water in the world.

## Remaining failure tail (unchanged)

- seasonal_vs_ratcheted: 7 worlds (5 with switching fully extinct) — same
  tail as pre-hydrology; still pointing at the ratchet/re-evaluation knobs
  (see `beta-sweep.md`).
- fusion_contingent: 2 worlds.
