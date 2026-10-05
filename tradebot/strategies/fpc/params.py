"""Popisy parametrov FPC 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕘 Obchodné okná (čas New York)"
_G1 = "📰 Správa o 8:30"
_G2 = "➡️ 1. obchod: pokračovanie"
_G3 = "↩️ Návrat k férovej cene"
_G4 = "🎯 Vstupný signál a riadenie"
_G5 = "🚦 Filtre (každý sa zapína zvlášť)"
_G6 = "💰 Riziko"
_G7 = "🎨 Vizualizácia"
_G8 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _G8, _GE)


def _window(k: int, name: str, h: int, m: int) -> dict[str, dict[str, Any]]:
    return {
        f"useS{k}": dict(group=_G0, title=name, inline=f"s{k}",
                         tooltip=f"Okno {name} (default {h}:{m:02d}, 90 min). Férová cena = open prvej sviečky okna."),
        f"s{k}H": dict(group=_G0, title="od (H)", inline=f"s{k}", tooltip="Začiatok okna — hodina (New York)."),
        f"s{k}M": dict(group=_G0, title="M", inline=f"s{k}", tooltip="Začiatok okna — minúta."),
        f"s{k}Len": dict(group=_G0, title="dĺžka (min)", inline=f"s{k}",
                         tooltip="Koľko minút po začiatku sa vstupuje. Video: prvých 90 minút seansy."),
    }


PARAMS: dict[str, dict[str, Any]] = {
    **_window(1, "NY ráno", 9, 30),
    **_window(2, "NY poobede", 14, 0),
    **_window(3, "Ázia", 20, 0),
    **_window(4, "Londýn", 3, 0),
    "pmFair": dict(group=_G0, title="Férová cena poobede",
                   tooltip="open = open poobedného okna; morning = férová cena z rána "
                           "(video: keď 14:00 otvorí dole, vracia to k 9:30)."),
    "newsMode": dict(group=_G1, title="Férová cena v deň správy",
                     tooltip="off = vždy open 9:30; auto = cena pred správou, keď sviečka správy skočí; "
                             "always = cena pred časom správy každý deň."),
    "newsH": dict(group=_G1, title="Čas správy (H)", inline="nt", tooltip="Video: 8:30 New York (CPI, PPI…)."),
    "newsM": dict(group=_G1, title="M", inline="nt", tooltip="Minúta správy."),
    "newsMult": dict(group=_G1, title="Skok = rozsah ≥ × priemer", step=0.5,
                     tooltip="Sviečka správy musí mať aspoň toľkonásobný rozsah ako priemer barov pred ňou."),
    "newsAvgBars": dict(group=_G1, title="Priemer z barov", tooltip="Z koľkých barov pred správou sa ráta priemerný rozsah."),
    "useNewsWin": dict(group=_G1, title="Návrat aj hneď po správe",
                       tooltip="Okno od baru za správou do začiatku NY ráno; cieľ = cena pred správou. "
                               "Video: najsilnejší obchod."),
    "useCont": dict(group=_G2, title="Pokračovanie podľa prvej sviečky",
                    tooltip="Raz za okno: vstup v smere prvej sviečky, keď príde signál v tom smere."),
    "contWin": dict(group=_G2, title="Len prvých N minút", tooltip="Video: pokračovania len prvých ~5 minút."),
    "useBias": dict(group=_G2, title="Len v súlade s biasom",
                    tooltip="Bias = opak pohybu za posledné hodiny (trh za 8 h stúpol → bias short)."),
    "biasH": dict(group=_G2, title="Bias: pohyb za N hodín", tooltip="Video: 6–12 hodín."),
    "contTP": dict(group=_G2, title="TP (body)", inline="ct", tooltip="Video: 38 bodov."),
    "contSL": dict(group=_G2, title="SL (body)", inline="ct", tooltip="Video: 25 bodov."),
    "bigBar": dict(group=_G2, title="Veľká otváracia sviečka nad (body)",
                   tooltip="Väčšia otváracia sviečka: TP aj SL × 2 (76 / 50); veľkosť z rizika vyjde polovičná."),
    "useRev": dict(group=_G3, title="Obchody späť k férovej cene",
                   tooltip="Nad férovou cenou short, pod ňou long, vstup na signál."),
    "tpMode": dict(group=_G3, title="Cieľ", tooltip="fixed = pevné body; fair = cieľ priamo na férovej cene."),
    "revTP": dict(group=_G3, title="TP (body)", inline="rt", tooltip="Video, eval účty: 38."),
    "revSL": dict(group=_G3, title="SL (body)", inline="rt",
                  tooltip="Video: 25 (v NY nikdy menej); stop je pevný od zavretia signálnej sviečky."),
    "minPct": dict(group=_G3, title="Min. % TP k férovej cene", step=5,
                   tooltip="Pri pevnom cieli: k férovej cene musí byť aspoň toľko % z TP. Video: 80 %."),
    "minDist": dict(group=_G3, title="Min. vzdialenosť k férovej (body)",
                    tooltip="Pri cieli na férovej cene: bližšie sa nevstupuje."),
    "useDisp": dict(group=_G4, title="Displacement",
                    tooltip="Telo väčšie ako telo predošlej sviečky opačnej farby a zavretie za jej knôt."),
    "useBos": dict(group=_G4, title="Prieraz štruktúry",
                   tooltip="Zavretie za posledný swing knôt (silnejší vstup podľa videa)."),
    "pivLen": dict(group=_G4, title="Swing knôt: sviečok z každej strany",
                   tooltip="1 = knôt nižší (vyšší) ako sviečka pred ním aj po ňom."),
    "tradeDirection": dict(group=_G4, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxLossRow": dict(group=_G4, title="Koniec okna po N stratách po sebe", tooltip="Video: 3."),
    "maxTrades": dict(group=_G4, title="Max. obchodov za okno", tooltip="Strop, jedna pozícia naraz."),
    "useCloseAfter": dict(group=_G4, title="Zavrieť obchod po okne", inline="cl",
                          tooltip="Otvorený obchod sa zavrie N minút po konci okna."),
    "closeAfter": dict(group=_G4, title="po (min)", inline="cl", tooltip="Minút po konci okna."),
    "useTrend": dict(group=_G5, title="Trendový deň (VWAP okna)", inline="f1",
                     tooltip="Keď je VWAP od začiatku okna za férovou cenou o viac bodov, proti nemu sa nevstupuje."),
    "trendPts": dict(group=_G5, title="o (body)", inline="f1", tooltip="Vzdialenosť VWAP okna od férovej ceny."),
    "useMaxD": dict(group=_G5, title="Max. vzdialenosť od férovej", inline="f2",
                    tooltip="Ďalej od férovej ceny sa proti pohybu nevstupuje (silný jednosmerný pohyb)."),
    "maxDist": dict(group=_G5, title="(body)", inline="f2", tooltip="Najväčšia vzdialenosť pre návrat."),
    "usePause": dict(group=_G5, title="Pauza po strate", inline="f3", tooltip="Po stratovom obchode sa N minút nevstupuje."),
    "pauseMin": dict(group=_G5, title="(min)", inline="f3", tooltip="Dĺžka pauzy."),
    "useRevDel": dict(group=_G5, title="Návrat až od N-tej minúty okna", inline="f4",
                      tooltip="Prvé minúty okna sa návraty neberú (chaos po otvorení)."),
    "revDelay": dict(group=_G5, title="(min)", inline="f4", tooltip="Od koľkej minúty okna."),
    "useTests": dict(group=_G5, title="Len pevná štruktúra", inline="f5",
                     tooltip="Prieraz platí, len keď sa cena ku knôtu aspoň N-krát vrátila a neprerazila ho."),
    "minTests": dict(group=_G5, title="testov", inline="f5", tooltip="Koľko testov úrovne."),
    "testTol": dict(group=_G5, title="Test = knôt príde k úrovni na (body)", tooltip="Tolerancia testu."),
    "useRevBias": dict(group=_G5, title="Návrat len v smere biasu",
                       tooltip="Short k férovej len pri biase short, long len pri biase long."),
    "riskDollar": dict(group=_G6, title="Riziko na obchod ($)",
                       tooltip="Strata na stope v dolároch; počet kontraktov sa dopočíta."),
    "showFair": dict(group=_G7, title="Kresliť férovú cenu", tooltip="Čiara férovej ceny so štítkom a okno."),
    "showZone": dict(group=_G7, title="Kresliť pásmo bez vstupu", tooltip="Okolo férovej ceny, kde je k nej príliš blízko."),
    "showSignals": dict(group=_G7, title="Kresliť signály", tooltip="D = displacement, S = prieraz štruktúry."),
    "showVwap": dict(group=_G7, title="Kresliť VWAP okna", tooltip="Pri zapnutom filtri trendového dňa."),
    "leverage": dict(group=_G8, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
