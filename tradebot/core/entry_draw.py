"""Kresba obchodu pri obaloch vstupov — aby graf ukazoval len obchody, ktoré naozaj vznikli.

Stratégia kreslí TP / SL boxy (`tp_box`, `sl_box`) a štítok vstupu (druh `…_entry`) na bare, na ktorom
pošle market vstup. Obal, ktorý vstup zmení (limitka, potvrdenie sviečkou) alebo zahodí (filter,
nevyplnená limitka), musí s kresbou urobiť to isté: posunúť ju na skutočný vstup a ceny, alebo ju zmazať.
Inak graf ukazuje obchody, ktoré neboli, a boxy na iných cenách než skutočný obchod.
"""

from __future__ import annotations

import copy
from typing import Any

from .drawing import DrawBox, DrawCommand, DrawDelete, DrawLabel, DrawUpdate

__all__ = ["trade_drawings", "relevel", "released", "moved", "deleted", "with_ids"]

_BOX_KINDS = ("tp_box", "sl_box")


def _is_trade(o: Any, bar_time: int) -> bool:
    if isinstance(o, DrawBox):
        return o.kind in _BOX_KINDS and o.x1_ms == bar_time and bool(o.obj_id)
    if isinstance(o, DrawLabel):
        return str(getattr(o.kind, "value", o.kind)).endswith("_entry") and o.x_ms == bar_time and bool(o.obj_id)
    return False


def trade_drawings(drawings: list[DrawCommand], bar_time: int) -> list[Any]:
    """Boxy a štítok vstupu, ktoré stratégia nakreslila na tomto bare."""
    return [o for o in drawings if _is_trade(o, bar_time)]


def relevel(objs: list[Any], plan: Any) -> None:
    """Boxy na ceny plánu (vstup → cieľ, vstup → stop); mení objekty na mieste."""
    for o in objs:
        if isinstance(o, DrawBox):
            level = plan.take_profit if o.kind == "tp_box" else plan.stop_loss
            o.y1, o.y2 = max(plan.entry, level), min(plan.entry, level)
            o.text = f"{'TP' if o.kind == 'tp_box' else 'SL'} {level:g}"


def released(objs: list[Any], t: int, plan: Any | None = None) -> list[DrawCommand]:
    """Nové kópie kresby začínajúce na `t` (bar skutočného vstupu); staré sa zmažú (rovnaké obj_id)."""
    out: list[DrawCommand] = []
    for o in objs:
        n = copy.copy(o)
        if isinstance(n, DrawBox):
            width = max(0, o.x2_ms - o.x1_ms)
            n.x1_ms, n.x2_ms = t, max(o.x2_ms, t + width)
        else:
            n.x_ms = t
        out += [DrawDelete(o.obj_id), n]
    if plan is not None:
        relevel([x for x in out if isinstance(x, DrawBox)], plan)
    return out


def moved(objs: list[Any], t: int) -> list[DrawCommand]:
    """Posun začiatku kresby na bar vyplnenia (ceny ostávajú)."""
    return [DrawUpdate(o.obj_id, "x1_ms" if isinstance(o, DrawBox) else "x_ms", t) for o in objs]


def deleted(objs: list[Any]) -> list[DrawCommand]:
    return [DrawDelete(o.obj_id) for o in objs]


def with_ids(ctx: Any, pending: set[str] | frozenset[str], dropped: set[str] | frozenset[str]) -> Any:
    """Kontext pre vnútorný engine s doplnenými čakajúcimi a zahodenými vstupmi."""
    if ctx is None or (not pending and not dropped):
        return ctx
    from dataclasses import replace
    return replace(ctx, pending_entry_ids=frozenset(ctx.pending_entry_ids) | frozenset(pending),
                   dropped_entry_ids=frozenset(ctx.dropped_entry_ids) | frozenset(dropped))
