"""Emit the GRAND-ARENA-1 PHASE 1 markdown tables from the results JSON.

Generated rather than transcribed, because a hand-copied 12x9 matrix is a
transcription-error surface and this document is the licence for every later
phase.

    python scripts/known_world_1_tables.py > tables.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RES = Path(__file__).resolve().parents[1] / "data" / "factory" / "known_world_1_results.json"

MARK = {"RECOVERED": "**RECOVERED**", "PARTIAL": "PARTIAL", "MISSED": "MISSED",
        "FALSE-POSITIVE": "**FALSE-POS**", "CORRECT-NULL": "**CORRECT-NULL**",
        "ERROR": "ERROR"}
ORDER = ["ridge", "logistic", "random_forest", "lightgbm", "mlp_torch",
         "evolutionary", "hmm_regime", "contextual_bandit", "offline_q"]
SHORT = {"ridge": "ridge", "logistic": "logit", "random_forest": "RF",
         "lightgbm": "LGBM", "mlp_torch": "MLP", "evolutionary": "evo",
         "hmm_regime": "HMM", "contextual_bandit": "bandit", "offline_q": "fitQ"}


def main() -> None:
    d = json.loads(RES.read_text(encoding="utf-8"))
    cells = {(c["world"], c["learner"]): c for c in d["cells"]}
    worlds = sorted({w for w, _ in cells})
    learners = [ln for ln in ORDER if any(l == ln for _, l in cells)]

    print("### Recovery matrix\n")
    print("| World | " + " | ".join(SHORT[l] for l in learners) + " |")
    print("|---|" + "---|" * len(learners))
    for w in worlds:
        row = []
        for ln in learners:
            c = cells.get((w, ln))
            row.append(MARK.get(c["verdict"], "-") if c else "—")
        print(f"| **{w}** | " + " | ".join(row) + " |")

    print("\n### Primary numbers with their MDEs\n")
    print("| World | Learner | primary | value | MDE | ratio | verdict |")
    print("|---|---|---|---|---|---|---|")
    for w in worlds:
        for ln in learners:
            c = cells.get((w, ln))
            if not c or not c.get("primary") or c["primary"].get("mean") is None:
                continue
            p = c["primary"]
            r = abs(p["mean"]) / p["mde"] if p["mde"] else float("nan")
            print(f"| {w} | {SHORT[ln]} | {p['label']} | {p['mean']:+.4f} | "
                  f"{p['mde']:.4f} | {r:.2f}x | {c['verdict']} |")

    print("\n### Oracle ceilings — what was achievable at all\n")
    for w, v in d.get("oracle_ceilings", {}).items():
        print(f"**{w}** — {json.dumps(v, default=str)[:600]}\n")

    print("\n### Per-learner\n")
    print("| Learner | cells | RECOVERED | PARTIAL | MISSED | CORRECT-NULL | FALSE-POS | clean on negative controls |")
    print("|---|---|---|---|---|---|---|---|")
    for ln, v in d["per_learner"].items():
        print(f"| {SHORT.get(ln, ln)} | {v['cells']} | {len(v['recovered'])} "
              f"({','.join(v['recovered'])}) | {len(v['partial'])} "
              f"({','.join(v['partial'])}) | {len(v['missed'])} "
              f"({','.join(v['missed'])}) | {len(v['correct_null'])} "
              f"({','.join(v['correct_null'])}) | {len(v['false_positive'])} "
              f"({','.join(v['false_positive'])}) | "
              f"{'yes' if v['clean_on_negative_controls'] else 'NO'} |")

    print("\n### §20 batch self-check\n")
    print("```json")
    print(json.dumps(d["batch_self_check_canon_20"], indent=2)[:2500])
    print("```")


if __name__ == "__main__":
    main()
