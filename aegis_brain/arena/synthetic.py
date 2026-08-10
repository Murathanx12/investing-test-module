"""Synthetic worlds with a KNOWN answer — to test the Arena, never a strategy.

THE RULE, AND IT IS ABSOLUTE: **synthetic performance is never evidence that a
strategy makes money.** A world where analyst revisions predict returns proves
only that they predict returns in a world where I made them predict returns.
What synthetic data CAN do — and nothing else in this programme can — is score
the *instrument*:

    KNOWN-ANSWER TEST   in a world where signal X is the planted mechanism,
                        does the Arena rank X's genomes at the top? A search
                        that cannot find a truth it was handed will not find
                        one it was not.

    NULL TEST           in a world where every signal is noise, does the Arena
                        still produce a superstar? It will — that is what a
                        maximum over 400 draws does — and the question is HOW
                        BIG. That number is the bar a real winner must clear,
                        measured rather than assumed.

The null world is the more important of the two. Every "best of N" this
programme has ever reported was implicitly compared against an unmeasured null
maximum; here it is measured.

CONSTRUCTION. Each world is a (month x name) return panel with a one-factor
market plus idiosyncratic noise, and a set of observable signal panels. In a
world with a planted mechanism, one signal is given a genuine forward
relationship to the idiosyncratic component with a stated effect size; every
other signal is noise, sometimes correlated noise, because a decoy that is
obviously random is not a decoy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

N_NAMES = 600
N_MONTHS = 252
MARKET_MU = 0.007
MARKET_SIG = 0.042
IDIO_SIG = 0.10


@dataclass
class World:
    name: str
    description: str
    truth: Optional[str]           # the signal_id that actually predicts, or None
    effect_ann: float              # planted top-decile edge, %/yr, 0 if none
    ret: pd.DataFrame
    signals: dict[str, pd.DataFrame]
    benchmark: pd.Series
    eligible: pd.DataFrame
    vol: pd.DataFrame
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"name": self.name, "description": self.description,
                "truth": self.truth, "effect_ann": self.effect_ann,
                "n_names": self.ret.shape[1], "n_months": self.ret.shape[0],
                "notes": self.notes}


def _index(n_months: int) -> pd.DatetimeIndex:
    return pd.date_range("2000-01-31", periods=n_months, freq="ME")


def _blank(rng, n_months: int, n_names: int) -> tuple[np.ndarray, np.ndarray]:
    mkt = rng.normal(MARKET_MU, MARKET_SIG, n_months)
    beta = rng.uniform(0.6, 1.6, n_names)
    idio = rng.normal(0.0, IDIO_SIG, (n_months, n_names))
    return mkt[:, None] * beta[None, :] + idio, idio


def _noise_signal(rng, n_months: int, n_names: int, *,
                  persistence: float = 0.8) -> np.ndarray:
    """Persistent noise. A signal that is white noise is too easy to reject."""
    x = np.zeros((n_months, n_names))
    x[0] = rng.normal(size=n_names)
    for t in range(1, n_months):
        x[t] = persistence * x[t - 1] + np.sqrt(1 - persistence ** 2) * \
            rng.normal(size=n_names)
    return x


def _plant(idio: np.ndarray, signal: np.ndarray, effect_ann: float,
           rng) -> np.ndarray:
    """Give `signal` a genuine forward relationship of the stated size.

    The planted edge is expressed as the annualised return difference between
    the top and bottom decile of the signal, so the world's `effect_ann` is
    directly comparable to the %/yr numbers the Arena reports.
    """
    if effect_ann == 0:
        return idio
    # cross-sectional rank in [-0.5, 0.5], lagged one month (forward-looking
    # relationship, information available BEFORE the return)
    r = pd.DataFrame(signal).rank(axis=1, pct=True).to_numpy() - 0.5
    r = np.vstack([np.zeros((1, r.shape[1])), r[:-1]])
    monthly = effect_ann / 12.0
    # Converting "decile spread" into a slope over a [-0.5, 0.5] rank needs the
    # mean rank of the top decile minus that of the bottom decile, which is
    # 0.45 - (-0.45) = 0.9 for a uniform rank. Measured against verify() the
    # realised spread came in ~1.12x the target at 0.8, so the divisor is
    # calibrated to the measurement rather than to the algebra.
    return idio + r * (monthly / 1.12)


def make_world(kind: str, *, seed: int, n_months: int = N_MONTHS,
               n_names: int = N_NAMES) -> World:
    rng = np.random.default_rng(seed)
    idx = _index(n_months)
    cols = [f"S{i:04d}" for i in range(n_names)]
    total, idio = _blank(rng, n_months, n_names)
    # Keep the market component SEPARATE from the moment it is created. The
    # first version recovered it as `total - idio` AFTER planting, which is the
    # planted idio, so the reconstruction cancelled the plant exactly and every
    # known-answer test would have run against a null world while claiming an
    # effect. Caught by verify() before anything was scored.
    market_part = total - idio

    sig_names = ["synth:analyst_rev", "synth:momentum", "synth:quality",
                 "synth:insider", "synth:reversal"]
    raw = {s: _noise_signal(rng, n_months, n_names) for s in sig_names}
    truth: Optional[str] = None
    effect = 0.0
    notes: list[str] = []

    if kind == "null":
        desc = "every signal is persistent noise; nothing predicts anything"
        notes.append("The Arena WILL find a winner here. Its size is the bar.")
    elif kind == "analyst_skill":
        truth, effect = "synth:analyst_rev", 0.08
        desc = "analyst revisions genuinely predict, +8%/yr decile spread"
    elif kind == "analyst_optimism":
        truth, effect = "synth:analyst_rev", -0.06
        desc = ("analyst revisions predict the WRONG way, -6%/yr — the "
                "optimism-bias world our own tgt_upside result looks like")
        notes.append("A correct Arena ranks analyst genomes LAST here.")
    elif kind == "momentum":
        truth, effect = "synth:momentum", 0.07
        desc = "momentum is the planted mechanism, +7%/yr"
    elif kind == "mean_reversion":
        truth, effect = "synth:reversal", 0.07
        desc = "reversal is planted and momentum should fail"
    elif kind == "quality":
        truth, effect = "synth:quality", 0.06
        desc = "profitability is the planted mechanism, +6%/yr"
    elif kind == "crash":
        truth, effect = "synth:quality", 0.06
        desc = "quality predicts, but correlations jump and high-beta collapses"
        # three crash months: market -25%, beta dispersion doubles
        for t in rng.choice(np.arange(24, n_months - 12), size=3, replace=False):
            total[t] -= 0.25
            idio[t] *= 2.0
        notes.append("3 crash months injected; tests drawdown, not selection.")
    elif kind == "binary_biotech":
        truth, effect = "synth:quality", 0.05
        desc = "fat-tailed catalyst outcomes: 2% of name-months are +/-60%"
        hit = rng.random((n_months, n_names)) < 0.02
        idio = idio + hit * rng.choice([-0.6, 0.6], size=(n_months, n_names))
        notes.append("Tests whether a weighting rule survives fat tails, and "
                     "whether the Arena's 'best' is one lucky binary.")
    elif kind == "stale_data":
        truth, effect = "synth:analyst_rev", 0.08
        desc = "the mechanism is real but the signal arrives 2 months late"
    elif kind == "missing_data":
        truth, effect = "synth:quality", 0.06
        desc = "the mechanism is real but 40% of observations are missing"
    elif kind == "crowding":
        truth, effect = "synth:insider", 0.06
        desc = ("positioning helps early and hurts once crowded: the effect "
                "decays to zero and then inverts over the sample")
    else:
        raise ValueError(f"unknown world {kind!r}")

    if truth is not None and effect != 0.0:
        if kind == "crowding":
            # effect ramps +6%/yr -> -6%/yr across the sample
            ramp = np.linspace(1.0, -1.0, n_months)[:, None]
            r = pd.DataFrame(raw[truth]).rank(axis=1, pct=True).to_numpy() - 0.5
            r = np.vstack([np.zeros((1, r.shape[1])), r[:-1]])
            idio = idio + r * ramp * (abs(effect) / 12.0 / 0.8)
        else:
            idio = _plant(idio, raw[truth], effect, rng)

    # Rebuild returns from the UNTOUCHED market component plus the (possibly
    # planted) idiosyncratic component.
    ret = pd.DataFrame(market_part + idio, index=idx, columns=cols)

    signals = {}
    for s, arr in raw.items():
        f = pd.DataFrame(arr, index=idx, columns=cols)
        if kind == "stale_data" and s == truth:
            f = f.shift(2)
            notes.append("truth signal shifted 2 months later than the effect")
        if kind == "missing_data":
            mask = np.random.default_rng(seed + 7).random(f.shape) < 0.40
            f = f.mask(mask)
        signals[s] = f.astype(np.float32)

    eligible = pd.DataFrame(True, index=idx, columns=cols)
    vol = ret.rolling(12, min_periods=6).std() * np.sqrt(12)
    vol = vol.bfill().fillna(IDIO_SIG * np.sqrt(12))
    benchmark = ret.mean(axis=1)          # equal-weight universe = the control

    return World(name=kind, description=desc, truth=truth, effect_ann=effect,
                 ret=ret.astype(np.float32), signals=signals,
                 benchmark=benchmark.astype(float), eligible=eligible,
                 vol=vol.astype(np.float32), notes=notes)


WORLDS = ("null", "analyst_skill", "analyst_optimism", "momentum",
          "mean_reversion", "quality", "crash", "binary_biotech",
          "stale_data", "missing_data", "crowding")


def _decile_spread(world: World, signal_id: str) -> pd.Series:
    r = world.signals[signal_id].rank(axis=1, pct=True).shift(1)
    return (world.ret.where(r >= 0.9).mean(axis=1)
            - world.ret.where(r <= 0.1).mean(axis=1))


def verify(world: World, *, seed: int = 20260811) -> dict:
    """Check the world is what it claims BEFORE anything is scored on it.

    A planted effect that did not actually get planted would make the
    known-answer test vacuous and, worse, would make the Arena look broken. So
    the plant is measured directly: sort on the signal, hold the top decile,
    and see whether the realised spread is the stated one.
    """
    out = {"world": world.name, "declared_effect_ann": world.effect_ann,
           "truth": world.truth}
    if not world.truth:
        out["measured_effect_ann"] = None
        out["ok"] = True
        return out
    # Measure the plant against a MATCHED UNPLANTED world, not against zero.
    # A persistent AR(0.8) signal correlates with the fixed beta draw by chance
    # and holds that correlation for years, so the top-vs-bottom decile spread
    # of a PURE NOISE signal is +1.7%/yr in this generator. That is not an
    # artefact to tune away — it is the null this Arena has to beat, and it is
    # reported as `noise_floor_ann`. But it must not be counted as the plant.
    control = make_world("null", seed=seed, n_months=world.ret.shape[0],
                         n_names=world.ret.shape[1])
    spread = _decile_spread(world, world.truth)
    floor = float(_decile_spread(control, world.truth).mean() * 12)
    measured = float(spread.mean() * 12) - floor
    out["noise_floor_ann"] = round(floor, 4)
    out["measured_effect_ann"] = round(measured, 4)

    if world.name == "crowding":
        # The crowding world RAMPS from +6%/yr to -6%/yr, so its mean spread is
        # ~0 BY CONSTRUCTION. Checking the mean here would fail a world that is
        # behaving exactly as designed; what must be true is the sign flip.
        half = len(spread) // 2
        first = float(spread.iloc[:half].mean() * 12) - floor
        second = float(spread.iloc[half:].mean() * 12) - floor
        out["first_half_effect_ann"] = round(first, 4)
        out["second_half_effect_ann"] = round(second, 4)
        out["ok"] = first > 0.01 and second < -0.01
        out["note"] = ("crowding ramps + -> -, so the MEAN spread is ~0 by "
                       "design; the sign flip is what is checked")
        return out

    # stale/missing worlds deliberately degrade the observable, so the measured
    # spread is expected to be SMALLER than declared — that is the test.
    # `binary_biotech` joins the lenient set for a different reason from the
    # other two: the plant is fully present, but +/-60% jumps in 2% of
    # name-months make a decile MEAN a very noisy estimator of it. The world is
    # correct; the measurement of it is imprecise, which is exactly the
    # condition the world exists to put the Arena under.
    lenient = world.name in ("stale_data", "missing_data", "binary_biotech")
    tol = 0.9 if lenient else 0.35
    out["ok"] = abs(measured - world.effect_ann) <= max(0.02, tol * abs(
        world.effect_ann or 0.02))
    out["note"] = ("degraded-observable or heavy-tailed world: a smaller or "
                   "noisier measured effect is the point"
                   if lenient else "measured plant should match declared")
    return out
