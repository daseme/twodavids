"""Phase 1 invariants: determinism, replay, the numeric/linguistic boundary,
and the repertoire mechanics (bias, lapse, recovery)."""

import re

import numpy as np
import pytest

from dawn.engine import Engine
from dawn.metrics import evaluate, nmi_culture_terrain
from dawn.oracle import ReplayOracle
from dawn.params import Params
from dawn.repertoire import (Origin, Repertoire, Stance, config_signature,
                             primordial_configurations, primordial_stances)
from dawn.values import N_AXES, sketch, vec


def test_same_seed_same_world():
    a = Engine(7, Params())
    b = Engine(7, Params())
    a.run(60)
    b.run(60)
    assert a.journal.content_hash() == b.journal.content_hash()


def test_different_seeds_differ():
    a = Engine(7, Params())
    b = Engine(8, Params())
    a.run(40)
    b.run(40)
    assert a.journal.content_hash() != b.journal.content_hash()


def test_replay_reproduces_journal():
    """Seed + journal = world, replayable forever without a model."""
    a = Engine(11, Params())
    a.run(80)
    oracle = ReplayOracle(a.journal.records)
    oracle.model_id = "stub-0"
    b = Engine(11, Params(), oracle=oracle)
    b.run(80)
    assert a.journal.content_hash() == b.journal.content_hash()


def test_sketch_contains_no_numbers():
    """The oracle must receive ethnographic prose, never raw numbers."""
    rng = np.random.default_rng(3)
    for _ in range(20):
        text = sketch(rng.uniform(-1, 1, N_AXES), rng.uniform(0, 1, N_AXES))
        assert not re.search(r"\d", text), text


def test_journal_sketches_have_no_numbers():
    e = Engine(5, Params())
    e.run(120)
    delibs = [r for r in e.journal.records if r["type"] == "deliberation"]
    assert delibs, "no deliberations in 120 ticks — trigger economy is broken"
    for d in delibs:
        assert not re.search(r"\d", d["sketch"]), d["sketch"]


def test_transmission_bias_discounts_the_unaligned():
    """Ideology: anti-dominant elements lapse; aligned ones survive unused."""
    p = Params()
    rep = Repertoire()
    for s in primordial_stances():
        rep.add(s)
    cfg = next(c for c in primordial_configurations() if c.eid == "wandering")
    rep.add(cfg)
    cfg.eid_is_dominant = True
    sig = config_signature(cfg)  # anti-rank, anti-command, anti-accumulation
    for e in rep.elements.values():
        e.use_ema = 0.0  # nobody exercises anything: pure bias, no practice
    for t in range(400):
        rep.transmission_tick(sig, p, t, frontier=False,
                              rng=np.random.default_rng(0),
                              recorded=set(), neighbor_live=set())
    submit = rep.get("submit")
    refuse = rep.get("refuse")
    assert submit is None or submit.lapsed, \
        "pro-command stance should fail to arrive under an anti-command dominant"
    assert refuse is not None and not refuse.lapsed, \
        "anti-command stance should keep arriving under an anti-command dominant"


def test_lapsed_element_can_be_recovered_then_forgotten():
    p = Params()
    rep = Repertoire()
    s = Stance(eid="x", kind="stance", name="x", gloss="x",
               alignment=vec(command=0.9), origin=Origin(0, "primordial"),
               delta=np.zeros(N_AXES), tags=frozenset(), weight=0.05, use_ema=0.0)
    rep.add(s)
    sig = -vec(command=0.9)
    for t in range(p.lapse_ticks + 2):
        rep.transmission_tick(sig, p, t, False, np.random.default_rng(0), set(), set())
    assert rep.get("x").lapsed
    assert rep.revive("x", 100, "recovery") is not None
    assert not rep.get("x").lapsed
    # Lapse again with no record and no neighbor: it must eventually be deleted.
    rep.get("x").weight, rep.get("x").use_ema = 0.01, 0.0
    for t in range(1000):
        rep.transmission_tick(sig, p, t, False, np.random.default_rng(0), set(), set())
        if rep.get("x") is None:
            break
    assert rep.get("x") is None, "an unrecorded, unremembered element must be forgettable"


def test_long_run_stays_sane():
    e = Engine(2, Params())
    e.run(400)
    checks = evaluate(e)
    assert checks["sanity_bounds"]["pass"], checks["sanity_bounds"]
    for c in e.world.living():
        assert np.isfinite(c.mean).all()
        assert (np.abs(c.mean) <= 1.0).all()
        assert 0.0 <= c.domination.min() and c.domination.max() <= 1.0


def test_viz_report_builds_from_run_dir(tmp_path):
    import json
    from dawn.almanac import compile_almanac
    from dawn.viz import write_report, write_watch
    e = Engine(3, Params(), out_dir=tmp_path)
    e.run(160)
    (tmp_path / "ALMANAC.md").write_text(compile_almanac(tmp_path))
    out = write_report(tmp_path)
    html = out.read_text()
    assert out.name == "report.html"
    assert "__DATA__" not in html
    assert '"seed": 3' in html or '"seed":3' in html
    assert "The land is not the people" in html
    # watch mode: territory history must be present and the page must build
    snap = json.loads((tmp_path / "world.json").read_text())
    assert "owner0" in snap and "deltas" in snap
    watch = write_watch(tmp_path).read_text()
    assert "__DATA__" not in watch
    assert "unfolding" in watch


def test_narrate_with_mock_provider(tmp_path):
    """Phase 2 narration: offline, deterministic, lexicon backstop enforced."""
    import json
    from dawn.almanac import compile_almanac
    from dawn.prose import narrate
    from dawn.providers import MockProvider
    e = Engine(3, Params(), out_dir=tmp_path)
    e.run(200)
    (tmp_path / "ALMANAC.md").write_text(compile_almanac(tmp_path))
    result = narrate(tmp_path, MockProvider())
    assert result["completed"] > 0
    prose = [json.loads(l) for l in (tmp_path / "chronicle_prose.jsonl").open()]
    assert prose, "no prose entries written"
    # The mock always says 'king'; a 200-tick world has earned no fusion,
    # so the gate backstop must have stripped it from every unearned entry.
    events = [json.loads(l) for l in (tmp_path / "journal.jsonl").open()]
    if not any(r["type"] == "fusion" for r in events):
        for p in prose:
            assert "king" not in p["text"].lower(), p["text"]
    # The regenerated almanac carries the prose overlay.
    almanac = (tmp_path / "ALMANAC.md").read_text()
    assert "the old ones still speak" in almanac
    # And the journal is untouched: replay must still verify.
    journal = (tmp_path / "prose_journal.jsonl").read_text()
    assert "prompt_hash" in journal


def test_nmi_bounds():
    e = Engine(1, Params())
    v = nmi_culture_terrain(e.world)
    assert 0.0 <= v <= 1.0
