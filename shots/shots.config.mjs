// The fixed shot list (GAP.md §0). Every shot is reproducible: the harness
// freezes the clock and steps frames by hand, so a given bundle, seek and
// step count always paints the same frame. Coordinates are grid cells for
// the seed-3 bundle (G = 47); a different bundle wants its own list.
//
// pre actions run in order after load and after `look`:
//   wander       — click the wander button (walk starts from the looked-at spot)
//   legend-first — click the legend's first living people (director flies there)
//   storm-seek   — scan winters for the highest severity and seek to it
export const VIEWER = "runs/seed-3/viewer.html";
export const SHOTS = [
  {name: "opening-mid", hash: "", steps: 24,
   note: "0.4 s into the establishing flight, title centred"},
  {name: "opening-landed", hash: "", steps: 560,
   note: "the flight done, the world handed over"},
  // Tick arithmetic for the hours below: one day is 32 ticks (%32 == 0 is
  // dawn, 8 is noon, 24 is full dark) and the season is tick % 4. The first
  // reference set was captured before the per-shot reload fix in capture.mjs,
  // when these hashes were silently ignored — the ticks are now chosen so the
  // frame actually shows what its note claims.
  {name: "valley-dawn", hash: "#t=64", look: [24, 24, 14, 0.45], steps: 40,
   note: "low across the world at first light — %32 == 0, spring"},
  // The one real wood on this map is a diagonal band from (9,38) up to
  // (11,33); the look is solved backwards so the walker starts at its
  // south-west end, at (9, 37.5), heading up the band under the trees.
  {name: "wood-walk", hash: "#t=616", look: [10.7, 34.1, 4, 0.3, 2.03],
   pre: ["wander"], steps: 120,
   note: "eye height in the trees at noon — the fade and collision shot"},
  {name: "night-hearths", hash: "#t=24", pre: ["legend-first"], steps: 260,
   note: "tick % 32 == 24 is full dark; the flight to a hearth lands"},
  {name: "storm", hash: "#t=8", pre: ["storm-seek"], look: [24, 24, 18, 0.5],
   steps: 40,
   note: "the worst recorded winter: snow, deck, flat light"},
  {name: "beat-card", hash: "#t=1720&play", steps: 260,
   note: "year 431's ratchet fires mid-play; card up, camera flown"},
  {name: "dig-wide", hash: "#t=3016&dig", look: [24, 24, 22, 0.6], steps: 20,
   note: "archaeologist mode at noon: mounds where the record is silent"},
];
