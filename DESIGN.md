# DESIGN.md — The repertoire's data shape, and what Phase 1 found

*Companion to the handover document. That document owns the theoretical
commitments; this one records the decisions that were still open when it was
written — chiefly open question 1 (the repertoire), plus the parts of
questions 2 and 4 the code now embodies — and the honest results of the first
acceptance runs. Every functional form below is a candidate answer to the
critics who say schismogenesis names a pattern without specifying a mechanism.
Argue with these decisions in this file, not silently in the code.*

## 1. The repertoire (open question 1 — decided)

### 1.1 Element types

One base shape, three kinds (`dawn/repertoire.py`):

| field | meaning |
|---|---|
| `eid`, `kind`, `name`, `gloss` | identity; the gloss is what a deliberation prompt shows |
| `alignment` (8-vector) | which value poles the element expresses — the hook ideology pulls on |
| `origin` | `{tick, mechanism, source}`, mechanism ∈ primordial \| proposed \| borrowed \| recovered |
| `weight` | transmission vitality in [0,1], **per holding culture** |
| `use_ema` | recency of exercise (chosen, run, uttered) |
| `lapsed`, `below_since` | the freedom-loss bookkeeping |

- **Stance** adds `delta` (bounded value-vector move, ‖δ‖∞ ≤ 0.15) and `tags`
  (refusal, consent, exit, exchange, proposal, memory, …). A stance is a move
  in cultural argument; the tags are what situations and side-effects key on.
- **Configuration** adds `seasons`: a 4-tuple of structure ids (spring, summer,
  autumn, winter) plus `ratcheted`. Structures (band_camp, council_hall,
  chiefly_lodge, sacred_assembly, hoard_fort) carry authority/pooling/
  settlement/roles and a value signature. A configuration's signature is the
  mean of its structures' signatures — the ideological face of a way of life.
- **Lexeme** adds `register` and `unlock`. Statal vocabulary (king, treasury,
  realm, decree, throne, subject) ships **locked**: present in the data model,
  absent from every world's sayable language until a fusion earns it. Locked
  lexemes neither rot nor can be "remembered" into existence — they are not
  lapsed memories, they are unearned words.

Each culture holds its **own copies** of elements (schisms deep-copy, borrowing
copies). This costs memory and buys the important thing: glosses, weights, and
histories can drift per culture.

### 1.2 The transmission-fitness function (ideology, made explicit)

Per tick, per element, per culture:

```
align(e)   = (e.alignment · signature(dominant configuration)) / 4
fitness(e) = clamp01( 0.25 + 0.5·use_ema + β·align(e) + bonuses )
weight    += η · (fitness − weight)
```

- **β (`beta_ideology`, default 0.8) is THE knob** — the strength of the bias
  toward elements that reproduce the currently dominant configuration. That
  bias *is* ideology; there is no separate ideology system.
- The /4 (not /8) divisor is deliberate: alignment vectors are sparse, and the
  bias must be strong enough to actually starve anti-dominant elements.
- Bonuses: the running configuration gets +0.35 (it reproduces itself);
  generic consent (`affirm`, zero alignment) gets +0.10 everywhere.
- An element below `w_live` (0.15) for `lapse_ticks` (40) **lapses**: it leaves
  the deliberation menu. Not banned — it failed to arrive.
- A lapsed element that is cited in no surviving chronicle entry of its culture
  and live in no hospitality-neighbor's repertoire decays further and is
  **deleted** — genuinely forgotten. This is why `propose` carries anti-command
  alignment: under a fused dominance, the third freedom itself is what quietly
  fails to arrive. (Verified in `test_transmission_bias_discounts_the_unaligned`.)

Time constant: η = 0.03 gives roughly 1–2 generations from disuse to lapse —
"alternatives fail to arrive after two or three generations of discounted
transmission," as specified.

### 1.3 The contradiction accumulator (liberation door 1)

Per faction: `promise` is what the dominant configuration's ideology claims for
everyone — grander structures make grander claims
(`0.55 + 0.25·max(0,sig_command) + 0.1·max(0,sig_rank)`). `lived` is the
faction's realized wellbeing after pooling skew (share = equal; redistribute =
mild rank skew; hoard = strong rank skew).

```
c_f ← (1 − 0.03)·c_f + max(0, promise − lived)
```

Crossing θ = 5.0 (roughly 20–30 bad seasons) triggers a deliberation whose
situation-bias opens refuse/leave/mock/propose. Consent (`submit`) halves the
accumulator without closing the gap — ideology buys time, not truth.

### 1.4 The three liberation doors, as implemented

- **Contradiction**: above. A resulting walk-out logs a liberation event.
- **Encounter** (the Kandiaronk mechanic): high-difference contact
  occasionally injects ONE foreign stance into a deliberation menu. If chosen,
  it enters the repertoire (`borrowed`) or revives a lapsed local copy.
- **Recovery**: chronicler cultures occasionally re-read their chronicle; the
  `remember` stance revives a lapsed element — preferring elements the
  surviving chronicle actually cites. **Ratchet entries cite the displaced
  seasonal configuration**, so the memory of the seasons survives in the
  record and a people can re-read its way back. Oral attrition (0.75/generation)
  vs written (0.985) makes this door structurally wider for literate cultures —
  and capture (redaction under information-fusion) narrows it again.

Liberation is priced: breaking a ratchet costs population (×0.97) and drops the
violence/charisma tracks — refusals are impressive because they cost.

## 2. The predators on schismogenesis (open question 2 — first commitments)

Every positive feedback loop ships with a predator. Chosen forms:

1. **Extremity pricing** (material): caloric-axis positions beyond 0.6 pay a
   quadratic calorie tax. Prices, never selects.
2. **Internal dissent**: when wellbeing < 0.55, the mean drifts on caloric axes
   back toward what feeds, at a rate proportional to hunger. *Phase-1 finding:
   without this predator, every world marched off the caloric cliff together
   (mean extremity 0.36→0.92, population −87% over 50 generations). Pricing
   alone is not a predator; something must respond to the price.*
3. **Contact decay**: salience decays 0.008/tick absent interaction — what is
   not argued about stops being contested.
4. **Ritualized exchange**: a feast damps the repulsion coefficient on that
   edge by 60% for 24 ticks. The feast stands between rivals.
5. **Cohesion** (added in tuning): faction offsets relax toward the mean at
   1%/tick — the same channels that bias transmission between generations
   homogenize within one. Without it, defection fired ~1.1×/tick, world-wide.
6. **Succession** (added in tuning): charisma is a person, not an office; a
   chief's death (~1%/tick) halves the charisma track. *Finding: without this,
   fusion was an absorbing state (14 fusions, 0 unfusions); with it, 52
   fusions / 47 unfusions across six worlds.*

## 3. The initial stance menu (open question 4 — first cut)

affirm, submit, refuse, mock, leave, invert, emulate, remember, feast, propose
— glosses, alignments, deltas, and tags in `repertoire.py::primordial_stances`.
Notable commitments: `mock` is a first-class political act (predator on
charisma); `feast` is a first-class diplomatic act (predator on repulsion);
`invert` and `emulate` are the schismogenetic and counter-schismogenetic moves;
`propose` mints new stances into that world's repertoire at that point in its
history (auto-accepted in Phase 1; the journal's `proposal` records are the
designer-review inbox).

## 4. Other decisions made here

- **The state assembles link by link**: seasonal dualism → failed handoff
  (ratchet) → generations of standing chiefship + drift toward accumulation/rank
  → **hardening** (chiefly_lodge → hoard_fort: tallies, walls, writing) → only
  then can all three tracks accumulate to fusion. No step is scheduled; each is
  a probability that history may never roll.
- **The year argues for dualism**: configurations with aggregated winters and
  dispersed summers get a material scoring bonus. A coefficient, not a value —
  paying to refuse the season remains a live choice.
- **Dominant-configuration re-evaluation** happens each spring: value-fit +
  incumbency inertia + domination pull for ratcheted configs + the seasonal
  coefficient. Leaving a ratcheted configuration is the ratchet-break
  liberation, with its price.
- **"Early fusion" means early durable fusion** in the acceptance metric: a
  year-134 kingdom that collapses by year 160 is the book's world, not its
  counterexample.

## 5. Where the tuning ridge stands (open question 3 — status, honest)

**Update (see `studies/beta-sweep.md`):** a 4×40-world sweep found the ridge
is a *plateau* in β ∈ [0.6, 0.9] — pass rates 30–32/40 everywhere, no cliff
on either side. The ideology mechanism is robust, not fine-tuned; the
seasonal-extinction tail (~5–17% of worlds) does not respond to β and is
suspected to live in the ratchet/re-evaluation dynamics instead
(`ratchet_dom_pull`, the hardcoded seasonal-fit coefficient, `ratchet_base`).

Initial small-sample survey at defaults (β = 0.8), seeds 1–6, 4000 ticks:

- **5/6 worlds pass all seven acceptance criteria.**
- Terrain decorrelation: NMI 0.06–0.12 against a 0.30 threshold — culture is
  not predictable from ecology. The core mechanic holds.
- Worlds differ in character, which is the point: seed 2 is mostly free and
  seasonal (16 switching, 1 ratcheted); seed 1 is mostly ratcheted with
  dynastic churn (14 fusions, 13 unfusions); seed 5 never fuses at all.
- Liberation runs 0.04–0.24 events per culture-generation — rare, costly,
  possible — with all three mechanisms represented (recovery most common,
  encounter rarest, as it should be).
- **The failure to watch**: seed 4 — a low-population world of churning
  short-lived states where seasonal switching died out entirely and liberation
  spiked (0.55/culture-gen, mostly contradiction walk-outs). One world in six
  landing off the ridge is currently accepted as variance, not tuned away.
  Whether such worlds should exist at defaults, and at what frequency, is the
  central research claim and is NOT settled.

## 6. Invariants the test suite enforces

- Same seed ⇒ identical journal (bit-for-bit).
- Seed + journal ⇒ identical world with **no oracle** (`dawn replay`).
- The oracle never sees a number: sketches are ethnographic prose, enforced by
  regex in tests over every journaled deliberation.
- Anti-dominant elements lapse; aligned ones survive unused; unrecorded lapsed
  elements are eventually deleted; revival works.
- 400-tick runs keep values in [−1,1], tracks in [0,1], populations sane.

## 7. What Phase 2 needs (not started)

The oracle interface is one function: `deliberate(sketch, situation) →
{stance, text}` (`dawn/oracle.py`). Phase 2 swaps `StubOracle` for a
Claude-backed provider behind the same protocol: Message Batches per tick
(custom_id = culture-id + tick, deliberations already resolve simultaneously
from pre-tick state, so batching is free), prompt-cache the static system
material on the 1-hour TTL, tier the calls (cheap narration / mid deliberation
/ top era synthesis). Nothing else in the engine may change — that is the
point of the journal test.
