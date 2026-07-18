"""Phase 3 experiment: promoted-vs-stub, the diff that is the finding.

Two run directories of the same seed — one stub, one with the model's stances
live — are exactly comparable because both are deterministic given seed +
journal. This reports where the histories diverge: stance distributions on the
promoted deliberation kinds, liberation rates and mechanisms, ratchet and
fusion counts, and the first tick at which the two worlds part.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def _load(run_dir: Path) -> dict:
    recs = [json.loads(l) for l in (run_dir / "journal.jsonl").open()]
    meta = json.loads((run_dir / "meta.json").read_text())
    metrics = json.loads((run_dir / "metrics.json").read_text())
    return {"recs": recs, "meta": meta, "metrics": metrics}


def _stance_dist(recs: list[dict], kinds: set[str], live_only: bool) -> Counter:
    c = Counter()
    for r in recs:
        if r["type"] != "deliberation" or r["kind"] not in kinds:
            continue
        if live_only and not r["model"].startswith(("claude", "fake")):
            continue
        c[r["stance"]] += 1
    return c


def _first_divergence(a: list[dict], b: list[dict]) -> int | None:
    """First tick where the two journals' event streams differ in shape."""
    def sig(recs):
        by_tick: dict[int, list] = {}
        for r in recs:
            if r["type"] in ("deliberation", "tick_summary", "genesis"):
                continue
            by_tick.setdefault(r.get("tick", -1), []).append(
                (r["type"], r.get("culture")))
        return {t: sorted(map(str, v)) for t, v in by_tick.items()}
    sa, sb = sig(a), sig(b)
    for t in sorted(set(sa) | set(sb)):
        if sa.get(t) != sb.get(t):
            return t
    return None


def compare(stub_dir: Path, model_dir: Path) -> dict:
    S, M = _load(stub_dir), _load(model_dir)
    promoted = {r["kind"] for r in M["recs"]
                if r["type"] == "deliberation" and r["model"].startswith(("claude", "fake"))}

    def counts(recs, typ):
        return sum(1 for r in recs if r["type"] == typ)

    lib_s = [r for r in S["recs"] if r["type"] == "liberation"]
    lib_m = [r for r in M["recs"] if r["type"] == "liberation"]

    out = {
        "seed": M["meta"]["seed"], "ticks": M["meta"]["ticks"],
        "model": M["meta"]["model"],
        "promoted_kinds": sorted(promoted),
        "stance_distribution_on_promoted_kinds": {
            "stub": dict(_stance_dist(S["recs"], promoted, live_only=False).most_common()),
            "model": dict(_stance_dist(M["recs"], promoted, live_only=True).most_common()),
        },
        "liberations": {
            "stub": {"count": len(lib_s),
                     "mechanisms": dict(Counter(r["mechanism"] for r in lib_s))},
            "model": {"count": len(lib_m),
                      "mechanisms": dict(Counter(r["mechanism"] for r in lib_m))},
        },
        "counts": {
            k: {"stub": counts(S["recs"], k), "model": counts(M["recs"], k)}
            for k in ("ratchet", "hardening", "fusion", "unfusion", "schism", "extinction")
        },
        "acceptance": {
            "stub": S["metrics"].get("all_pass"),
            "model": M["metrics"].get("all_pass"),
        },
        "living_at_close": {
            "stub": S["metrics"]["sanity_bounds"]["living"],
            "model": M["metrics"]["sanity_bounds"]["living"],
        },
        "first_divergence_tick": _first_divergence(S["recs"], M["recs"]),
    }
    return out


def format_report(cmp: dict) -> str:
    L = []
    L.append(f"# Promoted vs stub — seed {cmp['seed']}, {cmp['ticks']} ticks, {cmp['model']}\n")
    div = cmp["first_divergence_tick"]
    L.append(f"The histories first diverge at "
             + (f"tick {div} (year {div // 4})." if div is not None
                else "no point — identical event shape.") + "\n")
    L.append("## Stance choice on promoted deliberations "
             f"({', '.join(cmp['promoted_kinds'])})\n")
    sd = cmp["stance_distribution_on_promoted_kinds"]
    keys = sorted(set(sd["stub"]) | set(sd["model"]),
                  key=lambda k: -(sd["stub"].get(k, 0) + sd["model"].get(k, 0)))
    L.append("| stance | stub | model |\n|---|---:|---:|")
    for k in keys:
        L.append(f"| {k} | {sd['stub'].get(k, 0)} | {sd['model'].get(k, 0)} |")
    L.append("")
    lib = cmp["liberations"]
    L.append(f"## Liberations\n")
    L.append(f"- stub: {lib['stub']['count']} — {lib['stub']['mechanisms']}")
    L.append(f"- model: {lib['model']['count']} — {lib['model']['mechanisms']}\n")
    L.append("## Structural events\n")
    L.append("| event | stub | model |\n|---|---:|---:|")
    for k, v in cmp["counts"].items():
        L.append(f"| {k} | {v['stub']} | {v['model']} |")
    L.append(f"\nAcceptance — stub: {cmp['acceptance']['stub']}, "
             f"model: {cmp['acceptance']['model']}. "
             f"Living at close — stub {cmp['living_at_close']['stub']}, "
             f"model {cmp['living_at_close']['model']}.\n")
    return "\n".join(L)
