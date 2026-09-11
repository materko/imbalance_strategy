"""Popisy parametrov divergenčnej stratégie pre formulár webapp.

Jediný zdroj titulkov a tooltipov (rozsahy a defaulty sú v `config.py`).
"""

from __future__ import annotations

from typing import Any

from .divergence import INDICATOR_TITLES

__all__ = ["GROUPS", "PARAMS"]

_DIV = "🔎 Divergencie"
_IND_LONG = "📊 Indikátory pre long"
_IND_SHORT = "📊 Indikátory pre short"
_TREND = "📈 Trend (supertrend)"
_ZONY = "🧱 Divergenčné zóny na vyšších TF"
_VSTUP = "🚪 Vstup"
_VYSTUP = "🛑 Výstup"
_RIZIKO = "💰 Riziko"
_VIZUAL = "🎨 Vizualizácia"

GROUPS: tuple[str, ...] = (_DIV, _IND_LONG, _IND_SHORT, _TREND, _ZONY, _VSTUP, _VYSTUP, _RIZIKO, _VIZUAL)

_IND_TOOLTIP = {
    "macd": "MACD čiara (12/26/9) nad Heikin Ashi close.",
    "macdh": "MACD histogram (rozdiel MACD a signálu).",
    "rsi": "RSI 14 nad Heikin Ashi close.",
    "stoch": "Pomalé %K stochastiku (14, 3).",
    "cci": "CCI 10 z typickej ceny.",
    "mom": "Momentum 10 (close − close pred 10 barmi).",
    "obv": "On Balance Volume — kumulatívny objem podľa smeru baru.",
    "vwmacd": "Objemovo vážený MACD (VWMA 12 − VWMA 26).",
    "cmf": "Chaikin Money Flow 21.",
    "mfi": "Money Flow Index 14.",
    "cdv": "Kumulatívna delta objemu z knôtov sviečky, nulovaná o polnoci UTC. Na dátach bez "
           "burzového objemu (Dukascopy CFD) meria tickový objem klientov, nie trh.",
}


def _ind_params(group: str, fields: dict[str, str], side: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for field, key in fields.items():
        out[field] = dict(
            group=group, title=INDICATOR_TITLES[key],
            tooltip=f"{_IND_TOOLTIP[key]} Zapnuté = divergencia tohto indikátora sa počíta do "
                    f"{side} signálu.",
        )
    return out


PARAMS: dict[str, dict[str, Any]] = {
    # ---- 🔎 Divergencie ---------------------------------------------------- #
    "prd": dict(
        group=_DIV, title="Perióda pivotu",
        tooltip="Koľko barov vľavo aj vpravo musí byť nižších (pivot high) resp. vyšších (pivot "
                "low). Pivot sa potvrdí až toľkoto barov po tom, čo nastal — skôr ho stratégia "
                "nepozná. Pôvodná stratégia mala pivoty z celého DataFrame (pohľad dopredu), tu nie.",
    ),
    "source": dict(
        group=_DIV, title="Zdroj pivotov",
        tooltip="close = pivoty aj porovnanie ceny na zatváracej cene; high/low = pivot high na "
                "high a pivot low na low. Všetko na Heikin Ashi sviečkach, ako v origináli.",
    ),
    "searchDiv": dict(
        group=_DIV, title="Druh divergencií",
        tooltip="regular = cena nižšie low, indikátor vyššie low (obrat); hidden = cena vyššie "
                "low, indikátor nižšie low (pokračovanie); regular/hidden = obe.",
    ),
    "maxPp": dict(
        group=_DIV, title="Max. pivotov na kontrolu",
        tooltip="Koľko posledných pivotov sa skúša proti aktuálnemu baru. Viac = viac "
                "(a starších) divergencií.",
    ),
    "maxBars": dict(
        group=_DIV, title="Max. barov dozadu",
        tooltip="Pivot starší než toľkoto barov sa neberie. Divergencia cez pol roka nie je "
                "divergencia.",
    ),
    "dontConfirm": dict(
        group=_DIV, title="Bez potvrdenia",
        tooltip="Zapnuté = divergencia sa hlási hneď na aktuálnom bare. Vypnuté = čaká sa, kým "
                "indikátor alebo close stúpne (býčia) resp. klesne (medvedia), a porovnáva sa "
                "predchádzajúci bar — o bar neskôr, ale menej falošných.",
    ),
    "minDivsLong": dict(
        group=_DIV, title="Min. divergencií pre long",
        tooltip="Koľko dvojíc (indikátor × druh) musí na jednom bare súhlasiť, aby vznikol "
                "býčí signál.",
    ),
    "minDivsShort": dict(
        group=_DIV, title="Min. divergencií pre short",
        tooltip="To isté pre medvedí signál. Pôvodný config mal na short prísnejšie 2.",
    ),
    "signalBars": dict(
        group=_DIV, title="Platnosť divergencie (bary)",
        tooltip="Signál platí, ak divergencia nastala na niektorom z posledných toľkoto barov — "
                "a zároveň na žiadnom z nich nebola divergencia opačným smerom. Pôvodne 3 "
                "(`shift(0..2)`).",
    ),
    # ---- 📊 Indikátory ------------------------------------------------------ #
    **_ind_params(_IND_LONG, {
        "divMacdLong": "macd", "divMacdHistLong": "macdh", "divRsiLong": "rsi",
        "divStochLong": "stoch", "divCciLong": "cci", "divMomLong": "mom", "divObvLong": "obv",
        "divVwmacdLong": "vwmacd", "divCmfLong": "cmf", "divMfiLong": "mfi", "divCdvLong": "cdv",
    }, "long"),
    **_ind_params(_IND_SHORT, {
        "divMacdShort": "macd", "divMacdHistShort": "macdh", "divRsiShort": "rsi",
        "divStochShort": "stoch", "divCciShort": "cci", "divMomShort": "mom", "divObvShort": "obv",
        "divVwmacdShort": "vwmacd", "divCmfShort": "cmf", "divMfiShort": "mfi", "divCdvShort": "cdv",
    }, "short"),
    # ---- 📈 Trend ----------------------------------------------------------- #
    "stLen": dict(
        group=_TREND, title="Supertrend: ATR dĺžka",
        tooltip="Dĺžka ATR supertrendu — spoločná pre graf aj oba vyššie TF.",
    ),
    "stMult": dict(
        group=_TREND, title="Supertrend na grafe: násobok", step=0.5,
        tooltip="Násobok ATR supertrendu na grafovom TF (pôvodne 4). Používa ho filter pullbacku.",
    ),
    "htfMinutes": dict(
        group=_TREND, title="Vyšší TF (minúty)", inline="htf",
        tooltip="Prvý vyšší TF (pôvodne 1h = 60). Musí byť násobkom TF grafu — skladá sa z jeho "
                "barov. Jeho supertrend musí byť v smere obchodu.",
    ),
    "htf2Minutes": dict(
        group=_TREND, title="Druhý vyšší TF (minúty)", inline="htf",
        tooltip="Dlhší vyšší TF (pôvodne 4h = 240). Jeho supertrend musí byť v smere obchodu "
                "a jeho prerazenie zatvára stratový obchod (Výstup podľa trendu).",
    ),
    "stMultHtf": dict(
        group=_TREND, title="Supertrend na vyšších TF: násobok", step=0.5,
        tooltip="Násobok ATR supertrendu na oboch vyšších TF (pôvodne 3,5).",
    ),
    "pullbackFilter": dict(
        group=_TREND, title="Filter pullbacku",
        tooltip="Zapnuté = long len keď je supertrend na grafovom TF PROTI trendu vyšších TF "
                "(krátkodobý pokles v dlhodobom raste). Pôvodne sa počítali 5m bary v protismere "
                "vnútri baru grafu; na 5m grafe je to to isté.",
    ),
    "rsiLen": dict(
        group=_TREND, title="RSI dĺžka",
        tooltip="RSI nad Heikin Ashi close na grafovom TF — filter prekúpenosti.",
    ),
    "rsiLongMax": dict(
        group=_TREND, title="RSI max. pre long", inline="rsi", step=1,
        tooltip="Long len pri RSI najviac toľkoto (pôvodne 60) — nekupuje sa do prekúpeného trhu.",
    ),
    "rsiShortMin": dict(
        group=_TREND, title="RSI min. pre short", inline="rsi", step=1,
        tooltip="Short len pri RSI aspoň toľkoto (pôvodne 40).",
    ),
    # ---- 🧱 Zóny ------------------------------------------------------------ #
    "zoneFilter": dict(
        group=_ZONY, title="Filter divergenčných zón",
        tooltip="Zapnuté = na vyšších TF sa hľadajú divergencie všetkými indikátormi a long sa "
                "neotvorí, kým je v okne posledných barov čo i len jedna medvedia (a naopak). "
                "Pôvodné `pair_bear_zone` / `pair_bull_zone`.",
    ),
    "zoneSearchDiv": dict(
        group=_ZONY, title="Zóny: druh divergencií",
        tooltip="Ktoré divergencie tvoria zónu. Originál mal nastavené obe, ale chybou v počítaní "
                "rátal len regulárne — regular je preto to, čo pôvodná stratégia naozaj robila; "
                "regular/hidden je to, čo mala v úmysle, a blokuje podstatne viac.",
    ),
    "zonePrd1": dict(
        group=_ZONY, title="Vyšší TF: perióda pivotu",
        tooltip="Perióda pivotu pre divergencie na prvom vyššom TF (pôvodne 5 na 1h).",
    ),
    "zoneWindow1": dict(
        group=_ZONY, title="Vyšší TF: okno (bary)",
        tooltip="Koľko posledných barov vyššieho TF sa sčíta (pôvodne 6 na 1h = 6 hodín).",
    ),
    "zonePrd2": dict(
        group=_ZONY, title="Druhý vyšší TF: perióda pivotu",
        tooltip="Perióda pivotu na druhom vyššom TF (pôvodne 3 na 4h).",
    ),
    "zoneWindow2": dict(
        group=_ZONY, title="Druhý vyšší TF: okno (bary)",
        tooltip="Koľko posledných barov druhého vyššieho TF sa sčíta (pôvodne 44 na 4h ≈ týždeň).",
    ),
    "zoneMaxPp": dict(
        group=_ZONY, title="Zóny: max. pivotov",
        tooltip="Max. pivotov na kontrolu pre zónové divergencie (pôvodne 10).",
    ),
    "zoneMaxBars": dict(
        group=_ZONY, title="Zóny: max. barov dozadu",
        tooltip="Max. vzdialenosť pivotu pre zónové divergencie (pôvodne 200 barov vyššieho TF).",
    ),
    # ---- 🚪 Vstup ----------------------------------------------------------- #
    "tradeDirection": dict(
        group=_VSTUP, title="Smer obchodov",
        tooltip="Ktorú stranu obchodovať. Na spotovom páre musí byť Long only.",
    ),
    "entryMode": dict(
        group=_VSTUP, title="Ako vstúpiť",
        tooltip="confirm = pôvodný „trailing buy“: signál len vyzbrojí vstup a kým trvá (divergencia "
                "žije Platnosť divergencie barov a filtre držia), vstúpi sa na prvom bare, ktorý "
                "zavrie v smere obchodu nad (long) resp. pod (short) zatváracou cenou "
                "predchádzajúceho baru; immediate = vstup na zatvorení signálneho baru.",
    ),
    # ---- 🛑 Výstup ---------------------------------------------------------- #
    "atrLen": dict(
        group=_VYSTUP, title="ATR dĺžka (SL)",
        tooltip="ATR na grafovom TF (skutočné sviečky, nie Heikin Ashi), z ktorého sa počíta stop.",
    ),
    "slAtrMult": dict(
        group=_VYSTUP, title="SL vzdialenosť (násobok ATR)", step=0.5,
        tooltip="Tvrdý stop = vstup −/+ toľkoto ATR. Pôvodná stratégia mala stop −55 % a stratu "
                "držal len limit v dolároch; tu je limit v dolároch rizikom na obchod a stop mu "
                "určuje veľkosť pozície.",
    ),
    "rrRatio": dict(
        group=_VYSTUP, title="Risk:Reward pomer (0 = bez TP)", step=0.5,
        tooltip="Take profit ako násobok vzdialenosti stopu. 0 = žiadny pevný cieľ (ako originál, "
                "kde ROI 90 % nikdy nenastal) — obchod končí trailingom, trendom alebo stopom; "
                "TP box sa vtedy nekreslí.",
    ),
    "trendExit": dict(
        group=_VYSTUP, title="Výstup podľa trendu",
        tooltip="Zapnuté = stratový obchod (close na zlej strane vstupu) sa zavrie, keď supertrend "
                "druhého vyššieho TF otočí proti nemu alebo close prerazí jeho čiaru. Ziskový "
                "obchod nechá trailingu — presne ako pôvodný custom_stoploss.",
    ),
    "enableTrailing": dict(
        group=_VYSTUP, title="Trailing stop",
        tooltip="Dvojstupňový trailing z pôvodného custom_stoploss: najprv zámok malého zisku, "
                "potom sledovanie ceny.",
    ),
    "beActivationPct": dict(
        group=_VYSTUP, title="Zámok zisku: aktivácia (%)", step=0.1, inline="be",
        tooltip="Keď zisk dosiahne toľkoto % ceny vstupu, stop sa presunie na zámok (pôvodne 1,5 %).",
    ),
    "beLockPct": dict(
        group=_VYSTUP, title="Zámok zisku: úroveň (%)", step=0.05, inline="be",
        tooltip="Kam sa stop presunie: vstup + toľkoto % (pôvodne 0,35 %). Musí byť pod aktiváciou.",
    ),
    "trailActivationPct": dict(
        group=_VYSTUP, title="Trailing: aktivácia (%)", step=0.5, inline="trail",
        tooltip="Od toľkoto % zisku stop sleduje najlepšiu cenu (pôvodne 4 %).",
    ),
    "trailOffsetPct": dict(
        group=_VYSTUP, title="Trailing: odstup (%)", step=0.1, inline="trail",
        tooltip="Ako ďaleko za najlepšou cenou stop ide (pôvodne 1 %). Nikdy sa nevracia späť.",
    ),
    "maxHoldBars": dict(
        group=_VYSTUP, title="Časový limit obchodu (bary)",
        tooltip="Obchod starší než toľkoto barov grafu sa zavrie za trh. 0 = bez limitu (originál "
                "ho nemal). Je to v BAROCH, na inom TF je to iný čas.",
    ),
    # ---- 💰 Riziko ---------------------------------------------------------- #
    "riskDollar": dict(
        group=_RIZIKO, title="Riziko na obchod ($)", step=10,
        tooltip="Veľkosť pozície = riziko / vzdialenosť SL — pôvodných 200 $ maximálnej straty "
                "(`max_abs_loss`). 0 = 1 kontrakt.",
    ),
    # ---- 🎨 Vizualizácia ---------------------------------------------------- #
    "showDivergences": dict(
        group=_VIZUAL, title="Kresliť divergencie",
        tooltip="Spojnica od pivotu k baru divergencie a štítok s indikátormi.",
    ),
    "showSupertrend": dict(
        group=_VIZUAL, title="Kresliť supertrend",
        tooltip="Čiara supertrendu na grafe (farba podľa trendu) a čiara druhého vyššieho TF.",
    ),
    "showZones": dict(
        group=_VIZUAL, title="Kresliť divergenčné zóny",
        tooltip="Pozadie v čase, keď zónový filter blokuje long (medvedia zóna) alebo short "
                "(býčia zóna).",
    ),
    # ---- rozšírenia portu -------------------------------------------------- #
    "leverage": dict(
        title="Páka",
        tooltip="Páka vo Freqtrade futures (pôvodné `strat_lvrg`). Nemení signály, len či sa "
                "risk-based pozícia zmestí na účet.",
    ),
}
