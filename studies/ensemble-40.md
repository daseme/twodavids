# Ensemble study: 40 seeds at defaults (2026-07-17)

40 worlds, seeds 1–40, 4000 ticks (~50 generations), default `Params()`
(beta_ideology = 0.8). Raw per-world results: `ensemble-40.json`.
Reproduce: `dawn accept --seeds 40 --ticks 4000 --jobs 12 --json studies/ensemble-40.json`.

## Headline

**30/40 worlds pass all seven acceptance criteria.** This is the Phase-1
baseline against which any dynamics change — and eventually the Phase-3
promotion of the model's stances — must be compared.

## By criterion

| criterion | failures / 40 | notes |
|---|---|---|
| terrain decorrelation | 0 | median NMI 0.098, max 0.165 vs 0.30 ceiling — the core mechanic holds in every world |
| culture areas (inverted values) | 0 | |
| chronicle cadence | 0 | |
| sanity bounds | 0 | |
| liberation rare-costly-possible | 1 | one hot world at 0.548/culture-gen; median 0.084 |
| fusion contingent | 4 | early-durable fusions or fused-share > 0.2 |
| **seasonal vs ratcheted** | **8** | the ridge's weak edge |

## The finding

The tuning ridge's failure mode at defaults is **seasonal extinction**: by
generation 50, seasonal switching has died out entirely in 7/40 worlds
(median surviving switchers: 2 per world). Everything else is robust —
terrain decorrelation never fails, and fusion is reliably contingent and
reversible at the ensemble level (309 fusions, 264 unfusions; 23/40 worlds
ever fuse at all).

Interpretation (open question 3): with β = 0.8, transmission bias plus value
polarization slowly starves mixed-signature seasonal configurations even with
the material seasonal-fit coefficient in place. Whether ~20% of histories
losing seasonal dualism by year 1000 is *the tragedy the book describes* or
*too much Althusser* is precisely the unsettled research claim — the next
experiment is a β sweep (0.6 / 0.7 / 0.8 / 0.9) over this same seed set,
which the deterministic engine makes exactly reproducible.
