# Ratchet-knob sweep: finding the seasonal-extinction control (2026-07-17)

The β sweep (`beta-sweep.md`) showed transmission bias is *not* the knob for
the one persistent failure mode — seasonal switching going extinct in ~12–17%
of worlds — and named the ratchet/re-evaluation dynamics as the suspects.
This sweep tests them. Same 40 seeds, 4000 ticks, defaults except the named
knob. Data: `sweep-ratchet_dom_pull-*.json`, `sweep-seasonal_fit_bonus-*.json`.

## The table

| arm | pass /40 | seasonal fails | switching extinct | median switching | ratchet events | fus/unf |
|---|---:|---:|---:|---:|---:|---:|
| **baseline** (pull .03, fit .25) | 31 | 7 | 5 | 4 | 308 | 326/277 |
| ratchet_dom_pull 0.015 | 30 | 7 | 3 | 6.5 | 124 | 146/122 |
| ratchet_dom_pull 0.045 | 27 | 9 | 8 | 2 | 474 | 299/252 |
| seasonal_fit_bonus 0.15 | 25 | 9 | 7 | 3 | 273 | 586/498 |
| **seasonal_fit_bonus 0.40** | **36** | **2** | **1** | **7** | 440 | 301/263 |

## The finding: it's the seasonal-fit coefficient, and it's clean

`seasonal_fit_bonus = 0.40` is the best regime found in the whole project:
**36/40 passing, seasonal failures 7→2, switching extinct 5→1** — while
fusion stays contingent and reversible (301/263) and no other criterion
regresses. The seasonal-extinction tail was controllable all along, exactly
where the β study pointed.

Both knobs show the mechanistically-expected dose-response:

- **`ratchet_dom_pull`** (how hard accumulated charisma+violence hold a failed
  handoff open) is monotone in the right direction: 0.015 → fewer ratchets
  (124), fewer extinctions (3), more seasonal survivors (median 6.5); 0.045 →
  far more ratchets (474), more extinction (8). It moves the tail but at a
  cost — lowering it also thins fusion (146 events) toward the "nothing
  sticks" edge, so it is a worse lever than the fit bonus.
- **`seasonal_fit_bonus`** (how strongly the material year rewards a
  dispersed-summer/aggregated-winter configuration in re-evaluation) is the
  direct control: 0.15 starves dualism (25/40, and fusion churn explodes to
  586 as lineages abandon seasonal configs for standing ones); 0.40 sustains
  it (36/40).

## Interpretation

This is theoretically the right place for the control to live. Seasonal
dualism survives or dies in the yearly *re-evaluation* of which configuration
a people runs — not in transmission bias (ideology) and not in the ratchet
probability itself. The material year "arguing for dualism" is a coefficient,
not a value: 0.40 makes the seasonal round materially attractive enough that
most peoples keep paying for it, while a people can still choose to ratchet
and pay the price. The book's world — most peoples keeping the seasonal
capacity, a minority ratcheting into standing power — is the 0.40 regime.

**Not yet promoted to the default.** 0.40 is a strong candidate for the new
`Params` default, but changing it shifts every future baseline and the
Phase-3 stub-vs-model comparison should run against one fixed baseline first.
Flagged for a decision after promotion analysis.
