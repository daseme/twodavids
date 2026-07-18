"""Cultures as distributions (mean + weighted factions), never points.

Internal variance is not noise — it is the fuel for liberation events.
A culture is also a polity for Phase 1 (one node on the hospitality graph,
one set of domination tracks); polities that span cultures are later work.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .repertoire import (SEASONS, Configuration, Repertoire, Structure,
                         STRUCTURES, config_signature)
from .values import CLOSED, N_AXES

VIOLENCE_T, INFO_T, CHARISMA_T = range(3)  # the three independent domination tracks


@dataclass
class Faction:
    fid: str
    name: str
    weight: float                 # share of the culture's population
    offset: np.ndarray            # value offset from the cultural mean
    contradiction: float = 0.0    # the accumulator: lived vs. promised
    lived: float = 0.5            # last tick's realized wellbeing


@dataclass
class Culture:
    cid: int
    name: str
    mean: np.ndarray
    salience: np.ndarray          # which axes contact history has made contested
    factions: list[Faction]
    repertoire: Repertoire
    pop: float
    dominant_config: str          # eid of the configuration currently reproduced
    domination: np.ndarray = field(default_factory=lambda: np.zeros(3))
    fused: bool = False
    fused_since: int | None = None
    alive: bool = True
    notables: dict[str, dict] = field(default_factory=dict)
    handoffs_ok: int = 0
    handoffs_total: int = 0

    def values_of(self, f: Faction) -> np.ndarray:
        return np.clip(self.mean + f.offset, -1.0, 1.0)

    def config(self) -> Configuration:
        cfg = self.repertoire.get(self.dominant_config)
        assert isinstance(cfg, Configuration)
        return cfg

    def structure(self, tick: int) -> Structure:
        return STRUCTURES[self.config().seasons[tick % 4]]

    def dominant_signature(self) -> np.ndarray:
        return config_signature(self.config())

    def openness(self) -> float:
        return float((1.0 - self.mean[CLOSED]) / 2.0)

    def chronicler_kind(self, tick: int) -> str | None:
        """Oral vs. written: who can write history is a property of the configuration."""
        s = self.structure(tick)
        if "chronicler" in s.roles and s.settlement == "aggregated":
            return "written"
        if "ritual-office" in s.roles or "chronicler" in s.roles:
            return "oral"
        return None

    def is_switching(self) -> bool:
        """Does the current dominant configuration still change shape with the seasons?"""
        return len(set(self.config().seasons)) > 1

    def refusal_strength(self) -> float:
        """How alive the second freedom is: live refusal stances, weighted."""
        return sum(e.weight for e in self.repertoire.live("stance")
                   if "refusal" in getattr(e, "tags", frozenset()))

    def stamp_dominance(self) -> None:
        for e in self.repertoire.elements.values():
            e.eid_is_dominant = (e.eid == self.dominant_config)


def edge_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


@dataclass
class Edge:
    a: int
    b: int
    border: int = 0               # shared border cells (contact intensity)
    exchange_until: int = -1      # ritualized exchange predator: feast keeps it warm
    traffic: int = 0              # defections along this route (scar material)

    def openness(self, cultures: dict[int, Culture]) -> float:
        oa, ob = cultures[self.a].openness(), cultures[self.b].openness()
        return float(np.sqrt(max(oa, 0.0) * max(ob, 0.0)))
