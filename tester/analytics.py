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
(`tester.regime`). Všetko sa počíta z barov **uzavretých pred** vstupom (bar, v ktorom
vstup nastal, nie), takže sa podľa toho filtrovať dá — a práve tam býva zvyšný edge, keď ho v samotnom patterne už niet.

### Čo je generické a čo vie len stratégia
Vlastnosti odvodené z obchodu sú generické: `trades.json` má rovnaké polia pre každú
stratégiu (Freqtrade ho píše sám, emulátor MultiCharts v tom istom tvare). Plán obchodu
(SL a TP úroveň) sa berie **najprv zo záznamu obchodu**, kde ho engine naozaj drží — dnes
emulátor MultiCharts (`initial_stop_loss_abs`). Freqtrade v tom poli nesie len statický
`stoploss` stratégie (napr. 1 % z ceny pri `-0.99`), nie plán, preto sa preň plán berie
z kresieb stratégie; tie `StrategySpec` pomenuje (`sl_kind`, `tp_kind`) a spájajú sa časom
baru signálu v `enter_tag`. Viď `plan_from_record` a `enrich`.

Ktorý **parameter** danú vlastnosť riadi, je tiež vedomosť stratégie
(`hyperopt_cls.FEATURE_PARAMS`) — vďaka tomu analytika nekončí zistením, ale odkazom na
to, čo sa dá ladiť.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Sequence

from tradebot.core.money import fill_point_value
from tradebot.strategies import get_spec

from .trade_features import enrich

# Metriky, vlastnosti a skupiny obchodov majú vlastné moduly; tu ostávajú dostupné pod
# `tester.analytics`, ako ich volajú checkup, webapp, CLI aj testy.
from .trade_metrics import gross_and_volume, break_even_pct  # noqa: F401
from .trade_features import (  # noqa: F401
    DAYS, Feature, _dt, FEATURES, features_for, MIN_SIGNAL_MS, signal_time_ms, engine_of,
    plan_from_record, _boxes, _box_by_stop,
)
from .trade_splits import (  # noqa: F401
    MIN_BUCKET, QUANTILES, Bucket, Split, split, out_from, analyze, table,
)

__all__ = [
    "config_spread", "dedupe", "config_key", "trades_of", "Loaded",
    "FEATURES", "Feature", "Bucket", "Split", "break_even_pct", "gross_and_volume",
    "features_for", "split", "analyze", "table",
]


@lru_cache(maxsize=None)
def _pine_defaults(strategy: str) -> dict[str, Any]:
    from tradebot.strategies import get_spec

    try:
        return get_spec(strategy).config_cls().to_dict()
    except Exception:  # noqa: BLE001 - neznáma stratégia: bez defaultov, kľúč je len z parametrov
        return {}


def normalized_params(record: dict[str, Any]) -> dict[str, Any]:
    """Parametre behu doplnené Pine defaultmi stratégie a bez `_` metadát.

    Starší beh uložil len prepísané kľúče, novší celý config; beh bez kľúča a beh
    s jeho defaultom sú ale tá istá konfigurácia - kľúč aj porovnanie idú cez toto.
    """
    from .webapp.store import strategy_of

    params = {k: v for k, v in (record.get("params") or {}).items() if not str(k).startswith("_")}
    return {k: _canon(v) for k, v in {**_pine_defaults(strategy_of(record)), **params}.items()}


def _canon(value: Any) -> Any:
    """`1.0` a `1` sú tá istá hodnota - profil ich dáva ako float, beh z JSON ako int
    a odtlačok cez `json.dumps` by ich inak rozlíšil."""
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: _canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canon(v) for v in value]
    return value


def config_key(record: dict[str, Any]) -> str:
    """Odtlačok konfigurácie behu (parametre doplnené defaultmi + stratégia) — identita
    obchodu pre dedupe a kľúč, pod ktorým sa analytika viaže na konfiguráciu."""
    import hashlib

    from .webapp.store import strategy_of

    blob = json.dumps({"s": strategy_of(record), "p": normalized_params(record)},
                      sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:10]


def dedupe(trades: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Ten istý obchod len raz. Vracia `(obchody, koľko duplicít vypadlo)`.

    Referenčné okná sa prekrývajú (`20231001-20241001` a `20240904-20250904` majú
    spoločných 27 dní), takže zliate behy tej istej konfigurácie by ten mesiac počítali
    dvakrát — v Monte Carle, v teste úpadku aj v počte obchodov. Kľúč je **konfigurácia**
    (`_cfg`, dopĺňa `trades_of`), trh, vstup a výstup: dva body sweepu na tom istom okne
    sú dve rôzne stratégie a ich obchody ostanú obidva, aj keď skončili na tom istom stope.
    """
    videne: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for t in trades:
        kluc = (t.get("_cfg"), t.get("pair"), t.get("open_date"), t.get("enter_tag"),
                bool(t.get("is_short")), t.get("close_date"), t.get("close_rate"))
        if kluc in videne:
            continue
        videne.add(kluc)
        out.append(t)
    return out, len(trades) - len(out)


@dataclass
class Loaded:
    """Obchody vybraných behov po obohatení a dedupe."""

    trades: list[dict[str, Any]] = field(default_factory=list)
    #: koľko obchodov vypadlo ako duplicita z prekrývajúcich sa okien
    duplicates: int = 0
    #: `id behu -> počet obchodov` pred dedupe (do hlavičky výpisu)
    per_run: dict[str, int] = field(default_factory=dict)


def trades_of(records: Sequence[dict[str, Any]], trades_fn: Callable[[str], Any],
              chart_fn: Callable[[str], Any], *, strategy: str = "",
              with_market: bool = True) -> Loaded:
    """Obchody behov, obohatené kresbami (a stavom trhu) a bez duplicít — **jediné**
    miesto, kde sa zliate obchody skladajú. Každý konzument (checkup, webapp analytika,
    prop, paper, CLI) ide tadiaľto, inak by sa dedupe alebo enrichment v niektorej
    kópii stratili.

    `trades_fn(run_id)` a `chart_fn(run_id)` sú sklad behov (`RunStore.trades/chart`)
    alebo čokoľvek, čo ten istý tvar vráti (webapp API pri cudzom klone).
    """
    out = Loaded()
    vsetky: list[dict[str, Any]] = []
    for rec in records:
        run_id = rec.get("id") or ""
        t = trades_fn(run_id)
        if not t:
            continue
        nast = rec.get("settings") or {}
        # starší záznam bez hodnoty bodu (cudzí klon cez API) -> z inštrumentu páru
        fill_point_value(t, nast.get("pair"))
        strat = strategy or nast.get("strategy") or "ibs"
        obohatene = enrich([dict(x) for x in t], chart_fn(run_id), strat,
                           pair=(nast.get("pair") or "") if with_market else "",
                           timeframe=nast.get("timeframe") or "",
                           engine=nast.get("engine") or "")
        cfg = config_key(rec)
        for x in obohatene:
            x["_cfg"] = cfg
        out.per_run[run_id] = len(obohatene)
        vsetky += obohatene
    out.trades, out.duplicates = dedupe(vsetky)
    return out


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
