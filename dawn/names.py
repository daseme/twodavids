"""Deterministic name generation for cultures, persons, and minted stances."""

from __future__ import annotations

import numpy as np

_ONSETS = ["k", "t", "s", "m", "n", "w", "y", "h", "sh", "ts", "l", "r", "kw", "th", ""]
_VOWELS = ["a", "e", "i", "o", "u", "ai", "au", "ei"]
_CODAS = ["", "", "n", "l", "r", "s", "k", "m"]

_TRAITS = ["patient", "sharp-tongued", "grieving", "ambitious", "wry", "devout",
           "stubborn", "generous", "suspicious", "far-traveled", "young", "old",
           "scarred", "soft-spoken", "restless"]
_AGENDAS = ["wants the winter lodge kept", "wants their child well-married",
            "resents last year's division of the catch", "dreams of the old routes",
            "hopes to be remembered in the songs", "fears the neighbors' growing herds",
            "carries a grudge from the feast", "wants the boundary opened",
            "wants the boundary closed", "believes the rites have grown hollow"]


def _syllable(rng: np.random.Generator) -> str:
    return (_ONSETS[rng.integers(len(_ONSETS))]
            + _VOWELS[rng.integers(len(_VOWELS))]
            + _CODAS[rng.integers(len(_CODAS))])


def word(rng: np.random.Generator, n_syllables: int = 3) -> str:
    return "".join(_syllable(rng) for _ in range(n_syllables)).capitalize()


def culture_name(rng: np.random.Generator) -> str:
    return word(rng, int(rng.integers(2, 4)))


def person(rng: np.random.Generator, culture: str) -> dict:
    """Lazily instantiated notable: a voice, two traits, a one-line agenda."""
    t = rng.choice(len(_TRAITS), size=2, replace=False)
    return {"name": word(rng, int(rng.integers(2, 4))),
            "culture": culture,
            "traits": [_TRAITS[int(t[0])], _TRAITS[int(t[1])]],
            "agenda": _AGENDAS[int(rng.integers(len(_AGENDAS)))]}
