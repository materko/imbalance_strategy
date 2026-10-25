"""Natívne behy C# stratégií bez histórie (`/api/native/*`) — pre AI a skripty, ktoré potrebujú veľa behov rýchlo.

`POST /api/native/backtests` spočíta body × okná na pracovných procesoch C# (`tester.native`) a vráti súhrn
každého behu tými istými funkciami, akými ho počíta história (`summary_money`). Nič sa neukladá — kto chce
výsledok v histórii, pustí obyčajný beh, sweep alebo hyperopt.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES, get_spec

from .context import AppContext
from .models import NativeBacktestRequest
from .settings import TIMERANGE_RE, fee_for


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()

    @router.get("/api/native/status")
    def native_status():
        """Pracovné procesy C# (strop, požičané, voľné) a stratégie, ktoré vedia bežať natívne."""
        from ... import native

        return {"pool": native.POOL.stats(),
                "strategies": sorted(k for k in STRATEGIES if native.csharp_key(k) is not None)}

    @router.post("/api/native/backtests")
    def native_backtests(req: NativeBacktestRequest):
        """Body × okná natívne, bez histórie. Odpoveď: `results[i] = {point, values, window, summary[, trades]}`."""
        import json

        from tradebot.core import load_profile
        from tradebot.core.candles import timeframe_minutes
        from tradebot.core.types import INSTRUMENTS

        from ... import engines, native
        from ...hyperopt import REFERENCE_WINDOWS
        from ..market import instrument_for_pair

        if req.strategy not in STRATEGIES:
            raise HTTPException(422, f"neznáma stratégia {req.strategy!r}")
        if native.csharp_key(req.strategy) is None:
            raise HTTPException(422, f"{req.strategy} nemá C# jadro — natívne behy vedia len stratégie …net")
        try:
            inst = INSTRUMENTS[instrument_for_pair(req.pair)]
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        spec = get_spec(req.strategy)
        tf = req.timeframe or spec.default_timeframe
        okna = req.windows or list(REFERENCE_WINDOWS)
        for w in okna:
            if not TIMERANGE_RE.match(w):
                raise HTTPException(422, f"okno {w!r} musí byť YYYYMMDD-YYYYMMDD")
        if len(req.points) * len(okna) > 20000:
            raise HTTPException(422, "najviac 20 000 behov (body × okná) v jednej dávke")
        try:
            cfg, _ = load_profile(req.profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
            zaklad = {**cfg.to_dict(), **{k: v for k, v in (req.params or {}).items() if not k.startswith("_")}}
            configs = [json.dumps(spec.config_cls.from_dict({**zaklad, **bod}).to_dict()) for bod in req.points]
        except (ConfigError, ValueError, TypeError, FileNotFoundError) as exc:
            raise HTTPException(422, str(exc))
        fee = fee_for(req.fee, req.pair, tf, okna[0])["fee"]
        try:
            runner = native.NativeRunner(req.strategy, inst, timeframe_minutes(tf), fee)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(422, str(exc))
        t0 = time.perf_counter()
        ulohy = [(c, w) for c in configs for w in okna]
        vysledky = runner.run_many(ulohy)
        out: list[dict[str, Any]] = []
        for i, ((_c, w), res) in enumerate(zip(ulohy, vysledky)):
            bod = i // len(okna)
            row: dict[str, Any] = {"point": bod, "values": req.points[bod], "window": w}
            if "error" in res:
                row["error"] = res["error"]
            else:
                summary = native.summary_of(res, inst, fee, req.wallet)
                row["summary"] = {k: v for k, v in (summary or {}).items() if k not in ("exits", "streaks")}
                if req.trades:
                    from tradebot.adapters.multicharts.emulator import rows_from_trades

                    row["trades"] = rows_from_trades(native.emulation_of(res).trades, inst, fee)
            out.append(row)
        return {"strategy": req.strategy, "pair": req.pair, "timeframe": tf, "fee": fee, "windows": okna,
                "runs": len(ulohy), "seconds": round(time.perf_counter() - t0, 3), "results": out}

    return router
