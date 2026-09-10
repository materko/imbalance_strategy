"""Kalendár: sviatky búrz a makro udalosti — čo sa dá poznať **pred** vstupom.

### Načo to je
Dva dni v roku sa trh chová inak a nie je to náhoda: v deň rozhodnutia Fedu alebo
inflácie sa volatilita zbalí do niekoľkých minút, a keď je Wall Street zavretá, likvidita
zmizne aj tam, kde sa obchoduje ďalej (krypto, CFD). Obchod v takom dni je iná vec než
obchod v stredu bez správ — a keďže sa dátum vie **dopredu**, je to legitímny filter, nie
pohľad dozadu.

### Odkiaľ sú dáta
Dve rôzne veci, dva rôzne zdroje:

* **Sviatky búrz** sa počítajú **pravidlom**, lebo pravidlo majú: „tretí pondelok januára",
  „posledný pondelok mája", Veľký piatok podľa Veľkej noci. Nič sa nesťahuje a platí to
  pre ktorýkoľvek rok dopredu aj dozadu.
* **Makro udalosti** pravidlo nemajú — NFP nie je vždy prvý piatok a CPI nie je vždy 13.
  Dátumy sú preto **odpísané** z federalreserve.gov a bls.gov do
  [calendar_us.json](calendar_us.json), aj so zdrojom a dátumom odpísania.

### Prečo je dôležité `coverage`
Zoznam udalostí je úplný len pre roky, ktoré sú v ňom. Obchod mimo toho rozsahu
**nedostane nič** — nie „žiadna udalosť". Keby dostal, mlčanie kalendára by sa čítalo ako
pokojný deň a analytika by porovnávala „deň s CPI" proti zmesi pokojných dní a rokov, ku
ktorým dáta nemáme.

### Čo tu zámerne nie je
Európske makro (ECB, nemecké ZEW), lebo naše trhy sú americké a krypto; a intradenný
rozpad („päť minút po vyhlásení"), lebo na to treba tikové dáta. Sviatky sú v dennom
rozlíšení: skorý záver (Štedrý deň, deň po Vďakyvzdaní) je označený ako `polovičný deň`.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

__all__ = ["CALENDAR_FILE", "KEYS", "events", "coverage", "us_holidays", "eu_holidays",
           "annotate", "easter"]

CALENDAR_FILE = Path(__file__).with_name("calendar_us.json")

#: Kľúče, ktoré `annotate` dopĺňa do obchodov.
KEYS = ("_cal_event", "_cal_session")


def easter(year: int) -> date:
    """Veľkonočná nedeľa (gregoriánsky algoritmus) — od nej sú Veľký piatok aj pondelok."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mesiac = (h + l - 7 * m + 114) // 31
    den = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, mesiac, den)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """`n`-tý `weekday` (0 = pondelok) v mesiaci; `n = -1` je posledný."""
    if n > 0:
        prvy = date(year, month, 1)
        posun = (weekday - prvy.weekday()) % 7
        return prvy + timedelta(days=posun + 7 * (n - 1))
    posledny = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return posledny - timedelta(days=(posledny.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    """Sviatok cez víkend sa na burze drží v piatok alebo v pondelok."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


@lru_cache(maxsize=32)
def us_holidays(year: int) -> dict[date, str]:
    """Sviatky burzy v USA (NYSE/Nasdaq) a dni so skorým záverom.

    Sú to pravidlá, nie tabuľka — platia dopredu aj dozadu. Juneteenth je sviatkom burzy
    až od 2022, predtým sa obchodovalo.
    """
    velka_noc = easter(year)
    out: dict[date, str] = {
        _observed(date(year, 1, 1)): "Nový rok",
        _nth_weekday(year, 1, 0, 3): "Deň M. L. Kinga",
        _nth_weekday(year, 2, 0, 3): "Deň prezidentov",
        velka_noc - timedelta(days=2): "Veľký piatok",
        _nth_weekday(year, 5, 0, -1): "Deň pamiatky",
        _observed(date(year, 7, 4)): "Deň nezávislosti",
        _nth_weekday(year, 9, 0, 1): "Sviatok práce",
        _nth_weekday(year, 11, 3, 4): "Vďakyvzdanie",
        _observed(date(year, 12, 25)): "Vianoce",
    }
    if year >= 2022:
        out[_observed(date(year, 6, 19))] = "Juneteenth"
    # Nový rok, ktorý padne na sobotu, sa drží už 31. decembra — teda v TOMTO roku,
    # hoci je to sviatok toho nasledujúceho.
    if date(year + 1, 1, 1).weekday() == 5:
        out[date(year, 12, 31)] = "Nový rok (drží sa vopred)"
    return out


@lru_cache(maxsize=32)
def us_half_days(year: int) -> dict[date, str]:
    """Dni, keď burza v USA zatvára o 13:00 — likvidita je popoludní prakticky preč."""
    out: dict[date, str] = {}
    piatok = _nth_weekday(year, 11, 3, 4) + timedelta(days=1)
    out[piatok] = "deň po Vďakyvzdaní"
    stedry = date(year, 12, 24)
    if stedry.weekday() < 5:
        out[stedry] = "Štedrý deň"
    pred_nezavislostou = date(year, 7, 3)
    if pred_nezavislostou.weekday() < 5 and date(year, 7, 4).weekday() < 5:
        out[pred_nezavislostou] = "deň pred Dňom nezávislosti"
    return out


@lru_cache(maxsize=32)
def eu_holidays(year: int) -> dict[date, str]:
    """Sviatky európskych búrz (Xetra, Euronext) — spoločný prienik, nie každá zvlášť."""
    velka_noc = easter(year)
    return {
        date(year, 1, 1): "Nový rok",
        velka_noc - timedelta(days=2): "Veľký piatok",
        velka_noc + timedelta(days=1): "Veľkonočný pondelok",
        date(year, 5, 1): "Sviatok práce",
        date(year, 12, 25): "Vianoce",
        date(year, 12, 26): "Druhý sviatok vianočný",
    }


@lru_cache(maxsize=1)
def _raw() -> dict[str, Any]:
    if not CALENDAR_FILE.exists():
        return {}
    return json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))


def coverage() -> tuple[date, date] | None:
    """Odkiaľ dokiaľ je zoznam makro udalostí úplný. `None`, keď kalendár chýba."""
    c = (_raw().get("coverage") or {})
    try:
        return (date.fromisoformat(c["from"]), date.fromisoformat(c["to"]))
    except (KeyError, ValueError):
        return None


@lru_cache(maxsize=1)
def events() -> dict[date, tuple[str, str]]:
    """`dátum -> (kľúč udalosti, čas v New Yorku)`. Deň s dvoma udalosťami dostane obe."""
    out: dict[date, tuple[str, str]] = {}
    for kluc, blok in (_raw().get("events") or {}).items():
        for d in blok.get("dates") or ():
            try:
                den = date.fromisoformat(d)
            except ValueError:
                continue
            stary = out.get(den)
            # Dva výpisy v jeden deň sa nezlučujú do „nejaká udalosť" — je rozdiel, či
            # padne CPI, alebo CPI aj Fed naraz.
            out[den] = ((stary[0] + "+" + kluc, stary[1]) if stary
                        else (kluc, blok.get("time_et") or "08:30"))
    return out


def event_titles() -> dict[str, str]:
    return {k: (v.get("title") or k) for k, v in (_raw().get("events") or {}).items()}


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        out = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return out if out.tzinfo else out.replace(tzinfo=timezone.utc)


def annotate(trades: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Doplní obchodom deň podľa kalendára. Vracia ten istý zoznam (mení ho na mieste).

    Deň sa berie **v New Yorku**, nie v UTC: vyhlásenie o 08:30 ET je v lete 12:30 UTC
    a v zime 13:30 UTC, takže podľa UTC by časť obchodov padla do nesprávneho dňa.
    """
    from zoneinfo import ZoneInfo

    ny = ZoneInfo("America/New_York")
    rozsah = coverage()
    udalosti = events()
    out = list(trades)

    for t in out:
        cas = _dt(t.get("open_date"))
        if cas is None:
            continue
        miestny = cas.astimezone(ny)
        den = miestny.date()

        # -- seansa: sviatky sú pravidlo, platia pre ktorýkoľvek rok ----------- #
        sviatky = us_holidays(den.year)
        polovicne = us_half_days(den.year)
        if den in sviatky:
            t["_cal_session"] = f"sviatok v USA ({sviatky[den]})"
        elif den in polovicne:
            t["_cal_session"] = f"polovičný deň ({polovicne[den]})"
        elif (den + timedelta(days=1)) in us_holidays((den + timedelta(days=1)).year):
            t["_cal_session"] = "deň pred sviatkom"
        elif (den - timedelta(days=1)) in us_holidays((den - timedelta(days=1)).year):
            t["_cal_session"] = "deň po sviatku"
        else:
            t["_cal_session"] = "bežný deň"

        # -- makro: mimo pokrytia sa nedopĺňa NIČ ------------------------------ #
        if rozsah is None or not (rozsah[0] <= den <= rozsah[1]):
            continue
        udalost = udalosti.get(den)
        if udalost is None:
            t["_cal_event"] = "žiadna"
            t["_cal_event_window"] = "bez udalosti"
            continue
        kluc, cas_et = udalost
        t["_cal_event"] = kluc
        try:
            h, m = (int(x) for x in cas_et.split(":"))
        except ValueError:
            h, m = 8, 30
        vyhlasenie = miestny.replace(hour=h, minute=m, second=0, microsecond=0)
        # Rozdiel medzi „vstúpil pred vyhlásením" a „po ňom" je celý rozdiel medzi
        # hazardom a obchodovaním na už známej informácii.
        t["_cal_event_window"] = "pred vyhlásením" if miestny < vyhlasenie else "po vyhlásení"
    return out
