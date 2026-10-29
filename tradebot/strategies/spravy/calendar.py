"""Kalendár červených správ USA pre stratégiu SPRÁVY — jeden zdroj pre Python aj C# jadro.

`calendar.json` drží dátumy po typoch a čas vydania v **New Yorku** (`time_et`). Prevod na UTC robí
`America/New_York` pre každý deň zvlášť, takže sedí aj v týždňoch, keď USA a Európa menia čas v iné dni
(marec, október / november). C# jadro má ten istý zoznam vygenerovaný do `ports/csharp/SpravyCalendar.cs`
(`python -m tradebot.strategies.spravy.calendar --cs`); zhodu stráži test.

Opravy bez zmeny kódu (presunutá alebo pridaná správa, napr. pri shutdowne) idú cez profil:
`newsAdd` = "2026-11-25 08:30 PPI; …", `newsSkip` = "2026-11-13 PPI; …".
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

__all__ = ["CALENDAR_FILE", "TYPES", "NY", "load", "events_utc", "parse_add", "parse_skip", "to_utc_ms"]

CALENDAR_FILE = Path(__file__).resolve().parent / "calendar.json"
NY = ZoneInfo("America/New_York")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))


TYPES: tuple[str, ...] = tuple(load()["events"].keys())


def to_utc_ms(day: date, hhmm: str) -> int:
    """Miestny čas New York → UTC ms (letný / zimný čas podľa dňa)."""
    hh, mm = (int(x) for x in hhmm.split(":"))
    local = datetime(day.year, day.month, day.day, hh, mm, tzinfo=NY)
    return int(local.astimezone(timezone.utc).timestamp() * 1000)


def parse_add(text: str) -> list[tuple[date, str, str]]:
    """"YYYY-MM-DD HH:MM TYP; …" → [(deň, čas, typ)]."""
    out = []
    for part in (text or "").replace("\n", ";").split(";"):
        bits = part.split()
        if len(bits) == 3:
            out.append((date.fromisoformat(bits[0]), bits[1], bits[2].upper()))
    return out


def parse_skip(text: str) -> set[tuple[date, str]]:
    """"YYYY-MM-DD TYP; …" → {(deň, typ)}."""
    out = set()
    for part in (text or "").replace("\n", ";").split(";"):
        bits = part.split()
        if len(bits) == 2:
            out.add((date.fromisoformat(bits[0]), bits[1].upper()))
    return out


def events_utc(types: set[str] | None = None, add: str = "", skip: str = "") -> list[tuple[int, str]]:
    """Zoradené (UTC ms, typ) vybraných typov; s opravami z profilu."""
    cal = load()["events"]
    skipped = parse_skip(skip)
    out: list[tuple[int, str]] = []
    for typ, ev in cal.items():
        if types is not None and typ not in types:
            continue
        for d in ev["dates"]:
            day = date.fromisoformat(d)
            if (day, typ) in skipped:
                continue
            out.append((to_utc_ms(day, ev["time_et"]), typ))
    for day, hhmm, typ in parse_add(add):
        if types is None or typ in types:
            out.append((to_utc_ms(day, hhmm), typ))
    return sorted(set(out))


def csharp_source() -> str:
    """Zoznam pre C# jadro: (rok, mesiac, deň, hodina, minúta, typ) v čase New York."""
    cal = load()["events"]
    rows = []
    for typ, ev in cal.items():
        hh, mm = (int(x) for x in ev["time_et"].split(":"))
        for d in ev["dates"]:
            y, m, dd = (int(x) for x in d.split("-"))
            rows.append(f'            new Ev({y}, {m}, {dd}, {hh}, {mm}, "{typ}"),')
    body = "\n".join(rows)
    return f"""// VYGENEROVANÉ z tradebot/strategies/spravy/calendar.json — needitovať ručne.
// python -m tradebot.strategies.spravy.calendar --cs
using System;

namespace TradeBot.Strategies.SpravyNet
{{
    public static class SpravyCalendar
    {{
        public struct Ev
        {{
            public readonly int Y, M, D, H, Min;
            public readonly string Type;
            public Ev(int y, int m, int d, int h, int min, string type) {{ Y = y; M = m; D = d; H = h; Min = min; Type = type; }}
        }}

        /// <summary>Čas vydania v New Yorku (miestny, letný / zimný čas podľa dňa).</summary>
        public static readonly Ev[] Events = new Ev[]
        {{
{body}
        }};
    }}
}}
"""


if __name__ == "__main__":
    import sys

    if "--cs" in sys.argv:
        target = Path(__file__).resolve().parent / "ports" / "csharp" / "SpravyCalendar.cs"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(csharp_source(), encoding="utf-8")
        print(f"zapísané {target}")
    else:
        ev = events_utc()
        print(len(ev), "udalostí;", datetime.fromtimestamp(ev[0][0] / 1000, tz=NY), "…",
              datetime.fromtimestamp(ev[-1][0] / 1000, tz=NY))
