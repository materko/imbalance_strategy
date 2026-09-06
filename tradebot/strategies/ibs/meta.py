"""Metadáta IBS pre webapp: čo sa z Pine vyparsovať nedá (vstupy vynechané z portu,
polia navyše, závislosti prepínačov, vrstvy grafu).
"""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

#: Pine vstupy, ktoré sa VEDOME neportujú, aj s dôvodom.
REMOVED_INPUTS: frozenset[str] = frozenset({
    # PickMyTrade sa nebude používať (rozhodnutie 2026-09-04) - Freqtrade aj MultiCharts
    # posielajú ordre priamo, žiadny webhook medzi tým nie je.
    "pmtToken",
    "pmtAccountId",
    "pmtStratName",
    "pmtMarketOrderType",
    # Podľa vlastného Pine tooltipu použiteľné LEN pre PickMyTrade - `strategy.exit`
    # v TradingView pre neho nemá ekvivalent, takže bez PMT nemá čo robiť.
    "trailFreqPct",
})

#: Polia, kde sa vedome odchyľujeme od Pine defaultu, aj s dôvodom.
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset({
    # Pine má 0.5 (hodnota pre MNQ). Engine počíta z InstrumentSpec.point_value, takže
    # default je None a hodnota sa zadáva len v referenčných profiloch spolu
    # s legacyPineSizing — viď docs/ARCHITECTURE_port.md §3c.
    "tickDollarValue",
    # Pine color.rgb(51, 65, 85) -> hex; farby sa neporovnávajú číselne.
    "ewLineColor",
})

#: Pine vstupy, ktoré v configu ostali kvôli parite panela, ale v porte nerobia nič,
#: takže vo formulári len zavadzajú. V `IBSConfig` ostávajú, aby profil sedel s TV
#: panelom, a do uloženého profilu sa zapíšu s Pine defaultom.
#:
#: `alert*` posielali notifikáciu TradingView — vo Freqtrade notifikácie rieši sám
#: Freqtrade (Telegram) v live režime, v backteste nemajú význam.
#:
#: `showDashboard`, `showTradeLog`, `showDebugTable` a ich pozície/počty riadkov kreslili
#: tabuľky **na graf v TradingView**. Port ich nekreslí a ani nemá kam — históriu behov,
#: zoznam obchodov aj dôvody výstupu ukazuje webapp vo vlastných tabuľkách. Kresliaci
#: prepínač `showImbalance` medzi ne nepatrí: ten engine číta (`engine.py`) a rozhoduje,
#: či sa do kresieb behu dostanú imbalance boxy.
INERT_INPUTS: frozenset[str] = frozenset({
    "alertOnState2", "alertOnState3", "alertOnState4",
    "showDashboard", "dashPos", "dashboardRows",
    "showTradeLog", "tradeLogRows",
    "showDebugTable", "debugTableRows", "debugPos",
})

PARAM_NOTES: dict[str, str] = {
    "state4MaxBars": "Pine tento parameter nikde nepoužíva.",
    "maxSdZones": ("Strop je Pine dedičstvo (limit boxov na grafe a pamäte), Freqtrade ho "
                   "nepotrebuje — port ho drží kvôli parite: nad limitom sa najstaršia zóna "
                   "zahodí a už nikdy nevystrelí. Pri bežnom zoneValidHours (6 h) sú to len "
                   "dávno vypršané zóny, takže výsledok neovplyvní; keby strop zahodil ešte "
                   "platnú zónu, beh to napíše do logu. Pine si sám zaškrtáva na 200."),
    "enableTrading": ("V porte to nie je prepínač live/papier — to rieši `dry_run` v configu "
                      "Freqtradu. Vypnuté tu znamená, že stratégia neotvorí ani jeden obchod: "
                      "beh dobehne, ale skončí s nulou obchodov (zóny, gapy a kresby bežia ďalej). "
                      "V Pine malo pole zmysel na graf pripojený k reálnemu účtu."),
}

#: Metadáta polí, ktoré Pine nemá — ručne, lebo niet odkiaľ ich parsovať.
PORT_ONLY_META: dict[str, dict[str, Any]] = {
    "atrLen": dict(
        title="ATR dĺžka pre jednotku „atr“",
        tooltip="Dĺžka ATR na grafovom TF, z ktorej sa prepočítavajú parametre zadané v jednotke atr. "
        "V Pine ATR nie je; slúži na prenos prahov medzi nástrojmi s inou cenovou škálou.",
    ),
    "legacyPineSizing": dict(
        title="Pine sizing (1 kontrakt/BTC, ako TradingView)",
        tooltip="Doslovný Pine vzorec veľkosti pozície vrátane int() a max(1, …) — na BTC vždy 1 BTC bez ohľadu "
        "na maxLossDollar. Zapnúť len na porovnanie s TradingView. Vyžaduje tickDollarValue.",
    ),
    "leverage": dict(
        title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based sizingu, "
        "ktorá by sa inak na účet nezmestila (stake by sa orezal a riziko by bolo menšie než maxLossDollar).",
    ),
    "minSlDistance": dict(
        title="Min. vzdialenosť SL od vstupu",
        tooltip="Obchod s tesnejším SL sa preskočí (SKIP: SL PRILIS TESNY). Poplatok je percento z nominálu, "
        "zisk rastie s R — tesné SL majú najhorší pomer edge k poplatku. 0 = vypnuté. "
        "Odporúčaná jednotka pct (0,20 % ceny), viď docs/OPTIMALIZACIA_2026-09-05.md.",
    ),
}

#: Závislosti medzi vstupmi. Pine ich nedeklaruje (panel v TradingView ukazuje vždy
#: všetko), tak sú tu ručne. `switches`: podnastavenia v `params` majú zmysel, len keď
#: je aspoň jeden z prepínačov zapnutý — formulár ich inak skryje. `show`: kresliaci
#: prepínač tej istej feature; formulár ho zrkadlí hneď vedľa hlavného prepínača, keď
#: sú v Pine v rôznych skupinách. Reťazenie funguje (volume filter je pod SD zónami).
FEATURES: list[dict[str, Any]] = [
    {"switches": ["enableImbEntry"], "show": "showImbalance",
     "params": ["state1MaxBars", "state2MaxBars", "state2ConfirmTicks", "state3MaxBars"]},
    {"switches": ["enablePinBarEntry"], "params": ["pbWickToBodyRatio", "pbBodyPositionPct", "pbMinRangePoints"]},
    {"switches": ["enableEngulfingEntry"],
     "params": ["engMinRangePoints", "engSizeAvgLen", "engSizeMultiplier", "engTouchWindowBars"]},
    {"switches": ["enablePinBarEntry", "enableEngulfingEntry"], "params": ["pbEngOrderType"]},
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["enableZoneDetection"],
     "params": ["enableGapDetection", "zoneDetectionTF", "zoneValidHours", "maxSdZones", "snapMode",
                "invalidateOnFill", "useVolumeFilter"]},
    {"switches": ["enableGapDetection"], "params": ["imbLookback", "imbMaxDistTicks", "minImbSizePoints"]},
    {"switches": ["useVolumeFilter"], "params": ["volumeFilterBlockTrading", "volSmaLen", "volMultiplier"]},
    *[{"switches": [f"sess{i}On"],
       "params": [f"sess{i}{part}{hm}" for part in ("ZoneStart", "ZoneEnd", "TradeStart", "TradeEnd") for hm in "HM"]}
      for i in (1, 2, 3)],
    {"switches": ["useStructureFilter", "showMarketStructure"], "params": ["structureSwingLen"]},
    {"switches": ["enableSrTrading", "showSR"], "show": "showSR",
     "params": ["srSwingLen", "srClusterPoints", "srMinTouches", "srMaxLevels", "srLookbackDays", "srZoneSaturationPct"]},
    {"switches": ["enableLqTrading", "showLiqSweep"], "show": "showLiqSweep",
     "params": ["liqSweepLen", "liqSweepMinWick", "liqSweepConfirmBars", "liqStrengthLen"]},
    {"switches": ["showElliott"], "params": ["ewSwingLen", "ewMinWavePoints", "ewShowLabels", "ewShowProjection", "ewLineColor"]},
    {"switches": ["ewShowProjection"], "params": ["ewProjExtendBars"]},
]

#: Vrstvy grafu páru (prepínače vo webapp) a ľudské názvy druhov kresieb.
LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("session", "Seansy", ("session",), "#6366f1"),
    ChartLayer("zones", "SD zóny", ("sd_zone_pre", "sd_zone_post"), "#be3c46"),
    ChartLayer("imb", "Imbalance", ("imb_box", "imb_zero"), "#94a3b8", hollow_kinds=("imb_box",)),
    ChartLayer("patterns", "Pin bar / Engulfing", ("pin_bar_box", "engulfing_box"), "#d97706"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
    ChartLayer("labels", "Štítky stavov", ("skip", "counter", "state34", "expired", "max_daily"), "#334155"),
    ChartLayer("structure", "Štruktúra (BOS/CHoCH)", ("swing", "structure"), "#334155"),
    ChartLayer("sr", "S/R úrovne", ("sr_level", "sr_golden"), "#3b82f6"),
    ChartLayer("liq", "Likvidita", ("liq_sweep",), "#9333ea"),
    ChartLayer("elliott", "Elliott", ("elliott_wave", "elliott_proj"), "#0d9488"),
)

KIND_TITLES: dict[str, str] = {
    "sd_zone_pre": "SD zóna (formácia)", "sd_zone_post": "SD zóna", "imb_box": "Imbalance sviečka", "imb_zero": "Imbalance 0",
    "pin_bar_box": "Pin bar", "engulfing_box": "Engulfing", "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
    "skip": "SKIP", "counter": "Počítadlo", "state34": "STATE 3/4", "expired": "Expirovaný order", "max_daily": "Denný limit",
    "swing": "Swing", "structure": "Štruktúra", "sr_level": "S/R úroveň", "sr_golden": "S/R golden", "liq_sweep": "Liquidity sweep",
    "elliott_wave": "Elliott vlna", "elliott_proj": "Elliott projekcia", "session": "Seansa",
}
