"""Aký **charakter** má stratégia — zmerané z jej obchodov, nie odhadnuté z názvu.

### Načo to je
„Je to breakout, alebo protitrendová?" nie je akademická otázka. Od odpovede závisí, čo
sa má ladiť, čo je normálne a čo je problém:

| charakter | winrate | payoff | čo je normálne | na čo pozor |
|---|---|---|---|---|
| breakout | nízky | vysoký | dlhé série strát | falošné prerazenia v rozsahu |
| trendová | nízky | veľmi vysoký | málo obchodov nesie všetko | dlhé obdobia bez zisku |
| protitrendová | vysoký | nízky | takmer stále malé zisky | jedna strata zmaže mesiac |
| scalping | ~50 % | ~1 | edge je rádovo ako poplatok | poplatky rozhodujú o všetkom |

Kto ladí protitrendovú stratégiu na maximálny payoff, pracuje proti jej podstate. A kto sa
pri breakoute vystraší zo šiestich strát v rade, vypne niečo, čo funguje.

### Čím sa to meria
Všetko z `trades.json` a zo sviečok páru, teda **generickými** vecami, ktoré má každá
stratégia rovnaké. Rozhodujúca je jedna vec, ktorú nikde inde nevidno:

**Pohyb PRED vstupom v smere obchodu.** Breakout aj momentum vstupujú *po* pohybe a *v jeho
smere* — číslo je kladné. Protitrendová stratégia vstupuje *proti* poslednému pohybu —
číslo je záporné. Je to jediná vlastnosť, ktorá tie dva svety rozlíši spoľahlivo; winrate
a payoff samotné sa dajú nastaviť aj proti charakteru (stačí posunúť TP).

K tomu:
- **winrate a payoff** (priemerný zisk delený priemernou stratou) — mapa, na ktorej
  stratégia leží;
- **medián dĺžky v baroch** grafu — scalp, intradenná, swingová;
- **obchodov za deň** — frekvencia;
- **šikmosť výnosov** — kladná znamená „málo veľkých ziskov", záporná „veľa malých ziskov
  a občas rana";
- **teplo pred ziskom** (MAE/MFE) — koľko obchod znesie proti sebe, než sa otočí;
- **zmes výstupov** — koľko končí na TP, na stope, na čase.

### Prečo pravidlá a nie model
Zaradenie je pravidlá nad tými číslami, nie klasifikátor. Nie preto, že by model nešiel, ale
preto, že tu treba vidieť **prečo** — „nízky winrate a payoff 3,2, vstup po pohybe +0,8 ATR"
je vysvetlenie, s ktorým sa dá pracovať, kým „92 % breakout" nie je. A pri desiatkach behov
by sa model aj tak nemal na čom učiť.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from tradebot.core.candles import timeframe_minutes

__all__ = [
    "ARCHETYPES", "Archetype", "LOOKBACK_BARS", "Character",
    "pre_entry_moves", "measure", "classify", "describe", "table",
]

#: Koľko barov pred vstupom sa pozerá na predchádzajúci pohyb. Päť barov je kompromis:
#: dosť na to, aby bol pohyb vidieť, málo na to, aby to ešte bol *kontext vstupu*.
LOOKBACK_BARS = 5

#: Nad týmto (v ATR) je vstup „po pohybe v smere obchodu", pod mínus tým „proti pohybu".
MOMENTUM_EDGE = 0.25


@dataclass(frozen=True)
class Archetype:
    """Jeden typ stratégie: čím sa pozná a čo z toho vyplýva pre testovanie."""

    key: str
    title: str
    #: čím sa pozná — ide do vysvetlenia
    signature: str
    #: čo je pri tomto type normálne a netreba to „opravovať"
    normal: str
    #: na čo pozor pri ladení
    watch: str
    #: čo má zmysel optimalizovať
    tune: str


ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        "breakout", "Prerazenie (breakout)",
        "Vstup po pohybe v smere obchodu, nízky winrate, vysoký payoff, krátke držanie.",
        "Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. "
        "Winrate pod 40 % je pri tomto type v poriadku.",
        "Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh "
        "vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.",
        "Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá "
        "zvýšiť len skrátením TP, a tým sa stratégia pokazí.",
    ),
    Archetype(
        "trend", "Trendová (momentum)",
        "Vstup v smere pohybu, dlhé držanie, nízky winrate, veľmi vysoký payoff — "
        "výsledok nesie málo obchodov.",
        "Mesiace bez zisku a potom jeden obchod, ktorý vyrovná rok. Rovná krivka kapitálu "
        "sa od tohto typu čakať nedá.",
        "Vyhodnotenie na krátkom okne. Keď výsledok nesie päť obchodov z dvesto, jedno "
        "okno nehovorí nič — a Monte Carlo interval bude široký.",
        "Trailing a to, ako dlho sa obchod drží. Skrátenie TP tento typ zabije.",
    ),
    Archetype(
        "reversion", "Protitrendová (mean reversion)",
        "Vstup proti poslednému pohybu, vysoký winrate, nízky payoff, krátke držanie.",
        "Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa "
        "frekvenciou, nie veľkosťou.",
        "Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` "
        "aj drawdown limit majú väčší význam než pri ostatných typoch.",
        "Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR "
        "nahor väčšinou len zníži winrate a nič nepridá.",
    ),
    Archetype(
        "scalp", "Scalping",
        "Veľa obchodov, veľmi krátke držanie, payoff blízko 1, winrate blízko 50 %.",
        "Edge na obchod je rádovo taký veľký ako poplatok. Break-even poplatok je tu "
        "jediné číslo, ktoré niečo znamená.",
        "Poplatky a slippage rozhodujú o všetkom. Beh s `--fee 0` je pri tomto type "
        "úplne bezcenný.",
        "Break-even poplatok, nie PnL. A počet obchodov — menej lepších je zvyčajne viac.",
    ),
    Archetype(
        "pattern", "Formácia / štruktúra",
        "Vstup na konkrétnej konfigurácii, nie na pohybe — predchádzajúci pohyb nie je "
        "systematicky ani v smere, ani proti.",
        "Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto "
        "o jednotlivom obchode nehovorí veľa.",
        "Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny "
        "(`tester.analytics`) — priemer skrýva dve rôzne populácie.",
        "Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.",
    ),
    Archetype(
        "swing", "Swingová",
        "Málo obchodov, držanie v dňoch, payoff nad 1.",
        "Desiatky obchodov za rok. Štatistika je nutne slabá a intervaly široké.",
        "Málo obchodov = ľahké pretrénovanie. Hyperopt tu prefituje najrýchlejšie.",
        "Skôr výber trhu a obdobia než jednotlivé prahy.",
    ),
)


# --------------------------------------------------------------------------- #
# meranie
# --------------------------------------------------------------------------- #


def _dt_ms(value: Any) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    zoradene = sorted(values)
    n = len(zoradene)
    return zoradene[n // 2] if n % 2 else (zoradene[n // 2 - 1] + zoradene[n // 2]) / 2


def _skew(values: Sequence[float]) -> float | None:
    """Šikmosť: kladná = málo veľkých ziskov, záporná = veľa malých a občas rana."""
    n = len(values)
    if n < 3:
        return None
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    if var <= 0:
        return None
    sd = math.sqrt(var)
    return round(sum(((v - mean) / sd) ** 3 for v in values) / n, 3)


def pre_entry_moves(trades: Sequence[dict[str, Any]], pair: str, timeframe: str,
                    lookback: int = LOOKBACK_BARS) -> list[float]:
    """Pohyb pred vstupom v smere obchodu, v jednotkách ATR. Pre každý obchod jedno číslo.

    Kladné = vstup **po** pohybe v smere obchodu (prerazenie, momentum). Záporné = vstup
    **proti** poslednému pohybu (návrat k priemeru). Delí sa priemerným rozsahom baru,
    aby to platilo na BTC aj na EURUSD.
    """
    import numpy as np

    from .webapp.chart import series

    ts, cols = series(pair, timeframe)
    minutes = timeframe_minutes(timeframe)
    krok = minutes * 60_000
    close, high, low = cols["close"], cols["high"], cols["low"]

    out: list[float] = []
    for t in trades:
        cas = _dt_ms(t.get("open_date"))
        if cas is None:
            continue
        i = int(np.searchsorted(ts, cas, side="right")) - 1
        if i < lookback + 1:
            continue
        # Rozsah baru ako mierka: ATR by potreboval ďalší parameter a na normalizáciu
        # medzi trhmi stačí priemerný rozsah okna, ktoré sa aj tak pozerá.
        okno = slice(i - lookback, i + 1)
        atr = float((high[okno] - low[okno]).mean())
        if atr <= 0:
            continue
        pohyb = float(close[i] - close[i - lookback])
        smer = -1.0 if t.get("is_short") else 1.0
        out.append(round(pohyb * smer / atr, 3))
    return out


@dataclass
class Character:
    """Zmerané čísla a z nich zaradenie."""

    trades: int = 0
    winrate: float | None = None
    payoff: float | None = None
    expectancy_pct: float | None = None
    median_bars: float | None = None
    trades_per_day: float | None = None
    skew: float | None = None
    pre_entry_atr: float | None = None
    momentum_share: float | None = None
    heat_ratio: float | None = None
    exits: dict[str, float] = field(default_factory=dict)
    archetype: str = ""
    confidence: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.__dict__)
        arch = next((a for a in ARCHETYPES if a.key == self.archetype), None)
        if arch:
            data["title"] = arch.title
            data["signature"] = arch.signature
            data["normal"] = arch.normal
            data["watch"] = arch.watch
            data["tune"] = arch.tune
        return data


def measure(trades: Sequence[dict[str, Any]], *, pair: str = "", timeframe: str = "3m",
            lookback: int = LOOKBACK_BARS) -> Character:
    """Zmerá charakteristiky. `pair` sa dá vynechať — vtedy chýba pohyb pred vstupom."""
    out = Character(trades=len(trades))
    if not trades:
        return out

    zisky = [float(t.get("profit_abs") or 0.0) for t in trades]
    vyhry = [z for z in zisky if z > 0]
    straty = [-z for z in zisky if z < 0]
    out.winrate = round(len(vyhry) / len(trades) * 100, 2)
    if vyhry and straty:
        out.payoff = round((sum(vyhry) / len(vyhry)) / (sum(straty) / len(straty)), 3)
    ratios = [float(t.get("profit_ratio") or 0.0) for t in trades]
    out.expectancy_pct = round(sum(ratios) / len(ratios) * 100, 4)
    out.skew = _skew(ratios)

    minutes = timeframe_minutes(timeframe) if timeframe else 1
    trvania = [float(t["trade_duration"]) for t in trades if t.get("trade_duration") is not None]
    if trvania:
        out.median_bars = round((_median(trvania) or 0) / max(minutes, 1), 1)

    casy = [c for c in (_dt_ms(t.get("open_date")) for t in trades) if c]
    if len(casy) > 1:
        dni = (max(casy) - min(casy)) / 86_400_000
        out.trades_per_day = round(len(trades) / dni, 2) if dni > 0 else None

    # Teplo pred ziskom: koľko obchod znesie proti sebe voči tomu, čo dá v prospech.
    tepla = []
    for t in trades:
        open_rate = float(t.get("open_rate") or 0)
        hi, lo = t.get("max_rate"), t.get("min_rate")
        if not open_rate or hi is None or lo is None:
            continue
        short = bool(t.get("is_short"))
        mfe = abs((float(lo) if short else float(hi)) - open_rate)
        mae = abs((float(hi) if short else float(lo)) - open_rate)
        if mfe > 0:
            tepla.append(mae / mfe)
    out.heat_ratio = round(_median(tepla) or 0, 3) if tepla else None

    pocty: dict[str, int] = {}
    for t in trades:
        pocty[str(t.get("exit_reason") or "?")] = pocty.get(str(t.get("exit_reason") or "?"), 0) + 1
    out.exits = {k: round(v / len(trades) * 100, 1) for k, v in
                 sorted(pocty.items(), key=lambda kv: -kv[1])}

    if pair:
        try:
            pohyby = pre_entry_moves(trades, pair, timeframe, lookback)
        except (FileNotFoundError, ImportError, ValueError):
            pohyby = []
        if pohyby:
            out.pre_entry_atr = round(_median(pohyby) or 0, 3)
            out.momentum_share = round(
                sum(1 for p in pohyby if p > MOMENTUM_EDGE) / len(pohyby) * 100, 1)
    return classify(out)


# --------------------------------------------------------------------------- #
# zaradenie
# --------------------------------------------------------------------------- #


def classify(ch: Character) -> Character:
    """Doplní `archetype`, `confidence` a dôkazy. Pravidlá, nie model — vidno prečo."""
    dokazy: list[str] = []
    wr, payoff, bars = ch.winrate, ch.payoff, ch.median_bars
    pohyb, za_den = ch.pre_entry_atr, ch.trades_per_day

    if ch.trades < 20:
        ch.archetype = "pattern"
        ch.confidence = "slabá"
        ch.evidence = [f"len {ch.trades} obchodov — na zaradenie treba aspoň 20"]
        return ch

    # Pohyb pred vstupom je hlavný rozlišovač: winrate a payoff sa dajú nastaviť aj proti
    # charakteru (stačí posunúť TP), smer vstupu voči predchádzajúcemu pohybu nie.
    momentum = pohyb is not None and pohyb > MOMENTUM_EDGE
    protipohyb = pohyb is not None and pohyb < -MOMENTUM_EDGE
    if pohyb is not None:
        popis = ("po pohybe v smere obchodu" if momentum else
                 "proti poslednému pohybu" if protipohyb else "bez jasného smeru pohybu")
        dokazy.append(f"vstup {popis} ({pohyb:+.2f} ATR za {LOOKBACK_BARS} barov)")

    dlhe = bars is not None and bars >= 120
    velmi_kratke = bars is not None and bars <= 10
    if bars is not None:
        dokazy.append(f"medián držania {bars:g} barov grafu")
    if wr is not None and payoff is not None:
        dokazy.append(f"winrate {wr:g} %, payoff {payoff:g}")
    if za_den is not None:
        dokazy.append(f"{za_den:g} obchodov za deň")
    if ch.skew is not None:
        dokazy.append(f"šikmosť výnosov {ch.skew:+g}")

    if za_den is not None and za_den >= 5 and velmi_kratke and payoff is not None and payoff < 1.6:
        kluc, istota = "scalp", "dobrá"
    elif dlhe and payoff is not None and payoff >= 2.5:
        kluc, istota = "trend", "dobrá"
    elif bars is not None and bars >= 400 and (za_den or 0) < 0.5:
        kluc, istota = "swing", "dobrá"
    elif momentum and (wr or 100) < 50:
        kluc, istota = "breakout", "dobrá" if (payoff or 0) >= 1.5 else "priemerná"
    elif protipohyb and (wr or 0) >= 55:
        kluc, istota = "reversion", "dobrá" if (payoff or 9) <= 1.5 else "priemerná"
    elif momentum:
        kluc, istota = "breakout", "priemerná"
    elif protipohyb:
        kluc, istota = "reversion", "priemerná"
    else:
        kluc, istota = "pattern", "priemerná" if pohyb is not None else "slabá"

    if pohyb is None:
        istota = "slabá"
        dokazy.append("pohyb pred vstupom sa nedal zmerať (chýbajú sviečky páru) — "
                      "bez neho sa prerazenie a návrat rozlíšiť nedajú")
    ch.archetype, ch.confidence, ch.evidence = kluc, istota, dokazy
    return ch


def describe(ch: Character) -> str:
    """Zaradenie ako veta s dôkazmi — nie label, ale vysvetlenie."""
    arch = next((a for a in ARCHETYPES if a.key == ch.archetype), None)
    if arch is None:
        return "charakter sa nedal určiť"
    return (f"{arch.title} (istota {ch.confidence}): " + "; ".join(ch.evidence) + ". "
            + arch.normal)


def table(ch: Character) -> str:
    """Čísla ako text — ASCII, konzola na Windows beží v cp1250."""
    arch = next((a for a in ARCHETYPES if a.key == ch.archetype), None)
    lines = [f"charakter: {arch.title if arch else '?'}  (istota {ch.confidence})", ""]
    for dokaz in ch.evidence:
        lines.append(f"  - {dokaz}")
    lines += ["", f"{'obchodov':<30}{ch.trades}"]
    riadky = (
        ("winrate %", ch.winrate), ("payoff (zisk/strata)", ch.payoff),
        ("ocakavanie % na obchod", ch.expectancy_pct), ("median drzania (bary)", ch.median_bars),
        ("obchodov za den", ch.trades_per_day), ("sikmost vynosov", ch.skew),
        ("pohyb pred vstupom (ATR)", ch.pre_entry_atr),
        ("podiel vstupov po pohybe %", ch.momentum_share),
        ("teplo pred ziskom (MAE/MFE)", ch.heat_ratio),
    )
    for meno, hodnota in riadky:
        lines.append(f"{meno:<30}{'-' if hodnota is None else f'{hodnota:g}'}")
    if ch.exits:
        lines.append("")
        lines.append("vystupy: " + ", ".join(f"{k} {v:g} %" for k, v in ch.exits.items()))
    if arch:
        lines += ["", f"co je normalne: {arch.normal}", f"na co pozor:    {arch.watch}",
                  f"co ladit:       {arch.tune}"]
    return "\n".join(lines)
