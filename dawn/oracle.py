"""The oracle: one narrow interface for all inference.

deliberate(sketch, situation) -> {stance, text}. The sketch is ethnographic
prose rendered by code (the numeric<->linguistic boundary is owned entirely by
the sim); the oracle selects a stance from the culture's *own* repertoire menu
and voices it. Split language from judgment: the model does rhetoric and
selection, the sim does math.

Phase 1 ships StubOracle (seeded RNG + templates) so the sim is a pure
function of the seed. ReplayOracle re-reads a journal so any world is
replayable forever without a model. The Claude-backed oracle is Phase 2/3 and
must implement this same protocol behind the provider abstraction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from . import names
from .repertoire import Stance
from .values import N_AXES


@dataclass
class Situation:
    kind: str                  # contradiction | encounter | recovery | ratchet_crisis | baseline
    culture: int
    culture_name: str
    faction: str
    faction_name: str
    tick: int
    detail: dict
    menu: list[Stance]         # only moves this culture can currently think
    faction_values: np.ndarray # used by the stub's scoring, never shown as numbers

    def prompt_summary(self) -> str:
        moves = "; ".join(f"[{s.eid}] {s.gloss}" for s in self.menu)
        return (f"kind={self.kind} tick={self.tick} culture={self.culture_name} "
                f"faction={self.faction_name} detail={json.dumps(self.detail, sort_keys=True)} "
                f"menu: {moves}")


@dataclass
class Utterance:
    stance_id: str
    text: str
    speaker: dict
    model: str | None = None   # which model actually decided (mixed oracles)


class Oracle(Protocol):
    model_id: str

    def deliberate(self, sketch: str, situation: Situation) -> Utterance: ...


_SITUATION_BIAS = {
    # Which moves a situation makes thinkable-first. Theory, not tuning:
    # contradiction opens the door to refusal and exit; encounter to borrowing
    # and differentiation; recovery to memory.
    "contradiction": {"refuse": 0.8, "leave": 0.5, "mock": 0.5, "propose": 0.3},
    "encounter": {"emulate": 0.7, "invert": 0.7, "feast": 0.3, "propose": 0.2},
    "recovery": {"remember": 1.0},
    "ratchet_crisis": {"refuse": 0.9, "leave": 0.6, "mock": 0.6, "submit": 0.4},
    "baseline": {"affirm": 0.4, "feast": 0.2},
}

_VOICE = {
    "affirm": "Our ways carried our mothers and fathers; they will carry us. Let nothing be moved.",
    "submit": "There must be one voice in this, or we scatter. Let {leader} speak and be obeyed.",
    "refuse": "We were not born owing this. Let them hunger for our obedience; we refuse.",
    "mock": "Great one! So tall this winter — shall we carry you, or will you walk like a person?",
    "leave": "The land is wide and our kin at {route} keep an open door. We will not stay to be counted.",
    "invert": "Let the {neighbor} keep their way; by it we now know what we are not. We turn from it.",
    "emulate": "The {neighbor} do this better than we do, and pride is a poor meal. We will learn it.",
    "remember": "The old ones did not live as we now live. It was done otherwise once; it can be done otherwise again.",
    "feast": "Bring out everything. Let the tally die of shame, and let no one leave hungry or unbound.",
    "propose": "No one has tried this — not the old ones, not the neighbors. Hear me out.",
}


class StubOracle:
    """Seeded, deterministic stance selection with templated speech."""

    model_id = "stub-0"

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng

    def deliberate(self, sketch: str, situation: Situation) -> Utterance:
        bias = _SITUATION_BIAS.get(situation.kind, {})
        scores = []
        for s in situation.menu:
            fit = float(np.dot(situation.faction_values, s.alignment)) / N_AXES
            scores.append(2.5 * fit + bias.get(s.eid, 0.0) + 0.6 * s.weight
                          + self.rng.gumbel(0, 0.25))
        chosen = situation.menu[int(np.argmax(scores))]
        speaker = names.person(self.rng, situation.culture_name)
        line = _VOICE.get(chosen.eid, chosen.gloss)
        line = line.format(leader="the one who leads",
                           neighbor=situation.detail.get("neighbor", "neighbors"),
                           route=situation.detail.get("route", "the far camps"))
        text = (f"{speaker['name']} of the {situation.faction_name}, "
                f"{speaker['traits'][0]} and {speaker['traits'][1]}, stood and said: "
                f"“{line}”")
        return Utterance(stance_id=chosen.eid, text=text, speaker=speaker,
                         model=self.model_id)


class ReplayOracle:
    """Reads a prior journal: seed + journal = world, forever, no model needed."""

    model_id = "replay"

    def __init__(self, journal_lines: list[dict]) -> None:
        self.responses: dict[tuple[int, int, str], dict] = {}
        for rec in journal_lines:
            if rec.get("type") == "deliberation":
                k = (rec["tick"], rec["culture"], rec["faction"])
                self.responses[k] = rec

    def deliberate(self, sketch: str, situation: Situation) -> Utterance:
        rec = self.responses[(situation.tick, situation.culture, situation.faction)]
        return Utterance(stance_id=rec["stance"], text=rec["text"],
                         speaker=rec["speaker"], model=rec.get("model"))


def prompt_hash(sketch: str, situation: Situation) -> str:
    return hashlib.sha256(
        (sketch + "\n" + situation.prompt_summary()).encode()).hexdigest()[:16]
