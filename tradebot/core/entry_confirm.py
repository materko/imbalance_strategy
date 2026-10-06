"""Vstupný model — potvrdenie vstupu sviečkou (IBS imbalance / pin bar) — pre stratégie, ktoré ho nemajú vlastný.

Stratégia (engine) rozhodne, **kedy** je signál, a pošle market vstup. Keď má config `entryConfirm`
iné než `none`, obal `EntryConfirmEngine` ten vstup podrží a pošle ho až na sviečke, ktorá je v smere
obchodu naším základným vstupným modelom:

* ``imbalance`` — IBS: medzera medzi 1. a 3. sviečkou v smere (aspoň `confirmImbMinAtr` ATR),
  stredná sviečka zavrela za 1.,
* ``pinbar``    — dlhý knôt proti smeru (`confirmPbWickPct` % rozsahu), malé telo (`confirmPbBodyPct` %),
* ``any``       — jedno alebo druhé.

Čaká sa najviac `confirmBars` barov vrátane signálnej sviečky (tá sama môže byť potvrdením). Vstup je
market na zavretí potvrdzovacej sviečky; stop ostáva tam, kde ho dala stratégia, cieľ sa prepočíta na
rovnaký RR a veľkosť pozície na rovnaké riziko. Signál padá, keď cena medzitým prejde stopom, keď
stratégia pošle nový signál (ten ho nahradí) alebo keď by stop vyšiel pod 1/4 pôvodného.
Limitky stratégie (vstup na dotyk úrovne) sa nemenia. Kresba obchodu (TP / SL boxy, štítok vstupu) sa
posunie na potvrdzovaciu sviečku, pri prepadnutom signáli sa zmaže (`tradebot.core.entry_draw`).

Obal je generický (nepozná stratégiu menom) a nasadzujú ho adaptéry pod obal typu orderu
(`entry_order`): potvrdený vstup sa tak dá poslať aj limitkou späť do potvrdzovacej sviečky.
Pri `none` sa engine nebalí — parita s Pine / C# sa nemení. Stratégie s vlastným vstupným modelom
(IBS a odnože, JSS, Fibo, Volume Profile POC, Liquidity) tento obal nemajú.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from .engine import EngineOutput
from .orders import MarketContext, OrderAction, OrderIntent
from .types import Bar, Direction, OrderType
from .entry_draw import deleted, released, trade_drawings, with_ids

__all__ = ["EntryConfirm", "EntryConfirmFields", "ENTRY_CONFIRM_ENUMS", "ENTRY_CONFIRM_CONSTRAINTS",
           "ENTRY_CONFIRM_FIELD_NAMES", "entry_confirm_params", "EntryConfirmEngine", "wrap_entry_confirm",
           "is_imbalance", "is_pinbar"]

_ATR_LEN = 14


class EntryConfirm(str, Enum):
    NONE = "none"            # vstup tak, ako ho dáva stratégia
    IMBALANCE = "imbalance"  # IBS imbalance v smere
    PINBAR = "pinbar"        # pin bar v smere
    ANY = "any"              # imbalance alebo pin bar


@dataclass
class EntryConfirmFields:
    """Mixin polí configu. Pridáva sa ako ďalší predok configu stratégie."""

    entryConfirm: EntryConfirm = EntryConfirm.NONE
    confirmBars: int = 3
    confirmImbMinAtr: float = 0.05
    confirmPbWickPct: int = 60
    confirmPbBodyPct: int = 30


ENTRY_CONFIRM_FIELD_NAMES: frozenset[str] = frozenset(
    {"entryConfirm", "confirmBars", "confirmImbMinAtr", "confirmPbWickPct", "confirmPbBodyPct"})
ENTRY_CONFIRM_ENUMS: dict[str, type] = {"entryConfirm": EntryConfirm}
ENTRY_CONFIRM_CONSTRAINTS: dict[str, tuple[float, float]] = {
    "confirmBars": (1, 100), "confirmImbMinAtr": (0.0, 10.0), "confirmPbWickPct": (30, 95), "confirmPbBodyPct": (5, 60)}


def entry_confirm_params(group: str) -> dict[str, dict[str, Any]]:
    """Popisy polí pre formulár webapp (do `params.py` stratégie)."""
    return {
        "entryConfirm": dict(group=group, title="Vstupny model (potvrdenie svieckou)",
                             tooltip="none = vstup tak, ako ho dava strategia; imbalance = po signale cakat na IBS imbalance "
                                     "v smere; pinbar = na pin bar; any = jedno alebo druhe. Vstup na zavreti tej sviecky, "
                                     "stop ostava, ciel sa prepocita na rovnaky RR."),
        "confirmBars": dict(group=group, title="Potvrdenie do (bary)",
                            tooltip="Kolko barov vratane signalnej sviecky sa na vstupny model caka. Potom signal prepadne."),
        "confirmImbMinAtr": dict(group=group, title="Imbalance: min. medzera (ATR)", step=0.01,
                                 tooltip="Medzera medzi 1. a 3. svieckou aspon tolko ATR(14) grafu."),
        "confirmPbWickPct": dict(group=group, title="Pin bar: min. knot (% rozsahu)", tooltip="Knot proti smeru obchodu."),
        "confirmPbBodyPct": dict(group=group, title="Pin bar: max. telo (% rozsahu)", tooltip="Telo sviecky."),
    }


def is_imbalance(b0: Bar, b1: Bar, b2: Bar, long: bool, min_gap: float = 0.0) -> bool:
    """IBS imbalance: `b0` je najnovšia sviečka, `b2` prvá z trojice."""
    if long:
        return b0.low > b2.high and b1.close > b2.high and (b0.low - b2.high) >= min_gap
    return b0.high < b2.low and b1.close < b2.low and (b2.low - b0.high) >= min_gap


def is_pinbar(bar: Bar, long: bool, wick_pct: float, body_pct: float) -> bool:
    rng = bar.high - bar.low
    if rng <= 0 or abs(bar.close - bar.open) > body_pct / 100.0 * rng:
        return False
    wick = (min(bar.open, bar.close) - bar.low) if long else (bar.high - max(bar.open, bar.close))
    return wick >= wick_pct / 100.0 * rng


class EntryConfirmEngine:
    """Obal enginu: market vstup stratégie pošle až na potvrdzovacej sviečke (viď hlavičku modulu)."""

    def __init__(self, engine: Any, cfg: Any) -> None:
        self.engine = engine
        self.cfg = cfg
        self.mode = EntryConfirm(cfg.entryConfirm)
        self._bars: deque[Bar] = deque(maxlen=3)
        self._atr = 0.0
        self._tr: list[float] = []
        self._wait: tuple[OrderIntent, int, list] | None = None    #: (vstup stratégie, index baru signálu, jeho kresba)
        self._dropped: set[str] = set()
        self._idx = -1

    def __getattr__(self, name: str) -> Any:   # inst, required_history, warmup, final_drawings…
        if name == "engine" or name.startswith("__"):
            raise AttributeError(name)   # pri unpickle ešte `engine` nie je — bez tohto nekonečná rekurzia
        return getattr(self.engine, name)

    def _round(self, price: float) -> float:
        inst = getattr(self.engine, "inst", None)
        return inst.round_price(price) if inst is not None else price

    def _push(self, bar: Bar) -> None:
        prev = self._bars[-1] if self._bars else None
        tr = bar.high - bar.low if prev is None else max(bar.high - bar.low, abs(bar.high - prev.close),
                                                         abs(bar.low - prev.close))
        if self._atr > 0:
            self._atr += (tr - self._atr) / _ATR_LEN
        else:
            self._tr.append(tr)
            if len(self._tr) >= _ATR_LEN:
                self._atr = sum(self._tr) / len(self._tr)
        self._bars.append(bar)

    def _confirmed(self, bar: Bar, long: bool) -> bool:
        cfg = self.cfg
        imb = len(self._bars) == 3 and is_imbalance(self._bars[2], self._bars[1], self._bars[0], long,
                                                    float(cfg.confirmImbMinAtr) * self._atr)
        pin = is_pinbar(bar, long, float(cfg.confirmPbWickPct), float(cfg.confirmPbBodyPct))
        if self.mode is EntryConfirm.IMBALANCE:
            return imb
        if self.mode is EntryConfirm.PINBAR:
            return pin
        return imb or pin

    def _entry(self, intent: OrderIntent, bar: Bar) -> OrderIntent | None:
        """Vstup na zavretí potvrdzovacej sviečky: stop ostáva, RR a riziko tiež."""
        plan = intent.plan
        long = plan.direction is Direction.LONG
        price = self._round(bar.close)
        sl = price - plan.stop_loss if long else plan.stop_loss - price
        old_sl = plan.entry - plan.stop_loss if long else plan.stop_loss - plan.entry
        if sl <= 0 or old_sl <= 0 or sl < 0.25 * old_sl:
            return None
        rr = (plan.take_profit - plan.entry if long else plan.entry - plan.take_profit) / old_sl
        take = self._round(price + rr * sl if long else price - rr * sl)
        qty = plan.qty * old_sl / sl if plan.qty and plan.qty == plan.qty else plan.qty
        return replace(intent, plan=replace(plan, entry=price, take_profit=take, qty=qty, sl_distance=sl))

    def on_bar(self, bar: Bar, htf: Any = None, ctx: MarketContext | None = None) -> EngineOutput:
        self._idx += 1
        self._push(bar)
        pend = {self._wait[0].order_id} if self._wait is not None else set()
        out = self.engine.on_bar(bar, htf, with_ids(ctx, pend, self._dropped))
        self._dropped = set()
        pos = ctx.position_size if ctx is not None else 0.0
        if pos != 0.0 and self._wait is not None:
            self._drop(out)
        orders: list[OrderIntent] = []
        fresh = False
        for o in out.orders:
            if o.action is OrderAction.ENTRY and o.order_type is OrderType.MARKET and o.plan is not None:
                objs = trade_drawings(out.drawings, bar.time)
                if pos == 0.0:
                    if self._wait is not None:
                        self._drop(out)                      # nový signál nahrádza čakajúci
                    self._wait, fresh = (o, self._idx, objs), True
                else:
                    out.drawings = [d for d in out.drawings if not any(d is x for x in objs)]
                    self._dropped.add(o.order_id)
                continue
            if o.action is OrderAction.CANCEL and self._wait is not None and o.order_id == self._wait[0].order_id:
                self._wait = None
            orders.append(o)
        if self._wait is not None:
            intent, at, objs = self._wait
            plan = intent.plan
            long = plan.direction is Direction.LONG
            if not fresh and ((bar.low <= plan.stop_loss) if long else (bar.high >= plan.stop_loss)):
                self._drop(out)            # cena prešla stopom skôr, než prišlo potvrdenie
            elif self._confirmed(bar, long):
                entry = self._entry(intent, bar)
                if entry is not None:
                    orders.append(entry)
                    out.drawings = [d for d in out.drawings if not any(d is x for x in objs)]
                    out.drawings += released(objs, bar.time, entry.plan)   # kresba na potvrdzovaciu sviečku
                    self._wait = None
                else:
                    self._drop(out)
            elif self._idx - at + 1 >= int(self.cfg.confirmBars):
                self._drop(out)
        out.orders = orders
        return out

    def _drop(self, out: EngineOutput) -> None:
        """Čakajúci signál prepadol: kresba preč a stratégia sa to dozvie na ďalšom bare."""
        intent, _, objs = self._wait
        if any(d is x for d in out.drawings for x in objs):
            out.drawings = [d for d in out.drawings if not any(d is x for x in objs)]
        else:
            out.drawings += deleted(objs)
        self._dropped.add(intent.order_id)
        self._wait = None


def wrap_entry_confirm(engine: Any, cfg: Any) -> Any:
    """Engine obalený potvrdením vstupu, keď to config chce; inak ten istý engine."""
    t = getattr(cfg, "entryConfirm", None)
    if t is None or EntryConfirm(t) is EntryConfirm.NONE:
        return engine
    return EntryConfirmEngine(engine, cfg)
