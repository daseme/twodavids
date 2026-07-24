// capture.mjs — the eye (GAP.md §0). Headless Chromium screenshots of the
// viewer's fixed shot list, deterministic by construction: the page's
// requestAnimationFrame and performance.now are replaced before any app
// code runs, so frames advance only when __step() says so, by a fixed dt.
// Same bundle + same steps = same pixels, which is what makes the compare
// mode (compare.mjs) a diff of the change and not of the weather.
//
// Run: npm run shots   (writes shots/out/<name>.png)
import {chromium} from "playwright";
import {mkdirSync, writeFileSync} from "fs";
import path from "path";
import {fileURLToPath} from "url";
import {VIEWER, SHOTS} from "./shots.config.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "shots", "out");
mkdirSync(outDir, {recursive: true});

// The deterministic clock. Installed before the app boots: rAF callbacks
// queue up instead of running, and __step(n) fires n frames at a fixed dt.
// Everything time-driven in the viewer — water, sway, smoke, flights — is
// a function of this clock, so a stepped frame is a frozen frame.
const CLOCK = `(() => {
  let t = 1000;   // nonzero start, so boot-time prev = now arithmetic is sane
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

// UI chrome animates on wall-clock CSS, which the frozen clock does not
// drive. Snap it: transitions off, and the opening hint held at full
// opacity so the ceremony shot still shows it.
const STILL_CSS = `* { animation: none !important; transition: none !important; }
body.open #beginhint { opacity: 0.85 !important; }`;

const browser = await chromium.launch({args: [
  "--enable-unsafe-swiftshader",   // software WebGL in headless
  "--use-gl=angle", "--use-angle=swiftshader",
]});
const page = await browser.newPage({viewport: {width: 1280, height: 800},
                                    deviceScaleFactor: 1});
page.on("pageerror", e => { console.error("PAGE ERROR:", e.message); });
await page.addInitScript(CLOCK);
// page.screenshot() waits for a requestAnimationFrame our frozen clock will
// never deliver; CDP's captureScreenshot forces a compositor frame instead.
const cdp = await page.context().newCDPSession(page);
const snap = async file =>
  writeFileSync(file, Buffer.from(
    (await cdp.send("Page.captureScreenshot", {format: "png"})).data, "base64"));

const viewerUrl = "file://" + path.join(root, VIEWER);
for (const shot of SHOTS) {
  await page.goto(viewerUrl + shot.hash, {waitUntil: "load"});
  await page.waitForFunction(() => window.__dawn !== undefined);
  await page.addStyleTag({content: STILL_CSS});   // survives goto; reassert
  if (shot.pre?.includes("storm-seek")) {
    const best = await page.evaluate(() => {
      let bt = 0, bs = 0;
      for (let t = 3; t < 4000; t += 40) {
        window.__dawn.seek(t);
        const s = window.__dawn.snow();
        if (s > bs) { bs = s; bt = t; }
      }
      window.__dawn.seek(bt);
      return {bt, bs};
    });
    console.log(`  storm-seek: tick ${best.bt}, severity ${best.bs}`);
  }
  if (shot.look) await page.evaluate(l => window.__dawn.look(...l), shot.look);
  if (shot.pre?.includes("wander")) await page.click("#wander");
  if (shot.pre?.includes("legend-first")) await page.click("#legend .p");
  await page.evaluate(n => window.__step(n), shot.steps);
  const file = path.join(outDir, shot.name + ".png");
  await snap(file);
  console.log(`${shot.name}  (${shot.steps} steps)  ->  ${path.relative(root, file)}`);
}
await browser.close();
console.log("done — compare with: npm run shots:diff");
