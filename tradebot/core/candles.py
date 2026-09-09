"""Skladanie vyššieho timeframu z 1m sviečok — jedno pravidlo pre všetky cesty.

Bary sa zarovnávajú na násobky TF **od epochy** (`origin="epoch"`), rovnako ako
`htf_window_opens` v jadre, ako to robí TradingView aj MultiCharts pri skladaní 3m
a 5m z 1m v grafe. Vďaka tomu vidia webapp graf, offline simulátor, emulátor
MultiCharts aj súbory pre Freqtrade tie isté bary — keby sa pravidlo rozišlo,
porovnanie výsledkov medzi platformami by prestalo niečo znamenať.

Sviečka bez jediného 1m baru (víkend, prestávka) sa **vyhadzuje**, nedopĺňa sa plochým
barom: limity `*MaxBars` stratégie sú v baroch a vypchávka by ich posunula. Je to to isté
pravidlo, akým `dukas_import` zahadzuje vypchávku Dukascopy exportu.
"""

from __future__ import annotations

__all__ = ["AGG", "WEEK_MINUTES", "resample_ohlcv", "timeframe_minutes"]

#: Jednotky, v ktorých sa timeframe zapisuje. Jedno miesto pre celý repozitár —
#: adaptéry aj nástroje inak parsovali len `…m` a na `4h` padali.
_UNIT_MINUTES = {"m": 1, "h": 60, "d": 1440, "w": 10080}


def timeframe_minutes(timeframe: str) -> int:
    """`4h` → 240, `1d` → 1440, `1w` → 10080."""
    tf = str(timeframe).strip().lower()
    unit = _UNIT_MINUTES.get(tf[-1:])
    if unit is None or not tf[:-1].isdigit():
        raise ValueError(f"neznamy timeframe: {timeframe!r}")
    return int(tf[:-1]) * unit


#: Ako sa agregujú stĺpce sviečky pri skladaní vyššieho TF.
AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


#: Týždeň sa nezarovnáva od epochy, ale na pondelok — tak ho ukazujú burzy aj
#: TradingView. 1. 1. 1970 bol štvrtok, takže `origin="epoch"` by dal týždne od štvrtka.
#: Prvý pondelok po epoche je 5. 1. 1970; pre kratšie TF sa tým nič nemení (posun sú
#: presne 4 dni, teda násobok každého z nich), preto sa použije len pre týždeň.
WEEK_MINUTES = 7 * 24 * 60
_WEEK_ORIGIN = "1970-01-05"


def resample_ohlcv(df, minutes: int):
    """1m sviečky (`date`, o/h/l/c/v) → `minutes`-minútové. `minutes <= 1` vráti vstup."""
    if minutes <= 1:
        return df.reset_index(drop=True)
    origin = "epoch"
    if minutes % WEEK_MINUTES == 0:
        import pandas as pd

        origin = pd.Timestamp(_WEEK_ORIGIN, tz="UTC")
    return (
        df.set_index("date")
        .resample(f"{minutes}min", label="left", closed="left", origin=origin)
        .agg(AGG)
        .dropna(subset=["open"])
        .reset_index()
    )
