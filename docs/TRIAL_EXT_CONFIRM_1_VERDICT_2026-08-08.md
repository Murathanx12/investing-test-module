# TRIAL-EXT-CONFIRM-1 — INFORMATION PASS ×2, MONEY FAIL ×2 (2026-08-08)

Prereg commit a6b85d9 (before compute). Guards reproduced banked lines
exactly. One confirm read each — both windows now spent forever.

| | confirm t_ic (p vs null) | t_net flat / KO | bps/mo | long-leg share | information | money |
|---|---|---|---|---|---|---|
| GP | 5.14 (5e-05) | 1.16 / 1.19 | +34.6 | **0.689** | PASS | FAIL |
| OperProfRD | 6.36 (5e-05) | 0.74 / 0.82 | +18.6 | 0.133 | PASS | FAIL |

Placebos (5 information-free persistent signals, same book): net t −1.20
to **+1.99** — the max placebo alone would have blocked adoption this
round, which is the point of the clause: single-signal 72-month net t's
are this noisy.

## Prior scoring (house rule)

GP point 1.1 → realized 1.16: **HIT**. OperProfRD point 1.4 → 0.74:
missed high. P(≥1 TRADABLE-PASS) 0.35 → the 0.65 branch realized.

## The structural finding, stated once for all four money adjudications

Across tonight's four money-leg tests (10-book 1.07 vs placebo 1.32; EW-209
negative; GP 1.16 vs placebo 1.99; OperProfRD 0.74): **held-out
information confirms at IC t ≥ 4.4 every time; held-out money lands at
0.7-1.3 against placebo noise reaching 2.0.** A 72-month confirm window's
minimum detectable net edge at 80% power for t ≥ 1.5 is ≈ 0.6 annualized
Sharpe — plausibly ~2× what these candidates carry. Per the kill-mechanism
taxonomy (Amendment 2), both candidates exit
**INFORMATION-CONFIRMED / MONEY-UNDERPOWERED** — not MONEY-DEAD. The
one-shots are spent; the label records what the test could and could not
see. The instrument that CAN adjudicate edges of this size is the forward
paper lane (more months, real accounting, pre-trade intents) — which is
what these candidates would need Murat's attended flag for, with the
honest label "information-confirmed, money-unproven" and the 24-month
no-claim clock.

GP's 0.689 confirm long-leg share (unique among everything measured
tonight) plus its externally-fixed direction and its double validation of
the house survivor gp-small makes it the single best-evidenced candidate
in the project. That is a statement about evidence quality, not about
expected returns.
