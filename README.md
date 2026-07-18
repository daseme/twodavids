# dawn — *The Dawn of Everything* as a procedurally generated world

A world-history simulator that inverts the usual causal chain of procedural
worldbuilding: cultures here are self-created through mutual differentiation
(schismogenesis), conscious refusal, and argument; terrain constrains and
prices choices but never selects them. The primary output is a **chronicle** —
generated world-histories meant to be read. There is no victory condition.

Read `HANDOVER.md`-style context in the project brief, then `DESIGN.md` for
the decisions made during Phase 1 and the honest state of the tuning ridge.

## Status: Phase 1 complete · Phase 2 (model-written prose) scaffolded

The sim is a pure function of its seed; the run loop is model-free. Phase 2
narration is a **post-processing pass** over a finished run: `dawn narrate`
sends the surviving chronicle through the Claude Message Batches API (tiered:
Haiku for volume, Sonnet for major beats, Opus for era syntheses; ~$1.20 for a
full 1,000-year world) and overlays the prose on the almanac. Same seed, same
history, new voice — the journal is untouched and replay still verifies.
Stances remain stubbed until Phase 3 (promotion).

Baseline: `studies/ensemble-40.md` — 30/40 worlds pass all acceptance
criteria at defaults; the ridge's weak edge is seasonal extinction (~20% of
worlds), not terrain correlation (never fails) or fusion irreversibility.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m pytest            # invariants: determinism, replay, no-numbers boundary
.venv/bin/dawn run --seed 1 --ticks 4000   # ~20s: one world, ~50 generations
less runs/seed-1/ALMANAC.md           # read the history
.venv/bin/dawn viz runs/seed-1        # self-contained HTML report (maps, tracks, timeline)
.venv/bin/dawn watch runs/seed-1      # playback page: watch the world unfold in time
.venv/bin/dawn replay runs/seed-1     # verify seed + journal = world
.venv/bin/dawn accept --seeds 6       # the §5 acceptance suite, honest output
```

## What a run produces (`runs/seed-N/`)

- `journal.jsonl` — every oracle call and world event; **reproducibility is
  the journal, nothing else** (seed + journal = world, forever, no model).
- `chronicle.jsonl` — the in-world chronicles: authored, biased, attriting;
  oral entries decay fast, written ones persist but get captured.
- `ALMANAC.md` — the reader-facing meta-document compiled from *surviving*
  chronicles plus material traces, citing sources and honest about gaps.
- `scars.jsonl` — refusals, abandonments, dead routes, ratchet marks.
- `metrics.json` — the acceptance criteria for this world.
- `world.json` — the map and roster at close of record (feeds `dawn viz`).
- `report.html` — after `dawn viz`: maps, domination tracks, event lanes,
  chronicle excerpts; fully self-contained, run dirs from before `world.json`
  are reconstructed via replay.
- `watch.html` — after `dawn watch`: play/scrub through all seasons on a
  hillshaded map; schisms, fusions, liberations and abandonments pulse,
  defections flow, feasts arc, and the chronicle scrolls as it is written.
  Click a people for a live dossier (population, domination tracks, the eight
  value axes, and their prose sketch — the same text the oracle sees); click a
  second people to watch the pair diverge or converge in value-space.
  Inspection only, by design: no god-buttons, ever.

## Layout

```
dawn/values.py      eight-axis value basis; sketch() = the numeric→prose boundary
dawn/params.py      every tuning knob, including beta_ideology (THE knob)
dawn/repertoire.py  stances/configurations/lexemes; ideology as biased transmission
dawn/world.py       terrain, initial cultures (differentiated, never biome-derived)
dawn/culture.py     cultures as distributions: mean + factions; domination tracks
dawn/material.py    stochastic pricing, never determining; predators 1–2
dawn/contact.py     schismogenesis (both Batesonian modes); predators 3–4
dawn/polity.py      seasonal handoffs, ratchets, hardening, fusion detection
dawn/oracle.py      deliberate(sketch, situation) → {stance, text}; stub + replay
dawn/engine.py      the tick loop (tick = one season), in the specified order
dawn/chronicle.py   in-world chronicle: tone, lexicon gating, attrition, capture
dawn/almanac.py     the compiler for the reader-facing almanac
dawn/viz.py         dawn viz: self-contained HTML report from a run directory
dawn/metrics.py     acceptance tests (§5), thresholds marked provisional
```

## Build phases

1. ✅ Deterministic core + stub oracle (this).
2. LLM narration only (real prose, stubbed stances — trajectories unchanged).
3. **Promotion**: the model's stances go live and history forks on its
   choices. This is the point of the project, not a stretch goal.
