# Promotion interim: the hospitality loop (2026-07-18, run in flight)

> **Superseded in part by `promotion-seed3.md`.** Written at tick ~597 while
> the run was still going. Its central observation (feast dominates the
> answer to contradiction) held and strengthened. Its claim that liberations
> are *starved* did not: at 2002 ticks the model produces more liberations
> than the stub (48 vs 38), rerouted through recovery rather than
> contradiction. Read the numbers below as an early sample, not a result.

Written while the full seed-3 promoted run cooks (tick ~597 of 4000 at time
of analysis). Two independent promoted samples exist over the same span —
the live run and the interrupted first attempt
(`runs/seed-3-promoted-partial-t973.journal.jsonl`) — and they agree
closely, so the signal is not sampling noise. Stub comparison uses
`runs/seed-3` truncated to the same tick horizon. All numbers are
deliberations of the promoted kinds only; live-model share ~94%
(fallbacks to stub ~6%).

## The stance tables (ticks ≤ 597)

**Encounter** (model n=474 live / 393 partial; stub n=~440):

| stance | live | partial | stub |
|---|---:|---:|---:|
| feast | 367 | 299 | 52 |
| affirm | 85 | 80 | 7 |
| emulate | 12 | 8 | 211 |
| invert | 5 | 3 | 78 |
| injected "way_of_…" | 2 | 2 | ~46 |

**Contradiction** (model n=624 / 912; stub n=~230):

| stance | live | partial | stub |
|---|---:|---:|---:|
| feast | 598 | 866 | 8 |
| refuse | 17 | 24 | 101 |
| mock / leave / propose | 7 | 9 | 52 |

## Macro consequences, same span

| | live | partial | stub |
|---|---:|---:|---:|
| feast events | 1008 | 1219 | 104 |
| liberations | 8 | 10 | 16 |
| …via contradiction | 4 | 2 | 13 |
| peak per-culture contradiction load | 505 | 472 | 144 |

## The finding, sharpened: it is a *loop*, not just a preference

The smoke run's "the model likes feasting" undersells it. The deep pattern:

1. The model answers **contradiction** — the promise/lived gap, liberation
   door 1 — with *feast* 95–96% of the time. Not affirm (denial), not
   refuse (the stub's modal answer): feast.
2. Feast's mechanics bleed accumulation and display but do not touch
   command or rank — so the gap that raised the contradiction does not
   close. The same faction re-deliberates, the model feasts again.
   Contradiction volume balloons (culture 5: 505 deliberations vs the
   stub's 86) and contradiction-mechanism liberations starve (13 stub →
   4 and 2 in the replicates). Recovery-mechanism liberations survive.
3. This is not obviously *wrong* anthropology. "Answer the tension with a
   feast, giving until the ledger is shamed" is the potlatch as leveling
   mechanism — redistribution as the culturally normal response to a
   wealth-shaped legitimacy gap. The model may be arguing more faithfully
   than the stub's theory prior; it is also, mechanically, pouring water
   on a grease fire forever.

## Prompt audit: four artifacts that could inflate the signal

Audited `dawn/claude_oracle.py` against `dawn/oracle.py`:

1. **Asymmetric theory injection.** The stub receives `_SITUATION_BIAS` —
   Bateson in numeric form (encounter: emulate +0.7, invert +0.7;
   contradiction: refuse +0.8). The model receives no equivalent framing:
   its encounter note mentions the outsider's move (borrowing) but never
   hints that contact sharpens difference as often as it softens it. The
   comparison as run is model-vs-(RNG + theory), not model-vs-RNG.
2. **The hosting frame.** `KIND_NOTES["encounter"]` opens "Travelers from
   another people sit at the fires tonight" — the scene is already
   hospitality; feast is its natural completion. A neutral frame (met at
   the boundary; fire or distance undecided) would let values pick.
3. **Position bias.** The menu is alphabetized (`engine.menu_for`), so
   `affirm` is always first — and affirm is the model's #2 encounter move
   while being rare (7) for the stub.
4. **Vividness asymmetry.** Feast has the most vivid, morally flattering
   gloss on the menu ("giving until the ledger is shamed") vs invert's
   abstract "become in this matter the opposite of what our neighbors
   are." Glosses are the model's only view of the moves.

Also notable: the model almost never takes the injected `way_of_…` stance
(2 per replicate vs ~46 for the stub) even though the encounter note
explicitly gestures at it — the model prefers canonical moves.

## What to decide after the full run (not now)

- **(a) Treat it as the finding.** A faithful arguer given ethnographic
  sketches reaches for hospitality and redistribution over refusal and
  differentiation; schismogenesis weakens; the world drifts toward feast
  equilibria. Graeberian irony fully intended.
- **(b) Neutralize the artifacts and re-run**: symmetric encounter frame,
  deterministic per-call menu shuffle, gloss vividness pass — then measure
  what survives. The delta between (a) and (b) is the model's *own*
  hospitality prior, separated from ours.
- Recommended: both, in that order — (a) is this run; (b) is one more
  4000-tick promoted run after the prompt patch. The two runs bracket the
  truth, and the seasonal_fit_bonus default decision should wait for (b)
  since a feast-heavy world moves the accept-suite baselines.
