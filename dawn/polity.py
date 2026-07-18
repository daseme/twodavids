"""Seasonal handoffs, ratchets, the three domination tracks, and fusion detection.

"The state" is a contingent fusion, never a stage: three independent tracks
(violence, information, charisma) accumulate and decay on their own schedules.
Statehood is a conjunction the code *detects*, not an event it schedules, and
a fully fused polity must be able to unfuse.

A ratchet is a failed seasonal handoff — the winter chief who does not step down.
"""

from __future__ import annotations

import numpy as np

from .culture import CHARISMA_T, Culture, INFO_T, VIOLENCE_T
from .params import Params
from .repertoire import Configuration, Origin, config_signature
from .values import COMMAND, DISPLAY, VIOLENCE
from .world import Scar, World


def handoff_tick(world: World, c: Culture, rng: np.random.Generator,
                 p: Params) -> list[dict]:
    """At each season boundary, check whether power actually steps down."""
    events: list[dict] = []
    cfg = c.config()
    cur = cfg.seasons[world.tick % 4]
    nxt = cfg.seasons[(world.tick + 1) % 4]
    if cur == nxt:
        return events
    from .repertoire import STRUCTURES
    if STRUCTURES[nxt].authority_rank < STRUCTURES[cur].authority_rank:
        c.handoffs_total += 1
        p_fail = (p.ratchet_base
                  + p.ratchet_dom_pull * float(c.domination[CHARISMA_T]
                                               + c.domination[VIOLENCE_T])
                  - 0.02 * c.refusal_strength())
        if rng.random() < max(0.0, p_fail):
            _ratchet(world, c, cur, events)
        else:
            c.handoffs_ok += 1
    return events


def _ratchet(world: World, c: Culture, structure_id: str, events: list[dict]) -> None:
    displaced = c.dominant_config  # the seasonal way that just failed to resume
    eid = f"ratchet:{c.cid}:{world.tick}"
    ratcheted = Configuration(
        eid=eid, kind="configuration", name=f"{structure_id}_unbroken",
        gloss=f"the {structure_id.replace('_', ' ')} that no longer dissolves in spring",
        alignment=np.zeros(8), origin=Origin(world.tick, "proposed", source="ratchet"),
        seasons=(structure_id,) * 4, ratcheted=True, weight=0.7, use_ema=0.8)
    ratcheted.alignment = config_signature(ratcheted)
    c.repertoire.add(ratcheted)
    c.dominant_config = eid
    world.scars.append(Scar(world.tick, "ratchet_mark", c.name,
                            f"the season turned and the {structure_id.replace('_', ' ')} did not open its hand"))
    events.append({"type": "ratchet", "culture": c.cid, "structure": structure_id,
                   "displaced": displaced})


def hardening_tick(world: World, c: Culture, rng: np.random.Generator,
                   p: Params) -> list[dict]:
    """A ratcheted chief whose people have drifted toward accumulation and rank
    may begin keeping tallies and stores: chiefly lodge hardens into hoard-fort.

    This is the only road to the information track for a chief — the state, if
    it ever fuses, must be assembled link by contingent link, never scheduled.
    """
    cfg = c.config()
    from .values import ACCUMULATION, RANK
    if (cfg.ratcheted and cfg.seasons[0] == "chiefly_lodge"
            and world.tick - cfg.origin.tick > 300  # tallies take generations to grow
            and float(c.mean[ACCUMULATION]) > 0.4 and float(c.mean[RANK]) > 0.3
            and rng.random() < 0.01):
        cfg.seasons = ("hoard_fort",) * 4
        cfg.name += "_hardened"
        cfg.gloss = "the fort where what is owed is counted and kept"
        cfg.alignment = config_signature(cfg)
        return [{"type": "hardening", "culture": c.cid}]
    return []


def domination_tick(world: World, c: Culture, rng: np.random.Generator,
                    p: Params) -> list[dict]:
    events: list[dict] = []
    s = c.structure(world.tick)
    d = c.domination
    refusal = c.refusal_strength()

    # Succession: charisma is a person, not an office. When the big man dies,
    # the competition reruns from a lower rung — the predator on that track.
    if (s.authority == "chief" or float(d[CHARISMA_T]) > 0.3) and rng.random() < 0.01:
        d[CHARISMA_T] *= 0.5
        events.append({"type": "succession", "culture": c.cid})

    # Each track accumulates from its own sources: values feed it, structures
    # multiply it. Independence of the three is the point — fusion must be a
    # conjunction that happens to occur, not a package.
    v_feed = max(0.0, float(c.mean[VIOLENCE]))
    if "war-leader" in s.roles:
        v_feed = v_feed * 1.5 + (1.0 if s.authority == "chief" else 0.3)
    d[VIOLENCE_T] += p.dom_gain * v_feed

    if c.chronicler_kind(world.tick) == "written":
        d[INFO_T] += p.dom_gain * (1.5 if s.authority == "chief" else 0.4)

    ch_feed = max(0.0, float(c.mean[DISPLAY]))  # rivalrous display IS the fuel
    if s.authority == "chief":
        ch_feed = ch_feed * 1.5 + 1.0
    d[CHARISMA_T] += p.dom_gain * ch_feed

    d -= p.dom_decay
    d[VIOLENCE_T] -= p.refusal_erosion * refusal * 0.5
    d[CHARISMA_T] -= p.refusal_erosion * refusal * 0.5
    np.clip(d, 0.0, 1.0, out=d)

    was = c.fused
    now = bool((d > p.fusion_threshold).all())
    if now and not was:
        c.fused, c.fused_since = True, world.tick
        events.append({"type": "fusion", "culture": c.cid,
                       "tracks": [round(float(x), 3) for x in d]})
        _unlock_lexicon(c, "fusion", world.tick)
    elif was and bool((d < p.unfusion_threshold).any()):
        c.fused = False
        events.append({"type": "unfusion", "culture": c.cid,
                       "held_ticks": world.tick - (c.fused_since or world.tick)})
    if s.authority == "chief":
        _unlock_lexicon(c, "chiefly", world.tick)
    return events


def _unlock_lexicon(c: Culture, unlock: str, tick: int) -> None:
    """Words are earned: 'king' enters a chronicle only after the fusion occurred."""
    for e in c.repertoire.elements.values():
        if e.kind == "lexeme" and getattr(e, "unlock", None) == unlock and e.lapsed:
            e.lapsed = False
            e.weight = 0.5
            e.use_ema = 0.4
            e.origin = Origin(tick, "proposed", source=unlock)
