"""Matica trhov a timeframov: ten istý profil na všetkom, čo máme, v jednej tabuľke.

### Načo to je
Že stratégia funguje na BTC, hovorí o BTC. Že tá istá myšlenka funguje na indexe, na
forexe **aj** na komodite, hovorí o myšlienke — a je to najsilnejší dôkaz kvality, aký sa
z historických dát dá dostať. Naopak edge, ktorý drží presne na jednom páre a nikde inde,
je s vysokou pravdepodobnosťou vlastnosť toho páru (alebo toho, ako sme prahy ladili),
nie stratégie.

Matica je preto sweep, v ktorom sa nemení parameter, ale **trh a timeframe**. Každá bunka
je obyčajný backtest, ktorý ostane v histórii.

### Prečo sa profil musí najprv prepočítať
Toto je tá časť, bez ktorej by bola celá matica na nič. Referenčné profily majú prahy
v **absolútnych cenových bodoch** — `minImbSizePoints = 2,5` znamená 2,5 dolára na BTC.
Ten istý profil na EURUSD (cena 1,08) znamená prah 2,5 **celej ceny**, teda podmienku,
ktorá nikdy nenastane; na kakau naopak podmienku, ktorá nastane vždy. Výsledok by nebol
„na forexe to nefunguje", ale „profil je nezmysel" — a to dvoje sa v tabuľke nedá rozlíšiť.

Preto sa veľkostné polia prevedú na jednotku **`atr`**, jedinú naozaj prenositeľnú:
hodnota sa vydelí mediánom ATR referenčného trhu, na ktorom bol profil ladený. `2,5` na
BTC 3m, kde je typický ATR 50, sa stane `0,05 atr` — teda „dvadsatina typického rozsahu
baru", čo je tvrdenie, ktoré platí na každom trhu rovnako.

Kto to nechce, dostane maticu s varovaním pri každom cudzom trhu (`check_instrument`),
ale závery z nej nepatria nikam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from tradebot.core.types import INSTRUMENTS, SizeSpec
from tradebot.strategies import get_spec

from . import sweep as sweep_mod

__all__ = [
    "ATR_LEN", "Cell", "median_atr", "to_relative", "expand", "playable", "rank",
    "matrix", "verdict", "table", "contract_notional", "wallet_check",
]

#: Dĺžka ATR — musí sedieť s `tradebot.core.history.BarHistory` (Pine `ta.atr(14)`),
#: inak by prepočet znamenal inú vec než to, čo engine potom počíta.
ATR_LEN = 14

#: Menej než toľko obchodov v bunke a číslo je šum; v tabuľke sa označí.
MIN_TRADES = 10


@dataclass(frozen=True)
class Cell:
    """Jedna bunka matice: trh × timeframe."""

    pair: str
    timeframe: str

    @property
    def key(self) -> str:
        return f"{self.pair}|{self.timeframe}"


# --------------------------------------------------------------------------- #
# prepočet profilu na prenositeľné jednotky
# --------------------------------------------------------------------------- #


def median_atr(pair: str, timeframe: str, timerange: str | None = None) -> float | None:
    """Medián Wilderovho ATR(14) daného trhu a TF. `None`, keď nie sú sviečky.

    Medián, nie priemer: ATR má dlhý pravý chvost (jeden krach zdvihne priemer o desiatky
    percent) a nás zaujíma typický bar, nie výnimočný.
    """
    import numpy as np

    from .webapp.chart import series

    try:
        ts, cols = series(pair, timeframe)
    except (FileNotFoundError, ValueError):
        return None
    high, low, close = cols["high"], cols["low"], cols["close"]
    if timerange:
        from datetime import datetime, timezone

        try:
            a, b = timerange.split("-")
            od = int(datetime.strptime(a, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
            do = int(datetime.strptime(b, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            od, do = ts[0], ts[-1]
        i, j = int(np.searchsorted(ts, od)), int(np.searchsorted(ts, do))
        high, low, close = high[i:j], low[i:j], close[i:j]
    if len(close) < ATR_LEN * 3:
        return None

    prev = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))
    # Wilderov ATR je rekurzívny (RMA), takže sa nedá vektorizovať jedným výrazom;
    # exponenciálna váha 1/n je jeho presný ekvivalent pre dlhý rad.
    atr = np.empty_like(tr)
    atr[:ATR_LEN] = tr[:ATR_LEN].mean()
    alfa = 1.0 / ATR_LEN
    for i in range(ATR_LEN, len(tr)):
        atr[i] = atr[i - 1] * (1 - alfa) + tr[i] * alfa
    return float(np.median(atr[ATR_LEN:]))


def to_relative(params: dict[str, Any], *, strategy: str = "ibs", ref_pair: str,
                ref_timeframe: str, timerange: str | None = None) -> tuple[dict[str, Any], list[str]]:
    """Veľkostné polia v `abs` prepočíta na `atr` podľa referenčného trhu.

    Vráti `(nové parametre, čo sa zmenilo)`. Bez referenčných sviečok nezmení nič a vráti
    dôvod — tichý prepočet zlou mierkou by bol horší než žiadny.
    """
    from .webapp.runner import instrument_for_pair

    cls = get_spec(strategy).config_cls
    # `abs` aj `ticks` treba prepočítať, len každé inou mierkou. Prah v tickoch sa medzi
    # trhmi škáluje veľkosťou ticku, a tá s typickým rozsahom baru nijako nesúvisí:
    # `imbMaxDistTicks = 100` je na BTC 0,115 ATR, na EURUSD 3,86 ATR (ATR/tick je 602
    # oproti 26, teda 23-násobný rozdiel). Prvá verzia prepočtu prepisovala len `abs`
    # a forex mal preto NULA signálov — nie nula obchodov, žiadne signály.
    prepocitat = [n for n in cls.SIZE_FIELDS
                  if _unit_of(params, n, cls) in ("abs", "ticks") and _value_of(params, n) > 0]
    if not prepocitat:
        return dict(params), []

    atr = median_atr(ref_pair, ref_timeframe, timerange)
    if not atr or atr <= 0:
        return dict(params), [f"prepočet sa nedal urobiť: chýbajú sviečky {ref_pair} {ref_timeframe}"]

    try:
        tick = float(INSTRUMENTS[instrument_for_pair(ref_pair)].tick_size)
    except (KeyError, ValueError):
        return dict(params), [f"prepočet sa nedal urobiť: neznámy inštrument {ref_pair}"]

    out = dict(params)
    zmeny = [f"referenčný ATR({ATR_LEN}) na {ref_pair} {ref_timeframe} je {atr:g}"
             f" (tick {tick:g}, teda {atr / tick:.0f} tickov na ATR)"]
    for name in prepocitat:
        jednotka = _unit_of(params, name, cls)
        stara = _value_of(params, name)
        v_cene = stara * tick if jednotka == "ticks" else stara
        nova = round(v_cene / atr, 6)
        out[name] = {"value": nova, "unit": "atr"}
        zmeny.append(f"{name}: {stara:g} {jednotka} → {nova:g} atr")
    return out, zmeny


def _unit_of(params: dict[str, Any], name: str, cls) -> str:
    """Jednotka veľkostného poľa. Holé číslo znamená **predvolenú jednotku poľa**.

    Toto je miesto, kde sa dá ľahko pomýliť: vo formulári aj v profile je
    `minImbSizePoints: 2.5` bez jednotky a znamená to 2,5 absolútneho cenového bodu,
    lebo `SIZE_FIELDS` tak má pole zadefinované. Prvá verzia prepočtu hľadala len
    slovníky `{"value":…, "unit":…}`, takže na profile z formulára nespravila nič —
    a matica potom mala prah 2,5 na EURUSD, teda nula obchodov.
    """
    hodnota = params.get(name)
    if isinstance(hodnota, dict):
        return str(hodnota.get("unit") or cls.SIZE_FIELDS[name])
    unit = getattr(hodnota, "unit", None)
    return str(unit or cls.SIZE_FIELDS[name])


def _value_of(params: dict[str, Any], name: str) -> float:
    hodnota = params.get(name)
    if isinstance(hodnota, dict):
        return float(hodnota.get("value") or 0.0)
    if hasattr(hodnota, "value"):
        return float(hodnota.value)
    try:
        return float(hodnota)
    except (TypeError, ValueError):
        return 0.0


def contract_notional(pair: str, timeframe: str = "3m",
                      timerange: str | None = None) -> float | None:
    """Nominál JEDNÉHO kontraktu pri typickej cene trhu. `None`, keď nie sú sviečky.

    Toto je najčastejší dôvod, prečo bunka matice skončí s nula obchodmi napriek tomu, že
    signály vznikli: jeden lot EURUSD je 100 000 jednotiek bázy, teda pri cene 1,08 asi
    108 000 USD. S peňaženkou 10 000 a bez páky sa jeden kontrakt nezmestí, veľkosť sa
    oreže na nulu a beh vyzerá ako „tu stratégia nefunguje".
    """
    import numpy as np

    from .webapp.chart import series
    from .webapp.runner import instrument_for_pair

    try:
        inst = INSTRUMENTS[instrument_for_pair(pair)]
        ts, cols = series(pair, timeframe)
    except (KeyError, ValueError, FileNotFoundError):
        return None
    if not len(cols["close"]):
        return None
    cena = float(np.median(cols["close"]))
    return cena * float(inst.point_value) * float(inst.min_qty or 1.0)


def wallet_check(pairs: Iterable[str], wallet: float, timeframe: str = "3m",
                 timerange: str | None = None) -> dict[str, float]:
    """`{trh: nominál jedného kontraktu}` pre trhy, kde sa do peňaženky nezmestí.

    Break-even poplatok od peňaženky **nezávisí** (je to hrubý zisk na objem), takže
    zvýšiť ju len preto, aby sa kontrakt zmestil, tabuľku nezkreslí — na rozdiel od PnL
    v percentách, ktoré od nej závisí priamo.
    """
    out: dict[str, float] = {}
    for pair in pairs:
        nominal = contract_notional(pair, timeframe, timerange)
        if nominal is not None and nominal > wallet:
            out[pair] = round(nominal, 2)
    return out


def warnings_for(params: dict[str, Any], pairs: Iterable[str], *,
                 strategy: str = "ibs") -> dict[str, list[str]]:
    """Varovania `check_instrument` pre každý trh matice — čo tam nemusí dávať zmysel."""
    from .webapp.runner import instrument_for_pair

    cfg = get_spec(strategy).config_cls.from_dict(
        {k: v for k, v in params.items() if not k.startswith("_")})
    out: dict[str, list[str]] = {}
    for pair in pairs:
        try:
            inst = INSTRUMENTS[instrument_for_pair(pair)]
        except (KeyError, ValueError):
            continue
        problemy = cfg.check_instrument(inst)
        if problemy:
            out[pair] = problemy
    return out


# --------------------------------------------------------------------------- #
# mriežka
# --------------------------------------------------------------------------- #


def expand(pairs: Sequence[str], timeframes: Sequence[str]) -> list[Cell]:
    """Bunky matice. Poradie je „po trhoch", aby prvé výsledky pokryli viac trhov."""
    if not pairs:
        raise ValueError("matica potrebuje aspoň jeden trh")
    if not timeframes:
        raise ValueError("matica potrebuje aspoň jeden timeframe")
    return [Cell(p, tf) for p in pairs for tf in timeframes]


def playable(cells: Sequence[Cell], *, exchange: str = "tester", engine: str | None = None,
             params: dict[str, Any] | None = None) -> tuple[list[Cell], dict[str, str]]:
    """Rozdelí bunky na spustiteľné a nespustiteľné (s dôvodom) — bez toho by časť
    matice tichým zlyhaním chýbala a vyzeralo by to ako „nefunguje"."""
    from . import engines
    from .webapp.chart import available_timeframes
    from .webapp.runner import check_market_rules, instrument_for_pair

    ok: list[Cell] = []
    preco: dict[str, str] = {}
    for cell in cells:
        try:
            inst = INSTRUMENTS[instrument_for_pair(cell.pair)]
        except (KeyError, ValueError) as exc:
            preco[cell.key] = str(exc)
            continue
        if cell.timeframe not in available_timeframes(cell.pair):
            preco[cell.key] = f"chýbajú {cell.timeframe} dáta"
            continue
        if params is not None:
            # Spot nemá páku ani shorty. Zistiť to TERAZ je rozdiel medzi „preskočené,
            # lebo profil má páku 10" a šiestimi červenými bunkami bez vysvetlenia.
            try:
                check_market_rules(cell.pair, params)
            except ValueError as exc:
                preco[cell.key] = str(exc)
                continue
        moznosti = engines.available(inst, cell.timeframe, exchange)
        if engine and engine not in moznosti:
            preco[cell.key] = f"engine {engine} sa tu spustiť nedá"
            continue
        if not moznosti:
            preco[cell.key] = "žiadny engine sa tu spustiť nedá"
            continue
        ok.append(cell)
    return ok, preco


def rank(records: Sequence[dict[str, Any]], goal: str = "break_even",
         max_dd: float | None = None, min_trades: int | None = MIN_TRADES) -> list[dict[str, Any]]:
    """Poradie buniek podľa toho istého kritéria ako sweep — aby to bola jedna reč."""
    return sweep_mod.rank(list(records), goal, max_dd=max_dd, min_trades=min_trades)


def matrix(records: Sequence[dict[str, Any]], metric: str = "break_even_pct") -> dict[str, Any]:
    """Tabuľka `trh × timeframe` s jednou metrikou v bunke."""
    pary: list[str] = []
    tfs: list[str] = []
    bunky: dict[str, dict[str, Any]] = {}
    for rec in records:
        nast = rec.get("settings") or {}
        pair, tf = nast.get("pair"), nast.get("timeframe") or "3m"
        if not pair:
            continue
        if pair not in pary:
            pary.append(pair)
        if tf not in tfs:
            tfs.append(tf)
        vysledok = rec.get("result") or {}
        # Rozdiel medzi „setup tu nikdy nenastane" a „signály boli, ale Freqtrade každý
        # vstup odmietol" je zásadný: prvé je vlastnosť stratégie na tom trhu, druhé je
        # náš problém s peňaženkou alebo sizingom. `zero_trade_warning` to už rozlišuje.
        bez_obchodov = not (vysledok.get("trades") or 0)
        bunky.setdefault(pair, {})[tf] = {
            "id": rec.get("id"),
            "status": rec.get("status"),
            "value": vysledok.get(metric),
            "trades": vysledok.get("trades"),
            "pnl_pct": vysledok.get("pnl_pct"),
            "ok": bool(rec.get("sweep_ok", True)),
            "why": rec.get("sweep_why", ""),
            "empty": ("odmietnute" if bez_obchodov and vysledok.get("warning")
                      else "bez setupu" if bez_obchodov and rec.get("status") == "done"
                      else ""),
            "warning": vysledok.get("warning"),
        }
    tfs.sort(key=_tf_key)
    return {"metric": metric, "pairs": pary, "timeframes": tfs, "cells": bunky}


def _tf_key(tf: str) -> int:
    from tradebot.core.candles import timeframe_minutes

    try:
        return timeframe_minutes(tf)
    except (ValueError, KeyError):
        return 0


def verdict(records: Sequence[dict[str, Any]], min_trades: int = MIN_TRADES) -> str:
    """Jedna veta: drží myšlienka naprieč trhmi, alebo je to vlastnosť jedného páru?"""
    hotove = [r for r in records if r.get("status") == "done"
              and ((r.get("result") or {}).get("trades") or 0) >= min_trades]
    if not hotove:
        return "Ziadna bunka nedobehla s dostatkom obchodov - bez nich sa hodnotit neda."

    from .hyperopt import edge_of

    # Break-even mínus poplatok TEJ bunky: krypto platí 0,05 %, CFD polovicu spreadu,
    # takže „kladný break-even" bez nákladu by na jednom trhu znamenal zisk a na inom
    # stratu.
    podla_paru: dict[str, list[float]] = {}
    for r in hotove:
        edge = edge_of(r)
        if edge is None:
            continue
        podla_paru.setdefault(r["settings"]["pair"], []).append(edge)
    if not podla_paru:
        return "Bunky dobehli, ale break-even sa nedal spocitat."

    kladne = [p for p, hodnoty in podla_paru.items() if max(hodnoty) > 0]
    n, k = len(podla_paru), len(kladne)
    # Celý zmysel matice je porovnanie NAPRIEČ trhmi. Z jedného-dvoch sa taký záver
    # spraviť nedá a tvrdiť „čiastočne" by bolo zavádzajúce.
    if n < 3:
        return (f"Dobehli len {n} trhy - na zaver naprieč trhmi treba aspoň tri. "
                "Pozri, preco ostatne bunky nedobehli (preskocene / failed).")
    if k == n and n >= 3:
        return (f"MYSLIENKA DRZI: break-even je nad poplatkom na vsetkych {n} trhoch. "
                "To je najsilnejsi dokaz kvality, aky sa z historickych dat da dostat.")
    if k <= 1 and n >= 3:
        return (f"EDGE JE LEN NA JEDNOM TRHU ({k} z {n}). S vysokou pravdepodobnostou je to "
                "vlastnost toho paru alebo toho, ako sme prahy ladili, nie strategie.")
    if k * 2 >= n:
        return (f"CIASTOCNE: break-even je nad poplatkom na {k} z {n} trhov. Pozri, ci maju tie trhy "
                "nieco spolocne (trieda aktiva, volatilita) - to uz je pouzitelny zaver.")
    return (f"SLABE: break-even je nad poplatkom len na {k} z {n} trhov. Skor nahoda nez myslienka.")


# --------------------------------------------------------------------------- #
# výpis
# --------------------------------------------------------------------------- #


def table(report: dict[str, Any], width: int = 9) -> str:
    """Matica ako text — ASCII, konzola na Windows beží v cp1250."""
    tfs = report["timeframes"]
    lines = [f"{'trh':<18}" + "".join(f"{tf:>{width}}" for tf in tfs)]
    lines.append("-" * (18 + width * len(tfs)))
    for pair in report["pairs"]:
        riadok = f"{pair[:18]:<18}"
        for tf in tfs:
            bunka = report["cells"].get(pair, {}).get(tf)
            if bunka is None:
                riadok += f"{'.':>{width}}"
            elif bunka["status"] != "done":
                riadok += f"{bunka['status'][:7]:>{width}}"
            elif bunka["value"] is None:
                # `0 sig` = engine tu nenasel ani jeden setup (vlastnost strategie na tom
                # trhu). `odmiet` = signaly boli, ale vstupy neprosli (nas problem).
                znak = {"bez setupu": "0 sig", "odmietnute": "odmiet"}.get(bunka["empty"], "-")
                riadok += f"{znak:>{width}}"
            else:
                # `!` = bunka je mimo mantinelov (malo obchodov alebo drawdown) - cislo
                # tam je, ale zaver z neho robit netreba.
                znacka = "" if bunka["ok"] else "!"
                text = f"{bunka['value']:.4f}{znacka}"
                riadok += f"{text:>{width}}"
        lines.append(riadok)
    return "\n".join(lines)
