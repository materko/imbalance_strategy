"""`CSharpEngine` — engine napísaný v C#, ktorý sa zvyšku TradeBota javí ako obyčajný Python engine.

Spĺňa kontrakt `tradebot.core.engine.Engine` (`on_bar`, `final_drawings`, `required_history`,
`warmup`), takže generický Freqtrade adaptér, emulátor MultiCharts, webapp aj analytika s ním
pracujú bez zmeny. Logika beží v C# (`csharp/`), tu sa len prekladajú typy: `Bar` a
`MarketContext` dnu, `OrderIntent` / `DrawCommand` / `StateEvent` von.

Stratégia s C# jadrom si ho vyžiada v `StrategySpec.engine_factory`:

    engine_factory=csharp_engine_factory("ibsninja")
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from tradebot.core.clock import ClockState
from tradebot.core.drawing import (
    DrawBg, DrawBox, DrawCommand, DrawDelete, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle, LineStyle,
)
from tradebot.core.engine import EngineOutput
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent, StateEvent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .bridge import Transport, open_transport

__all__ = ["CSharpEngine", "CSharpEngineOutput", "csharp_engine_factory", "command_from_dict", "intent_from_dict"]


@dataclass
class CSharpEngineOutput(EngineOutput):
    """Výstup C# enginu: k generickému pridáva stav seáns (ak ich stratégia má) a bias štruktúry."""

    clock: ClockState | None = None
    market_bias: int = 0


# --------------------------------------------------------------------------- #
# JSON -> typy jadra
# --------------------------------------------------------------------------- #


def command_from_dict(d: dict[str, Any]) -> DrawCommand:
    t = d["t"]
    if t == "bg":
        return DrawBg(kind=DrawKind(d["k"]), x1_ms=d["x1"], x2_ms=d["x2"], color=d["c"],
                      obj_id=d["id"], text=d.get("tx", ""))
    if t == "update":
        return DrawUpdate(d["id"], d["f"], d["v"])
    if t == "box":
        return DrawBox(
            kind=DrawKind(d["k"]), x1_ms=d["x1"], y1=d["y1"], x2_ms=d["x2"], y2=d["y2"],
            border_color=d["bc"], fill_color=d.get("fc"),
            border_style=LineStyle(d["bs"]) if "bs" in d else LineStyle.SOLID,
            border_width=d.get("bw", 1), extend_right=d.get("er", False),
            obj_id=d["id"], zone_uid=d.get("z"), text=d.get("tx", ""),
        )
    if t == "label":
        return DrawLabel(
            kind=DrawKind(d["k"]), x_ms=d["x"], y=d["y"], text=d["tx"], color=d["c"],
            style=LabelStyle(d["s"]) if "s" in d else LabelStyle.NONE, above=d["ab"],
            bg_color=d.get("bg"), obj_id=d["id"], zone_uid=d.get("z"),
        )
    if t == "line":
        return DrawLine(
            kind=DrawKind(d["k"]), x1_ms=d["x1"], y1=d["y1"], x2_ms=d["x2"], y2=d["y2"], color=d["c"],
            style=LineStyle(d["s"]) if "s" in d else LineStyle.SOLID, width=d.get("w", 1),
            obj_id=d["id"], zone_uid=d.get("z"), text=d.get("tx", ""),
        )
    if t == "delete":
        return DrawDelete(d["id"])
    raise ValueError(f"neznámy príkaz kreslenia z C#: {t!r}")


_ACTIONS = {"entry": OrderAction.ENTRY, "cancel": OrderAction.CANCEL, "close": OrderAction.CLOSE}


def intent_from_dict(d: dict[str, Any]) -> OrderIntent:
    plan = None
    p = d.get("p")
    if p is not None:
        tr = p.get("tr")
        trailing = None if tr is None else TrailingPlan(
            activation_price_distance=tr["ap"], offset_price_distance=tr["op"],
            activation_ticks=tr["at"], offset_ticks=tr["ot"],
        )
        plan = TradePlan(direction=Direction(p["dir"]), entry=p["e"], stop_loss=p["sl"], take_profit=p["tp"],
                         qty=p["q"], sl_distance=p["sd"], trailing=trailing)
    return OrderIntent(
        action=_ACTIONS[d["a"]], order_id=d["id"], source_id=d["src"],
        direction=Direction(d["dir"]) if "dir" in d else None,
        plan=plan, order_type=OrderType(d["ot"]), reason=d.get("r", ""),
    )


# --------------------------------------------------------------------------- #


class _Stats:
    """Čísla z C# enginu pod menami, ktoré logy adaptérov čakajú (IBS: evidencia zón)."""

    def __init__(self, engine: "CSharpEngine") -> None:
        self._engine = engine

    def _get(self, name: str) -> int:
        return int(self._engine.stats().get(name, 0))

    def __len__(self) -> int:
        return self._get("zones")

    @property
    def max_zones(self) -> int:
        return self._get("max_zones")

    @property
    def evicted(self) -> int:
        return self._get("evicted")

    @property
    def evicted_alive(self) -> int:
        return self._get("evicted_alive")


class CSharpEngine:
    """Bar-by-bar engine v C#. `key` je kľúč z `[TradeBotEngine("...")]` na C# triede."""

    def __init__(self, key: str, cfg: Any, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.key = key
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = int(chart_tf_minutes)
        self._open()

    def _open(self) -> None:
        """Vytvorí C# engine (nový, bez stavu) a z neho odvodené veci."""
        inst = self.inst
        instrument = {
            "symbol": inst.symbol, "venue": inst.venue, "tick_size": inst.tick_size,
            "point_value": inst.point_value, "qty_step": inst.qty_step, "min_qty": inst.min_qty,
            "has_real_volume": inst.has_real_volume,
        }
        self._transport: Transport = open_transport(
            self.key, json.dumps(self.cfg.to_dict()), json.dumps(instrument), self.chart_tf_minutes)
        info = self._transport.info
        self.required_history: int = int(info["required_history"])
        self.warmup = self._warmup(info)
        #: evidencia zón pre logy adaptérov (`len(engine.book)`, `evicted_alive`...)
        self.book = _Stats(self)

    # Hyperopt posiela stratégiu (aj s enginmi) do paralelných procesov cez pickle. C# objekt sa
    # preniesť nedá a netreba: generický adaptér si pri hyperopte stavia runner pre každú epochu
    # nanovo, takže v novom procese stačí otvoriť čerstvý engine s tým istým configom.
    def __getstate__(self) -> dict[str, Any]:
        return {"key": self.key, "cfg": self.cfg, "inst": self.inst, "chart_tf_minutes": self.chart_tf_minutes}

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._open()

    def _warmup(self, info: dict[str, Any]) -> Warmup:
        w = Warmup(self.chart_tf_minutes)
        for need in info.get("warmup", []):
            if need["seeded"]:
                w.add_seeded(need["name"], need["bars"], need["tf"], self._seeder(need["name"]))
            else:
                w.add(need["name"], need["bars"], need["tf"])
        return w

    def _seeder(self, name: str) -> Callable[[Any, Bar | None], None]:
        def seed(closed, partial: Bar | None) -> None:
            bars = list(closed) + ([partial] if partial is not None else [])
            times = [int(b.time) for b in bars]
            values = [float(x) for b in bars for x in (b.open, b.high, b.low, b.close, b.volume)]
            self._transport.seed(name, times, values, partial is not None)

        return seed

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf: Any | None = None, ctx: MarketContext | None = None) -> CSharpEngineOutput:
        window = None
        if htf is not None:
            window = (
                [int(b.time) for b in htf.bars],
                [float(x) for b in htf.bars for x in (b.open, b.high, b.low, b.close, b.volume)],
                float(htf.vol_sma),
            )
        position = float(ctx.position_size) if ctx is not None else 0.0
        daily = bool(ctx.daily_win_limit_reached) if ctx is not None else False
        open_ids = ",".join(sorted(ctx.open_order_ids)) if ctx is not None and ctx.open_order_ids else ""

        raw = self._transport.on_bar(
            int(bar.time), (float(bar.open), float(bar.high), float(bar.low), float(bar.close), float(bar.volume)),
            window, position, daily, open_ids)

        clk = raw.get("clk")
        clock = None if clk is None else ClockState(tuple(clk["z"]), tuple(clk["t"]), clk["n"])
        out = CSharpEngineOutput(
            orders=[intent_from_dict(o) for o in raw.get("o", ())],
            drawings=[command_from_dict(d) for d in raw.get("d", ())],
            events=[StateEvent(e["ts"], e["z"], e["f"], e["to"], e["r"]) for e in raw.get("e", ())],
            close_session=raw.get("cs", False),
            clock=clock,
            market_bias=raw.get("mb", 0),
        )
        if ctx is not None:  # Python engine tieto dve veci do ctx zapisuje tiež
            ctx.market_bias = out.market_bias
            if clock is not None:
                ctx.in_trade_window = clock.in_trade_window
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        raw = self._transport.final_drawings(
            int(bar.time), (float(bar.open), float(bar.high), float(bar.low), float(bar.close), float(bar.volume)))
        return [command_from_dict(d) for d in raw]

    def stats(self) -> dict[str, float]:
        return self._transport.stats()

    def close(self) -> None:
        self._transport.close()


def csharp_engine_factory(key: str) -> Callable[[Any, InstrumentSpec, int], CSharpEngine]:
    """`StrategySpec.engine_factory` pre stratégiu, ktorej jadro je C# trieda s kľúčom `key`."""

    def factory(cfg: Any, inst: InstrumentSpec, chart_tf_minutes: int) -> CSharpEngine:
        return CSharpEngine(key, cfg, inst, chart_tf_minutes)

    factory.csharp_key = key  # type: ignore[attr-defined]
    return factory
