"""Manual calibration harness for M4 — prints both signals + fused result.

Run: .venv/bin/python test_signals.py
"""

from dotenv import load_dotenv

from fusion import fuse
from llm_signal import llm_score
from stylometry import stylometry_score

load_dotenv()

SAMPLES = {
    "clearly_AI": (
        "Artificial intelligence represents a transformative paradigm shift in modern "
        "society. It is important to note that while the benefits of AI are numerous, it "
        "is equally essential to consider the ethical implications. Furthermore, "
        "stakeholders across various sectors must collaborate to ensure responsible "
        "deployment."
    ),
    "clearly_human": (
        "ok so i finally tried that new ramen place downtown and honestly? underwhelming. "
        "the broth was fine but they put WAY too much sodium in it and i was thirsty for "
        "like three hours after. my friend got the spicy version and said it was better. "
        "probably won't go back unless someone drags me there"
    ),
    "borderline_formal_human": (
        "The relationship between monetary policy and asset price inflation has been "
        "extensively studied in the literature. Central banks face a fundamental tension "
        "between their mandate for price stability and the unintended consequences of "
        "prolonged low interest rates on equity and real estate valuations."
    ),
    "borderline_edited_AI": (
        "I've been thinking a lot about remote work lately. There are genuine tradeoffs — "
        "flexibility and no commute on one side, isolation and blurred work-life "
        "boundaries on the other. Studies show productivity varies widely by individual "
        "and role type."
    ),
}


def main():
    for name, text in SAMPLES.items():
        sty = stylometry_score(text)
        llm = llm_score(text)
        fused = fuse(sty["score"], llm["score"])
        print(f"\n=== {name} ===")
        print(f"  stylometry: {sty['score']}  (cv={sty['metrics']['sentence_cv']}, "
              f"ttr={sty['metrics']['ttr']}, punct={sty['metrics']['punct_kinds']})")
        print(f"  llm:        {llm['score']}  ({llm['reasoning']})")
        print(f"  -> combined={fused['combined_score']} agreement={fused['agreement']} "
              f"decisiveness={fused['decisiveness']}")
        print(f"  -> confidence={fused['confidence']}  VERDICT={fused['verdict']} "
              f"(direction={fused['direction']})")


if __name__ == "__main__":
    main()
