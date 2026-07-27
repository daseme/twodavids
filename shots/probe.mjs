// probe.mjs — boot the viewer headless, step a few frames, print a __dawn
// probe result. Usage: node probe.mjs <expr> [hash]
//   e.g. node probe.mjs "window.__dawn.trees()" "#t=72"
import {chromium} from "playwright";
const [expr, hash = ""] = process.argv.slice(2);
const browser = await chromium.launch({args: [
  "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader"]});
const page = await browser.newPage({viewport: {width: 640, height: 400}});
page.on("pageerror", e => console.error("PAGE ERROR:", e.message));
await page.addInitScript(`(() => {
  let t = 1000; const q = [];
  window.requestAnimationFrame = cb => (q.push(cb), q.length);
  window.cancelAnimationFrame = () => {};
  window.performance.now = () => t;
  window.__step = (n=1) => { for (let i=0;i<n;i++){ t+=16.7;
    const b=q.splice(0,q.length); for (const cb of b) cb(t);} };
})();`);
await page.goto("file:///home/daseme/ko/twodavids/runs/seed-3/viewer.html" + hash,
                {waitUntil: "load"});
await page.waitForFunction(() => window.__dawn !== undefined);
await page.evaluate(() => window.__step(30));
console.log(JSON.stringify(await page.evaluate(expr), null, 1));
await browser.close();
