"""CLI: run loop, almanac compiler, acceptance suite, replay verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .almanac import compile_almanac
from .engine import Engine
from .journal import read_journal
from .metrics import evaluate
from .oracle import ReplayOracle
from .params import Params


def cmd_run(args: argparse.Namespace) -> None:
    out = Path(args.out or f"runs/seed-{args.seed}")
    out.mkdir(parents=True, exist_ok=True)
    eng = Engine(args.seed, Params(), out_dir=out)
    print(f"world of seed {args.seed}: "
          + ", ".join(c.name for c in eng.world.living()))
    eng.run(args.ticks, progress=True)
    (out / "ALMANAC.md").write_text(compile_almanac(out))
    print(f"done: {args.ticks} ticks, {len(eng.world.living())} living cultures, "
          f"{sum(1 for e in eng.chronicle.entries if e.surviving)} surviving chronicle entries")
    print(f"outputs in {out}/ (journal.jsonl, chronicle.jsonl, ALMANAC.md, metrics.json)")
    print(f"visual report: dawn viz {out}")


def cmd_viz(args: argparse.Namespace) -> None:
    from .viz import write_report
    out = write_report(Path(args.run_dir))
    print(f"report written to {out}")
    print("open it in a browser — it is fully self-contained.")


def cmd_watch(args: argparse.Namespace) -> None:
    from .viz import write_watch
    out = write_watch(Path(args.run_dir))
    print(f"watch page written to {out}")
    print("open it in a browser and press play — the world unfolds; "
          "space pauses, arrows step by year.")


def cmd_narrate(args: argparse.Namespace) -> None:
    """Phase 2: the model writes the chronicle's prose; history does not move."""
    from .prose import build_requests, narrate
    run_dir = Path(args.run_dir)
    if not args.go:
        _, stats = build_requests(run_dir, args.limit)
        print("dry run — no API calls made")
        print(json.dumps(stats, indent=2))
        print("re-run with --go to submit the batch (uses ANTHROPIC_API_KEY "
              "or an `ant auth login` profile)")
        return
    if args.mock:
        from .providers import MockProvider
        provider = MockProvider()
    else:
        from .providers import AnthropicBatchProvider
        provider = AnthropicBatchProvider()
    result = narrate(run_dir, provider, args.limit)
    print(json.dumps(result, indent=2))


def cmd_almanac(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    text = compile_almanac(run_dir)
    (run_dir / "ALMANAC.md").write_text(text)
    print(text)


def _parse_overrides(pairs: list[str]) -> dict:
    """--set beta_ideology=0.6 → {"beta_ideology": 0.6}, typed from the default."""
    defaults = Params()
    out = {}
    for pair in pairs or []:
        k, _, v = pair.partition("=")
        if not hasattr(defaults, k):
            raise SystemExit(f"unknown parameter: {k}")
        out[k] = type(getattr(defaults, k))(v)
    return out


def _accept_one(job: tuple[int, int, dict]) -> tuple[int, dict]:
    seed, ticks, overrides = job
    eng = Engine(seed, Params(**overrides))
    eng.run(ticks)
    return seed, evaluate(eng)


def cmd_accept(args: argparse.Namespace) -> None:
    """Run the §5 acceptance suite across seeds; aggregate honestly."""
    overrides = _parse_overrides(args.set)
    if overrides:
        print(f"parameter overrides: {overrides}")
    jobs = [(seed, args.ticks, overrides)
            for seed in range(args.start_seed, args.start_seed + args.seeds)]
    if args.jobs > 1:
        import multiprocessing as mp
        with mp.Pool(args.jobs) as pool:
            results = pool.map(_accept_one, jobs)
    else:
        results = [_accept_one(j) for j in jobs]
    verbose = args.seeds <= 8
    for seed, checks in results:
        status = "PASS" if checks["all_pass"] else "FAIL"
        if not verbose:
            fails = [k for k, v in checks.items() if isinstance(v, dict) and not v["pass"]]
            print(f"seed {seed}: {status}" + (f"  ({', '.join(fails)})" if fails else ""))
            continue
        print(f"\nseed {seed}: {status}")
        for name, c in checks.items():
            if not isinstance(c, dict):
                continue
            mark = "ok " if c["pass"] else "FAIL"
            detail = {k: v for k, v in c.items() if k != "pass"}
            print(f"  [{mark}] {name}: {json.dumps(detail)}")
    # Cross-run criteria: 'occasionally a fused polity later unfuses' is a
    # property of the ensemble, not of every single history.
    fusions = sum(r["fusion_contingent"]["fusions"] for _, r in results)
    unfusions = sum(r["fusion_contingent"]["unfusions"] for _, r in results)
    print(f"\nensemble: {fusions} fusions, {unfusions} unfusions across "
          f"{args.seeds} worlds "
          + ("(reversibility demonstrated)" if unfusions else
             "(no unfusion observed — acceptable only if fusions are also rare)"))
    passed = sum(1 for _, r in results if r["all_pass"])
    print(f"{passed}/{args.seeds} worlds pass all per-run criteria")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"ticks": args.ticks, "overrides": overrides,
             "results": {s: r for s, r in results}}, indent=2))
        print(f"results written to {args.json}")


def cmd_replay(args: argparse.Namespace) -> None:
    """Seed + journal = world: re-run reading stances from the journal, compare."""
    run_dir = Path(args.run_dir)
    meta = json.loads((run_dir / "meta.json").read_text())
    original = read_journal(run_dir / "journal.jsonl")
    oracle = ReplayOracle(original)
    oracle.model_id = meta["model"]  # the journal speaks with the original model's voice
    eng = Engine(meta["seed"], Params(**meta["params"]), oracle=oracle)
    eng.run(meta["ticks"])
    import hashlib
    h = hashlib.sha256()
    for rec in original:
        h.update(json.dumps(rec, sort_keys=True).encode())
    ok = eng.journal.content_hash() == h.hexdigest()
    print("replay:", "IDENTICAL — seed + journal = world" if ok
          else "DIVERGED — reproducibility is broken, treat as a P0 bug")
    raise SystemExit(0 if ok else 1)


def _load_dotenv() -> None:
    """Load vars from ./.env if present (untracked; the key never enters the repo)."""
    import os
    p = Path(".env")
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.removeprefix("export ").strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def main() -> None:
    _load_dotenv()
    ap = argparse.ArgumentParser(prog="dawn",
                                 description="The Dawn of Everything as a procedurally generated world")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="generate a world-history")
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--ticks", type=int, default=4000, help="seasons (~50 generations)")
    r.add_argument("--out", type=str, default=None)
    r.set_defaults(fn=cmd_run)

    v = sub.add_parser("viz", help="build a self-contained HTML report from a run directory")
    v.add_argument("run_dir")
    v.set_defaults(fn=cmd_viz)

    wt = sub.add_parser("watch", help="build a playback page: the world unfolding in time")
    wt.add_argument("run_dir")
    wt.set_defaults(fn=cmd_watch)

    n = sub.add_parser("narrate", help="Phase 2: model-written prose for the chronicle (post-processing; history unchanged)")
    n.add_argument("run_dir")
    n.add_argument("--go", action="store_true", help="actually submit the batch (default: dry-run cost estimate)")
    n.add_argument("--mock", action="store_true", help="use the offline mock provider (testing)")
    n.add_argument("--limit", type=int, default=None, help="cap the number of requests")
    n.set_defaults(fn=cmd_narrate)

    a = sub.add_parser("almanac", help="recompile the almanac from a run directory")
    a.add_argument("run_dir")
    a.set_defaults(fn=cmd_almanac)

    c = sub.add_parser("accept", help="run the acceptance suite (§5)")
    c.add_argument("--seeds", type=int, default=3)
    c.add_argument("--start-seed", type=int, default=1)
    c.add_argument("--ticks", type=int, default=4000)
    c.add_argument("--jobs", type=int, default=1, help="parallel workers")
    c.add_argument("--json", type=str, default=None, help="write results to this path")
    c.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="override a Params field, e.g. --set beta_ideology=0.6")
    c.set_defaults(fn=cmd_accept)

    p = sub.add_parser("replay", help="verify seed + journal reproduces the world")
    p.add_argument("run_dir")
    p.set_defaults(fn=cmd_replay)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
