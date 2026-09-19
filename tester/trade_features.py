"""Vlastnosti obchodu pre analytiku (čas, smer, SL, RR, exkurzia…) a doplnenie
obchodov o plán z kresieb behu (`enrich`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from tradebot.strategies import get_spec


DAYS = ("pondelok", "utorok", "streda", "štvrtok", "piatok", "sobota", "nedeľa")


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
            note="ATR pri vstupe delené mediánom ATR za predošlý týždeň. 1,0 je bežný stav, "
                 "2,0 dvojnásobne rozkolísaný. Náhrada za „pozri sa na VIX“, ktorá funguje na každom trhu."),
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


#: Najmenší čas v ms, ktorý sa v `enter_tag` berie ako čas baru signálu (rok 1973).
#: Menšie číslo za dvojbodkou je index baru alebo poradie objednávky — MultiCharts píše
#: `gap:1234`, `orb:london:29` — a to sa s časom kresby spárovať nesmie.
MIN_SIGNAL_MS = 100_000_000_000

#: Polia záznamu obchodu s plánom obchodu, pri enginoch, ktoré ho tam píšu ako plán.
#: `initial_take_profit_abs` emulátor zatiaľ nepíše; keď ho začne, RR sa doplní bez kresieb.
RECORD_SL, RECORD_TP = "initial_stop_loss_abs", "initial_take_profit_abs"


def signal_time_ms(tag: Any) -> int | None:
    """Čas baru signálu z `enter_tag` (`<prefix>:<čas v ms>`), alebo `None`.

    `None` aj vtedy, keď je za poslednou dvojbodkou číslo, ktoré nie je čas — index baru
    z MultiCharts by sa inak tváril ako milisekundy.
    """
    cas = str(tag or "").rsplit(":", 1)[-1]
    if not cas.isdigit():
        return None
    hodnota = int(cas)
    return hodnota if hodnota >= MIN_SIGNAL_MS else None


def engine_of(trade: dict[str, Any], engine: str = "") -> str:
    """Engine, ktorý obchod vyrobil. Bez udania podľa tvaru riadku: `order_type` píše len
    emulátor MultiCharts, Freqtrade riadky ho nemajú (`webapp.runner._TRADE_COLS`)."""
    if engine:
        return str(engine)
    return "multicharts" if "order_type" in trade else "freqtrade"


def _on_side(level: Any, open_rate: float, above: bool) -> float | None:
    """Kladná úroveň nad (`above`) alebo pod vstupom, inak `None`."""
    try:
        cena = float(level)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(cena) or cena <= 0 or not open_rate:
        return None
    return cena if (cena > open_rate if above else cena < open_rate) else None


def plan_from_record(trade: dict[str, Any], engine: str = "") -> tuple[float | None, float | None]:
    """`(SL, TP)` plánované pri vstupe, ak ich záznam obchodu drží ako plán, inak `None`.

    MultiCharts (emulátor) píše do `initial_stop_loss_abs` stop objednávky pri vstupe.
    Freqtrade tam má statický `stoploss` stratégie, ktorý s plánom nesúvisí (pri IBS
    1 % z ceny), takže pre Freqtrade sa zo záznamu neberie nič. Stop na ziskovej strane
    vstupu (vyplnenie za stopom) sa za plán nepovažuje.
    """
    if engine_of(trade, engine) != "multicharts":
        return None, None
    open_rate = float(trade.get("open_rate") or 0.0)
    short = bool(trade.get("is_short"))
    sl = _on_side(trade.get(RECORD_SL), open_rate, above=short)
    tp = _on_side(trade.get(RECORD_TP), open_rate, above=not short) if sl is not None else None
    return sl, tp


def _boxes(chart: dict[str, Any] | None, kind: str) -> dict[int, tuple[float, float]]:
    """`x1 -> (y1, y2)` kresieb daného druhu. Box je od vstupu po stop (TP box od vstupu po
    cieľ), ale poradie `y1`/`y2` závisí od smeru — hore je vyššia cena."""
    out: dict[int, tuple[float, float]] = {}
    if not chart or not kind:
        return out
    for o in chart.get("objects") or ():
        if o.get("k") == kind and o.get("x1") is not None:
            out[int(o["x1"])] = (float(o.get("y1", 0)), float(o.get("y2", 0)))
    return out


def _box_by_stop(sl_boxes: dict[int, tuple[float, float]], open_ms: int | None,
                 stop: float, short: bool) -> int | None:
    """`x1` najneskoršieho SL boxu pred vstupom so stopom na úrovni `stop`.

    Obchod z MultiCharts nenesie čas signálu (tag je ID objednávky), ale nesie stop — a box
    plánu s tým istým stopom, nakreslený pred vyplnením, je ten istý plán.
    """
    if open_ms is None:
        return None
    tolerancia = abs(stop) * 1e-9 + 1e-9
    # Stop je horná hrana boxu pri shorte, dolná pri longu.
    kandidati = [x for x, (y1, y2) in sl_boxes.items()
                 if x <= open_ms and abs((max if short else min)(y1, y2) - stop) <= tolerancia]
    return max(kandidati) if kandidati else None


def enrich(trades: list[dict[str, Any]], chart: dict[str, Any] | None,
           strategy: str = "ibs", *, pair: str = "", timeframe: str = "",
           engine: str = "") -> list[dict[str, Any]]:
    """Doplní obchodom vzdialenosť stopu (`_sl_pct`) a plánovaný RR (`_rr_planned`).

    Poradie zdrojov plánu:

    1. **záznam obchodu** (`plan_from_record`) — MultiCharts má stop pri vstupe priamo
       v riadku. `_sl_pct` je vtedy `|open_rate - stop|`, teda riziko skutočne
       vyplnenej pozície; na nej stojí sizing v portfóliu a prop simulácii.
    2. **kresby stratégie** (`sl_kind`, `tp_kind`) — Freqtrade riadok plán nenesie.
       Spája sa časom baru signálu: `enter_tag` je `<prefix>:<čas v ms>` a box ho má
       v `x1`. Obchod MultiCharts (tag je ID objednávky) sa s boxom spáruje cez úroveň
       stopu — kvôli TP, ktorý jeho riadok zatiaľ nemá.

    `_plan_src` hovorí, odkiaľ plán je (`record`, `chart`, `record+chart`): pri `record`
    bez `_rr_planned` je TP **neznámy**, nie chýbajúci (`tester.nulltest` to rozlišuje).
    Prázdny `engine` = určí sa z tvaru riadku (`engine_of`).
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
    sl_boxes = _boxes(chart, sl_kind)
    tp_boxes = _boxes(chart, tp_kind) if sl_boxes else {}

    for t in trades:
        open_rate = float(t.get("open_rate") or 0.0)
        if not open_rate:
            continue
        # Už obohatený obchod a žiadne kresby: nič nové sa nedozvieme (idempotencia voči
        # `analyze` nad obchodmi z `trades_of`, ktorý kresby už použil).
        if "_sl_pct" in t and not sl_boxes:
            continue
        stop, ciel = plan_from_record(t, engine)

        box_x = signal_time_ms(t.get("enter_tag")) if sl_boxes else None
        if box_x is not None and box_x not in sl_boxes:
            box_x = None
        if box_x is None and stop is not None and sl_boxes:
            otvorenie = _dt(t.get("open_date"))
            box_x = _box_by_stop(sl_boxes, int(otvorenie.timestamp() * 1000) if otvorenie else None,
                                 stop, bool(t.get("is_short")))

        src: list[str] = []
        rr: float | None = None
        if stop is not None:
            t["_sl_pct"] = round(abs(open_rate - stop) / open_rate * 100.0, 4)
            src.append("record")
            if ciel is not None:
                rr = abs(ciel - open_rate) / abs(open_rate - stop)
        if box_x is not None:
            sl_dist = abs(sl_boxes[box_x][0] - sl_boxes[box_x][1])
            if stop is None:
                t["_sl_pct"] = round(sl_dist / open_rate * 100.0, 4)
            src.append("chart")
            tp = tp_boxes.get(box_x)
            if rr is None and tp and sl_dist > 0:
                rr = abs(tp[0] - tp[1]) / sl_dist
        if rr is not None:
            t["_rr_planned"] = round(rr, 2)
        if src:
            t["_plan_src"] = "+".join(src)
    return trades
