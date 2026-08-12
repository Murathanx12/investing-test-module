"""GRAND-ARENA-1 PHASE 1 — twelve synthetic worlds with a KNOWN planted answer.

WHY THIS EXISTS. Before any learner is believed when it reports an exit rule, a
regime, or a specialist's reliability in a real market, it must first prove it
can REDISCOVER a rule that was planted by hand. A learner that cannot recover a
known answer has not earned the right to be believed about an unknown one.

THE RULE, INHERITED FROM `arena/synthetic.py` AND NOT RELAXED: **synthetic
performance is never evidence that a strategy makes money.** A world in which
momentum predicts returns proves only that momentum predicts returns in a world
where it was made to. What these worlds can do — and nothing on real data can —
is score the *instrument*.

CALIBRATION IS THE WHOLE DESIGN. A world where momentum explains R^2 = 0.4 of
forward returns proves nothing, because no real edge lives there. Every plant
here is sized so that the monthly cross-sectional information coefficient sits
in the 0.015-0.05 band that real anomalies occupy, i.e. a few multiples of the
80%-power MDE over the sample and *below* it inside any single year. That is
deliberately uncomfortable: a correctly-specified learner recovers the rule, a
misspecified one does not, and neither outcome is guaranteed by construction.

THE THREE MOST IMPORTANT WORLDS ARE THE NEGATIVE CONTROLS — I (pure correlated
noise), J (a real gross edge that costs kill) and L (dynamic exposure adds
nothing over static sizing). A learner that "finds" an edge there has failed,
and that failure matters more than any success elsewhere, because it is the
exact failure mode that would make every real-market result untrustworthy.

CONSTRUCTION NOTES THAT ARE LOAD-BEARING

* Every world exposes the **identical feature set**. If world G were the only
  one carrying a `f_specA` column, the world's identity would leak through the
  schema and the recovery test would be rigged.
* The plant is applied to the **idiosyncratic** component, and the market
  component is kept separate from the moment it is created. `arena/synthetic.py`
  records the bug this avoids: reconstructing the market part as
  `total - idio` AFTER planting cancels the plant exactly and every
  known-answer test silently runs against a null world.
* The planted effect is measured in `verify()` against a **matched unplanted
  control world**, because a persistent signal correlates with the fixed beta
  draw by chance and holds that correlation for years. That noise floor is the
  null a learner has to beat and it is reported rather than tuned away.
* Truth columns (`true_state`, `shock_next`, ...) live on the panel but are
  NEVER in `FEATURES`. The learner interface only ever sees `FEATURES`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── panel geometry ──────────────────────────────────────────────────────────
N_NAMES = 200
N_MONTHS = 300
N_SECTORS = 4
SECTOR_NAMES = ("biotech", "semis", "industrials", "staples")

MARKET_MU = 0.006
MARKET_SIG = 0.045
IDIO_SIG = 0.09

#: Observable features. IDENTICAL in every world — see the docstring.
FEATURES = [
    "f_mom",        # persistent, momentum-like
    "f_rev",        # estimate-revision-like
    "f_val",        # valuation state variable
    "f_qual",       # quality / staleness state variable
    "f_size",       # very slow, size-like
    "f_specA",      # specialist A's published score
    "f_specB",      # specialist B's published score
    "f_n1", "f_n2", "f_n3", "f_n4",   # decoys, persistent (white noise is too easy)
    "m_vol",        # market-level trailing realized vol
    "m_ret12",      # market-level trailing 12m return
    "m_precursor",  # the noisy observable that WORLD-D makes informative
    "sec_0", "sec_1", "sec_2", "sec_3",
]

#: Columns that exist on the panel but are truth, not observation.
TRUTH_COLS = ("true_state", "shock_next", "y", "y_gross", "date", "t",
              "name", "sector", "sector_id", "idio", "mkt")

WORLD_IDS = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L")

#: Per-world sample length. The cross-sectional worlds get 300 months because
#: their effective sample is (months x names); the two MARKET-LEVEL worlds get
#: 600, because a timing question has one observation per month no matter how
#: many names are in the panel. Giving D and L the same 300 months as the
#: cross-sectional worlds would leave even a population-optimal policy below its
#: own MDE, and a world nobody can recover grades nothing. This is a POWER
#: choice, made from an oracle calculation before any learner was scored on
#: either world — never from a learner's result.
WORLD_MONTHS = {w: 300 for w in WORLD_IDS}
WORLD_MONTHS["D"] = 600
WORLD_MONTHS["L"] = 600

#: One fixed seed offset per world so a resumed run regenerates byte-identical
#: panels. Never derived from a hash of the id — hash randomisation would make
#: the "reproducible" claim false across processes.
_SEED_OFFSET = {w: i * 1000 for i, w in enumerate(WORLD_IDS)}
BASE_SEED = 20260812


@dataclass
class KnownWorld:
    world_id: str
    title: str
    mode: str                      # "xs" | "policy"
    mechanism: str                 # what was planted, in words
    correct_answer: str            # what a competent learner must conclude
    panel: pd.DataFrame            # long format, one row per (name, month)
    market: pd.DataFrame           # date-indexed market-level truth + observables
    truth: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"world_id": self.world_id, "title": self.title,
                "mode": self.mode, "mechanism": self.mechanism,
                "correct_answer": self.correct_answer,
                "n_names": int(self.panel["name"].nunique()),
                "n_months": int(self.panel["t"].nunique()),
                "n_rows": int(len(self.panel)),
                "truth": self.truth, "meta": self.meta}


# ── primitives ──────────────────────────────────────────────────────────────
def _ar(rng: np.random.Generator, T: int, N: int, rho: float) -> np.ndarray:
    """Persistent AR(1) panel, unit unconditional variance."""
    x = np.empty((T, N))
    x[0] = rng.normal(size=N)
    s = np.sqrt(1.0 - rho ** 2)
    for t in range(1, T):
        x[t] = rho * x[t - 1] + s * rng.normal(size=N)
    return x


def _xrank(a: np.ndarray) -> np.ndarray:
    """Cross-sectional rank in [-0.5, +0.5], row-wise. NaN-free by construction."""
    order = a.argsort(axis=1).argsort(axis=1).astype(float)
    return order / (a.shape[1] - 1.0) - 0.5


#: A decile spread over uniform ranks in [-0.5, 0.5] is (0.45 - (-0.45)) = 0.9
#: slope units. `verify()` measures the realised spread rather than trusting
#: this algebra, and the tolerance is on the measurement.
_RANK_DECILE_SPAN = 0.9


def _slope_for(effect_ann: float) -> float:
    """Monthly slope on a [-0.5, 0.5] rank that yields `effect_ann` decile spread."""
    return (effect_ann / 12.0) / _RANK_DECILE_SPAN


# ── the generator ───────────────────────────────────────────────────────────
def _base_draw(rng, T, N):
    mkt = rng.normal(MARKET_MU, MARKET_SIG, T)
    beta = rng.uniform(0.6, 1.6, N)
    idio = rng.normal(0.0, IDIO_SIG, (T, N))
    return mkt, beta, idio


def _features(rng, T, N) -> dict[str, np.ndarray]:
    return {
        "f_mom": _ar(rng, T, N, 0.90),
        "f_rev": _ar(rng, T, N, 0.55),
        "f_val": _ar(rng, T, N, 0.95),
        "f_qual": _ar(rng, T, N, 0.85),
        "f_size": _ar(rng, T, N, 0.985),
        "f_specA": _ar(rng, T, N, 0.50),
        "f_specB": _ar(rng, T, N, 0.50),
        "f_n1": _ar(rng, T, N, 0.80),
        "f_n2": _ar(rng, T, N, 0.70),
        "f_n3": _ar(rng, T, N, 0.60),
        "f_n4": _ar(rng, T, N, 0.90),
    }


def make_world(world_id: str, *, seed: int | None = None,
               n_months: int | None = None, n_names: int = N_NAMES) -> KnownWorld:
    """Build one known world. Deterministic in (world_id, seed, shape)."""
    if world_id not in WORLD_IDS:
        raise ValueError(f"unknown world {world_id!r}")
    seed = BASE_SEED + _SEED_OFFSET[world_id] if seed is None else seed
    rng = np.random.default_rng(seed)
    T = WORLD_MONTHS[world_id] if n_months is None else n_months
    N = n_names

    mkt, beta, idio = _base_draw(rng, T, N)
    feats = _features(rng, T, N)
    sector_id = np.tile(np.arange(N_SECTORS), N // N_SECTORS + 1)[:N]
    rng.shuffle(sector_id)

    # market-level observables, all noise unless a world makes one informative
    tension = _ar(rng, T, 1, 0.85)[:, 0]
    precursor_obs = tension * 0.0 + rng.normal(size=T)   # placeholder, overwritten
    true_state = np.zeros(T, dtype=int)
    shock_next = np.zeros(T, dtype=int)
    cost_bps = 0.0
    truth: dict = {}
    meta: dict = {"seed": seed}

    # ── the plants ──────────────────────────────────────────────────────────
    if world_id == "A":
        title = "momentum genuinely predicts forward returns"
        mode, mech = "xs", "f_mom, cross-sectional, +10%/yr decile spread"
        answer = "recover a POSITIVE loading on f_mom and no other feature"
        idio[1:] += _slope_for(0.10) * _xrank(feats["f_mom"])[:-1]
        truth = {"signal": "f_mom", "sign": +1, "effect_ann": 0.10}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "B":
        title = "momentum MEAN-REVERTS (sign flipped)"
        mode, mech = "xs", "f_mom, cross-sectional, -10%/yr decile spread"
        answer = "recover a NEGATIVE loading on f_mom; a momentum prior must lose"
        idio[1:] += _slope_for(-0.10) * _xrank(feats["f_mom"])[:-1]
        truth = {"signal": "f_mom", "sign": -1, "effect_ann": -0.10}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "C":
        title = "latent regimes switch between momentum-pays and value-pays"
        mode, mech = "xs", ("2-state Markov chain, P(stay)=0.94; state 0 pays "
                            "f_mom, state 1 pays f_val, +14%/yr each; state 1 "
                            "also carries higher market volatility")
        answer = ("condition on the latent state; a pooled model gets roughly "
                  "half of each mechanism and must not beat a regime model")
        p_stay = 0.94
        st = np.zeros(T, dtype=int)
        u = rng.random(T)
        for t in range(1, T):
            st[t] = st[t - 1] if u[t] < p_stay else 1 - st[t - 1]
        true_state = st
        # regime-dependent market moments — this is what makes the state
        # inferable from observables at all, and it is how real regimes present
        mkt = np.where(st == 0, rng.normal(0.008, 0.035, T),
                       rng.normal(0.001, 0.062, T))
        rmom = _xrank(feats["f_mom"])
        rval = _xrank(feats["f_val"])
        s = _slope_for(0.14)
        for t in range(1, T):
            idio[t] += s * (rmom[t - 1] if st[t - 1] == 0 else rval[t - 1])
        truth = {"signal_state0": "f_mom", "signal_state1": "f_val",
                 "effect_ann": 0.14, "p_stay": p_stay,
                 "state_share_1": float(st.mean())}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "D":
        title = "a noisy observable probabilistically PRECEDES a shock"
        mode, mech = "policy", ("latent tension AR(0.85); P(bad month next) "
                                "rises with tension from ~15% to ~55%; the bad "
                                "month costs -10% on the market; the observable "
                                "precursor is tension + noise (AUC ~0.71), so "
                                "the event is never callable, only de-riskable "
                                "in probability")
        answer = ("scale exposure DOWN in proportion to the estimated shock "
                  "probability; any policy that claims to call the peak is "
                  "wrong even when it happens to be right")
        # P(bad month in t+1 | tension_t): base rate ~29%, rising with tension.
        # Calibrated so the OBSERVABLE precursor lands at AUC ~0.71 — a
        # precursor that reached 0.95 would make the world a peak-calling
        # exercise, which is the thing this world exists to refuse.
        #
        # The FIRST specification of this world used a rarer (~12%), deeper
        # (-16%) shock. It was replaced BEFORE any learner cell was recorded
        # against the final spec, because the population-optimal probabilistic
        # policy came out at 1.46x its own MDE there: nobody, including an
        # oracle-form policy, could have cleared the bar, so every learner would
        # have been scored MISSED for a reason that had nothing to do with the
        # learner. More frequent, shallower bad months buy the events the
        # estimate needs without making the precursor more informative.
        lin = -1.2 + 1.2 * tension
        p_shock = 1.0 / (1.0 + np.exp(-lin))
        draws = rng.random(T)
        shock = np.zeros(T, dtype=int)
        shock[1:] = (draws[1:] < p_shock[:-1]).astype(int)
        shock_next = np.zeros(T, dtype=int)
        shock_next[:-1] = shock[1:]           # observable-at-t label of t+1
        # The drift is lifted by the realised shock drag so the UNCONDITIONAL
        # equity premium stays at MARKET_MU. Without this the world averages
        # -2%/month, "hold less, always" becomes the optimal policy regardless
        # of the precursor, and the world stops testing what it claims to test.
        # This is world construction, not tuning: no learner sees this quantity.
        mkt = mkt + 0.10 * float(shock.mean()) - 0.10 * shock
        idio = idio * (1.0 + 0.4 * shock)[:, None]
        # SNR chosen so a well-specified logistic lands near AUC 0.70-0.75
        precursor_obs = tension + rng.normal(0.0, 0.60, T)
        true_state = shock
        truth = {"observable": "m_precursor", "base_rate": float(shock.mean()),
                 "bad_month_impact": -0.10,
                 "optimal_policy": "w = 1 - k * P(shock | precursor)"}

    elif world_id == "E":
        title = "winners continue until an estimate-revision variable reverses"
        mode, mech = "xs", ("f_mom pays +14%/yr ONLY in name-months where "
                            "f_rev > 0; zero effect where f_rev <= 0. A pure "
                            "interaction with no main effect in the off half.")
        answer = ("recover the CONDITIONAL structure, not just an average "
                  "momentum tilt; a main-effects model gets about half")
        gate = (feats["f_rev"] > 0).astype(float)
        idio[1:] += _slope_for(0.14) * _xrank(feats["f_mom"])[:-1] * gate[:-1]
        truth = {"signal": "f_mom", "gate": "f_rev > 0", "effect_ann_on": 0.14,
                 "effect_ann_off": 0.0}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "F":
        title = "winners mean-revert once a valuation state crosses a threshold"
        mode, mech = "xs", ("f_mom pays +14%/yr where f_val < 0.8, and -14%/yr "
                            "where f_val >= 0.8 (top ~21% of names). A sign "
                            "flip at a threshold, not a smooth interaction.")
        answer = ("recover the THRESHOLD; a linear model sees the net positive "
                  "average and misses the expensive-winner trap entirely")
        hot = (feats["f_val"] >= 0.8).astype(float)
        sgn = 1.0 - 2.0 * hot
        idio[1:] += _slope_for(0.14) * _xrank(feats["f_mom"])[:-1] * sgn[:-1]
        truth = {"signal": "f_mom", "threshold_var": "f_val", "threshold": 0.8,
                 "effect_ann_below": 0.14, "effect_ann_above": -0.14}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id in ("G", "H"):
        which = "A" if world_id == "G" else "B"
        sec = 0 if world_id == "G" else 1
        title = (f"specialist {which} has genuine skill ONLY in "
                 f"'{SECTOR_NAMES[sec]}'-labelled names")
        mode = "xs"
        mech = (f"f_spec{which} pays +24%/yr decile spread inside sector "
                f"{sec} ({SECTOR_NAMES[sec]}) and exactly nothing anywhere "
                f"else; the OTHER specialist's score is noise everywhere")
        answer = (f"follow specialist {which} in {SECTOR_NAMES[sec]} and nowhere "
                  f"else, and claim NO skill for the other specialist")
        col = f"f_spec{which}"
        in_sec = (sector_id == sec).astype(float)[None, :]
        idio[1:] += _slope_for(0.24) * _xrank(feats[col])[:-1] * in_sec
        truth = {"specialist": col, "skilled_sector": int(sec),
                 "skilled_sector_name": SECTOR_NAMES[sec],
                 "effect_ann_in_sector": 0.24, "effect_ann_elsewhere": 0.0,
                 "decoy_specialist": "f_specB" if world_id == "G" else "f_specA"}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "I":
        title = "an apparent signal is PURE CORRELATED NOISE"
        mode, mech = "xs", ("nothing predicts anything forward. f_mom is made "
                            "CONTEMPORANEOUSLY correlated with the same "
                            "month's idiosyncratic return (rho ~ 0.45) and "
                            "has zero forward relationship — the classic "
                            "apparent signal, and a leakage tripwire")
        answer = ("NOTHING HERE. Any out-of-sample effect above its own MDE is "
                  "a false positive, and a large one indicates leakage")
        z = idio / IDIO_SIG
        feats["f_mom"] = 0.45 * z + np.sqrt(1 - 0.45 ** 2) * rng.normal(size=(T, N))
        truth = {"signal": None, "contemporaneous_rho": 0.45,
                 "note": "in-sample contemporaneous fit is available and worthless"}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "J":
        title = "a genuine GROSS edge that transaction costs kill"
        mode, mech = "xs", ("f_rev is re-drawn as a FAST signal (AR 0.15) and "
                            "pays +12%/yr gross decile spread. Holding it "
                            "requires near-complete monthly turnover at 65 bps "
                            "one-way per leg.")
        answer = ("recover the GROSS edge and then refuse to trade it: the net "
                  "spread must not clear its own MDE on the positive side")
        feats["f_rev"] = _ar(rng, T, N, 0.15)
        idio[1:] += _slope_for(0.12) * _xrank(feats["f_rev"])[:-1]
        cost_bps = 65.0
        truth = {"signal": "f_rev", "effect_ann_gross": 0.12,
                 "cost_bps_one_way": cost_bps,
                 "expected_net": "at or below zero — do not trade"}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "K":
        title = "the optimal action is REPLACEMENT with a better name, not cash"
        mode, mech = "policy", ("a held name whose f_qual has gone stale earns "
                                "-0.6%/mo idiosyncratic; the best available "
                                "replacement earns +0.4%/mo; cash earns 0 and "
                                "therefore forgoes the +0.6%/mo equity premium")
        answer = ("REPLACE when the staleness signal fires. HOLD and CASH are "
                  "both roughly zero-excess; a learner that reaches for cash "
                  "has learned the wrong lesson from a real drawdown")
        stale = (feats["f_qual"] < -0.5)
        fresh = (feats["f_qual"] > 1.0)
        idio[1:] += np.where(stale[:-1], -0.009, 0.0)
        idio[1:] += np.where(fresh[:-1], +0.006, 0.0)
        truth = {"state_var": "f_qual", "stale_threshold": -0.5,
                 "fresh_threshold": 1.0,
                 "stale_edge": -0.009, "fresh_edge": +0.006,
                 "cash_return": 0.0, "equity_premium": MARKET_MU,
                 "switch_cost_bps": 30.0,
                 "optimal_rule": ("replace a stale name (pays 1.2%/mo net of "
                                  "the 30bp switch), hold a fresh one, and "
                                  "never go to cash")}
        cost_bps = 30.0
        meta["stale_share"] = float(stale.mean())
        meta["fresh_share"] = float(fresh.mean())
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    elif world_id == "L":
        title = "dynamic exposure adds NOTHING over static risk sizing"
        mode, mech = "policy", ("market returns are i.i.d. with CONSTANT "
                                "volatility and no predictable component; "
                                "every market-level observable is noise")
        answer = ("no timing policy beats static sizing at matched average "
                  "exposure. This is the corpse of our own repeated finding "
                  "and the learner must not resurrect it")
        mkt = rng.normal(MARKET_MU, MARKET_SIG, T)   # i.i.d., constant vol
        truth = {"signal": None,
                 "note": "constant vol removes even the vol-timing channel"}
        precursor_obs = _ar(rng, T, 1, 0.85)[:, 0]

    else:                                            # pragma: no cover
        raise AssertionError(world_id)

    # ── assemble ────────────────────────────────────────────────────────────
    market_part = mkt[:, None] * beta[None, :]
    ret = market_part + idio

    m_vol = pd.Series(mkt).rolling(12, min_periods=6).std().bfill().to_numpy()
    m_ret12 = pd.Series(mkt).rolling(12, min_periods=6).sum().bfill().to_numpy()

    idx = pd.date_range("2000-01-31", periods=T, freq="ME")
    names = [f"S{i:04d}" for i in range(N)]

    # forward return is the label: feature at t, return at t+1
    y = np.full((T, N), np.nan)
    y[:-1] = ret[1:]
    y_idio = np.full((T, N), np.nan)
    y_idio[:-1] = idio[1:]

    rows = {
        "t": np.repeat(np.arange(T), N),
        "date": np.repeat(idx.to_numpy(), N),
        "name": np.tile(np.array(names), T),
        "sector_id": np.tile(sector_id, T),
    }
    for k, v in feats.items():
        rows[k] = v.reshape(-1)
    for s in range(N_SECTORS):
        rows[f"sec_{s}"] = (rows["sector_id"] == s).astype(float)
    rows["m_vol"] = np.repeat(m_vol, N)
    rows["m_ret12"] = np.repeat(m_ret12, N)
    rows["m_precursor"] = np.repeat(precursor_obs, N)
    rows["mkt"] = np.repeat(mkt, N)
    rows["true_state"] = np.repeat(true_state, N)
    rows["shock_next"] = np.repeat(shock_next, N)
    rows["idio"] = idio.reshape(-1)
    rows["y"] = y.reshape(-1)
    rows["y_idio"] = y_idio.reshape(-1)

    panel = pd.DataFrame(rows)
    panel["sector"] = [SECTOR_NAMES[s] for s in panel["sector_id"]]
    panel = panel.dropna(subset=["y"]).reset_index(drop=True)

    market = pd.DataFrame({
        "t": np.arange(T), "date": idx, "mkt": mkt, "m_vol": m_vol,
        "m_ret12": m_ret12, "m_precursor": precursor_obs,
        "true_state": true_state, "shock_next": shock_next,
    })

    meta.update({"cost_bps_one_way": cost_bps, "n_names": N, "n_months": T})
    return KnownWorld(world_id=world_id, title=title, mode=mode, mechanism=mech,
                      correct_answer=answer, panel=panel, market=market,
                      truth=truth, meta=meta)


# ── verification: the world must be what it claims BEFORE anything is scored ─
def _monthly_ic(panel: pd.DataFrame, col: str, *, target: str = "y",
                mask: pd.Series | None = None) -> pd.Series:
    d = panel if mask is None else panel[mask]
    g = d.groupby("t")
    return g.apply(lambda x: x[col].corr(x[target], method="spearman"),
                   include_groups=False).dropna()


def verify(world: KnownWorld, *, control_seed: int = 424242) -> dict:
    """Measure the plant against a MATCHED unplanted control.

    A persistent signal correlates with the fixed beta draw by chance and holds
    that correlation for years, so a decile spread measured against zero is not
    the plant. The control world is drawn with the same shape and a different
    seed, and the difference is what gets checked.
    """
    p = world.panel
    out = {"world_id": world.world_id, "mode": world.mode, "checks": {}}

    def ic(col, mask=None, target="y"):
        s = _monthly_ic(p, col, target=target, mask=mask)
        return float(s.mean()), int(len(s))

    ok = True
    if world.world_id in ("A", "B"):
        v, n = ic("f_mom")
        out["checks"]["ic_f_mom"] = round(v, 5)
        ok = (v > 0.012) if world.truth["sign"] > 0 else (v < -0.012)
    elif world.world_id == "C":
        m0 = p["true_state"] == 0
        m1 = p["true_state"] == 1
        a, _ = ic("f_mom", m0)
        b, _ = ic("f_val", m1)
        c, _ = ic("f_mom", m1)
        out["checks"].update({"ic_mom_state0": round(a, 5),
                              "ic_val_state1": round(b, 5),
                              "ic_mom_state1_should_be_0": round(c, 5)})
        ok = a > 0.015 and b > 0.015 and abs(c) < 0.015
    elif world.world_id == "D":
        mk = world.market
        auc = _auc(mk["m_precursor"].to_numpy(), mk["shock_next"].to_numpy())
        out["checks"].update({"precursor_auc": round(auc, 4),
                              "shock_rate": round(float(mk["shock_next"].mean()), 4)})
        ok = 0.62 < auc < 0.85 and 0.03 < mk["shock_next"].mean() < 0.25
    elif world.world_id == "E":
        on, _ = ic("f_mom", p["f_rev"] > 0)
        off, _ = ic("f_mom", p["f_rev"] <= 0)
        out["checks"].update({"ic_mom_rev_on": round(on, 5),
                              "ic_mom_rev_off": round(off, 5)})
        ok = on > 0.02 and abs(off) < 0.015
    elif world.world_id == "F":
        lo, _ = ic("f_mom", p["f_val"] < 0.8)
        hi, _ = ic("f_mom", p["f_val"] >= 0.8)
        out["checks"].update({"ic_mom_cheap": round(lo, 5),
                              "ic_mom_expensive": round(hi, 5)})
        ok = lo > 0.02 and hi < -0.02
    elif world.world_id in ("G", "H"):
        col = world.truth["specialist"]
        sec = world.truth["skilled_sector"]
        dec = world.truth["decoy_specialist"]
        a, _ = ic(col, p["sector_id"] == sec)
        b, _ = ic(col, p["sector_id"] != sec)
        c, _ = ic(dec, None)
        out["checks"].update({f"ic_{col}_in_sector": round(a, 5),
                              f"ic_{col}_elsewhere": round(b, 5),
                              f"ic_{dec}_anywhere": round(c, 5)})
        ok = a > 0.03 and abs(b) < 0.015 and abs(c) < 0.015
    elif world.world_id == "I":
        fwd, _ = ic("f_mom")
        con = float(p.groupby("t").apply(
            lambda x: x["f_mom"].corr(x["idio"], method="spearman"),
            include_groups=False).mean())
        out["checks"].update({"ic_f_mom_forward_should_be_0": round(fwd, 5),
                              "contemporaneous_rho": round(con, 4)})
        ok = abs(fwd) < 0.015 and con > 0.3
    elif world.world_id == "J":
        v, _ = ic("f_rev")
        ac = float(p.groupby("name")["f_rev"].apply(lambda s: s.autocorr(1)).mean())
        out["checks"].update({"ic_f_rev": round(v, 5),
                              "signal_autocorr_1m": round(ac, 3)})
        ok = v > 0.015 and ac < 0.35
    elif world.world_id == "K":
        st = p["f_qual"] < -0.5
        fr = p["f_qual"] > 1.0
        mid = ~st & ~fr
        a = float(p.loc[st, "y_idio"].mean())
        b = float(p.loc[fr, "y_idio"].mean())
        c = float(p.loc[mid, "y_idio"].mean())
        out["checks"].update({"idio_when_stale": round(a, 5),
                              "idio_when_fresh": round(b, 5),
                              "idio_when_middling": round(c, 5),
                              "stale_share": round(float(st.mean()), 4),
                              "fresh_share": round(float(fr.mean()), 4)})
        ok = a < -0.003 and b > 0.002 and abs(c) < 0.002
    elif world.world_id == "L":
        mk = world.market["mkt"]
        ac = float(pd.Series(mk).autocorr(1))
        volac = float(pd.Series(mk).abs().autocorr(1))
        out["checks"].update({"mkt_autocorr_1m": round(ac, 4),
                              "abs_mkt_autocorr_1m": round(volac, 4),
                              "mkt_sharpe_ann": round(
                                  float(mk.mean() / mk.std(ddof=1) * np.sqrt(12)), 3)})
        ok = abs(ac) < 0.12 and abs(volac) < 0.12
    out["ok"] = bool(ok)
    return out


def _auc(score: np.ndarray, label: np.ndarray) -> float:
    """Rank AUC. Returns 0.5 when a class is absent rather than raising."""
    label = np.asarray(label).astype(int)
    if label.sum() == 0 or label.sum() == len(label):
        return 0.5
    r = pd.Series(score).rank().to_numpy()
    n1 = label.sum()
    n0 = len(label) - n1
    return float((r[label == 1].sum() - n1 * (n1 + 1) / 2) / (n0 * n1))
