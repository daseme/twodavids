// compare.mjs — the diff loop. Each shot in shots/out is compared against
// the committed reference in shots/ref with pixelmatch. Because captures
// are deterministic (see capture.mjs), any difference is the change you
// just made — review it, and if it is the change you wanted, accept it:
//   npm run shots:accept
// Fails (exit 1) when any shot differs beyond its allowance, and writes
// shots/diff/<name>.png showing where. (Diffs live outside shots/out so
// shots:accept's `cp out/*.png ref/` can never promote a diff image to a
// reference.)
import {PNG} from "pngjs";
import pixelmatch from "pixelmatch";
import {existsSync, readFileSync, writeFileSync, readdirSync, mkdirSync} from "fs";
import path from "path";
import {fileURLToPath} from "url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "shots", "out");
const refDir = path.join(root, "shots", "ref");
const diffDir = path.join(root, "shots", "diff");
mkdirSync(diffDir, {recursive: true});
// Fraction of pixels allowed to differ before a shot fails. Deterministic
// captures should be at 0; the small allowance covers font rasterisation.
const ALLOW = 0.002;

let failed = 0;
for (const file of readdirSync(refDir).filter(f => f.endsWith(".png"))) {
  const out = path.join(outDir, file), ref = path.join(refDir, file);
  if (!existsSync(out)) { console.log(`MISSING  ${file} (not captured)`); failed++; continue; }
  const a = PNG.sync.read(readFileSync(out)), b = PNG.sync.read(readFileSync(ref));
  if (a.width !== b.width || a.height !== b.height) {
    console.log(`SIZE     ${file}: ${a.width}x${a.height} vs ref ${b.width}x${b.height}`);
    failed++; continue;
  }
  const diff = new PNG({width: a.width, height: a.height});
  const n = pixelmatch(a.data, b.data, diff.data, a.width, a.height,
                       {threshold: 0.12});
  const frac = n / (a.width * a.height);
  const mark = frac > ALLOW ? "DIFF" : "ok";
  if (frac > ALLOW) {
    writeFileSync(path.join(diffDir, file), PNG.sync.write(diff));
    failed++;
  }
  console.log(`${mark.padEnd(8)} ${file}  ${(frac * 100).toFixed(3)}% of pixels`);
}
// A capture with no reference is a new shot waiting to be accepted — say so
// rather than letting it pass silently.
const refNames = new Set(readdirSync(refDir).filter(f => f.endsWith(".png")));
for (const file of readdirSync(outDir).filter(f => f.endsWith(".png")))
  if (!refNames.has(file)) console.log(`NEW      ${file} (no reference — npm run shots:accept to adopt)`);
if (!refNames.size) console.log("no references yet — run: npm run shots && npm run shots:accept");
console.log(failed ? `\n${failed} shot(s) differ — review shots/diff/*.png` : "\nall shots match");
process.exit(failed ? 1 : 0);
