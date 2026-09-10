"""Druhy kresieb stratégie tržnej štruktúry.

Prefix `st_` je zámerný: IBS má vlastné `swing` a `structure` (jej štruktúrny filter)
a registr druhov je spoločný pre celý repozitár, takže by sa dva významy zliali
do jedného prepínača vo webapp.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

#: potvrdený swing — kreslí sa až na bare, ktorý ho potvrdil, ale na mieste swingu
ST_SWING_HIGH = DrawKind.register("st_swing_high", "ST_SWING_HIGH")
ST_SWING_LOW = DrawKind.register("st_swing_low", "ST_SWING_LOW")
#: referenčná úroveň swingu; končí presne tam, kde ju bar zavretím prerazil
ST_LEVEL = DrawKind.register("st_level", "ST_LEVEL")
ST_BOS = DrawKind.register("st_bos", "ST_BOS")
ST_CHOCH = DrawKind.register("st_choch", "ST_CHOCH")
ST_ENTRY = DrawKind.register("st_entry", "ST_ENTRY")
