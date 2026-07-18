"""The almanac: a meta-document compiled from surviving in-world chronicles
plus material traces, citing sources and honest about gaps."""

from __future__ import annotations

import json
from pathlib import Path

from .chronicle import PRIORITY


def compile_almanac(run_dir: Path) -> str:
    meta = json.loads((run_dir / "meta.json").read_text())
    entries = [json.loads(l) for l in (run_dir / "chronicle.jsonl").open()]
    scars = [json.loads(l) for l in (run_dir / "scars.jsonl").open()]
    # Phase 2 overlay: model-written prose, where a narration pass has run.
    # The grammar text is always the floor; prose replaces it entry by entry.
    prose: dict[int, str] = {}
    if (run_dir / "chronicle_prose.jsonl").exists():
        for l in (run_dir / "chronicle_prose.jsonl").open():
            rec = json.loads(l)
            prose[rec["eid"]] = rec["text"]
    era_intro: dict[int, str] = {}
    if (run_dir / "era_synthesis.jsonl").exists():
        for l in (run_dir / "era_synthesis.jsonl").open():
            rec = json.loads(l)
            era_intro[rec["era"]] = rec["text"]
    journal_path = run_dir / "journal.jsonl"
    genesis, final = {}, {}
    with journal_path.open() as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("type") == "genesis":
                genesis = rec
            elif rec.get("type") == "tick_summary":
                final = rec

    era_ticks = meta["params"]["era_ticks"]
    ticks = meta["ticks"]
    tpy = meta["params"]["ticks_per_year"]
    out: list[str] = []
    out.append(f"# An Almanac of the World of Seed {meta['seed']}\n")
    out.append("*Compiled from such chronicles as survive, and from the marks left "
               "on the land. Where the sources are silent, this book says so rather "
               "than invent. Every telling here was told by someone, from somewhere, "
               "for reasons of their own.*\n")

    peoples = genesis.get("cultures", {})
    out.append("## The peoples at the opening of the record\n")
    out.append(", ".join(sorted(peoples.values())) + ".\n")

    surviving = [e for e in entries if e["surviving"]]
    for era in range(max(1, (ticks + era_ticks - 1) // era_ticks)):
        lo, hi = era * era_ticks, min(ticks, (era + 1) * era_ticks)
        out.append(f"\n## Years {lo // tpy}–{hi // tpy}\n")
        if era in era_intro:
            out.append(f"*{era_intro[era]}*\n")
        era_entries = sorted((e for e in surviving if lo <= e["tick"] < hi),
                             key=lambda e: (-PRIORITY.get(e["event_type"], 0), e["tick"]))
        era_entries = sorted(era_entries[:14], key=lambda e: e["tick"])
        if not era_entries:
            lost = [e for e in entries if not e["surviving"] and lo <= e["tick"] < hi]
            out.append(f"*No sources survive for this era."
                       + (f" It is known that {len(lost)} tellings once existed and are lost.*\n"
                          if lost else "*\n"))
            continue
        for e in era_entries:
            year = e["tick"] // tpy
            body = prose.get(e["eid"], e["text"])
            cite = f"— as {'written' if e['medium'] == 'written' else 'sung'} by the {e['author_name']}"
            flag = " *(this entry bears the marks of a careful hand: what it omits, it omits on purpose)*" \
                if e.get("redacted") else ""
            out.append(f"**Year {year}.** {body} {cite}.{flag}\n")

    out.append("\n## The marks on the land\n")
    if not scars:
        out.append("*The land keeps no marks from these years.*\n")
    for s in scars[:40]:
        out.append(f"- Year {s['tick'] // tpy}, {s['where']}: {s['note']} ({s['kind']})\n")

    if final:
        out.append("\n## The peoples at the closing of the record\n")
        for cid, c in sorted(final.get("cultures", {}).items(), key=lambda kv: kv[0]):
            shape = "still turns with the seasons" if c["switching"] \
                else "keeps one shape the year round"
            fused = "; their leader holds spears, stories, and admiration in one hand" \
                if c.get("fused") else ""
            out.append(f"- **{c['name']}** — some {c['pop']} souls; their year {shape}{fused}.\n")

    lost_total = len(entries) - len(surviving)
    out.append(f"\n---\n*Of {len(entries)} tellings known to have existed, "
               f"{lost_total} are lost. This book is what remains.*\n")
    return "\n".join(out)
