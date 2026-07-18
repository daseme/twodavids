# Promoted vs stub, seed 3, 2002 ticks (2026-07-18)

The Phase-3 experiment, run to 25 generations and stopped there deliberately
(cost; see the note at the end). Both arms are the same seed and the same
engine; the only difference is who chooses stances on the four promoted
deliberation kinds. Model arm: `claude-sonnet-5`, 4312 of 4509 promoted
deliberations decided live (95.6%), with no degradation across the run
(94% → 97% by 500-tick bucket). The stub arm is the same world replayed to
the same horizon. Data: `compare-seed3-2002.json`, `runs/seed-3-promoted`,
`runs/seed-3-at2002`.

The histories diverge at **tick 2**.

## 1. The repertoire collapses

| | stub | model |
|---|---:|---:|
| promoted deliberations | 1855 | 4310 |
| distinct stances used | **54** | **6** |
| top move's share | emulate, 27.5% | **feast, 94.0%** |
| novel/borrowed moves (`way_of_*`) | 497 (26.8%) | **0 (0.0%)** |

This is the finding, and it is larger than the earlier interim read. The
stub's worlds argue in fifty-four different ways; the model's argue in six,
and 94% of the time in one. Given a menu that includes refusal, mockery,
exit, inversion and emulation, a faithful arguer reaches for the feast and
keeps reaching.

The zero is the sharpest number here. Encounters inject a stance no one in
the culture has used before — an outsider's move, the mechanism by which
this world is supposed to acquire new ways of arguing. The stub adopts one
497 times. **The model adopts one never.** Offered a move it has not seen
before, in a world designed around the proposition that cultures are
self-created through borrowing and refusing, it declines every time.

## 2. The feast does not close the gap it answers

The model answers *contradiction* — the promise/lived gap, liberation door
1 — with feast almost always. Feast bleeds accumulation and display but
touches neither command nor rank, so the gap that raised the contradiction
survives the answer and raises it again. Contradictions therefore multiply:
470 in the stub, **3137** in the model, against a nearly unchanged encounter
count (1373 vs 1160). The model's world is not busier; it is stuck in one
argument.

This is also why a promoted run's cost cannot be forecast: the model's own
choice of move inflates the number of choices it is asked to make.

## 3. Liberation is rerouted, not suppressed — correcting the interim study

`promotion-interim.md`, written at tick ~597, reported that liberations were
starving under the model. **At 2002 ticks that is wrong, and the correction
matters more than the original claim.**

| liberations by mechanism | stub | model |
|---|---:|---:|
| contradiction | 23 | 10 |
| recovery | 8 | **37** |
| encounter | 4 | 1 |
| ratchet_break | 3 | 0 |
| **total** | **38** | **48** |

The model's worlds free themselves *more often* than the stub's — but almost
entirely by **recovery**: reading the old tellings and resuming a way that
had lapsed. Liberation by refusing a present demand drops by more than half;
liberation by remembering an older one more than quadruples.

So the model does not produce a docile world. It produces a world whose
third freedom runs through memory rather than refusal — one that frees
itself by looking backward, not by walking out. Whether that is a finding
about the model, about the prompt, or about what "arguing faithfully as a
pre-modern people" pulls toward is exactly what the neutral-prompt ablation
is for.

## 4. The world is not worse, it is different

| | stub | model |
|---|---:|---:|
| living cultures at close | 11 | **15** |
| schisms | 0 | 5 |
| extinctions | 1 | 2 |
| ratchets | 4 | 3 |
| fusions / hardenings | 0 / 0 | 0 / 0 |
| acceptance suite | PASS | PASS |

Both worlds pass §5. The model's world ends more populous and more divided:
five schisms against none, and four more peoples alive. Feasting does not
homogenise here — peoples split while remaining hospitable. Fusion appears
in neither arm, which is expected at 25 generations; the fusion/ratchet
questions need the longer horizon this run deliberately did not buy.

## 5. What this does and does not license

- **Does**: the promotion is real and legible. The model's stances fork
  history from tick 2 and produce a measurably different world under the
  same physics.
- **Does not**: attribute the collapse to the model alone. Four prompt
  artifacts were identified in `promotion-interim.md`, three are patched in
  `--prompt-variant neutral`, and the fourth (the stub receives Bateson as
  numeric priors the model never sees) is deliberately unpatched and openly
  asymmetric. The 94%/0% figures above are the *unpatched* arm.
- **Next**: the ablation, `--prompt-variant neutral --ticks 858
  --max-calls 1600`, against the healthy prefix of this same run. If the
  repertoire stays collapsed under neutral framing, shuffled menus and
  levelled glosses, the collapse is the model's. If it opens up, a good part
  of it was ours.

**Horizon note.** This run was capped at 2002 ticks rather than 4000 for
cost, after credit exhaustion silently corrupted an earlier attempt (see
`--max-calls`, added in response). Every claim above is a 25-generation
claim. Fusion, hardening and the long-run ratchet tail are simply not
observable at this horizon and are not claimed either way.
