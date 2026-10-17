"""Čo a kedy poslať: config, výber udalostí, splatné upozornenia a text správy (bez stavu a siete)."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime, tzinfo
from typing import Any

from .feed import zone

__all__ = ["CalendarConfig", "remind_offsets", "event_key", "wanted", "due", "message", "AT_GRACE"]

#: Upozornenie „v čase udalosti“ (0 min) smie prísť ešte toľko po nej.
AT_GRACE = 120.0
DNI = ("po", "ut", "st", "št", "pi", "so", "ne")


def remind_offsets(lead: float = 30, count: int = 1, every: float = 10) -> list[float]:
    """`lead` minút pred udalosťou a potom ešte `count - 1`-krát po `every` minútach bližšie."""
    out = [float(lead) - i * float(every) for i in range(max(1, int(count)))]
    return sorted({o for o in out if o >= 0}, reverse=True)


@dataclass
class CalendarConfig:
    impact: list[str] = field(default_factory=lambda: ["High"])
    currencies: list[str] = field(default_factory=list)
    remind_min: list[float] = field(default_factory=lambda: [30.0])
    tz: str = "Europe/Bratislava"
    #: čas dňa (v `tz`), kedy sa export stiahne
    refresh: str = "07:00"
    chats: list[int] = field(default_factory=list)
    url: str = ""

    def zone(self) -> tzinfo:
        return zone(self.tz)

    def refresh_hm(self) -> tuple[int, int]:
        try:
            h, m = (int(x) for x in str(self.refresh).split(":", 1))
            if 0 <= h < 24 and 0 <= m < 60:
                return h, m
        except ValueError:
            pass
        return 7, 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalendarConfig":
        """Config pluginu; chýbajúce kľúče = predvolené (High, všetky meny, 1× 30 min pred, 07:00)."""
        c = cls()
        imp = data.get("impact")
        if isinstance(imp, str):
            imp = [imp]
        if imp:
            c.impact = [str(i).strip().capitalize() for i in imp]
        cur = data.get("currencies")
        if isinstance(cur, str):
            cur = cur.replace(";", ",").split(",")
        c.currencies = [str(x).strip().upper() for x in (cur or []) if str(x).strip()]
        if isinstance(data.get("remind_min"), list) and data["remind_min"]:
            c.remind_min = sorted({float(m) for m in data["remind_min"] if float(m) >= 0}, reverse=True)
        elif any(k in data for k in ("lead_min", "count", "every_min")):
            c.remind_min = remind_offsets(data.get("lead_min", 30), data.get("count", 1), data.get("every_min", 10))
        c.tz = str(data.get("tz") or c.tz)
        c.refresh = str(data.get("refresh") or c.refresh)
        ch = data.get("chats")
        if ch:
            c.chats = [int(x) for x in (ch if isinstance(ch, list) else str(ch).split(",")) if str(x).strip()]
        c.url = str(data.get("url") or "")
        return c


def event_key(e: dict[str, Any]) -> str:
    return f"{int(e['ts'])}|{e['country']}|{e['title']}"


def wanted(events: list[dict[str, Any]], cfg: CalendarConfig) -> list[dict[str, Any]]:
    imp = {i.lower() for i in cfg.impact}
    cur = set(cfg.currencies)
    return [e for e in events if e["impact"].lower() in imp and (not cur or e["country"].upper() in cur)]


def due(events: list[dict[str, Any]], cfg: CalendarConfig, sent: dict[str, list[float]],
        now: float) -> list[tuple[list[dict[str, Any]], list[float]]]:
    """Skupiny udalostí (rovnaký čas) a minúty upozornení, ktoré už mali prísť a neprišli.
    Keď hub v čase upozornenia nebežal, príde jedno oneskorené, kým udalosť nenastala."""
    skupiny: dict[float, list[dict[str, Any]]] = {}
    for e in wanted(events, cfg):
        skupiny.setdefault(e["ts"], []).append(e)
    out = []
    for ts, group in sorted(skupiny.items()):
        minuty = []
        for o in cfg.remind_min:
            koniec = ts + AT_GRACE if o <= 0 else ts
            if ts - o * 60 <= now < koniec and any(o not in sent.get(event_key(e), []) for e in group):
                minuty.append(o)
        if minuty:
            out.append((group, minuty))
    return out


def when(ts: float, now: float, z: tzinfo) -> str:
    d = datetime.fromtimestamp(ts, z)
    if d.date() == datetime.fromtimestamp(now, z).date():
        return d.strftime("%H:%M")
    return f"{DNI[d.weekday()]} {d.day}. {d.month}. {d.strftime('%H:%M')}"


def in_minutes(minutes: float) -> str:
    m = int(round(minutes))
    if m <= 0:
        return "teraz"
    if m < 90:
        return f"o {m} min"
    h, r = divmod(m, 60)
    return f"o {h} h {r} min" if r else f"o {h} h"


def message(group: list[dict[str, Any]], cfg: CalendarConfig, now: float) -> str:
    """HTML: `🔴 o 30 min · 14:30` a riadok na udalosť (mena, názov, prognóza, predtým)."""
    ts = group[0]["ts"]
    hlava = f"🔴 <b>{in_minutes((ts - now) / 60)}</b> · <b>{when(ts, now, cfg.zone())}</b>"
    if [i.lower() for i in cfg.impact] != ["high"]:
        hlava += " · " + "/".join(sorted({e["impact"] for e in group}))
    riadky = [hlava]
    for e in group:
        r = f"<b>{html.escape(e['country'])}</b> {html.escape(e['title'])}"
        cisla = [f"{n} {html.escape(e[k])}" for n, k in (("progn.", "forecast"), ("pred.", "previous")) if e[k]]
        if cisla:
            r += " · " + " · ".join(cisla)
        riadky.append(r)
    return "\n".join(riadky)
