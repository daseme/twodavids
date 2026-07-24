"""dawn viewer: the Phase 4 replay viewer (VIEWER.md), scaffold.

A replay client, not a second simulation: one HTML file consuming the run
bundle — journal → pixels, no API calls, no sim logic beyond interpolation.
Three.js is vendored inline (dawn/vendor/), never fetched: "seed + journal =
world, forever" extends to the film of it.

The viewer's data is the watch bundle plus the two things watch omits that
the film needs: deliberations verbatim (the beat cards cite their sources)
and scars with locations (dead routes, abandonments — things the camera can
find). All elaboration — settlement geometry, faces, trees — happens in the
template, deterministically from bundle + seed, and is evidence-free
(VIEWER.md §0, the elaboration rule).
"""

from __future__ import annotations

import html
import json
from importlib import resources
from pathlib import Path

from .journal import read_journal
from .viz import build_watch_data

# Beat-worthy deliberation kinds: the camera flies to arguments (VIEWER.md §4).
# Baseline re-affirmations are ambience, not beats, and are left out.
BEAT_KINDS = ("encounter", "contradiction", "ratchet_crisis", "recovery")


def build_viewer_data(run_dir: Path) -> dict:
    data = build_watch_data(run_dir)
    records = read_journal(run_dir / "journal.jsonl")

    data["deliberations"] = [
        {"tick": r["tick"], "culture": r["culture"], "kind": r["kind"],
         "stance": r["stance"], "speaker": r.get("speaker"),
         "text": r.get("text"), "other": (r.get("detail") or {}).get("other"),
         "model": r.get("model")}
        for r in records
        if r["type"] == "deliberation" and r["kind"] in BEAT_KINDS
    ]
    # Richer event detail than the 2D watch needs: liberation notes, ratchet
    # structures, and successions — the recurring non-event of power dissolving
    # on schedule, which the director films precisely because it is routine.
    data["events2"] = [
        {"tick": r["tick"], "type": r["type"], "culture": r.get("culture"),
         "note": r.get("note"), "mechanism": r.get("mechanism"),
         "structure": r.get("structure"), "displaced": r.get("displaced")}
        for r in records
        if r["type"] in ("ratchet", "hardening", "fusion", "unfusion",
                         "liberation", "schism", "extinction", "succession",
                         "hard_winter")
    ]
    # The margins: every entry as it was written, with its eventual fate —
    # chronicle attrition rendered as ambience (VIEWER.md §4). An entry that
    # will not survive existed at the moment it was made; the film shows it
    # fading. Redaction and survival are facts of the record, not inventions.
    data["margins"] = [
        {"tick": c["tick"], "cid": c["author"], "author": c["author_name"],
         "medium": c["medium"], "text": c["text"], "surviving": c["surviving"],
         "redacted": c.get("redacted", False), "type": c["event_type"]}
        for c in (json.loads(l) for l in (run_dir / "chronicle.jsonl").open())
    ]
    scars_path = run_dir / "scars.jsonl"
    data["scars"] = ([json.loads(l) for l in scars_path.open()]
                     if scars_path.exists() else [])
    return data


BUNDLE_FILES = ("meta.json", "world.json", "journal.jsonl", "chronicle.jsonl",
                "scars.jsonl", "metrics.json")
BUNDLE_VERSION = 1


def write_bundle(run_dir: Path) -> Path:
    """§6.3: zip the run's six files with a version stamp.

    Stored, not deflated: the viewer reads bundles by drag-and-drop with a
    ~30-line zip parser and no vendored inflate. Local disk is cheap; a
    dependency in the twenty-year replay path is not.
    """
    import zipfile
    out = run_dir / "bundle.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        z.writestr("bundle.json", json.dumps(
            {"version": BUNDLE_VERSION, "files": list(BUNDLE_FILES)}))
        for name in BUNDLE_FILES:
            p = run_dir / name
            if p.exists():
                z.write(p, name)
    return out


def _inline_three(core: str, module: str) -> tuple[str, str]:
    """Rewrite the split three.js build into two self-contained module scripts.

    The obvious packaging — import the vendored source from a blob: URL — is
    dead on arrival under a strict Content-Security-Policy, which refuses to
    load blob: as script and leaves a blank page. So the ES module wiring is
    resolved here at build time instead: core publishes its exports on a
    global, and the main build reads them back. Two <script type="module">
    blocks keep the two minified scopes apart, which matters because both
    builds minify their internals to the same short names.
    """
    import re

    def pairs(body: str, sep: str) -> list[tuple[str, str]]:
        out = []
        for item in body.split(","):
            item = item.strip()
            if not item:
                continue
            if " as " in item:
                a, b = item.split(" as ")
                out.append((a.strip(), b.strip()))
            else:
                out.append((item, item))
        return out

    ce = re.search(r"export\{([^}]*)\}\s*;?\s*$", core.strip())
    mi = re.search(r'import\{([^}]*)\}from"\./three\.core\.min\.js";', module)
    if not (ce and mi):
        raise RuntimeError("vendored three.js layout changed; rewrite _inline_three")
    # core: `local as Exported` -> {Exported: local}
    core_map = ", ".join(f"{ex}:{loc}" for loc, ex in pairs(ce.group(1), " as "))
    core_js = core[:core.rstrip().rfind("export{")] + \
        f"window.__THREE_CORE={{{core_map}}};"

    # module: `Exported as local` -> const {Exported: local} = core
    imp = ", ".join(f"{ex}:{loc}" for ex, loc in pairs(mi.group(1), " as "))
    module_js = module.replace(mi.group(0), f"const {{{imp}}}=window.__THREE_CORE;", 1)

    # The build re-exports a slice of core verbatim — `export{...}from
    # "./three.core.min.js"` — before exporting its own names. Those
    # re-exported names live in core's scope, not this one, so the statement
    # is dropped whole (its `from` clause included, or a dangling clause is
    # left behind) and the names arrive instead by spreading core below.
    module_js = re.sub(r'export\{[^}]*\}from"\./three\.core\.min\.js";',
                       "", module_js)
    local = re.search(r"export\{([^}]*)\};?\s*$", module_js.strip())
    if not local:
        raise RuntimeError("vendored three.js layout changed; rewrite _inline_three")
    module_js = module_js[:module_js.rstrip().rfind("export{")]
    names = ",".join(f"{ex}:{loc}" for loc, ex in pairs(local.group(1), " as "))
    module_js += f"window.THREE={{...window.__THREE_CORE,{names}}};"
    return core_js, module_js


def write_viewer(run_dir: Path) -> Path:
    template = resources.files("dawn").joinpath("viewer_template.html").read_text()
    vendor = resources.files("dawn").joinpath("vendor")
    # The r178 build is split: three.module.min.js imports ./three.core.min.js.
    # Both are embedded, their module wiring resolved here in _inline_three.
    core, three = _inline_three(
        vendor.joinpath("three.core.min.js").read_text(),
        vendor.joinpath("three.module.min.js").read_text())
    # The post chain (GAP §1) is pre-wired offline by dawn/vendor/build-post.mjs
    # into a single script that reads window.THREE and publishes window.__POST.
    post = vendor.joinpath("post.js").read_text()
    # "</" never survives into an inline script: valid JSON either way, and the
    # deliberation texts are model-written free prose.
    payload = json.dumps(build_viewer_data(run_dir)).replace("</", "<\\/")
    out = run_dir / "viewer.html"
    # Placeholder names must not occur in the three.js sources — the core
    # build contains the literal "__THREE__" (its multiple-instance guard).
    # The run name goes in first, while the string is still only the template:
    # after the vendored sources land there is a megabyte of minified JS for a
    # short placeholder to collide with.
    out.write_text(template.replace("__RUN__", html.escape(run_dir.name))
                           .replace("__POST_JS__", post)
                           .replace("__THREE_CORE_JS__", core)
                           .replace("__THREE_MODULE_JS__", three)
                           .replace("__DATA__", payload))
    return out
