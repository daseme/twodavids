# GAP.md — the professional gap, audited

*2026-07-23, after the reality pass (phases 1–3). The question: the best
walkabout worlds run on this same stack — Three.js, low-poly, procedural —
and we are still visibly far from them. This is the honest accounting of
what they have and we lack, ranked by perceptual weight, each item mapped
to what we would do within the §0/§5 discipline (deterministic from bundle
+ seed, evidence-free, the manuscript palette stays). Not a wish list: an
order of attack.*

The comparison set, named so the standard is concrete: **Townscaper**
(finish: every surface considered), **Proteus** (ambient life and audio),
**A Short Hike** (camera feel and scale), the ANNALS reference
implementation (the craft brief we already mine), and the better
SimonDev-style procedural walkabout demos (grass, light, post).

What is *not* the gap, checked before anything was blamed: MSAA is on,
pixelRatio is capped at 2, shadows are PCFSoft at 2048, the sky is a
painted dome with sun glow, fog is tuned inside the world. The bones are
fine. The gap is finish.

## 0. The process gap — the real one, listed first

Every world in the comparison set was polished by eye over hundreds of
A/B iterations. We have been polishing blind: every change so far was
verified only structurally, by driver, because there is no screenshot
loop. This is why VIEWER.md keeps saying "measured on seed 3" about
*counts* and never about *frames*. Nothing below this line gets done
well until this exists.

**Build the eye**: headless Chromium (playwright or puppeteer, dev
dependency only — never shipped in the single-file viewer) driving the
instrumentation we already have (`__dawn.look`, `__dawn.seek`, `#t=N`,
`flying`, `snow`). A fixed shot list — the opening frame, a wander frame
in the wood, a storm frame at a hard-winter tick, night over the hearths,
the ratchet shot — screenshotted on every change, committed as
references, pixel-diffed in CI. Until this exists, every phase below is
hope; after it, each becomes a loop we can actually run.

**Built (2026-07-24).** `npm run shots` rebuilds the seed-3 viewer from the
template, freezes the page clock (rAF and `performance.now` replaced before
boot, frames stepped by hand at a fixed dt), and captures the eight-shot
list via CDP; `npm run shots:diff` pixelmatches against `shots/ref/` and
fails on drift, writing visual diffs to `shots/diff/`; `npm run
shots:accept` promotes captures to references. Verified deterministic: all
eight shots at 0.000% pixel difference across independent runs and a full
viewer rebuild. References are committed; CI (`.github/workflows/shots.yml`)
re-captures from the committed bundle and diffs on every viewer-touching
push. The loop exists — §1 can begin.

**Hardened (2026-07-24), by §1's grading loop, which promptly caught three
latent bugs.** (1) When consecutive shots differed only in their `#t` hash,
`page.goto` was a same-document navigation and the app never rebooted — every
shot after the first showed the *previous* shot's world, so the first
reference set never actually honoured its ticks (night-hearths was not night;
wander leaked into four frames). Capture now hops through `about:blank` so
every shot boots clean. (2) With a real boot, `#play` turned out to have been
dead since the opening ceremony landed: the play button's handler touched
`opening` inside its declaration's dead zone, the click died, and beat-card
had never once captured a playing world. (3) Wander derives its start from
the camera's actual position, which under the frozen clock had not yet
followed a `look()` — the harness now settles one frame between the two. The
shot list's ticks were then re-solved so each frame shows what its note
claims (`%32`: 0 dawn, 8 noon, 24 dark; season is `%4`), `look` gained a yaw,
and capture takes shot names as arguments so a grading loop can re-capture
two frames instead of eight.

## 1. The post chain — the film look

The single biggest visual jump available, and the one every comparison
target shares: the image passes through a chain before it reaches the
screen. Ours goes straight from Lambert/Phong to canvas.

- **Bloom.** Fire glow, the sun disc, water glitter, snow — we already
  built the emitters; bloom is what makes them read as light instead of
  as sprites. Bloom is also what makes the whole frame read "polished"
  at thumbnail size, which is where people decide to click.
- **Tone mapping.** We run default `NoToneMapping`; ACES or AgX
  compresses highlights the way film does, and is half of why the
  comparison worlds' skies and sunlit grass look expensive.
- **Film grain + subtle vignette in-pipeline** (the CSS vignette stays,
  but grain belongs in the chain, over the world and under the UI).

Cost and caution, honestly: this means vendoring EffectComposer + the
bloom/shader passes inline (~90 KB more three.js, against our
single-file discipline — acceptable), one render becoming two
(acceptable), and — the real cost — **tone mapping shifts every colour
we authored**. The palette, the ground paint, the biome tints, the
culture hues: all re-tuned against the new curve. Bloom and tonemap must
land together with a full re-grade, as one pass, compared by the §0
screenshot harness. Attempting it without the harness is how we get a
worse world that is technically more advanced.

**Built (2026-07-24).** Scene → bloom → ACES → grain: EffectComposer,
RenderPass, UnrealBloomPass, OutputPass and a grain/vignette ShaderPass,
vendored offline by `dawn/vendor/build-post.mjs` (three r178 examples
rewired onto `window.THREE`, published as `window.__POST`, ~46 KB) and
inlined by the build exactly like three itself. The scene renders into a
multisampled half-float target, so the MSAA the renderer was asked for
survives the composer. The grade against the curve: ACES at exposure 1.12
with a day-for-night lift (cubed toward true night, so the golden hours
stay on the base curve), night floors raised on key and fill, and every
emitter — sun disc, hearth glows, embers, fireflies — pushed past 1.0 so
the 0.85 bloom threshold separates a light from a bright sticker. Grain
is hashed from pixel and the stepped clock: deterministic under the
harness, alive at play; the framing warmth stays with the CSS vignette.
A/B'd frame-by-frame on §0's harness, which the pass repaid by exposing
three latent bugs (see §0's hardening note) — the corrected shot list
finally captured what it always claimed: beat-card's ratchet with the
card up and playback running, dig-wide's mounds at noon, night that is
night, with hearths that bloom against it.

## 2. The missing bottom layer — grass and understory

Every walkabout that reads "alive" has ground cover that moves. Ours has
canopy trees, then painted ground with scatter pebbles — the middle and
bottom storeys are missing, so the world is bald between its trees.

- **Grass**: thousands of instanced blades or crossed cards in the
  meadows and shores, swaying on the `WIND` uniforms we already built —
  the shader work is done, this is a geometry and placement problem.
  Height and density following biome and moisture (we have the fields:
  biome, distWater, forestGrid). This is the single highest-content
  change available: it fills the bottom third of every wander frame.
- **Understory**: bushes at wood edges, saplings, ferns in the wet
  biomes — the layer that makes a forest a place instead of a
  distribution.
- **Specks**: seed-heads, petals, snow-dust on scrub in winter. Cheap,
  seeded, and they read at exactly the distance grass stops reading.

Discipline holds: placement is biome- and moisture-driven from fields we
already compute; nothing here contradicts the record, and no agriculture
(§7's refusal stands — no rotated fields, no crop strips, ever).

## 3. The water's edge

The hardest edge left in the frame. Pros spend disproportionately on
shorelines because that is where the eye goes; ours is a painted band,
a breathing foam line, and a hard silhouette.

- Depth-graded foam width (the band widens over gentle shallows, pinches
  at steep banks — we have `distLand` and the shore slope to drive it).
- Lapping: a second foam band that advances and retreats on a slow
  period, offset per shore segment so it never pulses in unison.
- Caustic dapple in the shallows — a moving light pattern on the ground
  under the first half-unit of water, the thing that says "clear water"
  louder than any blue.
- The wet band animates with the lap phase (it is currently a per-tick
  paint; it wants to move to the shader beside the foam).

## 4. Light with only one source

One directional + a hemisphere fill is a diagram's lighting. What the
comparison set adds, cheapest first:

- **Contact AO**, baked: the terrain already knows where things stand
  (forestGrid, the wear field, settlement clearings) — darken the vertex
  paint under canopies and structures the way the hollow-occlusion bake
  already darkens hollows. This grounds every object in the frame; its
  absence is half of why things look placed rather than planted.
- **Sun shafts** at dawn and dusk through the wood: a few camera-facing
  shaft sprites near the sun's azimuth, gated by dayness and forest
  density. The cheapest drama there is, and dawn is already our opening
  shot.
- The shadow-penumbra question (VSM) stays deferred per the phase-4
  note — unverifiable until §0's harness exists, then testable.

## 5. The camera has no body

Half of "feel" in the comparison set is input processing, and ours does
almost none:

- **Input smoothing**: yaw/pitch/dist lerp toward the pointer's intent
  instead of tracking it instantly; the wheel arrives in eased steps,
  not jumps.
- **A body in wander**: subtle head-bob scaled by pace, a breath of FOV
  widening with speed, footfall-timed micro-settle when stopping.
- Flight easing is already good; the *ends* of flights want a beat of
  settle (a 200 ms overshoot-dampen) rather than a hard kinematic stop.

## 6. Audio locality

Three global beds was the right start; the gap is that nothing is
*anywhere*:

- **Footsteps by surface**: the surface under the walker is knowable
  (biome, wear, snow severity, shore distance) — grass whisper, gravel
  crunch, snow squeak, timed to the bob from §5. This is the single
  most legible audio upgrade in a walkabout.
- **Locality**: hearth crackle pans and falls off by the camera's
  relative bearing (StereoPannerNode is enough; no HRTF needed), water
  swells as the shore nears laterally, the wood muffles wind (a lowpass
  keyed to forestGrid under the camera).
- UI sounds: a paper tick on the scrubber, a page-turn on the beat card.
  The product is a chronicle; it should sound like one being handled.

## 7. The scale question — a decision, not a task

The world is ~30 seconds across on foot. Part of "diorama" is traversal
time, not geometry. Three honest options:

1. **Lean in** (recommended): the world is a valley, not a continent —
  slow the walker's pace, lower the eye slightly, let grass (§2) fill
  the near field. Small stops reading as toy when it reads as
  *intimate*.
2. **Render-scale**: multiply the render world ×2–3 (rendering-only,
  §0-legal) and fill the new space with §2's bottom layer. More walk
  per world; risks emptiness between content.
3. Leave it. Some of the best walkabouts are tiny and dense.

Decide after grass lands — it changes what the same 47 units feel like.

## 8. What we must not chase

Photoreal PBR, SSAO passes, volumetric fog, texture megascans: off-stack
and off-identity. The standard is Townscaper, not Unreal — professional
here means *consistent, intentional, finished*, and the manuscript
palette is the identity, not the limitation. §7's refusals all stand:
no farmland, no omens, no statal architecture the record didn't earn.
The gap is finish, never fidelity.

## The order of attack

1. **§0 — the screenshot harness.** Everything else is unverifiable
   without it; with it, each phase below becomes a loop instead of a
   gamble.
2. **§1 — post chain + full re-grade**, one coordinated pass, A/B'd on
   the harness. Biggest jump; must not be attempted blind.
3. **§2 — grass and understory.** Biggest content gap; fills the bottom
   of every frame.
4. **§3 — the water's edge.** The last hard edge.
5. **§4 — contact AO**, then sun shafts.
6. **§5 — camera body** and **§6 — audio locality** together: the feel
   pass.
7. **§7 — the scale decision**, made with §2 in the frame.
