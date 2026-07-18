# VIEWER.md — the replay viewer (Phase 4, scaffold building)

*A specification extracted from the ANNALS craft reference with its ontology
inverted. Status: Phase 3 shipped, so the pixel gate has opened — `dawn
viewer <run-dir>` builds a scaffold (dawn/viewer.py + viewer_template.html,
Three.js r178 vendored in dawn/vendor/). Working today: terrain/water/rivers,
territory tint with closed-axis border sharpness, seasonal
assembly/disassembly from the config table, all eight §3.3 axis→parameter
rows (salience-gated), earned statal architecture from the domination tracks
(§3.2: palisade/watchtower, monumental lodge + plaza, guarded granaries,
keep + regalia + processional axis at fusion), heraldic charge repulsion
against territorial neighbours with fallen-crown scars at unfusion (§3.5),
an LOD person band, spring-damper camera, a director that flies to arguments
— deliberations verbatim, liberation notes, ratchet displacements, and the
succession non-event; encounters land on the frontier midpoint over a fire —
defection walks and feast fires interpolated from the journal's flow records,
chronicle attrition as margin ambience (doomed entries render crumbling),
a day/night cycle, `dawn bundle` (§6.3), and `#t=N&play` deep links.
Still to come: the full ANNALS shot grammar (cuts, shot variety, cooldown
tuning), heraldic regalia unlock animation, drag-and-drop bundle loading.*

## 0. The architecture in one sentence

Because the sim is deterministic and journal-replayable, the viewer is a
**replay client**: a single HTML file that consumes a run bundle (seed +
journal + snapshots) and renders a finished history — no API calls, no sim
logic beyond interpolation, no second simulation to drift out of sync.
ANNALS's conceit was "watching a history write itself"; ours is **watching a
history that was argued into being** — and unlike ANNALS, the arguments are
in the journal verbatim, so the film can quote its sources.

**The dependency arrow points one way: journal → pixels.** A bundle field is
legitimate only if it is (a) already-simulated state, or (b) a rendering-only
worldgen product that never drives culture (precedent: `elevation`, exported
for relief, marked "never drives culture"). "This would look great" is how
ontology creeps back in; nothing enters the sim for the viewer's sake.

**The elaboration rule** (the viewer's prime directive). The sim has no
settlement coordinates, no faces, no trees — the viewer must invent geometry.
Invention is permitted under two constraints: it is **deterministic** from
bundle + seed (same bundle, same film, forever), and it is **evidence-free** —
it may decorate what the record is silent about but may never contradict or
add to the record. This is the almanac's honesty-about-gaps discipline in
visual form. (It is also the archaeologist-mode contract run in reverse.)

## 1. The run bundle — the contract between sim and viewer

### Exists today (the 2D watch mode already consumes it)
- `meta.json` — seed, ticks, model id, full params.
- `world.json` — grid, biome, elevation (mils, rendering-only), `owner0` +
  territory `deltas` (ownership changes only at schism/extinction, so the
  map's whole past is one grid plus ~dozens of deltas), configuration
  glosses, final culture roster.
- `journal.jsonl` — every event; every deliberation **verbatim** (speaker
  name, traits, quoted argument, stance chosen, menu offered); tick summaries
  every 20 ticks (per culture: pop, mean value vector, domination tracks,
  dominant config, switching flag).
- `chronicle.jsonl` — the in-world record with authorship, medium, survival,
  redaction. `scars.jsonl` — refusals, abandonments, dead routes, ratchet marks.

### Additive fields needed (small, rendering-neutral; useful to 2D watch too)
1. **Config table**: eid → season→structure map (authority, pooling,
   settlement, roles), not just the gloss. Drives seasonal assembly/disassembly.
2. **Salience** vector in tick summaries — which axes a culture currently
   *performs* (contested axes are displayed axes).
3. Optional, v2: hospitality-edge snapshots (openness per edge per summary)
   for route rendering. V1 derives border character from the two cultures'
   closed/open values, which summaries already carry.

Explicitly rejected: per-tick weather journaling. Weather is not recorded;
the viewer renders season + `hard_winter` events and nothing finer. That gap
is the backward-leak rule holding, not an oversight.

## 2. Severable craft — adopt from ANNALS wholesale

- Single-file discipline, **amended**: vanilla JS, no build step — but
  Three.js **vendored inline** (a current release, not r128; no CDN). A CDN
  breaks offline use, artifact CSP, and twenty-year replayability, and
  "seed + journal = world, forever" extends to the film of it.
- Spring-damper camera rig with the curved altitude path.
- LOD bands, especially the **bubble band**: people are statistics until the
  camera is close, then individuals instantiate. This is philosophically apt
  here — lazily instantiated notables are already the sim's person model.
- Performance budget; procedural-everything via vertex colors and small
  canvas atlases; day/night cycle; render/sim decoupling via interpolated paths.
- Parchment UI skin and period-serif chronicle typography — a better fit for
  this project than for ANNALS, since the product literally is a chronicle.
- The illuminated-manuscript aesthetic: low-poly painterly, the marginalia of
  a chronicle come to life.

## 3. Carrying ontology — take, but invert

### 3.1 Borders are not facts
ANNALS paints bounded polities in flat house colors. Here, membership renders
as a **gradient field with fuzzy edges**, and border *sharpness* is a
simulated variable: edges crisp as the closed/open axis hardens or a
hospitality route dies (dead routes are already scars with locations).
Freedom of movement made visible as blur. A fused polity's frontier should
read like a line; a feasting pair's frontier like a watercolor bleed.

### 3.2 Visual vocabulary must be earned
No keeps, walls, or treasuries at worldgen — the renderer's statal
architecture is `king`/`realm`/`treasury` in polygon form, and the lexicon
rule applies to it identically:

| appears only when | visual |
|---|---|
| violence track accumulates / closed hardens | palisade, watchtower |
| charisma track + display | monumental lodge, plaza of assembly |
| accumulation + hoard pooling | granary-with-guards |
| hardening | walls around the stores, the counting-house |
| fusion | keep, regalia, processional axis |

A viewer scrubbing a ratcheted lineage should *watch it start looking like
ANNALS* — that resemblance arriving late and contingently is the argument.

### 3.3 How to see a value vector
Map the eight axes to rendering parameters, gated by salience (contested axes
are performed loudly; unsalient ones fade toward vernacular default):

| axis | render parameter |
|---|---|
| rank / equality | variance of building sizes — a Gini coefficient of rooflines, readable at 800 m |
| display / modesty | ornament density, banners, painted facades |
| nomadism / settled | structure permanence: hide tents ↔ timber ↔ stone footings |
| closed / open | palisade and gate ↔ open plaza and many paths in |
| accumulation / distribution | granaries and fenced herds ↔ feast hearths and open middens |
| command / refusal | axial, planned layout around a central lodge ↔ organic, unplanned scatter |
| sacred-elaborate / plain | shrine elaboration, processional markers |
| violence-honored / shamed | weapon iconography, trophy posts ↔ none visible |

Payoff: a viewer can read culture from the look of a place and **cannot**
read it from the terrain — the terrain-decorrelation acceptance test becomes
something verified with the eyes.

### 3.4 The single best shot
Seasonal dualism. A settlement that physically **disassembles in spring** —
houses struck, the camp dispersing along the valley — and reassembles in
autumn under a different spatial logic: the winter form concentric around the
big lodge, the summer form scattered and even. Driven directly from the
config table (season → structure settlement/authority). A ratchet is then
*visible as an absence*: the autumn assembly convenes and the spring
disassembly never comes. Seasonal dualism is nearly unfilmable in prose and
trivially legible in 3D; this is the strongest single argument for the viewer.

### 3.5 Heraldry, schismogenetically
Sigils stay; charge selection is biased **against** neighbors' charges
(deterministic from culture id + contact history), so heraldry itself
exhibits the repulsion dynamic. Statal regalia unlock with fusion, are
abandoned at unfusion, and an abandoned crown is a scar the camera can find.

## 4. The director — mechanism adopted, beat list replaced

Keep the shot grammar, priority bus, and cooldowns. Replace the beats: this
camera flies to arguments, not battles.

- **Deliberation** — two delegations across a frontier fire; the beat card
  carries the journal's actual quote, speaker name and traits. The film cites.
- **Handoff** — the chief stepping down as the ice breaks: the recurring
  *non-event* that ANNALS could never film because its ontology had no verb
  for power dissolving on schedule.
- **Ratchet** — the assembly that fails to disperse (see 3.4).
- **Defection** — families walking a hospitality route; **schism** — the
  larger walking-out, a new camp rising across the valley.
- **Feast** — the boundary softening on screen (3.1); **encounter** —
  travelers at the fire, the Kandiaronk beat.
- **Fusion** — regalia appearing; **unfusion** — regalia abandoned where they
  fell; **liberation** — the chronicle re-read aloud, the old way resumed.
- Chronicle attrition as ambience: entries visibly fading from the margins.

## 5. Deliberately absent

The Acts panel and every god-button; any control that lets the viewer touch
history; battles as default spectacle; pre-installed statal architecture; any
schema change to the sim justified by appearance. The viewer watches. The
only causal verb remains *argue*, and it lives in the CLI with the oracle
(interlocutor mode, Phase 3+).

## 6. Sequencing

1. **Now** (cheap, additive): land bundle fields §1.2 (config table, salience
   in summaries) the next time the engine is touched; they serve the 2D watch
   immediately.
2. **After Phase 3** (promotion — the model's stances fork history): build
   the viewer against the bundle, as a side-track that cannot distort the core.
3. `dawn bundle <run-dir>` CLI: zip the six files with a version stamp; the
   viewer accepts a bundle by drag-and-drop or URL fragment.
