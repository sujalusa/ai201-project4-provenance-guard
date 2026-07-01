"""Append-only audit log, stored as JSONL on disk (planning.md storage decision).

Every attribution decision and every appeal is one line of JSON. Inspectable,
survives restarts, and backs GET /log.
"""

import json
import os
from datetime import datetime, timezone

_LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.jsonl")


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def append(entry):
    """Append one entry (dict) to the log, stamping a timestamp if absent."""
    entry.setdefault("timestamp", _now_iso())
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_all():
    """Return every log entry as a list of dicts (oldest first)."""
    if not os.path.exists(_LOG_PATH):
        return []
    entries = []
    with open(_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries
