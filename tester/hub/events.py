"""Log udalostí hubu: v pamäti posledné, na disku všetko (`events.jsonl`, rotuje sa)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


#: Koľko udalostí sa drží v pamäti na čítanie cez API; súbor rastie ďalej (rotuje sa).
EVENTS_KEEP = 5000
EVENTS_ROTATE_BYTES = 20 * 1024 * 1024


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


class EventsMixin:
    """Log udalostí (`events.jsonl`) — časť `HubState`."""

    @property
    def events_file(self) -> Path:
        return self.root / "events.jsonl"

    def _load_events(self) -> None:
        if not self.events_file.exists():
            return
        try:
            riadky = self.events_file.read_text(encoding="utf-8").splitlines()[-EVENTS_KEEP:]
        except OSError:
            return
        for line in riadky:
            try:
                self._events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def log(self, event: str, **fields: Any) -> None:
        """Jedna udalosť do pamäte aj do `events.jsonl` (prázdne polia sa nepíšu)."""
        zaznam = {"ts": _iso(self.clock()), "event": event,
                  **{k: v for k, v in fields.items() if v is not None and v != ""}}
        with self._lock:
            self._events.append(zaznam)
            try:
                if self.events_file.exists() and self.events_file.stat().st_size > EVENTS_ROTATE_BYTES:
                    os.replace(self.events_file, self.events_file.with_suffix(".1.jsonl"))
                with open(self.events_file, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(zaznam, ensure_ascii=False, default=str) + "\n")
            except OSError:
                pass

    def events(self, limit: int = 100, job: str | None = None, agent: str | None = None,
               event: str | None = None) -> list[dict[str, Any]]:
        """Posledné udalosti, od najnovšej; filtre podľa výpočtu, agenta a druhu."""
        with self._lock:
            out = []
            for e in reversed(self._events):
                if job and e.get("job") != job:
                    continue
                if agent and agent not in (e.get("agent"), e.get("submitter"), e.get("by")):
                    continue
                if event and e.get("event") != event:
                    continue
                out.append(dict(e))
                if len(out) >= max(1, int(limit)):
                    break
            return out
