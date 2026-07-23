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
The shot grammar frames each beat kind (ratchet overhead, liberation low
and close, schism wide; long moves cut instead of touring; the crown pulses
at fusion), and a dropped `bundle.zip` re-boots the viewer into any world —
bundles are stored, not deflated, so the parser needs no vendored inflate.
**Archaeologist mode** (`dig`, or `a`, or `#dig`) renders only what the
surviving record supports: peoples are known through their surviving
chronicle entries, unattested ones collapse to anonymous grey mounds with
their territory tint stripped, heraldry and regalia drop away as textual
inference while built form stays as material trace, and beat cards may
quote only surviving entries — showing the gap where there is none. On
seed 3 this exposes the argument directly: Thaillaukak wrote 663 entries
and none reach us, Kwirthesyus 1 of 433, while Yuslos keeps 234 of 474;
oral entries survive at 3%, written at 76%. Whose past we can see is a
fact about media, not about who mattered.
Scars render as the material record — ratchet marks as standing stones, cold
hearths at abandonments, a broken line where a hospitality route died — and
they persist in `dig` even for unattested peoples, which is the point: the
mark outlasts the argument about it. Clicking a people opens a **dossier**
(inspection only, §5): population, seasonal round, the eight axes with
salience as band width, the domination tracks, what survives of their record,
and the prose sketch verbatim — the same text the oracle reads when it argues
as them. `window.__dawn` exposes read-only counts, a fractional `seek`, and slot
positions so the page can be checked by a driver rather than by eye.
The §3.4 shot now animates: every element carries a stable slot id, so a
household's winter house and summer tent are one mesh moving. The camp holds
its form for most of the season and strikes in the last third — measured on
seed 3, household d0 of a seasonal people walks ~4 units out to the summer
camps while the lodge scales away, and the same household of the lineage
that ratcheted in year 431 walks 0. The ratchet is legible as an absence,
exactly as specified.
The material world is named and worked: feature names from the record float
as constant-size map labels (the Sholausreach, the Roraismere), water is
flood-filled into bodies so the viewer knows who shares a shore, crossings
between peoples on the same water go by boat rather than on foot — every boat
is somebody's boat — and a jetty marks each waterside people's landing.
**The visual pass (2026-07-18)** took the §2 craft seriously for the first
time. The terrain render mesh is subdivided six ways per cell (283×283,
159k triangles, against 4.4k before) and samples a continuous height field —
bilinear over cell heights plus two noise octaves, admitted only where a
`detailAmp` field allows, which is nowhere in water and nowhere on the bank.
The data grid is untouched; only the sampling of it is finer, because detail
has to live *between* cells to exist at all. Shadows exist at all now (2048
PCFSoft, one ortho box over a fixed world). The ground is painted in two
passes — tint per cell, where the record's resolution and the neighbourhood
vote are, then sampled onto the fine mesh along noise-jittered coordinates
so biome and frontier edges stop following cell boundaries — carrying rock
on slope measured from the coarse surface, a wood's floor under clumped lit
crowns, worn earth normalised against the most-trodden cell, per-vertex
mottle and grain, and a fixed-angle hillshade that does not move with the
sun. 1400 instanced trees in two species with a four-buffer seasonal ramp
that bares the broadleaves in winter. A painted sky dome with sun, moon and
seeded stars, its horizon colour also the fog's, so the land has no seam.
Shores are softened: the last cells of land ramp into the water with a noisy
lip, so the waterline wanders inside the shore cell while *which* cells are
water stays exactly what the record says. A skirt and floor under the world.
Compound built forms from a small geometry forge, with per-face shading
baked at authoring time. Colours are authored in sRGB and converted —
see §7. Rivers are courses rather than hairlines: the segment graph is walked
downhill from the exported elevation, accumulation counted where courses meet,
and width follows its square root, so a river widens only where the record says
two of them joined. They are drawn as ribbons resampled at the render mesh's
frequency, with a meander inside the cell under the §0 elaboration rule — the
same move the shore already makes. On seed 3 the network is genuinely marginal
(24 unit segments; 12 of 34 nodes on the map edge, 9 already under water), so
this reads at valley scale and vanishes at map scale, which is the record's
fact and not the renderer's failure. Still to come: sound.*

**The second visual pass (2026-07-22)** gave the world its hours and its
weather. Night is no longer a dimmer day: every earned hearth, lodge and keep
carries a fire-glow sprite that flickers against the dark, the ember beds
brighten as the light fails, and one smoke column per living settlement —
thinning at night, never rising from an unattested mound — makes habitation
readable from altitude, which was the one thing the map could not say at
distance. The sun's arc now follows the season the record asserts: summer
long and high, winter short, low and pale. `hard_winter`, specified in §1 and
unrendered until now, lands as weather — but the journal's events are
per-culture (a people's wellbeing breaking in the cold), and on seed 3 fully
998 of 1000 winters hit someone, so a storm keyed to any event would have
been permanent. Severity is instead the share of the living hit that season:
past a third of the world hungry, snow falls, the horizon closes in, and the
light goes flat; one camp's bad winter stays their dossier's news. Measured:
359 of 998 winters carry some snow, the median a flurry, peak severity 0.98 —
storms are earned, not ambient. The terrain carries baked occlusion folded
into the hillshade (hollows sit darker at any hour, measured on the coarse
surface under the same rule as slope) and a noisy foam line hugs the
waterline the record asserts. Fireflies work summer nights over wet ground,
one draw call, per-point twinkle in the colour buffer. A **wander mode**
(`w`) walks the world at eye height against the decorated surface — camera
only, §5 untouched; drag steers, the wheel is pace, the world's edge turns
you. The scrubber now shows the history's skeleton (one notch per structural
beat) and eras announce themselves as they turn while the film rolls —
a scrub must not flash its chapter headings. All of it is ambience of the
trees' standing: deterministic from bundle + seed, evidence-free, and the
new systems are instrumented in `window.__dawn` (glows, smoke, snow severity,
wander state) so the page can still be checked by a driver rather than by
eye. Still to come: sound.*

**The third visual pass (2026-07-23)** let the camera travel and gave the
world its hearing. Directed moves are no longer sprung but **flown**: the
old rig's speed was whatever the remaining distance said, and pitch and
distance arrived on their own clocks, so a shot composed piecemeal. A beat
now plans one path — focus, distance and pitch eased on a single clock over
a duration the path length sets (0.9 s at the shortest hop, 3.3 s at the
cut threshold), the altitude arc a function of progress rather than of
distance still to go. Long moves still cut, by the ANNALS rig's rule against
airline tours; a beat landing where the camera already stands does nothing;
and any drag, wheel or walk cancels the flight mid-air, because the
viewer's hand outranks the director's plan (§5). The flight writes the
spring's own state as it goes, so completion and interruption hand over at
the same place with no lurch. **Sound** arrives under the same discipline
as everything else here: ambience of the world's standing, never a score.
Three layers, all of them something already drawn, heard — wind that
strengthens with altitude and with recorded storms (severity opens the
filter, so a hard winter is audible before it is seen), water that swells
slowly where the view nears a shore and is silent inland, hearth-crackle
near a living camp after dark — and nothing else, no melody, no sting on a
beat, because the film quotes its sources and the mix has none. The noise
bed is mulberry32(NSEED), so the same bundle roars the same way; the
crackle pops are hash2 over 90 ms quanta, the fireflies' trick in another
medium; and the mix is measured on the world, throttled to 300 ms — nearest
water cell under the view, nearest lit hearth to the camera — so unattested
mounds, which carry no glow, make no sound either. Off until asked (`s` or
the button): a record should open silent, and the browser would refuse a
gestureless start anyway. The walk takes the keys now, too: WASD drives and
turns while wandering, the letters' other duties (dig, sound, the wander
toggle itself) yielding for the walk's duration — pressing W to go forward
must not leave the world. The flight and the mix are instrumented in
`window.__dawn` (`flying`, `sound`), so both can be checked by a driver
rather than by eye or ear. Nothing remains on the old list.*

**The hook list (2026-07-23).** What a first-time visitor sees, in the order
they see it — each item held to the §0/§5 discipline, ambience of the
record's standing and nothing more:
1. **An opening sequence.** The page now loads paused, overhead, at year 0 —
   the weakest possible first frame. Instead: a held dawn, one slow
   establishing flight over the world under the title card, settling on the
   first settlement, then control handed over with "space to begin".
2. **Clouds.** The dome is painted but empty. Drifting seeded sprites,
   flat-bottomed, lit by the sun's colour, thickening into a grey deck when
   a recorded storm's severity rises — weather you can see coming.
3. **Birds.** Wide shots are still except water. Small deterministic flocks
   over the water bodies at dawn and dusk — evidence-free decoration, the
   fireflies' class.
4. **Wind in the trees.** Vertex sway on the instanced crowns, gusting with
   the same severity that drives snow and the wind sound layer, so a storm
   is visible, audible, and felt as one signal.
5. **Beat cards as illuminated marginalia.** The product *is* a chronicle:
   drop caps, a gold-leaf initial at fusion, redaction strikes in the card's
   own type.
6. **Water polish.** A darker wet band on the shore's last cells; a
   sun-glitter path on the big bodies. Shores are in most frames.
Course: 1 + 2 first (the opening and the sky are the first ten seconds),
then 3 + 4 as one ambient-life pass, 5 + 6 after.

**The fourth visual pass (2026-07-23)** shipped the first four of the hook
list. The page now opens with ceremony: a held dawn (time still paused —
tick 0 is dawn by the clock's own arithmetic), the title centred, and one
slow forced flight from high and wide down to the first hearth the record
holds, sun in frame. Deep links, a reduced-motion preference, or any touch
of the controls skip or end it; no beat may hijack the flight in
(`directorStep` waits out the ceremony); the furniture waits outside until
it lands. The sky gained its furniture: twenty-two cloud sprites off one
shared texture and material (tint is uniform across the sky at any hour),
seeded, drifting on a fixed prevailing wind, greying and thickening into a
deck when a recorded storm's severity rises — the storm you can see coming
is the same signal the snow and the wind sound already carry. Birds ride
the flood-filled water bodies, nine to a flock in a ragged V, only at the
light's edges — a band around dayness 0.32, gone by full day and full
night. And the crowns sway: a vertex patch on the leaf material, phased off
each instance's own translation so the stand never moves as one sheet, the
gust uniform driven by the same severity — §7's instancing hazard respected,
instanceColor set as it always was. Still to come from the list: beat cards
as illuminated marginalia, and the water's wet band and glitter path.*

**The reality list (2026-07-23).** The verdict from a fresh eye: it reads as
a middle-school diorama, not a finished world. The diagnosis, before any
prescription: (1) the camera looks *down* at a model — pitch 0.9 at 1.15
world-widths is god-view of a model railway, and real places are filmed
across, low; (2) no scale cues — trees, houses and mountains are all the
same order of size, where real landscapes hold things much smaller than a
house (stones, scrub) and much bigger than the frame (cloud shadows, haze);
(3) cell-scale flat colour — territory and biome tints are poster-sized
regions of uniform paint, and at wander range the ground is smooth plastic;
(4) the sun strobes — a full day every 8 ticks is one circuit every 1.3 s
at 6 t/s; (5) the trees are 20-face icosahedra on sticks, authored for 800
m and exposed at 0.55 m, where wander's eye height sits inside canopy
height and clips through paper polygons. The plan, phases in order:
1. **Stop lying.** Wander glides around trunks and fades near canopies so a
   clipped face is never seen; visible speed buttons (default 3 t/s) and
   beat dwell — time eases to a third while a card is up; one day = 32
   ticks so golden hours linger.
2. **Scale cues.** Instanced scatter an order smaller than the tents
   (stones, scrub — stumps refused: felling is not in the record); cloud
   shadows riding the cloud wind, each under its cloud; stronger aerial
   perspective; reframed defaults — across the world, not down at it.
3. **Close-range surfaces.** Ground grain at fragment level faded in near
   the camera (the fifth ANNALS technique, previously refused, now
   justified by measured wander flatness); tree rebuild (more blobs,
   detail-1 icosahedra, per-instance squash, trunks sunk); water's wet
   band, glitter path, animated foam.
4. **Light polish.** Contact shadows under structures, softer shadow
   radius.
The constraint holds throughout: procedural, single-file, deterministic —
the manuscript palette stays, but it must chase real scale, real light,
real atmosphere, all of it instrumented in `__dawn` because we verify by
driver, not by eye.

**The reality pass, phases 1–2 (2026-07-23).** Phase 1 stopped the lies.
The walk no longer wears the wood: one spatial hash over tree positions
serves trunk collision (the camera slides around the bole) and canopy
courtesy (a crown within reach shrinks away, re-derived each frame from the
season's own matrices so the winter swap never pops it back) — the answer
to geometry authored for 800 m being met at 0.55 m is not better geometry
but never having to look at it that closely. Time became watchable:
visible −/+ controls beside the readout, the default pace 3 t/s, and beat
dwell — while a card is up, time eases to a third and resumes after, so the
argument on screen can be read before the world moves on (`dwell` is in
`__dawn`). One day now spans 32 ticks; a golden hour lingers long enough
to read as light rather than strobe. Phase 2 laid in the scale cues.
Scatter: instanced stones favouring slope and scrub favouring green, an
order under the structures, seeded, on the record's own land — stumps
refused, because a felled tree asserts logging and the record does not.
Cloud shadows: six of the sprites now darken the ground they cross, draped
over the relief by a patch to the terrain shader (world-space darkening
under six uniforms — the material serves exactly one non-instanced mesh,
the §7 rule kept), each shadow under its cloud, fading with the light that
casts it and broadening when the deck closes: something bigger than the
frame, moving. Aerial perspective: haze now starts at 0.55 world-widths
instead of 1.4 — the far shore is softer than the near one, the dome and
its furniture exempt. And the grammar reframed across rather than down:
default pitch 0.6 at 0.85 widths, every shot's pitch lowered except the
ratchet's plan view, which is the point of it. Still to come from the
list: phase 3 (close-range ground grain, tree rebuild, water's wet band
and glitter) and phase 4 (contact shadows).

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

## 7. Relation to the ANNALS visual brief

The ANNALS craft reference has a companion *visual* brief, and a working
implementation at `github.com/emollick/annals-kingdom`. This section records
what we take from it and what we refuse, so the question does not have to be
re-litigated every time the viewer looks worse than the reference.

**Refused, and refusing is the argument.** Its world is a kingdom: monarch,
treasury, great houses, capital, keeps, armies, caravans, plague, a dragon.
Our record asserts none of those. Rendering them would violate §0 — invention
may decorate what the record is silent about, never add to it. A capital with
a keep, in a run where no lineage ever fused, is a lie about the history.
This also rules out its farmland (rotated fields, hashed crop strips), which
is a large part of why its map reads as inhabited: our record asserts no
agriculture. Likewise its comets, eclipses and red moons — those are omens,
portents that something happened, and nothing did. §5 already refuses
pre-installed statal architecture and battles-as-spectacle; this is the same
refusal continued into the visual layer.

**Adopted wholesale**, being severable craft (§2): baked fixed-angle
hillshade; per-face shading baked at geometry-authoring time; a CSS vignette
over the canvas; a warm-key/cool-fill light pair; fog whose colour is always
the sky's horizon; instanced vegetation with per-instance colour jitter;
depth-tinted water with an analytic swell; a time-of-day gradient dome.

**Where we now depart: water gets a specular term.** The paragraph below is
still the right diagnosis of the *first* gap, but it has an expiry date, and
water is where it expired. Lambert has no specular lobe at all, so the largest
surface in most frames could not catch the sun and read as slate. Water alone
is now `MeshPhongMaterial` (specular `0x9db6c4`, shininess 84), plus a fresnel
that mixes toward `scene.fog.color` — which already *is* the sky's horizon and
is retinted hourly, so it tracks dawn and dusk for free and never disagrees
with the dome. The normals carry a second, finer ripple that the positions do
not: the swell's own slope is ~0.009, flat enough that the highlight would
spread into one featureless sheet, so the extra term stands in for waves below
the mesh's resolution without changing the silhouette that boats sit on.
Everything else stays Lambert; this is one surface, not a move to PBR.

Tuned by A/B on a fixed frame, and the first attempt was wrong in an
instructive way. At fresnel `pow(...,3.0) * 0.62` almost the whole lake sits at
a grazing angle from a low camera, mixes nearly fully into an orange horizon,
and goes brown — physically defensible and still a mistake, because it erases
the shallow-warm/deep-cold depth tint the sheet exists to carry. `pow(...,4.5)
* 0.34` keeps the blue where the water is deep and puts the reflected sky only
where the angle genuinely earns it. When a physical effect and an encoded
signal collide here, the signal wins: the viewer is a record, not a render.

**What the gap actually was.** Not tone mapping, not post-processing, not
PBR — the reference has none of those (r128, Lambert, one render call, no
colour management). It was geometry and shadows: our terrain was 4,418
triangles against its 293,000, and we had no shadows at all. Everything else
was surface treatment applied to a surface that was not there. Two
consequences worth keeping in mind: detail noise evaluated at the data grid's
own frequency is worthless, and any painted feature must be measured for
coverage, since a feature at 90% coverage is a wash and looks identical to a
bug.

**One inherited hazard, now live.** The reference documents that every
`InstancedMesh` sharing a patched material must set `instanceColor`, or the
renderer crashes seed-dependently by draw order. We have an `onBeforeCompile`
material as of the water fresnel above. It is safe *only* because exactly one
non-instanced `Mesh` uses it — reuse `waterMat` on anything instanced and this
becomes a real, draw-order-dependent crash. The same applies if we ever
adopt its `onBeforeCompile` world-space albedo noise — the fifth technique,
still unadopted, and deliberately so: that technique earns its keep on a
surface with no other variation, and our ground already carries two per-vertex
noise fields (mottle at 0.24, grain at 2.9) plus a fixed hillshade. Adding a
third would most likely read as mud. Revisit it only if the ground looks flat
*after* something has been measured, not because the list is unfinished.

**A failure mode worth writing down: geometry that is built and not drawn.**
The river ribbons rendered nothing on first build while every instrument said
they were fine — 288 triangles, `visible: true`, a correct bounding box, no
console error. The quads were wound from each course's own left and right, so
their faces pointed away from the camera and `MeshLambertMaterial` culled them
at `FrontSide`. Nothing counts that. The tell was that a bright red fill at a
half-unit lift with `depthTest: false` changed the frame not at all — when a
diagnostic that loud does nothing, the geometry is not being drawn rather than
being drawn wrong, and winding is the first place to look. `DoubleSide` is the
fix; forcing the normals to `(0,1,0)` is *not*, because DoubleSide flips the
normal on back fragments and the water goes black.
