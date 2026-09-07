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

__all__ = ["AGG", "resample_ohlcv"]

#: Ako sa agregujú stĺpce sviečky pri skladaní vyššieho TF.
AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}


def resample_ohlcv(df, minutes: int):
    """1m sviečky (`date`, o/h/l/c/v) → `minutes`-minútové. `minutes <= 1` vráti vstup."""
    if minutes <= 1:
        return df.reset_index(drop=True)
    return (
        df.set_index("date")
        .resample(f"{minutes}min", label="left", closed="left", origin="epoch")
        .agg(AGG)
        .dropna(subset=["open"])
        .reset_index()
    )
