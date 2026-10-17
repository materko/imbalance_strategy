"""Export kalendára ForexFactory: stiahnutie a rozbor.

Zdroj je oficiálny export (`https://www.forexfactory.com/calendar` → „Export“): JSON aktuálneho
týždňa na `nfs.faireconomy.media`. Stránku samu (Cloudflare, HTML) nečítame. Čas je **New York
s posunom** (`2026-10-14T08:30:00-04:00`), takže prevod na pásmo hubu je presný aj v týždňoch,
keď USA a Európa menia letný čas v iné dni. Týždeň exportu je nedeľa–sobota podľa New Yorku; na
budúci týždeň export nemá nič, kým sa neprehodí.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Any

__all__ = ["FF_URL", "fetch", "parse_feed", "feed_week", "ny_week", "zone"]

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def zone(name: str, fallback: tzinfo | None = None) -> tzinfo:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - bez tzdata
        return fallback or datetime.now().astimezone().tzinfo or timezone.utc


NY = zone("America/New_York", timezone(timedelta(hours=-5)))


def fetch(url: str = FF_URL, timeout: float = 20.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "TradeBot-hub/1 (ff_calendar)",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - adresa z configu hubu
        body = resp.read().decode("utf-8")
    try:
        return json.loads(body)
    except ValueError as exc:   # pri prekročení limitu príde HTML stránka
        raise ValueError(f"nie je JSON ({body[:80]!r})") from exc


def parse_feed(raw: Any) -> list[dict[str, Any]]:
    """Export → udalosti s `ts` (UTC epoch) a `ny_date` (deň v New Yorku). Bez času či s chybným časom von."""
    out = []
    for e in raw if isinstance(raw, list) else []:
        if not isinstance(e, dict):
            continue
        try:
            dt = datetime.fromisoformat(str(e.get("date") or ""))
        except ValueError:
            continue
        if dt.tzinfo is None:
            continue
        out.append({"title": str(e.get("title") or "").strip(), "country": str(e.get("country") or "").strip(),
                    "impact": str(e.get("impact") or "").strip(), "ts": dt.timestamp(),
                    "ny_date": dt.date().isoformat(),
                    "forecast": str(e.get("forecast") or "").strip(), "previous": str(e.get("previous") or "").strip()})
    return sorted(out, key=lambda x: (x["ts"], x["country"], x["title"]))


def _sunday(d: date) -> date:
    return d - timedelta(days=(d.weekday() + 1) % 7)


def feed_week(events: list[dict[str, Any]]) -> date | None:
    """Nedeľa týždňa, ktorý export pokrýva."""
    if not events:
        return None
    return _sunday(min(date.fromisoformat(e["ny_date"]) for e in events))


def ny_week(now: float) -> date:
    """Nedeľa aktuálneho týždňa v New Yorku."""
    return _sunday(datetime.fromtimestamp(now, NY).date())
