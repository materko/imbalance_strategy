"""Popisy parametrov pre formulár webapp — pri stratégii, nie v Pine.

Zdroj pravdy pre to, **ako sa parameter volá po ľudsky a čo robí**. Rozsahy a defaulty
sem nepatria: tie sú v `config.py` (`CONSTRAINTS` a defaulty dataclass) a formulár si ich
vyzdvihne odtiaľ, takže sa nemá ako rozísť s tým, čo config prijme. Zoznam hodnôt enumu
sa dopĺňa sám z `ENUM_FIELDS`.

Prečo pri stratégii a nie v Pine: Pine skript vzniká len na vyžiadanie (aby sa stratégia
dala pozrieť na TradingView) a formulár na ňom nesmie závisieť.

Tento súbor vznikol jednorazovým prevodom z demo_breakout.pine; odvtedy sa mení tu.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

#: Poradie skupín vo formulári.
GROUPS: tuple[str, ...] = (
    "🎯 Obchodovanie",
    "💰 Riziko",
    "🎨 Vizualizacia",)

#: `pole configu -> {group, title, tooltip, [step], [options], [inline]}`.
PARAMS: dict[str, dict[str, Any]] = {
    "channelLen": dict(group="🎯 Obchodovanie", title="Dlzka kanala (bary)",
        tooltip="Kolko predchadzajucich barov tvori Donchian kanal. Close nad jeho hornou hranou = "
                "LONG breakout, pod dolnou = SHORT breakout. Aktualny bar sa do kanala nepocita.",
    ),
    "atrLen": dict(group="🎯 Obchodovanie", title="ATR dlzka",
        tooltip="Dlzka ATR (Wilder), z ktoreho sa pocita vzdialenost SL.",
    ),
    "slAtrMult": dict(group="🎯 Obchodovanie", title="SL vzdialenost (nasobok ATR)", step=0.1,
        tooltip="Stop loss = vstup -/+ tolkoto nasobkov ATR. Jednotka atr, aby to sedelo na kazdom "
                "nastroji.",
    ),
    "rrRatio": dict(group="🎯 Obchodovanie", title="Risk:Reward pomer", step=0.5,
        tooltip="Take profit = rrRatio × vzdialenost SL.",
    ),
    "allowShort": dict(group="🎯 Obchodovanie", title="Povolit short",
        tooltip="Vypnute = obchoduje sa len LONG breakout hornej hrany kanala.",
    ),
    "exitMode": dict(group="🎯 Obchodovanie", title="Vystup",
        tooltip="opposite = otvorena pozicia sa zavrie aj pri opacnom breakoute (okrem SL/TP); "
                "tp_only = len SL alebo TP.",
    ),
    "riskDollar": dict(group="💰 Riziko", title="Riziko na obchod ($)", step=10.0,
        tooltip="Velkost pozicie = riziko / vzdialenost SL. 0 = 1 kontrakt.",
    ),
    "showChannel": dict(group="🎨 Vizualizacia", title="Kreslit kanal",
        tooltip="Zapne/vypne kreslenie hornej a dolnej hrany Donchian kanala.",
    ),
    "leverage": dict(title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based "
                "sizingu, ktorá by sa inak na účet nezmestila.",
    ),
}
