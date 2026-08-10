"""N7 — calibrate the capacity instrument before any capacity verdict is trusted.

The standing rule is that instruments are calibrated before their verdicts are
believed (NEGATIVE_RESULTS #34; GATE-M1, which measured the adoption ladder as
having a 0% chance of adopting a true edge). G7's daily simulator is about to be
asked whether the book has a capacity limit below AVUV's floor. Nobody has ever
asked G7 whether it can tell a capacity effect from nothing.

Synthetic worlds with known answers, run through the real `simulate()`:

  WORLD Z (known-zero)  huge ADV, zero spread, zero slippage, zero commission,
                        open == close. The correct answer is EXACTLY the target
                        book's return. Anything else is instrument bias, and
                        the size of it is the false-positive floor for every
                        capacity claim G7 has made or will make.

  WORLD C (known-cost)  same, but a known half-spread. Cost per dollar traded is
                        analytically (half_spread + slippage + commission), so
                        the instrument either recovers it or it does not.

  WORLD K (known-cap)   ADV sized so that a known fraction of desired notional
                        cannot fill on the rebalance day. Degradation must rise
                        monotonically with NAV, and must be ZERO at the rung
                        where the cap cannot bind.

False positive = a capacity effect reported in a world that has none.
False negative = a real, economically material effect the instrument misses.

Reported, never deciding. Nothing here touches market data or a lane.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_brain.config import MODULE_ROOT
from aegis_brain.pf.daily_sim import DailyData, SimConfig, simulate

OUT = MODULE_ROOT / "runs" / "NIGHT8"
SEED = 20260810
N_NAMES = 150
N_YEARS = 20
DAYS_PER_YEAR = 252
REBAL_EVERY = 252                 # annual, like the book
DRIFT_ANNUAL = 0.10
VOL_ANNUAL = 0.35
#: a "capacity effect" smaller than this is not one; it is instrument noise
MATERIAL = 0.01                   # 1%/yr


def build_world(seed: int, *, adv_multiple: float, half_spread_bps: float,
                price: float = 30.0) -> tuple[DailyData, list[dict], pd.Series]:
    """A market with known returns, known liquidity and a known target book.

    `adv_multiple` is each name's daily dollar volume as a multiple of the
    position it must hold at $1m of NAV, so the participation cap binds in a way
    that is known in advance rather than discovered.
    """
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2002-01-01", periods=N_YEARS * DAYS_PER_YEAR)
    cols = list(range(10_000, 10_000 + N_NAMES))
    mu = DRIFT_ANNUAL / DAYS_PER_YEAR
    sd = VOL_ANNUAL / np.sqrt(DAYS_PER_YEAR)
    r = pd.DataFrame(rng.normal(mu, sd, (len(days), N_NAMES)),
                     index=days, columns=cols)

    px = price * (1.0 + r).cumprod()
    position_at_1m = 1_000_000.0 / N_NAMES
    dvol = pd.DataFrame(position_at_1m * adv_multiple, index=days, columns=cols)
    hs = pd.DataFrame(half_spread_bps, index=days, columns=cols)

    # open == close removes the execution-drift adjustment, which is a real
    # effect in the real world and pure noise in a calibration
    data = DailyData(ret=r, prc=px, opn=px, dvol=dvol, half_spread=hs,
                     rf=pd.Series(0.0, index=days), delist_ret={})

    w = pd.Series(1.0 / N_NAMES, index=cols)
    targets = [{"effective": days[i], "weights": w}
               for i in range(0, len(days), REBAL_EVERY)]

    # the truth: an equal-weight book rebalanced on exactly those days, with no
    # frictions of any kind. Computed independently of the simulator.
    nav, hold = 1.0, None
    truth = {}
    rebal = {days[i] for i in range(0, len(days), REBAL_EVERY)}
    for day in days:
        if hold is None or day in rebal:
            hold = w.copy()
        hold = hold * (1.0 + r.loc[day])
        nav_mult = float(hold.sum())
        hold = hold / nav_mult
        nav *= nav_mult
        truth[day] = nav
    return data, targets, pd.Series(truth)


def cagr(nav: pd.Series) -> float:
    yrs = (nav.index[-1] - nav.index[0]).days / 365.25
    return float((nav.iloc[-1] / nav.iloc[0]) ** (1 / yrs) - 1)


def frictionless(**kw) -> SimConfig:
    return SimConfig(slippage_bps=0.0, commission_bps=0.0, **kw)


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    res = {
        "task": "N7 — calibration of the capacity instrument (G7 daily sim)",
        "status": "REPORTED-NEVER-DECIDING",
        "why": ("G7 is about to be asked whether the book has a capacity limit "
                "below AVUV's floor. It has never been asked whether it can "
                "tell a capacity effect from nothing."),
        "material_threshold_pct_yr": MATERIAL,
        "worlds": {},
    }

    # ── WORLD Z: no frictions, no cap. The answer is known exactly ──────────
    zs = []
    for s in range(6):
        data, tg, truth = build_world(SEED + s, adv_multiple=1e6,
                                      half_spread_bps=0.0)
        sim = simulate(tg, data, frictionless(start_nav=1_000_000.0))
        zs.append({"seed": SEED + s,
                   "truth_cagr": round(cagr(truth), 6),
                   "sim_cagr": round(cagr(sim["nav"]), 6),
                   "bias_pct_yr": round(cagr(sim["nav"]) - cagr(truth), 6),
                   "cost_dollars": sim["diag"]["cost_dollars"],
                   "capped_days": sim["diag"]["days_with_capped_orders"]})
        print(f"  Z seed {SEED + s}: truth {zs[-1]['truth_cagr']:+.4f} "
              f"sim {zs[-1]['sim_cagr']:+.4f} bias {zs[-1]['bias_pct_yr']:+.5f}",
              flush=True)
    bias = np.array([z["bias_pct_yr"] for z in zs])
    res["worlds"]["Z_known_zero"] = {
        "runs": zs,
        "mean_bias_pct_yr": round(float(bias.mean()), 6),
        "max_abs_bias_pct_yr": round(float(np.abs(bias).max()), 6),
        "false_positive_rate": round(float((np.abs(bias) > MATERIAL).mean()), 4),
        "reading": ("bias is the CAGR the simulator invents in a world with no "
                    "frictions and no capacity limit. It is the floor below "
                    "which no capacity claim from this instrument means "
                    "anything."),
    }

    # ── WORLD C: known cost per dollar traded ──────────────────────────────
    cs = []
    for hs_bps in (5.0, 25.0, 100.0):
        data, tg, _ = build_world(SEED, adv_multiple=1e6,
                                  half_spread_bps=hs_bps)
        sim = simulate(tg, data, SimConfig(start_nav=1_000_000.0,
                                           slippage_bps=5.0,
                                           commission_bps=1.0))
        expected = hs_bps + 5.0 + 1.0
        got = sim["diag"]["cost_bps_of_traded"]
        cs.append({"half_spread_bps": hs_bps, "expected_bps": expected,
                   "measured_bps": got,
                   "error_bps": round(got - expected, 3)})
        print(f"  C half-spread {hs_bps:6.1f}: expected {expected:6.1f} bps, "
              f"measured {got:6.1f}", flush=True)
    res["worlds"]["C_known_cost"] = {
        "runs": cs,
        "max_abs_error_bps": round(max(abs(c["error_bps"]) for c in cs), 3),
        "reading": ("cost per dollar traded is analytic here: half-spread plus "
                    "slippage plus commission. The instrument either recovers "
                    "it or it is mis-charging every book it has ever priced."),
    }

    # ── WORLD K: the cap binds, by construction, and harder with size ───────
    ks = []
    for mult in (1e6, 100.0, 20.0, 5.0, 1.0):
        data, tg, truth = build_world(SEED, adv_multiple=mult,
                                      half_spread_bps=0.0)
        sim = simulate(tg, data, frictionless(start_nav=1_000_000.0))
        unfilled = float(sim["daily"]["pending_abs"].mean()
                         / sim["daily"]["nav"].mean())
        ks.append({"adv_multiple": mult,
                   "degradation_pct_yr": round(cagr(sim["nav"]) - cagr(truth), 5),
                   "capped_days": sim["diag"]["days_with_capped_orders"],
                   "mean_unfilled_share_of_nav": round(unfilled, 5)})
        print(f"  K adv x{mult:<9g}: degradation "
              f"{ks[-1]['degradation_pct_yr']:+.5f}/yr  capped days "
              f"{ks[-1]['capped_days']:5d}  unfilled {unfilled:.5f}", flush=True)

    deg = [abs(k["degradation_pct_yr"]) for k in ks]
    detected = [k for k in ks if abs(k["degradation_pct_yr"]) > MATERIAL]
    monotone = all(deg[i] <= deg[i + 1] + 1e-9 for i in range(len(deg) - 1))
    res["worlds"]["K_known_cap"] = {
        "runs": ks,
        "monotone_in_tightness": monotone,
        "first_detected_at_adv_multiple": (detected[0]["adv_multiple"]
                                           if detected else None),
        "false_negative": not detected,
        "reading": ("liquidity tightens down the list. Degradation must be "
                    "zero where the cap cannot bind and must grow as it does. "
                    "A non-monotone column means the instrument is reading "
                    "something other than capacity."),
    }

    # ── WORLD I: is the instrument's COST size-aware at all? ───────────────
    # World K found monotone but tiny degradation, which is ambiguous: either
    # an annual clock genuinely has a year to work its orders down, or the
    # instrument prices capacity as DELAY and never as PRICE. This separates
    # them. If cost per dollar traded is identical across a 1,000,000x range of
    # liquidity, the instrument has no impact term, and that is structural.
    it = []
    for mult in (1e6, 100.0, 5.0, 1.0):
        data, tg, _ = build_world(SEED, adv_multiple=mult,
                                  half_spread_bps=25.0)
        sim = simulate(tg, data, SimConfig(start_nav=1_000_000.0,
                                           slippage_bps=5.0,
                                           commission_bps=1.0))
        it.append({"adv_multiple": mult,
                   "cost_bps_of_traded": sim["diag"]["cost_bps_of_traded"],
                   "capped_days": sim["diag"]["days_with_capped_orders"]})
        print(f"  I adv x{mult:<9g}: cost {it[-1]['cost_bps_of_traded']:6.2f} "
              f"bps of traded, capped days {it[-1]['capped_days']:5d}",
              flush=True)
    spread_of_cost = (max(x["cost_bps_of_traded"] for x in it)
                      - min(x["cost_bps_of_traded"] for x in it))
    size_aware = spread_of_cost > 1.0
    res["worlds"]["I_impact_term"] = {
        "runs": it,
        "cost_bps_range_across_1e6x_liquidity": round(spread_of_cost, 3),
        "cost_is_size_aware": size_aware,
        "reading": (
            "cost per dollar traded is IDENTICAL across a million-fold range of "
            "liquidity. G7 charges half-spread + slippage + commission on "
            "notional and nothing that grows with participation, so it prices "
            "capacity as DELAY (orders that cannot fill are carried) and never "
            "as PRICE (moving the market against yourself). That is the "
            "dominant capacity cost in the literature and this instrument "
            "cannot see it." if not size_aware else
            "cost per dollar traded varies with liquidity, so an impact term "
            "is present."),
    }

    fp = res["worlds"]["Z_known_zero"]["false_positive_rate"]
    floor = res["worlds"]["Z_known_zero"]["max_abs_bias_pct_yr"]
    cost_err = res["worlds"]["C_known_cost"]["max_abs_error_bps"]
    clean = fp == 0.0 and cost_err < 1.0 and monotone
    res["verdict"] = {
        "trustworthy_where_it_measures": clean,
        "usable_for_a_capacity_limit_verdict": clean and size_aware,
        "statement": (
            f"PARTIALLY CALIBRATED. What it does well: false positives {fp:.0%} "
            f"in a world with no capacity effect (max invented CAGR "
            f"{floor:.2%}/yr), cost per dollar traded recovered to "
            f"{cost_err:.2f} bps, degradation monotone in liquidity tightness. "
            "What it CANNOT do: price impact. Cost per dollar traded is "
            f"identical across a 1,000,000x range of liquidity (range "
            f"{spread_of_cost:.2f} bps), so G7 models capacity as DELAY and "
            "never as PRICE. Even with a name's whole daily volume equal to the "
            "position, degradation reached only "
            f"{max(deg):.3%}/yr — because an annual clock has a year to work "
            "orders down. CONSEQUENCE: a capacity number from this instrument "
            "is a LOWER BOUND, and CAPACITY-EDGE-1 may not report a capacity "
            "limit from it without either adding a participation-dependent "
            "impact term or labelling the result as delay-only."
            if clean else
            f"NOT USABLE AS IS — false-positive rate {fp:.0%}, cost error "
            f"{cost_err:.2f} bps, monotone={monotone}. A capacity verdict from "
            "this instrument would not be trustworthy until these are "
            "explained."),
        "hard_floor_pct_yr": max(floor, MATERIAL),
        "blocks": ("CAPACITY-EDGE-1 as currently scoped" if not size_aware
                   else None),
    }
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUT / "N7_CAPACITY_INSTRUMENT_CALIBRATION.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8")
    print("\n" + res["verdict"]["statement"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
