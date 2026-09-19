"""Rozdelenie obchodov podľa vlastnosti na skupiny a hľadanie tých, ktoré kazia
výsledok (`split`, `analyze`, `table`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from tradebot.adapters.freqtrade.hyperplan import knowledge
from tradebot.strategies import get_spec

from .trade_features import Feature, enrich, features_for
from .trade_metrics import _winrate, break_even_pct


#: Menej než toľko obchodov v skupine a číslo je šum, nie zistenie.
MIN_BUCKET = 8


#: Na koľko rovnako veľkých skupín sa delí číselná vlastnosť.
QUANTILES = 4


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
            min_bucket: int = MIN_BUCKET, pair: str = "", timeframe: str = "") -> dict[str, Any]:
    """Celá analytika behu (alebo viacerých behov spolu).

    Vlastnosti sú zoradené podľa toho, koľko by sa dalo získať odfiltrovaním najhoršej
    skupiny — hore je to, čo sa najviac oplatí riešiť. `pair` a `timeframe` treba na
    stav trhu pri vstupe (`tester.regime`): bez nich tie štyri vlastnosti ticho chýbajú.
    `enrich` je idempotentný (stav trhu aj kalendár preskočia už doplnené obchody),
    takže obohatené obchody z `trades_of` sa neprepočítavajú.
    """
    obchody = enrich([dict(t) for t in trades], chart, strategy, pair=pair, timeframe=timeframe)
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
