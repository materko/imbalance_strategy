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
    for name in ("app.js", "app.css"):
        try:
            stamp = max(stamp, (STATIC / name).stat().st_mtime)
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
