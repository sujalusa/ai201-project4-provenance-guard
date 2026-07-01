"""Provenance Guard — Flask app.

Full pipeline: POST /submit runs two detection signals (stylometry + Groq),
fuses them into an agreement-weighted confidence, builds a transparency label,
and records the decision in an append-only audit log. POST /appeal lets creators
contest a verdict (status -> under_review, logged). Rate limiting protects the
write endpoints; GET /log surfaces the audit trail.
"""

import uuid

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import audit
import store
from fusion import fuse
from labels import build_label
from llm_signal import llm_score
from stylometry import stylometry_score

load_dotenv()

app = Flask(__name__)

# Rate limiting (planning.md §API). Per-IP, in-memory store for local dev.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

MIN_WORDS = 8  # below this, text is too short to analyze (planning.md §5)

# Maps the internal verdict to the public attribution string.
_ATTRIBUTION = {"ai": "likely_ai", "human": "likely_human", "uncertain": "uncertain"}


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text:
        return jsonify({"error": "field 'text' is required"}), 400
    if not creator_id:
        return jsonify({"error": "field 'creator_id' is required"}), 400

    sty = stylometry_score(text)
    if sty["metrics"]["n_tokens"] < MIN_WORDS:
        return jsonify({"error": f"text too short to analyze (min {MIN_WORDS} words)"}), 400

    # Two signals -> agreement-weighted fusion -> transparency label.
    llm = llm_score(text)
    fused = fuse(sty["score"], llm["score"])
    attribution = _ATTRIBUTION[fused["verdict"]]
    label_text = build_label(
        fused["verdict"], fused["confidence"], fused["combined_score"], fused["agreement"]
    )

    content_id = str(uuid.uuid4())

    # Current-state record (mutable; appeals flip its status).
    store.put(content_id, {
        "content_id": content_id,
        "creator_id": creator_id,
        "text_excerpt": text[:200],
        "attribution": attribution,
        "confidence": fused["confidence"],
        "combined_score": fused["combined_score"],
        "stylometry_score": sty["score"],
        "llm_score": llm["score"],
        "status": "classified",
        "appeal_filed": False,
    })

    # Append-only audit record.
    audit.append({
        "content_id": content_id,
        "creator_id": creator_id,
        "type": "decision",
        "attribution": attribution,
        "confidence": fused["confidence"],
        "combined_score": fused["combined_score"],
        "stylometry_score": sty["score"],
        "stylometry_metrics": sty["metrics"],
        "llm_score": llm["score"],
        "llm_reasoning": llm["reasoning"],
        "agreement": fused["agreement"],
        "label_text": label_text,
        "appeal_filed": False,
        "status": "classified",
    })

    return jsonify({
        "content_id": content_id,
        "creator_id": creator_id,
        "attribution": attribution,
        "confidence": fused["confidence"],
        "signals": {"stylometry": sty["score"], "llm": llm["score"]},
        "combined_score": fused["combined_score"],
        "label_text": label_text,
        "status": "classified",
    })


@app.route("/appeal", methods=["POST"])
@limiter.limit("20 per hour")
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = (data.get("content_id") or "").strip()
    reasoning = (data.get("creator_reasoning") or data.get("reason") or "").strip()

    if not content_id:
        return jsonify({"error": "field 'content_id' is required"}), 400
    if not reasoning:
        return jsonify({"error": "field 'creator_reasoning' is required"}), 400

    original = store.get(content_id)
    if original is None:
        return jsonify({"error": f"unknown content_id '{content_id}'"}), 404

    store.update_status(content_id, "under_review", appeal_filed=True)

    audit.append({
        "content_id": content_id,
        "creator_id": original.get("creator_id"),
        "type": "appeal",
        "appeal_reasoning": reasoning,
        "original_attribution": original.get("attribution"),
        "original_confidence": original.get("confidence"),
        "appeal_filed": True,
        "status": "under_review",
    })

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "appeal_logged": True,
        "message": "Appeal received. This content is now under human review.",
    })


@app.route("/log", methods=["GET"])
def log():
    entries = audit.read_all()
    content_id = request.args.get("content_id")
    status = request.args.get("status")
    if content_id:
        entries = [e for e in entries if e.get("content_id") == content_id]
    if status:
        entries = [e for e in entries if e.get("status") == status]
    return jsonify({"entries": entries})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
