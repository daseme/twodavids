"""Phase 2: the model writes the chronicle's prose; history does not move.

This is a pure post-processing pass over a finished run directory — the run
loop stays model-free, the journal is untouched, and replay still verifies.
Same seed, same history, new voice: regenerate prose as often as you like and
diff it against the grammar floor with the trajectory held constant.

Tiering follows the handover doc: cheap model for volume narration, mid-tier
for the major beats, top tier rarely for era synthesis.

The elaboration rule (VIEWER.md) applies to prose exactly as it will to
pixels: the model may add texture the record is silent about, but may never
contradict or add to the record. The lexicon gate runs twice — once in the
prompt ("this world has not earned these words") and once as a hard regex
backstop over the model's output.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .providers import Provider
from .viz import build_watch_data

TIER_VOLUME = "claude-haiku-4-5"
TIER_BEATS = "claude-sonnet-5"
TIER_SYNTHESIS = "claude-opus-4-8"

# Batch API prices are 50% of standard ($/MTok in, out).
PRICES = {TIER_VOLUME: (0.5, 2.5), TIER_BEATS: (1.5, 7.5), TIER_SYNTHESIS: (2.5, 12.5)}

HIGH_BEATS = {"ratchet", "fusion", "unfusion", "liberation", "hardening",
              "schism", "extinction"}
STATAL = ["king", "realm", "treasury", "subject", "decree", "throne"]
CHIEFLY = ["chief", "retinue", "tribute"]
SWAPS = {"king": "one who does not step down", "realm": "lands that answer him",
         "treasury": "guarded stores", "subject": "those who may not refuse",
         "decree": "word that may not be laughed at", "throne": "high seat",
         "chief": "winter leader", "retinue": "young men at his fire",
         "tribute": "taken share"}

SYSTEM = [{
    "type": "text",
    "text": (
        "You are the annalist of a generated world — the hand that turns its dry "
        "record into a chronicle meant to be read.\n\n"
        "Rules, none negotiable:\n"
        "- The record you are given is the complete set of facts. Never add an "
        "event, a name, a number, or an outcome that is not in it. You may add "
        "texture — weather, gesture, the look of a place — that asserts no new "
        "fact of consequence. Decoration, never fabrication.\n"
        "- Write as the author people, in their bias and register. They do not "
        "know what they could not know, and they are not neutral about their "
        "neighbors.\n"
        "- Annalist voice: past tense, concrete, unhurried. No numerals — spell "
        "out small numbers or stay vague, as chronicles do.\n"
        "- No modern vocabulary, no anachronism, no irony aimed at the people.\n"
        "- Each entry will list forbidden words: vocabulary this world has not "
        "yet earned. Never use them, in any form.\n"
        "- Output only the rewritten entry text. No preamble, no quotation marks "
        "around the whole, no commentary."
    ),
    "cache_control": {"type": "ephemeral"},
}]


def _banned_words(author: int | None, tick: int, events: list[dict]) -> list[str]:
    """Conservative approximation of the in-sim lexicon gate, for the backstop.

    Statal words unlock only after the author's own fusion; chiefly words after
    their first ratchet/hardening/fusion. The in-sim gate remains authoritative
    for the grammar floor; this guards the model's additions.
    """
    def before(kinds: set[str]) -> bool:
        return any(e["type"] in kinds and e.get("culture") == author
                   and e["tick"] <= tick for e in events)
    banned = []
    if not before({"fusion"}):
        banned += STATAL
    if not before({"ratchet", "hardening", "fusion"}):
        banned += CHIEFLY
    return banned


def _gate(text: str, banned: list[str]) -> str:
    for w in banned:
        text = re.sub(rf"\b{w}s?\b", SWAPS[w], text, flags=re.IGNORECASE)
    return text


def build_requests(run_dir: Path, limit: int | None = None) -> tuple[list[dict], dict]:
    data = build_watch_data(run_dir)
    entries = [json.loads(l) for l in (run_dir / "chronicle.jsonl").open()]
    surviving = [e for e in entries if e["surviving"]]
    events = data["events"]
    era_ticks = data["era_ticks"]

    # Author id lookup: chronicle.jsonl carries author + author_name.
    requests: list[dict] = []
    for e in surviving:
        tier = TIER_BEATS if e["event_type"] in HIGH_BEATS else TIER_VOLUME
        era = str(e["tick"] // era_ticks)
        sketch = (data["sketches"].get(era) or {}).get(str(e["author"]), "")
        banned = _banned_words(e["author"], e["tick"], events)
        season = ["spring", "summer", "autumn", "winter"][e["tick"] % 4]
        user = (
            f"The author people, the {e['author_name']}, as an ethnographer would "
            f"describe them at this time: {sketch}\n"
            f"The entry is {e['medium']}; the event is a {e['event_type']}, in the "
            f"{season} of year {e['tick'] // 4}.\n"
            f"Forbidden words in this world at this time: "
            f"{', '.join(banned) if banned else 'none beyond the standing rules'}.\n\n"
            f"The record states: \"{e['text']}\"\n\n"
            f"Rewrite this entry in the author's voice, two to four sentences."
        )
        req = {"custom_id": f"e{e['eid']}", "model": tier, "max_tokens": 350,
               "system": SYSTEM,
               "messages": [{"role": "user", "content": user}],
               "_meta": {"eid": e["eid"], "banned": banned, "tier": tier}}
        if tier == TIER_BEATS:
            req["thinking"] = {"type": "disabled"}  # prose rewriting needs no deliberation
        requests.append(req)

    # Era synthesis: one top-tier call per era, in the compiler's meta-voice.
    n_eras = max(1, (data["ticks"] + era_ticks - 1) // era_ticks)
    for era in range(n_eras):
        lo, hi = era * era_ticks, (era + 1) * era_ticks
        era_entries = [e for e in surviving if lo <= e["tick"] < hi]
        if not era_entries:
            continue
        lost = sum(1 for e in entries if not e["surviving"] and lo <= e["tick"] < hi)
        digest = "\n".join(f"- ({e['event_type']}, yr {e['tick'] // 4}) {e['text']}"
                           for e in era_entries[:24])
        banned = sorted(set(w for e in era_entries
                            for w in _banned_words(e["author"], hi - 1, events)))
        user = (
            f"You are compiling the almanac of this world — a meta-document built "
            f"from surviving chronicles, honest about its gaps. Years "
            f"{lo // 4}–{hi // 4}. {lost} tellings from this era are lost.\n"
            f"The surviving record of the era:\n{digest}\n\n"
            f"Forbidden words (unearned in every relevant lineage): "
            f"{', '.join(banned) if banned else 'none'}.\n\n"
            f"Write a short introductory passage for this era, three to five "
            f"sentences, in the compiler's voice: what turned, what held, what "
            f"the silence of the lost tellings might cover. Assert nothing the "
            f"record does not support."
        )
        requests.append({"custom_id": f"era{era}", "model": TIER_SYNTHESIS,
                         "max_tokens": 800, "system": SYSTEM,
                         "messages": [{"role": "user", "content": user}],
                         "thinking": {"type": "adaptive"},
                         "_meta": {"era": era, "banned": banned,
                                   "tier": TIER_SYNTHESIS}})

    if limit is not None:
        requests = requests[:limit]
    stats = _estimate(requests)
    return requests, stats


def _estimate(requests: list[dict]) -> dict:
    tiers: dict[str, dict] = {}
    sys_tokens = len(SYSTEM[0]["text"]) // 4
    for r in requests:
        t = tiers.setdefault(r["model"], {"n": 0, "in": 0, "out": 0})
        t["n"] += 1
        t["in"] += sys_tokens + len(r["messages"][0]["content"]) // 4
        t["out"] += r["max_tokens"] // 2  # entries rarely fill the cap
    cost = sum(PRICES[m][0] * v["in"] / 1e6 + PRICES[m][1] * v["out"] / 1e6
               for m, v in tiers.items())
    return {"requests": len(requests),
            "by_tier": {m: v["n"] for m, v in tiers.items()},
            "est_input_tokens": sum(v["in"] for v in tiers.values()),
            "est_cost_usd": round(cost, 3)}


def narrate(run_dir: Path, provider: Provider, limit: int | None = None) -> dict:
    """Run the narration pass and write prose files + the prose journal."""
    requests, stats = build_requests(run_dir, limit)
    wire = [{k: v for k, v in r.items() if k != "_meta"} for r in requests]
    results = provider.run_batch(wire)

    prose_path = run_dir / "chronicle_prose.jsonl"
    era_path = run_dir / "era_synthesis.jsonl"
    journal_path = run_dir / "prose_journal.jsonl"
    n_ok = 0
    with prose_path.open("w") as pf, era_path.open("w") as ef, \
            journal_path.open("w") as jf:
        for r in requests:
            cid = r["custom_id"]
            raw = results.get(cid)
            jf.write(json.dumps({
                "custom_id": cid, "model": r["model"], "provider": provider.name,
                "prompt_hash": hashlib.sha256(
                    (SYSTEM[0]["text"] + r["messages"][0]["content"]).encode()
                ).hexdigest()[:16],
                "prompt": r["messages"][0]["content"],
                "response": raw}) + "\n")
            if raw is None:
                continue  # grammar text remains the floor for this entry
            text = _gate(raw.strip(), r["_meta"]["banned"])
            n_ok += 1
            if cid.startswith("era"):
                ef.write(json.dumps({"era": r["_meta"]["era"], "text": text}) + "\n")
            else:
                pf.write(json.dumps({"eid": r["_meta"]["eid"], "text": text,
                                     "model": r["model"]}) + "\n")

    from .almanac import compile_almanac
    (run_dir / "ALMANAC.md").write_text(compile_almanac(run_dir))
    return {**stats, "completed": n_ok, "provider": provider.name,
            "outputs": [str(prose_path), str(era_path), str(journal_path),
                        str(run_dir / "ALMANAC.md")]}
