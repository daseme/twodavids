"""Every tuning knob in one place.

The handover doc's open question 3 (the tuning ridge) lives in this file:
beta_ideology too strong and every run ratchets (Althusser wins, the book
loses); too weak and nothing sticks (no tragedy). Treat changes here as
research moves, not cleanup.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Params:
    # --- world ---------------------------------------------------------------
    grid: int = 48
    n_cultures: int = 12
    ticks_per_year: int = 4            # tick = one season; native to the timestep
    generation_ticks: int = 80         # ~20 years; transmission attrition boundary

    # --- schismogenesis (the positive feedback loop) -------------------------
    gamma_schismo: float = 0.015       # repulsion step per contact tick
    salience_up: float = 0.06          # how fast contact makes an axis contested
    lambda_salience: float = 0.008     # predator 3: salience decays absent contact
    rho_exchange: float = 0.6          # predator 4: ritualized exchange damps repulsion
    exchange_duration: int = 24        # ticks a feast keeps an exchange edge warm
    symmetric_pop_ratio: float = 2.0   # rivalry needs rough parity, else complementary

    # --- material pricing (stochastic and pricing, never determining) --------
    kappa_extremity: float = 0.45      # predator 1: quadratic price of caloric extremity
    extremity_threshold: float = 0.6
    weather_sigma: float = 0.18
    growth_rate: float = 0.005         # demographic response to wellbeing, per tick
    growth_cap: float = 0.008
    min_pop: float = 120.0             # below this a culture dissolves (scar: abandonment)

    # --- repertoire transmission (ideology as biased reproduction) -----------
    beta_ideology: float = 0.8         # THE knob: bias toward elements reproducing dominance
    fitness_base: float = 0.25
    fitness_use: float = 0.5           # weight of the recency-of-use EMA
    eta_weight: float = 0.03           # per-tick weight learning rate (~2-3 gen loss horizon)
    use_decay: float = 0.02
    w_live: float = 0.15               # below this an element is lapsed (not banned — unarrived)
    lapse_ticks: int = 40              # ticks below w_live before lapsing
    frontier_noise: float = 0.012      # predator 2 fuel: variance regeneration at frontiers
    frontier_gap: float = 0.8          # mean |Δv| on an edge that counts as a frontier
    cohesion: float = 0.01             # per-tick pull of faction offsets toward the mean

    # --- contradiction accumulator (liberation mechanism 1) ------------------
    contradiction_decay: float = 0.03
    contradiction_theta: float = 5.0   # ~20-30 bad seasons before the gap speaks

    # --- deliberation economy -------------------------------------------------
    encounter_distance: float = 1.2    # value distance that makes contact an *encounter*
    encounter_prob: float = 0.05       # per eligible edge per tick (Kandiaronk is rare)
    recovery_prob: float = 0.008       # chronicler re-reads the old chronicle
    baseline_prob: float = 0.03        # cultural life goes on: occasional ordinary argument
    max_deliberations_per_tick: int = 6

    # --- domination tracks & fusion (the state as contingent fusion) ---------
    dom_gain: float = 0.006
    dom_decay: float = 0.0015
    refusal_erosion: float = 0.006     # live refusal stances eat command/violence tracks
    fusion_threshold: float = 0.7
    unfusion_threshold: float = 0.5
    ratchet_base: float = 0.002        # base chance a seasonal handoff fails
    ratchet_dom_pull: float = 0.03     # charisma+violence make the winter chief stay
    liberation_pop_cost: float = 0.97  # refusals are impressive because they cost

    # --- membership ------------------------------------------------------------
    defect_tolerance: float = 0.9      # faction offset norm that forces the question
    hospitality_min: float = 0.25      # edge openness needed to leave along it
    schism_min_weight: float = 0.22
    schism_min_pop: float = 600.0

    # --- chronicle -------------------------------------------------------------
    oral_survival: float = 0.75        # per generation; oral decays faster, resists capture
    written_survival: float = 0.985    # writing preserves but centralizes
    era_ticks: int = 200

    def to_dict(self) -> dict:
        return asdict(self)
