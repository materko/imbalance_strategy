"""Denník obchodov agenta (docs/LIVE.md, „Telegram“ → 🧾 Obchody, 📈 Výkon).

Agent číta spool **vlastným kurzorom** (`LIVE_JOURNAL_CURSOR`, nezávisle od shippera aj od správ
Telegramu) a do `LIVE_JOURNAL` (JSONL, append) zapisuje, čo sa s ordermi stalo: zámer vstupu
(`entry`, len `ready` — nie predhistória), zrušenie čakajúceho vstupu (`cancel`), vyplnenie vstupu
(`in`) a výstupu (`out` s P&L v bodoch a v $ z tej istej priemernej ceny vstupu ako správa
o výstupe — `format_event`). Hub ani webapp netreba.

Prvý štart prejde celý spool, takže v denníku sú aj staré obchody. Výpadok uprostred = kurzor stojí
a čo už je v denníku, sa nezopakuje (`(instance, session, seq)` v `LIVE_JOURNAL_STATE`). Beh
v Testeri / Analyzeri sa nezapisuje.

Záznam: `{"k", "t" (ms UTC), "instance", "session", "seq", "platform", "account", "symbol", "tf",
"strategy", "profile", …polia podľa druhu}`. P&L je **hrubý** — spool poplatky nenesie.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable, Iterable

from .telegram import LiveNotifier, TelegramConfig, TelegramState

__all__ = ["TradeJournal", "JournalBuilder"]

log = logging.getLogger(__name__)

#: Polia inštancie, ktoré idú do každého záznamu.
INSTANCE_FIELDS = ("platform", "account", "symbol", "tf", "strategy", "profile")


class TradeJournal:
    """Súbor denníka: pridávanie a čítanie (malý — riadok na order, nie na bar)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(self, records: Iterable[dict[str, Any]]) -> int:
        riadky = [json.dumps(r, ensure_ascii=False, default=str) for r in records]
        if not riadky:
            return 0
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(riadky) + "\n")
        return len(riadky)

    def read(self, *, since_ms: float | None = None, instance: str | None = None) -> list[dict[str, Any]]:
        try:
            with self._lock:
                data = self.path.read_text(encoding="utf-8")
        except OSError:
            return []
        out, videne = [], set()
        for riadok in data.splitlines():
            try:
                r = json.loads(riadok)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if instance is not None and r.get("instance") != instance:
                continue
            if since_ms is not None and float(r.get("t") or 0) < since_ms:
                continue
            kluc = (r.get("instance"), r.get("session"), r.get("seq"), r.get("k"))
            if r.get("seq") is not None and kluc in videne:   # pád medzi zápisom a stavom = riadok dvakrát
                continue
            videne.add(kluc)
            out.append(r)
        return out


class JournalBuilder(LiveNotifier):
    """Spool → denník. Ten istý prechod udalostí ako notifier správ (kontext inštancie, P&L výstupu), ale
    s vlastným stavom a kurzorom, nič neposiela a začína od začiatku spoolu."""

    def __init__(self, reader: Any, journal: TradeJournal, state_path: Path, *,
                 clock: Callable[[], float] | None = None) -> None:
        import time

        super().__init__(reader, None, TelegramConfig(token="", notes="off"), TelegramState(state_path),
                         clock=clock or time.time)
        self.journal = journal
        self._silent = True   # životný cyklus sa nezbiera
        self._pending: list[dict[str, Any]] = []
        self._recorder = self._make_record

    def _make_record(self, batch: Any, ctx: dict[str, Any], ev: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
        def rec(r: dict[str, Any]) -> None:
            t = r.get("ft") or ev.get("t")
            self._pending.append({**r, "t": t, "instance": batch.instance, "session": batch.session,
                                  "seq": ev.get("seq"), **{f: ctx.get(f) for f in INSTANCE_FIELDS}})
        return rec

    def pump(self, max_events: int = 5000) -> dict[str, Any]:
        """Prečítaj, zapíš, potvrď — dávku po dávke, kým spool nedobehne (najviac 50 kôl naraz)."""
        zapisane = 0
        for _ in range(50):
            batches = self.reader.read(max_events)
            if not batches:
                break
            for batch in batches:
                self._pending = []
                riadky = self.messages(batch)
                zapisane += self.journal.append(self._pending)
                self._pending = []
                if riadky:
                    kluc = f"{batch.instance}|{batch.session}"
                    self.state["seq"][kluc] = max(int(self.state["seq"].get(kluc) or 0), riadky[-1][0])
                self.state.data["initialized"] = True
                self.state.save()
                self.reader.commit(batch)
        return {"written": zapisane}
