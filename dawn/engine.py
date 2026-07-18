"""The engine: tick = one season, in the handover doc's system order.

material draws -> economy -> contact/schismogenesis -> transmission ->
handoffs/ratchets -> deliberation triggers -> membership/hospitality ->
domination/fusion -> journal flush.

Deliberations within a tick resolve *simultaneously from pre-tick state*:
sketches and faction values are snapshotted at tick start, all oracle calls
are made from that snapshot, and all consequences land together — cultures
argue in parallel ignorance and their consequences meet next season.
"""

from __future__ import annotations

import copy
import json
from collections import deque
from pathlib import Path

import numpy as np

from . import names, values as V
from .chronicle import ChronicleStore
from .contact import schismogenesis_tick
from .culture import CHARISMA_T, Culture, Faction, INFO_T, VIOLENCE_T, edge_key
from .journal import Journal
from .material import material_tick
from .oracle import Oracle, Situation, StubOracle, Utterance, prompt_hash
from .params import Params
from .polity import domination_tick, handoff_tick, hardening_tick
from .repertoire import Configuration, Origin, Stance, config_signature
from .rng import Streams
from .world import Scar, World, generate, recompute_edges

TRIGGER_PRIORITY = {"ratchet_crisis": 0, "contradiction": 1, "encounter": 2,
                    "recovery": 3, "baseline": 4}


class Engine:
    def __init__(self, seed: int, params: Params | None = None,
                 out_dir: Path | None = None, oracle: Oracle | None = None) -> None:
        self.params = params or Params()
        self.streams = Streams.from_seed(seed)
        self.world = generate(self.streams, self.params)
        self.oracle: Oracle = oracle or StubOracle(self.streams.oracle)
        self.journal = Journal(out_dir / "journal.jsonl" if out_dir else None)
        self.out_dir = out_dir
        self.chronicle = ChronicleStore()
        self.liberations: list[dict] = []
        self._regions_dirty = False
        # Territory history for watch mode: ownership only ever changes at
        # schism and extinction, so the whole map's past is owner0 + few deltas.
        self.owner0 = self.world.owner.copy()
        self.territory_deltas: list[dict] = []
        self.journal.write({"type": "genesis", "tick": 0, "seed": seed,
                            "model": self.oracle.model_id,
                            "params": self.params.to_dict(),
                            "cultures": {c.cid: c.name for c in self.world.living()}})

    # ------------------------------------------------------------------ tick --
    def tick(self) -> None:
        w, p, rng = self.world, self.params, self.streams.history
        events: list[dict] = []
        snapshot = {c.cid: (c.mean.copy(), {f.fid: c.values_of(f).copy() for f in c.factions},
                            c.salience.copy(), c.config().gloss)
                    for c in w.living()}

        # 1-2. material draws and economy
        material = {}
        for c in sorted(w.living(), key=lambda c: c.cid):
            m = material_tick(w, c, rng, p)
            material[c.cid] = m
            if w.season == "winter" and m["wellbeing"] < 0.35:
                events.append({"type": "hard_winter", "culture": c.cid})

        # 3. contact and schismogenetic drift
        events += schismogenesis_tick(w, rng, p)

        # 4. transmission: biased reproduction, frontier variance, contradiction
        neighbor_live: dict[int, set[str]] = {c.cid: set() for c in w.living()}
        frontier: dict[int, bool] = {c.cid: False for c in w.living()}
        for key in sorted(w.edges):
            e = w.edges[key]
            if e.openness(w.cultures) >= p.hospitality_min:
                for x, y in ((e.a, e.b), (e.b, e.a)):
                    if x in neighbor_live:
                        neighbor_live[x] |= {el.eid for el in
                                             w.cultures[y].repertoire.live()}
            gap = float(np.abs(w.cultures[e.a].mean - w.cultures[e.b].mean).max())
            if gap > p.frontier_gap:
                frontier[e.a] = frontier[e.b] = True
        for c in sorted(w.living(), key=lambda c: c.cid):
            c.stamp_dominance()
            forgotten = c.repertoire.transmission_tick(
                c.dominant_signature(), p, w.tick, frontier[c.cid], rng,
                self.chronicle.recorded_ids(c.cid), neighbor_live[c.cid])
            for eid in forgotten:
                events.append({"type": "forgotten", "culture": c.cid, "eid": eid})
            m = material[c.cid]
            for f in c.factions:
                gap = max(0.0, m["promise"] - f.lived)
                f.contradiction = (1.0 - p.contradiction_decay) * f.contradiction + gap
                # Cohesion: the same channels that bias transmission between
                # generations pull members toward the mean within one.
                f.offset *= (1.0 - p.cohesion)

        # 5. configuration handoffs and ratchet checks; yearly re-evaluation
        ratcheted_now: list[int] = []
        for c in sorted(w.living(), key=lambda c: c.cid):
            evs = handoff_tick(w, c, rng, p)
            events += evs
            if any(e["type"] == "ratchet" for e in evs):
                ratcheted_now.append(c.cid)
        if w.tick % 4 == 0:  # each spring the year's shape is up for argument
            for c in sorted(w.living(), key=lambda c: c.cid):
                events += self._reevaluate_dominant(c)

        # 6. deliberation triggers -> oracle (simultaneous, from snapshot)
        situations = self._collect_triggers(material, ratcheted_now, rng)
        utterances: list[tuple[Situation, Utterance]] = []
        for sit in situations:
            mean, fvals, sal, gloss = snapshot.get(sit.culture, (None,) * 4)
            if mean is None:
                continue
            sketch = (V.sketch(fvals.get(sit.faction, mean), sal)
                      + f" Their year is shaped so: {gloss}.")
            utt = self.oracle.deliberate(sketch, sit)
            self.journal.write({
                "type": "deliberation", "tick": w.tick, "culture": sit.culture,
                "faction": sit.faction, "kind": sit.kind,
                "model": utt.model or self.oracle.model_id,
                "prompt_hash": prompt_hash(sketch, sit), "sketch": sketch,
                "menu": [s.eid for s in sit.menu], "stance": utt.stance_id,
                "text": utt.text, "speaker": utt.speaker, "detail": sit.detail})
            utterances.append((sit, utt))
            events.append({"type": "deliberation", "culture": sit.culture,
                           "kind": sit.kind, "stance": utt.stance_id,
                           "text": utt.text})

        # 7. apply consequences; membership shifts and hospitality updates
        for sit, utt in utterances:
            events += self._apply_stance(sit, utt, rng)
        events += self._membership_tick(rng)

        # 8. domination tracks and fusion detection
        for c in sorted(w.living(), key=lambda c: c.cid):
            events += hardening_tick(w, c, rng, p)
            events += domination_tick(w, c, rng, p)

        # 9. flush: journal, chronicle, attrition
        for ev in events:
            ev.setdefault("tick", w.tick)
            if ev["type"] != "deliberation":  # deliberations already journaled in full
                self.journal.write(ev)
            entry = self.chronicle.maybe_record(ev, w, p)
            if entry is not None:
                self.journal.write({"type": "chronicle_entry", "tick": w.tick,
                                    "author": entry.author, "medium": entry.medium,
                                    "about": entry.event_type, "text": entry.text})
        if w.tick % p.generation_ticks == p.generation_ticks - 1:
            self.chronicle.attrition(w, rng, p)
        if w.tick % 20 == 0:
            self.journal.write(self._summary())
        self.journal.flush()
        w.tick += 1

    # ------------------------------------------------------- dominant config --
    def _reevaluate_dominant(self, c: Culture) -> list[dict]:
        p, w = self.params, self.world
        configs = [e for e in c.repertoire.live("configuration")]
        if not configs:
            return []
        cur = c.dominant_config

        def score(cfg: Configuration) -> float:
            s = float(np.dot(config_signature(cfg), c.mean))
            if cfg.eid == cur:
                s += 0.35  # inertia: ways of living are not shopped for
            if cfg.ratcheted:
                s += 0.35 * float(c.domination[VIOLENCE_T] + c.domination[CHARISMA_T])
            # The year itself argues for dualism: winter aggregation and summer
            # dispersal are materially cheaper. A coefficient, not a value —
            # cultures remain free to pay for refusing the season.
            from .repertoire import STRUCTURES
            if STRUCTURES[cfg.seasons[3]].settlement == "aggregated":
                s += p.seasonal_fit_bonus
            if STRUCTURES[cfg.seasons[1]].settlement == "dispersed":
                s += p.seasonal_fit_bonus
            return s + 0.2 * cfg.weight

        best = max(configs, key=score)
        if best.eid == cur:
            return []
        was = c.repertoire.get(cur)
        c.dominant_config = best.eid
        events = [{"type": "config_switch", "culture": c.cid,
                   "frm": cur, "to": best.eid}]
        if isinstance(was, Configuration) and was.ratcheted and not best.ratcheted:
            # Breaking a ratchet is a liberation, and it costs.
            c.pop *= p.liberation_pop_cost
            c.domination[VIOLENCE_T] = max(0.0, float(c.domination[VIOLENCE_T]) - 0.15)
            c.domination[CHARISMA_T] = max(0.0, float(c.domination[CHARISMA_T]) - 0.15)
            lib = {"type": "liberation", "culture": c.cid, "mechanism": "ratchet_break",
                   "note": "they put down the standing chief and took up the seasons again"}
            self.liberations.append(lib)
            events.append(lib)
            self.world.scars.append(Scar(w.tick, "liberation", c.name,
                                         "here a people un-kinged itself"))
        return events

    # ------------------------------------------------------------- triggers --
    def _collect_triggers(self, material: dict, ratcheted_now: list[int],
                          rng: np.random.Generator) -> list[Situation]:
        w, p = self.world, self.params
        sits: list[Situation] = []

        def menu_for(c: Culture) -> list[Stance]:
            return sorted((e for e in c.repertoire.live("stance")
                           if isinstance(e, Stance)), key=lambda s: s.eid)

        def add(kind: str, c: Culture, f: Faction, detail: dict,
                extra: list[Stance] | None = None) -> None:
            menu = menu_for(c) + (extra or [])
            if not menu:
                return
            sits.append(Situation(kind=kind, culture=c.cid, culture_name=c.name,
                                  faction=f.fid, faction_name=f.name, tick=w.tick,
                                  detail=detail, menu=menu,
                                  faction_values=c.values_of(f)))

        for cid in ratcheted_now:
            c = w.cultures[cid]
            f = max(c.factions, key=lambda f: f.contradiction)
            add("ratchet_crisis", c, f, {"structure": c.config().seasons[0]})

        for c in sorted(w.living(), key=lambda c: c.cid):
            for f in c.factions:
                if f.contradiction > p.contradiction_theta:
                    add("contradiction", c, f,
                        {"promised": round(material[c.cid]["promise"], 2),
                         "lived": round(f.lived, 2)})
                    break  # one voice per culture per season

        for key in sorted(w.edges):
            e = w.edges[key]
            A, B = w.cultures[e.a], w.cultures[e.b]
            if not (A.alive and B.alive):
                continue
            dist = float(np.abs(A.mean - B.mean).sum())
            if (e.openness(w.cultures) > 0.3 and dist > p.encounter_distance
                    and rng.random() < p.encounter_prob):
                host = A if A.openness() >= B.openness() else B
                guest = B if host is A else A
                own = {s.name for s in host.repertoire.live("stance")}
                foreign = [s for s in guest.repertoire.live("stance")
                           if isinstance(s, Stance) and s.name not in own]
                inject = []
                if foreign:
                    fs = foreign[int(rng.integers(len(foreign)))]
                    inject = [fs]  # the Kandiaronk mechanic: critique from outside the bias
                f = host.factions[int(rng.integers(len(host.factions)))]
                add("encounter", host, f,
                    {"neighbor": guest.name, "other": guest.cid,
                     "injected": inject[0].eid if inject else None}, extra=inject)

        for c in sorted(w.living(), key=lambda c: c.cid):
            if (c.chronicler_kind(w.tick) and c.repertoire.lapsed_elements()
                    and rng.random() < p.recovery_prob):
                f = c.factions[int(rng.integers(len(c.factions)))]
                add("recovery", c, f, {"lapsed": len(c.repertoire.lapsed_elements())})
            elif rng.random() < p.baseline_prob:
                f = c.factions[int(rng.integers(len(c.factions)))]
                add("baseline", c, f, {})

        sits.sort(key=lambda s: (TRIGGER_PRIORITY[s.kind], s.culture))
        seen: set[int] = set()
        out = []
        for s in sits:
            if s.culture in seen:
                continue
            seen.add(s.culture)
            out.append(s)
        return out[:p.max_deliberations_per_tick]

    # ---------------------------------------------------------- apply stance --
    def _apply_stance(self, sit: Situation, utt: Utterance,
                      rng: np.random.Generator) -> list[dict]:
        w, p = self.world, self.params
        c = w.cultures.get(sit.culture)
        if c is None or not c.alive:
            return []
        f = next((x for x in c.factions if x.fid == sit.faction), None)
        if f is None:
            return []
        events: list[dict] = []
        stance = next((s for s in sit.menu if s.eid == utt.stance_id), None)
        if stance is None:
            return []
        own = c.repertoire.get(stance.eid)
        if sit.detail.get("injected") == stance.eid and (own is None or own.lapsed):
            # A foreign stance, heard and taken up: liberation by encounter —
            # either arriving from outside or re-arriving where it had lapsed.
            if own is None:
                borrowed = copy.deepcopy(stance)
                borrowed.origin = Origin(w.tick, "borrowed",
                                         source=sit.detail.get("neighbor"))
                borrowed.weight, borrowed.use_ema, borrowed.lapsed = 0.45, 0.6, False
                borrowed.below_since = None
                c.repertoire.add(borrowed)
            else:
                c.repertoire.revive(own.eid, w.tick, "encounter")
            lib = {"type": "liberation", "culture": c.cid, "mechanism": "encounter",
                   "note": f"an outsider's argument ({stance.eid}) took root among the {c.name}"}
            self.liberations.append(lib)
            events.append(lib)
        elif own is not None:
            c.repertoire.note_use(stance.eid)

        # The stance's value delta lands on the speaking faction and drags the mean.
        target = np.clip(c.values_of(f) + stance.delta, -1, 1)
        f.offset = target - c.mean
        c.mean = V.soft_step(c.mean, stance.delta * f.weight * 0.5)

        eid = stance.eid
        if eid == "affirm":
            sig = c.dominant_signature()
            f.offset += 0.04 * (sig - c.values_of(f))
        elif eid == "submit":
            c.domination[CHARISMA_T] = min(1.0, float(c.domination[CHARISMA_T]) + 0.01)
            f.contradiction *= 0.5  # consent quiets the gap without closing it
        elif eid == "refuse":
            c.domination[VIOLENCE_T] = max(0.0, float(c.domination[VIOLENCE_T]) - 0.02)
            c.domination[CHARISMA_T] = max(0.0, float(c.domination[CHARISMA_T]) - 0.02)
            f.contradiction *= 0.4
        elif eid == "mock":
            c.domination[CHARISMA_T] = max(0.0, float(c.domination[CHARISMA_T]) - 0.03)
        elif eid == "leave":
            events += self._defect(c, f, rng, reason=sit.kind)
        elif eid == "invert":
            other = w.cultures.get(sit.detail.get("other", -1))
            if other is not None:
                k = int(np.argmax((c.salience + other.salience)
                                  * np.abs(c.mean - other.mean)))
                push = -np.sign(other.mean[k]) * 0.12
                f.offset[k] += push
                c.mean = V.soft_step(c.mean, np.eye(V.N_AXES)[k] * push * f.weight)
        elif eid == "emulate":
            other = w.cultures.get(sit.detail.get("other", -1))
            if other is not None:
                own_names = {e.name for e in c.repertoire.elements.values()}
                cands = [e for e in other.repertoire.live()
                         if e.name not in own_names and e.kind != "lexeme"]
                if cands:
                    el = copy.deepcopy(cands[int(rng.integers(len(cands)))])
                    el.eid = f"{el.eid}@{c.cid}" if el.eid in c.repertoire.elements else el.eid
                    el.origin = Origin(w.tick, "borrowed", source=other.name)
                    el.weight, el.lapsed, el.below_since = 0.4, False, None
                    c.repertoire.add(el)
        elif eid == "remember":
            lapsed = c.repertoire.lapsed_elements()
            recorded = self.chronicle.recorded_ids(c.cid)
            cands = ([e for e in lapsed if e.eid in recorded]
                     or [e for e in lapsed if e.kind == "configuration"] or lapsed)
            if cands:
                el = cands[int(rng.integers(len(cands)))]
                c.repertoire.revive(el.eid, w.tick, "recovery")
                lib = {"type": "liberation", "culture": c.cid, "mechanism": "recovery",
                       "note": f"they recalled {el.name} out of the old tellings"}
                self.liberations.append(lib)
                events.append(lib)
        elif eid == "feast":
            other_cid = sit.detail.get("other")
            neigh = [k for k in sorted(w.edges) if c.cid in k]
            if other_cid is None and neigh:
                key = neigh[int(rng.integers(len(neigh)))]
            elif other_cid is not None:
                key = edge_key(c.cid, other_cid)
            else:
                key = None
            if key is not None and key in w.edges:
                w.edges[key].exchange_until = w.tick + p.exchange_duration
                other = w.cultures[key[0] if key[1] == c.cid else key[1]]
                events.append({"type": "feast", "culture": c.cid,
                               "other": other.cid, "other_name": other.name})
        elif eid == "propose":
            base = [s for s in c.repertoire.live("stance") if isinstance(s, Stance)]
            src = base[int(rng.integers(len(base)))]
            delta = np.clip(src.delta + rng.normal(0, 0.06, V.N_AXES), -0.15, 0.15)
            nm = names.word(rng, 2).lower()
            new = Stance(eid=f"way_of_{nm}", kind="stance", name=f"way_of_{nm}",
                         gloss=f"the way of {nm}, which no one had tried before",
                         alignment=np.clip(delta * 5.0, -0.9, 0.9),
                         origin=Origin(w.tick, "proposed", source=sit.faction),
                         delta=delta, tags=frozenset({"proposed"}),
                         weight=0.4, use_ema=0.6)
            c.repertoire.add(new)
            events.append({"type": "proposal", "culture": c.cid, "eid": new.eid,
                           "gloss": new.gloss, "auto_accepted": True})
        return events

    # ------------------------------------------------------------ membership --
    def _defect(self, c: Culture, f: Faction, rng: np.random.Generator,
                reason: str) -> list[dict]:
        w, p = self.world, self.params
        events: list[dict] = []
        best, best_d = None, 1e9
        for key in sorted(w.edges):
            e = w.edges[key]
            if c.cid not in key:
                continue
            if e.openness(w.cultures) < p.hospitality_min:
                continue
            other = w.cultures[key[0] if key[1] == c.cid else key[1]]
            if not other.alive:
                continue
            d = float(np.abs(other.mean - c.values_of(f)).sum())
            if d < best_d:
                best, best_d = (e, other), d
        if best is not None:
            e, other = best
            moving = c.pop * f.weight * 0.5
            c.pop -= moving
            other.pop += moving
            e.traffic += 1
            other.mean = V.soft_step(other.mean, (c.values_of(f) - other.mean) * 0.02)
            f.weight *= 0.5
            f.offset *= 0.5  # those who most needed to go have gone
            total = sum(x.weight for x in c.factions)
            for x in c.factions:
                x.weight /= total
            f.contradiction *= 0.3
            ev = {"type": "defection", "culture": c.cid, "to": other.cid,
                  "to_name": other.name, "pop": round(moving)}
            events.append(ev)
            if reason in ("contradiction", "ratchet_crisis"):
                lib = {"type": "liberation", "culture": c.cid, "mechanism": "contradiction",
                       "note": f"families walked out of the {c.name} rather than live the gap"}
                self.liberations.append(lib)
                events.append(lib)
        elif f.weight > p.schism_min_weight and c.pop > p.schism_min_pop:
            events += self._schism(c, f, rng)
        return events

    def _schism(self, c: Culture, f: Faction, rng: np.random.Generator) -> list[dict]:
        w = self.world
        cells = np.argwhere(w.owner == c.cid)
        if len(cells) < 8:
            return []
        n_take = max(2, int(len(cells) * f.weight))
        start = cells[int(rng.integers(len(cells)))]
        taken: set[tuple[int, int]] = set()
        q = deque([tuple(start)])
        while q and len(taken) < n_take:
            x, y = q.popleft()
            if (x, y) in taken or not (0 <= x < w.owner.shape[0]
                                       and 0 <= y < w.owner.shape[1]):
                continue
            if w.owner[x, y] != c.cid:
                continue
            taken.add((x, y))
            q.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
        new_cid = max(w.cultures) + 1
        for x, y in taken:
            w.owner[x, y] = new_cid
        self.territory_deltas.append({"tick": w.tick, "to": new_cid,
                                      "cells": sorted([int(a), int(b)] for a, b in taken)})
        moving = c.pop * f.weight
        c.pop -= moving
        new_name = names.culture_name(rng)
        nf_off = rng.normal(0, 0.12, (2, V.N_AXES))
        new = Culture(
            cid=new_cid, name=new_name,
            mean=np.clip(c.mean + f.offset, -1, 1),
            salience=c.salience.copy(),
            factions=[Faction(fid=f"{new_cid}.{i}", name=names.word(rng, 2),
                              weight=0.5, offset=nf_off[i]) for i in range(2)],
            repertoire=copy.deepcopy(c.repertoire), pop=moving,
            dominant_config=c.dominant_config)
        w.cultures[new_cid] = new
        c.factions.remove(f)
        total = sum(x.weight for x in c.factions) or 1.0
        for x in c.factions:
            x.weight /= total
        recompute_edges(w)
        return [{"type": "schism", "culture": c.cid, "new": new_cid,
                 "new_name": new_name, "why": "the gap between what was said and what was lived",
                 "pop": round(moving)}]

    def _membership_tick(self, rng: np.random.Generator) -> list[dict]:
        w, p = self.world, self.params
        events: list[dict] = []
        for c in sorted(w.living(), key=lambda c: c.cid):
            for f in list(c.factions):
                if len(c.factions) > 1 and float(np.linalg.norm(f.offset)) > p.defect_tolerance:
                    events += self._defect(c, f, rng, reason="drift")
            if c.pop < p.min_pop:
                c.alive = False
                lost = np.argwhere(w.owner == c.cid)
                self.territory_deltas.append({"tick": w.tick, "to": -1,
                                              "cells": lost.tolist()})
                w.owner[w.owner == c.cid] = -1
                w.scars.append(Scar(w.tick, "abandonment", c.name,
                                    "their lands lie open; their hearths are cold"))
                events.append({"type": "extinction", "culture": c.cid})
                recompute_edges(w)
        # Dead routes scar: an edge that once carried defectors and now is closed.
        for key in sorted(w.edges):
            e = w.edges[key]
            if e.traffic >= 3 and e.openness(w.cultures) < 0.1:
                a, b = w.cultures[e.a], w.cultures[e.b]
                w.scars.append(Scar(w.tick, "dead_route", f"{a.name}–{b.name}",
                                    "a road much walked, now watched from both sides"))
                e.traffic = 0
        return events

    # ---------------------------------------------------------------- output --
    def _summary(self) -> dict:
        w = self.world
        return {"type": "tick_summary", "tick": w.tick,
                "cultures": {c.cid: {"name": c.name, "pop": round(c.pop),
                                     "mean": c.mean, "salience": c.salience,
                                     "dominant": c.dominant_config,
                                     "switching": c.is_switching(),
                                     "fused": c.fused,
                                     "domination": c.domination,
                                     # internal variance is the fuel for liberation;
                                     # export it so it can be *seen*
                                     "factions": [[round(f.weight, 3)]
                                                  + [round(float(x), 2) for x in f.offset]
                                                  for f in c.factions]}
                             for c in w.living()}}

    def run(self, n_ticks: int, progress: bool = False) -> None:
        for i in range(n_ticks):
            self.tick()
            if progress and i % 200 == 199:
                print(f"  tick {i + 1}/{n_ticks}  cultures={len(self.world.living())}")
        self.journal.write(self._summary())
        self.journal.flush()
        if self.out_dir is not None:
            self._write_outputs()

    def _write_outputs(self) -> None:
        assert self.out_dir is not None
        w = self.world
        (self.out_dir / "meta.json").write_text(json.dumps({
            "seed": self.streams.seed, "ticks": w.tick, "model": self.oracle.model_id,
            "params": self.params.to_dict()}, indent=2))
        from .metrics import evaluate
        from .viz import world_snapshot
        (self.out_dir / "metrics.json").write_text(json.dumps(evaluate(self), indent=2))
        snap = world_snapshot(w)
        snap["owner0"] = self.owner0.astype(int).tolist()
        snap["deltas"] = self.territory_deltas
        (self.out_dir / "world.json").write_text(json.dumps(snap))
        with (self.out_dir / "chronicle.jsonl").open("w") as fh:
            for e in self.chronicle.entries:
                fh.write(json.dumps({
                    "eid": e.eid, "tick": e.tick, "author": e.author,
                    "author_name": w.cultures[e.author].name if e.author in w.cultures else "?",
                    "medium": e.medium, "event_type": e.event_type, "text": e.text,
                    "cites": e.cites, "surviving": e.surviving,
                    "redacted": e.redacted}) + "\n")
        with (self.out_dir / "scars.jsonl").open("w") as fh:
            for s in w.scars:
                fh.write(json.dumps({"tick": s.tick, "kind": s.kind,
                                     "where": s.where, "note": s.note}) + "\n")
        self.journal.close()
