"""NOA 1.0 (Noise Area, Concretum): engine na syntetických 5m baroch seansy New York.

Testuje sa mechanika podľa článku: pásmo šumu z predošlých dní (dnešok nie), hranice podľa medzery,
rozhodovanie len na kontrolách o celej a o pol, výstup pod max(hranica, VWAP), koniec seansy 16:00,
poistka a pozícia, ktorá prežila do ďalšieho dňa.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType
from tradebot.strategies.noa import NoaConfig, NoaEngine, TradeDirection

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
M5 = 300_000
BASE = 20_000.0
NOISE = 0.001            # každý deň pohyb 0,1 % od otvorenia v každej minúte -> σ = 0,001
FLAT = MarketContext(in_trade_window=True)
LONG = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({"noa:1"}))
SHORT = MarketContext(in_trade_window=True, position_size=-1.0, open_order_ids=frozenset({"noa:1"}))


def weekdays(n: int) -> list[datetime]:
    d, out = datetime(2025, 9, 1, tzinfo=NY), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


DAYS = weekdays(16)
TEST_DAY = DAYS[-1]


def ts(day: datetime, h: int, m: int) -> int:
    """Otvorenie 5m baru o h:m New York."""
    return int(day.replace(hour=h, minute=m).timestamp() * 1000)


def bar(t: int, c: float, o: float | None = None, hi: float | None = None, lo: float | None = None) -> Bar:
    o = c if o is None else o
    return Bar(t, o, max(o, c) + 1 if hi is None else hi, min(o, c) - 1 if lo is None else lo, c, 100.0)


def engine(**kw) -> NoaEngine:
    return NoaEngine(NoaConfig(**kw), MNQ, 5)


def warm(e: NoaEngine) -> None:
    """15 dní seansy 9:30–16:00: open BASE, každý bar zavrie o NOISE vyššie -> včerajšie zavretie BASE × 1,001."""
    for d in DAYS[:-1]:
        first = True
        for k in range(78):
            t = ts(d, 9, 30) + k * M5
            e.on_bar(bar(t, BASE * (1 + NOISE), o=BASE if first else None), None, FLAT)
            first = False


def at(h: int, m: int) -> int:
    """Otvorenie baru testovacieho dňa, ktorý sa ZATVÁRA o h:m."""
    return ts(TEST_DAY, h, m) - M5


def run_day(e: NoaEngine, closes: dict[tuple[int, int], float], ctx=FLAT, until=(16, 0)):
    """Testovací deň od 9:30: bary s danými close (inak BASE), vráti výstupy podľa času zavretia."""
    outs = {}
    t, k = ts(TEST_DAY, 9, 30), 0
    while True:
        close_t = datetime.fromtimestamp((t + M5) / 1000, tz=NY)
        key = (close_t.hour, close_t.minute)
        c = closes.get(key, BASE)
        outs[key] = e.on_bar(bar(t, c, o=BASE if k == 0 else None), None, ctx(key) if callable(ctx) else ctx)
        if key == until:
            return outs
        t += M5
        k += 1


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def closes_(out):
    return [o for o in out.orders if o.action is OrderAction.CLOSE]


UB = BASE * (1 + NOISE) * (1 + NOISE)       # max(open, včerajšie zavretie) × (1 + σ)
LB = BASE * (1 - NOISE)                     # min(open, včerajšie zavretie) × (1 − σ)


def test_pasmo_sumu_z_predoslych_dni_a_hranice_podla_medzery():
    e = engine()
    warm(e)
    outs = run_day(e, {}, until=(10, 0))
    assert abs(e.sigma(30) - NOISE) < 1e-12
    assert len(e.hist[30]) == 14                       # z 15 dní sa drží 14
    ub, lb = e.bounds(30)
    assert abs(ub - UB) < 1e-6 and abs(lb - LB) < 1e-6
    assert not any(entries(o) for o in outs.values())   # cena v pásme


def test_vstup_len_na_kontrole_o_celej_a_o_pol():
    e = engine()
    warm(e)
    hi = UB + 20
    outs = run_day(e, {(9, 45): hi, (9, 50): hi, (9, 55): hi, (10, 0): hi}, until=(10, 0))
    assert not entries(outs[(9, 45)]) and not entries(outs[(9, 55)])   # nad hranicou, ale nie je kontrola
    oi = entries(outs[(10, 0)])[0]
    assert oi.direction is Direction.LONG and oi.order_type is OrderType.MARKET
    assert abs(oi.plan.stop_loss - MNQ.round_price(hi * 0.99)) < 1e-9     # poistka 1 %
    assert oi.plan.take_profit > hi * 1.5                                   # bez cieľa
    assert oi.plan.qty == 1.0


def test_short_pod_dolnou_hranicou_a_len_long():
    e = engine()
    warm(e)
    assert entries(run_day(e, {(10, 0): LB - 20}, until=(10, 0))[(10, 0)])[0].direction is Direction.SHORT
    e = engine(tradeDirection=TradeDirection.LONG_ONLY)
    warm(e)
    assert not entries(run_day(e, {(10, 0): LB - 20}, until=(10, 0))[(10, 0)])


def test_vystup_pod_vwap_len_na_kontrole():
    e = engine()
    warm(e)
    hi, low = UB + 40, UB - 30                 # 10:15 a 10:30 pod hranicou aj pod VWAP
    closes = {(10, 0): hi, (10, 5): hi, (10, 10): hi, (10, 15): low, (10, 20): low, (10, 25): low, (10, 30): low}
    ctx = lambda key: FLAT if key <= (10, 0) else LONG  # noqa: E731 — po vstupe je pozícia long
    outs = run_day(e, closes, ctx=ctx, until=(10, 30))
    assert entries(outs[(10, 0)])
    assert not closes_(outs[(10, 15)])                       # medzi kontrolami nič
    assert closes_(outs[(10, 30)])[0].reason == "zavretie pod hranicou / VWAP"


def test_drzi_nad_vwap_a_koniec_seansy_16_00():
    e = engine()
    warm(e)
    hi = UB + 40
    closes = {(h, m): hi for h in range(10, 16) for m in range(0, 60, 5)}
    closes[(16, 0)] = hi
    ctx = lambda key: FLAT if key <= (10, 0) else LONG  # noqa: E731
    outs = run_day(e, closes, ctx=ctx)
    assert not any(closes_(o) for k, o in outs.items() if k < (16, 0))
    assert closes_(outs[(16, 0)])[0].reason == "koniec seansy 16:00"


def test_short_vystup_nad_vwap_a_pozicia_z_predosleho_dna():
    e = engine()
    warm(e)
    closes = {(10, 0): LB - 40, (10, 30): LB + 30}
    ctx = lambda key: FLAT if key <= (10, 0) else SHORT  # noqa: E731
    outs = run_day(e, closes, ctx=ctx, until=(10, 30))
    assert closes_(outs[(10, 30)])[0].reason == "zavretie nad hranicou / VWAP"
    # pozícia, ktorá ostala otvorená cez noc (skrátená seansa), sa zavrie na prvom bare ďalšieho dňa
    nxt = TEST_DAY + timedelta(days=1)
    out = e.on_bar(bar(ts(nxt, 9, 30), BASE), None, LONG)
    assert closes_(out)[0].reason == "pozícia z predošlého dňa"


def test_max_vstupov_za_den_a_posledny_vstup():
    e = engine(maxTradesPerDay=1)
    warm(e)
    closes = {(10, 0): UB + 40, (10, 30): UB - 30, (11, 0): UB + 40}
    ctx = lambda key: LONG if (10, 0) < key <= (10, 30) else FLAT  # noqa: E731
    outs = run_day(e, closes, ctx=ctx, until=(11, 0))
    assert entries(outs[(10, 0)]) and not entries(outs[(11, 0)])     # druhý vstup už nie
    e = engine(lastEntryMin=30)
    warm(e)
    outs = run_day(e, {(10, 30): UB + 40}, until=(10, 30))
    assert not entries(outs[(10, 30)])                                # 10:30 je po poslednom vstupe 10:00
