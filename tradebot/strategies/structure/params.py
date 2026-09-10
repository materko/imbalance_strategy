"""Popisy parametrov pre formulár webapp — pri stratégii, nie v Pine.

Toto je zdroj pravdy pre to, **ako sa parameter volá po ľudsky a čo robí**. Rozsahy
a defaulty sem nepatria: tie sú v `config.py` (`CONSTRAINTS` a defaulty dataclass) a
formulár si ich vyzdvihne odtiaľ, takže sa nemá ako rozísť s tým, čo config prijme.
Zoznam hodnôt enumu sa dopĺňa sám z `ENUM_FIELDS`.

Prečo pri stratégii a nie v Pine: Pine skript vzniká len na vyžiadanie (aby sa stratégia
dala pozrieť na TradingView) a formulár na ňom nesmie závisieť. Stratégia bez Pine musí
mať plnohodnotný formulár.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_STRUKTURA = "🎯 Štruktúra"
_VSTUP = "🚪 Vstup"
_VYSTUP = "🛑 Výstup"
_RIZIKO = "💰 Riziko"
_SEANSA = "🕒 Seansa"
_VIZUAL = "🎨 Vizualizácia"

#: Poradie skupín vo formulári.
GROUPS: tuple[str, ...] = (_STRUKTURA, _VSTUP, _VYSTUP, _RIZIKO, _SEANSA, _VIZUAL)

#: `pole configu -> {group, title, tooltip, [step], [options], [inline]}`.
PARAMS: dict[str, dict[str, Any]] = {
    # ---- 🎯 Štruktúra ------------------------------------------------------ #
    "swingLeft": dict(
        group=_STRUKTURA, title="Swing: barov vľavo",
        tooltip="Koľko barov vľavo musí byť nižších (swing high) resp. vyšších (swing low). "
                "Väčšie číslo = menej swingov, ale významnejších.",
    ),
    "swingRight": dict(
        group=_STRUKTURA, title="Swing: barov vpravo (potvrdenie)",
        tooltip="Koľko barov vpravo musí swing prežiť, aby sa POTVRDIL. Až potvrdený swing sa "
                "smie použiť na rozhodnutie aj na kreslenie — dovtedy o ňom stratégia nevie. "
                "Vyššie číslo = neskoršie potvrdenie, ale menej falošných swingov.",
    ),
    "minSwingSize": dict(
        group=_STRUKTURA, title="Min. veľkosť swingu", step=0.1,
        tooltip="Swing, ktorého vzdialenosť od posledného prijatého swingu je menšia než toľkoto "
                "ATR, sa ignoruje ako šum — úroveň sa neposunie a swing sa ani nenakreslí. "
                "0 = filter vypnutý.",
    ),
    "atrLen": dict(
        group=_STRUKTURA, title="ATR dĺžka",
        tooltip="Dĺžka ATR (Wilder) na grafovom TF. Z neho sa počítajú všetky prahy zadané "
                "v násobkoch ATR — vďaka tomu platí ten istý config na BTC aj na NAS100.",
    ),
    # ---- 🚪 Vstup ---------------------------------------------------------- #
    "entryMode": dict(
        group=_VSTUP, title="Variant vstupu",
        tooltip="choch = vstup v smere NOVEJ štruktúry na zatvorení baru, ktorý CHoCH spôsobil "
                "(otočenie trendu); bos = vstup v smere pokračovania po BOS; sweep = PROTI CHoCH "
                "(CHoCH nadol znamená long) — falošné prerazenie / odber likvidity.",
    ),
    "tradeDirection": dict(
        group=_VSTUP, title="Smer obchodov",
        tooltip="Ktorú stranu obchodovať. Na spotovom páre musí byť Long only — burza nemá čo požičať.",
    ),
    # ---- 🛑 Výstup --------------------------------------------------------- #
    "exitMode": dict(
        group=_VYSTUP, title="Výstup",
        tooltip="rr = take profit je násobok rizika (Risk:Reward pomer); structure = obchod končí "
                "na DALŠEJ štruktúrnej udalosti (BOS alebo CHoCH) v smere obchodu. Pri structure sa "
                "TP box nekreslí — obchod žiadny pevný cieľ nemá.",
    ),
    "rrRatio": dict(
        group=_VYSTUP, title="Risk:Reward pomer", step=0.5,
        tooltip="Take profit = pomer × vzdialenosť SL. Platí len pri Výstup = rr.",
    ),
    "slMode": dict(
        group=_VYSTUP, title="Odkiaľ stop",
        tooltip="swing = za posledným potvrdeným swingom v protismere plus rezerva; atr = pevný "
                "násobok ATR od vstupu. Keď potvrdený swing v protismere ešte nie je, použije sa "
                "ATR aj v režime swing.",
    ),
    "slBuffer": dict(
        group=_VYSTUP, title="Rezerva za swing", step=0.05,
        tooltip="O koľko ATR sa stop odsunie za swing, aby ho nezobral šum. Platí len pri "
                "Odkiaľ stop = swing.",
    ),
    "slAtrMult": dict(
        group=_VYSTUP, title="SL vzdialenosť (násobok ATR)", step=0.1,
        tooltip="Stop loss = vstup -/+ toľkoto násobkov ATR. Platí pri Odkiaľ stop = atr a ako "
                "záloha, keď swing stop vyjde na zlú stranu vstupu (typicky pri sweep vstupe).",
    ),
    "maxBars": dict(
        group=_VYSTUP, title="Časový limit obchodu (bary)",
        tooltip="Obchod, ktorý po toľkoto baroch grafu od baru signálu stále beží, sa zavrie za trh. "
                "0 = bez časového limitu. Pozor: je to v BAROCH, takže na inom TF je to iný čas.",
    ),
    # ---- 💰 Riziko --------------------------------------------------------- #
    "riskDollar": dict(
        group=_RIZIKO, title="Riziko na obchod ($)", step=10,
        tooltip="Veľkosť pozície = riziko / vzdialenosť SL. Vďaka tomu sa výsledok dá prepočítať "
                "na iný účet a Monte Carlo vie dať odporúčanie k riziku. 0 = 1 kontrakt.",
    ),
    # ---- 🕒 Seansa --------------------------------------------------------- #
    "useSession": dict(
        group=_SEANSA, title="Obchodovať len v okne",
        tooltip="Zapnuté = vstupy len v čase medzi Začiatkom a Koncom okna. Štruktúra sa počíta "
                "a kreslí stále, obmedzené sú len vstupy. Predvolene vypnuté — krypto obchoduje "
                "24/7 a okno je tvrdenie, ktoré treba najprv zmerať.",
    ),
    "sessionTZ": dict(
        group=_SEANSA, title="Časové pásmo okna",
        tooltip="V ktorom pásme sa čítajú hodiny nižšie. Bez neho sú hodiny nejednoznačné a cez "
                "prechod na letný čas by okno ubehlo.",
    ),
    "sessionStartH": dict(
        group=_SEANSA, title="Začiatok okna (hodina)", inline="okno",
        tooltip="Prvá hodina okna vrátane. Okno cez polnoc sa zadá tak, že koniec je menší než "
                "začiatok (napr. 22 -> 6).",
    ),
    "sessionEndH": dict(
        group=_SEANSA, title="Koniec okna (hodina)", inline="okno",
        tooltip="Prvá hodina UŽ MIMO okna. Musí sa líšiť od začiatku — rovnaké hodiny znamenajú "
                "nulové okno a žiadny obchod.",
    ),
    # ---- 🎨 Vizualizácia --------------------------------------------------- #
    "showStructure": dict(
        group=_VIZUAL, title="Kresliť štruktúru",
        tooltip="Značky potvrdených swingov, úrovne a štítky BOS/CHoCH. Vypnutím sa graf odľahčí — "
                "na piatich rokoch je tých objektov desaťtisíce.",
    ),
    # ---- rozšírenia portu (skupinu doplní formulár sám) --------------------- #
    "leverage": dict(
        title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based "
                "sizingu, ktorá by sa inak na účet nezmestila.",
    ),
}
