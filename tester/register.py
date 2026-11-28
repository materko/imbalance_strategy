"""Register pokusov, rozpočet, trezory a zámky podľa SMERNICE V2 (§1, §2, kroky 6 a 8; zadanie U6 a U7).

Prečo: DSR, haircut aj prah t na trezore stoja na tom, **koľko sa toho skúšalo**. Doteraz sa to číslo opisovalo
ručne z rannej tabuľky a obdobia na kontrolu sa pri ladení používali tiež. Tento modul to drží na jednom mieste
v gite (`tester/register/`, cesta v `tradebot.core.paths.REGISTER_DIR`):

    <hypotéza>.md      hlavička — commit PRED prvým behom (dôvod edge, zdroj, štúdie, mriežka, trhy, L, brány…)
    <hypotéza>.jsonl   pokusy, len pridávanie: čas, kľúč, trh, TF, parametre, obdobie, zdroj, git hash kódu, PF,
                       obchody a mesačný PnL
    vaults.json        trezory: počiatočné k trhu (z histórie behov a štúdií), kto a kedy trezor otvoril, zámok WF

Čo sa tu vynucuje (výnimka `RegisterError` = beh sa nespustí):

- **Hľadanie len na L trhu.** Mriežka, hyperopt, ručný beh, plató aj WF nesmú siahnuť na trezor B, rok A ani C
  (`check_search`). Trh sa určí z páru; pár mimo §1 (CFD, akcie, ETH) obmedzenie nemá.
- **Hlavička commitnutá pred prvým pokusom** a so všetkými povinnými časťami.
- **Rozpočet ≤ 300 konfigurácií** na hypotézu (všetky kópie a trhy, aj susedia v plató; WF, štúdia ani legacy sa
  do 300 nerátajú), **≤ 5 voľných parametrov** (bez tých, ktoré hlavička vymenuje ako pevné) a **≤ 10 nových
  hypotéz za štvrťrok na jeden trezor**.
- **Trezor sa otvára raz na hypotézu** (druhé `open_vault` pre tú istú hypotézu, trh a trezor sa odmietne) a len
  keď je v `vaults.json` spočítané počiatočné k. Každé otvorenie pridá k trezoru +1 za každý kľúč (kópiu rodiny).
- **WF raz na hypotézu** (`lock_wf`).

N pre DSR = počet konfigurácií v registri bez WF (+ odhad legacy a behy štúdie), N_eff = zhluky mesačného PnL
pri |ρ| > 0,5 s podlahou N/50. t_req = Φ⁻¹(1 − 0,025 / k) s úpravami zo smernice.

Príklady:

    python -m tester.register new orb-pondelok              # šablóna hlavičky (vyplniť a commitnúť)
    python -m tester.register check orb-pondelok            # je hlavička v poriadku a commitnutá?
    python -m tester.register status [orb-pondelok]         # N, N_eff, rozpočet, voľné parametre, trezory
    python -m tester.register periods MNQ                   # L, trezor B, rok A, okná L po rokoch
    python -m tester.register k0 [--write]                  # počiatočné k trezorov z histórie behov a štúdií
    python -m tester.register open orb-pondelok MNQ B --keys orb,orbnet   # otvorí trezor (zámok)
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable, Sequence

from tradebot.core.paths import ARCHIVE_DIR, REGISTER_DIR, REPO, RUNS_DIR

__all__ = [
    "RegisterError", "Market", "MARKETS", "YEAR_A", "STUDIES", "SOURCES", "BUDGET", "MAX_FREE_PARAMS",
    "MAX_NEW_PER_QUARTER", "HEADER_SECTIONS",
    "market_of", "market_of_instrument", "check_windows", "default_windows", "periods", "zones", "l_timerange", "l_windows", "check_search",
    "header_path", "header_problems", "header_template", "require_header", "header_markets", "header_fixed",
    "attempts", "append", "config_id", "n_trials", "n_eff", "free_params", "status",
    "load_vaults", "save_vaults", "k_of", "t_req", "open_vault", "lock_wf", "initial_k",
]


class RegisterError(RuntimeError):
    """Pokus alebo otvorenie trezoru, ktoré smernica nedovolí."""


# -- §1 rozdelenie dát ------------------------------------------------------- #

@dataclass(frozen=True)
class Market:
    """Pevné rozdelenie jedného trhu (§1). Dátumy vrátane oboch koncov, ISO."""

    name: str
    L: tuple[str, str]
    B: tuple[str, str]
    #: walk-forward: učenie a test v mesiacoch, posun = test
    wf: tuple[int, int]


#: Rok A je na všetkých trhoch spálený (len negatívna kontrola); C = nové dáta od commitu hraníc (`c_from`
#: vo `vaults.json`, kým tam nie je, trezor C sa neotvorí).
YEAR_A = ("2025-09-04", "2026-09-03")

MARKETS: dict[str, Market] = {m.name: m for m in (
    Market("ES", ("2015-01-01", "2025-09-03"), ("2010-06-06", "2014-12-31"), (24, 6)),
    Market("6E", ("2016-01-03", "2021-09-30"), ("2021-10-01", "2025-09-03"), (24, 6)),
    Market("MNQ", ("2019-05-05", "2022-09-30"), ("2022-10-01", "2025-09-03"), (18, 6)),
    Market("MYM", ("2019-06-02", "2022-09-30"), ("2022-10-01", "2025-09-03"), (18, 6)),
    Market("BTC", ("2019-09-08", "2022-09-30"), ("2022-10-01", "2025-09-03"), (18, 6)),
    Market("MGC", ("2023-01-01", "2025-09-03"), ("2020-01-01", "2022-12-31"), (18, 6)),
)}

#: pár (ako ho píše `--pair`) -> trh §1. BTC spot je ten istý podklad ako perp, preto tiež BTC (prísnejšie).
_PAIRS = {
    "ES/USD": "ES", "MES/USD": "ES", "6E/USD": "6E", "MNQ/USD": "MNQ", "MYM/USD": "MYM", "MGC/USD": "MGC",
    "BTC/USDT:USDT": "BTC", "BTC/USDT": "BTC",
}

#: Štúdie a prieskumy z §1 (iCloud), ktoré videli obdobia trhov: (meno, trh, od, do). Do k trezoru sa ráta
#: každá ako jedna hypotéza na každom trezore, ktorého obdobie videla. Triedenie starých rokov (26. 11.) tu nie
#: je — jeho behy sú v histórii behov a rátajú sa ako kľúče rodín.
STUDIES: tuple[tuple[str, str, str, str], ...] = (
    ("SP500-ES", "ES", "2019-01-01", "2026-09-03"),
    ("EUR-PRIESKUM", "6E", "2016-01-01", "2026-09-03"),
    ("NASDAQ-STUDIUM", "MNQ", "2019-01-01", "2026-09-03"),
    ("prieskum nocpon", "MNQ", "2019-01-01", "2026-09-03"),
    ("ZLATO-PRIESKUM", "MGC", "2011-01-01", "2026-09-30"),
    ("BTC-PRIESKUM", "BTC", "2019-09-01", "2026-09-30"),
    ("KLZAKY-STUDIA", "ES", "2016-01-01", "2026-09-03"),
    ("KLZAKY-STUDIA", "MGC", "2016-01-01", "2026-09-03"),
    ("KLZAKY-STUDIA", "MNQ", "2019-01-01", "2026-09-03"),
    ("KLZAKY-STUDIA", "MYM", "2019-01-01", "2026-09-03"),
    ("KLZAKY-STUDIA", "BTC", "2019-01-01", "2026-09-03"),
)


#: Referenčné okná ladenia (`tester/hyperopt.py`, `glsearch`, `checkup`) 10/2021–9/2026 videli na všetkých trhoch
#: všetky legacy rodiny (§1) -> trezor, ktorý do nich zasahuje, dostane do k všetky kľúče registra (prísny horný odhad).
REFERENCE_SPAN = ("2021-10-01", "2026-09-03")

#: Triedenie starých rokov (26. 11. 2026, 11 rodín): trh -> (od, do). Jeho behy bežali na Mac mini a v histórii
#: nemusia byť všetky, preto sa do k ráta najmenej týchto 11 rodín.
TRIEDENIE = {"ES": ("2010-07-01", "2021-09-30"), "MNQ": ("2019-01-01", "2021-09-30"),
             "MYM": ("2019-01-01", "2021-09-30"), "MGC": ("2020-01-01", "2021-09-30")}
TRIEDENIE_FAMILIES = 11


def _d(s: str) -> date:
    s = s.strip()
    return date.fromisoformat(s) if "-" in s else datetime.strptime(s, "%Y%m%d").date()


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def market_of(pair: str | None) -> str | None:
    """Trh §1 pre pár, inak None (CFD, akcie, ETH — pre ne smernica rozdelenie nemá)."""
    if not pair:
        return None
    p = pair.strip().upper()
    if p in MARKETS:
        return p
    return _PAIRS.get(p)


#: kľúč nástroja natívneho hyperoptu (`tester.native_hyperopt.INSTRUMENTS`) -> trh §1
_INSTRUMENTS = {"mnq": "MNQ", "mnq_databento": "MNQ", "mym_databento": "MYM", "es_databento": "ES",
                "mgc_databento": "MGC", "6e_databento": "6E", "btcusdt_binance": "BTC", "btcusdt_binance_spot": "BTC"}


def market_of_instrument(key: str | None) -> str | None:
    return _INSTRUMENTS.get((key or "").strip().lower())


def periods(market: str, vaults: dict[str, Any] | None = None) -> dict[str, tuple[date, date] | None]:
    """L, B, A a C trhu ako (od, do) vrátane. C je None, kým nie je vo `vaults.json` `c_from`."""
    m = MARKETS[market]
    c_from = ((vaults or {}).get("markets", {}).get(market) or {}).get("c_from")
    return {"L": (_d(m.L[0]), _d(m.L[1])), "B": (_d(m.B[0]), _d(m.B[1])), "A": (_d(YEAR_A[0]), _d(YEAR_A[1])),
            "C": (_d(c_from), date(9999, 12, 31)) if c_from else None}


def _span(timerange: str) -> tuple[date, date]:
    """Freqtrade `YYYYMMDD-YYYYMMDD` (koniec bez) -> (od, do) vrátane."""
    a, _, b = timerange.strip().partition("-")
    if not a or not b:
        raise RegisterError(f"obdobie {timerange!r} nemá tvar YYYYMMDD-YYYYMMDD")
    return _d(a), _d(b) - timedelta(days=1)


def zones(timerange: str, market: str) -> list[str]:
    """Ktorých častí rozdelenia sa obdobie dotkne: L, B, A, C (všetko po roku A) a `mimo` (pred dátami §1)."""
    od, do = _span(timerange)
    p = periods(market)
    out = [z for z in ("L", "B", "A") if od <= p[z][1] and do >= p[z][0]]   # type: ignore[index]
    if do > p["A"][1]:                                                         # type: ignore[index]
        out.append("C")
    first = min(p["L"][0], p["B"][0])                                          # type: ignore[index]
    if od < first:
        out.append("mimo")
    return out


def l_timerange(market: str) -> str:
    m = MARKETS[market]
    return f"{_ymd(_d(m.L[0]))}-{_ymd(_d(m.L[1]) + timedelta(days=1))}"


def l_windows(market: str) -> list[str]:
    """L po rokoch od začiatku L (posledné okno kratšie) — náhrada piatich referenčných okien pre `checkup`."""
    m = MARKETS[market]
    od, koniec = _d(m.L[0]), _d(m.L[1]) + timedelta(days=1)
    out = []
    while od < koniec:
        try:
            do = od.replace(year=od.year + 1)
        except ValueError:            # 29. 2.
            do = od.replace(year=od.year + 1, day=28)
        if (koniec - do).days < 120:   # zvyšok pod 4 mesiace pridať k poslednému roku
            do = koniec
        do = min(do, koniec)
        out.append(f"{_ymd(od)}-{_ymd(do)}")
        od = do
    return out


def check_search(timerange: str, pair: str | None, what: str = "hľadanie") -> None:
    """Hľadanie (mriežka, hyperopt, ručný pokus, plató, WF, checkup) smie len na L trhu (§2, U6.5)."""
    market = market_of(pair)
    if market is None:
        return
    z = zones(timerange, market)
    if z != ["L"]:
        bad = ", ".join(x for x in z if x != "L")
        raise RegisterError(f"{what} {timerange} na {market} siaha mimo L ({bad}). L {market} je {l_timerange(market)}; "
                            f"trezor sa púšťa len `--vault`, rok A je len kontrola (SMERNICA V2 §1)")


def check_windows(windows: Iterable[str], market: str | None, what: str = "hľadanie") -> None:
    """`check_search` pre každé okno; `market` je trh §1 (alebo None = bez obmedzenia)."""
    if market is None:
        return
    for w in windows:
        check_search(w, market, what)


def default_windows(market: str | None, fallback: Sequence[str]) -> list[str]:
    """Okná hľadania a analytiky: L trhu po rokoch, pre trh mimo §1 `fallback` (päť referenčných okien)."""
    return l_windows(market) if market else list(fallback)


# -- hlavička hypotézy ------------------------------------------------------- #

#: Povinné časti hlavičky (nadpisy `## …`); každá musí mať obsah. `## Pevné parametre` a `## Výnimka` sú voliteľné.
HEADER_SECTIONS = ("Dôvod edge", "Zdroj", "Štúdie a výskumy", "Mriežka", "Trhy", "Obdobie L", "Hranice brán",
                   "Typ vstupu a filter IBS + pin bar")

_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_PLACEHOLDER = re.compile(r"^\s*(…|\.\.\.|TODO|_\(.*\)_)\s*$", re.I)


def _name(hypothesis: str) -> str:
    if not _NAME.match(hypothesis or ""):
        raise RegisterError(f"meno hypotézy {hypothesis!r}: malé písmená, číslice, - a _")
    return hypothesis


def header_path(hypothesis: str, root: Path | None = None) -> Path:
    return Path(root or REGISTER_DIR) / f"{_name(hypothesis)}.md"


def _sections(text: str) -> dict[str, str]:
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def header_problems(text: str) -> list[str]:
    """Čo hlavičke chýba (prázdny zoznam = v poriadku)."""
    s = _sections(text)
    problems = []
    for name in HEADER_SECTIONS:
        body = s.get(name)
        if body is None:
            problems.append(f"chýba časť „## {name}“")
        elif not body or all(_PLACEHOLDER.match(x) or not x.strip() for x in body.splitlines()):
            problems.append(f"časť „## {name}“ je prázdna")
    if s.get("Trhy") and not _markets_in(s["Trhy"]):
        problems.append("v „## Trhy“ nie je žiadny trh (ES, 6E, MNQ, MYM, BTC, MGC alebo CFD symbol)")
    return problems


def _markets_in(text: str) -> list[str]:
    found = [m for m in MARKETS if re.search(rf"(?<![A-Za-z0-9]){re.escape(m)}(?![A-Za-z0-9])", text)]
    return found or re.findall(r"\b(US100\.cash|US500\.cash|XAUUSD|US30|EURUSD|BTCUSD|NAS100)\b", text)


def header_markets(hypothesis: str, root: Path | None = None) -> list[str]:
    text = header_path(hypothesis, root).read_text(encoding="utf-8")
    return _markets_in(_sections(text).get("Trhy", ""))


def header_fixed(hypothesis: str, root: Path | None = None) -> set[str]:
    """Parametre, ktoré hlavička vyberá vopred (typ vstupu, IBS, pin bar…) — do 5 voľných sa nerátajú."""
    p = header_path(hypothesis, root)
    if not p.exists():
        return set()
    body = _sections(p.read_text(encoding="utf-8")).get("Pevné parametre", "")
    return set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", body))


def header_template(hypothesis: str) -> str:
    return f"""# Hypotéza `{_name(hypothesis)}`

*Hlavička podľa SMERNICE V2 §2. Commitni ju **pred prvým behom**; zmena po prvom behu = nová hypotéza.*

## Dôvod edge
…

## Zdroj
…

## Štúdie a výskumy
…

## Mriežka
…

## Trhy
…

## Obdobie L
…

## Hranice brán
…

## Typ vstupu a filter IBS + pin bar
…

## Pevné parametre
Parametre vybrané vopred, ktoré sa neladia (do 5 voľných sa nerátajú), v `spätných apostrofoch`.

## Výnimka
Žiadna (napr. menej než 75 obchodov za rok: t_req + 0,5 a ≥ 150 obchodov v trezore).

## Iný režim
Meranie pred otvorením trezoru (ATR % štvrťrokov mimo IQR L alebo pokles > 15 %); bez merania najviac ⏳.
"""


def _committed(path: Path) -> bool:
    """Súbor je v gite a bez necommitnutých zmien."""
    try:
        rel = str(path.resolve().relative_to(REPO.resolve())).replace("\\", "/")
    except ValueError:
        return False
    try:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True).returncode == 0
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO, capture_output=True).returncode == 0
    except OSError:
        return False
    return tracked and clean


def require_header(hypothesis: str, root: Path | None = None, *, committed=_committed) -> Path:
    p = header_path(hypothesis, root)
    if not p.exists():
        raise RegisterError(f"hypotéza {hypothesis}: chýba hlavička {p} (python -m tester.register new {hypothesis})")
    problems = header_problems(p.read_text(encoding="utf-8"))
    if problems:
        raise RegisterError(f"hypotéza {hypothesis}: hlavička nie je hotová — " + "; ".join(problems))
    if not committed(p):
        raise RegisterError(f"hypotéza {hypothesis}: hlavička {p.name} nie je commitnutá (commit pred prvým behom)")
    return p


# -- pokusy ------------------------------------------------------------------ #

#: zdroj pokusu. Do rozpočtu 300 idú len BUDGET_SOURCES; do N pre DSR všetko okrem `wf`.
SOURCES = ("grid", "hyperopt", "manual", "study", "plateau", "wf", "legacy")
BUDGET_SOURCES = ("grid", "hyperopt", "manual", "plateau")
BUDGET = 300
MAX_FREE_PARAMS = 5
MAX_NEW_PER_QUARTER = 10


def _jsonl(hypothesis: str, root: Path | None) -> Path:
    return Path(root or REGISTER_DIR) / f"{_name(hypothesis)}.jsonl"


def attempts(hypothesis: str, root: Path | None = None) -> list[dict[str, Any]]:
    p = _jsonl(hypothesis, root)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def config_id(rec: dict[str, Any]) -> str:
    """Konfigurácia = kľúč, trh, TF a parametre (obdobie nie: to isté nastavenie na inom okne nie je nový pokus)."""
    ident = {"key": rec.get("key"), "market": rec.get("market"), "tf": rec.get("tf"), "params": rec.get("params") or {}}
    return hashlib.sha1(json.dumps(ident, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _configs(rows: Iterable[dict[str, Any]], sources: Sequence[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r.get("source") in sources:
            out.setdefault(config_id(r), r)
    return out


def n_trials(rows: Sequence[dict[str, Any]]) -> int:
    """N pre DSR: konfigurácie bez WF; legacy a štúdia prispejú odhadom `n` (počet ich behov)."""
    plain = _configs(rows, [s for s in SOURCES if s not in ("wf", "legacy", "study")])
    extra = sum(int(r.get("n") or 1) for r in rows if r.get("source") in ("legacy", "study"))
    return len(plain) + extra


def _corr(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def n_eff(rows: Sequence[dict[str, Any]], rho: float = 0.5) -> int:
    """Počet zhlukov mesačného PnL konfigurácií pri |ρ| > rho (hltavo, poradie registra), podlaha N/50."""
    n = n_trials(rows)
    if n == 0:
        return 0
    series: list[dict[str, float]] = []
    for r in _configs(rows, [s for s in SOURCES if s not in ("wf", "legacy", "study")]).values():
        m = {x["month"]: float(x["pnl"]) for x in (r.get("monthly") or []) if "month" in x}
        if m:
            series.append(m)
    reps: list[dict[str, float]] = []
    for s in series:
        for rep in reps:
            common = sorted(set(s) & set(rep))
            if len(common) >= 6 and abs(_corr([s[k] for k in common], [rep[k] for k in common])) > rho:
                break
        else:
            reps.append(s)
    bez_mesiacov = len(_configs(rows, [s for s in SOURCES if s not in ("wf", "legacy", "study")])) - len(series)
    # konfigurácia bez mesačného PnL sa nedá zhlukovať -> ráta sa sama (prísnejšie); legacy/štúdia len cez podlahu
    return max(len(reps) + bez_mesiacov, math.ceil(n / 50))


def free_params(rows: Sequence[dict[str, Any]], fixed: Iterable[str] = ()) -> list[str]:
    """Parametre, ktorých hodnota sa medzi pokusmi rozpočtu mení (+ `timeframe`, ak sa mení TF)."""
    fixed = set(fixed)
    vals: dict[str, set[str]] = {}
    tfs: set[str] = set()
    for r in rows:
        if r.get("source") not in BUDGET_SOURCES:
            continue
        tfs.add(str(r.get("tf")))
        for k, v in (r.get("params") or {}).items():
            vals.setdefault(k, set()).add(json.dumps(v, sort_keys=True, default=str))
    # parameter, ktorý časť pokusov vôbec nemá, sa tiež mení (default proti hodnote)
    for k in vals:
        if any(k not in (r.get("params") or {}) for r in rows if r.get("source") in BUDGET_SOURCES):
            vals[k].add("<default>")
    out = sorted(k for k, v in vals.items() if len(v) > 1 and k not in fixed)
    if len(tfs) > 1 and "timeframe" not in fixed:
        out.append("timeframe")
    return out


def _quarter(ts: str) -> str:
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def _first_time(rows: Sequence[dict[str, Any]]) -> str | None:
    t = [r["time"] for r in rows if r.get("time") and r.get("source") not in ("legacy",)]
    return min(t) if t else None


def _hypotheses(root: Path | None) -> list[str]:
    d = Path(root or REGISTER_DIR)
    return sorted(p.stem for p in d.glob("*.jsonl")) if d.exists() else []


def _new_in_quarter(market: str, quarter: str, root: Path | None, skip: str) -> list[str]:
    out = []
    for h in _hypotheses(root):
        if h == skip:
            continue
        rows = attempts(h, root)
        if any(r.get("source") == "legacy" for r in rows):
            continue
        first = _first_time(rows)
        if first and _quarter(first) == quarter and any(r.get("market") == market for r in rows):
            out.append(h)
    return out


def _git_hash(key: str | None) -> str | None:
    if not key:
        return None
    from tradebot.strategies import get_spec

    try:
        spec = get_spec(key)
        rel = "tradebot/strategies/" + (getattr(spec, "base_key", None) or key)
    except Exception:          # noqa: BLE001 — neznámy kľúč: hash sa nezapíše, pokus áno
        rel = "tradebot/strategies/" + key
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=REPO, capture_output=True, text=True)
    except OSError:
        return None
    return out.stdout.strip() or None


def append(hypothesis: str, rec: dict[str, Any], root: Path | None = None, *, committed=_committed,
           now: datetime | None = None) -> dict[str, Any]:
    """Zapíše jeden pokus. Odmietne ho (RegisterError) bez hlavičky, mimo L, nad rozpočet, nad 5 voľných parametrov
    alebo ako 11. novú hypotézu štvrťroka na jednom trezore. Vráti zapísaný riadok."""
    src = rec.get("source")
    if src not in SOURCES:
        raise RegisterError(f"zdroj pokusu {src!r} nie je jeden z {', '.join(SOURCES)}")
    row = dict(rec)
    row.setdefault("time", (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"))
    if not row.get("market") and row.get("pair"):
        row["market"] = market_of(row["pair"]) or row["pair"]
    if src != "legacy":
        require_header(hypothesis, root, committed=committed)
    if src not in ("legacy", "study") and row.get("timerange"):
        check_search(row["timerange"], row.get("pair") or row.get("market"), f"pokus ({src})")
    if src != "legacy" and "git" not in row:
        row["git"] = _git_hash(row.get("key"))
    rows = attempts(hypothesis, root)
    if src in BUDGET_SOURCES:
        configs = _configs(rows, BUDGET_SOURCES)
        if config_id(row) not in configs and len(configs) >= BUDGET:
            raise RegisterError(f"hypotéza {hypothesis}: rozpočet {BUDGET} konfigurácií je vyčerpaný (navýšenie sa nepripúšťa)")
        volne = free_params(rows + [row], header_fixed(hypothesis, root))
        if len(volne) > MAX_FREE_PARAMS:
            raise RegisterError(f"hypotéza {hypothesis}: {len(volne)} voľných parametrov ({', '.join(volne)}), "
                                f"najviac {MAX_FREE_PARAMS}; pevné vymenuj v hlavičke („## Pevné parametre“)")
    if src not in ("legacy",) and _first_time(rows) is None and row.get("market") in MARKETS:
        q = _quarter(row["time"])
        uz = _new_in_quarter(row["market"], q, root, hypothesis)
        if len(uz) >= MAX_NEW_PER_QUARTER:
            raise RegisterError(f"trezor {row['market']}: v {q} je už {len(uz)} nových hypotéz (najviac {MAX_NEW_PER_QUARTER})")
    p = _jsonl(hypothesis, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return row


def monthly_pnl(trades: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mesačný PnL z obchodov behu (mesiac zatvorenia, `profit_abs`) — pre N_eff a PBO."""
    out: dict[str, float] = {}
    for t in trades:
        d = str(t.get("close_date") or t.get("open_date") or "")[:7]
        if len(d) == 7:
            out[d] = out.get(d, 0.0) + float(t.get("profit_abs") or 0.0)
    return [{"month": m, "pnl": round(v, 2)} for m, v in sorted(out.items())]


def attempt_of_run(rec: dict[str, Any], trades: Iterable[dict[str, Any]], source: str = "manual") -> dict[str, Any]:
    """Riadok registra z hotového behu histórie (`cli run --hypothesis`)."""
    s = rec.get("settings") or {}
    r = rec.get("result") or {}
    return {"key": s.get("strategy"), "pair": s.get("pair"), "market": market_of(s.get("pair")) or s.get("pair"),
            "tf": s.get("timeframe"), "params": rec.get("params") or {}, "timerange": s.get("timerange"),
            "source": source, "run": rec.get("id"), "pf": r.get("profit_factor"), "trades": r.get("trades"),
            "monthly": monthly_pnl(trades)}


def vault_timerange(market: str, vault: str, data: dict[str, Any] | None = None) -> str:
    """Obdobie trezoru ako Freqtrade timerange (koniec bez). C končí dnes."""
    per = periods(market, data if data is not None else load_vaults())[vault]
    if per is None:
        raise RegisterError(f"trezor {market} {vault} nemá hranicu")
    do = min(per[1], date.today())
    return f"{_ymd(per[0])}-{_ymd(do + timedelta(days=1))}"


def status(hypothesis: str, root: Path | None = None) -> dict[str, Any]:
    rows = attempts(hypothesis, root)
    budget = len(_configs(rows, BUDGET_SOURCES))
    v = load_vaults(root)
    opened = [o for m in (v.get("markets") or {}).values() for o in (m.get("opened") or [])
              if o.get("hypothesis") == hypothesis]
    return {"hypothesis": hypothesis, "attempts": len(rows), "budget_used": budget, "budget": BUDGET,
            "N": n_trials(rows), "N_eff": n_eff(rows), "free_params": free_params(rows, header_fixed(hypothesis, root)),
            "markets": sorted({str(r.get("market")) for r in rows if r.get("market")}),
            "sources": {s: sum(1 for r in rows if r.get("source") == s) for s in SOURCES if any(r.get("source") == s for r in rows)},
            "vaults_opened": opened, "wf": (v.get("wf") or {}).get(hypothesis)}


# -- trezory ----------------------------------------------------------------- #

def _vaults_path(root: Path | None) -> Path:
    return Path(root or REGISTER_DIR) / "vaults.json"


def load_vaults(root: Path | None = None) -> dict[str, Any]:
    p = _vaults_path(root)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"version": 1, "markets": {}, "wf": {}}


def save_vaults(data: dict[str, Any], root: Path | None = None) -> Path:
    p = _vaults_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def k_of(market: str, vault: str = "B", data: dict[str, Any] | None = None) -> int | None:
    """k trezoru = počiatočné k + každý kľúč každej hypotézy, ktorá ho otvorila. None = k0 ešte nie je spočítané."""
    data = data if data is not None else load_vaults()
    m = (data.get("markets") or {}).get(market) or {}
    k0 = (m.get("k0") or {}).get(vault) if isinstance(m.get("k0"), dict) else None
    if k0 is None and vault == "C" and m.get("c_from"):
        k0 = {"k": 0}            # C = nové dáta od commitu hraníc: pred prvým otvorením ich nevidel nikto
    if k0 is None:
        return None
    return int(k0["k"]) + sum(len(o.get("keys") or [1]) for o in (m.get("opened") or []) if o.get("vault") == vault)


def t_req(k: int, *, economic: bool = False, few_trades: bool = False, skew: bool = False) -> float:
    """Φ⁻¹(1 − 0,025 / k), −0,3 za ekonomický dôvod, +0,5 pri výnimke pod 75 obchodov/rok, +0,3 pri šikmosti < −1."""
    if k < 1:
        raise ValueError("k musí byť aspoň 1")
    t = NormalDist().inv_cdf(1 - 0.025 / k)
    return t - (0.3 if economic else 0) + (0.5 if few_trades else 0) + (0.3 if skew else 0)


def _years(a: date, b: date) -> float:
    return ((b - a).days + 1) / 365.25


def vault_length_ok(market: str) -> tuple[bool, str]:
    """Trezor ≥ 2 roky alebo ≥ 30 % použiteľných dát trhu (L + B), platí dlhšie z oboch; tolerancia 1 %."""
    p = periods(market)
    b = _years(*p["B"])                                              # type: ignore[misc]
    usable = _years(*p["L"]) + b                                     # type: ignore[misc]
    need = max(2.0, 0.3 * usable)
    return b >= need * 0.99, f"trezor {b:.2f} r, treba {need:.2f} r (2 roky alebo 30 % z {usable:.2f} r)"


def _k0_in_head(market: str, vault: str, root: Path | None = None) -> bool:
    """Počiatočné k trhu je v commitnutej verzii `vaults.json` (HEAD), nie len lokálne spočítané."""
    p = _vaults_path(root)
    try:
        rel = str(p.resolve().relative_to(REPO.resolve())).replace("\\", "/")
        out = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    except (ValueError, OSError):
        return False
    if out.returncode != 0:
        return False
    try:
        head = json.loads(out.stdout)
    except ValueError:
        return False
    return k_of(market, vault, head) is not None


def open_vault(hypothesis: str, market: str, vault: str, keys: Sequence[str], root: Path | None = None, *,
               committed=_committed, k0_committed=_k0_in_head, today: date | None = None) -> dict[str, Any]:
    """Zapíše otvorenie trezoru (zámok). Vráti {"k": k vrátane tohto otvorenia, "t_req": …, "period": …}."""
    if market not in MARKETS:
        raise RegisterError(f"trh {market} nemá v §1 trezor")
    if vault not in ("B", "C"):
        raise RegisterError("trezor je B alebo C")
    if not keys:
        raise RegisterError("otvorenie trezoru potrebuje kľúče stratégií (kópie rodiny sa rátajú do k)")
    p = require_header(hypothesis, root, committed=committed)
    if market not in header_markets(hypothesis, root):
        raise RegisterError(f"hypotéza {hypothesis}: trh {market} nie je v hlavičke („## Trhy“)")
    data = load_vaults(root)
    m = data.setdefault("markets", {}).setdefault(market, {})
    if vault == "C" and not m.get("c_from"):
        raise RegisterError(f"trezor {market} C: hranica C (`c_from`) nie je commitnutá vo vaults.json")
    if k_of(market, vault, data) is None:
        raise RegisterError(f"trezor {market} {vault}: počiatočné k nie je spočítané (python -m tester.register k0 --write)")
    if not k0_committed(market, vault, root):
        raise RegisterError(f"trezor {market} {vault}: počiatočné k nie je commitnuté vo vaults.json (commit pred otvorením)")
    if vault == "B":
        ok, why = vault_length_ok(market)
        if not ok:
            raise RegisterError(f"trezor {market} B je krátky: {why}")
    if any(o.get("hypothesis") == hypothesis and o.get("vault") == vault for o in m.get("opened") or []):
        raise RegisterError(f"hypotéza {hypothesis} už trezor {market} {vault} otvorila — druhé otvorenie = nová hypotéza")
    regime = "Iný režim" in _sections(p.read_text(encoding="utf-8")) and not header_problems_section(p, "Iný režim")
    m.setdefault("opened", []).append({"hypothesis": hypothesis, "vault": vault, "keys": sorted(set(keys)),
                                       "date": (today or date.today()).isoformat(), "regime_measured": regime})
    save_vaults(data, root)
    k = k_of(market, vault, data) or 1
    per = periods(market, data)[vault]
    return {"k": k, "t_req": t_req(k), "period": [per[0].isoformat(), per[1].isoformat()] if per else None,
            "regime_measured": regime}


def header_problems_section(path: Path, name: str) -> bool:
    """True, ak voliteľná časť hlavičky chýba alebo je len šablóna."""
    body = _sections(path.read_text(encoding="utf-8")).get(name, "")
    return not body or body.startswith("Meranie pred otvorením") or all(_PLACEHOLDER.match(x) or not x.strip()
                                                                        for x in body.splitlines())


def lock_wf(hypothesis: str, root: Path | None = None, *, today: date | None = None) -> None:
    """Walk-forward sa pre hypotézu púšťa raz (krok 6); druhý = nová hypotéza."""
    data = load_vaults(root)
    wf = data.setdefault("wf", {})
    if hypothesis in wf:
        raise RegisterError(f"hypotéza {hypothesis}: walk-forward už bežal {wf[hypothesis].get('date')} — druhý = nová hypotéza")
    wf[hypothesis] = {"date": (today or date.today()).isoformat()}
    save_vaults(data, root)


# -- počiatočné k ------------------------------------------------------------ #

def _settings_of_line(line: str) -> dict[str, Any] | None:
    i = line.find('"settings"')
    if i < 0:
        return None
    j = line.find("{", i)
    try:
        obj, _ = json.JSONDecoder().raw_decode(line, j)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def _runs_settings(runs_dir: Path, archive_dir: Path) -> Iterable[dict[str, Any]]:
    """Nastavenia všetkých behov histórie aj archívu (len `settings`, bez parsovania krivky)."""
    if runs_dir.exists():
        for p in runs_dir.glob("*/run.json"):
            try:
                s = json.loads(p.read_text(encoding="utf-8")).get("settings")
            except (OSError, ValueError):
                continue
            if isinstance(s, dict):
                yield s
    if archive_dir.exists():
        for p in sorted(archive_dir.glob("runs-*.jsonl.gz")):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    s = _settings_of_line(line)
                    if s is not None:
                        yield s


def initial_k(runs_dir: Path | None = None, archive_dir: Path | None = None,
              settings: Iterable[dict[str, Any]] | None = None,
              registry_keys: Sequence[str] | None = None) -> dict[str, dict[str, Any]]:
    """Počiatočné k trezoru B každého trhu: kľúče stratégií (rodiny aj kópie), ktoré mali beh dotýkajúci sa
    obdobia trezoru, + štúdie §1, ktoré ho videli. Prísny horný odhad (§9): každý kľúč sa ráta, aj keď beh bol
    len jeden. Behy automatu na Mac mini mimo histórie (`gl_state`, `hyper_state`) tu nie sú."""
    from tradebot.strategies import canonical_key

    keys: dict[str, set[str]] = {m: set() for m in MARKETS}
    src = settings if settings is not None else _runs_settings(Path(runs_dir or RUNS_DIR), Path(archive_dir or ARCHIVE_DIR))
    n_runs: dict[str, int] = {m: 0 for m in MARKETS}
    for s in src:
        market = market_of(s.get("pair"))
        tr = s.get("timerange")
        if market is None or not tr:
            continue
        try:
            if "B" not in zones(tr, market):
                continue
        except (RegisterError, ValueError):
            continue
        key = canonical_key(s.get("strategy")) or "ibs"
        keys[market].add(key)
        n_runs[market] += 1
    if registry_keys is None:
        from tradebot.strategies import STRATEGIES

        registry_keys = [k for k in STRATEGIES if not k.startswith("demo")]
    out = {}
    for m in MARKETS:
        b0, b1 = periods(m)["B"]                                         # type: ignore[misc]
        studies = sorted({name for name, mk, a, b in STUDIES if mk == m and _d(a) <= b1 and _d(b) >= b0})
        parts = {"behy": len(keys[m])}
        rodiny = set(keys[m])
        if _d(REFERENCE_SPAN[0]) <= b1 and _d(REFERENCE_SPAN[1]) >= b0:
            rodiny |= set(registry_keys)             # referenčné okná videli všetky legacy kľúče
            parts["referenčné okná (všetky kľúče registra)"] = len(registry_keys)
        n_rodin = len(rodiny)
        tri = TRIEDENIE.get(m)
        if tri and _d(tri[0]) <= b1 and _d(tri[1]) >= b0 and n_rodin < TRIEDENIE_FAMILIES:
            parts["triedenie starých rokov (najmenej rodín)"] = TRIEDENIE_FAMILIES
            n_rodin = TRIEDENIE_FAMILIES
        parts["štúdie"] = len(studies)
        out[m] = {"k": n_rodin + len(studies), "keys": sorted(rodiny), "studies": studies, "parts": parts,
                  "runs": n_runs[m], "computed": date.today().isoformat(),
                  "note": "prísny horný odhad (§1, §9): kľúče s behom v trezore (história aj archív), pri prekryve "
                          "s referenčnými oknami 10/2021–9/2026 všetky kľúče registra, triedenie a štúdie §1; "
                          "gl_state/hyper_state z Mac mini nie sú v repe"}
    return out


def _params_of_line(line: str) -> dict[str, Any] | None:
    i = line.find('"params"')
    if i < 0:
        return None
    j = line.find("{", i)
    try:
        obj, _ = json.JSONDecoder().raw_decode(line, j)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def history_n(keys: Iterable[str], runs_dir: Path | None = None, archive_dir: Path | None = None) -> dict[str, int]:
    """Odhad N legacy stratégie z histórie behov (aj archívu): počet rôznych nastavení (parametre, pár, TF) na kľúč.
    Behy automatu Mac mini, ktoré sa do histórie nevrátili (`gl_state`, `hyper_state`, `glwr`, `glrr`), tu nie sú —
    ich odhad sa pripíše zvlášť (`register legacy … --n`)."""
    from tradebot.strategies import canonical_key

    chcene = {canonical_key(k) or k for k in keys}
    seen: dict[str, set[str]] = {k: set() for k in chcene}

    def add(s: dict[str, Any] | None, params: dict[str, Any] | None) -> None:
        if not isinstance(s, dict):
            return
        key = canonical_key(s.get("strategy")) or "ibs"
        if key in seen:
            ident = json.dumps([s.get("pair"), s.get("timeframe"), params or {}], sort_keys=True, default=str)
            seen[key].add(hashlib.sha1(ident.encode()).hexdigest())

    rd, ad = Path(runs_dir or RUNS_DIR), Path(archive_dir or ARCHIVE_DIR)
    if rd.exists():
        for p in rd.glob("*/run.json"):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            add(r.get("settings"), r.get("params"))
    if ad.exists():
        for p in sorted(ad.glob("runs-*.jsonl.gz")):
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    add(_settings_of_line(line), _params_of_line(line))
    return {k: len(v) for k, v in seen.items()}


# -- CLI --------------------------------------------------------------------- #

def _print_status(st: dict[str, Any]) -> None:
    print(f"{st['hypothesis']}: {st['attempts']} pokusov, rozpočet {st['budget_used']}/{st['budget']}, "
          f"N {st['N']}, N_eff {st['N_eff']}, voľné parametre {len(st['free_params'])}/{MAX_FREE_PARAMS}"
          + (f" ({', '.join(st['free_params'])})" if st["free_params"] else ""))
    if st["sources"]:
        print("  zdroje: " + ", ".join(f"{k} {v}" for k, v in st["sources"].items()))
    for o in st["vaults_opened"]:
        print(f"  trezor {o['vault']} otvorený {o['date']} ({', '.join(o['keys'])})")
    if st["wf"]:
        print(f"  walk-forward {st['wf'].get('date')}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.register", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", help="adresár registra (default tester/register)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="šablóna hlavičky hypotézy")
    p.add_argument("hypothesis")
    p = sub.add_parser("check", help="je hlavička hotová a commitnutá?")
    p.add_argument("hypothesis")
    p = sub.add_parser("status", help="N, N_eff, rozpočet, voľné parametre a trezory")
    p.add_argument("hypothesis", nargs="?")
    p = sub.add_parser("periods", help="rozdelenie trhu (§1)")
    p.add_argument("market", nargs="?")
    p = sub.add_parser("k0", help="počiatočné k trezorov z histórie behov a štúdií")
    p.add_argument("--write", action="store_true", help="zapísať do vaults.json (potom commitnúť)")
    p = sub.add_parser("open", help="otvoriť trezor (raz na hypotézu)")
    p.add_argument("hypothesis")
    p.add_argument("market")
    p.add_argument("vault", choices=("B", "C"))
    p.add_argument("--keys", required=True, help="kľúče stratégií oddelené čiarkou (všetky kópie, ktoré trezor uvidia)")
    p = sub.add_parser("legacy", help="zapíše odhad N legacy stratégie (história behov + --n z Mac mini)")
    p.add_argument("hypothesis")
    p.add_argument("--keys", required=True, help="kľúče rodiny oddelené čiarkou (všetky kópie)")
    p.add_argument("--n", type=int, default=0, help="behy mimo histórie (gl_state, hyper_state, glwr, glrr, štúdie)")
    p.add_argument("--note", default="")
    p = sub.add_parser("treq", help="t_req pre k")
    p.add_argument("k", type=int)
    p.add_argument("--economic", action="store_true")
    p.add_argument("--few-trades", action="store_true")
    p.add_argument("--skew", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")         # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass
    root = Path(a.root) if a.root else None
    try:
        if a.cmd == "new":
            path = header_path(a.hypothesis, root)
            if path.exists():
                raise RegisterError(f"{path} už existuje")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(header_template(a.hypothesis), encoding="utf-8")
            print(f"{path}: vyplň všetky časti a commitni ju pred prvým behom")
        elif a.cmd == "check":
            require_header(a.hypothesis, root)
            print(f"{a.hypothesis}: hlavička je hotová a commitnutá; trhy {', '.join(header_markets(a.hypothesis, root))}")
        elif a.cmd == "status":
            for h in ([a.hypothesis] if a.hypothesis else _hypotheses(root)):
                _print_status(status(h, root))
            data = load_vaults(root)
            if not a.hypothesis:
                for m in MARKETS:
                    k = k_of(m, "B", data)
                    print(f"trezor {m} B: " + (f"k {k}, t_req {t_req(k):.2f}" if k else "počiatočné k nie je spočítané"))
        elif a.cmd == "periods":
            for m in ([a.market] if a.market else list(MARKETS)):
                p_ = periods(m, load_vaults(root))
                print(f"{m}: L {p_['L'][0]} – {p_['L'][1]} ({l_timerange(m)}), trezor B {p_['B'][0]} – {p_['B'][1]}, "
                      f"rok A {p_['A'][0]} – {p_['A'][1]}, WF {MARKETS[m].wf[0]}/{MARKETS[m].wf[1]} mes.")
                print("   okná L: " + ", ".join(l_windows(m)))
        elif a.cmd == "k0":
            res = initial_k()
            for m, r in res.items():
                print(f"{m}: k0 {r['k']}, t_req {t_req(max(1, r['k'])):.2f} — "
                      + ", ".join(f"{k} {v}" for k, v in r["parts"].items())
                      + (f" ({', '.join(r['studies'])})" if r["studies"] else "") + f"; {r['runs']} behov v trezore")
            if a.write:
                data = load_vaults(root)
                for m, r in res.items():
                    mk = data.setdefault("markets", {}).setdefault(m, {})
                    mk.update({"L": list(MARKETS[m].L), "B": list(MARKETS[m].B), "A": list(YEAR_A)})
                    mk.setdefault("c_from", None)
                    mk.setdefault("k0", {})["B"] = r
                print(f"zapísané do {save_vaults(data, root)} — commitni ho, až potom sa trezor smie otvoriť")
        elif a.cmd == "open":
            r = open_vault(a.hypothesis, a.market, a.vault, [x.strip() for x in a.keys.split(",") if x.strip()], root)
            print(f"trezor {a.market} {a.vault} otvorený pre {a.hypothesis}: obdobie {r['period'][0]} – {r['period'][1]}, "
                  f"k {r['k']}, t_req {r['t_req']:.2f}" + ("" if r["regime_measured"] else
                                                          "; iný režim nie je zmeraný v hlavičke -> výsledok najviac ⏳"))
        elif a.cmd == "legacy":
            keys = [x.strip() for x in a.keys.split(",") if x.strip()]
            hist = history_n(keys)
            n = sum(hist.values()) + max(0, a.n)
            append(a.hypothesis, {"source": "legacy", "key": ",".join(keys), "n": n, "history": hist,
                                  "outside_history": a.n, "note": a.note}, root)
            print(f"{a.hypothesis}: legacy N {n} = história {sum(hist.values())} "
                  f"({', '.join(f'{k} {v}' for k, v in hist.items())}) + mimo histórie {a.n}")
        elif a.cmd == "treq":
            print(f"{t_req(a.k, economic=a.economic, few_trades=a.few_trades, skew=a.skew):.2f}")
    except RegisterError as e:
        print(f"chyba: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
