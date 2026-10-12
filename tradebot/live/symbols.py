"""Symbol a TF nasadenia z profilu stratégie — „Nasadiť“ ich nepotrebuje zadávať ručne.

    deploy_defaults("ninjatrader", "mnq_databento", "1m", existing=["MNQ 12-26"])
    # {"symbol": "MNQ 12-26", "tf": 1, "symbol_from": "účet", ...}

Profil nesie `_instrument` (kľúč v `INSTRUMENTS`, napr. `mnq_databento` → `MNQ/USD`) a `_timeframe`
(`1m`, `15m`). Platforma chce symbol po svojom:

- **NinjaTrader** celý názov kontraktu `MNQ 12-26` (master + expirácia). Kvartálne futures CME
  (indexy, menové) dostanú front-month; roll 8 dní pred tretím piatkom mesiaca expirácie (ako
  rollover NinjaTraderu). Iné kontrakty (MGC, CL — mesačné) sa hádať nedajú.
- **MetaTrader 5** meno symbolu u brokera — z Dukascopy CFD sa vezme jeho meno (`NAS100`, `EURUSD`,
  `XAU/USD` → `XAUUSD`); futures z Databento meno brokera nemajú.

Prvé slovo má vždy to, čo už na tom istom účte beží s rovnakým základom (`existing`) — broker aj
expiráciu vtedy niekto overil. Keď sa symbol odvodiť nedá, je `None` a formulár ho pýta.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Iterable

__all__ = ["front_month", "platform_symbol", "profile_tf", "deploy_defaults", "QUARTERLY_CME"]

#: Kvartálne (H, M, U, Z) futures CME, ktoré NinjaTrader pomenúva `MASTER MM-YY`.
QUARTERLY_CME = frozenset({
    "ES", "MES", "NQ", "MNQ", "RTY", "M2K", "YM", "MYM", "EMD",
    "6E", "M6E", "6B", "M6B", "6J", "6A", "M6A", "6C", "6S", "6N",
})
_QUARTER_MONTHS = (3, 6, 9, 12)
#: Toľko dní pred tretím piatkom expirácie NinjaTrader prechádza na ďalší kontrakt.
ROLL_DAYS = 8


def _third_friday(year: int, month: int) -> _dt.date:
    first = _dt.date(year, month, 1)
    return first + _dt.timedelta(days=(4 - first.weekday()) % 7 + 14)


def front_month(master: str, today: _dt.date | None = None) -> str:
    """`MNQ` → `MNQ 12-26` (12. 10. 2026); od roll dňa už ďalší kvartál."""
    today = today or _dt.date.today()
    year = today.year
    while True:
        for month in _QUARTER_MONTHS:
            if today < _third_friday(year, month) - _dt.timedelta(days=ROLL_DAYS):
                return f"{master} {month:02d}-{year % 100:02d}"
        year += 1


def _base(symbol: str) -> tuple[str, str]:
    """`MNQ/USD` → (`MNQ`, `USD`); `SYNTH/USDT:USDT` → (`SYNTH`, `USDT`)."""
    base, _, quote = str(symbol or "").partition("/")
    return base.strip().upper(), quote.split(":")[0].strip().upper()


def _master(platform: str, symbol: str) -> str:
    """Čím sa dva symboly platformy porovnajú: NT master (`MNQ 12-26` → `MNQ`), MT5 celé meno."""
    text = str(symbol or "").strip().upper()
    return text.split()[0] if platform == "ninjatrader" and text.split() else text


def platform_symbol(platform: str, instrument: Any, existing: Iterable[str] = (),
                    today: _dt.date | None = None) -> tuple[str | None, str]:
    """(symbol, odkiaľ) pre platformu z `InstrumentSpec` (alebo `None`); `(None, dôvod)`, keď sa nedá."""
    if instrument is None:
        return None, "profil nemá inštrument (_instrument)"
    base, quote = _base(getattr(instrument, "symbol", ""))
    source = str(getattr(instrument, "source", "") or getattr(instrument, "venue", "") or "")
    if platform == "mt5":
        guess = base + quote if (source == "dukascopy" and len(base) == 3 and base.isalpha() and len(quote) == 3) else base
    else:
        guess = base
    for sym in existing:
        if sym and _master(platform, sym) in (guess, base):
            return str(sym).strip(), "účet"
    if platform == "ninjatrader":
        if base in QUARTERLY_CME:
            return front_month(base, today), "front-month"
        return None, f"{base} nie je kvartálny kontrakt CME — zadaj symbol s expiráciou (napr. {base} 12-26)"
    if platform == "mt5":
        if source == "dukascopy":
            return guess, "profil"
        return None, f"{base} ({source or 'futures'}) nemá meno u MT5 brokera — zadaj symbol (napr. NAS100)"
    return (guess or None), "profil"


def profile_tf(timeframe: Any) -> int | None:
    """`_timeframe` profilu (`3m`, `1h`) na minúty; neznámy/prázdny = `None`."""
    if not timeframe:
        return None
    from tradebot.core.candles import timeframe_minutes

    try:
        return timeframe_minutes(str(timeframe))
    except ValueError:
        return None


def deploy_defaults(platform: str, instrument_key: str | None, timeframe: Any, existing: Iterable[str] = (),
                    today: _dt.date | None = None) -> dict[str, Any]:
    """Symbol a TF nasadenia z profilu (`_instrument`, `_timeframe`) pre platformu účtu."""
    from tradebot.core.types import INSTRUMENTS

    inst = INSTRUMENTS.get(instrument_key) if instrument_key else None
    symbol, why = platform_symbol(platform, inst, existing, today)
    tf = profile_tf(timeframe)
    return {"symbol": symbol, "symbol_from": why if symbol else None, "symbol_error": None if symbol else why,
            "tf": tf, "tf_error": None if tf else "profil nemá _timeframe — zadaj TF",
            "instrument": instrument_key or None}
