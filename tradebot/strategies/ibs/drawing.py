"""Druhy kresieb IBS — registrujú sa do `DrawKind` pri importe balíka stratégie.

Hodnoty kopírujú miesta v Pine, aby sa dali porovnať vedľa seba. Generické druhy
(`tp_box`, `sl_box`, `entry`, `exit`, `session`) registruje jadro.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

# -- SD zóny a ich sprievodné boxy (Pine 652, 656, 697, 1684, 1758) ----
SD_ZONE_PRE = DrawKind.register("sd_zone_pre", "SD_ZONE_PRE")  # formácia zóny, bodkovaný obrys bez výplne
SD_ZONE_POST = DrawKind.register("sd_zone_post", "SD_ZONE_POST")  # potvrdená zóna, plná výplň
IMB_BOX = DrawKind.register("imb_box", "IMB_BOX")
PIN_BAR_BOX = DrawKind.register("pin_bar_box", "PIN_BAR_BOX")  # Pine 1572
ENGULFING_BOX = DrawKind.register("engulfing_box", "ENGULFING_BOX")  # Pine 1617
# -- štítky stavového automatu ----------------------------------------
SKIP = DrawKind.register("skip", "SKIP")  # Pine 2042
COUNTER = DrawKind.register("counter", "COUNTER")  # Pine 2265
STATE34 = DrawKind.register("state34", "STATE34")  # Pine 1850 / 1872
EXPIRED = DrawKind.register("expired", "EXPIRED")  # Pine 2173
MAX_DAILY = DrawKind.register("max_daily", "MAX_DAILY")  # Pine 1894
IMB_ZERO = DrawKind.register("imb_zero", "IMB_ZERO")  # Pine 2246 - "0" pri imbalance
# -- display-only moduly ----------------------------------------------
SWING = DrawKind.register("swing", "SWING")  # HH/HL/LH/LL štítky (Pine 750, 762)
STRUCTURE = DrawKind.register("structure", "STRUCTURE")  # BOS/CHoCH čiara + štítok (Pine 781-812)
SR_LEVEL = DrawKind.register("sr_level", "SR_LEVEL")  # Pine 1126 / 1129
SR_GOLDEN = DrawKind.register("sr_golden", "SR_GOLDEN")  # Pine 1114 / 1117
LIQ_SWEEP = DrawKind.register("liq_sweep", "LIQ_SWEEP")  # Pine 1181-1231
ELLIOTT_WAVE = DrawKind.register("elliott_wave", "ELLIOTT_WAVE")  # Pine 1346 / 1357
ELLIOTT_PROJ = DrawKind.register("elliott_proj", "ELLIOTT_PROJ")  # Pine 1425 / 1468

#: Všetky druhy IBS (bez generických) — pre vrstvy grafu a testy.
IBS_KINDS = (
    SD_ZONE_PRE, SD_ZONE_POST, IMB_BOX, PIN_BAR_BOX, ENGULFING_BOX,
    SKIP, COUNTER, STATE34, EXPIRED, MAX_DAILY, IMB_ZERO,
    SWING, STRUCTURE, SR_LEVEL, SR_GOLDEN, LIQ_SWEEP, ELLIOTT_WAVE, ELLIOTT_PROJ,
)
