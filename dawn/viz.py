"""dawn viz: build a self-contained HTML report from a run directory.

Reads only the run's own files (meta, journal, chronicle, scars, metrics,
world snapshot). Run directories from before world.json existed are
reconstructed via replay — seed + journal = world, so no data is ever lost.
"""

from __future__ import annotations

import json
from collections import Counter
from importlib import resources
from pathlib import Path

import numpy as np

from . import values as V
from .journal import read_journal
from .params import Params


def world_snapshot(world) -> dict:
    """The map and roster at the moment of writing, as plain JSON."""
    from .repertoire import STRUCTURES
    glosses, configs = {}, {}
    for c in world.cultures.values():
        for e in c.repertoire.elements.values():
            if e.kind == "configuration":
                glosses[e.eid] = e.gloss
                configs[e.eid] = {"gloss": e.gloss, "seasons": list(e.seasons),
                                  "ratcheted": e.ratcheted}
    structures = {sid: {"authority": s.authority, "pooling": s.pooling,
                        "settlement": s.settlement, "roles": sorted(s.roles)}
                  for sid, s in STRUCTURES.items()}
    return {
        "grid": world.params.grid,
        "biome": world.biome.astype(int).tolist(),
        "owner": world.owner.astype(int).tolist(),
        # Elevation ships in mils for rendering relief; it never drives culture.
        "elevation": (np.asarray(world.elevation) * 1000).astype(int).tolist()
                     if world.elevation is not None else None,
        "water": world.water.astype(int).tolist() if world.water is not None else None,
        "rivers": world.river_segments,
        "features": world.features,
        "home": {str(k): v for k, v in world.home_feature.items()},
        "glosses": glosses,
        "configs": configs,        # eid -> season->structure map (VIEWER.md §1.2)
        "structures": structures,  # structure id -> authority/pooling/settlement/roles
        "cultures": {str(c.cid): {"name": c.name, "pop": round(c.pop),
                                  "alive": c.alive, "switching": c.is_switching(),
                                  "fused": c.fused}
                     for c in world.cultures.values()},
    }


def _ensure_world_json(run_dir: Path, meta: dict, records: list[dict]) -> dict:
    path = run_dir / "world.json"
    if path.exists():
        snap = json.loads(path.read_text())
        # "water" may be absent on runs from before hydrology existed; such
        # worlds cannot be reconstructed under the new worldgen (their journal
        # belongs to the old world), so we take the snapshot as-is.
        if "owner0" in snap and snap.get("elevation") is not None:
            return snap
    # Older run dir: rebuild the world from its own journal. Slow but exact.
    print("world snapshot missing or pre-territory-history — "
          "reconstructing via replay (seed + journal = world)…")
    from .engine import Engine
    from .oracle import ReplayOracle
    oracle = ReplayOracle(records)
    oracle.model_id = meta["model"]
    eng = Engine(meta["seed"], Params(**meta["params"]), oracle=oracle)
    eng.run(meta["ticks"])
    snap = world_snapshot(eng.world)
    snap["owner0"] = eng.owner0.astype(int).tolist()
    snap["deltas"] = eng.territory_deltas
    path.write_text(json.dumps(snap, default=int))
    return snap


def build_viz_data(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text())
    records = read_journal(run_dir / "journal.jsonl")
    world = _ensure_world_json(run_dir, meta, records)
    metrics = json.loads((run_dir / "metrics.json").read_text())
    chron = [json.loads(l) for l in (run_dir / "chronicle.jsonl").open()]
    scars = [json.loads(l) for l in (run_dir / "scars.jsonl").open()]

    sums = [r for r in records if r["type"] == "tick_summary"]
    events = [{"tick": r["tick"], "type": r["type"], "culture": r.get("culture")}
              for r in records
              if r["type"] in ("ratchet", "fusion", "unfusion", "liberation",
                               "schism", "hardening")]

    # The featured people: most fusions; failing that, highest final domination.
    fus = Counter(r["culture"] for r in records if r["type"] == "fusion")
    if fus:
        star = fus.most_common(1)[0][0]
    elif sums and sums[-1]["cultures"]:
        star = int(max(sums[-1]["cultures"],
                       key=lambda k: sum(sums[-1]["cultures"][k]["domination"])))
    else:
        star = None
    star_data = None
    if star is not None:
        series = [{"tick": s["tick"],
                   "dom": (s["cultures"].get(str(star)) or {}).get("domination")}
                  for s in sums]
        star_data = {"cid": star, "name": world["cultures"][str(star)]["name"],
                     "fusions": fus.get(star, 0), "series": series}

    surviving = [c for c in chron if c["surviving"]]
    picks, seen = [], set()
    for et in ("ratchet", "fusion", "unfusion", "liberation", "hardening", "schism"):
        for c in surviving:
            if c["event_type"] == et and et not in seen:
                picks.append(c)
                seen.add(et)
                break

    return {
        "seed": meta["seed"], "ticks": meta["ticks"],
        "grid": world["grid"], "biome": world["biome"], "owner": world["owner"],
        "cultures": world["cultures"],
        "star": star_data,
        "pop_series": [{"tick": s["tick"],
                        "pop": sum(c["pop"] for c in s["cultures"].values()),
                        "n": len(s["cultures"])} for s in sums],
        "events": events,
        "chronicle_picks": picks,
        "scars": scars[:10],
        "n_entries": len(chron), "n_surviving": len(surviving),
        "metrics": metrics,
    }


def write_report(run_dir: Path) -> Path:
    template = resources.files("dawn").joinpath("viz_template.html").read_text()
    data = build_viz_data(run_dir)
    out = run_dir / "report.html"
    out.write_text(template.replace("__DATA__", json.dumps(data)))
    return out


# --- watch mode: the world unfolding in time -----------------------------------

WATCH_EVENT_TYPES = ("ratchet", "hardening", "fusion", "unfusion", "liberation",
                     "schism", "extinction")


def build_watch_data(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text())
    records = read_journal(run_dir / "journal.jsonl")
    world = _ensure_world_json(run_dir, meta, records)
    chron = [json.loads(l) for l in (run_dir / "chronicle.jsonl").open()]

    sums = [r for r in records if r["type"] == "tick_summary"]
    summaries = [{"tick": s["tick"],
                  "c": {cid: {"pop": round(c["pop"]), "fused": c.get("fused", False),
                              "switching": c.get("switching", True),
                              "dom": [round(float(x), 3) for x in c["domination"]],
                              "mean": [round(float(x), 2) for x in c["mean"]],
                              "sal": [round(float(x), 2) for x in c["salience"]]
                                     if "salience" in c else None,
                              "fx": c.get("factions"),
                              "cfg": c.get("dominant")}
                        for cid, c in s["cultures"].items()}}
                 for s in sums]

    # Per-era prose sketches: the same numeric->linguistic boundary the oracle
    # sees, so the dossier describes a people the way the sim itself would.
    era_ticks = meta["params"]["era_ticks"]
    sketches: dict[str, dict[str, str]] = {}
    for s in summaries:
        era = str(s["tick"] // era_ticks)
        if era not in sketches:
            sketches[era] = {cid: V.sketch(np.array(c["mean"]))
                             for cid, c in s["c"].items()}

    events = [{"tick": r["tick"], "type": r["type"], "culture": r.get("culture"),
               "new": r.get("new")}
              for r in records if r["type"] in WATCH_EVENT_TYPES]

    # Splits get their pulses from events; sutures are the flows: defections
    # (people crossing) and feasts (the exchange edge). Defections are frequent,
    # so aggregate them to the summary cadence.
    frame = 20
    flows: dict[tuple[int, int, int], int] = {}
    for r in records:
        if r["type"] == "defection" and r.get("to") is not None:
            k = (r["tick"] // frame * frame, r["culture"], r["to"])
            flows[k] = flows.get(k, 0) + 1
    feasts = [{"tick": r["tick"], "a": r["culture"], "b": r["other"]}
              for r in records if r["type"] == "feast" and r.get("other") is not None]

    # The ticker speaks in the world's own chronicle voice where an entry exists
    # (even entries later lost to attrition existed at the moment they were made).
    chron_keyed = [{"tick": c["tick"], "type": c["event_type"],
                    "author": c["author_name"], "medium": c["medium"],
                    "text": c["text"]}
                   for c in chron if c["event_type"] in WATCH_EVENT_TYPES]

    return {
        "seed": meta["seed"], "ticks": meta["ticks"], "grid": world["grid"],
        "biome": world["biome"], "owner0": world["owner0"],
        "elevation": world.get("elevation"),
        "water": world.get("water"),
        "rivers": world.get("rivers", []),
        "features": world.get("features", []),
        "home": world.get("home", {}),
        "glosses": world.get("glosses", {}),
        "configs": world.get("configs", {}),
        "structures": world.get("structures", {}),
        "deltas": world.get("deltas", []),
        "cultures": world["cultures"],
        "summaries": summaries,
        "era_ticks": era_ticks,
        "sketches": sketches,
        "axes": [[p, n] for p, n in zip(V.POS, V.NEG)],
        "events": events,
        "flows": [{"tick": t, "from": a, "to": b, "n": n}
                  for (t, a, b), n in sorted(flows.items())],
        "feasts": feasts,
        "chronicle": chron_keyed,
    }


def write_watch(run_dir: Path) -> Path:
    template = resources.files("dawn").joinpath("watch_template.html").read_text()
    data = build_watch_data(run_dir)
    out = run_dir / "watch.html"
    out.write_text(template.replace("__DATA__", json.dumps(data)))
    return out
