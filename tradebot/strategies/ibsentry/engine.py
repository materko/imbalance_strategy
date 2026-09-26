"""Engine IBS Entry Zone — IBS plus štvrtý zdroj zón: veľké imbalance z vyšších TF.

IBS dnes obchoduje zóny z troch zdrojov: SD pattern, S/R úrovne a likvidita. Všetky
končia v tej istej knihe (`ZoneBook`) a ďalej ich rieši ten istý stavový automat.
Táto stratégia pridáva štvrtý: fair value gap z 5m, 15m, 30m a 1h.

Zóna z FVG sa teda **značí rovnako ako SD zóna a obchoduje sa rovnakým modelom** —
nie je to filter a entry modely (imbalance, pin bar, engulfing) sa na ňu vzťahujú
presne tak ako na každú inú zónu.

Smer: bullish FVG je medzera pod cenou, čiže dopyt → LONG zóna. Bearish je ponuka → SHORT.
"""

from __future__ import annotations

import math

from tradebot.core.engine import EngineOutput
from tradebot.core.types import Bar, Direction, InstrumentSpec

from ..ibs.engine import IBSEngine
from ..ibs.zones import ZoneSource
from .config import IBSEntryZoneConfig
from .fvg import FvgDetector

__all__ = ["IBSEntryZoneEngine"]


class IBSEntryZoneEngine(IBSEngine):
    """`IBSEngine`, ktorý do knihy zón pridáva aj veľké imbalance z vyšších TF."""

    def __init__(self, cfg: IBSEntryZoneConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        super().__init__(cfg, inst, chart_tf_minutes)
        self._tfs = cfg.active_fvg_timeframes()
        self.fvg = FvgDetector(self._tfs)
        #: koľko zón z FVG (a z IFVG) vrstva doteraz vyrobila — čítajú to testy a ladenie
        self.fvg_zones_created = 0
        self.ifvg_zones_created = 0
        # `required_history` je v IBS obyčajný atribút, nie property — dorovná sa tu tak,
        # aby bolo z čoho zložiť tri sviečky najvyššieho zapnutého TF.
        if (cfg.enableFvgTrading or cfg.enableIfvgTrading) and self._tfs:
            need = 3 * math.ceil(max(self._tfs) / self.chart_tf_minutes) + 1
            self.required_history = max(self.required_history, need)

    def _spawn_extra_zones(self, bar: Bar, out: EngineOutput) -> None:
        """Hook z `IBSEngine` — volá sa na tom istom mieste ako S/R a likvidita."""
        fvg_on, ifvg_on = self.cfg.enableFvgTrading, self.cfg.enableIfvgTrading
        if not (fvg_on or ifvg_on) or not self._tfs:
            return
        min_size = self.cfg.fvgMinSize.resolve(self.inst, price=bar.close, atr=self.history.atr)
        # Medzera sa sleduje kvôli inverzii tak dlho, ako by žila jej zóna.
        hits = self.fvg.on_bar(bar, min_size, max_age_ms=int(self.cfg.zoneValidHours * 3_600_000))
        if fvg_on:
            for hit in hits:
                self._push_gap_zone(hit, "FVG", bar, out)
                self.fvg_zones_created += 1
        if ifvg_on:
            for hit in self.fvg.inverted:
                self._push_gap_zone(hit, "IFVG", bar, out)
                self.ifvg_zones_created += 1

    def _push_gap_zone(self, hit, label: str, bar: Bar, out: EngineOutput) -> None:
        """Medzera -> obyčajná zóna v knihe (smer podľa `hit.direction`)."""
        direction = Direction.LONG if hit.direction == 1 else Direction.SHORT
        zone = self.book.create_raw(direction, hit.top, hit.bot, bar.time, ZoneSource.FVG)
        zone.created_bar_index = self.history.bar_index
        zone.variant = f"{label}{hit.tf_minutes}m"
        out.drawings.extend(zone.boxes(self.chart_tf_minutes * 60_000))
