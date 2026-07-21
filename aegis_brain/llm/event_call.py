"""LLM event-call MVP: an entity-neutered situation -> a calibrated probability.

Concrete, non-vaporware use of the LLM as a *perception organ*. Given a description
of a catalyst with all identifying details stripped (no ticker/name/date — Gao-Jiang-Yan
entity-neutering) and a stated base rate, DeepSeek returns P(stock beats the market over
N trading days) plus a one-line rationale and a kill condition. It NEVER sees the outcome
and NEVER proposes a position size — a downstream rules layer does that.

The probability is only ever validated FORWARD by the ledger's Brier score.
"""

from __future__ import annotations

import json
import re

from aegis_brain.llm.client import chat

_SYSTEM = (
    "You are a calibrated forecasting module inside a quantitative research system. "
    "You output ONLY a JSON object, never prose outside it, never an allocation or trade "
    "size. You are given a catalyst with identifying details removed and a base rate for "
    "the outcome. You do NOT know how this resolves. Anchor your probability to the base "
    "rate and adjust only modestly for the specifics described. Be well-calibrated: if you "
    "are unsure, stay near the base rate. Overconfidence is penalized by forward Brier "
    "scoring."
)

_TEMPLATE = """A stock experiences the following catalyst (identifying details removed):

{situation}

Base rate for this class of event: P(the stock beats the market over {horizon} trading
days) = {base_rate:.2f}.

Return a JSON object with exactly these keys:
  "prob_up": float in [0,1]  — your calibrated P(stock beats market over {horizon} trading days)
  "rationale": string        — one sentence, the mechanism, no identifying details
  "kill_condition": string   — what realized pattern would falsify this call
"""

# strip tickers ($XYZ / (XYZ)), 4-digit years, and obvious date fragments
_TICKER = re.compile(r"\$?\b[A-Z]{1,5}\b(?=\s*(?:\)|shares|stock|,|\.|$))")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def neuter(text: str) -> str:
    """Best-effort removal of identifiers so the model can't recall the specific
    outcome. Not a security boundary — a bias control. Callers should also avoid
    passing company names."""
    # dates first — otherwise the year sub eats the year inside "04/15/2023"
    # and the date pattern can no longer match it.
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "[DATE]", text)
    text = _YEAR.sub("[YEAR]", text)
    return text


def propose_call(situation: str, base_rate: float, horizon_days: int,
                 model: str = "deepseek-chat") -> dict:
    """Ask the LLM for a calibrated probability on a (pre-neutered) situation.
    Returns {prob_up, rationale, kill_condition, model, base_rate}. Raises on a
    malformed response (fail loud — never fabricate a call)."""
    prompt = _TEMPLATE.format(situation=neuter(situation), horizon=horizon_days,
                              base_rate=base_rate)
    resp = chat(prompt, system=_SYSTEM, model=model, temperature=0.0,
                max_tokens=400, response_json=True)
    obj = json.loads(resp["text"])
    p = float(obj["prob_up"])
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"prob_up out of range: {p}")
    return {
        "prob_up": p,
        "rationale": str(obj.get("rationale", "")).strip(),
        "kill_condition": str(obj.get("kill_condition", "")).strip(),
        "model": resp["model"],
        "base_rate": base_rate,
    }
