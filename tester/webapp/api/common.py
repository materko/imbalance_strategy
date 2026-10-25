"""Pomocné funkcie a konštanty zdieľané routermi webapp."""

from __future__ import annotations

import os
from collections import OrderedDict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from tradebot.core.env import getenv

from .. import gitsync
from ... import montecarlo


STATIC = Path(__file__).resolve().parent.parent / "static"

#: Meraný čas jedného roka backtestu s 1m detailom na tomto stroji (~30 s).
#: Slúži len na odhad „ako dlho to pobeží", nie na rozhodovanie.
SECONDS_PER_YEAR = 30


#: Posledné výsledky Monte Carla. Beh sa po dokončení už nemení, takže rovnaký dopyt
#: dá vždy to isté (seed je fixný) — a pri behu s tisíckami obchodov to trvá sekundy.
_MC_CACHE: "OrderedDict[tuple, dict[str, Any]]" = OrderedDict()
_MC_CACHE_MAX = 32


def montecarlo_cached(run_id: str, trades: list[dict[str, Any]], opts: dict[str, Any]) -> dict[str, Any]:
    key = (run_id, *(round(v, 6) if isinstance(v, float) else v for v in opts.values()))
    if key not in _MC_CACHE:
        result = montecarlo.analyze(trades, **opts)
        result["run_id"] = run_id
        _MC_CACHE[key] = result
        while len(_MC_CACHE) > _MC_CACHE_MAX:
            _MC_CACHE.popitem(last=False)
    _MC_CACHE.move_to_end(key)
    return _MC_CACHE[key]


def asset_version() -> str:
    """Odtlačok skriptu a štýlov — mení sa s každou zmenou súboru, inak je stály."""
    stamp = 0.0
    for path in (STATIC / "app.css", *(STATIC / "js").glob("*.js")):
        try:
            stamp = max(stamp, path.stat().st_mtime)
        except OSError:
            continue
    return format(int(stamp), "x")


def current_user() -> str:
    return getenv("USER") or gitsync.user_name() or os.environ.get("USERNAME", "") or "tester"


def plateau_note() -> str:
    return ("Susedia víťaza: o krok a o dva kroky na každom ladenom parametri. Plató znamená, "
            "že presná hodnota nie je kritická; špička, že optimum je tvar toho okna.")


def null_note(vysledky: dict[str, Any]) -> str:
    """Rozdiel medzi dvoma náhodami je hodnota samotného výberu času.

    Keď je stratégia výrazne lepšia než náhoda kedykoľvek, ale nie než náhoda v tých
    istých hodinách, celý jej edge je v tom, KEDY obchoduje — a to sa dá mať aj bez nej.
    """
    kedykolvek = (vysledky.get("anytime") or {}).get("sigma")
    v_seanse = (vysledky.get("session") or {}).get("sigma")
    if kedykolvek is None or v_seanse is None:
        return ""
    if kedykolvek - v_seanse > 1.0:
        return ("Proti náhode kedykoľvek je stratégia výrazne lepšia, proti náhode v tých "
                "istých hodinách už nie — väčšina jej edge je v tom, KEDY obchoduje, "
                "nie na čom vstupuje.")
    return ("Obe náhody dávajú podobný výsledok, takže edge nie je len o výbere času — "
            "je v tom, na čom stratégia vstupuje.")


def goal_note(goal: str, max_dd: float | None, min_trades: int | None) -> str:
    """Zadanie ako veta — to isté pre sweep aj hyperopt, aby sa nedali rozísť."""
    from ... import sweep as sweep_mod

    return sweep_mod.describe(goal, max_dd, min_trades)


def fmt_value(value: Any) -> str:
    """Hodnota bodu mriežky do poznámky behu."""
    if isinstance(value, dict):
        return f"{value.get('value')}@{value.get('unit')}"
    return f"{value:g}" if isinstance(value, float) else str(value)


def clean_user(name: str | None) -> str:
    name = (name or "").strip()
    return name[:80] if name else current_user()


def market_config_key(rec: dict[str, Any]) -> str:
    """Konfigurácia = parametre + trh + TF: analytika (náhoda, charakter, dĺžka
    v baroch) je párová a limity v baroch znamenajú na inom TF inú stratégiu,
    takže ten istý profil na inom trhu alebo TF je iný výber."""
    from ... import analytics as an

    s = rec.get("settings") or {}
    return f"{an.config_key(rec)}|{s.get('pair') or '?'}|{s.get('timeframe') or '?'}"


def default_timerange(pairs: list[dict[str, Any]]) -> str:
    """Posledných 365 dní dostupných dát — rozumný štart pre tabuľku."""
    to = max((p["to"] for p in pairs), default=str(date.today()))
    end = datetime.strptime(to, "%Y-%m-%d")
    start = end - timedelta(days=365)
    return f"{start:%Y%m%d}-{end:%Y%m%d}"


def hyperopt_settings(req: Any, base: dict[str, Any]) -> dict[str, Any]:
    """`settings.hyperopt` zo zadania formulára — to isté pre lokálnu frontu aj hub.

    Na emulátore MultiCharts Freqtrade nebeží; epochy tam počíta C# jadro stratégie
    (`tester.native_hyperopt`), takže stratégia bez neho sa tam ladiť nedá.
    """
    from fastapi import HTTPException

    from tradebot.strategies import get_spec

    from ... import engines
    from ...native_hyperopt import SAMPLERS

    sampler = getattr(req, "sampler", None) or None
    if sampler is not None and sampler not in SAMPLERS:
        raise HTTPException(422, f"neznámy sampler {sampler!r}; známe: {', '.join(SAMPLERS)}")
    native = base.get("engine") == engines.MULTICHARTS
    if native and sampler is None:
        sampler = "tpe"
    if native and getattr(get_spec(req.strategy).engine_factory, "csharp_key", None) is None:
        raise HTTPException(422, (
            f"hyperopt na emulátore MultiCharts vie len stratégia s C# jadrom (napr. {req.strategy}net); "
            f"{req.strategy} sa dá ladiť cez Freqtrade"))
    from ...native_hyperopt import AGGREGATES, OBJECTIVES, SELECTS
    from .settings import TIMERANGE_RE

    windows = [w.strip() for w in (getattr(req, "windows", None) or []) if w and w.strip()]
    objectives = [o for o in (getattr(req, "objectives", None) or []) if o and o != req.goal]
    aggregate = getattr(req, "aggregate", None) or "min"
    select = getattr(req, "select", None) or "best"
    mode = getattr(req, "mode", None) or "search"
    anchored = bool(getattr(req, "anchored", False))
    continue_from = getattr(req, "continue_from", None) or None
    for w in windows:
        if not TIMERANGE_RE.match(w) or w.split("-")[0] >= w.split("-")[1]:
            raise HTTPException(422, f"okno {w!r} musí byť YYYYMMDD-YYYYMMDD so začiatkom pred koncom")
    if aggregate not in AGGREGATES:
        raise HTTPException(422, f"neznáme skladanie okien {aggregate!r}; známe: {', '.join(AGGREGATES)}")
    for o in objectives:
        if o not in OBJECTIVES:
            raise HTTPException(422, f"neznámy cieľ {o!r}; známe: {', '.join(OBJECTIVES)}")
    if select not in SELECTS:
        raise HTTPException(422, f"neznámy výber víťaza {select!r}; známe: {', '.join(SELECTS)}")
    if mode not in ("search", "walkforward"):
        raise HTTPException(422, f"neznámy režim {mode!r}; známe: search, walkforward")
    if native and objectives and sampler == "cmaes":
        raise HTTPException(422, "CMA-ES vie len jeden cieľ; pre viac cieľov zvoľ NSGA-II alebo TPE")
    if not native and "break_even" in objectives:
        raise HTTPException(422, "break-even ako ďalší cieľ Freqtrade epocha nenesie — daj ho ako „Vybrať podľa\"")
    if mode == "walkforward" and objectives:
        raise HTTPException(422, "walk-forward s viacerými cieľmi nie je — zvoľ jedno")
    return {
        "knobs": dict(req.space), "goal": req.goal, "max_dd": req.max_dd,
        "min_trades": req.min_trades, "epochs": req.epochs, "seed": req.seed,
        "verify": req.verify, "native": native, "sampler": sampler,
        "windows": windows or None, "aggregate": aggregate, "objectives": objectives or None, "select": select,
        "mode": mode, "anchored": anchored if mode == "walkforward" else False, "continue_from": continue_from,
    }
