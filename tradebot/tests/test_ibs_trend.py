"""Smer obchodov podľa indikátorov (`tradeDirection = Indicator`) — Supertrend a ADX/DMI."""

from __future__ import annotations

import math
import random

import pytest

from tradebot.core.warmup import Warmup
from tradebot.core import MNQ, Bar, BarHistory, Direction, IBSConfig, MarketContext, StateMachine, ZoneBook, ZoneState
from tradebot.strategies.ibs import IBSEngine
from tradebot.strategies.ibs.config import INDICATOR_RULES, IndicatorAction, PriceSource, TradeDirection
from tradebot.strategies.ibs.ta.trend import DMI, BoundaryAggregator, DirectionGate, Supertrend, price_of

T0 = 1_756_684_800_000  # 2025-09-01 00:00 UTC, násobok 15 minút aj dňa
MIN3 = 180_000


def bars(n: int, *, step: int = MIN3, seed: int = 7) -> list[Bar]:
    rnd = random.Random(seed)
    out, price = [], 100.0
    for i in range(n):
        o = price
        c = o + rnd.gauss(0, 1.5)
        h = max(o, c) + abs(rnd.gauss(0, 0.8))
        lo = min(o, c) - abs(rnd.gauss(0, 0.8))
        out.append(Bar(T0 + i * step, o, h, lo, c, 10.0))
        price = c
    return out


def pine_supertrend(series: list[Bar], periods: int, mult: float, src: PriceSource, change_atr: bool):
    """Doslovný prepis Pine v4 skriptu s `na`/`nz` sémantikou — nezávislý od implementácie."""
    na = math.nan
    n = len(series)
    tr_true = [s.high - s.low if i == 0 else max(s.high - s.low, abs(s.high - series[i - 1].close),
                                                  abs(s.low - series[i - 1].close)) for i, s in enumerate(series)]
    tr = [na] + tr_true[1:]
    atr: list[float] = []
    rma = na
    for i in range(n):
        if change_atr:
            if math.isnan(rma):
                rma = sum(tr_true[i - periods + 1:i + 1]) / periods if i >= periods - 1 else na
            else:
                rma = (tr_true[i] - rma) / periods + rma
            atr.append(rma)
        else:
            win = tr[i - periods + 1:i + 1] if i >= periods - 1 else [na]
            atr.append(na if any(math.isnan(x) for x in win) else sum(win) / periods)
    up, dn, trend = [na] * n, [na] * n, [1] * n
    for i in range(n):
        s = price_of(series[i], src)
        u = s - mult * atr[i]
        u1 = up[i - 1] if i and not math.isnan(up[i - 1]) else u
        u = max(u, u1) if i and series[i - 1].close > u1 else u
        d = s + mult * atr[i]
        d1 = dn[i - 1] if i and not math.isnan(dn[i - 1]) else d
        d = min(d, d1) if i and series[i - 1].close < d1 else d
        t = trend[i - 1] if i else 1
        close = series[i].close
        t = 1 if (t == -1 and close > d1) else (-1 if (t == 1 and close < u1) else t)
        up[i], dn[i], trend[i] = u, d, t
    return up, dn, trend


@pytest.mark.parametrize("change_atr", [True, False])
@pytest.mark.parametrize("src", [PriceSource.HL2, PriceSource.CLOSE, PriceSource.OHLC4])
def test_supertrend_matches_pine_script(change_atr, src):
    series = bars(600, seed=11)
    up, dn, trend = pine_supertrend(series, 10, 3.0, src, change_atr)
    st = Supertrend(10, 3.0, src, change_atr)
    flips = 0
    for i, b in enumerate(series):
        st.push(b)
        if math.isnan(up[i]):
            assert not st.ready
            continue
        assert st.ready
        assert st.trend == trend[i], i
        assert st.up == pytest.approx(up[i]) and st.dn == pytest.approx(dn[i])
        flips += st.flipped
    assert flips > 3  # náhodná prechádzka musí trend niekoľkokrát otočiť


def pine_dmi(series: list[Bar], di_len: int, smoothing: int):
    """Doslovný prepis TradingView „Directional Movement Index" s `na` sémantikou."""
    na = math.nan

    def rma(src: list[float], n: int) -> list[float]:
        out, prev = [], na
        for i, v in enumerate(src):
            if math.isnan(prev):
                win = src[i - n + 1:i + 1] if i >= n - 1 else [na]
                prev = na if any(math.isnan(x) for x in win) else sum(win) / n
            else:
                prev = (v - prev) / n + prev
            out.append(prev)
        return out

    plus_dm, minus_dm, tr = [na], [na], [na]
    for i in range(1, len(series)):
        b, a = series[i], series[i - 1]
        up, down = b.high - a.high, a.low - b.low
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        tr.append(max(b.high - b.low, abs(b.high - a.close), abs(b.low - a.close)))
    trur, rp, rm = rma(tr, di_len), rma(plus_dm, di_len), rma(minus_dm, di_len)
    plus = [100 * p / t if not math.isnan(t) else na for p, t in zip(rp, trur)]
    minus = [100 * m / t if not math.isnan(t) else na for m, t in zip(rm, trur)]
    dx = [abs(p - m) / ((p + m) or 1) for p, m in zip(plus, minus)]
    adx = [100 * v for v in rma(dx, smoothing)]
    return plus, minus, adx


@pytest.mark.parametrize("di_len, smoothing", [(14, 14), (7, 20)])
def test_dmi_matches_pine_script(di_len, smoothing):
    series = bars(500, seed=5)
    plus, minus, adx = pine_dmi(series, di_len, smoothing)
    dmi = DMI(di_len, smoothing)
    states = set()
    for i, b in enumerate(series):
        dmi.push(b)
        if math.isnan(adx[i]):
            assert not dmi.ready, i
            continue
        assert dmi.adx == pytest.approx(adx[i]), i
        assert dmi.plus == pytest.approx(plus[i]) and dmi.minus == pytest.approx(minus[i])
        states.add(dmi.state(20.0))
    assert {"up", "down"} <= states


def test_aggregator_closes_on_the_last_chart_bar_of_the_period():
    agg = BoundaryAggregator(15, 3)
    closed = [agg.push(b) for b in bars(10)]
    assert [len(c) for c in closed] == [0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    first = closed[4][0]
    src = bars(10)[:5]
    assert first.time == T0
    assert (first.open, first.close) == (src[0].open, src[-1].close)
    assert first.high == max(b.high for b in src) and first.low == min(b.low for b in src)


def test_aggregator_closes_period_with_missing_last_bar_on_next_period():
    series = bars(10)
    del series[4]  # chýba bar 00:12, perióda 00:00 sa uzavrie až barom 00:15
    agg = BoundaryAggregator(15, 3)
    closed = [agg.push(b) for b in series]
    assert [len(c) for c in closed] == [0, 0, 0, 0, 1, 0, 0, 0, 1]
    assert closed[4][0].time == T0 and closed[4][0].close == series[3].close
    assert closed[8][0].time == T0 + 15 * 60_000


def _gate_cfg(**kw) -> IBSConfig:
    return IBSConfig(**{"tradeDirection": "Indicator", "stTimeframe": "15", "stAtrPeriod": 3, **kw})


RISING = [Bar(T0 + i * MIN3, 100 + i, 101 + i, 99 + i, 100.8 + i, 1.0) for i in range(400)]


def test_gate_is_off_unless_trade_direction_is_indicator():
    gate = DirectionGate(IBSConfig(stTimeframe="5"), chart_tf_minutes=3)  # 5 nie je násobok 3, no nevadí
    assert not gate.enabled and gate.add_warmup(Warmup(3)).needs == []
    assert gate.allowed(Direction.SHORT) and gate.on_bar(bars(1)[0]) == []


@pytest.mark.parametrize("field", ["stTimeframe", "adxTimeframe"])
def test_gate_requires_timeframe_multiple_of_chart(field):
    cfg = IBSConfig(**{"tradeDirection": "Indicator", "indAdx": True, field: "5"})
    with pytest.raises(ValueError, match="násobkom"):
        DirectionGate(cfg, chart_tf_minutes=3)


def test_indicator_mode_needs_at_least_one_indicator():
    with pytest.raises(Exception, match="žiadny indikátor"):
        IBSConfig(tradeDirection="Indicator", indSupertrend=False, indAdx=False)


def test_supertrend_only_blocks_until_ready_then_follows_rules():
    gate = DirectionGate(_gate_cfg(), chart_tf_minutes=3)
    assert gate.block_reason(Direction.LONG) == "ST15 SA ROZBIEHA: CAKA"
    for b in RISING[:60]:
        gate.on_bar(b)
    assert gate.states == ("up", None)
    assert gate.allowed(Direction.LONG) and not gate.allowed(Direction.SHORT)
    assert gate.block_reason(Direction.SHORT) == "ST15 HORE: LEN LONG"
    falling = [Bar(T0 + (60 + i) * MIN3, 160 - 3 * i, 161 - 3 * i, 157 - 3 * i, 157.2 - 3 * i, 1.0) for i in range(30)]
    for b in falling:
        gate.on_bar(b)
    assert gate.allowed(Direction.SHORT) and not gate.allowed(Direction.LONG)


def test_rule_values_decide_for_supertrend_state():
    gate = DirectionGate(_gate_cfg(ruleStUp="No trade"), chart_tf_minutes=3)
    for b in RISING[:60]:
        gate.on_bar(b)
    assert not gate.allowed(Direction.LONG) and not gate.allowed(Direction.SHORT)
    assert gate.block_reason(Direction.LONG) == "ST15 HORE: NEOBCHODOVAT"
    gate = DirectionGate(_gate_cfg(ruleStUp="Both"), chart_tf_minutes=3)
    for b in RISING[:60]:
        gate.on_bar(b)
    assert gate.allowed(Direction.LONG) and gate.allowed(Direction.SHORT)


def test_adx_only_and_combination_pick_their_own_rules():
    adx_only = DirectionGate(_gate_cfg(indSupertrend=False, indAdx=True, adxTimeframe="15",
                                       adxDiLength=5, adxSmoothing=5, ruleAdxUp="Short only"), 3)
    both = DirectionGate(_gate_cfg(indAdx=True, adxTimeframe="15", adxDiLength=5, adxSmoothing=5,
                                   ruleStUpAdxUp="Both"), 3)
    for b in RISING:
        adx_only.on_bar(b)
        both.on_bar(b)
    assert adx_only.states == (None, "up") and adx_only.action() is IndicatorAction.SHORT_ONLY
    assert adx_only.allowed(Direction.SHORT) and not adx_only.allowed(Direction.LONG)
    assert both.states == ("up", "up") and both.action() is IndicatorAction.BOTH
    assert both.describe() == "ST15 HORE + ADX15 HORE"


def test_adx_below_threshold_is_sideways():
    gate = DirectionGate(_gate_cfg(indSupertrend=False, indAdx=True, adxTimeframe="15",
                                   adxDiLength=5, adxSmoothing=5, adxThreshold=99), 3)
    for b in bars(400):  # náhodná prechádzka — ADX na nej 99 nedosiahne
        gate.on_bar(b)
    assert gate.states == (None, "side")
    assert gate.block_reason(Direction.LONG) == "ADX15 STRANA: NEOBCHODOVAT"  # default ruleAdxSide


def test_every_state_combination_has_a_rule_field():
    fields = set(IBSConfig().to_dict())
    assert set(INDICATOR_RULES.values()) <= fields
    assert len(INDICATOR_RULES) == 2 + 3 + 6


def test_statemachine_skips_zone_against_indicator():
    cfg = IBSConfig(enableImbEntry=True, tradeDirection="Indicator")
    book = ZoneBook(cfg, MNQ, chart_tf_minutes=3)
    sm = StateMachine(cfg, MNQ, book)

    class AgainstLongs:
        def block_reason(self, direction):
            return "SUPERTREND 60 PROTI" if direction is Direction.LONG else None

    sm.direction_gate = AgainstLongs()
    from tradebot.tests.test_statemachine import make_zone

    z = make_zone(book, direction=Direction.LONG)
    z.state = ZoneState.READY
    z.imb_open, z.imb_body_top, z.imb_body_bot = 95.0, 96.0, 94.0
    h = BarHistory()
    for i in range(3):
        h.append(Bar(T0 + i * MIN3, 95, 97, 93, 95, 100.0))
    z.state_bar_index = h.bar_index
    sm.on_bar(h.current, h, MarketContext(in_trade_window=True))
    assert z.state == ZoneState.INVALID
    assert any("SUPERTREND 60 PROTI" in e.reason for e in sm.events)


def test_engine_draws_supertrend_and_seeds_instead_of_longer_history():
    plain = IBSEngine(IBSConfig(), MNQ, 3)
    cfg = _gate_cfg(stAtrPeriod=10)
    engine = IBSEngine(cfg, MNQ, 3)
    # Supertrend na vlastnom TF predhistóriu grafu nezväčšuje — má vlastnú (seed)
    assert engine.required_history == plain.required_history
    assert [(n.tf_minutes, n.bars) for n in engine.warmup.seeds] == [(15, engine.direction_gate.st.warmup_bars)]
    kinds: list[str] = []
    for b in bars(400):
        kinds.extend(d.kind.value for d in engine.on_bar(b).drawings if d.kind.value.startswith("st_"))
    assert "st_line" in kinds and "st_fill" in kinds and "st_signal" in kinds

    quiet = IBSEngine(_gate_cfg(stAtrPeriod=10, stShowSignals=False, stHighlighting=False), MNQ, 3)
    kinds = [d.kind.value for b in bars(400) for d in quiet.on_bar(b).drawings if d.kind.value.startswith("st_")]
    assert set(kinds) == {"st_line"}

    adx = IBSEngine(_gate_cfg(indAdx=True, adxTimeframe="30"), MNQ, 3)
    kinds = {d.kind.value for b in bars(400) for d in adx.on_bar(b).drawings}
    assert "adx_state" in kinds


def test_indicator_direction_round_trips_through_profile_dict():
    cfg = IBSConfig(tradeDirection="Indicator", stTimeframe="240", stSource="ohlc4", stMultiplier=2.5)
    again = IBSConfig.from_dict(cfg.to_dict())
    assert again.tradeDirection is TradeDirection.INDICATOR
    assert again.stSource is PriceSource.OHLC4 and again.stTimeframe == "240"
    assert TradeDirection.INDICATOR.allows(Direction.SHORT)  # rozhoduje až brána


def test_timeframe_given_as_number_is_accepted():
    """`cli run --set stTimeframe=60` pošle číslo, formulár reťazec."""
    assert IBSConfig(stTimeframe=60).stTimeframe == "60"


def test_invalid_supertrend_timeframe_is_rejected():
    with pytest.raises(Exception, match="stTimeframe"):
        IBSConfig(stTimeframe="7")
