"""Popisy parametrov VA NÁVRAT 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '📊 Value area (predošlý deň RTH)'
_G1 = '🕘 Návrat a vstup (New York)'
_G2 = '🛡️ Stop a cieľ'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'vaPct': dict(group=_G0, title='Value area (% objemu)', tooltip='Klasicky 70 %.'),
    'vaBinPct': dict(group=_G0, title='Kôš profilu (% ceny)', tooltip='Veľkosť koša pre objem (0,05 % ≈ 10 bodov na NQ 20 000).'),
    'vaMethod': dict(group=_G0, title='Výpočet VA', options=['rank', 'expand'], tooltip='rank = najobjemnejšie koše (prieskum), expand = rozširovanie od POC.'),
    'returnBarMin': dict(group=_G1, title='Sviečka návratu (min)', tooltip='Návrat = zavretie tejto sviečky (od 9:30) späť vo VA.'),
    'minOpenOutside': dict(group=_G1, title='Otvorenie mimo VA aspoň (× šírka VA)', tooltip='0 = stačí otvoriť mimo.'),
    'lastEntry': dict(group=_G1, title='Posledný vstup (HHMM)', tooltip='Prieskum: 12:00–14:00.'),
    'exitTime': dict(group=_G1, title='Výstup v čase (HHMM)', tooltip='Intraday — pozícia cez noc nejde.'),
    'requireOpenOutside': dict(group=_G1, title='Len dni s otvorením mimo VA', tooltip='Vypnuté = signál dá aj výbeh mimo VA počas dňa (zavretie sviečky mimo VA a návrat).'),
    'maxTradesPerDay': dict(group=_G1, title='Max obchodov za deň', tooltip='Po pokuse sa stratégia znova nabije zavretím sviečky mimo VA.'),
    'allowLong': dict(group=_G1, title='Long', inline='dir', tooltip=''),
    'allowShort': dict(group=_G1, title='Short', inline='dir', tooltip=''),
    'tpMode': dict(group=_G2, title='Cieľ', options=['poc', 'opp', 'mid', 'rr'], tooltip='poc = včerajší POC, opp = opačný okraj VA, mid = stred VA, rr = pevné RR × stop.'),
    'rrRatio': dict(group=_G2, title='RR (pri cieli rr)', tooltip='Cieľ = vstup ± RR × vzdialenosť stopu; najmenej 0,5.'),
    'slBufferVa': dict(group=_G2, title='Rezerva stopu (× šírka VA)', tooltip='Stop za extrémom dňa od otvorenia + rezerva.'),
    'maxStopAtr': dict(group=_G2, title='Stop najviac (× denné ATR)', tooltip='0 = bez filtra; inak sa obchod so stopom ďalej ako toľko denných ATR (14 dní RTH) preskočí — dni s veľkým výbehom mimo VA.'),
    'minRR': dict(group=_G2, title='Najmenší RR', tooltip='Obchod s cieľom bližším ako minRR × stop sa preskočí (pravidlo RR ≥ 0,5).'),
    'fixedQty': dict(group=_G2, title='Pevný počet kontraktov', tooltip=''),
    'riskDollar': dict(group=_G2, title='Riziko na obchod ($)', tooltip='Pri vypnutom pevnom počte.'),
    'showLevels': dict(group=_G2, title='Kresliť VA a POC', tooltip=''),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
