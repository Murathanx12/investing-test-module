"""Stage 4 — paper exhibits A and B (design §5).

Exhibit A — "Operating characteristics of a strategy factory": x = injected
annualized Sharpe, y = P(discover), one line per CUMULATIVE gate stage
(explore-graduate → +confirm → +DSR/PBO@n=42 → +DSR/PBO@n=179), one panel
per injection design. The x=0 intercept is the false-discovery rate; the gap
between lines is what each gate costs a real edge.

Exhibit B — "What the verdict is worth": P(alpha >= 0.2 | evidence bucket)
heatmap with the sizing-ladder bands (0x/0.25x/0.5x/0.75x/1.0x) annotated.
Reads stage4_posterior_report.json (ships whether or not the map cleared the
monotonicity gate — the exhibit shows what IS, the gate decides what the
ladder may consume).

Colors: reference dataviz palette (light mode) — categorical slots 1-4 for
the four gate stages in fixed order, sequential blue ramp for the heatmap.

Run:  .venv/Scripts/python.exe -m aegis_brain.calibration.exhibits
"""

from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from aegis_brain.calibration.config import ALPHA_GRID, RUNS_DIR  # noqa: E402

# reference palette (light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SEQ_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
            "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281",
            "#0d366b"]
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, SURFACE = "#e1e0d9", "#fcfcfb"

STAGES = [
    ("p_graduate", "graduate"),
    ("p_confirm_pass", "+ confirm"),
    ("p_adopt_n42", "+ DSR/PBO (n=42)"),
    ("p_adopt_n179", "+ DSR@179"),
]
# RECAL-1 bank tables: one adopt column, the ladder's own terminal state.
STAGES_BANK = [
    ("p_graduate", "graduate"),
    ("p_confirm_pass", "+ confirm"),
    ("p_adopt", "+ DSR/PBO"),
]
DESIGNS = {"I1": "I1 constant · largemid (easy mode)",
           "I2": "I2 decaying τ=60m (headline)",
           "I3": "I3 small-segment only",
           "I4": "I4 size-correlated (ρ=0.5)"}


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def exhibit_a(tables: dict, out_name: str = "exhibit_A_operating_characteristics",
              subtitle: str = "") -> None:
    t1 = {r["cell"]: r for r in tables["table1_operating_characteristics"]}
    base = t1["a0.0/base"]
    # RECAL-1 bank tables carry one adopt column (the ladder's own terminal
    # state) instead of the M1 n42/n179 pair — pick whichever the file has.
    stages = STAGES if "p_adopt_n42" in base else STAGES_BANK
    wkey = "p_adopt_n42_wilson95" if "p_adopt_n42" in base else "p_adopt_wilson95"
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5), facecolor=SURFACE)
    for ax, (design, title) in zip(axes.ravel(), DESIGNS.items()):
        _style(ax)
        for (kcol, label), color in zip(stages, SERIES):
            xs, ys = [0.0], [base[kcol]]
            for a in ALPHA_GRID[1:]:
                row = t1.get(f"a{a}/{design}")
                if row:
                    xs.append(a)
                    ys.append(row[kcol])
            ax.plot(xs, ys, color=color, linewidth=2, marker="o",
                    markersize=6, label=label)
            ax.annotate(label, (xs[-1], ys[-1]), textcoords="offset points",
                        xytext=(6, -2), fontsize=8, color=color)
        # Wilson interval on the primary adopt line
        for a in ALPHA_GRID:
            row = base if a == 0 else t1.get(f"a{a}/{design}")
            if row:
                lo, hi = row[wkey]
                ax.plot([a, a], [lo, hi], color=SERIES[2], linewidth=1,
                        alpha=0.6)
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.set_xlim(-0.03, 0.72)
        ax.set_ylim(-0.03, 1.03)
        ax.set_xticks(ALPHA_GRID)
    for ax in axes[1]:
        ax.set_xlabel("injected annualized Sharpe (gross)", fontsize=9,
                      color=INK2)
    for ax in axes[:, 0]:
        ax.set_ylabel("P(candidate survives stage)", fontsize=9, color=INK2)
    n_note = (f"n = {base['n']} reps/cell (registered descope), Wilson 95% "
              "whiskers on the adopt line; x = 0 intercept = FDR"
              + (f" · {subtitle}" if subtitle else ""))
    fig.suptitle("Exhibit A — Operating characteristics of the strategy "
                 "factory (DGP-A v6, ρ_sig = 0.5)", fontsize=12, color=INK,
                 x=0.02, ha="left")
    fig.text(0.02, 0.945, n_note, fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = RUNS_DIR / f"{out_name}.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(f"-> {out}")


def exhibit_b(post: dict, out_name: str = "exhibit_B_posterior_heatmap") -> None:
    buckets = post["buckets"]
    keys = sorted(buckets, key=lambda k: eval(k))
    bank = "buckets_definition" in post      # RECAL-1 coordinates
    # rows = explore bucket, cols = (confirm, dsr) pairs actually observed
    e_labels = ["t<1.5", "t 1.5-2", "t 2-2.5", "t≥2.5"]
    cd_pairs = sorted({tuple(eval(k)[1:]) for k in keys})
    c_lab = (["none", "<0.75", "0.75-1.5", "≥1.5"] if bank
             else ["none", "<0.8", "0.8-1.5", "≥1.5"])
    d_lab = (["none", "<0.25", ".25-.75", "≥.75"] if bank
             else ["none", "<0.5", ".5-.95", "≥.95"])
    mat = np.full((4, len(cd_pairs)), np.nan)
    counts = np.zeros_like(mat)
    for k in keys:
        key = eval(k)
        e, rest = key[0], tuple(key[1:])
        j = cd_pairs.index(rest)
        mat[e, j] = buckets[k]["headline"]
        counts[e, j] = sum(buckets[k]["counts"].values())

    fig, ax = plt.subplots(figsize=(1.6 + 1.15 * len(cd_pairs), 5.2),
                           facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ_RAMP)
    im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isnan(mat[i, j]):
                continue
            p = mat[i, j]
            mult = buckets[str((i, *cd_pairs[j]))]["band_multiplier"]
            ink = "#ffffff" if p > 0.55 else INK
            ax.text(j, i - 0.13, f"{p:.2f}", ha="center", fontsize=10,
                    color=ink, fontweight="bold")
            ax.text(j, i + 0.18, f"{mult:g}×  (n={int(counts[i, j])})",
                    ha="center", fontsize=7.5, color=ink)
    ax.set_xticks(range(len(cd_pairs)))
    # RECAL-1 run 2 dropped the DSR axis (spec S12), so a bucket key may be
    # (e, c) rather than (e, c, d) — label whichever shape arrived.
    ax.set_xticklabels(
        [f"conf {c_lab[p[0]]}" + (f"\nDSR {d_lab[p[1]]}" if len(p) > 1 else "")
         for p in cd_pairs], fontsize=8, color=INK2)
    ax.set_yticks(range(4))
    ax.set_yticklabels(e_labels, fontsize=9, color=INK2)
    ax.set_ylabel("explore t(rank IC) bucket" if bank
                  else "explore t(net excess) bucket", fontsize=9, color=INK2)
    ax.tick_params(colors=MUTED)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("P(α ≥ 0.2 | evidence)", fontsize=9, color=INK2)
    cb.ax.tick_params(colors=MUTED, labelsize=8)
    monotone = "monotone — SHIPPED" if post["monotone"] else \
        "NON-MONOTONE — not shipped to the ladder"
    design = post.get("design", "I2")
    ax.set_title("Exhibit B — What the verdict is worth\n"
                 f"posterior under {design}/ρ=0.5 + prior π(0)=0.85 · "
                 f"{monotone} · cell annotation = sizing-ladder multiplier",
                 fontsize=10.5, color=INK, loc="left")
    fig.tight_layout()
    out = RUNS_DIR / f"{out_name}.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(f"-> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None,
                    help="RECAL-1 bank tag; absent = frozen BRAIN-008 exhibits")
    ap.add_argument("--ruleset", default="BRAIN-009")
    ap.add_argument("--design", default="I2")
    args = ap.parse_args()

    if args.tag is None:
        tables = json.loads((RUNS_DIR / "stage3_tables.json").read_text(
            encoding="utf-8"))
        exhibit_a(tables)
        post_path = RUNS_DIR / "stage4_posterior_report.json"
        if post_path.exists():
            exhibit_b(json.loads(post_path.read_text(encoding="utf-8")))
        else:
            print("no posterior report yet — Exhibit B skipped")
        return

    sfx = f"_{args.tag}_{args.ruleset}"
    tpath = RUNS_DIR / f"stage3_tables{sfx}_all.json"
    if not tpath.exists():
        raise SystemExit(f"missing {tpath} — run the bank aggregate first")
    exhibit_a(json.loads(tpath.read_text(encoding="utf-8")),
              out_name=f"exhibit_A_operating_characteristics{sfx}",
              subtitle=f"ladder {args.ruleset}")
    ppath = RUNS_DIR / f"stage4_posterior_report{sfx}_{args.design}.json"
    if ppath.exists():
        exhibit_b(json.loads(ppath.read_text(encoding="utf-8")),
                  out_name=f"exhibit_B_posterior_heatmap{sfx}_{args.design}")
    else:
        print(f"no posterior report at {ppath} — Exhibit B skipped")


if __name__ == "__main__":
    main()
