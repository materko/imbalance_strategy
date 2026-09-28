"""Engine VWAP ORB 1.0: ORB, v ktorom je prerazenie signálom až keď je za rangom aj VWAP.

Celý ORB (stavanie rangu, stop, cieľ, koniec seansy, kresby) je `ORBEngine`; tento engine
k nemu pridáva seansový VWAP (`tradebot.core.vwap.SessionVwap`) a podmienku cez háčik
`_break_allowed`:

* **long** — close nad high rangu (to kontroluje ORB) **a** VWAP nad high rangu
  (o ``vwapBreakAtr`` × ATR); pri ``closeBeyondVwap`` aj close nad VWAP
* **short** — zrkadlovo pod low

ORB hodnotí prerazenie na každom bare obchodného okna, kým nepadne obchod — vstup je teda
na zavretí **prvej** sviečky, na ktorej platí oboje, aj keď VWAP za range dôjde až hodinu
po tom, čo ho prerazila cena.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawCommand, DrawLine
from tradebot.core.engine import EngineOutput
from tradebot.core.orders import MarketContext
from tradebot.core.types import Bar, Direction, InstrumentSpec
from tradebot.core.vwap import SessionVwap

from ..orb.engine import ORBEngine
from .config import VwapOrbConfig
from .drawing import VO_VWAP

__all__ = ["VwapOrbEngine"]

_VWAP_COLOR = "#a855f7"


class VwapOrbEngine(ORBEngine):
    """ORB + VWAP. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: VwapOrbConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        super().__init__(cfg, inst, chart_tf_minutes)
        start, end, tz = cfg.vwapAnchor.window(cfg.nyStartH * 60 + cfg.nyStartM)
        self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=start, end_minutes=end,
                                tz=tz, period_minutes=cfg.vwapPeriod.minutes)
        self._vwap_value: float | None = None
        #: posledný nakreslený bod čiary VWAP (čas, hodnota, deň)
        self._vwap_point: tuple[int, float, tuple[int, int, int] | None] | None = None

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        # VWAP pred ORB: podmienka prerazenia sa pýta na hodnotu po zavretí tohto baru
        self._vwap_value = self.vwap.push(bar)
        out = super().on_bar(bar, htf, ctx)
        if self.cfg.showVwap and self.vwap.updated and self._vwap_value is not None:
            out.drawings += self._vwap_drawing(bar, self._vwap_value)
        return out

    def _break_allowed(self, st, direction: Direction, bar: Bar, atr: float) -> bool:
        """VWAP je za hranicou rangu v smere prerazenia (a pri ``closeBeyondVwap`` aj cena za VWAP)."""
        vwap = self._vwap_value
        if vwap is None or st.high is None or st.low is None:
            return False
        cfg = self.cfg
        need = cfg.vwapBreakAtr.resolve(self.inst, price=bar.close, atr=atr)
        if direction is Direction.LONG:
            return vwap > st.high + need and (not cfg.closeBeyondVwap or bar.close > vwap)
        return vwap < st.low - need and (not cfg.closeBeyondVwap or bar.close < vwap)

    def _vwap_drawing(self, bar: Bar, vwap: float) -> list[DrawCommand]:
        """Úsečka VWAP od posledného bodu; bod je na konci baru, keď je hodnota známa."""
        end_ms = bar.time + self.step_ms
        prev = self._vwap_point
        self._vwap_point = (end_ms, vwap, self.vwap.day)
        if prev is None or prev[2] != self.vwap.day:
            return []
        return [DrawLine(VO_VWAP, prev[0], prev[1], end_ms, vwap, _VWAP_COLOR,
                         obj_id=f"vo_vwap.{end_ms}", text="VWAP")]
