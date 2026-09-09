"""Burza **Tester** — fiktívna burza pre Freqtrade, ktorá pozná naše páry a všetky timeframy.

    python -m tester.ftrun backtesting --config deploy/freqtrade/config.tester.json …
    python -m tester.ftexchange           # čo burza ponúka (kontrola)

### Načo to je
Freqtrade kontroluje beh proti **skutočnej burze z ccxt**: timeframe musí byť v jej zozname,
pár v jej trhoch. Preto sa nedalo backtestovať na 2m ani 4m (Binance ich nemá, Coinbase nemá
ani 3m) a Dukascopy CFD sa museli voziť na cudzej burze s doplneným `market info`.

Dáta pritom máme vlastné — sklad sviečok v `data/tester/`. Chýbala len burza, ktorá by
povedala „tieto páry a tieto timeframy poznám". Tou je Tester: ccxt trieda bez siete, ktorá
zoznam trhov poskladá z `INSTRUMENTS` (tick, krok množstva, limity sedia s inštrumentom,
takže sizing je ten istý ako v MultiCharts) a zoznam timeframov z `tester/timeframes.json`.

### Čo to NEROBÍ
Nesťahuje, neobchoduje, nemá ceny. Je to len **popis trhu** pre backtest, hyperopt a FreqAI;
v dry-run ani live sa nesmie použiť a odmietne to (`validate_demo_trading`). Poplatky si
zadávaš sám (`--fee`), funding je nula — dummy burza nemá čo účtovať.

### Ako sa registruje
`register()` dopíše triedu do `ccxt`, `ccxt.async_support` aj do `freqtrade.exchange`, takže
ju Freqtrade nájde ako ktorúkoľvek inú. Musí sa to stať **pred** štartom Freqtradu — na to je
`python -m tester.ftrun`, ktorý registráciu spraví a potom pustí Freqtrade CLI.
"""

from __future__ import annotations

from typing import Any

from tradebot.core.types import INSTRUMENTS, InstrumentSpec

from . import timeframes as tf_config

__all__ = ["NAME", "TITLE", "markets", "timeframes", "register", "main"]

#: Meno burzy v configu (`exchange.name`) aj v ccxt.
NAME = "tester"
TITLE = "Tester"

#: Poplatky sú nula — reálnu sadzbu dáva beh cez `--fee`, nech je vidno, s čím sa počítalo.
MAKER = TAKER = 0.0

#: Páka, ktorú burza pripustí. Dummy burza nemá margin volania; strop je tu len preto,
#: aby Freqtrade mal čo validovať.
MAX_LEVERAGE = 125.0


def timeframes() -> dict[str, str]:
    """Timeframy, ktoré burza „pozná" — zdrojový 1m plus všetko z `timeframes.json`."""
    names = sorted({tf_config.SOURCE_TF, *tf_config.wanted()}, key=tf_config.minutes)
    return {name: name for name in names}


def _market(inst: InstrumentSpec) -> dict[str, Any]:
    """Trh v tvare, aký čaká ccxt a Freqtrade — čísla z `InstrumentSpec`."""
    base, _, rest = inst.symbol.partition("/")
    quote, _, settle = rest.partition(":")
    swap = bool(settle)
    return {
        "id": inst.symbol.replace("/", "").replace(":", ""),
        "lowercaseId": None,
        "symbol": inst.symbol,
        "base": base,
        "quote": quote,
        "settle": settle or None,
        "baseId": base,
        "quoteId": quote,
        "settleId": settle or None,
        "type": "swap" if swap else "spot",
        "spot": not swap,
        "margin": False,
        "swap": swap,
        "future": False,
        "option": False,
        "index": False,
        "active": True,
        "contract": swap,
        "linear": swap or None,
        "inverse": False if swap else None,
        "subType": "linear" if swap else None,
        "taker": TAKER,
        "maker": MAKER,
        "contractSize": 1.0 if swap else None,
        "expiry": None,
        "expiryDatetime": None,
        "strike": None,
        "optionType": None,
        "precision": {"amount": inst.qty_step, "price": inst.tick_size, "cost": None, "base": None, "quote": None},
        "limits": {
            "leverage": {"min": 1.0, "max": MAX_LEVERAGE if swap else 1.0},
            "amount": {"min": inst.min_qty, "max": None},
            "price": {"min": inst.tick_size, "max": None},
            "cost": {"min": None, "max": None},
        },
        "created": None,
        "info": {"tradebot_instrument": inst.symbol, "point_value": inst.point_value},
    }


def markets() -> list[dict[str, Any]]:
    """Páry z registry inštrumentov — spot aj perpetuál podľa toho, ako sa volajú.

    Inštrumenty bez kótovacej meny v symbole (`MNQ`, `BTC-USD` z MultiCharts) sem nepatria:
    Freqtrade by z nich nevedel určiť `quote` a beh na nich aj tak ide emulátorom.
    """
    return [_market(inst) for inst in INSTRUMENTS.values() if "/" in inst.symbol]


def _describe() -> dict[str, Any]:
    return {
        "id": NAME,
        "name": TITLE,
        "countries": [],
        "rateLimit": 1,
        "certified": False,
        "pro": False,
        "dex": False,
        # Freqtrade nepustí burzu, ktorá nehlási createOrder/cancelOrder/fetchOrder/
        # fetchBalance/fetchOHLCV/fetchL2OrderBook (`EXCHANGE_HAS_REQUIRED`). Dummy burza
        # ich nemá čo robiť — hlási ich, aby prešla kontrolou, a keby ich niekto naozaj
        # zavolal (dry-run, live), ccxt skončí na `NotSupported`. Živý beh je aj tak
        # zakázaný v `validate_demo_trading`.
        "has": {
            "CORS": None,
            "spot": True,
            "margin": False,
            "swap": True,
            "future": False,
            "option": False,
            "fetchMarkets": True,
            "fetchCurrencies": False,
            "fetchOHLCV": True,
            "fetchL2OrderBook": True,
            "fetchOrderBook": True,
            "fetchTicker": True,
            "fetchTickers": True,
            "fetchTrades": False,
            "fetchOrder": True,
            "fetchOrders": True,
            "fetchOpenOrders": True,
            "fetchClosedOrders": True,
            "fetchMyTrades": True,
            "createOrder": True,
            "createLimitOrder": True,
            "createMarketOrder": True,
            "cancelOrder": True,
            "fetchBalance": True,
            "fetchLeverageTiers": False,
            "fetchFundingRates": False,
            "fetchFundingRateHistory": False,
            "setLeverage": True,
            "setMarginMode": True,
            "fetchPositions": True,
        },
        "timeframes": timeframes(),
        "urls": {"api": {"public": "https://tester.invalid"}, "www": "https://tester.invalid"},
        "api": {},
        "requiredCredentials": {k: False for k in (
            "apiKey", "secret", "uid", "login", "password", "twofa", "privateKey",
            "walletAddress", "token")},
        "options": {"defaultType": "spot"},
    }


def _ccxt_classes():
    """(sync, async) ccxt trieda burzy Tester. Bez siete — trhy sú z registry inštrumentov."""
    import ccxt
    import ccxt.async_support as ccxt_async

    class Tester(ccxt.Exchange):
        def describe(self):
            return self.deep_extend(super().describe(), _describe())

        def fetch_markets(self, params={}):  # noqa: B006  (podpis je z ccxt)
            return markets()

    class AsyncTester(ccxt_async.Exchange):
        def describe(self):
            return self.deep_extend(super().describe(), _describe())

        async def fetch_markets(self, params={}):  # noqa: B006
            return markets()

    Tester.__name__ = AsyncTester.__name__ = NAME
    return Tester, AsyncTester


def _freqtrade_class():
    """Freqtrade nadstavba: futures bez fundingu a bez likvidácie — dummy burza ich nemá."""
    from freqtrade.enums import MarginMode, TradingMode
    from freqtrade.exchange import Exchange

    class Tester(Exchange):
        """Fiktívna burza pre backtest, hyperopt a FreqAI nad vlastnými dátami."""

        _ft_has: dict = {
            **Exchange._ft_has,
            "ohlcv_candle_limit": 1000,
            "ohlcv_has_history": True,
            "trades_has_history": False,
            "needs_trading_fees": False,
            "tickers_have_price": False,
            "l2_limit_range": None,
            # Bez tierov: dummy burza nemá margin volania ani likvidáciu, a backtest
            # by inak odmietol každý pár ("got no leverage tiers available").
            "uses_leverage_tiers": False,
        }
        _supported_trading_mode_margin_pairs: list[tuple] = [
            (TradingMode.FUTURES, MarginMode.ISOLATED),
        ]

        def get_max_leverage(self, pair: str, stake_amount: float | None) -> float:
            return MAX_LEVERAGE

        def load_leverage_tiers(self) -> dict:
            return {}

        def fill_leverage_tiers(self) -> None:
            self._leverage_tiers = {}

        def get_funding_fees(self, pair: str, amount: float, is_short: bool, open_date) -> float:
            """Dummy burza funding neúčtuje — inak by beh závisel od dát, ktoré nemáme."""
            return 0.0

        def get_liquidation_price(self, *args, **kwargs) -> float | None:
            """Bez likvidácie: nie je marža ani tiery, na ktorých by sa počítala."""
            return None

    Tester.__name__ = TITLE
    return Tester


def register() -> None:
    """Sprístupní burzu Tester ccxt-u aj Freqtradu. Volať PRED štartom Freqtradu."""
    import ccxt
    import ccxt.async_support as ccxt_async

    import freqtrade.exchange as ft_exchange

    sync_cls, async_cls = _ccxt_classes()
    for module, cls in ((ccxt, sync_cls), (ccxt_async, async_cls)):
        setattr(module, NAME, cls)
        if NAME not in module.exchanges:
            module.exchanges.append(NAME)

    # Freqtrade hľadá triedu podľa mena burzy s veľkým začiatočným písmenom
    setattr(ft_exchange, TITLE, _freqtrade_class())


def main(argv: list[str] | None = None) -> int:
    """Kontrolný výpis: čo burza ponúka."""
    register()
    tfs = timeframes()
    print(f"burza {NAME!r} ({TITLE}) — {len(markets())} parov, {len(tfs)} timeframov")
    print("  timeframy:", ", ".join(tfs))
    for m in markets():
        typ = "perpetual" if m["swap"] else "spot"
        print(f"  {m['symbol']:<16} {typ:<10} tick {m['precision']['price']:<10g} "
              f"krok {m['precision']['amount']:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
