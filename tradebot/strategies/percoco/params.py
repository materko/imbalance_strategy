"""Popisy parametrov Craig Percoco 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🧭 15m: smer a body záujmu"
_G1 = "🎯 1m vstup: CHoCH + FVG"
_G2 = "🚦 Okno obchodovania"
_G3 = "🛡️ Stop a cieľ"
_G4 = "💰 Riziko"
_G5 = "🎨 Vizualizacia"
_G6 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu, potvrdenie a filtre"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "htfTF": dict(group=_G0, title="Vyšší TF (min)", tooltip="Na akom TF sa číta smer a FVG. Video: 15m. Skladá sa z grafu."),
    "htfSwingLen": dict(group=_G0, title="Swing: sviečok z každej strany", tooltip="Pivot na vyššom TF potvrdený toľkými sviečkami."),
    "useHtfBias": dict(group=_G0, title="Len v smere 15m trendu", tooltip="Trend = smer posledného prierazu swingu zavretím (BOS / CHoCH)."),
    "useHtfPoi": dict(group=_G0, title="Len po dotyku 15m FVG", tooltip="CHoCH musí prísť krátko po tom, čo cena zasiahla nevyplnené 15m FVG v smere."),
    "htfFvgMinAtr": dict(group=_G0, title="15m FVG: min. veľkosť (ATR)", tooltip="ATR na 15m. 0 = každé FVG."),
    "htfFvgMaxBars": dict(group=_G0, title="15m FVG platí (sviečok)", tooltip="Po toľkých 15m sviečkach FVG zaniká. 288 = 3 dni."),
    "poiBars": dict(group=_G0, title="Od dotyku FVG po CHoCH (sviečok)", tooltip="Najviac toľko sviečok grafu medzi dotykom 15m FVG a CHoCH."),
    "swingLen": dict(group=_G1, title="Swing na grafe: sviečok z každej strany", tooltip="Pivoty na 1m pre CHoCH."),
    "fvgMinAtr": dict(group=_G1, title="FVG: min. veľkosť (ATR)", tooltip="ATR grafu. 0 = každé FVG."),
    "entryPct": dict(group=_G1, title="Limitka vo FVG (%)", tooltip="50 = stred FVG (video), 0 = bližšia hrana, 100 = vzdialenejšia."),
    "setupMaxBars": dict(group=_G1, title="Setup platí (sviečok)", tooltip="Po toľkých sviečkach od CHoCH bez vyplnenia setup zaniká."),
    "tradeDirection": dict(group=_G1, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G1, title="Max. obchodov za deň", tooltip="Denný strop vstupov."),
    "weekdaysOnly": dict(group=_G2, title="Len pondelok–piatok", tooltip="Cez víkend sa neobchoduje."),
    "useTradeWindow": dict(group=_G2, title="Obchodné okno", tooltip="CHoCH a vstup len v zadaných hodinách. Video: od otvorenia NY 9:30."),
    "tradeTZ": dict(group=_G2, title="Časové pásmo okna", tooltip="Predvolene New York."),
    "tradeStartH": dict(group=_G2, title="Okno od (H)", inline="tws", tooltip="Začiatok okna — hodina."),
    "tradeStartM": dict(group=_G2, title="M", inline="tws", tooltip="Začiatok okna — minúta."),
    "tradeEndH": dict(group=_G2, title="Okno do (H)", inline="twe", tooltip="Koniec okna — hodina."),
    "tradeEndM": dict(group=_G2, title="M", inline="twe", tooltip="Koniec okna — minúta."),
    "slBufferAtr": dict(group=_G3, title="Rezerva za low / high pohybu (ATR)", tooltip="Stop je za extrémom pohybu CHoCH."),
    "rrRatio": dict(group=_G3, title="Cieľ (násobok rizika)", step=0.25, tooltip="Video: 1:3 až 1:4."),
    "atrLen": dict(group=_G3, title="ATR dĺžka", tooltip="Predvolene 14."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)", tooltip="Strata na stope v dolároch."),
    "showHtfFvg": dict(group=_G5, title="Kresliť 15m FVG", tooltip="Body záujmu z vyššieho TF."),
    "showStructure": dict(group=_G5, title="Kresliť CHoCH", tooltip="Prerazená úroveň swingu na grafe."),
    "tickDollarValue": dict(group=_G6, title="Hodnota ticku ($)", type="float", tooltip="Len pre Pine vzorec veľkosti pozície."),
    "legacyPineSizing": dict(group=_G6, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G6, title="Min. vzdialenosť SL od vstupu", tooltip="Obchod s tesnejším stopom sa preskočí (% z ceny). 0 = vypnuté."),
    "leverage": dict(group=_G6, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
