"""Základné čísla nad obchodmi: hrubý zisk, objem, break-even poplatok, winrate.
"""

from __future__ import annotations

from typing import Any, Sequence


def gross_and_volume(trades: Sequence[dict[str, Any]]) -> tuple[float, float]:
    """Hrubý zisk z cien a obchodovaný objem v mene účtu — základ break-even poplatku.

    Z cien, nie z `profit_abs`: skóre tak nezávisí od toho, s akým `--fee` beh bežal.
    S hodnotou bodu záznamu — jediná definícia je `tradebot.core.money`.
    """
    from tradebot.core.money import gross_and_volume as _gv

    return _gv(trades)


def break_even_pct(trades: Sequence[dict[str, Any]]) -> float | None:
    """Koľko smie burza brať na stranu, aby tieto obchody vyšli na nulu (v %)."""
    gross, volume = gross_and_volume(trades)
    return None if volume <= 0 else round(gross / volume * 100.0, 4)


def _winrate(trades: Sequence[dict[str, Any]]) -> float | None:
    if not trades:
        return None
    return round(sum(1 for t in trades if float(t.get("profit_abs") or 0) > 0) / len(trades) * 100, 2)
