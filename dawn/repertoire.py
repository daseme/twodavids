"""The repertoire: stances, configurations, lexemes — and ideology as biased transmission.

This module is the answer to the handover doc's open question 1, and it encodes
the load-bearing synthesis (§2): ideology and freedom are one architecture.

- A society *holds a repertoire of structures*; a Configuration maps season ->
  structure, and the interesting variable is whether switching capacity survives.
- Every element carries a per-culture transmission weight. Each tick, weight
  chases a fitness biased (beta_ideology) toward elements whose alignment
  reproduces the currently dominant configuration. That bias IS ideology.
- Freedom-loss is differential reproduction: alternatives are never banned,
  they lapse — and after long enough with no surviving record and no neighbor
  who remembers, they are forgotten outright.
- Liberation re-enters lapsed elements via exactly three doors: contradiction,
  encounter, recovery. Those doors are implemented in the engine; this module
  only guarantees they *can* open (revive/forget bookkeeping).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .params import Params
from .values import (ACCUMULATION, CLOSED, COMMAND, DISPLAY, ELABORATE, N_AXES,
                     NOMADISM, RANK, VIOLENCE, vec)

SEASONS = ("spring", "summer", "autumn", "winter")


@dataclass
class Origin:
    tick: int
    mechanism: str          # primordial | proposed | borrowed | recovered
    source: str | None = None


@dataclass
class Element:
    eid: str
    kind: str               # stance | configuration | lexeme
    name: str
    gloss: str
    alignment: np.ndarray   # which value poles this element expresses/reproduces
    origin: Origin
    weight: float = 0.6     # transmission vitality, per holding culture
    use_ema: float = 0.3    # recency of exercise
    below_since: int | None = None
    lapsed: bool = False


@dataclass
class Stance(Element):
    delta: np.ndarray = field(default_factory=lambda: np.zeros(N_AXES))
    tags: frozenset[str] = frozenset()


@dataclass
class Configuration(Element):
    seasons: tuple[str, str, str, str] = ("band_camp",) * 4  # structure ids by season
    ratcheted: bool = False


@dataclass
class Lexeme(Element):
    register: str = "plain"   # plain | chiefly | statal
    unlock: str | None = None  # None | "chiefly" | "fusion" — words must be earned


# --- structures: what a season can be configured as ---------------------------

@dataclass(frozen=True)
class Structure:
    sid: str
    authority: str            # none | council | chief
    pooling: str              # share | redistribute | hoard
    settlement: str           # dispersed | aggregated
    roles: frozenset[str]     # chronicler, ritual-office, war-leader
    signature: np.ndarray     # the value profile this structure reproduces

    @property
    def authority_rank(self) -> int:
        return {"none": 0, "council": 1, "chief": 2}[self.authority]


STRUCTURES: dict[str, Structure] = {s.sid: s for s in [
    Structure("band_camp", "none", "share", "dispersed", frozenset(),
              vec(rank=-0.7, accumulation=-0.6, nomadism=0.5, command=-0.6, closed=-0.2)),
    Structure("council_hall", "council", "redistribute", "aggregated",
              frozenset({"ritual-office"}),
              vec(rank=-0.2, nomadism=-0.5, command=-0.1, elaborate=0.3)),
    Structure("chiefly_lodge", "chief", "redistribute", "aggregated",
              frozenset({"war-leader", "ritual-office"}),
              vec(rank=0.6, display=0.5, command=0.5, accumulation=0.3, nomadism=-0.3)),
    Structure("sacred_assembly", "council", "share", "aggregated",
              frozenset({"ritual-office", "chronicler"}),
              vec(elaborate=0.7, rank=-0.3, command=-0.3, display=0.2)),
    Structure("hoard_fort", "chief", "hoard", "aggregated",
              frozenset({"war-leader", "chronicler"}),
              vec(rank=0.8, accumulation=0.8, command=0.7, closed=0.5, violence=0.4,
                  nomadism=-0.6)),
]}


def config_signature(cfg: Configuration) -> np.ndarray:
    return np.mean([STRUCTURES[s].signature for s in cfg.seasons], axis=0)


# --- the repertoire container --------------------------------------------------

class Repertoire:
    def __init__(self) -> None:
        self.elements: dict[str, Element] = {}

    def add(self, e: Element) -> None:
        self.elements[e.eid] = e

    def get(self, eid: str) -> Element | None:
        return self.elements.get(eid)

    def live(self, kind: str | None = None) -> list[Element]:
        return [e for e in self.elements.values()
                if not e.lapsed and (kind is None or e.kind == kind)]

    def lapsed_elements(self, kind: str | None = None) -> list[Element]:
        """Lapsed-from-use elements. Locked vocabulary (unlock set) is excluded:
        'treasury' cannot be remembered into a world that never earned it."""
        return [e for e in self.elements.values()
                if e.lapsed and not getattr(e, "unlock", None)
                and (kind is None or e.kind == kind)]

    def revive(self, eid: str, tick: int, mechanism: str) -> Element | None:
        """A liberation door: contradiction/encounter/recovery re-enter a lapsed element."""
        e = self.elements.get(eid)
        if e is None or not e.lapsed:
            return None
        e.lapsed = False
        e.below_since = None
        e.weight = max(e.weight, 0.35)
        e.use_ema = 0.5
        e.origin = Origin(tick, "recovered", source=mechanism)
        return e

    def note_use(self, eid: str) -> None:
        e = self.elements.get(eid)
        if e is not None:
            e.use_ema = min(1.0, e.use_ema + 0.5)

    def transmission_tick(self, dominant_sig: np.ndarray, p: Params, tick: int,
                          frontier: bool, rng: np.random.Generator,
                          recorded: set[str], neighbor_live: set[str]) -> list[str]:
        """One season of biased reproduction. Returns eids forgotten outright.

        fitness = base + use·recency + beta·(alignment · dominant signature) + tag bonuses
        Weight chases fitness; elements below w_live for lapse_ticks lapse; a
        lapsed element with no surviving chronicle record and no living
        neighbor copy is deleted — not banned, simply failed to arrive.
        """
        forgotten: list[str] = []
        for e in list(self.elements.values()):
            e.use_ema *= (1.0 - p.use_decay)
            # Alignment vectors are sparse; /4 keeps the bias strong enough to
            # actually starve anti-dominant elements (that starvation IS ideology).
            align = float(np.dot(e.alignment, dominant_sig)) / 4.0
            bonus = 0.0
            if (isinstance(e, Stance) and "consent" in e.tags
                    and not e.alignment.any()):
                bonus += 0.10  # generic consent: every dominance smiles on 'affirm'
            if isinstance(e, Configuration) and e.eid_is_dominant:
                bonus += 0.35  # the running configuration reproduces itself
            fitness = float(np.clip(
                p.fitness_base + p.fitness_use * e.use_ema + p.beta_ideology * align + bonus,
                0.0, 1.0))
            e.weight += p.eta_weight * (fitness - e.weight)
            if frontier and e.kind == "stance" and not e.lapsed:
                e.weight = float(np.clip(e.weight + rng.normal(0, p.frontier_noise), 0.0, 1.0))
            if e.lapsed:
                if getattr(e, "unlock", None):
                    continue  # locked vocabulary waits to be earned, it does not rot
                if e.eid not in recorded and e.eid not in neighbor_live:
                    e.weight -= 0.004  # unrecorded memory rots
                    if e.weight <= 0.0:
                        del self.elements[e.eid]
                        forgotten.append(e.eid)
                continue
            if e.weight < p.w_live:
                if e.below_since is None:
                    e.below_since = tick
                elif tick - e.below_since >= p.lapse_ticks:
                    e.lapsed = True
            else:
                e.below_since = None
        return forgotten


# Configuration self-reproduction needs to know dominance; the engine stamps this
# each tick before transmission rather than the repertoire reaching outward.
Element.eid_is_dominant = False


# --- primordial stance menu (open question 4, first cut — every entry is theory) ---

def primordial_stances() -> list[Stance]:
    o = Origin(0, "primordial")

    def S(eid: str, gloss: str, alignment: np.ndarray, delta: np.ndarray,
          tags: set[str]) -> Stance:
        return Stance(eid=eid, kind="stance", name=eid, gloss=gloss,
                      alignment=alignment, origin=replace(o), delta=delta,
                      tags=frozenset(tags))

    return [
        S("affirm", "affirm that our ways are good and should continue as they are",
          np.zeros(N_AXES), np.zeros(N_AXES), {"consent"}),
        S("submit", "grant that those who lead should be obeyed in this",
          vec(command=0.9, rank=0.5), vec(command=0.10, rank=0.05), {"consent"}),
        S("refuse", "refuse the demand outright, whatever it costs",
          vec(command=-0.9, rank=-0.4), vec(command=-0.12), {"refusal"}),
        S("mock", "puncture the great one's pretension with laughter",
          vec(rank=-0.7, display=-0.6), vec(display=-0.08, rank=-0.08),
          {"refusal", "mockery"}),
        S("leave", "strike camp and go to kin who will take us in",
          vec(nomadism=0.8, closed=-0.5), vec(nomadism=0.10), {"exit"}),
        S("invert", "become in this matter the opposite of what our neighbors are",
          vec(closed=0.3), np.zeros(N_AXES), {"differentiate"}),
        S("emulate", "take up openly what the neighbors do better",
          vec(closed=-0.7), np.zeros(N_AXES), {"borrow"}),
        S("remember", "recall how it was done in the old days, and do it so again",
          vec(elaborate=0.3), np.zeros(N_AXES), {"memory"}),
        S("feast", "answer the tension with a feast, giving until the ledger is shamed",
          vec(accumulation=-0.7, display=0.4), vec(accumulation=-0.08, display=0.05),
          {"exchange"}),
        # New ways threaten whoever the current way serves: under a fused
        # dominance, 'propose' itself is what quietly fails to arrive.
        S("propose", "propose a way no one here has yet tried",
          vec(command=-0.5, rank=-0.3), np.zeros(N_AXES), {"proposal"}),
    ]


def primordial_configurations() -> list[Configuration]:
    o = Origin(0, "primordial")

    def C(eid: str, gloss: str, seasons: tuple[str, str, str, str]) -> Configuration:
        cfg = Configuration(eid=eid, kind="configuration", name=eid, gloss=gloss,
                            alignment=np.zeros(N_AXES), origin=replace(o),
                            seasons=seasons)
        cfg.alignment = config_signature(cfg)
        return cfg

    return [
        C("wandering", "dispersed bands the year round, gathering only to marry and trade",
          ("band_camp",) * 4),
        C("winter_lodge", "free bands in the warm seasons; a chief and police in the winter town",
          ("band_camp", "band_camp", "band_camp", "chiefly_lodge")),
        C("harvest_chief", "a commander for the harvest and the raid; no one's servant by the fires of winter",
          ("band_camp", "chiefly_lodge", "chiefly_lodge", "band_camp")),
        C("steady_council", "a settled village under a council that speaks long and rules little",
          ("council_hall",) * 4),
        C("ritual_round", "plain camps that fuse each winter into one great rite",
          ("band_camp", "band_camp", "band_camp", "sacred_assembly")),
    ]


def base_lexicon() -> list[Lexeme]:
    """No ossified political vocabulary: 'king', 'treasury', 'realm' must be earned."""
    o = Origin(0, "primordial")
    plain = ["camp", "council", "feast", "kin", "song", "boundary", "harvest",
             "herd", "elder", "speaker", "stranger", "gift"]
    lex = [Lexeme(eid=f"lex:{w}", kind="lexeme", name=w, gloss=w,
                  alignment=np.zeros(N_AXES), origin=replace(o), register="plain")
           for w in plain]
    chiefly = [("chief", vec(rank=0.5, command=0.4)), ("retinue", vec(rank=0.5, violence=0.3)),
               ("tribute", vec(accumulation=0.6, command=0.4))]
    lex += [Lexeme(eid=f"lex:{w}", kind="lexeme", name=w, gloss=w, alignment=a,
                   origin=replace(o), register="chiefly", unlock="chiefly", weight=0.0,
                   lapsed=True)
            for w, a in chiefly]
    statal = [("king", vec(rank=0.8, command=0.8)), ("realm", vec(closed=0.5, command=0.6)),
              ("treasury", vec(accumulation=0.9)), ("subject", vec(command=0.8)),
              ("decree", vec(command=0.9)), ("throne", vec(rank=0.9, display=0.6))]
    lex += [Lexeme(eid=f"lex:{w}", kind="lexeme", name=w, gloss=w, alignment=a,
                   origin=replace(o), register="statal", unlock="fusion", weight=0.0,
                   lapsed=True)
            for w, a in statal]
    return lex
