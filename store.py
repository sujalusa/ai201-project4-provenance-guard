"""Content store — the mutable record of each submission (planning.md storage).

The audit log (audit.py) is append-only history; this is the current-state view
keyed by content_id, so an appeal can flip a piece's status to "under_review".
Persisted as a single JSON object on disk.
"""

import json
import os

_STORE_PATH = os.path.join(os.path.dirname(__file__), "content_store.json")


def _load():
    if not os.path.exists(_STORE_PATH):
        return {}
    with open(_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def put(content_id, record):
    """Create or overwrite the record for content_id."""
    data = _load()
    data[content_id] = record
    _save(data)
    return record


def get(content_id):
    """Return the record for content_id, or None if unknown."""
    return _load().get(content_id)


def update_status(content_id, status, **extra):
    """Set status (and any extra fields) on an existing record. Returns the
    updated record, or None if content_id is unknown."""
    data = _load()
    record = data.get(content_id)
    if record is None:
        return None
    record["status"] = status
    record.update(extra)
    _save(data)
    return record
