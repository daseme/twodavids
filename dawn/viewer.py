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
                         "liberation", "schism", "extinction", "succession")
    ]
    scars_path = run_dir / "scars.jsonl"
    data["scars"] = ([json.loads(l) for l in scars_path.open()]
                     if scars_path.exists() else [])
    return data


BUNDLE_FILES = ("meta.json", "world.json", "journal.jsonl", "chronicle.jsonl",
                "scars.jsonl", "metrics.json")
BUNDLE_VERSION = 1


def write_bundle(run_dir: Path) -> Path:
    """§6.3: zip the run's six files with a version stamp."""
    import zipfile
    out = run_dir / "bundle.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bundle.json", json.dumps(
            {"version": BUNDLE_VERSION, "files": list(BUNDLE_FILES)}))
        for name in BUNDLE_FILES:
            p = run_dir / name
            if p.exists():
                z.write(p, name)
    return out


def write_viewer(run_dir: Path) -> Path:
    template = resources.files("dawn").joinpath("viewer_template.html").read_text()
    vendor = resources.files("dawn").joinpath("vendor")
    # The r178 build is split: three.module.min.js imports ./three.core.min.js.
    # Both are embedded; the template stitches them with blob URLs at load.
    three = vendor.joinpath("three.module.min.js").read_text()
    core = vendor.joinpath("three.core.min.js").read_text()
    # "</" never survives into an inline script: valid JSON either way, and the
    # deliberation texts are model-written free prose.
    payload = json.dumps(build_viewer_data(run_dir)).replace("</", "<\\/")
    out = run_dir / "viewer.html"
    # Placeholder names must not occur in the three.js sources — the core
    # build contains the literal "__THREE__" (its multiple-instance guard).
    out.write_text(template.replace("__THREE_CORE_JS__", core)
                           .replace("__THREE_MODULE_JS__", three)
                           .replace("__DATA__", payload))
    return out
