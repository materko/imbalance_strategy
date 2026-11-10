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

__all__ = ["CALENDAR_FILE", "TYPES", "NY", "CalendarError", "load", "events_utc", "parse_add", "parse_skip", "to_utc_ms",
           "last_dates", "coverage_gaps"]

CALENDAR_FILE = Path(__file__).resolve().parent / "calendar.json"
NY = ZoneInfo("America/New_York")


#: Typy správ = polia `use<TYP>` v `SpravyConfig`; zhodu s `calendar.json` stráži `test_spravy_calendar.py`.
#: Použijú sa len vtedy, keď sa kalendár pri importe nedá prečítať (viď `_types`).
_KNOWN_TYPES: tuple[str, ...] = ("FOMC", "FOMC_MIN", "CPI", "NFP", "PPI", "JOLTS", "RETAIL", "PCE", "GDP",
                                 "ISM_M", "ISM_S", "CLAIMS")


class CalendarError(ValueError):
    """`calendar.json` chýba alebo je pokazený — stratégia SPRÁVY bez neho nemá čo obchodovať."""


@lru_cache(maxsize=1)
def load() -> dict:
    try:
        data = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("events"), dict):
            raise ValueError("chýba objekt 'events'")
    except (OSError, ValueError) as exc:
        raise CalendarError(f"kalendár správ {CALENDAR_FILE} sa nedá načítať: {exc}") from exc
    return data


def _types() -> tuple[str, ...]:
    """Typy z kalendára. Pokazený súbor nesmie pri importe zhodiť celý registry stratégií (audit M-CORE-9):
    formulár a config dostanú známe typy a chybu povie až `load()` — keď sa SPRÁVY naozaj použijú
    (engine pri štarte, kontrola pokrytia, generovanie C#)."""
    try:
        return tuple(load()["events"].keys())
    except CalendarError as exc:
        import logging

        logging.getLogger(__name__).error("%s — stratégia SPRÁVY nepôjde, ostatné áno", exc)
        return _KNOWN_TYPES


TYPES: tuple[str, ...] = _types()


def last_dates() -> dict[str, date]:
    """Posledný deň v kalendári za každý typ správy."""
    return {typ: max(date.fromisoformat(d) for d in ev["dates"]) for typ, ev in load()["events"].items() if ev["dates"]}


def coverage_gaps(today: date, days: int = 45) -> list[tuple[str, date]]:
    """Typy správ, ktorým kalendár končí do `days` dní od `today` (alebo už skončil): `[(typ, posledný deň)]`.

    Engine koniec kalendára nepozná — po poslednom dátume typu jednoducho žiadnu správu nevidí a stratégia ju
    naživo ticho prestane obchodovať (audit 9. 11. 2026, M-CORE-3). Úrady zverejňujú termíny na ďalší rok
    postupne, takže kalendár končí pre každý typ inokedy; toto je kontrola, ktorá to povie vopred
    (`python -m tradebot.strategies.spravy.calendar --check`, test `test_spravy_calendar.py`)."""
    limit = today.toordinal() + int(days)
    return sorted((typ, last) for typ, last in last_dates().items() if last.toordinal() < limit)


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


#: Názvy udalostí v exporte ForexFactory (krajina USD), ktoré patria k typu správy. Viac názvov jedného typu
#: vychádza v tom istom čase a počíta sa ako jedna správa. Zhoda je presná, bez ohľadu na veľkosť písmen.
#: Overené na exporte z 9.–13. 11. 2026: CPI, PPI, CLAIMS; ostatné podľa zaužívaných názvov ForexFactory —
#: nesprávny názov sa prejaví ako „v kalendári je, vo feede nie“ (`missing`), nikdy ako zrušená správa.
FF_TITLES: dict[str, tuple[str, ...]] = {
    "FOMC": ("Federal Funds Rate",),
    "FOMC_MIN": ("FOMC Meeting Minutes",),
    "CPI": ("CPI m/m", "Core CPI m/m", "CPI y/y"),
    "NFP": ("Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m"),
    "PPI": ("PPI m/m", "Core PPI m/m"),
    "JOLTS": ("JOLTS Job Openings",),
    "RETAIL": ("Retail Sales m/m", "Core Retail Sales m/m"),
    "PCE": ("Core PCE Price Index m/m",),
    "GDP": ("Advance GDP q/q", "Prelim GDP q/q", "Final GDP q/q"),
    "ISM_M": ("ISM Manufacturing PMI",),
    "ISM_S": ("ISM Services PMI",),
    "CLAIMS": ("Unemployment Claims",),
}
#: Správa mimo týchto hodín New Yorku je vo feede skoro určite chyba — do kalendára sa nepridá.
FF_HOURS = (4, 20)


def ff_type(title: str) -> str | None:
    """Typ správy podľa názvu udalosti ForexFactory, alebo `None`."""
    t = (title or "").strip().lower()
    for typ, names in FF_TITLES.items():
        if any(t == n.lower() for n in names):
            return typ
    return None


def week_diff(feed: list[dict], week_start: date, cal: dict | None = None) -> dict[str, list]:
    """Rozdiel medzi týždenným exportom ForexFactory a kalendárom stratégie.

    `feed` = udalosti s `title`, `country` a `ts` (UTC epoch) — tvar `ff_calendar.feed.parse_feed`; berú sa len
    USD udalosti v týždni `week_start` … +6 dní (New York). Vráti:

    * `add` — `[(deň, "HH:MM", typ)]`: správa je vo feede, v kalendári nie (alebo je v iný čas) → `newsAdd`;
    * `skip` — `[(deň, typ)]`: kalendár ju má inde, než je tento týždeň vo feede (presunutá) → `newsSkip`;
    * `missing` — `[(deň, typ)]`: kalendár ju má, feed tento týždeň typ nemá vôbec. **Len na oznámenie**: môže
      byť zrušená (shutdown), ale aj názov, ktorý nepoznáme — sama od seba sa preto nevynechá;
    * `record` / `unrecord` — dni, ktoré patria do `calendar.json` (správa v bežnom čase typu) a ktoré z neho von.
    """
    events = (cal or load())["events"]
    days = {date.fromordinal(week_start.toordinal() + i) for i in range(7)}
    seen: dict[str, dict[date, str]] = {}
    for e in feed:
        if str(e.get("country") or "").upper() != "USD":
            continue
        typ = ff_type(str(e.get("title") or ""))
        if typ is None or typ not in events:
            continue
        local = datetime.fromtimestamp(float(e["ts"]), tz=NY)
        if local.date() not in days or not FF_HOURS[0] <= local.hour < FF_HOURS[1]:
            continue
        hhmm = f"{local.hour:02d}:{local.minute:02d}"
        byday = seen.setdefault(typ, {})
        byday[local.date()] = min(hhmm, byday.get(local.date(), hhmm))
    out: dict[str, list] = {"add": [], "skip": [], "missing": [], "record": [], "unrecord": []}
    for typ, ev in events.items():
        planned = {d for d in (date.fromisoformat(x) for x in ev["dates"]) if d in days}
        real = seen.get(typ, {})
        for day, hhmm in sorted(real.items()):
            if hhmm != ev["time_et"]:
                out["add"].append((day, hhmm, typ))
                if day in planned:
                    out["skip"].append((day, typ))      # ten istý deň, iný čas: bežný čas von, skutočný dnu
            elif day not in planned:
                out["add"].append((day, hhmm, typ))
                out["record"].append((day, typ))
        for day in sorted(planned - set(real)):
            if real:
                out["skip"].append((day, typ))          # typ je tento týždeň inde → presunutá
                out["unrecord"].append((day, typ))
            else:
                out["missing"].append((day, typ))
    return {k: sorted(v) for k, v in out.items()}


def fmt_add(items: list[tuple[date, str, str]]) -> str:
    """`newsAdd` z `[(deň, "HH:MM", typ)]`."""
    return "; ".join(f"{d.isoformat()} {hhmm} {typ}" for d, hhmm, typ in sorted(set(items)))


def fmt_skip(items: list[tuple[date, str]]) -> str:
    """`newsSkip` z `[(deň, typ)]`."""
    return "; ".join(f"{d.isoformat()} {typ}" for d, typ in sorted(set(items)))


def with_changes(cal: dict, record: list[tuple[date, str]], unrecord: list[tuple[date, str]] = ()) -> tuple[dict, int]:
    """Kópia kalendára s pridanými (`record`) a odobratými (`unrecord`) dňami a prepočítaným `coverage.to`.
    Vráti (kalendár, koľko dní sa naozaj zmenilo)."""
    out = json.loads(json.dumps(cal))
    changed = 0
    for day, typ in record:
        dates = out["events"][typ]["dates"]
        if day.isoformat() not in dates:
            dates.append(day.isoformat())
            changed += 1
    for day, typ in unrecord:
        dates = out["events"][typ]["dates"]
        if day.isoformat() in dates:
            dates.remove(day.isoformat())
            changed += 1
    for typ, ev in out["events"].items():
        ev["dates"] = sorted(set(ev["dates"]))
        if ev["dates"]:
            out["coverage"]["to"][typ] = ev["dates"][-1]
    return out, changed


def dumps(cal: dict) -> str:
    """Text `calendar.json` v tvare, v akom je v repozitári."""
    return json.dumps(cal, ensure_ascii=False, indent=1) + "\n"


def csharp_source(cal: dict | None = None) -> str:
    """Zoznam pre C# jadro: (rok, mesiac, deň, hodina, minúta, typ) v čase New York."""
    cal = (cal or load())["events"]
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
    elif "--check" in sys.argv:
        # koniec pokrytia: nenulový návratový kód, keď niektorému typu končí kalendár do N dní (predvolene 45)
        i = sys.argv.index("--check")
        days = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 45
        today = datetime.now(NY).date()
        gaps = coverage_gaps(today, days)
        for typ, last in gaps:
            left = last.toordinal() - today.toordinal()
            print(f"{typ}: kalendár končí {last}" + (f" (o {left} dní)" if left >= 0 else f" (pred {-left} dňami — správy sa NEOBCHODUJÚ)"))
        if not gaps:
            print(f"kalendár pokrýva všetky typy aspoň {days} dní dopredu")
        sys.exit(1 if gaps else 0)
    else:
        ev = events_utc()
        print(len(ev), "udalostí;", datetime.fromtimestamp(ev[0][0] / 1000, tz=NY), "…",
              datetime.fromtimestamp(ev[-1][0] / 1000, tz=NY))
