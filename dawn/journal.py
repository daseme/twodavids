"""The journal: reproducibility is the journal, nothing else.

Every oracle call and world event as JSONL. Seed + journal = world. The
journal is simultaneously the almanac's raw source layer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _clean(x):
    import numpy as np
    if isinstance(x, dict):
        # Keys become strings here so in-memory records hash identically to
        # records re-read from disk (replay verification depends on this).
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return [round(float(v), 4) for v in x]
    if isinstance(x, (np.floating,)):
        return round(float(x), 6)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


class Journal:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.records: list[dict] = []
        self._fh = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = path.open("w")

    def write(self, rec: dict) -> None:
        rec = _clean(rec)
        self.records.append(rec)
        if self._fh is not None:
            self._fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def flush(self) -> None:
        if self._fh is not None:
            self._fh.flush()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for rec in self.records:
            h.update(json.dumps(rec, sort_keys=True).encode())
        return h.hexdigest()


def read_journal(path: Path) -> list[dict]:
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]
