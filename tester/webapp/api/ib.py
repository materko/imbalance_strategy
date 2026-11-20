"""Karta Initial Balance: štatistika prvej hodiny seansy ako IB Lab (`/api/ib/*`).

Výpočet je v `tester.initial_balance`; tu je len cache dní a preklad filtrov z adresy.
Riadky dní symbolu a seansy sa spočítajú raz (ES 2010–2026 ~8 s) a držia sa v pamäti, kým
sa nezmenia súbory v archíve; každý filter je potom len prechod cez ne (desiatky ms).
"""

from __future__ import annotations

import threading
from typing import Any

from fastapi import APIRouter, HTTPException

from .context import AppContext

#: (symbol, seansa) → (podpis súborov, riadky dní)
_CACHE: dict[tuple[str, str], tuple[tuple, list[dict[str, Any]]]] = {}
_LOCKS: dict[tuple[str, str], threading.Lock] = {}
_GUARD = threading.Lock()
#: koľko posledných vybraných dní ide do tabuľky
DAYS_TABLE = 60


def cached_days(symbol: str, session: str) -> list[dict[str, Any]]:
    from ... import initial_balance as ib

    key = (symbol.upper(), session)
    with _GUARD:
        lock = _LOCKS.setdefault(key, threading.Lock())
    with lock:  # dve karty naraz nepočítajú ten istý symbol dvakrát
        sig = ib.data_signature(symbol)
        hit = _CACHE.get(key)
        if hit and hit[0] == sig:
            return hit[1]
        days = ib.compute_days(ib.load_1m(symbol), session)
        _CACHE[key] = (sig, days)
        return days


def _ints(s: str) -> frozenset[int]:
    try:
        return frozenset(int(x) for x in s.split(",") if x.strip())
    except ValueError as e:
        raise HTTPException(422, f"čakal som čísla oddelené čiarkou: {s!r}") from e


def _strs(s: str) -> frozenset[str]:
    return frozenset(x.strip() for x in s.split(",") if x.strip())


def _check(name: str, value, allowed) -> None:
    if value not in allowed:
        raise HTTPException(422, f"{name}: {value!r} nie je z {', '.join(map(str, allowed))}")


def build(ctx: AppContext) -> APIRouter:  # karta nepotrebuje históriu behov ani bežce
    router = APIRouter()

    @router.get("/api/ib/meta")
    def ib_meta():
        """Symboly v archíve, seansy, pásma IB % a obdobia pre formulár karty."""
        from ... import initial_balance as ib

        return {"symbols": ib.symbols(),
                "sessions": {k: {"ib": [ib._hhmm(s.ib_start), ib._hhmm(s.ib_end)],
                                 "end": ib._hhmm(s.session_end)} for k, s in ib.SESSIONS.items()},
                "ib_bands": [b[2] for b in ib.IB_PCT_BANDS],
                "periods": list(ib.PERIODS),
                "cached": sorted(f"{k[0]}:{k[1]}" for k in _CACHE)}

    @router.get("/api/ib/summary")
    def ib_summary(symbol: str = "ES", session: str = "ny", scope: str = "pre", dir: str = "bull",
                   dow: int | None = None, bias: str = "all", bias_break: str = "with",
                   bands: str = "", close_bands: str = "", slots: str = "", slot_step: int = 5,
                   brk: str = "all", news: str = "all", period: str = "all", gran: int = 15):
        """Karty a rozdelenia pre zvolený filter + posledné vybrané dni (ako dashboard IB Lab)."""
        from ... import initial_balance as ib

        if symbol.upper() not in ib.symbols():
            raise HTTPException(404, f"{symbol!r}: v archíve nie sú 1m sviečky (máme {', '.join(ib.symbols())})")
        _check("session", session, tuple(ib.SESSIONS))
        _check("scope", scope, ("pre", "post"))
        _check("dir", dir, ("bull", "bear"))
        _check("bias", bias, ("all", "lowFirst", "highFirst"))
        _check("bias_break", bias_break, ("with", "against"))
        _check("brk", brk, ("all", "single", "double"))
        _check("news", news, ("all", "fomc", "cpi", "nfp", "holiday", "quiet"))
        _check("period", period, ib.PERIODS)
        _check("slot_step", slot_step, (5, 15, 30, 60))
        _check("gran", gran, (5, 15, 30, 60))
        if dow is not None:
            _check("dow", dow, (1, 2, 3, 4, 5))
        days = cached_days(symbol, session)
        flt = ib.Filter(scope=scope, dir=dir, dow=dow, bias=bias, bias_break=bias_break,
                        bands=_ints(bands), close_bands=_ints(close_bands), slots=_strs(slots),
                        slot_step=slot_step, brk=brk, news=news, period=period)
        sel = ib.select(days, flt)
        out = ib.summary(days, flt, session, gran)
        out.update(symbol=symbol.upper(), session=session, gran=gran, total=len(days),
                   first=days[0]["date"] if days else None, last=days[-1]["date"] if days else None,
                   selected=len(sel), days=sel[-DAYS_TABLE:][::-1])
        if news != "all":
            sets = ib._news_sets() or {}
            cov = sorted(sets.get("_coverage") or ())
            out["news_coverage"] = cov or None
        return out

    return router
