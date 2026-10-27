"""Odosielanie spoolu na hub: `LiveShipper.pump()` číta dávky z `SpoolReader`, pošle ich cez
`Transport.push_events` a **kurzor posunie až po potvrdení** — hub dole = kurzor stojí, nič sa
nestratí, nič sa nepošle dvakrát (a keby aj, hub je idempotentný).

`transport` je `tradebot.live.transport.Transport` (dnes `HttpTransport` nad
`tester.hub.client.HubHttp`, ktorý POSTuje na `/api/live/events`). Kvôli starým volajúcim
a testom sa berie aj holý HTTP klient s `.post()` — zabalí ho `as_transport`.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .spool import Batch, SpoolReader
from .transport import EVENTS_PATH, as_transport

__all__ = ["LiveShipper", "EVENTS_PATH"]

log = logging.getLogger(__name__)


#: Udalostí na jeden POST najviac. Réžia požiadavky na hub (100–200 ms cez verejnú adresu, občas sekundy)
#: prevýši spracovanie — po 500 dobiehala história po reštarte platforiem ~240/s. Veľkosť sa ale prispôsobuje
#: (`BATCH_START` → dvojnásobok, kým hub odpovie do `BATCH_FAST` s; polovica, keď je pomalý alebo POST zlyhá):
#: hub na NAS-e pod záťažou nestihol 2000 udalostí do timeoutu agenta (30 s) a tú istú dávku dostával dookola.
BATCH_EVENTS = 2000
BATCH_START = 500
BATCH_MIN = 50
BATCH_FAST = 3.0
BATCH_SLOW = 10.0


class LiveShipper:
    def __init__(self, reader: SpoolReader, transport: Any, agent: str, *, batch_events: int = BATCH_EVENTS,
                 max_batches: int = 20, clock=time.time) -> None:
        self.reader = reader
        self.transport = as_transport(transport)
        #: Podkladový HTTP klient, keď ho transport má (stav agenta, staré volania) — inak transport sám.
        self.http = getattr(self.transport, "http", self.transport)
        self.agent = agent
        self.batch_events = max(1, int(batch_events))
        #: Aktuálna veľkosť dávky (prispôsobuje sa odozve hubu, strop `batch_events`).
        self.batch_now = min(BATCH_START, self.batch_events)
        self.max_batches = max(1, int(max_batches))
        self.clock = clock
        self.last_ok: float | None = None
        self.last_error: str | None = None
        self.sent_total = 0
        self.accepted_total = 0
        #: Diagnostika posledného kola: priemer čítania spoolu a POST-u na dávku (ms), udalostí/s.
        self.read_ms: float | None = None
        self.post_ms: float | None = None
        self.rate: float | None = None

    @staticmethod
    def batches_body(batches: list[Batch]) -> list[dict[str, Any]]:
        """Dávky v tvare transportu: `[{"instance", "session", "events"}, …]`."""
        return [{"instance": b.instance, "session": b.session, "events": b.events} for b in batches]

    @staticmethod
    def body(agent: str, batches: list[Batch]) -> dict[str, Any]:
        """Celé telo `POST /api/live/events` (ako ho posiela `HttpTransport`)."""
        return {"agent": agent, "batches": LiveShipper.batches_body(batches)}

    def pump(self) -> dict[str, Any]:
        """Jedno kolo: kým je čo posielať (najviac `max_batches` čítaní), pošli a potvrď.
        Pri chybe skončí bez posunu kurzora — ďalšie kolo to skúsi znova od toho istého miesta."""
        sent = accepted = rounds = 0
        error: str | None = None
        cit = posl = 0.0
        kolo = time.monotonic()
        for _ in range(self.max_batches):
            t0 = time.monotonic()
            batches = self.reader.read(self.batch_now)
            cit += time.monotonic() - t0
            if not batches:
                break
            rounds += 1
            zaciatok = time.monotonic()
            try:
                odpoved = self.transport.push_events(self.agent, self.batches_body(batches))
            except Exception as exc:  # noqa: BLE001 - hub mimo, sieť, 4xx/5xx — kurzor ostáva
                error = f"{type(exc).__name__}: {exc}"
                self.batch_now = max(min(BATCH_MIN, self.batch_events), self.batch_now // 2)
                break
            trvanie = time.monotonic() - zaciatok
            posl += trvanie
            if trvanie > BATCH_SLOW:
                self.batch_now = max(min(BATCH_MIN, self.batch_events), self.batch_now // 2)
            elif trvanie < BATCH_FAST:
                self.batch_now = min(self.batch_events, self.batch_now * 2)
            for b in batches:
                self.reader.commit(b)
            n = sum(len(b.events) for b in batches)
            sent += n
            prijate = odpoved.get("accepted") if isinstance(odpoved, dict) else None
            accepted += int(prijate) if isinstance(prijate, (int, float)) else n
            self.last_ok = self.clock()
            self.last_error = None
        if error is not None:
            self.last_error = error
        if rounds:
            self.read_ms, self.post_ms = cit / rounds * 1000, posl / rounds * 1000
            self.rate = sent / max(1e-6, time.monotonic() - kolo)
        self.sent_total += sent
        self.accepted_total += accepted
        return {"sent": sent, "accepted": accepted, "rounds": rounds, "error": error}

    def status(self) -> dict[str, Any]:
        return {"agent": self.agent, "last_ok": self.last_ok, "last_error": self.last_error, "batch": self.batch_now,
                "read_ms": self.read_ms, "post_ms": self.post_ms, "rate": self.rate, "files": self.reader.files,
                "sent_total": self.sent_total, "accepted_total": self.accepted_total,
                "reader": self.reader.status()}
