"""Čo o ladení ukážkovej stratégie vieme — a hlavne, ako to má vyzerať.

Pri IBS je obsah tejto triedy zápis merania. Tu meranie za sebou nemáme (ukážka nie je
obchodné odporúčanie), takže je to vzor tvaru: **ktoré tri veci vie povedať len
stratégia** a generická časť ich z configu nevyčíta —

1. `SUGGESTED` — čo sa oplatí ladiť. Že `rrRatio` je float 0,5–10, vie config;
   že práve pomer TP k SL a dĺžka kanála sú tie dve veci, ktoré menia štruktúru
   obchodu a nie citlivosť filtra, vie len stratégia.
2. `FEATURE_PARAMS` — ktorý parameter riadi ktorú vlastnosť obchodu. Vďaka tomu
   analytika nekončí zistením „obchody s tesným stopom nezarábajú", ale odkazom na
   parameter, ktorý sa tým dá zmeniť.
3. `constrain` — väzby medzi parametrami. Donchian breakout žiadnu nemá (parametre sú
   nezávislé), preto sa tu neprepisuje; vzor väzby je v `tradebot/strategies/ibs/hyperopt.py`.

Rozsahy nižšie sú „rozumné okolie defaultu", nie výsledok hľadania — kto ich berie ako
odporúčanie, berie ako odporúčanie ukážku.
"""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion

__all__ = ["DemoBreakoutHyperopt"]


class DemoBreakoutHyperopt(StrategyHyperopt):
    """Ladenie ukážky: štyri parametre, žiadne väzby, žiadne meranie za chrbtom."""

    NOTE: ClassVar[str] = (
        "Ukazkova strategia - rozsahy su rozumne okolie defaultu, nie vysledok merania. "
        "Zaver z hyperoptu nad nou plati o ramci (ze cela cesta funguje), nie o trhu."
    )

    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        # Pomer TP k SL mení štruktúru obchodu, nie citlivosť filtra — najsilnejšia páka.
        "rrRatio": {"low": 1.0, "high": 5.0, "step": 0.5},
        # Dĺžka kanála rozhoduje, čo ešte je prerazenie: krátky kanál dá veľa signálov v šume.
        "channelLen": {"low": 10, "high": 60},
        # Vzdialenosť stopu v ATR — prenositeľná medzi trhmi, na rozdiel od prahu v bodoch.
        "slAtrMult": {"low": 0.5, "high": 4.0, "step": 0.25, "unit": "atr"},
        "allowShort": {"choices": [False, True]},
    }

    #: Vlastnosť obchodu -> parameter, ktorým sa dá zmeniť (`tester/analytics.py`).
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {
        "sl_pct": "slAtrMult",        # vzdialenosť stopu je priamo tento násobok ATR
        "rr_planned": "rrRatio",      # plánovaný pomer TP k SL
        "direction": "allowShort",    # keď celý edge nesie jedna strana
        "duration_min": "exitMode",   # čím obchod končí: opačný breakout alebo TP
    }

    WARN: ClassVar[dict[str, str]] = {
        "riskDollar": "riziko na obchod nemení edge, len veľkosť pozície — break-even "
                      "poplatok od neho nezávisí, takže sa ladiť nemá čo",
        "leverage": "páka nemení signály; ovplyvní len to, či sa pozícia zmestí na účet",
    }
