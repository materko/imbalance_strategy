"""Sviečkové patterny pre Pin Bar a Engulfing entry model.

Repliky Pine `f_isPinBar` (riadok 603) a `f_isEngulfing` (riadok 631).

Pozor pri Engulfingu: napriek názvu to **nie je** klasický geometrický engulfing.
Používateľ si to zmenil na jednoduchšie a spoľahlivejšie kritérium — sviečka je
„engulfing", keď je jej rozsah výrazný **outlier** voči priemeru posledných
`engSizeAvgLen` sviečok. Rovnaký princíp ako volume filter, len na rozsahu.
"""

from __future__ import annotations

from ..config import IBSConfig
from ..history import BarHistory
from ..types import Bar, Direction, InstrumentSpec

__all__ = ["is_pin_bar", "is_engulfing"]


def is_pin_bar(
    bar: Bar,
    direction: Direction,
    cfg: IBSConfig,
    inst: InstrumentSpec,
    *,
    atr: float = 0.0,
) -> bool:
    """Pine `f_isPinBar(dir)`.

    Tri podmienky naraz:
      * celkový rozsah sviečky ≥ `pbMinRangePoints` (filter proti šumu),
      * knôt v smere vstupu ≥ `pbWickToBodyRatio` × telo,
      * telo je v okrajovej časti rozsahu (≤ `pbBodyPositionPct` % od správneho okraja).

    Sviečka bez tela (`bodyLen <= 0`) prejde podmienkou knôta automaticky — presne
    ako v Pine, kde je to ošetrené vetvou ``bodyLen <= 0 or ...``.
    """
    rng = bar.high - bar.low
    body_top = bar.body_top
    body_bot = bar.body_bottom
    body_len = body_top - body_bot
    upper_wick = bar.high - body_top
    lower_wick = body_bot - bar.low

    min_range = cfg.pbMinRangePoints.resolve(inst, price=bar.close, atr=atr)
    if rng < min_range:
        return False

    if direction is Direction.LONG:
        wick_ok = body_len <= 0 or lower_wick >= body_len * cfg.pbWickToBodyRatio
    else:
        wick_ok = body_len <= 0 or upper_wick >= body_len * cfg.pbWickToBodyRatio
    if not wick_ok:
        return False

    pos_limit = rng * (cfg.pbBodyPositionPct / 100.0)
    if direction is Direction.LONG:
        return (bar.high - body_top) <= pos_limit
    return (body_bot - bar.low) <= pos_limit


def is_engulfing(
    history: BarHistory,
    direction: Direction,
    cfg: IBSConfig,
    inst: InstrumentSpec,
    *,
    atr: float = 0.0,
) -> bool:
    """Pine `f_isEngulfing(dir)` — „outlier" sviečka, nie geometrický engulfing.

    Priemerný rozsah sa v Pine počíta na top-level cez ``ta.sma(high - low,
    engSizeAvgLen)``, teda **vrátane aktuálnej sviečky**.
    """
    bar = history.current
    rng = bar.high - bar.low

    min_range = cfg.engMinRangePoints.resolve(inst, price=bar.close, atr=atr)
    if rng < min_range:
        return False

    color_ok = bar.close > bar.open if direction is Direction.LONG else bar.close < bar.open
    if not color_ok:
        return False

    avg_range = history.sma_range(cfg.engSizeAvgLen)
    if avg_range <= 0:
        return False
    return rng >= cfg.engSizeMultiplier * avg_range
