"""Dvojstupňový trailing z pôvodného `custom_stoploss` ako `TrailingPlan`.

Pôvodná stratégia vracala Freqtradu relatívny stop podľa zisku:

* zisk 1,5 % – 4 %: stop = `current_profit − 0,35 %` pod aktuálnou cenou, čo po
  ratchete (`adjust_stop_loss` stop len uťahuje) znamená **zámok** na vstup + 0,35 %;
* zisk nad 4 %: stop 1 % pod aktuálnou cenou — obyčajný trailing s odstupom 1 %.

Generický `TrailingPlan` má jednu aktiváciu a jeden odstup; tento potomok pridáva zámok.
Adaptéry ho nepoznajú menom — volajú `plan.trailing.stop_price(...)` polymorfne
(MC runner, emulátor), Freqtrade vetva ho stavia znova v `freqtrade.py`.

Percentá sú z **ceny vstupu**, nie z marže: pôvodné `strat_lvrg` násobilo prahy pákou
práve preto, aby z percent marže vyšli percentá ceny.
"""

from __future__ import annotations

from dataclasses import dataclass

from tradebot.core.risk import TrailingPlan
from tradebot.core.types import Direction, InstrumentSpec

__all__ = ["TwoStageTrailing"]


@dataclass(frozen=True, slots=True)
class TwoStageTrailing(TrailingPlan):
    #: od akého zisku (v cene) sa stop presunie na zámok a kde zámok leží (nad vstupom)
    lock_activation_distance: float = 0.0
    lock_level_distance: float = 0.0

    def stop_price(self, direction: Direction, entry: float, base_stop: float, extreme: float) -> float:
        if direction is Direction.LONG:
            gain = extreme - entry
            stop = base_stop
            if self.lock_activation_distance > 0 and gain >= self.lock_activation_distance:
                stop = max(stop, entry + self.lock_level_distance)
            if gain >= self.activation_price_distance:
                stop = max(stop, extreme - self.offset_price_distance)
            return stop
        gain = entry - extreme
        stop = base_stop
        if self.lock_activation_distance > 0 and gain >= self.lock_activation_distance:
            stop = min(stop, entry - self.lock_level_distance)
        if gain >= self.activation_price_distance:
            stop = min(stop, extreme + self.offset_price_distance)
        return stop

    @classmethod
    def from_config(cls, cfg, inst: InstrumentSpec, entry: float) -> "TwoStageTrailing | None":
        """Percentá z configu → cenové vzdialenosti pre konkrétny vstup."""
        if not cfg.enableTrailing or entry <= 0 or inst.tick_size <= 0:
            return None
        activation = float(cfg.trailActivationPct) / 100.0 * entry
        offset = float(cfg.trailOffsetPct) / 100.0 * entry
        lock_act = float(cfg.beActivationPct) / 100.0 * entry
        lock_lvl = float(cfg.beLockPct) / 100.0 * entry
        return cls(
            activation_price_distance=activation,
            offset_price_distance=offset,
            activation_ticks=activation / inst.tick_size,
            offset_ticks=offset / inst.tick_size,
            lock_activation_distance=lock_act,
            lock_level_distance=lock_lvl,
        )
