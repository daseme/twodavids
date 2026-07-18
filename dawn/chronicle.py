"""The chronicle is an in-world object, not an output layer.

A culture has chroniclers only if its current structure supports the role.
Oral entries decay fast but resist capture; written entries persist but are
capturable when the information track fuses. Every chronicle is from
somewhere: tone is keyed to the chronicler-culture's values, and its lexicon
gates what it can say — no world writes 'king' before a fusion has earned it.

The reader-facing almanac is a meta-document compiled from surviving in-world
chronicles plus material traces, citing sources and honest about gaps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from .culture import Culture, INFO_T
from .params import Params
from .values import DISPLAY, ELABORATE, VIOLENCE
from .world import World


@dataclass
class Entry:
    eid: int
    tick: int
    author: int              # culture id; every chronicle is from somewhere
    medium: str              # written | oral
    event_type: str
    text: str
    cites: list[str] = field(default_factory=list)  # element eids this entry records
    surviving: bool = True
    redacted: bool = False


# Priority: the attention economy. A plague outranks a routine harvest.
PRIORITY = {"fusion": 10, "unfusion": 10, "ratchet": 9, "liberation": 9,
            "hardening": 8, "schism": 8,
            "extinction": 8, "deliberation": 5, "defection": 5, "proposal": 6,
            "encounter": 4, "feast": 3, "hard_winter": 3}
COOLDOWN = {"deliberation": 6, "feast": 12, "hard_winter": 8}


def _tone(c: Culture) -> dict:
    v = c.mean
    return {
        "open_phrase": ("In the year of which we now tell, " if v[ELABORATE] > 0.2
                        else ""),
        "grand": float(v[DISPLAY]) > 0.25,
        "martial": float(v[VIOLENCE]) > 0.25,
    }


def _gate(text: str, c: Culture) -> str:
    """Lexicon gating: statal/chiefly words are replaced unless earned and live."""
    live = {e.name for e in c.repertoire.live("lexeme")}
    swaps = {"king": "one who does not step down", "realm": "lands that answer him",
             "treasury": "guarded stores", "subject": "those who may not refuse",
             "decree": "word that may not be laughed at", "throne": "high seat",
             "chief": "winter leader", "retinue": "young men at his fire",
             "tribute": "taken share"}
    for w, plain in swaps.items():
        if w not in live:
            text = re.sub(rf"\b{w}\b", plain, text)
    return text


def render(event: dict, author: Culture, world: World) -> tuple[str, list[str]]:
    """Template grammar, annalist voice, tone keyed to the chronicler's vector."""
    t = _tone(author)
    et = event["type"]
    cites: list[str] = []
    other = world.cultures.get(event.get("other", -1))
    subj = world.cultures.get(event.get("culture", author.cid), author)
    name = subj.name if subj else "a people"
    epithet = ""
    if other is not None and other.cid != author.cid:
        d = float(np.abs(author.mean - other.mean).mean())
        epithet = " the unbending" if d > 0.5 else ""

    if et == "ratchet":
        body = (f"among the {name}, the chief did not step down when the ice broke, "
                f"and the camps did not scatter as they had always done. His retinue ate well.")
        if event.get("displaced"):
            # The chronicle keeps what the ratchet displaced: this citation is
            # the recovery door — a people can re-read its way back to the seasons.
            cites.append(event["displaced"])
    elif et == "fusion":
        body = (f"the one who leads the {name} now holds the spears, the stories, and the "
                f"admiration of the young together in one hand. They begin to speak of him as a king.")
    elif et == "unfusion":
        body = (f"what was joined among the {name} has come apart; the king is once more "
                f"only a man with a loud voice and fewer friends than before.")
    elif et == "hardening":
        body = (f"the winter leader of the {name} set his men to counting what each "
                f"family gathers, and to keeping it behind walls, and to writing it down. "
                f"The old people did not like the counting.")
    elif et == "liberation":
        body = (f"the {name} did what their fathers had forgotten could be done: "
                f"{event.get('note', 'they refused, and paid for it, and were lighter after')}.")
    elif et == "schism":
        body = (f"a part of the {name} went out from them over {event.get('why', 'an old grievance')} "
                f"and now calls itself the {event.get('new_name', 'Parted')}.")
    elif et == "defection":
        body = (f"families of the {name} crossed over to the {event.get('to_name', 'neighbors')}"
                f"{epithet}, who did not turn them away.")
    elif et == "extinction":
        body = (f"the fires of the {name} are cold. Their lands lie open and their songs "
                f"are sung, where they are sung at all, by strangers.")
    elif et == "deliberation":
        body = (f"there was long argument among the {name}. {event.get('text', '')} "
                f"And the matter settled toward {event.get('stance', 'no decision')}.")
        cites.append(event.get("stance", ""))
    elif et == "proposal":
        body = (f"one among the {name} proposed {event.get('gloss', 'a new way')}, "
                f"and it was not laughed down.")
        cites.append(event.get("eid", ""))
    elif et == "encounter":
        body = (f"travelers from the {event.get('other_name', 'far side')} sat at the fires of the "
                f"{name} and asked questions that were hard to answer well.")
    elif et == "feast":
        body = (f"the {name} feasted the {event.get('other_name', 'neighbors')} until the "
                f"tally was shamed, and the boundary between them softened.")
    elif et == "hard_winter":
        body = f"the winter was hard on the {name}, and the count of them is less."
    else:
        body = f"a thing worth telling happened among the {name}."

    if t["grand"]:
        body = body.replace("chief", "great chief").replace("feasted", "feasted magnificently")
    if t["martial"] and et in ("schism", "extinction"):
        body += " So it goes with the weak."
    text = _gate(t["open_phrase"] + body, author)
    return text[0].upper() + text[1:], [c for c in cites if c]


class ChronicleStore:
    def __init__(self) -> None:
        self.entries: list[Entry] = []
        self._next = 0
        self._cool: dict[tuple[int, str], int] = {}

    def maybe_record(self, event: dict, world: World, p: Params) -> Entry | None:
        et = event["type"]
        if PRIORITY.get(et, 0) <= 0:
            return None
        subj_cid = event.get("culture", -1)
        # The nearest chronicler writes it down — their own affairs first.
        candidates = [c for c in world.living() if c.chronicler_kind(world.tick)]
        if not candidates:
            return None
        author = next((c for c in candidates if c.cid == subj_cid), None)
        if author is None:
            # Neighbors' great events travel; small ones don't.
            if PRIORITY.get(et, 0) < 8:
                return None
            author = candidates[(subj_cid + world.tick) % len(candidates)]
        key = (author.cid, et)
        if world.tick < self._cool.get(key, -1):
            return None
        self._cool[key] = world.tick + COOLDOWN.get(et, 0)
        medium = author.chronicler_kind(world.tick) or "oral"
        text, cites = render(event, author, world)
        for lex in author.repertoire.live("lexeme"):
            if lex.name in text:
                author.repertoire.note_use(lex.eid)
        entry = Entry(eid=self._next, tick=world.tick, author=author.cid,
                      medium=medium, event_type=et, text=text, cites=cites)
        self._next += 1
        self.entries.append(entry)
        return entry

    def attrition(self, world: World, rng: np.random.Generator, p: Params) -> None:
        """Once a generation: oral decays fast but resists capture; writing
        persists but is redacted where the information track has fused."""
        for e in self.entries:
            if not e.surviving:
                continue
            if e.medium == "oral":
                if rng.random() > p.oral_survival:
                    e.surviving = False
            else:
                if rng.random() > p.written_survival:
                    e.surviving = False
                else:
                    author = world.cultures.get(e.author)
                    if (author and author.alive
                            and float(author.domination[INFO_T]) > p.fusion_threshold
                            and e.event_type in ("liberation", "unfusion", "ratchet",
                                                 "deliberation", "mock")):
                        e.redacted = True

    def recorded_ids(self, cid: int) -> set[str]:
        """Element eids a culture's surviving chronicle still cites (recovery door)."""
        return {c for e in self.entries
                if e.surviving and e.author == cid for c in e.cites}
