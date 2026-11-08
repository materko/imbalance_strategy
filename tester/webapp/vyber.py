"""Výber stratégií a profilov, ktoré webapp ukazuje (`tester/webapp_vyber.json`).

Používateľ 8. 11. 2026: vo webapp majú byť len stratégie s C# jadrom zo stránky výsledkov a pri každej len
najlepšie nastavenia zo stránky (top 3) plus profily, na ktoré sa odvolávajú živé nasadenia. Súbor je
``{"strategies": {"<kľúč>": ["<profil>", …]}}``; čo v ňom nie je, sa skryje (nič sa nemaže — profily
aj behy ostávajú na disku a v gite). Bez súboru (alebo s chybným) webapp ukáže všetko ako predtým.
"""

from __future__ import annotations

import json
from typing import Any

from tradebot.core.paths import WEBAPP_SELECTION

_cache: tuple[int, dict[str, list[str]] | None] | None = None


def selection() -> dict[str, list[str]] | None:
    """Stratégia → povolené profily; `None` = bez výberu (všetko viditeľné)."""
    global _cache
    try:
        mtime = WEBAPP_SELECTION.stat().st_mtime_ns
    except OSError:
        return None
    if _cache is None or _cache[0] != mtime:
        try:
            data: Any = json.loads(WEBAPP_SELECTION.read_text(encoding="utf-8"))
            sel = {str(k): [str(p) for p in v] for k, v in (data.get("strategies") or {}).items()}
        except (OSError, ValueError, AttributeError, TypeError):
            sel = None
        _cache = (mtime, sel)
    return _cache[1]


def version() -> str:
    try:
        return str(WEBAPP_SELECTION.stat().st_mtime_ns)
    except OSError:
        return "0"


def strategy_visible(key: str) -> bool:
    sel = selection()
    return sel is None or key in sel


def profile_visible(key: str, name: str) -> bool:
    sel = selection()
    return sel is None or name in sel.get(key, ())


def filter_names(key: str, names: list[str]) -> list[str]:
    sel = selection()
    if sel is None:
        return names
    allowed = sel.get(key, [])
    return [n for n in names if n in allowed]


def filter_map(key: str, items: dict[str, Any]) -> dict[str, Any]:
    sel = selection()
    if sel is None:
        return items
    allowed = sel.get(key, [])
    return {n: v for n, v in items.items() if n in allowed}
