"""Phase 3: promotion. The model's stances go live and history forks.

Partial promotion by default: the liberation-typed deliberations —
contradiction, encounter, ratchet crisis, recovery — go to the model, and the
stub keeps the baseline chatter. These are the theoretically loaded choices:
whether the gap between promise and lived experience becomes refusal, whether
an outsider's argument takes root, whether a people un-kings itself.

Discipline, enforced at the API layer, not by parsing hope:
- The model chooses from the culture's live stance menu ONLY — the response
  schema's stance field is an enum of exactly the menu's ids. Thrownness as a
  constraint: an instantiated voice literally cannot argue moves its culture
  lacks.
- The model receives the ethnographic sketch, never numbers; the sim keeps
  the math. Split language from judgment.
- On any failure (API error, refusal, invalid stance) the call falls back to
  the stub, and the journal records which model actually decided each
  deliberation — so a mixed history remains exactly replayable.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np

from . import names
from .oracle import Situation, StubOracle, Utterance

DEFAULT_PROMOTED = frozenset({"contradiction", "encounter", "ratchet_crisis", "recovery"})

# How many consecutive stub fallbacks before a "promoted" run is no longer
# one. Generous enough to ride out a rate-limit squall or a brief outage.
MAX_FALLBACK_STREAK = 40

# Substrings of the API's terminal complaints: billing and access problems
# that no amount of waiting will resolve.
_TERMINAL_TEXT = ("credit balance", "billing", "quota", "payment",
                  "invalid x-api-key", "authentication_error",
                  "permission_error")


class PromotionUnavailable(RuntimeError):
    """The model can no longer decide; the run stops instead of degrading."""


class BudgetExhausted(PromotionUnavailable):
    """The run hit its own call ceiling and stopped itself.

    A promoted run's cost is not knowable up front: the model's choices
    change how many deliberations the world raises, and a feedback loop
    (see studies/promotion-interim.md) can inflate that several-fold
    mid-run. So the ceiling is declared, not discovered from a bill.
    """


def _is_terminal(exc: Exception) -> bool:
    import anthropic
    if isinstance(exc, (anthropic.AuthenticationError,
                        anthropic.PermissionDeniedError)):
        return True
    return any(t in str(exc).lower() for t in _TERMINAL_TEXT)

KIND_NOTES = {
    "contradiction": (
        "The gap has grown too wide to ignore: what the way of living promises "
        "and what this faction actually eats and endures no longer match. The "
        "gap itself is on the table."),
    "encounter": (
        "Travelers from another people sit at the fires tonight, and their "
        "questions are hard to answer well. One of the moves below may be a "
        "way of arguing that no one here has used before — an outsider's move, "
        "heard for the first time."),
    "ratchet_crisis": (
        "The season turned and the one who leads did not step down. The camps "
        "did not scatter as they always have. What is said in the next days "
        "may decide whether this is an outrage or the new way of things."),
    "recovery": (
        "The old tellings have been read or sung again, and they describe ways "
        "of living that no one now alive has practiced. It was done otherwise "
        "once; the question is whether that matters."),
}

# --- the neutral variant (studies/promotion-interim.md) ----------------------
# The audit of the first promoted run found four features of the prompt that
# could inflate the model's hospitality bias rather than reveal it. This
# variant removes them so the ablation isolates the model's own prior:
#
# 1. The encounter note staged a hosting scene ("travelers sit at the fires
#    tonight"), of which feast is the natural completion. NEUTRAL_NOTES name
#    the situation without staging its resolution.
# 2. The menu arrived alphabetised from the engine, so `affirm` was always
#    first. The neutral variant shuffles it per call, deterministically.
# 3. `feast` carried the most vivid and morally flattering gloss on the menu
#    ("giving until the ledger is shamed") while `invert` was abstract.
#    NEUTRAL_GLOSS levels register and concreteness across the moves.
#
# The fourth artifact — the stub receives Bateson as numeric priors that the
# model never sees — is deliberately NOT patched by injecting counter-theory.
# Telling the model that contact sharpens difference would swap one thumb on
# the scale for another. The question is what it does when the situation is
# described without a preferred answer, so the neutral variant is neutral,
# not counter-biased. This leaves the comparison honestly asymmetric, and the
# asymmetry is documented rather than hidden.
NEUTRAL_NOTES = {
    "contradiction": (
        "What the way of living promises and what this faction actually eats "
        "and endures have come apart, and the difference is now spoken of "
        "openly. The matter is before the people."),
    "encounter": (
        "A party from another people is here, and their ways are not ours. "
        "What passes between the two peoples now is undecided."),
    "ratchet_crisis": (
        "The season turned and the one who leads did not step down. The camps "
        "did not scatter as they always have. What is said in the next days "
        "may decide whether this is an outrage or the new way of things."),
    "recovery": (
        "The old tellings have been read or sung again, and they describe ways "
        "of living that no one now alive has practiced. It was done otherwise "
        "once; the question is whether that matters."),
}

# Same moves, levelled: comparable concreteness, no move carrying more moral
# glamour than its neighbours. Keyed by stance id; anything absent falls back
# to the sim's own gloss. These are presentation only — the sim's glosses in
# repertoire.py are untouched, because they feed prompt_hash and every
# existing journal replays against them.
NEUTRAL_GLOSS = {
    "affirm": "say our ways are good and should go on unchanged",
    "submit": "grant that those who lead should be obeyed in this",
    "refuse": "refuse what is asked, whatever it costs us",
    "mock": "meet the great one's claim with laughter",
    "leave": "strike camp and go to kin who will take us in",
    "invert": "do the opposite of what they do in this matter, on purpose",
    "emulate": "take up their way in this matter instead of ours",
    "remember": "do it again as the old tellings say it was done",
    "feast": "give a feast and spend our stores on them",
    "propose": "try a way no one here has tried",
}

SYSTEM = """You are the deliberative voice inside a generated pre-modern world — one faction's speaker in a moment of cultural argument.

The world is invented and its peoples are not yours: you will be given an ethnographic description of who they are, and you must choose and argue as THEY would — by their values, their pride, their fears — not as you would, and not as a modern person would. Their values may be repugnant or admirable; voice them faithfully either way.

Rules, none negotiable:
- Choose exactly one stance from the menu you are given, by its id. The menu is everything this people can currently think; there are no other moves.
- The choice must follow from the description of the people and the situation — not from what would be wise, kind, or interesting. A people that honors command will often submit. A people that laughs at bosses will often mock. Let them be who they are.
- Voice the argument in one to three sentences, in their register: concrete, spoken aloud to kin around a fire, no abstractions a herder would not use.
- No numerals. No modern vocabulary, no anachronism, no irony aimed at the speakers, no reference to anything outside their world.
- You are one voice, not a narrator: first person plural is natural ("we", "our dead", "our fires").

You will answer in JSON with the chosen stance id and the spoken argument, nothing else."""


class ClaudeOracle:
    """Live stance selection for promoted deliberation kinds; stub otherwise."""

    def __init__(self, seed: int, model: str = "claude-sonnet-5",
                 promoted: frozenset[str] = DEFAULT_PROMOTED,
                 variant: str = "original", max_calls: int | None = None) -> None:
        self.max_calls = max_calls
        self.model = model
        self.variant = variant
        # The variant rides in the model tag, so a journal says which prompt
        # produced it and an ablation cannot be mistaken for a rerun.
        self.tag = model if variant == "original" else f"{model}#{variant}"
        self.model_id = f"{self.tag}+stub"
        self.promoted = promoted
        self.rng = np.random.default_rng(seed ^ 0xC1A0DE)
        self.stub = StubOracle(self.rng)
        self.calls = 0
        self.fallbacks = 0
        self._streak = 0
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def deliberate_many(self, pairs: list[tuple[Situation, str]]) -> list[Utterance]:
        """Resolve a tick's deliberations simultaneously (design §3): promoted
        calls run concurrently, order preserved so the journal is deterministic."""
        from concurrent.futures import ThreadPoolExecutor
        promoted_idx = [i for i, (s, _) in enumerate(pairs)
                        if s.kind in self.promoted]
        out: list[Utterance | None] = [None] * len(pairs)
        for i, (s, sk) in enumerate(pairs):
            if s.kind not in self.promoted:
                out[i] = self.stub.deliberate(sk, s)
        if promoted_idx:
            with ThreadPoolExecutor(max_workers=min(6, len(promoted_idx))) as ex:
                futs = {ex.submit(self.deliberate, pairs[i][1], pairs[i][0]): i
                        for i in promoted_idx}
                for fut in futs:
                    out[futs[fut]] = fut.result()
        return [u for u in out]

    def deliberate(self, sketch: str, situation: Situation) -> Utterance:
        if situation.kind not in self.promoted:
            return self.stub.deliberate(sketch, situation)
        # Per-situation RNG so concurrent promoted calls never race on a shared
        # stream — speaker naming and any fallback stay deterministic under
        # thread order, keeping the journal exactly replayable.
        key = f"{self.model}|{situation.tick}|{situation.culture}|{situation.faction}"
        r = np.random.default_rng(
            int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big"))
        local_stub = StubOracle(r)
        speaker = names.person(r, situation.culture_name)
        if self.max_calls is not None and self.calls >= self.max_calls:
            raise BudgetExhausted(
                f"call ceiling reached: {self.calls} live deliberations at "
                f"tick {situation.tick}. Nothing is lost — resume with "
                f"dawn run --resume (raise or drop --max-calls to continue)")
        menu_ids = {s.eid for s in situation.menu}
        try:
            stance_id, argument = self._call(sketch, situation)
        except Exception as exc:
            # A promoted run that quietly finishes on stub decisions is worse
            # than one that stops: the journal looks complete and is not the
            # experiment. Credit exhaustion, bad keys and revoked access are
            # terminal — they will not fix themselves mid-run — so they end
            # the run and leave a resumable prefix. Transient failures still
            # fall back, but a long unbroken streak of them is terminal too.
            if _is_terminal(exc):
                raise PromotionUnavailable(
                    f"promotion cannot continue at tick {situation.tick}: "
                    f"{type(exc).__name__}: {exc}. The journal so far is "
                    f"intact — resume with: dawn run --resume") from exc
            self.fallbacks += 1
            self._streak += 1
            if self._streak >= MAX_FALLBACK_STREAK:
                raise PromotionUnavailable(
                    f"{self._streak} consecutive fallbacks ending at tick "
                    f"{situation.tick} (last: {type(exc).__name__}: {exc}) — "
                    f"stopping rather than writing a stub history under a "
                    f"promoted run's name. Resume with: dawn run --resume"
                ) from exc
            return local_stub.deliberate(sketch, situation)
        self._streak = 0
        if stance_id not in menu_ids or not argument:
            self.fallbacks += 1
            return local_stub.deliberate(sketch, situation)
        self.calls += 1
        text = (f"{speaker['name']} of the {situation.faction_name}, "
                f"{speaker['traits'][0]} and {speaker['traits'][1]}, stood and said: "
                f"“{argument}”")
        return Utterance(stance_id=stance_id, text=text, speaker=speaker,
                         model=self.tag)

    def _menu_order(self, situation: Situation) -> list:
        """Alphabetical (the engine's order) unless the neutral variant is
        running, which shuffles per call so no move owns first place. Seeded
        from the situation alone, so the same call always shows the same
        order and the ablation is reproducible."""
        if self.variant != "neutral":
            return list(situation.menu)
        key = f"{situation.tick}|{situation.culture}|{situation.faction}|{situation.kind}"
        r = np.random.default_rng(
            int.from_bytes(hashlib.sha256(key.encode()).digest()[8:16], "big"))
        menu = list(situation.menu)
        r.shuffle(menu)
        return menu

    def _call(self, sketch: str, situation: Situation) -> tuple[str, str]:
        notes = NEUTRAL_NOTES if self.variant == "neutral" else KIND_NOTES
        gloss = ((lambda s: NEUTRAL_GLOSS.get(s.eid, s.gloss))
                 if self.variant == "neutral" else (lambda s: s.gloss))
        menu = "\n".join(f"- {s.eid}: {gloss(s)}" for s in self._menu_order(situation))
        detail = {k: v for k, v in situation.detail.items() if k != "injected"}
        user = (
            f"The people, as an ethnographer would describe them:\n{sketch}\n\n"
            f"The situation: {notes.get(situation.kind, situation.kind)}\n"
            + (f"Particulars: {json.dumps(detail, sort_keys=True)}\n" if detail else "")
            + f"\nThe moves this people can think — choose exactly one by id:\n{menu}\n\n"
            f"Speak as one voice of the {situation.faction_name} among the "
            f"{situation.culture_name}. Choose the stance THIS people would choose, "
            f"and voice the argument for it."
        )
        schema = {
            "type": "object",
            "properties": {
                "stance": {"type": "string", "enum": sorted(s.eid for s in situation.menu)},
                "argument": {"type": "string"},
            },
            "required": ["stance", "argument"],
            "additionalProperties": False,
        }
        resp = self._get_client().messages.create(
            model=self.model,
            max_tokens=400,
            thinking={"type": "disabled"},
            system=[{"type": "text", "text": SYSTEM,
                     "cache_control": {"type": "ephemeral"}}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": user}],
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("model declined")
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        return data["stance"], data["argument"].strip()
