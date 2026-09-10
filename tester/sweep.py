"""Sweep: tá istá stratégia na mriežke hodnôt parametra — a kritérium, podľa ktorého vybrať.

    PY -m tester.webapp.cli sweep --param rrRatio=2:8:0.5 --timerange 20250904-20260904
    PY -m tester.webapp.cli sweep --param rrRatio=2,3,5 --param slLookback=10,20,30 \\
        --goal winrate --max-dd 15

### Načo to je
Hľadanie parametrov bez toho, aby tester čokoľvek písal v kóde. Každý bod mriežky je
**obyčajný backtest** — uloží sa do histórie, dá sa otvoriť, porovnať, prehnať Monte
Carlom. Sweep k tomu pridá len dve veci: rozbalí hodnoty a na konci zoradí výsledky podľa
kritéria, ktoré si tester zvolil.

Oproti hyperoptu je to hlúpejšie (prejde všetko, nič sa neučí), ale čitateľné: „RR 3 → 5
zlepší break-even vo všetkých oknách" je záver, s ktorým sa dá pracovať, kým „optimalizátor
našiel 7,3" nie. A nemá ako pretrénovať viac, než koľko bodov mriežka má.

### Kritériá
Stratégia sa nedá „optimalizovať" všeobecne — treba povedať, čo je lepšie:

| kritérium | čo maximalizuje | kedy |
|---|---|---|
| `break_even` | break-even poplatok (% na stranu) | prednastavené — jediné číslo nezávislé od sizingu a peňaženky |
| `profit` | čistý zisk v % | keď ide o výnos a drawdown stačí strážiť limitom |
| `winrate` | podiel ziskových obchodov | keď má byť séria strát krátka |
| `drawdown` | najnižší max drawdown | keď je hranicou účet, nie výnos |

Ku každému sa dá pridať strop `--max-dd` (max drawdown v %) a `--min-trades` (obchodov
**za rok**, prepočíta sa na dĺžku okna — rovnako ako v hyperopte). Body, ktoré
ich porušia, sa nezahodia — zobrazia sa pod čiarou a označia, aby bolo vidno, že tam
optimum „je", len je mimo dohodnutých mantinelov.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

__all__ = ["GOALS", "GOAL_TITLES", "parse_values", "to_knob", "expand", "rank",
           "table", "describe"]

#: kritérium -> (pole vo výsledku behu, väčšie je lepšie)
GOALS: dict[str, tuple[str, bool]] = {
    "break_even": ("break_even_pct", True),
    "profit": ("pnl_pct", True),
    "winrate": ("winrate", True),
    "drawdown": ("max_drawdown_pct", False),
}

GOAL_TITLES = {
    "break_even": "najvyšší break-even poplatok",
    "profit": "najvyšší zisk",
    "winrate": "najvyšší podiel ziskových",
    "drawdown": "najnižší drawdown",
}


def parse_values(spec: str) -> list[Any]:
    """`2:8:0.5` → rozsah, `3,5,8` → zoznam, `0.25@pct` → veľkostné pole.

    Rozsah je vrátane hornej hranice; keď sú všetky tri čísla celé, sú celé aj hodnoty.
    """
    from .webapp.cli import parse_set

    text = spec.strip()
    if ":" in text and "," not in text:
        parts = text.split(":")
        if len(parts) != 3:
            raise ValueError(f"rozsah chce od:do:krok, dostal {spec!r}")
        lo, hi, step = (float(p) for p in parts)
        if step <= 0:
            raise ValueError(f"krok musí byť kladný, dostal {step}")
        whole = all(float(p).is_integer() for p in parts)
        out: list[Any] = []
        value = lo
        while value <= hi + step * 1e-9:
            out.append(int(round(value)) if whole else round(value, 10))
            value += step
        return out
    return [parse_set(f"x={item.strip()}")[1] for item in text.split(",") if item.strip()]


def to_knob(spec: str) -> dict[str, Any]:
    """Ten istý text pre hyperopt: `2:8:0.5` → rozsah, `3,5,8` → zoznam možností.

    Zadanie sa medzi sweepom a hyperoptom nepíše dvakrát — tester napíše hodnoty raz
    a rozhodne sa až, či sa má mriežka prejsť celá (sweep), alebo sa v nej má hľadať
    (hyperopt). Rozdiel je v tom, čo si z textu vezmú: sweep zoznam hodnôt, hyperopt
    krajné hodnoty a krok ako presnosť.

    Rozsah `od:do:krok` sa preto stane rozsahom, nie zoznamom — hyperopt hľadá spojito
    a `2:8:0.5` znamená „medzi 2 a 8, po desatinách", nie „presne týchto trinásť hodnôt".
    Vypísaný zoznam ostáva zoznamom možností aj tu: keď tester vymenuje `3,5,8`, iné
    číslo nechce, a to hyperopt vyjadriť vie (`CategoricalParameter`).
    """
    text = spec.strip()
    if ":" in text and "," not in text:
        parts = text.split(":")
        if len(parts) != 3:
            raise ValueError(f"rozsah chce od:do:krok, dostal {spec!r}")
        lo, hi, step = (float(p) for p in parts)
        if step <= 0:
            raise ValueError(f"krok musí byť kladný, dostal {step}")
        if lo >= hi:
            raise ValueError(f"dolná hranica {lo:g} musí byť pod hornou {hi:g}")
        return {"low": lo, "high": hi, "step": step}

    values = parse_values(text)
    if not values:
        raise ValueError(f"{spec!r}: žiadne hodnoty")
    if len(values) == 1:
        raise ValueError(f"{spec!r}: na hľadanie treba rozsah alebo aspoň dve možnosti")
    # Vypísaný zoznam je zoznam možností aj pri veľkostnom poli (`0.1@pct,0.5@pct`):
    # ladí sa číslo, jednotka je pevná a plán si ju z prvej hodnoty vezme.
    return {"choices": values}


def expand(space: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Kartézsky súčin hodnôt — jeden slovník na každý bod mriežky."""
    points: list[dict[str, Any]] = [{}]
    for name, values in space.items():
        if not values:
            raise ValueError(f"parameter {name!r} nemá žiadne hodnoty")
        points = [{**point, name: value} for point in points for value in values]
    return points


def _metric(row: dict[str, Any], key: str) -> float | None:
    value = (row.get("result") or {}).get(key)
    return None if value is None else float(value)


def _window_days(row: dict[str, Any]) -> float | None:
    """Dĺžka okna behu v dňoch z `settings.timerange`, alebo `None`."""
    from datetime import datetime

    okno = (row.get("settings") or {}).get("timerange") or ""
    try:
        a, b = okno.split("-")
        return max((datetime.strptime(b, "%Y%m%d") - datetime.strptime(a, "%Y%m%d")).days, 1)
    except ValueError:
        return None


def required_trades(min_trades: int, row: dict[str, Any]) -> int:
    """`min_trades` platí **na rok** — prepočíta sa na dĺžku okna behu (ako v loss funkcii
    hyperoptu), aby zadanie znamenalo to isté v sweepe aj v hyperopte. Bez okna platí
    číslo tak, ako je."""
    dni = _window_days(row)
    if dni is None:
        return int(min_trades)
    return max(3, int(min_trades * dni / 365))


def _within(row: dict[str, Any], max_dd: float | None, min_trades: int | None,
            per_year: bool = True) -> str | None:
    """Prečo je bod mimo mantinelov — alebo `None`, keď je v nich."""
    result = row.get("result") or {}
    if row.get("status") != "done":
        return row.get("status") or "nedobehol"
    trades = int(result.get("trades") or 0)
    if not trades:
        return "0 obchodov"
    if min_trades is not None:
        treba = required_trades(min_trades, row) if per_year else int(min_trades)
        if trades < treba:
            return f"< {treba} obchodov" + (f" ({min_trades}/rok)" if treba != min_trades else "")
    dd = _metric(row, "max_drawdown_pct")
    if max_dd is not None and dd is not None and dd > max_dd:
        return f"drawdown {dd:.1f} % > {max_dd:g} %"
    return None


def rank(rows: Iterable[dict[str, Any]], goal: str = "break_even", *,
         max_dd: float | None = None, min_trades: int | None = None,
         per_year: bool = True) -> list[dict[str, Any]]:
    """Body zoradené podľa kritéria; tie mimo mantinelov idú na koniec s dôvodom.

    Vracia tie isté záznamy doplnené o `sweep_ok` (v mantineloch) a `sweep_why` (dôvod).
    `per_year=False` berie `min_trades` ako absolútny počet — pre maticu (prah šumu na
    bunku) a pre mriežky z histórie, ktoré vznikli ešte so starým významom.
    """
    if goal not in GOALS:
        raise ValueError(f"neznáme kritérium {goal!r}; známe: {', '.join(GOALS)}")
    key, bigger_is_better = GOALS[goal]

    out = []
    for row in rows:
        why = _within(row, max_dd, min_trades, per_year)
        value = _metric(row, key)
        out.append({**row, "sweep_ok": why is None and value is not None, "sweep_why": why,
                    "sweep_value": value})

    def sort_key(row):
        value = row["sweep_value"]
        if value is None:
            return (1, 0.0)
        return (0, -value if bigger_is_better else value)

    ok = sorted([r for r in out if r["sweep_ok"]], key=sort_key)
    bad = sorted([r for r in out if not r["sweep_ok"]], key=sort_key)
    return ok + bad


def describe(goal: str, max_dd: float | None, min_trades: int | None) -> str:
    """Jednoriadkový popis zadania — patrí do výpisu aj do poznámky behu."""
    text = GOAL_TITLES.get(goal, goal)
    limits = []
    if max_dd is not None:
        limits.append(f"drawdown ≤ {max_dd:g} %")
    if min_trades is not None:
        limits.append(f"≥ {min_trades} obchodov")
    return text + (f" pri {' a '.join(limits)}" if limits else "")


def table(rows: Sequence[dict[str, Any]], names: Sequence[str], goal: str = "break_even") -> str:
    """Výsledky ako textová tabuľka pre konzolu. Bez diakritiky (Windows konzola)."""
    head = [f"{n[:12]:>12}" for n in names]
    head += [f"{'obchodov':>9}", f"{'PnL %':>8}", f"{'WR %':>6}", f"{'maxDD %':>8}",
             f"{'break-even':>11}", "  "]
    lines = ["  ".join(head), "-" * (len(" ".join(head)) + 2)]
    for i, row in enumerate(rows, 1):
        values = row.get("settings", {}).get("sweep", {}).get("values", {})
        result = row.get("result") or {}
        cells = [f"{_fmt(values.get(n)):>12}" for n in names]
        cells += [
            f"{result.get('trades', '-'):>9}",
            f"{_num(result.get('pnl_pct')):>8}",
            f"{_num(result.get('winrate'), 1):>6}",
            f"{_num(result.get('max_drawdown_pct')):>8}",
            f"{_num(result.get('break_even_pct'), 4):>11}",
        ]
        mark = "  <- najlepsi" if i == 1 and row.get("sweep_ok") else (
            f"  ({row['sweep_why']})" if row.get("sweep_why") else "")
        lines.append("  ".join(cells) + mark)
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if isinstance(value, dict):
        return f"{value.get('value')}@{value.get('unit')}"
    if isinstance(value, float):
        return f"{value:g}"
    return "-" if value is None else str(value)


def _num(value: Any, digits: int = 2) -> str:
    return "-" if value is None else f"{float(value):.{digits}f}"
