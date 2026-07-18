# β sweep: beta_ideology ∈ {0.6, 0.7, 0.8, 0.9} × 40 seeds (2026-07-17)

Same 40 seeds (1–40), 4000 ticks, defaults except `beta_ideology`. Raw data:
`sweep-beta0.6.json`, `sweep-beta0.7.json`, `ensemble-40.json` (0.8),
`sweep-beta0.9.json`. Reproduce with
`dawn accept --seeds 40 --ticks 4000 --jobs 12 --set beta_ideology=<β> --json <path>`.

## The table

| metric (40 worlds) | β=0.6 | β=0.7 | β=0.8 | β=0.9 |
|---|---:|---:|---:|---:|
| worlds passing all criteria | 31 | 32 | 30 | 32 |
| seasonal switching extinct | 7 | 3 | 7 | 5 |
| median switching lineages at end | 2 | 3 | 2 | 4 |
| ratchet events (total) | 263 | 311 | 187 | 234 |
| ratcheted lineages at end | 347 | 313 | 324 | 347 |
| fusions / unfusions | 391/326 | 209/175 | 309/264 | 385/317 |
| worlds ever fusing | 24 | 25 | 23 | 25 |
| median liberation rate | .069 | .063 | .084 | .077 |
| median terrain NMI | .100 | .102 | .098 | .101 |

## The finding: the ridge is a plateau in this range

The handover doc feared a knife-edge — "transmission bias too strong and
every run ratchets (Althusser wins); too weak and nothing sticks." **Within
β ∈ [0.6, 0.9], neither cliff exists.** Pass rates (30–32/40) are within
binomial noise of each other (σ ≈ 2.7 at p ≈ 0.75, n = 40); seasonal
extinction (3–7 worlds) shows no monotone response to β; terrain
decorrelation, liberation rates, and fusion contingency are all flat.

Two conclusions, one reassuring and one redirecting:

1. **Reassuring:** the load-bearing ideology mechanism is *robust*, not
   fine-tuned. The book does not lose to Althusser anywhere in a ±25% band
   around the default bias strength. The acceptance behavior of the sim is
   not an artifact of a lucky β.
2. **Redirecting:** β is *not the control knob* for the one recurring failure
   mode (seasonal extinction in ~5–17% of worlds). That tail must be driven
   by the ratchet/re-evaluation dynamics rather than transmission bias —
   candidate knobs for the next sweep, in order of suspicion:
   `ratchet_dom_pull` (how hard accumulated charisma+violence hold a failed
   handoff in place), the seasonal-fit coefficient in dominant-config
   re-evaluation (currently 0.25+0.25, hardcoded in `engine._reevaluate_dominant`
   — should be a `Params` field before sweeping), and `ratchet_base`.

Method note: fusion totals swing widely between arms (209–391) because a few
fusion-churn worlds dominate the count; per-world "ever fuses" (23–25/40) is
the stable statistic and is flat across β.
