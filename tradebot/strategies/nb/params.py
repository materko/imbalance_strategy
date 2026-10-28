"""Popisy parametrov NB pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📈 Trend (vyšší TF)"
_G1 = "📦 Konsolidácia (graf)"
_G2 = "🎯 Vstup (čas New York)"
_G3 = "🛡️ Stop a cieľ"
_G4 = "💰 Veľkosť"
_G5 = "🎨 Vizualizácia"
_G6 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "htfTF": dict(group=_G0, title="TF trendu (min)", tooltip="240 = H4. Sviečky sa skladajú zo sviečok grafu."),
    "smaFast": dict(group=_G0, title="SMA rýchla", inline="sma", tooltip="Zo zavretí, na vyššom TF aj na grafe (Nikola: 10)."),
    "smaSlow": dict(group=_G0, title="pomalá", inline="sma", tooltip="Nikola: 20 — samotná 10 dávala falošné prierazy."),
    "useHtfTrend": dict(group=_G0, title="Len v smere trendu vyššieho TF",
                        tooltip="Uptrend = rýchla SMA nad pomalou → len longy; downtrend → len shorty."),
    "htfNeedClose": dict(group=_G0, title="… a zavretie za rýchlou SMA",
                         tooltip="Uptrend len keď posledná sviečka vyššieho TF zavrela nad rýchlou SMA (downtrend pod ňou)."),
    "useChartSma": dict(group=_G0, title="SMA grafu v smere obchodu",
                        tooltip="Long len keď je zavretie nad oboma SMA grafu a rýchla nad pomalou („SMA ukážu smer“)."),
    "consBars": dict(group=_G1, title="Konsolidácia (sviečok)", tooltip="Posledných toľko sviečok grafu vrátane knôtov."),
    "atrLen": dict(group=_G1, title="ATR grafu (dĺžka)", tooltip="Jednotka šírky konsolidácie a rezervy stopu."),
    "consMinWidth": dict(group=_G1, title="Šírka od (0 = bez)", inline="cw", tooltip="High − low okna."),
    "consMaxWidth": dict(group=_G1, title="do", inline="cw",
                         tooltip="Širšie okno nie je konsolidácia, ale pohyb — a stop by bol ďaleko."),
    "allowLong": dict(group=_G2, title="Longy", tooltip="Prieraz nahor v uptrende."),
    "allowShort": dict(group=_G2, title="Shorty", tooltip="Prieraz nadol v downtrende."),
    "entryOffsetTicks": dict(group=_G2, title="Stop order za hranou (tickov)",
                             tooltip="Vstup hneď pri prieraze, bez čakania na zavretie sviečky."),
    "entryStartH": dict(group=_G2, title="Vstupy od (H)", inline="es", tooltip="2:00 NY = 8:00 SK (Londýn)."),
    "entryStartM": dict(group=_G2, title="M", inline="es", tooltip="Minúta."),
    "entryEndH": dict(group=_G2, title="Vstupy do (H)", inline="ee", tooltip="16:00 NY = 22:00 SK."),
    "entryEndM": dict(group=_G2, title="M", inline="ee", tooltip="Minúta."),
    "tradeMon": dict(group=_G2, title="Po", inline="dn", tooltip="Deň New York."),
    "tradeTue": dict(group=_G2, title="Ut", inline="dn", tooltip="Deň New York."),
    "tradeWed": dict(group=_G2, title="St", inline="dn", tooltip="Deň New York."),
    "tradeThu": dict(group=_G2, title="Št", inline="dn", tooltip="Nikole sa najlepšie darí po–st."),
    "tradeFri": dict(group=_G2, title="Pi", inline="dn", tooltip="Deň New York."),
    "maxTradesPerDay": dict(group=_G2, title="Max obchodov za deň (0 = bez)", tooltip="Deň New York."),
    "slBuffer": dict(group=_G3, title="Rezerva SL za konsolidáciou",
                     tooltip="Stop = opačná hrana + rezerva + 1 tick (Nikola: 5 pipov)."),
    "rrRatio": dict(group=_G3, title="RRR (cieľ = RR × riziko)", step=0.1, tooltip="Nikola: 3."),
    "useRoom": dict(group=_G3, title="Miesto do cieľa",
                    tooltip="Najbližší swing vyššieho TF v smere obchodu musí byť aspoň toľko R od vstupu, inak sa nevstúpi."),
    "roomMinR": dict(group=_G3, title="Miesto aspoň (R)", step=0.1, tooltip="Nikola: pod 2,5 R obchod neberie."),
    "pivotLen": dict(group=_G3, title="Swing vyššieho TF (sviečok z každej strany)",
                     tooltip="Vrchol / dno, ktoré má po oboch stranách toľko sviečok nižšie / vyššie."),
    "maxHoldHours": dict(group=_G3, title="Zavrieť po (hodinách, 0 = nie)",
                         tooltip="Obchod, ktorý nedošiel do stopu ani cieľa, sa zavrie trhom."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)", tooltip="Pri vypnutom pevnom počte."),
    "showZones": dict(group=_G5, title="Kresliť konsolidácie", tooltip="Box konsolidácie pri vstupe."),
    "leverage": dict(group=_G6, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
