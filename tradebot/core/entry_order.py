"""Typ vstupného orderu — market alebo limit — pre stratégie, ktoré vstupujú market orderom.

Stratégia (engine) rozhodne, **kedy** vstúpiť, a pošle market vstup na zavretí signálnej sviečky.
Keď má config `entryOrderType = limit`, obal `EntryOrderEngine` ten vstup zmení na limitku:

* cena: `limitOffsetPct` % rozsahu signálnej sviečky späť od zavretia (long nižšie, short vyššie;
  0 = na cene zavretia, 50 = stred sviečky, 100 = na jej low / high),
* platí `limitValidBars` barov grafu, potom sa zruší,
* stop ostáva tam, kde ho dala stratégia; cieľ sa pri `limitKeepRR` prepočíta tak, aby RR
  ostal rovnaký (inak ostane tam, kde bol), a veľkosť pozície sa prepočíta na rovnaké riziko,
* kým limitka čaká, ďalšie vstupy stratégie sa zahodia,
* keď by limitka bola za stopom alebo tak blízko neho, že stop klesne pod 1/4 pôvodného, vstup sa
  vynechá (inak by z tesného stopu vznikla obrovská pozícia).

Obal je generický (nepozná stratégiu menom) a nasadzujú ho adaptéry (Freqtrade aj MultiCharts
runner) — logika stratégií ani ich parita s Pine / C# sa nemení. Pri `market` sa engine nebalí.
IBS a jej odnože ho nemajú (majú vlastné vstupné modely).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from .engine import EngineOutput
from .orders import MarketContext, OrderAction, OrderIntent
from .types import Bar, Direction, OrderType

__all__ = ["EntryOrderType", "EntryOrderFields", "ENTRY_ORDER_ENUMS", "ENTRY_ORDER_CONSTRAINTS",
           "ENTRY_ORDER_FIELD_NAMES", "entry_order_params", "EntryOrderEngine", "wrap_entry_order"]


class EntryOrderType(str, Enum):
    MARKET = "market"  # na zavretí signálnej sviečky (správanie stratégie)
    LIMIT = "limit"    # limitka späť do signálnej sviečky, platí N barov


@dataclass
class EntryOrderFields:
    """Mixin polí configu. Pridáva sa ako druhý predok configu stratégie."""

    entryOrderType: EntryOrderType = EntryOrderType.MARKET
    limitOffsetPct: int = 50
    limitValidBars: int = 3
    limitKeepRR: bool = True


ENTRY_ORDER_FIELD_NAMES: frozenset[str] = frozenset({"entryOrderType", "limitOffsetPct", "limitValidBars", "limitKeepRR"})
ENTRY_ORDER_ENUMS: dict[str, type] = {"entryOrderType": EntryOrderType}
ENTRY_ORDER_CONSTRAINTS: dict[str, tuple[float, float]] = {"limitOffsetPct": (0, 100), "limitValidBars": (1, 100)}


def entry_order_params(group: str) -> dict[str, dict[str, Any]]:
    """Popisy polí pre formulár webapp (do `params.py` stratégie)."""
    return {
        "entryOrderType": dict(group=group, title="Typ vstupu",
                               tooltip="market = na zavreti signalnej sviecky; limit = limitka spat do signalnej "
                                       "sviecky, plati N barov."),
        "limitOffsetPct": dict(group=group, title="Limitka: % sviecky spat",
                               tooltip="0 = na cene zavretia, 50 = stred signalnej sviecky, 100 = jej low (long) / high (short)."),
        "limitValidBars": dict(group=group, title="Limitka plati (bary)", tooltip="Potom sa nevyplnena limitka zrusi."),
        "limitKeepRR": dict(group=group, title="Limitka: zachovat RR",
                            tooltip="Ciel sa posunie s lepsou cenou vstupu, aby RR ostal rovnaky. Vypnute = ciel ostane."),
    }


class EntryOrderEngine:
    """Obal enginu: market vstupy stratégie mení na limitky (viď hlavičku modulu)."""

    def __init__(self, engine: Any, cfg: Any) -> None:
        self.engine = engine
        self.cfg = cfg
        self._pending: tuple[str, int] | None = None
        self._idx = -1

    def __getattr__(self, name: str) -> Any:   # inst, required_history, warmup, final_drawings…
        if name == "engine" or name.startswith("__"):
            raise AttributeError(name)   # pri unpickle ešte `engine` nie je — bez tohto nekonečná rekurzia
        return getattr(self.engine, name)

    def _round(self, price: float) -> float:
        inst = getattr(self.engine, "inst", None)
        return inst.round_price(price) if inst is not None else price

    def _limit(self, intent: OrderIntent, bar: Bar) -> OrderIntent | None:
        cfg = self.cfg
        plan = intent.plan
        long = plan.direction is Direction.LONG
        k = float(cfg.limitOffsetPct) / 100.0
        rng = bar.high - bar.low
        price = self._round(plan.entry - k * rng if long else plan.entry + k * rng)
        sl = price - plan.stop_loss if long else plan.stop_loss - price
        old_sl = plan.entry - plan.stop_loss if long else plan.stop_loss - plan.entry
        if sl <= 0 or old_sl <= 0 or sl < 0.25 * old_sl:
            return None   # limitka za stopom alebo tesne pri ňom (stop by bol pod 1/4 pôvodného) — vstup sa vynechá
        take = plan.take_profit
        if cfg.limitKeepRR:
            rr = (plan.take_profit - plan.entry if long else plan.entry - plan.take_profit) / old_sl
            take = self._round(price + rr * sl if long else price - rr * sl)
        qty = plan.qty * old_sl / sl if plan.qty and plan.qty == plan.qty else plan.qty
        new = replace(plan, entry=price, take_profit=take, qty=qty, sl_distance=sl)
        return replace(intent, plan=new, order_type=OrderType.LIMIT)

    def on_bar(self, bar: Bar, htf: Any = None, ctx: MarketContext | None = None) -> EngineOutput:
        self._idx += 1
        out = self.engine.on_bar(bar, htf, ctx)
        pos = ctx.position_size if ctx is not None else 0.0
        orders: list[OrderIntent] = []
        if self._pending is not None:
            if pos != 0.0:
                self._pending = None   # vyplnila sa
            elif self._idx - self._pending[1] >= int(self.cfg.limitValidBars):
                orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="limitka nevyplnená"))
                self._pending = None
        for o in out.orders:
            if o.action is OrderAction.ENTRY and o.order_type is OrderType.MARKET and o.plan is not None:
                if self._pending is not None or pos != 0.0:
                    continue   # kým limitka čaká, ďalší vstup sa neposiela
                lim = self._limit(o, bar)
                if lim is None:
                    continue
                self._pending = (lim.order_id, self._idx)
                orders.append(lim)
                continue
            if o.action is OrderAction.CANCEL and self._pending is not None and o.order_id == self._pending[0]:
                self._pending = None
            orders.append(o)
        out.orders = orders
        return out


def wrap_entry_order(engine: Any, cfg: Any) -> Any:
    """Engine obalený limitkami, keď to config chce; inak ten istý engine."""
    t = getattr(cfg, "entryOrderType", None)
    if t is None or EntryOrderType(t) is EntryOrderType.MARKET:
        return engine
    return EntryOrderEngine(engine, cfg)
