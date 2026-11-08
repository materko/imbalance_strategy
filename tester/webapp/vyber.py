"""Výber stratégií a profilov, ktoré webapp ukazuje (`tester/webapp_vyber.json`).

Používateľ 8. 11. 2026: navrchu webapp sú stratégie s C# jadrom zo stránky výsledkov a pri každej len najlepšie
nastavenia zo stránky (top 3) plus profily, na ktoré sa odvolávajú živé nasadenia; ostatné stratégie sú celkom dole
so všetkými profilmi. Súbor je ``{"strategies": {"<kľúč>": ["<profil>", …]}}``: pri stratégii v ňom sa ukážu len
vymenované profily, stratégia mimo neho ide na koniec. Pri stratégii v ``"dole"`` (ostatné stratégie, len ich
najlepšie 3 profily s analytikou) sa tiež ukážu len vymenované profily, ale stratégia ostáva dole. Bez súboru
(alebo s chybným) je všetko ako predtým.
"""

from __future__ import annotations

import json
from typing import Any

from tradebot.core.paths import WEBAPP_SELECTION

_cache: tuple[int, tuple[dict[str, list[str]], dict[str, list[str]]] | None] | None = None


def selection() -> dict[str, list[str]] | None:
    """Stratégie navrchu → povolené profily; `None` = bez výberu (všetko viditeľné)."""
    both = _load()
    return both[0] if both else None


def _profiles() -> dict[str, list[str]] | None:
    """Stratégia → povolené profily (navrchu aj dole); `None` = bez výberu."""
    both = _load()
    return {**both[1], **both[0]} if both else None


def _load():
    global _cache
    try:
        mtime = WEBAPP_SELECTION.stat().st_mtime_ns
    except OSError:
        return None
    if _cache is None or _cache[0] != mtime:
        try:
            data: Any = json.loads(WEBAPP_SELECTION.read_text(encoding="utf-8"))
            sel = ({str(k): [str(p) for p in v] for k, v in (data.get("strategies") or {}).items()},
                   {str(k): [str(p) for p in v] for k, v in (data.get("dole") or {}).items()})
        except (OSError, ValueError, AttributeError, TypeError):
            sel = None
        _cache = (mtime, sel)
    return _cache[1]


def version() -> str:
    try:
        return str(WEBAPP_SELECTION.stat().st_mtime_ns)
    except OSError:
        return "0"


def selected(key: str) -> bool:
    """Stratégia patrí navrch (je vo výbere, alebo výber nie je)."""
    sel = selection()
    return sel is None or key in sel


def profile_visible(key: str, name: str) -> bool:
    sel = _profiles()
    return sel is None or key not in sel or name in sel[key]


def filter_names(key: str, names: list[str]) -> list[str]:
    """Pri stratégii vo výbere (navrchu aj dole) len jej vymenované profily; ostatné všetky."""
    sel = _profiles()
    if sel is None or key not in sel:
        return names
    return [n for n in names if n in sel[key]]


def filter_map(key: str, items: dict[str, Any]) -> dict[str, Any]:
    sel = _profiles()
    if sel is None or key not in sel:
        return items
    return {n: v for n, v in items.items() if n in sel[key]}


def ordered(keys: list[str]) -> list[str]:
    """Najprv stratégie vo výbere, potom ostatné (každá skupina v pôvodnom poradí)."""
    return [k for k in keys if selected(k)] + [k for k in keys if not selected(k)]
