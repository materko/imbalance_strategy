"""Fiktívna burza **Tester** pre Freqtrade — `tester.ftexchange`.

Freqtrade púšťa beh len na burze, ktorú pozná ccxt, s timeframom z jej zoznamu a párom
z jej trhov. Táto burza to všetko dodá z našich vlastných dát — testy strážia, že sa
nerozíde s tým, čo Freqtrade vyžaduje, ani s registrom inštrumentov.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("ccxt")
pytest.importorskip("freqtrade")

from tradebot.core.paths import FREQTRADE_DIR
from tradebot.core.types import INSTRUMENTS
from tester import engines, ftexchange
from tester import timeframes as tf_config


@pytest.fixture(scope="module", autouse=True)
def registered():
    ftexchange.register()


# --------------------------------------------------------------------------- #
# registrácia
# --------------------------------------------------------------------------- #


def test_ccxt_burzu_pozna_synchronne_aj_asynchronne():
    """Freqtrade načítava trhy asynchrónnou triedou a kopíruje ich do synchrónnej."""
    import ccxt
    import ccxt.async_support as ccxt_async

    for module in (ccxt, ccxt_async):
        assert ftexchange.NAME in module.exchanges
        assert hasattr(module, ftexchange.NAME)


def test_freqtrade_najde_nasu_triedu_burzy():
    """Resolver hľadá `freqtrade.exchange.<Meno>`; bez toho by vzal generickú triedu."""
    import freqtrade.exchange as ft_exchange

    from freqtrade.exchange import Exchange

    cls = getattr(ft_exchange, ftexchange.TITLE)
    assert issubclass(cls, Exchange)
    assert cls._ft_has["uses_leverage_tiers"] is False


def test_burza_prejde_kontrolou_freqtradu():
    """`validate_exchange` je presne tá kontrola, na ktorej beh spadne ako prvej."""
    from freqtrade.exchange import validate_exchange

    can_use, reason, *_ = validate_exchange(ftexchange.NAME)
    assert can_use, reason


def test_hlasi_vsetky_povinne_schopnosti():
    """Keby Freqtrade pridal ďalšiu povinnú metódu, nech to povie test, nie až beh."""
    from freqtrade.exchange.common import EXCHANGE_HAS_REQUIRED

    has = ftexchange._describe()["has"]
    for name, alternatives in EXCHANGE_HAS_REQUIRED.items():
        assert has.get(name) or any(has.get(alt) for alt in alternatives), name


# --------------------------------------------------------------------------- #
# timeframy a trhy
# --------------------------------------------------------------------------- #


def test_pozna_vsetky_nase_timeframy_vratane_tych_co_burzy_nemaju():
    tfs = ftexchange.timeframes()
    assert set(tfs) == {tf_config.SOURCE_TF, *tf_config.wanted()}
    assert {"2m", "4m", "1w"} <= set(tfs)          # Binance nemá 2m ani 4m
    assert list(tfs) == sorted(tfs, key=tf_config.minutes)


def test_trhy_su_z_registra_instrumentov():
    by_symbol = {m["symbol"]: m for m in ftexchange.markets()}
    inst = INSTRUMENTS["btcusdt_binance"]
    m = by_symbol[inst.symbol]

    assert m["precision"]["price"] == inst.tick_size
    assert m["precision"]["amount"] == inst.qty_step
    assert m["limits"]["amount"]["min"] == inst.min_qty
    assert m["active"] is True


def test_perpetual_je_swap_a_spot_je_spot():
    by_symbol = {m["symbol"]: m for m in ftexchange.markets()}
    perp, spot = by_symbol["BTC/USDT:USDT"], by_symbol["BTC/USDT"]

    assert perp["swap"] and perp["linear"] and perp["type"] == "swap"
    assert perp["settle"] == "USDT" and perp["contractSize"] == 1.0
    assert spot["spot"] and not spot["swap"] and spot["settle"] is None


def test_freqtrade_povazuje_pary_za_obchodovatelne():
    """`market_is_tradable` rozhoduje, či pár vôbec prejde do whitelistu."""
    from freqtrade.enums import TradingMode
    from freqtrade.exchange import Exchange

    by_symbol = {m["symbol"]: m for m in ftexchange.markets()}
    ex = Exchange.__new__(Exchange)
    ex._ft_has = {"ccxt_futures_name": "swap"}
    ex._config = {}
    ex._exchange_ws = None          # inak sa `__del__` sťažuje na nedokončenú inštanciu
    ex._api = ex._api_async = None
    ex.trading_mode = TradingMode.FUTURES
    assert ex.market_is_future(by_symbol["BTC/USDT:USDT"])
    assert ex.market_is_spot(by_symbol["NAS100/USD"])


def test_instrumenty_bez_kotovacej_meny_sa_nepridavaju():
    """`MNQ` a `BTC-USD` sú MultiCharts symboly — Freqtrade by z nich quote nevyčítal."""
    symbols = {m["symbol"] for m in ftexchange.markets()}
    assert "MNQ" not in symbols and "BTC-USD" not in symbols
    assert all("/" in s for s in symbols)


# --------------------------------------------------------------------------- #
# configy
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name,mode,stake", [
    ("config.tester.json", "futures", "USDT"),
    ("config.tester.spot.json", "spot", "USDT"),
    ("config.tester.cfd.json", "spot", "USD"),
])
def test_configy_bezia_na_burze_tester(name, mode, stake):
    cfg = json.loads((FREQTRADE_DIR / name).read_text(encoding="utf-8"))
    assert cfg["exchange"]["name"] == ftexchange.NAME
    assert cfg["trading_mode"] == mode and cfg["stake_currency"] == stake
    assert cfg["dry_run"] is True


def test_engines_posle_kazdy_par_na_spravny_config():
    picked = {key: engines.freqtrade_config(inst).name for key, inst in INSTRUMENTS.items()}
    assert picked["btcusdt_binance"] == "config.tester.json"          # perpetuál
    assert picked["btcusdt_binance_spot"] == "config.tester.spot.json"
    assert picked["nas100_dukascopy"] == "config.tester.cfd.json"     # CFD v USD


def test_chybajuci_timeframe_uz_nie_je_prekazkou():
    """Burza pozná všetky TF a adaptér si súbor poskladá z 1m — blokuje len chýbajúce 1m."""
    inst = INSTRUMENTS["btcusdt_binance"]
    assert engines.freqtrade_blocker(inst, "2m") is None
    assert engines.freqtrade_blocker(inst, "1w") is None
