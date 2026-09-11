"""Dva enginy, ktorými sa dá prehrať tá istá stratégia — a kde má každý dáta.

| engine | čo to je | dáta |
|---|---|---|
| `freqtrade` | Freqtrade backtest v podprocese, fill model Freqtradu | súbor na každý timeframe |
| `multicharts` | emulátor MultiCharts v tomto procese (`MCRunner` + broker podľa MultiCharts) | jeden 1m súbor, vyššie TF sa skladajú v pamäti |

Dáta sú pre oba spoločné — `data/tester/<zdroj>/<trh>/`, delené podľa zdroja a trhu,
nie podľa platformy.

Engine **nie je vlastnosť páru**. Krypto sa dá prehrať aj emulátorom a Dukascopy CFD aj
cez Freqtrade — práve na tom stojí porovnanie oboch ciest
([docs/FREQTRADE.md §G](../docs/FREQTRADE.md)). Obmedzuje to len to, aké dáta sú na disku,
a to hovorí `available()`.

Sviečky sú vždy `data/tester/<zdroj>/<trh>/<PÁR>-<TF>.feather` — zdroj (`binance`, `dukascopy`)
aj trh (`spot`, `futures`) sú adresáre, takže z cesty vidno, čo to je.

Podadresár `futures/` a príponu `-futures` v mene si Freqtrade drží natvrdo
(`IDataHandler._pair_data_filename`), pre spot nepridáva nič. Preto sa mu `--datadir`
podáva rôzne podľa trhu — pri futures o úroveň vyššie, aby si `futures/` doplnil sám,
pri spote priamo na `spot/`. Na disku je tým rozloženie súmerné a `data_dir()` je jediné
miesto, kde tú asymetriu treba vedieť.
"""

from __future__ import annotations

from pathlib import Path

from tradebot.core.paths import FREQTRADE_DIR, TESTER_DATA
from tradebot.core.types import InstrumentSpec

__all__ = ["FREQTRADE", "MULTICHARTS", "ENGINES", "ENGINE_TITLES",
           "EXCHANGES", "EXCHANGE_TITLES", "DEFAULT_EXCHANGE", "exchanges_for",
           "exchange_timeframes", "one_minute_file", "freqtrade_file", "market_dir",
           "data_dir", "freqtrade_config", "freqtrade_blocker", "available", "default_engine"]

FREQTRADE = "freqtrade"
MULTICHARTS = "multicharts"
ENGINES = (FREQTRADE, MULTICHARTS)

ENGINE_TITLES = {
    FREQTRADE: "Freqtrade",
    MULTICHARTS: "MultiCharts (emulátor)",
}

#: Zdroje, ktoré nie sú ccxt burza — Freqtrade ich vezme len cez vlastný config
#: a nemá pre ne futures podadresár. `databento` = CME futures (MNQ) z Databento,
#: pre Tester ten istý druh zdroja ako Dukascopy: 1m na disku, beh emulátorom.
_OFF_EXCHANGE = ("dukascopy", "databento")


def _is_off_exchange(inst: InstrumentSpec) -> bool:
    return inst.data_source in _OFF_EXCHANGE


def market_dir(inst: InstrumentSpec) -> Path:
    """`data/tester/<zdroj>/<trh>/` — kde sviečky tohto inštrumentu naozaj ležia."""
    return TESTER_DATA / inst.data_source / inst.market


def data_dir(inst: InstrumentSpec) -> Path:
    """Čo podať Freqtradu ako `--datadir`.

    Pri futures na burze je to o úroveň vyššie než `market_dir` — `futures/` si Freqtrade
    doplní sám. Pri spote (a pri CFD, ktoré bežia cez spotový config) je to priamo
    `market_dir`, lebo tam nič nedopĺňa.
    """
    if _is_off_exchange(inst) or inst.is_spot:
        return market_dir(inst)
    return TESTER_DATA / inst.data_source


def freqtrade_file(inst: InstrumentSpec, timeframe: str) -> Path:
    """`BTC/USDT:USDT`, `3m` → `data/tester/binance/futures/BTC_USDT_USDT-3m-futures.feather`.

    Príponu `-futures` pridáva Freqtrade len tomu, čo u neho beží ako futures; CFD cez
    spotový config ju nemá. Emulátor číta tie isté súbory, takže konvencia je jedna.
    """
    suffix = "" if (_is_off_exchange(inst) or inst.is_spot) else "-futures"
    return market_dir(inst) / f"{inst.data_stem}-{timeframe}{suffix}.feather"


def one_minute_file(inst: InstrumentSpec) -> Path:
    """1m sviečky pre emulátor — z toho istého stromu ako Freqtrade."""
    return freqtrade_file(inst, "1m")


#: Burzy, cez ktoré sa dá beh prehnať, a config na každý trh. `tester` je naša fiktívna
#: burza (`tester/ftexchange.py`) — pozná všetky naše páry aj timeframy; ostatné sú
#: skutočné burzy z ccxt a slúžia na kontrolu, či sa niečo nerozišlo s realitou.
TESTER_EXCHANGE = "tester"
DEFAULT_EXCHANGE = TESTER_EXCHANGE

_CONFIGS: dict[str, dict[str, str]] = {
    "tester": {"futures": "config.tester.json", "spot": "config.tester.spot.json",
               "cfd": "config.tester.cfd.json"},
    "binance": {"futures": "config.binance.json", "spot": "config.binance.spot.json"},
    "coinbase": {"spot": "config.coinbase.json"},
    "dukascopy": {"cfd": "config.dukascopy.json"},
}

EXCHANGES = tuple(_CONFIGS)

EXCHANGE_TITLES = {
    "tester": "Tester (fiktívna)",
    "binance": "Binance",
    "coinbase": "Coinbase",
    "dukascopy": "Bitstamp (nosná pre CFD)",
}


def market_kind(inst: InstrumentSpec) -> str:
    """`futures`, `spot` alebo `cfd` — podľa toho sa vyberá config."""
    if _is_off_exchange(inst):
        return "cfd"
    return "spot" if inst.is_spot else "futures"


def exchanges_for(inst: InstrumentSpec) -> list[str]:
    """Burzy, cez ktoré má zmysel tento pár prehnať.

    Vždy naša fiktívna (ak pár pozná) a k tomu tá, odkiaľ sviečky naozaj sú — beh na cudzej
    burze by dal cudzie pravidlá trhu k našim dátam a nič by to nepovedalo.
    """
    from .ftexchange import markets

    kind = market_kind(inst)
    out = []
    if TESTER_EXCHANGE in _CONFIGS and kind in _CONFIGS[TESTER_EXCHANGE]:
        if any(m["symbol"] == inst.symbol for m in markets()):
            out.append(TESTER_EXCHANGE)
    native = "dukascopy" if kind == "cfd" else inst.data_source
    if native != TESTER_EXCHANGE and kind in _CONFIGS.get(native, {}):
        out.append(native)
    return out


def stake_config(inst, exchange: str | None = None) -> Path:
    """Config fiktívnej burzy s `stake_currency` podľa meny kótovania inštrumentu.

    Freqtrade vyhodí z whitelistu každý pár, ktorého kótovacia mena nesedí so
    `stake_currency` configu („Pair JP225/JPY is not compatible with your stake currency
    USD. Removing it from whitelist" a hneď za tým „No pair in whitelist"). Naše
    Dukascopy symboly sú kótované v USD, JPY, EUR aj CAD, takže jeden hotový config
    pokryť nemôže — a bez tohto by šesť trhov matice tichým zlyhaním chýbalo.

    Robí sa to len pre **fiktívnu** burzu Tester: u skutočných búrz je mena daná burzou
    a config sa vymýšľať nesmie.
    """
    import json

    from tradebot.core.paths import TMP_PROFILES

    povodny = freqtrade_config(inst, exchange)
    if exchange not in (None, DEFAULT_EXCHANGE):
        return povodny
    data = json.loads(Path(povodny).read_text(encoding="utf-8"))
    if data.get("stake_currency") == inst.quote_currency:
        return povodny
    data["stake_currency"] = inst.quote_currency
    out = TMP_PROFILES / f"config.tester.{inst.quote_currency.lower()}.{market_kind(inst)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def freqtrade_config(inst: InstrumentSpec, exchange: str | None = None) -> Path:
    """Ktorý Freqtrade config na tento inštrument a burzu sedí.

    Predvolene fiktívna burza **Tester**: pozná naše páry aj všetky timeframy, takže beh
    nie je obmedzený tým, čo ponúka skutočná burza. Configy skutočných búrz ostávajú na
    sťahovanie dát a na kontrolu, či sa niečo nerozišlo s reálnou burzou.
    """
    want = exchange or DEFAULT_EXCHANGE
    configs = _CONFIGS.get(want) or _CONFIGS[DEFAULT_EXCHANGE]
    kind = market_kind(inst)
    name = configs.get(kind) or _CONFIGS[DEFAULT_EXCHANGE][kind]
    return FREQTRADE_DIR / name


def exchange_timeframes(exchange: str) -> frozenset[str]:
    """Timeframy, ktoré burza pozná. Naša fiktívna všetky naše, ostatné podľa ccxt."""
    if exchange == TESTER_EXCHANGE:
        from .ftexchange import timeframes

        return frozenset(timeframes())
    name = "bitstamp" if exchange == "dukascopy" else exchange
    try:
        import ccxt

        return frozenset(getattr(ccxt, name)().timeframes or ())
    except Exception:  # noqa: BLE001  (chýbajúce ccxt ani neznáma burza nesmú zhodiť ponuku)
        return frozenset()


def freqtrade_blocker(inst: InstrumentSpec, timeframe: str,
                     exchange: str | None = None) -> str | None:
    """Prečo sa tento beh cez Freqtrade nedá spustiť — alebo `None`, keď sa dá.

    Chýbajúci súbor prekážka nie je: adaptér si vyšší TF poskladá z 1m
    (`TradebotStrategyBase.ensure_timeframe`), stačí mať 1m sviečky. Prekážkou je
    **timeframe, ktorý zvolená burza nepozná** — taký beh Freqtrade odmietne už pri
    validácii configu. Naša fiktívna burza pozná všetky, skutočné nie (Binance nemá 2m
    ani 4m, Coinbase ani 3m), a práve preto je predvolená.
    """
    if not freqtrade_file(inst, timeframe).exists() and not one_minute_file(inst).exists():
        return f"chýba súbor pre {timeframe} a nie sú ani 1m sviečky, z ktorých ho poskladať"
    want = exchange or DEFAULT_EXCHANGE
    if want not in exchanges_for(inst):
        known = ", ".join(EXCHANGE_TITLES.get(e, e) for e in exchanges_for(inst)) or "žiadna"
        return f"burza {EXCHANGE_TITLES.get(want, want)} tento pár nemá; dostupné: {known}"
    known_tfs = exchange_timeframes(want)
    if known_tfs and timeframe not in known_tfs:
        return f"burza {EXCHANGE_TITLES.get(want, want)} timeframe {timeframe} nepozná"
    return None


def available(inst: InstrumentSpec, timeframe: str = "3m",
              exchange: str | None = None) -> list[str]:
    """Ktoré enginy sa na tomto inštrumente a timeframe dajú spustiť.

    Obom stačí 1m: emulátor si vyššie TF skladá v pamäti, Freqtrade adaptér ich zapíše
    na disk pri štarte behu. Freqtrade navyše potrebuje timeframe, ktorý pozná jeho burza.
    Chýbajúce dáta pre Dukascopy doplní `tester.dukas_import`.
    """
    out = []
    if freqtrade_blocker(inst, timeframe, exchange) is None:
        out.append(FREQTRADE)
    if one_minute_file(inst).exists():
        out.append(MULTICHARTS)
    return out


def default_engine(inst: InstrumentSpec, timeframe: str = "3m") -> str:
    """Predvolený engine: Freqtrade, ak preň sú dáta; inak emulátor.

    Pre Dukascopy symboly to prakticky znamená emulátor — ten je pre ne referenciou,
    lebo sedí s tým, čo v MultiCharts naozaj pobeží.
    """
    engines = available(inst, timeframe)
    if _is_off_exchange(inst):
        return MULTICHARTS if MULTICHARTS in engines else FREQTRADE
    return engines[0] if engines else FREQTRADE


# --------------------------------------------------------------------------- #
# FreqAI: filter nad portom
# --------------------------------------------------------------------------- #

#: Predvolené nastavenie AI vrstvy. Zámerne skromné — model má rádovo stovky nálepiek,
#: takže široké okno a málo pretrénovaní je bezpečnejšie než opak.
AI_DEFAULTS: dict[str, Any] = {
    "model": "LightGBMClassifier",
    # Dva roky tréningu a pol roka medzi pretrénovaniami. Sú to zámerne veľké čísla:
    # nálepku dostane len bar so signálom, takže stratégia s 30 obchodmi za rok má
    # v polročnom okne pätnásť nálepiek — a model, ktorý v tréningu nevidí obe triedy,
    # sa vôbec nenatrénuje. Menšie okná znamenajú častejšie pretrénovanie a ešte menej
    # nálepiek na jedno.
    "train_period_days": 730,
    "backtest_period_days": 180,
    "min_probability": 0.55,
    "adjust": {},
}


def ai_config(inst: InstrumentSpec, exchange: str | None, timeframe: str,
              ai: dict[str, Any]) -> Path:
    """Config s blokom `freqai` a s naším nastavením filtra.

    Vyrába sa zo `stake_config`, aby ostalo všetko ostatné (mena, burza) rovnaké. Príznaky
    si stratégia počíta sama v `feature_engineering_standard`, takže sa tu **vypína** celé
    štandardné rozširovanie FreqAI: žiadne posunuté sviečky, žiadne korelované páry,
    jedna perióda. Pri stovkách nálepiek by desiatky príznakov naučili model vzorku.
    """
    import json

    from tradebot.core.paths import TMP_PROFILES

    nastavenie = {**AI_DEFAULTS, **(ai or {})}
    data = json.loads(Path(stake_config(inst, exchange)).read_text(encoding="utf-8"))
    data["freqai"] = {
        "enabled": True,
        "identifier": nastavenie.get("identifier") or "tradebot",
        "train_period_days": int(nastavenie["train_period_days"]),
        "backtest_period_days": int(nastavenie["backtest_period_days"]),
        "fit_live_predictions_candles": 300,
        "purge_old_models": 2,
        "feature_parameters": {
            "include_timeframes": [timeframe],
            "include_corr_pairlist": [],
            "label_period_candles": 0,
            "include_shifted_candles": 0,
            "indicator_periods_candles": [10],
            "DI_threshold": 0,
            "weight_factor": 0,
            "principal_component_analysis": False,
            "use_SVM_to_remove_outliers": False,
        },
        "data_split_parameters": {"test_size": 0.2, "shuffle": False},
        "model_training_parameters": dict(nastavenie.get("model_training_parameters") or {}),
    }
    # Naše nastavenie ide do configu vedľa, nie do `freqai` — Freqtrade by cudzí kľúč
    # v jeho schéme odmietol.
    data["tradebot_ai"] = {
        "min_probability": float(nastavenie["min_probability"]),
        "adjust": dict(nastavenie.get("adjust") or {}),
    }
    out = TMP_PROFILES / f"config.ai.{inst.quote_currency.lower()}.{market_kind(inst)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
