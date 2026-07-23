"""Phase 1 invariants: determinism, replay, the numeric/linguistic boundary,
and the repertoire mechanics (bias, lapse, recovery)."""

import re
from pathlib import Path

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


def test_promotion_stops_rather_than_degrading():
    """A promoted run must not quietly finish on stub decisions: billing and
    auth failures are terminal, and a long streak of transient ones is too."""
    from dawn.claude_oracle import ClaudeOracle, PromotionUnavailable
    from dawn.oracle import Situation
    from dawn.repertoire import primordial_stances

    sit = Situation(kind="encounter", culture=0, culture_name="Aa",
                    faction="0.0", faction_name="Bb", tick=7, detail={},
                    menu=primordial_stances(), faction_values=np.zeros(8))
    billing = RuntimeError("Error code: 400 - 'Your credit balance is too low'")

    o = ClaudeOracle(1)
    o._call = lambda *a, **k: (_ for _ in ()).throw(billing)
    with pytest.raises(PromotionUnavailable):
        o.deliberate("sketch", sit)          # terminal: stops on the first one

    o = ClaudeOracle(1)
    o._call = lambda *a, **k: (_ for _ in ()).throw(TimeoutError("blip"))
    with pytest.raises(PromotionUnavailable):
        for _ in range(60):
            o.deliberate("sketch", sit)      # transient, but unbroken: stops

    o = ClaudeOracle(1)                      # intermittent: rides it out
    n = {"i": 0}

    def flaky(sketch, situation):
        n["i"] += 1
        if n["i"] % 7:
            raise TimeoutError("blip")
        return ("affirm", "we hold to our ways")

    o._call = flaky
    for _ in range(60):
        o.deliberate("sketch", sit)
    assert o.calls == 8 and o.fallbacks == 52


def test_viewer_boat_routing_is_water_to_water():
    """Boats interpolated between the two peoples' anchors sail over dry
    land, because anchors are on land. The route must run shore-to-shore
    across the water body the two peoples actually share."""
    tpl = (Path(__file__).parent.parent / "dawn" / "viewer_template.html").read_text()
    assert "function sharedBody(" in tpl
    assert "function shorePoint(" in tpl and "function bodyCentre(" in tpl
    # The hull path must be built from shore points, not raw anchors.
    voyage = tpl.split("const body = sharedBody(")[1].split("continue;")[0]
    assert "shorePoint(f.from, body, tick)" in voyage
    assert "shorePoint(f.to, body, tick)" in voyage
    assert "bodyCentre(body)" in voyage, "the path must bow through the water"


def test_max_calls_caps_the_spend():
    """A promoted run's cost is not knowable up front, so the ceiling must be
    declarable — and the stop must be clean, not a silent degradation."""
    from dawn.claude_oracle import BudgetExhausted, ClaudeOracle
    from dawn.oracle import Situation
    from dawn.repertoire import primordial_stances

    sit = Situation(kind="encounter", culture=0, culture_name="Aa",
                    faction="0.0", faction_name="Bb", tick=7, detail={},
                    menu=primordial_stances(), faction_values=np.zeros(8))

    o = ClaudeOracle(1, max_calls=5)
    o._call = lambda *a, **k: ("affirm", "we hold to our ways")
    with pytest.raises(BudgetExhausted):
        for _ in range(50):
            o.deliberate("s", sit)
    assert o.calls == 5, "must stop at the ceiling, not past it"

    o = ClaudeOracle(1)                      # uncapped stays uncapped
    o._call = lambda *a, **k: ("affirm", "x")
    for _ in range(30):
        o.deliberate("s", sit)
    assert o.calls == 30


def test_neutral_prompt_variant_changes_only_what_the_model_sees():
    """The ablation prompt must move the model's view and nothing else: the
    sim's glosses feed prompt_hash, so touching them would break the replay
    of every existing journal."""
    from dawn.claude_oracle import ClaudeOracle
    from dawn.oracle import Situation
    from dawn.repertoire import primordial_stances

    # The engine hands the oracle an alphabetised menu (engine.menu_for),
    # which is the position bias the ablation removes; mimic that here.
    menu = sorted(primordial_stances(), key=lambda s: s.eid)
    sit = Situation(kind="encounter", culture=0, culture_name="Aa",
                    faction="0.0", faction_name="Bb", tick=7, detail={},
                    menu=menu, faction_values=np.zeros(8))

    orig, neu = ClaudeOracle(1), ClaudeOracle(1, variant="neutral")
    assert orig.tag == "claude-sonnet-5"
    assert neu.tag == "claude-sonnet-5#neutral"      # journals self-describe

    # Menu order: alphabetical for the original, shuffled but deterministic
    # for the ablation.
    a = [s.eid for s in orig._menu_order(sit)]
    b = [s.eid for s in neu._menu_order(sit)]
    assert a == sorted(a) and a[0] == "affirm"
    assert b != a and sorted(b) == sorted(a)
    assert b == [s.eid for s in neu._menu_order(sit)]   # reproducible

    # A different situation gets a different order (no fixed permutation).
    sit2 = Situation(kind="encounter", culture=1, culture_name="Aa",
                     faction="1.0", faction_name="Bb", tick=9, detail={},
                     menu=menu, faction_values=np.zeros(8))
    assert [s.eid for s in neu._menu_order(sit2)] != b

    # The sim's own data is untouched: glosses still say what repertoire says.
    feast = next(s for s in menu if s.eid == "feast")
    assert "ledger is shamed" in feast.gloss


def test_resume_continues_an_interrupted_run(tmp_path):
    """Interruption insurance: seed + journal prefix + live oracle = a valid
    continued world. The prefix must survive byte-identical, and the resumed
    journal must itself replay-verify."""
    import json
    from dawn.journal import read_journal
    from dawn.oracle import ResumeOracle, StubOracle
    from dawn.oracle import ReplayOracle as RO
    from dawn.rng import Streams

    full = tmp_path / "full"
    e = Engine(11, Params(), out_dir=full)
    e.run(80)
    e.journal.close()
    lines = (full / "journal.jsonl").read_text().splitlines(keepends=True)
    cut = int(len(lines) * 0.4)   # an abrupt kill, possibly mid-tick
    resumed = tmp_path / "resumed"
    resumed.mkdir()
    (resumed / "journal.jsonl").write_text("".join(lines[:cut]))

    records = read_journal(resumed / "journal.jsonl")
    prefix_delibs = [r for r in records if r["type"] == "deliberation"]
    oracle = ResumeOracle(records, StubOracle(Streams.from_seed(11).oracle))
    e2 = Engine(11, Params(), out_dir=resumed, oracle=oracle)
    e2.run(80)
    e2.journal.close()

    new = read_journal(resumed / "journal.jsonl")
    new_delibs = [r for r in new if r["type"] == "deliberation"]
    assert not oracle.replaying, "the whole prefix must be consumed"
    assert len(new_delibs) > len(prefix_delibs), "the run must continue past the cut"
    for a, b in zip(prefix_delibs, new_delibs):
        assert a == b, "the recorded prefix must survive byte-identical"
    # And the continued world is itself a valid journal: replay-verify it.
    replay = Engine(11, Params(), oracle=RO(new))
    replay.run(80)
    assert [r for r in replay.journal.records if r["type"] == "deliberation"] \
           == new_delibs


def test_viewer_directed_moves_are_flown_not_sprung():
    """A beat shot must be one planned path — focus, distance and pitch on a
    single clock — with long moves still cutting and the viewer's hand
    cancelling the flight. A spring-only rig composes the framing piecemeal,
    which reads as the camera changing its mind."""
    tpl = (Path(__file__).parent.parent / "dawn" / "viewer_template.html").read_text()
    shot = tpl.split("function frameShot(")[1].split("function flyTo(")[0]
    assert "flight = {u: 0" in shot, "a directed move must plan a flight"
    assert "cut, don't tour" in shot, "the rule against airline tours stands"
    step = tpl.split("if (flight) {")[1].split("// Critically-damped")[0]
    # One easing curve drives all three, so the shot composes together.
    assert step.count("(3 - 2 *") == 1
    for eased in ("cam.focus.lerpVectors", "cam.dist =", "cam.pitch ="):
        assert eased in step
    # The spring's state is written throughout, so handing over never lurches.
    assert "cam.vel.set(0, 0, 0)" in step
    for interrupt in ('pointerdown', 'wheel'):
        handler = tpl.split(f'addEventListener("{interrupt}"')[1].split("}, ")[0]
        assert "cancelFlight()" in handler, f"{interrupt} must cancel the flight"


def test_viewer_sound_is_seeded_ambience_off_until_asked():
    """Sound is ambience of what is drawn — wind, water, hearths — procedural
    from the seed (the same bundle roars the same way), silent until the
    viewer asks, and layered over no event the journal does not hold."""
    tpl = (Path(__file__).parent.parent / "dawn" / "viewer_template.html").read_text()
    section = tpl.split("// ---- sound:")[1].split("// ---- the director")[0]
    assert "Math.random" not in section, "the mix must be deterministic"
    assert "mulberry32(NSEED" in section, "the noise bed comes from the seed"
    assert "hash2(" in section, "the crackle is hashed quanta, not chance"
    assert "new (window.AudioContext" in section
    assert 'getElementById("sound")' in tpl
    assert 'setSound(!audioOn)' in tpl, "the button and the key both ask"
    step = section.split("function soundStep(now) {")[1]
    assert step.lstrip().startswith("if (!audio || !audioOn) return;")
    # Every layer is a drawn system heard: storm wind, shore water, hearth.
    for layer in ("winterSeverity", "DATA.water", "s.glow && s.mesh.visible",
                  "curDayness"):
        assert layer in section
    assert "sound: () =>" in tpl, "the mix must be checkable by a driver"


def test_viewer_wasd_walks_only_while_wandering():
    """The walk takes the keys: WASD drives and turns in wander mode, and
    the letters' other duties (dig, sound, the wander toggle itself) yield
    for the walk's duration — otherwise pressing W to go forward would
    leave the world instead."""
    tpl = (Path(__file__).parent.parent / "dawn" / "viewer_template.html").read_text()
    keydown = tpl.split('addEventListener("keydown"')[1]
    guard, *rest = keydown.splitlines()[1:]
    assert "wander" in guard and "walkKeys.add" in guard
    assert any('e.key === "w"' in ln for ln in rest), "the toggle returns above ground"
    assert 'addEventListener("keyup"' in tpl, "keys must release"
    step = tpl.split("if (walkKeys.size) {")[1].split("const drive")[0]
    assert '"KeyA"' in step and '"KeyD"' in step
    drive = tpl.split("const drive")[1].split(";")[0]
    assert '"KeyW"' in drive and '"KeyS"' in drive


def test_viewer_builds_from_run_dir(tmp_path):
    from dawn.viewer import write_viewer
    e = Engine(3, Params(), out_dir=tmp_path)
    e.run(160)
    out = write_viewer(tmp_path)
    html = out.read_text()
    assert out.name == "viewer.html"
    for placeholder in ("__DATA__", "__THREE_CORE_JS__", "__THREE_MODULE_JS__"):
        assert placeholder not in html
    # Self-contained: vendored three.js inline, nothing fetched from a host.
    assert "Three.js Authors" in html
    assert "<script src=" not in html and "import(\"http" not in html
    assert '"deliberations"' in html
    # Archaeologist mode reads attestation per author and cites by event key;
    # without cid and type every people renders unattested — a lie about the
    # record, and a silent one.
    assert '"cid"' in html and '"surviving"' in html


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


def test_promoted_oracle_mixed_journal_replays():
    """Phase 3 plumbing: a mixed stub+model history is exactly replayable,
    invalid model output falls back to the stub, and the journal records
    which model decided each deliberation."""
    from dawn.claude_oracle import ClaudeOracle

    class FakeClaude(ClaudeOracle):
        def _call(self, sketch, situation):
            # deterministic fake "model" keyed to the situation (not call order,
            # which is non-deterministic under the concurrent deliberate_many):
            # some situations return garbage to exercise the fallback path
            ids = sorted(s.eid for s in situation.menu)
            if (situation.tick + situation.culture) % 3 == 0:
                return "not_a_stance", "gibberish"
            return ("refuse" if "refuse" in ids else ids[0]), "We will not carry this."

    a = Engine(11, Params(), oracle=FakeClaude(11, model="fake-model"))
    a.run(300)
    delibs = [r for r in a.journal.records if r["type"] == "deliberation"]
    models = {d["model"] for d in delibs}
    promoted = [d for d in delibs if d["kind"] != "baseline"]
    assert promoted, "no promoted deliberations in 300 ticks"
    assert "fake-model" in models, models
    assert "stub-0" in models, models  # baseline chatter and fallbacks
    # every deliberation's stance is in the menu it was offered
    for d in delibs:
        assert d["stance"] in d["menu"]
    # replay: the mixed history reproduces bit-for-bit without any model
    oracle = ReplayOracle(a.journal.records)
    oracle.model_id = a.oracle.model_id if hasattr(a, "oracle") else "fake-model+stub"
    oracle.model_id = "fake-model+stub"
    b = Engine(11, Params(), oracle=oracle)
    b.run(300)
    assert a.journal.content_hash() == b.journal.content_hash()


def test_nmi_bounds():
    e = Engine(1, Params())
    v = nmi_culture_terrain(e.world)
    assert 0.0 <= v <= 1.0


def test_hydrology_invariants():
    """Rivers flow downhill to water or the edge; water is uninhabited;
    named geography exists; water never determines culture placement."""
    coastal = 0
    for seed in range(1, 9):
        e = Engine(seed, Params())
        w = e.world
        g = w.params.grid
        assert w.water is not None and w.river is not None
        assert (w.owner[w.water > 0] == -1).all(), "water cells must be uninhabited"
        assert w.river.any(), "every world has at least one river"
        assert any(f["kind"] == "river" for f in w.features)
        for x, y, x2, y2 in w.river_segments:
            assert w.elevation[x2, y2] <= w.elevation[x, y] + 0.05  # filled surface may flatten
        if (w.water == 1).any():
            coastal += 1
            assert any(f["kind"] == "sea" for f in w.features)
        assert 0.0 <= nmi_culture_terrain(w) <= 1.0
    assert coastal >= 1, "a share of seeds should be coastal"


def test_water_contact_infrastructure():
    """Waterside borders and sea routes carry contact weight."""
    for seed in range(1, 12):
        e = Engine(seed, Params())
        edges = e.world.edges.values()
        if any(x.water_frac > 0 for x in edges) or any(x.sea_route for x in edges):
            return
    raise AssertionError("no water-weighted contact found in 11 worlds")
