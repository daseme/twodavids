// look.mjs — one deterministic frame from anywhere, for grading loops that
// need an angle the shot list doesn't have. Same frozen clock as capture.mjs.
// Run: node shots/look.mjs <out.png> <hash> <x> <z> <dist> <pitch> <yaw> [steps]
//   e.g. node shots/look.mjs shots/edge/wood.png "#t=64" 10.7 34.1 6 0.5 2.0 90
import {chromium} from "playwright";
import {writeFileSync} from "fs";
import path from "path";
import {fileURLToPath} from "url";
import {VIEWER} from "./shots.config.mjs";

const [out, hash, x, z, dist, pitch, yaw, steps = "90"] = process.argv.slice(2);
if (!out) { console.error("usage: look.mjs <out.png> <hash> <x> <z> <dist> <pitch> <yaw> [steps]"); process.exit(1); }
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

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

const browser = await chromium.launch({args: [
  "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader",
]});
const page = await browser.newPage({viewport: {width: 1280, height: 800},
                                    deviceScaleFactor: 1});
page.on("pageerror", e => console.error("PAGE ERROR:", e.message));
await page.addInitScript(CLOCK);
const cdp = await page.context().newCDPSession(page);
await page.goto("file://" + path.join(root, VIEWER) + (hash || ""), {waitUntil: "load"});
await page.waitForFunction(() => window.__dawn !== undefined);
await page.addStyleTag({content:
  "* { animation: none !important; transition: none !important; }"});
await page.evaluate(a => window.__dawn.look(...a),
                    [+x, +z, +dist, +pitch, +yaw]);
await page.evaluate(() => window.__step(1));
await page.evaluate(n => window.__step(n), +steps);
writeFileSync(out, Buffer.from(
  (await cdp.send("Page.captureScreenshot", {format: "png"})).data, "base64"));
console.log(`-> ${out}`);
await browser.close();
