"""Signal 1 — Stylometric heuristics (structural, pure Python).

Measures statistical regularity of writing. AI text trends uniform; human text
trends bursty/varied. Returns an AI-likeness score in [0, 1] (higher = more
AI-like) plus the raw metrics, per planning.md §1.
"""

import re
import statistics

# Sentence splitter: break on ., !, ? followed by whitespace.
_SENTENCE_RE = re.compile(r"[.!?]+(?:\s+|$)")
_WORD_RE = re.compile(r"[A-Za-z']+")
_PUNCT_KINDS = [",", ";", ":", "—", "-", "?", "!", "(", ")"]

# Lexical "AI tells": boilerplate transitions and hedging phrases that LLM prose
# over-uses. A structural/lexical heuristic (regex word-list), distinct from the
# LLM's holistic semantic judgment — it catches AI text that has varied sentence
# lengths and rich vocabulary and so slips past the uniformity metrics.
_BOILERPLATE = [
    r"it is important to note",
    r"it is worth noting",
    r"it is essential to",
    r"it is equally (?:important|essential)",
    r"furthermore",
    r"moreover",
    r"in conclusion",
    r"in today's (?:world|society|digital age)",
    r"paradigm shift",
    r"plays a (?:crucial|key|vital|significant) role",
    r"delve into",
    r"stakeholders",
    r"navigate the complexities",
    r"a testament to",
    r"when it comes to",
    r"studies show",
    r"on the other hand",
    r"transformative",
    r"responsible (?:deployment|use|development)",
]
_BOILERPLATE_RE = re.compile("|".join(_BOILERPLATE), re.IGNORECASE)


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _split_sentences(text):
    parts = [s.strip() for s in _SENTENCE_RE.split(text)]
    return [s for s in parts if s]


def stylometry_score(text):
    """Return {'score': float, 'metrics': {...}} for the given text.

    score is AI-likeness in [0, 1]; metrics carries the raw values for the
    audit log. Very short text is flagged via metrics but still scored.
    """
    sentences = _split_sentences(text)
    tokens = [t.lower() for t in _WORD_RE.findall(text)]
    n_sentences = len(sentences)
    n_tokens = len(tokens)

    # Per-sentence word counts -> coefficient of variation (rhythm/burstiness).
    sent_word_counts = [len(_WORD_RE.findall(s)) for s in sentences]
    if n_sentences >= 2 and statistics.mean(sent_word_counts) > 0:
        mean_len = statistics.mean(sent_word_counts)
        sentence_cv = statistics.pstdev(sent_word_counts) / mean_len
    else:
        # Too few sentences to measure rhythm; treat as neutral (0.5 CV).
        sentence_cv = 0.5

    # Type-token ratio on first 200 tokens (vocabulary diversity).
    window = tokens[:200]
    ttr = (len(set(window)) / len(window)) if window else 0.65

    # Distinct punctuation marks used (stylistic texture).
    punct_kinds = sum(1 for p in _PUNCT_KINDS if p in text)

    # Boilerplate-phrase density (lexical AI tells per sentence).
    boilerplate_hits = len(_BOILERPLATE_RE.findall(text))
    boilerplate_density = boilerplate_hits / max(n_sentences, 1)

    # Normalize each sub-metric to AI-likeness in [0, 1] (higher = more AI-like).
    sty_var = _clamp((0.50 - sentence_cv) / 0.50)     # low CV -> AI
    sty_ttr = _clamp((0.65 - ttr) / 0.40)             # low diversity -> AI
    sty_punct = _clamp((4 - punct_kinds) / 4.0)       # few kinds -> AI
    sty_boiler = _clamp(boilerplate_density / 0.75)   # ~0.75 hits/sentence -> AI

    # Boilerplate phrasing is the strongest lexical AI tell and the only metric
    # that catches polished AI text whose sentence variance and vocabulary
    # otherwise read as human, so it carries the most weight.
    score = round(
        0.25 * sty_var + 0.20 * sty_ttr + 0.15 * sty_punct + 0.40 * sty_boiler, 4
    )

    return {
        "score": score,
        "metrics": {
            "sentence_cv": round(sentence_cv, 4),
            "ttr": round(ttr, 4),
            "punct_kinds": punct_kinds,
            "boilerplate_hits": boilerplate_hits,
            "n_sentences": n_sentences,
            "n_tokens": n_tokens,
        },
    }
