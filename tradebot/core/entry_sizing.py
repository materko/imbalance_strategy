"""Veľkosť pozície a strop straty — spoločné pre všetky stratégie.

Stratégia počíta počet kontraktov sama z rizika v $ (`riskDollar`, pri Pine mene `maxLossDollar`):
``qty = riziko / (vzdialenosť SL × hodnota bodu)``, zaokrúhlené nadol na `qty_step`. Strata na stope je
tak rovnaká pri SL 30 aj 50 tickov. Dve veci sa tým ale nedajú vyjadriť a tie robí tento obal:

* ``fixedQty`` — pevný počet kontraktov ``qty`` namiesto rizika (stratégie, ktoré prepínač majú vlastný,
  dávajú to isté; obal je pre ne no-op),
* ``skipOverRisk`` — strop straty: počet sa zaokrúhli nadol na celý krok (ako ho pošle broker) a keď by
  strata na stope aj tak bola väčšia než riziko, obchod sa vynechá. Stáva sa to pri širokom stope, keď
  aj najmenšia pozícia (`min_qty`, na futures 1 kontrakt) stojí viac než riziko, alebo pri pevnom
  počte. Bez neho sa obchoduje aspoň `min_qty` a strata riziko prekročí.

Polia sú v `SizingFields`, predkovi `StrategyConfig`, takže ich má každá stratégia; kto ich deklaruje
sám (Pine vstup `fixedQty`), má vlastný default. Pri defaultoch (`fixedQty` vypnutý alebo vlastný,
`skipOverRisk` vypnutý) sa výsledky nemenia. Obal je generický, nasadzujú ho adaptéry ako vonkajší
(nad typ orderu — riziko sa počíta z konečnej ceny vstupu); C# zrkadlo je `EntrySizingEngine`
v `EntryLayers.cs`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .engine import EngineOutput
from .entry_draw import trade_drawings, with_ids
from .orders import MarketContext, OrderAction
from .types import Bar

__all__ = ["SizingFields", "SIZING_FIELD_NAMES", "SIZING_CONSTRAINTS", "sizing_params", "risk_limit",
           "EntrySizingEngine", "wrap_entry_sizing"]

#: Mená poľa s rizikom na obchod v $ — prvé, ktoré config má.
RISK_FIELDS = ("riskDollar", "maxLossDollar")


@dataclass
class SizingFields:
    """Mixin polí configu — predok `StrategyConfig`, takže ho má každá stratégia."""

    fixedQty: bool = False
    qty: float = 1.0
    skipOverRisk: bool = False


SIZING_FIELD_NAMES: frozenset[str] = frozenset({"fixedQty", "qty", "skipOverRisk"})
SIZING_CONSTRAINTS: dict[str, tuple[float, float]] = {"qty": (0.001, 1000)}
#: Prepínač → podnastavenia pre formulár (`StrategySpec.features`).
SIZING_FEATURE: dict[str, Any] = {"switches": ["fixedQty"], "params": ["qty"]}


def sizing_params(group: str) -> dict[str, dict[str, Any]]:
    """Popisy polí pre formulár webapp; `StrategySpec` ich doplní k tým, ktoré stratégia nepopísala."""
    return {
        "fixedQty": dict(group=group, title="Pevný počet kontraktov",
                         tooltip="Zapnuté = vždy `Počet kontraktov`. Vypnuté = počet z rizika na obchod: "
                                 "strata na stope je rovnaká pri krátkom aj dlhom SL."),
        "qty": dict(group=group, title="Počet kontraktov", step=1.0,
                    tooltip="Pri pevnom počte kontraktov (loty, mince)."),
        "skipOverRisk": dict(group=group, title="Vynechať obchod nad riziko",
                             tooltip="Strop straty: keď by strata na stope bola väčšia než riziko na obchod "
                                     "(široký SL, pri ktorom aj 1 kontrakt stojí viac, alebo pevný počet), "
                                     "obchod sa nespraví. Vypnuté = obchoduje sa aspoň najmenšia pozícia."),
    }


def risk_limit(cfg: Any) -> float:
    """Riziko na obchod v $ z configu; 0 = stratégia ho nemá alebo je vypnuté."""
    for name in RISK_FIELDS:
        v = getattr(cfg, name, None)
        if v is not None:
            return float(v)
    return 0.0


class EntrySizingEngine:
    """Obal enginu: pevný počet kontraktov a strop straty (viď hlavičku modulu)."""

    def __init__(self, engine: Any, cfg: Any) -> None:
        self.engine = engine
        self.cfg = cfg
        self._dropped: set[str] = set()

    def __getattr__(self, name: str) -> Any:   # inst, required_history, warmup, final_drawings…
        if name == "engine" or name.startswith("__"):
            raise AttributeError(name)   # pri unpickle ešte `engine` nie je — bez tohto nekonečná rekurzia
        return getattr(self.engine, name)

    def _size(self, plan: Any) -> Any | None:
        """Plán s konečnou veľkosťou, alebo `None`, keď by strata na stope prekročila riziko."""
        cfg = self.cfg
        qty = float(cfg.qty) if cfg.fixedQty else plan.qty
        if not cfg.skipOverRisk:
            return plan if qty == plan.qty else replace(plan, qty=qty)
        inst = getattr(self.engine, "inst", None)
        risk = risk_limit(cfg)
        if inst is None or risk <= 0 or qty != qty:
            return plan if qty == plan.qty else replace(plan, qty=qty)
        qty = inst.round_qty(qty)   # broker berie len celé kroky (NinjaTrader by 2,7 zaokrúhlil na 3)
        if qty * plan.sl_distance * inst.point_value > risk * (1.0 + 1e-9):
            return None
        return plan if qty == plan.qty else replace(plan, qty=qty)

    def on_bar(self, bar: Bar, htf: Any = None, ctx: MarketContext | None = None) -> EngineOutput:
        out = self.engine.on_bar(bar, htf, with_ids(ctx, frozenset(), self._dropped))
        self._dropped = set()
        orders = []
        for o in out.orders:
            if o.action is OrderAction.ENTRY and o.plan is not None:
                plan = self._size(o.plan)
                if plan is None:
                    # obchod nebude — kresba jeho boxov preč, vnútorné obaly sa to dozvedia na ďalšom bare
                    objs = trade_drawings(out.drawings, bar.time)
                    out.drawings = [d for d in out.drawings if not any(d is x for x in objs)]
                    self._dropped.add(o.order_id)
                    continue
                if plan is not o.plan:
                    o = replace(o, plan=plan)
            orders.append(o)
        out.orders = orders
        return out


def wrap_entry_sizing(engine: Any, cfg: Any) -> Any:
    """Engine obalený veľkosťou pozície, keď to config chce; inak ten istý engine."""
    if getattr(engine, "native_entry_layers", False):   # C# engine má obaly vstupov v sebe
        return engine
    if not (getattr(cfg, "fixedQty", False) or getattr(cfg, "skipOverRisk", False)):
        return engine
    return EntrySizingEngine(engine, cfg)
