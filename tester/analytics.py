"""Analytika nad obchodmi: ktorá skupina obchodov kazí výsledok — a čo s ňou.

### Na akú otázku odpovedá
Backtest povie jedno číslo za celý beh. To nestačí na rozhodnutie „čo zmeniť": break-even
0,09 % môže znamenať, že stratégia je vyrovnane mierne zisková, alebo že polovica obchodov
zarába a druhá polovica to zožerie. Prvý prípad sa ladiť nedá, druhý áno — a rozdiel je
vidieť len po rozdelení obchodov na skupiny.

Preto sa tu obchody rozrežú podľa vlastností, ktoré sú v nich už uložené (dôvod výstupu,
smer, hodina, deň, dĺžka, ako hlboko šli proti nám, aká bola vzdialenosť stopu), a pre
každú skupinu sa spočíta **break-even poplatok** — jediné číslo, ktoré nezávisí od sizingu
ani peňaženky, takže sa skupiny dajú porovnať medzi sebou.

### Prečo break-even a nie PnL
Skupina s dvoma obchodmi a +500 USD vyzerá v PnL lepšie než skupina so sto obchodmi
a +400 USD, hoci o stratégii hovorí druhá. Break-even je hrubý zisk delený obchodovaným
objemom, takže veľkosť pozície ani počet obchodov skóre nenafúknu.

### Kľúčové číslo: čo by sa stalo, keby skupina nebola
Ku každej skupine sa dopočíta break-even **zvyšku** behu. Rozdiel je to, čo by filter
priniesol, keby sa tá skupina dala vopred rozoznať:

    exit_reason = session_end   43 obchodov (24 %)   break-even -0.021 %
      bez nej by break-even behu bol 0.134 % namiesto 0.094 %   (+0.040)

To je odpoveď na otázku, či sa filter (a teda aj model, ktorý by ho robil) oplatí. Keď
žiadna skupina nevyčnieva, nie je čo filtrovať a model nemá čo nájsť — ušetrí sa práca.

### Stav trhu je tiež vlastnosť — a je známa pri vstupe
Okrem vlastností obchodu (hodina, smer, vzdialenosť stopu) sa delí aj podľa toho, **v akom
stave bol trh**, keď obchod vznikol: či bol v trende alebo v rozsahu, aká bola volatilita
voči normálu, kde v rozsahu sa vstupovalo a či išiel obchod s trendom alebo proti nemu
(`tester.regime`). Všetko sa počíta z barov **pred** vstupom, takže sa podľa toho filtrovať
dá — a práve tam býva zvyšný edge, keď ho v samotnom patterne už niet.

### Čo je generické a čo vie len stratégia
Vlastnosti odvodené z obchodu sú generické: `trades.json` má rovnaké polia pre každú
stratégiu, lebo ho píše Freqtrade. Presnú vzdialenosť stopu a plánovaný RR pozná len
stratégia (vo svojich kresbách), preto ich `StrategySpec` pomenuje (`sl_kind`, `tp_kind`)
a bez toho sa tie dve vlastnosti jednoducho nepočítajú.

Ktorý **parameter** danú vlastnosť riadi, je tiež vedomosť stratégie
(`hyperopt_cls.FEATURE_PARAMS`) — vďaka tomu analytika nekončí zistením, ale odkazom na
to, čo sa dá ladiť.
"""

from __future__ import annotations

import json

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Sequence

from tradebot.adapters.freqtrade.hyperplan import knowledge
from tradebot.strategies import get_spec

__all__ = [
    "config_spread",
    "FEATURES", "Feature", "Bucket", "Split", "break_even_pct", "gross_and_volume",
    "features_for", "split", "analyze", "table",
]

#: Menej než toľko obchodov v skupine a číslo je šum, nie zistenie.
MIN_BUCKET = 8

#: Na koľko rovnako veľkých skupín sa delí číselná vlastnosť.
QUANTILES = 4

DAYS = ("pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota", "nedeľa")


# --------------------------------------------------------------------------- #
# break-even
# --------------------------------------------------------------------------- #


def gross_and_volume(trades: Sequence[dict[str, Any]]) -> tuple[float, float]:
    """Hrubý zisk z cien a obchodovaný objem — základ break-even poplatku.

    Z cien, nie z `profit_abs`: skóre tak nezávisí od toho, s akým `--fee` beh bežal.
    """
    gross = volume = 0.0
    for t in trades:
        amount = float(t.get("amount") or 0.0)
        open_rate, close_rate = float(t.get("open_rate") or 0.0), float(t.get("close_rate") or 0.0)
        smer = -1.0 if t.get("is_short") else 1.0
        gross += (close_rate - open_rate) * amount * smer
        volume += (open_rate + close_rate) * amount
    return gross, volume


def break_even_pct(trades: Sequence[dict[str, Any]]) -> float | None:
    """Koľko smie burza brať na stranu, aby tieto obchody vyšli na nulu (v %)."""
    gross, volume = gross_and_volume(trades)
    return None if volume <= 0 else round(gross / volume * 100.0, 4)


def _winrate(trades: Sequence[dict[str, Any]]) -> float | None:
    if not trades:
        return None
    return round(sum(1 for t in trades if float(t.get("profit_abs") or 0) > 0) / len(trades) * 100, 2)


# --------------------------------------------------------------------------- #
# vlastnosti obchodu
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Feature:
    """Vlastnosť, podľa ktorej sa dajú obchody rozdeliť."""

    key: str
    title: str
    #: `trade -> hodnota`, alebo `None` keď sa pre tento obchod nedá určiť
    value: Callable[[dict[str, Any]], Any]
    #: `True` = číslo (delí sa na kvantily), `False` = kategória
    numeric: bool = True
    #: jednotka do výpisu (`%`, `min`, `R`)
    unit: str = ""
    #: prečo je to zaujímavé — ide do stránky ako vysvetlenie
    note: str = ""
    #: `True` = hodnotu poznáme **pri vstupe**, takže sa podľa nej dá filtrovať.
    #: `False` = vieme ju až po obchode (dôvod výstupu, dĺžka, kam cena zašla) — také
    #: rozdelenie je opis, nie filter. Rozdiel je podstatný: „nebrať obchody, ktoré
    #: skončia na stope" nie je filter, je to pohľad dozadu.
    at_entry: bool = True


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _excursion(t: dict[str, Any], favourable: bool) -> float | None:
    """Ako ďaleko cena zašla v náš prospech (MFE) alebo proti nám (MAE), v % vstupu."""
    open_rate = float(t.get("open_rate") or 0.0)
    if not open_rate:
        return None
    hi, lo = t.get("max_rate"), t.get("min_rate")
    if hi is None or lo is None:
        return None
    short = bool(t.get("is_short"))
    prospech = (float(lo) - open_rate) if short else (float(hi) - open_rate)
    proti = (float(hi) - open_rate) if short else (float(lo) - open_rate)
    hodnota = prospech if favourable else proti
    return round(abs(hodnota) / open_rate * 100.0, 4)


FEATURES: tuple[Feature, ...] = (
    Feature("exit_reason", "Dôvod výstupu", lambda t: t.get("exit_reason") or "?", numeric=False,
            at_entry=False,
            note="Ktorým výstupom obchody končia a ktorý z nich zarába. `session_end` je "
                 "výstup na čas, nie na plán — ak práve tie kazia výsledok, je to o nastavení "
                 "okna, nie o vstupoch."),
    Feature("direction", "Smer", lambda t: "short" if t.get("is_short") else "long", numeric=False,
            note="Jedna strana môže niesť celý edge. Vtedy má zmysel `tradeDirection`, "
                 "nie ladenie prahov."),
    Feature("hour", "Hodina vstupu (UTC)", lambda t: (_dt(t.get("open_date")) or None) and _dt(t["open_date"]).hour,
            unit="h", note="Rozdelenie po hodinách ukáže, či edge nesie jedna seansa. Na IBS "
                           "to tak bolo — celý edge bol v NY seanse."),
    Feature("weekday", "Deň v týždni",
            lambda t: (_dt(t.get("open_date")) or None) and DAYS[_dt(t["open_date"]).weekday()],
            numeric=False, note="Pondelkové otvorenie a piatkové zatváranie majú iný charakter."),
    Feature("duration_min", "Dĺžka obchodu", lambda t: t.get("trade_duration"), unit="min",
            at_entry=False,
            note="Veľmi krátke obchody sú často šum na vstupe; veľmi dlhé držia kapitál."),
    Feature("mae_pct", "Ako hlboko šiel proti nám", lambda t: _excursion(t, False), unit="%",
            at_entry=False,
            note="Obchody, ktoré hneď idú proti nám, končia zle častejšie — a je to vidieť "
                 "už pár sviečok po vstupe, teda vopred."),
    Feature("mfe_pct", "Ako ďaleko šiel v náš prospech", lambda t: _excursion(t, True), unit="%",
            at_entry=False,
            note="Keď je MFE vysoké a zisk nie, výstup je nastavený zle (TP ďaleko, trailing skoro)."),
    Feature("day_of_month", "Deň v mesiaci",
            lambda t: (_dt(t.get("open_date")) or None) and _dt(t["open_date"]).day,
            note="Larryho Williamsa preslávilo hľadanie tendencií v kalendári — začiatok "
                 "mesiaca býva iný než koniec (výplaty, rebalansovanie fondov). Je to "
                 "zároveň klasická pasca na preoptimalizovanie: rozdiel medzi 3. a 17. dňom "
                 "vyzerá presvedčivo, kým sa neoverí po oknách."),
    Feature("month_of_year", "Kalendárny mesiac",
            lambda t: (_dt(t.get("open_date")) or None) and f"{_dt(t['open_date']):%m}",
            numeric=False,
            note="Sezónnosť naprieč rokmi — nie „marec 2023“, ale „marec vôbec“. "
                 "Pri piatich rokoch je to päť pozorovaní na mesiac, takže to skôr ukazuje "
                 "smer na overenie než hotový záver."),

    # -- kalendár: sviatky a makro (tester.calendar) -------------------------- #
    Feature("cal_event", "Makro udalosť v ten deň", lambda t: t.get("_cal_event"),
            numeric=False,
            note="Deň rozhodnutia Fedu, inflácie alebo zamestnanosti v USA. Dátumy sú "
                 "odpísané z federalreserve.gov a bls.gov, nie odvodené pravidlom — "
                 "a keďže sa vedia dopredu, filtrovať sa podľa nich dá."),
    Feature("cal_event_window", "Pred vyhlásením, alebo po ňom",
            lambda t: t.get("_cal_event_window"), numeric=False,
            note="Rozdiel medzi vstupom pred vyhlásením a po ňom je celý rozdiel medzi "
                 "hazardom a obchodovaním na už známej informácii."),
    Feature("cal_session", "Sviatok na burze v USA", lambda t: t.get("_cal_session"),
            numeric=False,
            note="Keď je Wall Street zavretá, likvidita zmizne aj tam, kde sa obchoduje "
                 "ďalej (krypto, CFD). Sviatky sa počítajú pravidlom, platia pre každý rok."),

    Feature("month", "Mesiac", lambda t: (_dt(t.get("open_date")) or None) and f"{_dt(t['open_date']):%Y-%m}",
            numeric=False, note="Režim trhu. Keď je edge len v dvoch mesiacoch z dvanástich, "
                                "je to o režime, nie o parametroch."),

    # -- stav trhu pri vstupe (tester.regime) -------------------------------- #
    Feature("regime_trend", "Trend alebo rozsah", lambda t: t.get("_regime_trend"),
            note="Efektivita pohybu za posledných 50 barov: 1 je priamka, 0 pílka okolo "
                 "jednej úrovne. Prerazenie v rozsahu je falošné častejšie než v trende — "
                 "a toto je číslo, ktorým sa to dá odfiltrovať."),
    Feature("regime_vol", "Volatilita voči normálu", lambda t: t.get("_regime_vol"),
            note="ATR pri vstupe delené typickým ATR trhu. 1,0 je bežný deň, 2,0 dvojnásobne "
                 "rozkolísaný. Náhrada za „pozri sa na VIX“, ktorá funguje na každom trhu."),
    Feature("regime_pos", "Kde v rozsahu, v smere obchodu", lambda t: t.get("_regime_pos"),
            note="1 = cena už došla na koniec rozsahu v smere obchodu (long na vrchu, short "
                 "na spodku), 0 = na opačnom konci. V smere obchodu preto, že surová poloha "
                 "sa pri polovici shortov vyruší — pre short je spodok to isté, čo pre long vrch."),
    Feature("regime_align", "S trendom, alebo proti", lambda t: t.get("_regime_align"),
            numeric=False,
            note="Smer obchodu voči sklonu posledných 50 barov. Klasické „neobchoduj proti "
                 "trendu“ sa dá overiť práve týmto rozdelením."),
)


def features_for(strategy: str = "ibs") -> tuple[Feature, ...]:
    """Vlastnosti pre stratégiu — generické plus tie, ktoré pozná len ona."""
    spec = get_spec(strategy)
    extra: list[Feature] = []
    if getattr(spec, "sl_kind", ""):
        extra.append(Feature("sl_pct", "Vzdialenosť stopu", lambda t: t.get("_sl_pct"), unit="%",
                             note="Poplatok je percento z nominálu, zisk rastie s R — tesné "
                                  "stopy majú najhorší pomer edge k poplatku. Gate je "
                                  "`minSlDistance`."))
    if getattr(spec, "sl_kind", "") and getattr(spec, "tp_kind", ""):
        extra.append(Feature("rr_planned", "Plánovaný RR", lambda t: t.get("_rr_planned"), unit="R",
                             note="Skutočný pomer TP k SL obchodu. Keď vysoké RR nezarába, "
                                  "je `rrRatio` nad optimom."))
    return FEATURES + tuple(extra)


def enrich(trades: list[dict[str, Any]], chart: dict[str, Any] | None,
           strategy: str = "ibs", *, pair: str = "", timeframe: str = "") -> list[dict[str, Any]]:
    """Doplní obchodom vzdialenosť stopu a plánovaný RR z kresieb stratégie.

    Kresby sú jediné miesto, kde je plán obchodu (SL a TP úroveň) uložený tak, ako ho
    engine vypočítal — v `trades.json` je len to, čo Freqtrade nakoniec urobil. Spája sa
    to časom baru signálu: `enter_tag` je `<prefix><čas v ms>` a kresba ho má v `x1`.
    """
    # Stav trhu pri vstupe potrebuje sviečky páru, nie kresby — doplní sa nezávisle
    # od plánu obchodu, takže funguje aj pre behy bez uložených kresieb.
    if pair:
        from . import regime as regime_mod

        regime_mod.annotate(trades, pair, timeframe or "3m")

    # Kalendár nepotrebuje ani sviečky, ani pár — dátum stačí.
    from . import calendar as cal_mod

    cal_mod.annotate(trades)

    spec = get_spec(strategy)
    sl_kind, tp_kind = getattr(spec, "sl_kind", ""), getattr(spec, "tp_kind", "")
    if not chart or not sl_kind:
        return trades

    sl_by_time: dict[int, tuple[float, float]] = {}
    tp_by_time: dict[int, tuple[float, float]] = {}
    for o in chart.get("objects") or ():
        kind = o.get("k")
        if kind == sl_kind and o.get("x1") is not None:
            sl_by_time[int(o["x1"])] = (float(o.get("y1", 0)), float(o.get("y2", 0)))
        elif kind == tp_kind and o.get("x1") is not None:
            tp_by_time[int(o["x1"])] = (float(o.get("y1", 0)), float(o.get("y2", 0)))

    for t in trades:
        tag = str(t.get("enter_tag") or "")
        cas = tag.rsplit(":", 1)[-1]
        if not cas.isdigit():
            continue
        sl = sl_by_time.get(int(cas))
        if not sl:
            continue
        open_rate = float(t.get("open_rate") or 0.0)
        if not open_rate:
            continue
        sl_dist = abs(sl[0] - sl[1])
        t["_sl_pct"] = round(sl_dist / open_rate * 100.0, 4)
        tp = tp_by_time.get(int(cas))
        if tp and sl_dist > 0:
            t["_rr_planned"] = round(abs(tp[0] - tp[1]) / sl_dist, 2)
    return trades


# --------------------------------------------------------------------------- #
# delenie na skupiny
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Bucket:
    """Jedna skupina obchodov a to, čo by sa stalo bez nej."""

    label: str
    trades: int
    share_pct: float
    winrate: float | None
    break_even_pct: float | None
    pnl_abs: float
    #: break-even zvyšku behu, keby táto skupina nebola
    without_pct: float | None
    #: `without_pct - break_even celku` — o koľko by sa výsledok zmenil
    impact: float | None


@dataclass
class Split:
    """Rozdelenie behu podľa jednej vlastnosti."""

    feature: str
    title: str
    unit: str = ""
    note: str = ""
    buckets: list[Bucket] = field(default_factory=list)
    #: parameter configu, ktorý túto vlastnosť riadi (od stratégie), alebo `None`
    param: str | None = None
    #: `impact` najhoršej skupiny — podľa toho sa vlastnosti radia
    best_impact: float | None = None
    #: hodnotu poznáme pri vstupe (dá sa filtrovať), alebo až po obchode (len opis)
    at_entry: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"feature": self.feature, "title": self.title, "unit": self.unit,
                "note": self.note, "param": self.param, "best_impact": self.best_impact,
                "at_entry": self.at_entry, "buckets": [b.__dict__ for b in self.buckets]}


def _quantile_edges(values: Sequence[float], parts: int) -> list[float]:
    """Hranice kvantilov — rovnako veľké skupiny, nie rovnako široké intervaly.

    Rovnako široké intervaly by pri zošikmenom rozdelení (a to je väčšina vlastností
    obchodu) dali jednu skupinu so všetkým a zvyšok prázdny.
    """
    zoradene = sorted(values)
    edges = []
    for i in range(1, parts):
        idx = int(len(zoradene) * i / parts)
        edges.append(zoradene[min(idx, len(zoradene) - 1)])
    return sorted(set(edges))


def _fmt_num(value: float, unit: str) -> str:
    text = f"{value:g}" if abs(value) < 1000 else f"{value:,.0f}".replace(",", " ")
    return f"{text} {unit}".strip()


def split(trades: Sequence[dict[str, Any]], feature: Feature, *,
          quantiles: int = QUANTILES, min_bucket: int = MIN_BUCKET) -> Split | None:
    """Rozdelí obchody podľa vlastnosti. `None`, keď sa vlastnosť nedá určiť."""
    dvojice = [(feature.value(t), t) for t in trades]
    pouzitelne = [(v, t) for v, t in dvojice if v is not None]
    if len(pouzitelne) < min_bucket * 2:
        return None

    skupiny: dict[str, list[dict[str, Any]]] = {}
    if feature.numeric:
        hodnoty = [float(v) for v, _ in pouzitelne]
        rozne = sorted(set(hodnoty))
        if len(rozne) < 2:
            return None
        # Málo rôznych hodnôt (hodina 9 a 15, RR 2 a 4) — každá je vlastná skupina.
        # Kvantily by ich zliali do jedného intervalu a rozdelenie by zmizlo, hoci
        # rozdiel medzi nimi je práve to, čo chceme vidieť.
        if len(rozne) <= quantiles:
            for v, t in pouzitelne:
                skupiny.setdefault(_fmt_num(float(v), feature.unit), []).append(t)
            return _finish(out_from(feature), skupiny, [t for _, t in pouzitelne], min_bucket)
        edges = _quantile_edges(hodnoty, quantiles)
        if not edges:
            return None
        for v, t in pouzitelne:
            cislo = float(v)
            i = sum(1 for e in edges if cislo > e)
            dolna = "" if i == 0 else _fmt_num(edges[i - 1], feature.unit)
            horna = "" if i == len(edges) else _fmt_num(edges[i], feature.unit)
            label = (f"do {horna}" if not dolna else
                     f"nad {dolna}" if not horna else f"{dolna} – {horna}")
            skupiny.setdefault(label, []).append(t)
    else:
        for v, t in pouzitelne:
            skupiny.setdefault(str(v), []).append(t)

    return _finish(out_from(feature), skupiny, [t for _, t in pouzitelne], min_bucket)


def out_from(feature: Feature) -> Split:
    return Split(feature.key, feature.title, feature.unit, feature.note,
                 at_entry=feature.at_entry)


def _finish(out: Split, skupiny: dict[str, list[dict[str, Any]]],
            vsetky: list[dict[str, Any]], min_bucket: int) -> Split | None:
    """Doplní skupinám čísla vrátane toho, čo by sa stalo bez nich."""
    celok = break_even_pct(vsetky)
    zvysne = {id(t) for kus in skupiny.values() if len(kus) >= min_bucket for t in kus}
    for label, kus in skupiny.items():
        if len(kus) < min_bucket:
            continue
        v_kuse = {id(t) for t in kus}
        zvysok = [t for t in vsetky if id(t) not in v_kuse]
        bez = break_even_pct(zvysok) if zvysok else None
        impact = None if (bez is None or celok is None) else round(bez - celok, 4)
        out.buckets.append(Bucket(
            label=label, trades=len(kus),
            share_pct=round(len(kus) / len(vsetky) * 100, 1),
            winrate=_winrate(kus), break_even_pct=break_even_pct(kus),
            pnl_abs=round(sum(float(t.get("profit_abs") or 0) for t in kus), 2),
            without_pct=bez, impact=impact,
        ))
    if len(out.buckets) < 2:
        return None
    out.buckets.sort(key=lambda b: (b.break_even_pct if b.break_even_pct is not None else 0))
    out.best_impact = max((b.impact for b in out.buckets if b.impact is not None), default=None)
    return out


def analyze(trades: Sequence[dict[str, Any]], *, strategy: str = "ibs",
            chart: dict[str, Any] | None = None, quantiles: int = QUANTILES,
            min_bucket: int = MIN_BUCKET) -> dict[str, Any]:
    """Celá analytika behu (alebo viacerých behov spolu).

    Vlastnosti sú zoradené podľa toho, koľko by sa dalo získať odfiltrovaním najhoršej
    skupiny — hore je to, čo sa najviac oplatí riešiť.
    """
    obchody = enrich([dict(t) for t in trades], chart, strategy)
    riadene = knowledge(get_spec(strategy)).FEATURE_PARAMS

    splits: list[Split] = []
    for feature in features_for(strategy):
        rozdelenie = split(obchody, feature, quantiles=quantiles, min_bucket=min_bucket)
        if rozdelenie is None:
            continue
        rozdelenie.param = riadene.get(feature.key)
        splits.append(rozdelenie)
    # Radí sa podľa toho, koľko by sa dalo získať — ale LEN medzi vlastnosťami známymi
    # pri vstupe. Výsledkové vlastnosti by inak obsadili celé prvé miesta (obchody, ktoré
    # skončili na TP, majú samozrejme lepší break-even než tie na stope) a vyzeralo by to
    # ako obrovská príležitosť, hoci je to len pohľad dozadu.
    vopred = sorted([s for s in splits if s.at_entry],
                    key=lambda s: (s.best_impact if s.best_impact is not None else -9e9),
                    reverse=True)
    potom = sorted([s for s in splits if not s.at_entry],
                   key=lambda s: (s.best_impact if s.best_impact is not None else -9e9),
                   reverse=True)

    najlepsi = vopred[0] if vopred else None
    return {
        "trades": len(obchody),
        "break_even_pct": break_even_pct(obchody),
        "winrate": _winrate(obchody),
        "pnl_abs": round(sum(float(t.get("profit_abs") or 0) for t in obchody), 2),
        "splits": [s.to_dict() for s in vopred],
        "descriptive": [s.to_dict() for s in potom],
        "tunable": sorted({s.param for s in splits if s.param}),
        "headline": _headline(najlepsi, break_even_pct(obchody)),
    }


def _headline(best: Split | None, celok: float | None) -> str:
    """Jedna veta: má filter priestor, alebo nie je čo filtrovať?

    Toto je odpoveď na otázku, či sa oplatí stavať model. Keď žiadna vopred známa
    vlastnosť nevyčnieva, model nemá čo nájsť a ušetrí sa práca.
    """
    if best is None or best.best_impact is None or celok is None:
        return "Na rozdelenie je málo obchodov — pusti viac behov alebo dlhšie okno."
    najhorsia = best.buckets[0]
    if best.best_impact < 0.01:
        return ("Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac "
                f"{best.best_impact:+.4f} % break-even). Filter ani model tu nema co najst - "
                "hladaj radsej v parametroch (hyperopt) alebo v inom podklade.")
    zaklad = (f"Najhorsia skupina je '{najhorsia.label}' vlastnosti '{best.title}': "
              f"{najhorsia.trades} obchodov ({najhorsia.share_pct} %), break-even "
              f"{najhorsia.break_even_pct} % oproti {celok} % celku. Bez nej by break-even "
              f"bol {najhorsia.without_pct} % ({best.best_impact:+.4f}).")
    # Skupina, ktora je vacsina obchodov, nie je filter - je to cely rozsah parametra.
    # Odfiltrovat 90 % obchodov nie je zlepsenie, je to ina strategia.
    if najhorsia.share_pct > 50:
        koniec = (" Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: "
                  + (f"skus preladit `{best.param}`." if best.param
                     else "hladaj parameter, ktory tuto vlastnost riadi."))
    elif best.param:
        koniec = (f" Filter na to postavit ide, ale najprv skus `{best.param}` - "
                  "parameter je lacnejsi a citatelnejsi nez model.")
    else:
        koniec = (" Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi "
                  "aj na inych oknach, je to kandidat na filter.")
    return zaklad + koniec


# --------------------------------------------------------------------------- #
# výpis
# --------------------------------------------------------------------------- #


def table(report: dict[str, Any], limit: int = 6, descriptive: bool = False) -> str:
    """Analytika ako text — ASCII, konzola na Windows beží v cp1250."""
    lines = [f"obchodov {report['trades']}, break-even {report['break_even_pct']} %, "
             f"winrate {report['winrate']} %", "", report["headline"]]
    sekcie = list(report["splits"][:limit])
    if descriptive:
        sekcie += report.get("descriptive", [])[:limit]
    for s in sekcie:
        lines.append("")
        hlavicka = f"=== {s['title']}"
        if s["param"]:
            hlavicka += f"  (riadi: {s['param']})"
        if not s.get("at_entry", True):
            hlavicka += "  [az po obchode - opis, nie filter]"
        lines.append(hlavicka + " ===")
        lines.append(f"{'skupina':<22}{'obch.':>7}{'podiel':>8}{'WR %':>7}"
                     f"{'break-even':>12}{'bez nej':>10}{'zmena':>9}")
        for b in s["buckets"]:
            lines.append(
                f"{b['label'][:22]:<22}{b['trades']:>7}{b['share_pct']:>7.1f}%"
                f"{(b['winrate'] or 0):>7.1f}{(b['break_even_pct'] if b['break_even_pct'] is not None else 0):>12.4f}"
                f"{(b['without_pct'] if b['without_pct'] is not None else 0):>10.4f}"
                f"{(b['impact'] if b['impact'] is not None else 0):>+9.4f}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# z akej konfigurácie tie obchody vlastne sú
# --------------------------------------------------------------------------- #
#
# Analytika, prop výzva aj meranie počítajú nad **zliatymi** obchodmi z viacerých behov.
# Kým sú tie behy tá istá konfigurácia na rôznych oknách alebo trhoch, je to v poriadku.
# Keď nie sú, zlieva sa dokopy niekoľko rôznych stratégií a výsledok nehovorí o žiadnej
# z nich — presne tak vznikli čísla „3× a 5×“ v REZIM_filtre_btcusdt_2026-09-10.md, ktoré
# neplatili. Pri zmiešaných pároch sa už varovalo; toto je to isté pre konfigurácie.

#: Koľko rozdielnych parametrov sa vymenuje, kým sa to stane nečitateľným.
MAX_DIFFS = 8


def config_spread(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Čo majú behy spoločné a v čom sa líšia.

    Vracia zoznam profilov, parametre s viac než jednou hodnotou a vetu do výpisu.
    Okná a trhy sa za rozdiel nepovažujú — práve preto sa behy zlievajú.
    """
    zoznam = [r for r in records if r.get("params")]
    profily = sorted({(r.get("settings") or {}).get("profile") or "(Pine defaulty)"
                      for r in records})
    #: `severity`: "ok" = jedna konfigurácia, "pozor" = jeden profil s inými číslami
    #: (typicky `--set` alebo prepočet na ATR), "chyba" = zliate rôzne profily.
    out: dict[str, Any] = {"runs": len(records), "profiles": profily,
                           "differing": {}, "mixed": False, "severity": "ok", "note": ""}
    if len(zoznam) < 2:
        out["note"] = f"jedna konfigurácia: {profily[0]}" if profily else ""
        return out

    kluce = {k for r in zoznam for k in (r.get("params") or {})}
    rozdiely: dict[str, list[Any]] = {}
    for k in sorted(kluce):
        hodnoty = {json.dumps((r.get("params") or {}).get(k), sort_keys=True, default=str)
                   for r in zoznam}
        if len(hodnoty) > 1:
            rozdiely[k] = [json.loads(v) for v in sorted(hodnoty)][:6]
    out["differing"] = dict(list(rozdiely.items())[:MAX_DIFFS])
    out["mixed"] = bool(rozdiely)
    out["severity"] = "ok" if not rozdiely else ("chyba" if len(profily) > 1 else "pozor")
    if not rozdiely:
        out["note"] = ("všetky behy majú tú istú konfiguráciu"
                       + (f": {profily[0]}" if len(profily) == 1 else ""))
        return out

    mena = list(rozdiely)[:4]
    vymenovane = ", ".join(f"`{m}`" for m in mena) + ("…" if len(rozdiely) > len(mena) else "")
    kolko = f"{len(rozdiely)} {'parametri' if len(rozdiely) == 1 else 'parametroch'}"
    if len(profily) > 1:
        # Rozne profily = rozne strategie zliate dokopy. To je ta chyba, ktora vyrobila
        # neplatne cisla v REZIM_filtre_btcusdt_2026-09-10.md.
        out["note"] = (f"behy NIE SÚ jedna konfigurácia: {len(profily)} rôznych profilov "
                       f"a líšia sa v {kolko} ({vymenovane}). Zliate obchody potom "
                       f"nehovoria o žiadnej z nich — vyber si jednu.")
    else:
        # Jeden profil a predsa iné čísla: buď `--set`, alebo prepočet prahov na ATR
        # v matici (tam je to zámer, lebo prah v bodoch znamená na každom trhu inú vec).
        out["note"] = (f"všetky behy sú z profilu {profily[0]}, ale v {kolko} sa líšia "
                       f"({vymenovane}) — typicky `--set`, alebo prepočet prahov na ATR "
                       f"v matici trhov. Over, či to tak má byť.")
    return out
