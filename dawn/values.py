"""The fixed eight-axis value basis and the numeric<->linguistic boundary.

The basis is universal to the engine; *salience* of an axis is local to each
culture (cultures differentiate only along dimensions their contact history
has made contested). +1 is always the first-named pole from the handover doc.

sketch() is the only sanctioned way to turn a value vector into words: the
oracle must always receive ethnographic prose, never raw numbers.
"""

from __future__ import annotations

import numpy as np

N_AXES = 8
RANK, DISPLAY, NOMADISM, CLOSED, ACCUMULATION, COMMAND, ELABORATE, VIOLENCE = range(N_AXES)

POS = ["rank", "display", "nomadism", "closed", "accumulation",
       "command", "sacred-elaborate", "violence-honored"]
NEG = ["equality", "modesty", "settled", "open", "distribution",
       "refusal", "sacred-plain", "violence-shamed"]

# Axes whose positions carry the heaviest material coefficients (§2: caloric axes).
CALORIC_AXES = (NOMADISM, ACCUMULATION)

# Axes where rivalry tends to escalate in the same direction (Bateson's
# symmetrical mode: potlatch-like display contests, feud honor, rank races).
RIVALROUS_AXES = frozenset({RANK, DISPLAY, VIOLENCE})


def vec(**kw: float) -> np.ndarray:
    """Build a value/alignment vector from axis names, e.g. vec(command=-0.9)."""
    idx = {"rank": RANK, "display": DISPLAY, "nomadism": NOMADISM, "closed": CLOSED,
           "accumulation": ACCUMULATION, "command": COMMAND, "elaborate": ELABORATE,
           "violence": VIOLENCE}
    v = np.zeros(N_AXES)
    for k, x in kw.items():
        v[idx[k]] = x
    return v


def soft_step(v: np.ndarray, dv: np.ndarray) -> np.ndarray:
    """Move v by dv, damped near the poles so values approach but never pin at ±1.

    Irreversibility may only ever be emergent (probabilities asymptoting),
    never hard-coded; the damping keeps extremes reachable but unstable.
    """
    return np.clip(v + dv * (1.0 - np.abs(v)), -1.0, 1.0)


# --- the sketch renderer: value vector -> ethnographic prose -----------------

_PHRASES = {
    RANK: ("some houses stand above others and expect to be served",
           "no one may give another an order by right of birth"),
    DISPLAY: ("wealth and prowess are shown openly, and shame falls on the plain",
              "boasting is met with laughter; the admired hold themselves small"),
    NOMADISM: ("they strike camp with the seasons and despise those who root themselves",
               "they are bound to their fields and houses and pity the wanderer"),
    CLOSED: ("strangers are kept at the boundary and watched",
             "the stranger's bowl is filled first; their doors have no bars"),
    ACCUMULATION: ("granaries and herds are gathered into few hands against the future",
                   "to keep more than you give is counted a kind of theft"),
    COMMAND: ("a word from those who lead is expected to be obeyed",
              "commands are things one is free to laugh at and walk away from"),
    ELABORATE: ("their rites are long, costly, and exact, and much turns on them",
                "their dealings with the sacred are brief and plain"),
    VIOLENCE: ("the killer of enemies is honored and retold",
               "those who shed blood must be cleansed and are not praised"),
}

_INTENSITY = ((0.75, "Above all, "), (0.45, ""), (0.15, "Somewhat, "))


def sketch(values: np.ndarray, salience: np.ndarray | None = None,
           min_axes: int = 3) -> str:
    """Render a value vector as prose. Salient axes speak even when mild."""
    order = np.argsort(-np.abs(values))
    lines: list[str] = []
    for k in order:
        a = abs(float(values[k]))
        salient = salience is not None and float(salience[k]) > 0.4
        if a < 0.15 and not (salient and a > 0.05) and len(lines) >= min_axes:
            continue
        if a < 0.05:
            continue
        prefix = next(p for cut, p in _INTENSITY if a >= cut or cut == 0.15)
        phrase = _PHRASES[k][0] if values[k] > 0 else _PHRASES[k][1]
        contested = " — and this is contested ground with their neighbors" if salient else ""
        lines.append(f"{prefix}{phrase}{contested}.")
    if not lines:
        lines.append("They are unremarkable in their ways, holding no value to an extreme.")
    return " ".join(s[0].upper() + s[1:] for s in lines)
