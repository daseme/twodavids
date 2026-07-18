"""Separate seeded RNG streams: nothing in history ever back-contaminates the map.

worldgen  — terrain, initial cultures, names of places/peoples
history   — material draws, drift noise, demography, triggers
oracle    — the stub oracle's stance choices (isolated so promoting the real
            model in Phase 3 changes *only* this stream's consumers)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Streams:
    seed: int
    worldgen: np.random.Generator
    history: np.random.Generator
    oracle: np.random.Generator

    @classmethod
    def from_seed(cls, seed: int) -> "Streams":
        ss = np.random.SeedSequence(seed)
        w, h, o = ss.spawn(3)
        return cls(seed=seed,
                   worldgen=np.random.default_rng(w),
                   history=np.random.default_rng(h),
                   oracle=np.random.default_rng(o))
