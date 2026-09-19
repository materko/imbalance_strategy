"""Prevody DataFrame Freqtradu, ktoré potrebuje adaptér na viacerých miestach."""

from __future__ import annotations


def _ts_ms(series) -> list[int]:
    """Stĺpec `date` → ms epoch.

    Freqtrade drží `date` ako **datetime64[ms]**, takže `.astype("int64")` vráti
    milisekundy — zatiaľ čo `Timestamp.value` vracia nanosekundy vždy. Tie dve cesty
    sa líšia o 10^6 a keď sa zmiešajú, kľúče sa nikdy netrafia a stratégia ticho
    nevygeneruje ani jeden signál. Preto sa prevod robí na jednom mieste.
    """
    return (series.astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()


def _between(frame, since_ms: int, until_ms: int):
    """Riadky `frame` s `date` v `[since_ms, until_ms)` (OHLCV stĺpce), alebo None."""
    if frame is None or len(frame) == 0:
        return None
    import pandas as pd

    dates = pd.to_datetime(frame["date"], utc=True)
    lo = pd.Timestamp(int(since_ms), unit="ms", tz="UTC")
    hi = pd.Timestamp(int(until_ms), unit="ms", tz="UTC")
    part = frame.loc[((dates >= lo) & (dates < hi)).to_numpy(),
                     ["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
    return part if len(part) else None
