"""Druhy kresieb divergenčnej stratégie. Prefix `dv_`, aby sa v spoločnom registri
nezliali s druhmi IBS a štruktúry."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

#: spojnica pivot → bar divergencie (na cene) a štítok s indikátormi
DV_BULL = DrawKind.register("dv_bull", "DV_BULL")
DV_BEAR = DrawKind.register("dv_bear", "DV_BEAR")
DV_LINE_BULL = DrawKind.register("dv_line_bull", "DV_LINE_BULL")
DV_LINE_BEAR = DrawKind.register("dv_line_bear", "DV_LINE_BEAR")
#: supertrend na grafe (segment na bar, farba podľa trendu) a čiara druhého vyššieho TF
DV_ST_UP = DrawKind.register("dv_st_up", "DV_ST_UP")
DV_ST_DOWN = DrawKind.register("dv_st_down", "DV_ST_DOWN")
DV_ST_HTF = DrawKind.register("dv_st_htf", "DV_ST_HTF")
#: pozadie: zónový filter blokuje long (medvedia zóna) / short (býčia zóna)
DV_ZONE_BEAR = DrawKind.register("dv_zone_bear", "DV_ZONE_BEAR")
DV_ZONE_BULL = DrawKind.register("dv_zone_bull", "DV_ZONE_BULL")
#: vyzbrojený vstup (confirm) a vstup
DV_ARMED = DrawKind.register("dv_armed", "DV_ARMED")
DV_ENTRY = DrawKind.register("dv_entry", "DV_ENTRY")
