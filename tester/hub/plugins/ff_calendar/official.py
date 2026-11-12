"""Oficiálne rozvrhy úradov → termíny kalendára stratégie SPRÁVY dopredu.

Týždenný export ForexFactory (`sync.py`) vidí len aktuálny týždeň, takže koniec pokrytia `calendar.json` sám
neposunie — typ, ktorému termíny dôjdu, by stratégia naživo ticho prestala obchodovať a EA to pri štarte hlási
(`IPreflight`, 45 dní vopred). Úrady pritom rozvrh na ďalší rok zverejňujú samy; tu sa z nich berie:

| typ | zdroj |
|---|---|
| CPI, NFP, PPI, JOLTS | rozvrh vydania BLS (`bls.gov/schedule/news_release/<vydanie>.htm`, ~13 mesiacov dopredu) |
| GDP, PCE | BEA `release_dates.json` (GDP; Personal Income and Outlays) |
| FOMC | `federalreserve.gov/monetarypolicy/fomccalendars.htm` — rozhodnutie je druhý deň zasadnutia, 14:00 |
| FOMC_MIN | FOMC + 21 dní |
| ISM_M, ISM_S, CLAIMS | pravidlo so sviatkami burzy (`tester.calendar.us_holidays`): 1. a 3. pracovný deň mesiaca, štvrtok (pri sviatku deň pred) — sedí na celú históriu kalendára od 2021 |
| RETAIL | **žiadny**: Census automatizovaných klientov odmieta (403). Ide len týždenne z ForexFactory; keď koniec príde bez doplnenia, plugin to hlási ako `problem` |

Tu je len sťahovanie a rozbor; čo s termínmi (nasadenia, repozitár) robí `CalendarSync.extend`.
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable

from .feed import NY

__all__ = ["SOURCES", "fetch_text", "parse_bls", "parse_bea", "parse_fomc", "rule_dates", "official_dates"]

UA = "TradeBot-hub/1 (ff_calendar)"
BLS_URL = "https://www.bls.gov/schedule/news_release/{}.htm"
BLS_PAGES = {"CPI": "cpi", "NFP": "empsit", "PPI": "ppi", "JOLTS": "jolts"}
BEA_URL = "https://apps.bea.gov/API/signup/release_dates.json"
BEA_NAMES = {"GDP": "Gross Domestic Product", "PCE": "Personal Income and Outlays"}
FED_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_TIME = "14:00"
#: Zápisnica FOMC vychádza tri týždne po rozhodnutí (ako v `calendar.json`).
MINUTES_AFTER = 21
#: Čas vydania typov počítaných pravidlom (ako `time_et` v `calendar.json`).
RULE_TIME = {"ISM_M": "10:00", "ISM_S": "10:00", "CLAIMS": "08:30"}

#: Typ → odkiaľ sa berie (pre `status` a CLI). Typ, ktorý tu nie je, oficiálny zdroj nemá.
SOURCES: dict[str, str] = {
    **{t: f"BLS {p}.htm" for t, p in BLS_PAGES.items()},
    **{t: f"BEA {n}" for t, n in BEA_NAMES.items()},
    "FOMC": "federalreserve.gov", "FOMC_MIN": "FOMC + 21 dní",
    "ISM_M": "pravidlo: 1. pracovný deň", "ISM_S": "pravidlo: 3. pracovný deň", "CLAIMS": "pravidlo: štvrtok",
}

_MESIACE = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def fetch_text(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - pevné adresy úradov
        return resp.read().decode("utf-8", errors="replace")


def _mesiac(text: str) -> int:
    try:
        return _MESIACE[text.strip().lower()[:3]]
    except KeyError:
        raise ValueError(f"neznámy mesiac {text!r}") from None


# --------------------------------------------------------------------------- #
# rozbor
# --------------------------------------------------------------------------- #

_BLS_ROW = re.compile(r"<td>\s*([A-Za-z]{3,9})\.?\s+(\d{1,2}),\s*(\d{4})\s*</td>\s*"
                      r"<td>\s*(\d{1,2}):(\d{2})\s*([AP])\.?M\.?\s*</td>", re.I)


def parse_bls(page: str) -> list[tuple[date, str]]:
    """Rozvrh vydania BLS (tabuľka „Reference Month | Release Date | Release Time“) → [(deň, "HH:MM" New York)]."""
    out = set()
    for mes, den, rok, hh, mm, ampm in _BLS_ROW.findall(page or ""):
        h = int(hh) % 12 + (12 if ampm.upper() == "P" else 0)
        out.add((date(int(rok), _mesiac(mes), int(den)), f"{h:02d}:{mm}"))
    return sorted(out)


def parse_bea(raw: Any, name: str) -> list[tuple[date, str]]:
    """BEA `release_dates.json` (`{vydanie: {"release_dates": [ISO s posunom]}}`) → [(deň, "HH:MM" New York)]."""
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    out = set()
    for x in ((data or {}).get(name) or {}).get("release_dates") or []:
        dt = datetime.fromisoformat(str(x))
        if dt.tzinfo is None:
            continue
        ny = dt.astimezone(NY)
        out.add((ny.date(), f"{ny.hour:02d}:{ny.minute:02d}"))
    return sorted(out)


_FED_PANEL = re.compile(r"(\d{4}) FOMC Meetings")
_FED_ROW = re.compile(r"fomc-meeting__month[^>]*>\s*(?:<strong>)?\s*([A-Za-z/]+)\s*(?:</strong>)?\s*</div>\s*"
                      r"<div[^>]*fomc-meeting__date[^>]*>\s*([^<]*)<", re.I)
_FED_DNI = re.compile(r"^(\d{1,2})\s*-\s*(\d{1,2})\b")


def parse_fomc(page: str) -> list[tuple[date, str]]:
    """Stránka kalendára FOMC → [(deň rozhodnutia, "14:00")]. Rozhodnutie je druhý deň zasadnutia („27-28“ → 28.,
    „Apr/May 30-1“ → 1. mája); hlasovanie písomne či mimoriadne zasadnutie (bez rozsahu dní) sa preskočí."""
    out = set()
    casti = _FED_PANEL.split(page or "")
    for i in range(1, len(casti) - 1, 2):
        rok = int(casti[i])
        for mesiace, dni in _FED_ROW.findall(casti[i + 1]):
            m = _FED_DNI.match(dni.strip())
            if not m:
                continue
            mes = _mesiac(mesiace.split("/")[-1])
            out.add((date(rok, mes, int(m.group(2))), FOMC_TIME))
    return sorted(out)


# --------------------------------------------------------------------------- #
# pravidlá
# --------------------------------------------------------------------------- #

def _pracovny(d: date) -> bool:
    from tester.calendar import us_holidays

    return d.weekday() < 5 and d not in us_holidays(d.year)


def _nty_pracovny(rok: int, mes: int, n: int) -> date:
    d, k = date(rok, mes, 1), 0
    while True:
        if _pracovny(d):
            k += 1
            if k == n:
                return d
        d += timedelta(days=1)


def rule_dates(typ: str, rok: int) -> list[date]:
    """Termíny typu, ktorý má pravidlo (ISM_M, ISM_S, CLAIMS), na celý rok."""
    if typ == "ISM_M":
        return [_nty_pracovny(rok, m, 1) for m in range(1, 13)]
    if typ == "ISM_S":
        return [_nty_pracovny(rok, m, 3) for m in range(1, 13)]
    if typ == "CLAIMS":
        d = date(rok, 1, 1)
        d += timedelta(days=(3 - d.weekday()) % 7)
        out = []
        while d.year == rok:
            x = d
            while not _pracovny(x):
                x -= timedelta(days=1)
            out.append(x)
            d += timedelta(weeks=1)
        return out
    raise KeyError(typ)


# --------------------------------------------------------------------------- #
# zber
# --------------------------------------------------------------------------- #

def official_dates(types: Iterable[str], fetch: Callable[[str], str] = fetch_text, *, years: Iterable[int] = (),
                   known_fomc: Iterable[date] = ()) -> tuple[dict[str, list[tuple[date, str]]], dict[str, str]]:
    """Termíny vybraných typov z oficiálnych zdrojov: `({typ: [(deň, "HH:MM")]}, {typ: chyba})`.

    Každá adresa sa stiahne najviac raz. `years` = roky pre typy s pravidlom; `known_fomc` = rozhodnutia FOMC, ktoré
    už kalendár má (zápisnica sa počíta aj z nich). Typ bez zdroja (RETAIL) dostane chybu „bez oficiálneho zdroja“."""
    types = list(dict.fromkeys(types))
    found: dict[str, list[tuple[date, str]]] = {}
    errors: dict[str, str] = {}
    cache: dict[str, Any] = {}

    def get(url: str) -> Any:
        if url not in cache:
            try:
                cache[url] = fetch(url)
            except Exception as exc:  # noqa: BLE001 - jeden zdroj nesmie zhodiť ostatné
                cache[url] = exc
        if isinstance(cache[url], Exception):
            raise cache[url]
        return cache[url]

    for typ in types:
        try:
            if typ in BLS_PAGES:
                found[typ] = parse_bls(get(BLS_URL.format(BLS_PAGES[typ])))
            elif typ in BEA_NAMES:
                found[typ] = parse_bea(get(BEA_URL), BEA_NAMES[typ])
            elif typ in ("FOMC", "FOMC_MIN"):
                fomc = parse_fomc(get(FED_URL))
                if typ == "FOMC":
                    found[typ] = fomc
                else:
                    # známe rozhodnutia len pred rozsahom stránky — v ňom platí stránka (presunuté zasadnutie)
                    od = min((d for d, _ in fomc), default=None)
                    rozhodnutia = {d for d, _ in fomc} | {d for d in known_fomc if od is None or d < od}
                    found[typ] = sorted((d + timedelta(days=MINUTES_AFTER), FOMC_TIME) for d in rozhodnutia)
            elif typ in RULE_TIME:
                found[typ] = [(d, RULE_TIME[typ]) for rok in years for d in rule_dates(typ, rok)]
            else:
                errors[typ] = "bez oficiálneho zdroja (len týždenne z ForexFactory)"
                continue
        except Exception as exc:  # noqa: BLE001
            errors[typ] = f"{type(exc).__name__}: {exc}"
            continue
        if not found[typ]:
            errors[typ] = "zdroj nedal žiadny termín (zmenila sa stránka?)"
    return found, errors
