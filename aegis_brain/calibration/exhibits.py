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


def exhibit_a(tables: dict) -> None:
    t1 = {r["cell"]: r for r in tables["table1_operating_characteristics"]}
    base = t1["a0.0/base"]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7.5), facecolor=SURFACE)
    for ax, (design, title) in zip(axes.ravel(), DESIGNS.items()):
        _style(ax)
        for (kcol, label), color in zip(STAGES, SERIES):
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
                lo, hi = row["p_adopt_n42_wilson95"]
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
              "whiskers on the n=42 adopt line; x = 0 intercept = FDR")
    fig.suptitle("Exhibit A — Operating characteristics of the strategy "
                 "factory (DGP-A v6, ρ_sig = 0.5)", fontsize=12, color=INK,
                 x=0.02, ha="left")
    fig.text(0.02, 0.945, n_note, fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = RUNS_DIR / "exhibit_A_operating_characteristics.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(f"-> {out}")


def exhibit_b(post: dict) -> None:
    buckets = post["buckets"]
    keys = sorted(buckets, key=lambda k: eval(k))
    # rows = explore bucket, cols = (confirm, dsr) pairs actually observed
    e_labels = ["t<1.5", "t 1.5-2", "t 2-2.5", "t≥2.5"]
    cd_pairs = sorted({tuple(eval(k)[1:]) for k in keys})
    c_lab = ["none", "<0.8", "0.8-1.5", "≥1.5"]
    d_lab = ["none", "<0.5", ".5-.95", "≥.95"]
    mat = np.full((4, len(cd_pairs)), np.nan)
    counts = np.zeros_like(mat)
    for k in keys:
        e, c, d = eval(k)
        j = cd_pairs.index((c, d))
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
    ax.set_xticklabels([f"conf {c_lab[c]}\nDSR {d_lab[d]}"
                        for c, d in cd_pairs], fontsize=8, color=INK2)
    ax.set_yticks(range(4))
    ax.set_yticklabels(e_labels, fontsize=9, color=INK2)
    ax.set_ylabel("explore t(net excess) bucket", fontsize=9, color=INK2)
    ax.tick_params(colors=MUTED)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("P(α ≥ 0.2 | evidence)", fontsize=9, color=INK2)
    cb.ax.tick_params(colors=MUTED, labelsize=8)
    monotone = "monotone — SHIPPED" if post["monotone"] else \
        "NON-MONOTONE — not shipped to the ladder"
    ax.set_title("Exhibit B — What the verdict is worth\n"
                 f"posterior under I2/ρ=0.5 + prior π(0)=0.85 · {monotone} · "
                 "cell annotation = sizing-ladder multiplier",
                 fontsize=10.5, color=INK, loc="left")
    fig.tight_layout()
    out = RUNS_DIR / "exhibit_B_posterior_heatmap.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(f"-> {out}")


def main() -> None:
    tables = json.loads((RUNS_DIR / "stage3_tables.json").read_text(
        encoding="utf-8"))
    exhibit_a(tables)
    post_path = RUNS_DIR / "stage4_posterior_report.json"
    if post_path.exists():
        exhibit_b(json.loads(post_path.read_text(encoding="utf-8")))
    else:
        print("no posterior report yet — Exhibit B skipped")


if __name__ == "__main__":
    main()
