"""Confidence scoring — agreement-weighted fusion of the two signals.

Implements planning.md §1 (fusion math) and §2 (bands):
    C  = 0.6*llm + 0.4*sty            combined AI-likeness
    A  = 1 - |llm - sty|              agreement (1=agree, 0=disagree)
    D  = min(1, 2.5*|C - 0.5|)        decisiveness (0 at boundary, 1 when clearly off it)
    confidence = D * (0.6 + 0.4*A)    in [0, 1]; agreement scales the result
                                      between 0.6x (full disagreement) and 1.0x
                                      (full agreement) — it tempers confidence
                                      without collapsing it to zero.

Bands: confidence >= HIGH_CONF -> "ai"/"human" by direction (C vs 0.5);
otherwise "uncertain". If the LLM signal errored, fall back to stylometry alone
with a single-signal penalty (agreement factor fixed at 0.6).
"""

W_LLM = 0.6
W_STY = 0.4
DECISIVENESS_GAIN = 2.5
HIGH_CONF = 0.45


def fuse(sty_score, llm_score_value):
    """Combine the two signal scores into verdict + confidence.

    sty_score: float in [0,1]. llm_score_value: float in [0,1] or None (error).
    Returns a dict with combined_score, confidence, agreement, decisiveness,
    direction, and verdict.
    """
    if llm_score_value is None:
        # Single-signal fallback: stylometry only, with a penalty.
        combined = sty_score
        decisiveness = min(1.0, DECISIVENESS_GAIN * abs(combined - 0.5))
        agreement = None
        confidence = round(decisiveness * 0.6, 2)
    else:
        combined = W_LLM * llm_score_value + W_STY * sty_score
        agreement = 1 - abs(llm_score_value - sty_score)
        decisiveness = min(1.0, DECISIVENESS_GAIN * abs(combined - 0.5))
        confidence = round(decisiveness * (0.6 + 0.4 * agreement), 2)

    direction = "ai" if combined >= 0.5 else "human"

    if confidence >= HIGH_CONF:
        verdict = direction
    else:
        verdict = "uncertain"

    return {
        "combined_score": round(combined, 4),
        "confidence": confidence,
        "agreement": None if agreement is None else round(agreement, 4),
        "decisiveness": round(decisiveness, 4),
        "direction": direction,
        "verdict": verdict,
    }
