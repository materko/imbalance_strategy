"""Silver Bullet 1.0: engine na syntetických 5m baroch MNQ.

Testuje sa mechanika, nie edge: likvidita pred oknom → sweep v okne 10–11 NY → FVG → limitka na okraji FVG,
SL za extrém sweepu, cieľ na protiľahlej likvidite.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, OrderType, SizeSpec
from tradebot.strategies.silverbullet import EntryType, SilverBulletConfig, SilverBulletEngine, TpMode

NY = ZoneInfo("America/New_York")
MNQ = INSTRUMENTS["mnq_databento"]
OKNO = MarketContext(in_trade_window=True)
T8 = int(datetime(2025, 9, 2, 8, 0, tzinfo=NY).timestamp() * 1000)
FLAT = (105.0, 106.0, 104.0, 105.0)


def day_bars(sweep_at: str = "10:00", swing_hi: bool = False):
    """8:00–10:00 plocho okolo 105, vrchol 120 o 8:30, dno 100 o 9:00; sweep dna, prudký pohyb hore s FVG."""
    bars = []
    for i in range(24):                                          # 8:00 … 9:55 (otvorenie baru)
        if i == 6:
            bars.append((105.0, 120.0, 104.0, 105.0))           # skorší vrchol 120 (8:30)
        elif i == 12:
            bars.append((105.0, 106.0, 100.0, 105.0))           # skoršie dno 100 (9:00)
        elif i == 21 and swing_hi:
            bars.append((105.0, 107.0, 104.0, 105.0))           # menší vrchol 107 (9:45) — úroveň MSS
        else:
            bars.append(FLAT)
    move = [(104.0, 104.5, 99.0, 103.0),                         # sweep dna 100 → extrém 99
            (103.0, 108.0, 102.5, 107.5),
            (107.5, 110.0, 105.0, 109.5)]                        # FVG: low 105 nad high 104,5 sweepovej sviečky
    if sweep_at == "09:30":
        bars = bars[:18] + move + [FLAT] * 3                     # pohyb ešte pred oknom
    else:
        bars += move
    return bars


def cfg(**kw) -> SilverBulletConfig:
    base = dict(liqPivotLen=1, structPivotLen=1, atrLen=2, fvgMinAtr=SizeSpec(0.0, "atr"),
                slBufferAtr=SizeSpec(0.0, "atr"))
    base.update(kw)
    return SilverBulletConfig(**base)


def run(c: SilverBulletConfig, bars):
    e = SilverBulletEngine(c, MNQ, 5)
    return e, [e.on_bar(Bar(T8 + i * 300_000, *ohlc, 100.0), None, OKNO) for i, ohlc in enumerate(bars)]


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def test_sweep_v_okne_fvg_a_limitka_na_okraji():
    e, outs = run(cfg(), day_bars())
    assert not any(entries(o) for o in outs[:-1])                 # pred FVG nič
    (en,) = entries(outs[-1])
    assert en.order_type is OrderType.LIMIT
    p = en.plan
    assert p.direction is Direction.LONG and p.entry == 105.0 and p.stop_loss == 99.0
    assert p.take_profit == 120.0                                 # protiľahlá likvidita — skorší vrchol
    kinds = {d.kind.value for o in outs for d in o.drawings if hasattr(d, "kind")}
    assert {"sb_window", "sb_sweep", "sb_fvg"} <= kinds


def test_sweep_pred_oknom_sa_neobchoduje():
    _, outs = run(cfg(), day_bars("09:30"))
    assert not any(entries(o) for o in outs)


def test_ciel_rr_a_market_na_zavreti():
    _, outs = run(cfg(tpMode=TpMode.RR, rrRatio=2.0), day_bars())
    assert entries(outs[-1])[0].plan.take_profit == 117.0          # 105 + 2 × 6
    _, outs = run(cfg(entryType=EntryType.MARKET, minRR=0.5), day_bars())   # cieľ 120 je od 109,5 menej ako 1 R
    (en,) = entries(outs[-1])
    assert en.order_type is OrderType.MARKET and en.plan.entry == 109.5 and en.plan.stop_loss == 99.0


def test_len_long_a_mss():
    _, outs = run(cfg(tradeDirection="Short only"), day_bars())
    assert not any(entries(o) for o in outs)
    _, outs = run(cfg(requireMss=True), day_bars())                # bez menšieho vrcholu: MSS = vrchol 120 → nič
    assert not any(entries(o) for o in outs)
    _, outs = run(cfg(requireMss=True), day_bars(swing_hi=True))   # vrchol 107 pred sweepom → zavretie 107,5 = MSS
    assert entries(outs[-1])
