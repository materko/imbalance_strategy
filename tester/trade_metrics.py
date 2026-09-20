"""Základné čísla nad obchodmi: hrubý zisk, objem, break-even poplatok, winrate, série.
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


#: Čo z obchodu ide do výpisu série — toľko, aby sa dal prečítať bez `trades.json`.
STREAK_COLS = ("open_date", "close_date", "profit_abs", "profit_ratio", "exit_reason")


def streaks_with_trades(trades: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Najdlhšia séria ziskov a strát (`tradebot.core.money`) aj s obchodmi, z ktorých je.

    Analytika zlieva obchody z viacerých behov, takže index do „obchodov behu" tu nič
    neznamená — séria si preto nesie svoje obchody. Poradie je poradie zatvorenia:
    séria cez dve prekrývajúce sa okná by inak bola sériou v poradí načítania behov.
    """
    from tradebot.core.money import streaks

    rows = sorted(trades, key=lambda t: str(t.get("close_date") or ""))
    out = streaks(rows)
    for s in out.values():
        if s is None:
            continue
        od, do = s.pop("from_i"), s.pop("to_i")
        s["trades"] = [{k: t.get(k) for k in STREAK_COLS} for t in rows[od:do + 1]]
    return out
