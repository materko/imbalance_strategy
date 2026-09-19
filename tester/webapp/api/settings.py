"""Overenie zadania behu z formulára a poskladanie jeho `settings`.

Spoločné pre jeden beh, sweep, hyperopt, maticu, prípravu analytiky aj beh na hube.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import STRATEGIES, get_spec

from .. import chart as chart_data
from ... import engines
from ..runner import check_market_rules, instrument_for_pair, tf_minutes
from .models import RunRequest


TIMERANGE_RE = re.compile(r"^\d{8}-\d{8}$")


def ai_for(ai: dict[str, Any] | None, strategy: str) -> dict[str, Any] | None:
    """Overí zadanie AI vrstvy. `None` alebo bez `enabled` = vypnutá."""
    from tradebot.strategies.hyperopt import StrategyHyperopt

    if not ai or not ai.get("enabled"):
        return None
    povolene = (get_spec(strategy).hyperopt_cls or StrategyHyperopt).ai_adjustable()
    adjust = {}
    for kluc, rozsah in (ai.get("adjust") or {}).items():
        if kluc not in povolene:
            raise HTTPException(422, f"{kluc!r} sa modelom meniť nedá; stratégia "
                                     f"{strategy} dovolí: {', '.join(povolene)}")
        try:
            a, b = (float(x) for x in rozsah)
        except (TypeError, ValueError):
            raise HTTPException(422, f"{kluc}: rozsah musí byť dvojica čísel")
        if a <= 0 or b <= 0:
            raise HTTPException(422, f"{kluc}: násobok musí byť kladný")
        adjust[kluc] = [a, b]
    cisla = {k: ai[k] for k in ("min_probability", "train_period_days",
                                "backtest_period_days", "model") if ai.get(k) is not None}
    return {"enabled": True, **cisla, **({"adjust": adjust} if adjust else {})}

def fee_for(fee: float | None, pair: str, timeframe: str, timerange: str) -> dict[str, Any]:
    """`{"fee": …, "fee_note": …}` — zadané číslo, alebo náklad toho trhu."""
    from ... import fees as fees_mod

    if fee is not None:
        return {"fee": fee, "fee_note": "zadané vo formulári"}
    hodnota, note = fees_mod.for_pair(pair, timeframe, timerange)
    if hodnota is None:
        return {"fee": 0.0, "fee_note": f"neznámy: {note}"}
    return {"fee": hodnota, "fee_note": note}

def run_settings(req: RunRequest) -> dict[str, Any]:
    """Overí zadanie a poskladá `settings` behu. Spoločné pre jeden beh aj pre sweep."""
    if not TIMERANGE_RE.match(req.timerange):
        raise HTTPException(422, "timerange musí byť YYYYMMDD-YYYYMMDD")
    a, b = req.timerange.split("-")
    if a >= b:
        raise HTTPException(422, "začiatok obdobia musí byť pred koncom")
    if req.strategy not in STRATEGIES:
        raise HTTPException(422, f"neznáma stratégia {req.strategy!r}; známe: {sorted(STRATEGIES)}")
    if req.timeframe not in chart_data.TIMEFRAMES:
        raise HTTPException(422, f"timeframe {req.timeframe!r} nie je podporovaný ({', '.join(chart_data.TIMEFRAMES)})")
    if req.timeframe not in chart_data.available_timeframes(req.pair):
        raise HTTPException(422, f"pre {req.pair} nie sú stiahnuté {req.timeframe} dáta")
    detail = req.timeframe_detail or None
    if detail and tf_minutes(detail) >= tf_minutes(req.timeframe):
        detail = None  # detail fillov musí byť jemnejší než TF grafu, inak ho Freqtrade odmietne
    # Pravidlá trhu (spot: bez shortov a páky) sa kontrolujú skôr než engine —
    # nezmyselný beh má povedať, čo je zle na ňom, nie na výbere engine.
    try:
        check_market_rules(req.pair, req.params)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    try:
        inst = INSTRUMENTS[instrument_for_pair(req.pair)]
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    engine = req.engine or engines.default_engine(inst, req.timeframe)
    if engine not in engines.ENGINES:
        raise HTTPException(422, f"neznámy engine {engine!r}; známe: {', '.join(engines.ENGINES)}")
    exchange = req.exchange or engines.DEFAULT_EXCHANGE
    if engine == engines.FREQTRADE and exchange not in engines.EXCHANGES:
        raise HTTPException(422, f"neznáma burza {exchange!r}; známe: {', '.join(engines.EXCHANGES)}")
    possible = engines.available(inst, req.timeframe, exchange)
    if engine not in possible:
        preco = (engines.freqtrade_blocker(inst, req.timeframe, exchange)
                 if engine == engines.FREQTRADE else "chýbajú 1m sviečky")
        raise HTTPException(422, (
            f"engine {engines.ENGINE_TITLES[engine]} sa na {req.pair} {req.timeframe} "
            f"spustiť nedá ({preco}); dostupné: "
            f"{', '.join(engines.ENGINE_TITLES[e] for e in possible) or 'žiadne'}"))
    znacky = {k: getattr(req, k) for k in ("hyperopt_run", "plateau", "checkup", "matrix")
              if getattr(req, k, None)}
    return {
        **znacky,
        "strategy": req.strategy,
        "exchange": exchange if engine == engines.FREQTRADE else None,
        "sweep": req.sweep,
        "pair": req.pair,
        "engine": engine,
        "timeframe": req.timeframe,
        "timerange": req.timerange,
        # Jeden default pre vsetky trhy nefunguje: 0,05 % je Binance taker, kym na
        # CFD je provizia drobna a naklad je spread. Bez zadaneho `fee` sa berie
        # naklad instrumentu a ulozi sa aj to, odkial cislo je.
        **fee_for(req.fee, req.pair, req.timeframe, req.timerange),
        "ai": ai_for(req.ai, req.strategy),
        "wallet": req.wallet,
        "timeframe_detail": detail,
        "profile": req.profile,
    }
