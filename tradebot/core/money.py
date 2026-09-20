"""Peniaze jedného obchodu a celého behu — **jediná** definícia pre oba enginy aj analytiku.

### Prečo na jednom mieste
Trh s hodnotou bodu inou než 1 (MNQ 2 $, zlato 100 $, forex lot 100 000) prezradí každú
kópiu vzorca, ktorá na `point_value` zabudla: raz je hrubý zisk v dolároch a objem
v bodoch, inokedy oboje v bodoch. Pomer (break-even) potom vyjde ×hodnota bodu, alebo
sedí, ale doláre, drawdown a škálovanie podľa rizika nie. Preto tu:

    hodnota bodu  pv      = InstrumentSpec.point_value (mena účtu za pohyb ceny o 1.0 na 1 kus)
    nominál vstupu        = open_rate  × amount × pv
    nominál výstupu       = close_rate × amount × pv
    objem (volume)        = nominál vstupu + nominál výstupu
    hrubý zisk (gross)    = (close_rate − open_rate) × smer × amount × pv
    poplatky              = nominál vstupu × fee_open + nominál výstupu × fee_close
    čistý zisk (net)      = gross − poplatky          (Freqtrade `profit_abs`, funding 0)
    break-even poplatok   = gross / volume × 100      (% na stranu)

`amount` je **počet kusov tak, ako ich plánuje engine** (kontrakty, loty, mince) —
v zázname obchodu (`trades.json`) rovnako pre emulátor MultiCharts aj pre Freqtrade.
Freqtrade si interne drží množstvo v základnej mene (`kontrakty × contractSize`) a burza
Tester mu dáva `contractSize = point_value`; normalizácia výsledku to delí späť
(`tester.webapp.runner.result_from_zip`).

Záznam obchodu nesie `point_value` výslovne. Starší záznam ho nemá — to **nie je**
hodnota 1, ale „nevedno": doplní ju `fill_point_value` z inštrumentu páru behu.
Poplatok za tick (CFD spread, `InstrumentSpec.cost_pct`) je percento z ceny, a keďže
nominál aj zisk nesú tú istú hodnotu bodu, vyjde v peniazoch presne `ticky × tick × pv × kusy`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

__all__ = [
    "TradeMoney", "trade_money", "row_money", "row_point_value", "point_value_for_pair",
    "fill_point_value", "gross_and_volume", "break_even_pct", "max_drawdown", "streaks",
    "summary_money",
]


@dataclass(frozen=True)
class TradeMoney:
    """Peniaze jedného uzavretého obchodu v mene účtu."""

    gross: float
    notional_open: float
    notional_close: float
    fee_open: float
    fee_close: float

    @property
    def volume(self) -> float:
        """Obojstranný nominál — základ, z ktorého sa počíta poplatok aj break-even."""
        return self.notional_open + self.notional_close

    @property
    def fees(self) -> float:
        return self.fee_open + self.fee_close

    @property
    def net(self) -> float:
        return self.gross - self.fees


def trade_money(open_rate: float, close_rate: float, amount: float, *, is_short: bool,
                point_value: float = 1.0, fee_open: float = 0.0,
                fee_close: float | None = None) -> TradeMoney:
    """Peniaze obchodu. `fee_*` sú podiely (0.0005 = 0,05 %) na stranu; `fee_close`
    bez hodnoty = `fee_open`."""
    pv = float(point_value)
    qty = float(amount)
    o, c = float(open_rate), float(close_rate)
    smer = -1.0 if is_short else 1.0
    n_open = o * qty * pv
    n_close = c * qty * pv
    f_close = fee_open if fee_close is None else fee_close
    return TradeMoney(
        gross=(c - o) * smer * qty * pv,
        notional_open=n_open, notional_close=n_close,
        fee_open=n_open * float(fee_open or 0.0), fee_close=n_close * float(f_close or 0.0),
    )


def row_point_value(row: dict[str, Any], default: float = 1.0) -> float:
    """Hodnota bodu zo záznamu obchodu; `default`, keď ju záznam nenesie."""
    pv = row.get("point_value")
    try:
        pv = float(pv) if pv is not None else None
    except (TypeError, ValueError):
        pv = None
    return pv if pv and pv > 0 else float(default)


def row_money(row: dict[str, Any], *, fee: float | None = None,
              point_value: float | None = None) -> TradeMoney:
    """Peniaze záznamu z `trades.json`. `fee` prebije poplatok uložený v zázname."""
    pv = float(point_value) if point_value else row_point_value(row)
    f_open = float(row.get("fee_open") or 0.0) if fee is None else float(fee)
    f_close = float(row.get("fee_close") or 0.0) if fee is None else float(fee)
    return trade_money(
        float(row.get("open_rate") or 0.0), float(row.get("close_rate") or 0.0),
        float(row.get("amount") or 0.0), is_short=bool(row.get("is_short")),
        point_value=pv, fee_open=f_open, fee_close=f_close,
    )


def point_value_for_pair(pair: str | None) -> float | None:
    """Hodnota bodu inštrumentu s týmto symbolom, alebo `None`, keď ho register nepozná."""
    if not pair:
        return None
    from .types import INSTRUMENTS

    for inst in INSTRUMENTS.values():
        if inst.symbol == pair:
            return float(inst.point_value)
    return None


def fill_point_value(rows: Iterable[dict[str, Any]], pair: str | None) -> list[dict[str, Any]]:
    """Doplní `point_value` záznamom, ktoré ho nemajú (behy spred jeho zavedenia).

    Mení záznamy na mieste a vráti ich zoznam. Neznámy pár aj hodnota 1 → nechá tak
    (chýbajúce pole konzument číta ako 1, čo je pre ten pár pravda; záznam z API tak
    ostane bajt po bajte, aký bol). Existujúcu hodnotu nikdy neprepíše.
    """
    rows = list(rows)
    if not rows or all("point_value" in r for r in rows):
        return rows
    pv = point_value_for_pair(pair)
    if pv is None or pv == 1.0:
        return rows
    for r in rows:
        r.setdefault("point_value", pv)
    return rows


def gross_and_volume(rows: Iterable[dict[str, Any]]) -> tuple[float, float]:
    """(hrubý zisk, objem) v mene účtu — z cien, nezávisle od poplatku behu."""
    gross = volume = 0.0
    for r in rows:
        m = row_money(r, fee=0.0)
        gross += m.gross
        volume += m.volume
    return gross, volume


def break_even_pct(gross: float, volume: float, digits: int | None = 4) -> float | None:
    """Koľko smie burza brať na stranu (%), aby obchody vyšli na nulu."""
    if not volume or volume <= 0:
        return None
    be = gross / volume * 100.0
    return round(be, digits) if digits is not None else be


def max_drawdown(profits: Sequence[float], wallet: float) -> tuple[float, float]:
    """(max drawdown v mene, v % z vrcholu účtu) — definícia Freqtradu.

    Vrchol začína na nule (štart účtu); percento je pokles v bode najväčšieho
    absolútneho poklesu voči zostatku na vtedajšom vrchole (`max_drawdown_account`).
    """
    cum = peak = 0.0
    dd_abs = 0.0
    dd_pct = 0.0
    for p in profits:
        cum += float(p)
        peak = max(peak, cum)
        gap = peak - cum
        if gap > dd_abs:
            dd_abs = gap
            vrchol = float(wallet) + peak
            dd_pct = gap / vrchol * 100.0 if vrchol > 0 else 0.0
    return dd_abs, dd_pct


def streaks(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Najdlhšia séria ziskov a najdlhšia séria strát za sebou — kedy bola a za koľko.

    Obchody idú v poradí zatvorenia (tak, ako sú v `trades.json` behu). Nulový obchod
    (`profit_abs == 0`) nepatrí do žiadnej série a obe preruší. Pri viacerých rovnako
    dlhých sériách sa vypíše prvá a `count` povie, koľko ich bolo.

    Séria je `from_i`..`to_i` — indexy do obchodov behu, nie ich kópia: obchody série
    (a ich zisky) sa vypíšu z `trades.json`, takže sa nemôžu rozísť so súhrnom.
    """
    best: dict[str, dict[str, Any]] = {}
    counts = {"win": 0, "loss": 0}
    i, n = 0, len(rows)
    while i < n:
        p = float(rows[i].get("profit_abs") or 0.0)
        if p == 0.0:
            i += 1
            continue
        kind = "win" if p > 0 else "loss"
        total = 0.0
        j = i
        while j < n:
            q = float(rows[j].get("profit_abs") or 0.0)
            if q == 0.0 or (q > 0) != (p > 0):
                break
            total += q
            j += 1
        dlzka = j - i
        doteraz = best.get(kind)
        if doteraz is None or dlzka > doteraz["n"]:
            best[kind] = {
                "n": dlzka, "from_i": i, "to_i": j - 1,
                "start": rows[i].get("open_date"), "end": rows[j - 1].get("close_date"),
                "pnl_abs": round(total, 2),
            }
            counts[kind] = 1
        elif dlzka == doteraz["n"]:
            counts[kind] += 1
        i = j
    out: dict[str, Any] = {}
    for kind in ("win", "loss"):
        b = best.get(kind)
        if b is not None:
            b["count"] = counts[kind]
        out[kind] = b
    return out


def summary_money(rows: Sequence[dict[str, Any]], wallet: float) -> dict[str, Any]:
    """Peňažná časť súhrnu behu z uložených obchodov (zoradených podľa zatvorenia).

    Kľúče sú tie isté ako v `run.json → result`, takže súhrn emulátora, normalizovaný
    Freqtrade beh aj prepočet starých behov (`tester.recompute`) sa nemôžu rozísť.
    """
    profits = [float(r.get("profit_abs") or 0.0) for r in rows]
    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)
    pnl = sum(profits)
    gp = sum(p for p in profits if p > 0)
    gl = -sum(p for p in profits if p < 0)
    gross, volume = gross_and_volume(rows)
    dd_abs, dd_pct = max_drawdown(profits, wallet)
    wallet = float(wallet)
    exits: dict[str, dict[str, Any]] = {}
    for r, p in zip(rows, profits):
        e = exits.setdefault(str(r.get("exit_reason")), {"n": 0, "pnl_abs": 0.0})
        e["n"] += 1
        e["pnl_abs"] += p
    for e in exits.values():
        e["pnl_abs"] = round(e["pnl_abs"], 2)
    return {
        "trades": len(rows), "wins": wins, "losses": losses, "draws": len(rows) - wins - losses,
        "winrate": round(100.0 * wins / len(rows), 2) if rows else 0.0,
        "pnl_abs": round(pnl, 2), "pnl_pct": round(pnl / wallet * 100.0, 3) if wallet else 0.0,
        "profit_factor": round(gp / gl, 3) if gl else (round(gp, 3) if gp else 0.0),
        "max_drawdown_abs": round(dd_abs, 2), "max_drawdown_pct": round(dd_pct, 3),
        "starting_balance": wallet, "final_balance": round(wallet + pnl, 2),
        "gross_abs": round(gross, 2), "volume_abs": round(volume, 2),
        "break_even_pct": break_even_pct(gross, volume),
        "exits": exits, "streaks": streaks(rows),
    }
