"""Transport live telemetrie — jediné miesto, kde shipper agenta a zrkadlo webapp hovoria so
sieťou (docs/LIVE.md, „Transport“).

Dnes ide všetko cez HTTP hubu (`HttpTransport` nad `tester.hub.client.HubHttp`), ale shipper
ani zrkadlo cesty `/api/live/*` nepoznajú — vidia len tri operácie:

    push_events(agent, batches) -> {"accepted": n}    # agent → hub (idempotentné, kľúč (instance, session, seq))
    pull_export(after, limit)   -> [rows]             # hub → zrkadlo webapp, riadky od rowid `after`
    heartbeat(name, body)       -> odpoveď hubu       # voliteľné; hub agent ho dnes robí cez HubHttp

Ostatné cesty hubu (výpočty, tokeny, účty a nasadenia) sem **nepatria** — protokol výpočtov
agenta (`tester/hub/protocol.py`) je mimo rozsah transportu; cez `Transport` ide len telemetria.

Ako by to isté vyzeralo cez NATS (JetStream), keby raz HTTP nestačilo — len náčrt, žiadna
implementácia:

* `push_events(agent, batches)` = publish na subject `live.events.<agent>` (jedna správa = jedna
  dávka `{"instance", "session", "events"}`), JetStream stream `LIVE` so `subjects: live.events.>`
  a **dedup podľa `Nats-Msg-Id` = `<instance>/<session>/<seq prvého>-<seq posledného>`**; „200 od
  hubu“ je ACK publishu (PubAck) — kurzor spoolu sa posunie až po ňom, ako dnes.
* `pull_export(after, limit)` = durable pull consumer nad `LIVE` (`deliver_policy: by_start_sequence`,
  `after` = stream sequence, `limit` = batch `fetch(limit)`); rowid hubu nahradí sequence streamu,
  kurzor zrkadla ostáva jedno číslo (`tester/live/mirror_cursor.json` má už `hub_url`, pod ktorým
  sa kurzor pri zmene adresy zahodí).
* `heartbeat(name, body)` = request/reply na `hub.agents.<name>.heartbeat`.
* Hub sa z aktívneho servera stane konzumentom toho istého streamu (`LiveStore.ingest` z
  `live.events.>`), takže sqlite hubu ostáva a `/api/live/instances*` bežia ako dnes.

Spätná kompatibilita: `as_transport(obj)` vezme čokoľvek — hotový `Transport` vráti, ako je;
objekt s `.post()`/`.get()` (starý `http` shipperu, falošné HTTP v testoch) zabalí do
`HttpTransport`.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = ["Transport", "HttpTransport", "as_transport", "EVENTS_PATH", "EXPORT_PATH"]

EVENTS_PATH = "/api/live/events"
EXPORT_PATH = "/api/live/export"


@runtime_checkable
class Transport(Protocol):
    """Čo shipper a zrkadlo od transportu potrebujú. Každá metóda pri chybe **vyhodí výnimku**
    (spadnuté spojenie, 4xx/5xx) — volajúci nechá kurzor stáť a skúsi to v ďalšom kole."""

    def push_events(self, agent: str, batches: list[dict[str, Any]]) -> dict[str, Any]:
        """`batches` = `[{"instance", "session", "events": [...]}, …]` → `{"accepted": n}`."""
        ...

    def pull_export(self, after: int = 0, limit: int = 5000) -> list[dict[str, Any]]:
        """Riadky `{"id", "agent", "instance", "session", "event"}` s `id > after`, najviac `limit`."""
        ...


class HttpTransport:
    """`Transport` nad HTTP hubu: `http` je `tester.hub.client.HubHttp` (alebo čokoľvek
    s `post(path, body)` a `get(path)`)."""

    def __init__(self, http: Any) -> None:
        self.http = http

    def push_events(self, agent: str, batches: list[dict[str, Any]]) -> dict[str, Any]:
        odpoved = self.http.post(EVENTS_PATH, {"agent": agent, "batches": batches})
        return odpoved if isinstance(odpoved, dict) else {}

    def pull_export(self, after: int = 0, limit: int = 5000) -> list[dict[str, Any]]:
        rows = self.http.get(f"{EXPORT_PATH}?after={int(after)}&limit={int(limit)}")
        return rows if isinstance(rows, list) else []

    def heartbeat(self, name: str, body: dict[str, Any]) -> dict[str, Any]:
        from urllib.parse import quote

        return self.http.post(f"/api/agents/{quote(name, safe='')}/heartbeat", body)

    def __repr__(self) -> str:
        return f"HttpTransport({getattr(self.http, 'url', self.http)!r})"


def as_transport(obj: Any) -> Any:
    """Hotový transport vráti; objekt s `.post`/`.get` (HubHttp, falošné HTTP) zabalí."""
    if obj is None:
        raise TypeError("transport nesmie byť None")
    if hasattr(obj, "push_events") and hasattr(obj, "pull_export"):
        return obj
    if hasattr(obj, "post") or hasattr(obj, "get"):
        return HttpTransport(obj)
    raise TypeError(f"{type(obj).__name__} nie je Transport ani HTTP klient hubu")
