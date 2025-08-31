"""In-memory job store for report rendering jobs.

This store is intentionally simple and only suitable for development and
continuous integration environments. It keeps job metadata in-process and is
protected by a threading lock for concurrent access from the API and worker
threads.
"""

import threading
import time
import hashlib
import json
from typing import Dict, Any, Optional

_STATUS = ("queued", "processing", "done", "error")


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.time()

    def _hash(self, payload: dict) -> str:
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return h

    # Basic CRUD helpers -------------------------------------------------

    def get(self, rid: str) -> Optional[dict]:
        with self._lock:
            return self._jobs.get(rid)

    def find_by_fingerprint(self, fprint: str) -> Optional[str]:
        """Return existing report id by fingerprint if present."""
        with self._lock:
            for rid, meta in self._jobs.items():
                if meta.get("fingerprint") == fprint:
                    return rid
        return None

    def create(self, payload: dict, idempotency_key: Optional[str]) -> str:
        """Create a job and return its id.

        If a job with the same payload and idempotency key already exists, the
        existing id is returned to satisfy idempotency.
        """

        fprint = self._hash({"payload": payload, "idk": idempotency_key or ""})
        existing = self.find_by_fingerprint(fprint)
        if existing:
            return existing
        rid = "rpt_" + self._hash({"t": self._now(), "rand": id(payload)})[:18]
        with self._lock:
            self._jobs[rid] = {
                "status": "queued",
                "payload": payload,
                "created_at": self._now(),
                "fingerprint": fprint,
                "file_path": None,
                "error": None,
            }
        return rid

    def update(self, rid: str, **patch: Any) -> None:
        with self._lock:
            if rid in self._jobs:
                self._jobs[rid].update(patch)


# Global singleton store used by API and worker.
STORE = JobStore()

