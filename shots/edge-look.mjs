// edge-look.mjs — an ad-hoc grading eye for GAP §3 (not part of the shot
// list). Finds a gentle shore by probing __dawn.surfaceY, then captures the
// water's edge close up at a few clock phases so the lap's travel is
// visible as a sequence. Same frozen clock as capture.mjs.
// Run: node shots/edge-look.mjs [outdir]
import {chromium} from "playwright";
import {mkdirSync, writeFileSync} from "fs";
import path from "path";
import {fileURLToPath} from "url";
import {VIEWER} from "./shots.config.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.argv[2] || path.join(root, "shots", "edge");
mkdirSync(outDir, {recursive: true});

const CLOCK = `(() => {
  let t = 1000;
  const q = [];
  window.requestAnimationFrame = cb => (q.push(cb), q.length);
  window.cancelAnimationFrame = () => {};
  window.performance.now = () => t;
  window.__step = (n = 1, dt = 50 / 3) => {
    for (let i = 0; i < n; i++) {
      t += dt;
      const batch = q.splice(0, q.length);
      for (const cb of batch) cb(t);
    }
  };
})();`;
const STILL_CSS = `* { animation: none !important; transition: none !important; }
#hud, #legend, #beats, #titlecard, #hint, #controls { display: none !important; }`;

const browser = await chromium.launch({args: [
  "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader",
]});
const page = await browser.newPage({viewport: {width: 1280, height: 800},
                                    deviceScaleFactor: 1});
page.on("pageerror", e => console.error("PAGE ERROR:", e.message));
await page.addInitScript(CLOCK);
const cdp = await page.context().newCDPSession(page);
const snap = async file =>
  writeFileSync(file, Buffer.from(
    (await cdp.send("Page.captureScreenshot", {format: "png"})).data, "base64"));

const capture = async (hash, label) => {
  await page.goto("about:blank");
  await page.goto("file://" + path.join(root, VIEWER) + hash, {waitUntil: "load"});
  await page.waitForFunction(() => window.__dawn !== undefined);
  await page.addStyleTag({content: STILL_CSS});
  // Probe for gentle shores: land just above the waterline whose seaward
  // neighbour is under it, with a shallow drop — the graded-foam case.
  const spots = await page.evaluate(() => {
    const out = [];
    for (let gx = 2; gx < 45; gx += 0.5) for (let gz = 2; gz < 45; gz += 0.5) {
      const wx = gx - 23.5, wz = gz - 23.5;
      const h = window.__dawn.surfaceY(wx, wz);
      if (h < 0.01 || h > 0.06) continue;
      let deep = 0, gentle = false, dir = null;
      for (const [dx, dz] of [[1.5, 0], [-1.5, 0], [0, 1.5], [0, -1.5]]) {
        const hn = window.__dawn.surfaceY(wx + dx, wz + dz);
        if (hn < -0.15) { deep++; if (hn > -0.45) { gentle = true; dir = [dx, dz]; } }
      }
      if (deep >= 2 && dir) out.push({gx, gz, h, gentle, dir});
    }
    return out;
  });
  const pick = spots.filter(s => s.gentle);
  const list = pick.length ? pick : spots;
  const spot = list[Math.floor(list.length / 2)];
  console.log(`${label}: ${spots.length} shore probes, ${pick.length} gentle; ` +
              `looking at (${spot.gx}, ${spot.gz}) toward [${spot.dir}]`);
  // Low, close, and from the land side looking out over the water: the
  // camera sits at focus + (cos yaw, sin yaw) * dist, so the yaw that puts
  // it opposite the deep-water direction is atan2(-dz, -dx).
  const yaw = Math.atan2(-spot.dir[1], -spot.dir[0]);
  await page.evaluate(a => window.__dawn.look(...a),
                      [spot.gx, spot.gz, 6, 0.42, yaw]);
  await page.evaluate(() => window.__step(1));
  // Four frames ~2s apart: the lap period is ~7.9s, so the sequence shows
  // the second line at four points of its travel.
  for (let k = 0; k < 4; k++) {
    await page.evaluate(() => window.__step(120));   // 120 * 16.7ms = 2s
    const file = path.join(outDir, `${label}-p${k}.png`);
    await snap(file);
    console.log(`  -> ${path.relative(root, file)}`);
  }
  // Overhead over the shallows: the angle where the fresnel lets go of the
  // sky and the bed shows — the caustics' frame.
  await page.evaluate(a => window.__dawn.look(...a),
                      [spot.gx + spot.dir[0] * 0.7, spot.gz + spot.dir[1] * 0.7,
                       4.5, 1.25, yaw]);
  await page.evaluate(() => window.__step(60));
  const file = path.join(outDir, `${label}-top.png`);
  await snap(file);
  console.log(`  -> ${path.relative(root, file)}`);
};

await capture("#t=72", "noon");   // %32 == 8: caustics under full light
await capture("#t=64", "dawn");   // %32 == 0: the foam against low light
await browser.close();
console.log("done");
