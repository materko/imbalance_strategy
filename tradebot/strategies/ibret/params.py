"""Popisy parametrov IB RETRACE pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕘 Initial Balance a prieraz (New York, HHMM)"
_G1 = "🎯 Vstup a úrovne (zlomok IB od prerazenej hrany)"
_G2 = "🛡️ Cieľ a koniec"
_G3 = "💰 Veľkosť"
_G4 = "🎨 Vizualizácia"
_G5 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu, potvrdenie a filtre"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "ibStart": dict(group=_G0, title="Začiatok IB (HHMM)", inline="ib", tooltip="930 = 9:30 New York."),
    "ibMinutes": dict(group=_G0, title="Dĺžka IB (min)", inline="ib", tooltip="60 = IB 9:30–10:30 (IB Lab)."),
    "breakFrom": dict(group=_G0, title="Prieraz od (HHMM)", inline="br",
                      tooltip="Otvorenie sviečky, ktorá zavrela za IB. IB Lab filtruje 10:30, 10:35, 10:40 …"),
    "breakTo": dict(group=_G0, title="Prieraz do (HHMM)", inline="br",
                    tooltip="Neskorší prvý prieraz = v ten deň bez obchodu."),
    "tradeMon": dict(group=_G0, title="Po", inline="dni", tooltip="Obchodovať v pondelok."),
    "tradeTue": dict(group=_G0, title="Ut", inline="dni", tooltip="Obchodovať v utorok."),
    "tradeWed": dict(group=_G0, title="St", inline="dni", tooltip="Obchodovať v stredu."),
    "tradeThu": dict(group=_G0, title="Št", inline="dni", tooltip="Obchodovať vo štvrtok."),
    "tradeFri": dict(group=_G0, title="Pi", inline="dni", tooltip="Obchodovať v piatok."),
    "minIbPoints": dict(group=_G0, title="IB najmenej (body)", inline="w", tooltip="0 = bez hranice."),
    "maxIbPoints": dict(group=_G0, title="IB najviac (body)", inline="w", tooltip="0 = bez hranice."),
    "tradeDirection": dict(group=_G0, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "entryMode": dict(group=_G1, title="Vstup",
                      tooltip="pullback = limitka na úrovni návratu do IB; breakout = market na zavretí sviečky prierazu."),
    "entryRetr": dict(group=_G1, title="Limitka na úrovni (× IB)", step=0.05,
                      tooltip="0 = hrana IB, 0,25 = štvrtina IB dovnútra, 0,5 = stred IB."),
    "slRetr": dict(group=_G1, title="Stop na úrovni (× IB)", step=0.05,
                   tooltip="Za max retracementom: video long 0,60–0,69, short 0,70–0,79 v 70 % dní. 1 = druhá strana IB."),
    "slBufferTicks": dict(group=_G1, title="Stop + rezerva (ticky)", tooltip="Odstup stopu za úrovňou."),
    "lastEntry": dict(group=_G1, title="Limitka čaká do (HHMM)", tooltip="Potom sa zruší (video: medián max retracementu 13:30)."),
    "tpMode": dict(group=_G2, title="Cieľ", tooltip="ext = extenzia × IB za prerazenou hranou; rr = RR × stop."),
    "tpExt": dict(group=_G2, title="Extenzia (× IB)", inline="tp", step=0.05, tooltip="Video: medián max extenzie +0,59 IB."),
    "rr": dict(group=_G2, title="RR", inline="tp", step=0.25, tooltip="Pri cieli rr."),
    "minRR": dict(group=_G2, title="Najmenší RR", step=0.1, tooltip="Obchod s menším pomerom cieľ / stop sa vynechá (pravidlo: nie pod 0,5)."),
    "closeAtEnd": dict(group=_G2, title="Zavrieť na konci dňa", inline="end", tooltip="Pozícia sa zavrie na zavretí sviečky o exitTime."),
    "exitTime": dict(group=_G2, title="Čas (HHMM)", inline="end", tooltip="1600 = 16:00 New York (štatistika IB Lab končí 16:00)."),
    "fixedQty": dict(group=_G3, title="Pevný počet kontraktov", tooltip="Zapnuté = qty; vypnuté = veľkosť z rizika v $ k stopu."),
    "qty": dict(group=_G3, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_G3, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "drawRange": dict(group=_G4, title="Kresliť IB", tooltip="Box Initial Balance."),
    "leverage": dict(group=_G5, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
