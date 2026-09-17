"""Trailing vo Freqtrade z plánu obchodu — audit A6.

Gap, ORB, Range a SD zóny vkladajú trailing do `TradePlan.trailing`, ale Freqtrade vetva
ho nečítala: `SignalRow` ho nenesol a adaptéry zdedili `_trailing_stop`, ktorý vracal
pevný stop. Zapnutý `enableTrailing` tak vo Freqtrade nerobil nič, v MultiCharts áno.

Testy idú cez celý reťazec, nie len cez vznik `TrailingPlan`:
engine (`GapEngine._plan`) → `EngineRunner.process` → `SignalRow.trailing` →
`custom_stoploss` volaný skutočným `IStrategy.should_exit` Freqtradu po 1m sviečkach →
cena výstupu podľa pravidla backtestu (`Backtesting._get_close_rate_for_stoploss`).
Na konci je ten istý scenár cez emulátor MultiCharts.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("freqtrade")

from freqtrade.enums import ExitType, RunMode
from freqtrade.persistence import LocalTrade

from tradebot.adapters.freqtrade.runner import EngineRunner
from tradebot.core import Bar, load_profile
from tradebot.core.engine import EngineOutput
from tradebot.core.orders import OrderAction, OrderIntent
from tradebot.core.types import Direction, OrderType
from tradebot.strategies import get_spec

PAIR = "NAS100/USD"
MIN = 60_000
TF = 5
T0 = 1_767_628_800_000  # 2026-01-05 16:00 UTC (pondelok)

#: 1m sviečky (minúta od T0, o, h, l, c). Bar 0 = signál, bar 1 = vyplnenie na 100,
#: bar 2 = rast na 110 (trailing 1R = 5 sa aktivuje, odstup 0,5R = 2,5 → stop 107,5),
#: bar 3 = pokles, ktorý posunutý stop trafí; bar 4-5 = návrat pod pôvodný SL 95.
MINUTES = (
    [(m, 100, 100, 100, 100) for m in range(0, 10)]
    + [(10, 100, 102, 100, 102), (11, 102, 104, 102, 104), (12, 104, 106, 104, 106),
       (13, 106, 108, 106, 108), (14, 108, 110, 108, 110)]
    + [(15, 110, 110, 109, 109), (16, 109, 109, 107, 107), (17, 107, 107, 105, 105),
       (18, 105, 105, 103, 103), (19, 103, 103, 101, 101)]
    + [(m, 101 - (m - 20), 101 - (m - 20), 100 - (m - 20), 100 - (m - 20)) for m in range(20, 30)]
)


def _gap_cfg(trailing: bool):
    from tradebot.strategies.gap.config import SlMode, TpMode

    cfg, inst = load_profile(get_spec("gap").default_profile, strategy="gap")
    cfg.slMode = SlMode.GAP_MULT
    cfg.slGapMult = 1.0
    cfg.tpMode = TpMode.RR
    cfg.rrRatio = 6.0
    cfg.enableTrailing = trailing
    cfg.trailActivationR = 1.0
    cfg.trailOffsetR = 0.5
    return cfg, inst


def _gap_plan(cfg, inst):
    """Plán tak, ako ho postaví `GapEngine` — medzera 5 bodov dole → long, SL 1× medzera."""
    from tradebot.strategies.gap.engine import GapEngine

    engine = GapEngine(cfg, inst, TF)
    engine.day.direction = Direction.LONG
    engine.day.gap = -5.0
    plan = engine._plan(100.0, atr=5.0)
    assert plan is not None and plan.stop_loss == 95.0 and plan.take_profit == 130.0
    assert (plan.trailing is not None) is bool(cfg.enableTrailing)
    return plan


class _ScriptedEngine:
    """Engine, ktorý na bare `signal_ms` vydá vstup s daným plánom a inak nič."""

    def __init__(self, plan, signal_ms: int, inst) -> None:
        self.plan, self.signal_ms, self.inst = plan, signal_ms, inst
        self.chart_tf_minutes = TF
        self.required_history = 1

    def on_bar(self, bar, htf=None, ctx=None):
        out = EngineOutput()
        if bar.time == self.signal_ms:
            out.orders.append(OrderIntent(OrderAction.ENTRY, "LONG_1", 1, direction=Direction.LONG,
                                          plan=self.plan, order_type=OrderType.LIMIT))
        return out

    def final_drawings(self, bar):
        return []


def _chart_bars() -> list[Bar]:
    from tradebot.adapters.multicharts.emulator import bars_from_frame

    return bars_from_frame(_m1_frame(), TF)


def _m1_frame():
    return pd.DataFrame({
        "date": [pd.Timestamp(T0 + m * MIN, unit="ms", tz="UTC") for m, *_ in MINUTES],
        "open": [float(r[1]) for r in MINUTES], "high": [float(r[2]) for r in MINUTES],
        "low": [float(r[3]) for r in MINUTES], "close": [float(r[4]) for r in MINUTES],
        "volume": [1.0] * len(MINUTES),
    })


def _strategy(key: str, cfg, inst, plan):
    """Skutočná Freqtrade trieda stratégie so skriptovaným engine v runneri."""
    spec = get_spec(key)
    module = __import__(f"tradebot.strategies.{key}.freqtrade", fromlist=["x"])
    cls = next(v for v in vars(module).values()
               if isinstance(v, type) and getattr(v, "STRATEGY_KEY", None) == key)
    config = {"timeframe": f"{TF}m", "exchange": {"pair_whitelist": [], "name": "binance"},
              "runmode": RunMode.BACKTEST, "stake_currency": "USD", "dry_run": True,
              "trading_mode": "futures", "margin_mode": "isolated"}
    strategy = cls(config)
    strategy.minimal_roi = {0: 100.0}  # resolver Freqtradu kľúče prevádza na int; tu resolver nie je
    strategy.tb_cfg, strategy.tb_inst = cfg, inst
    runner = EngineRunner(cfg, inst, TF, spec=spec)
    runner.engine = _ScriptedEngine(plan, T0, inst)
    for b in _chart_bars():
        runner.process(b, None)
    strategy._runners = {PAIR: runner}
    strategy._runner_fp = strategy._config_fingerprint()
    # `_detail_close` číta close 1m sviečky; `dp` stačí nenulový, dáta sú už v dicte
    strategy.dp = object()
    strategy._closes = {PAIR: {T0 + m * MIN: float(c) for m, _o, _h, _l, c in MINUTES}}
    return strategy


def _freqtrade_exit(strategy) -> tuple[float, str] | None:
    """Mini backtest jednej pozície: `should_exit` po 1m sviečkach ako `Backtesting`."""
    fill_min = 10  # prvá minúta baru po signáli, limitka 100 sa vyplní na open
    trade = LocalTrade(
        pair=PAIR, open_rate=100.0, open_date=datetime.fromtimestamp((T0 + fill_min * MIN) / 1000, tz=timezone.utc),
        amount=1.0, fee_open=0.0, fee_close=0.0, is_short=False, leverage=1.0, stake_amount=100.0,
        exchange="binance", enter_tag=f"{strategy.ENTRY_TAG_PREFIX}{T0}",
    )
    trade.orders = []
    trade.adjust_stop_loss(trade.open_rate, strategy.stoploss, initial=True)
    for m, o, h, low, c in MINUTES:
        if m <= fill_min:
            continue
        when = datetime.fromtimestamp((T0 + m * MIN) / 1000, tz=timezone.utc)
        exits = strategy.should_exit(trade, float(o), when, enter=False, exit_=False,
                                     low=float(low), high=float(h))
        for ex in exits:
            if ex.exit_type in (ExitType.STOP_LOSS, ExitType.TRAILING_STOP_LOSS):
                # Backtesting._get_close_rate_for_stoploss: stop nad high → open, inak stop
                price = float(o) if trade.stop_loss > h else trade.stop_loss
                return price, ex.exit_type.value
    return None


@pytest.mark.parametrize("trailing, expected", [(True, 107.5), (False, 95.0)])
def test_gap_trailing_meni_vystup_vo_freqtrade(trailing, expected):
    cfg, inst = _gap_cfg(trailing)
    plan = _gap_plan(cfg, inst)
    strategy = _strategy("gap", cfg, inst, plan)

    row = strategy._runners[PAIR].signal_at(T0)
    assert (row.trailing is not None) is trailing  # plán prešiel do SignalRow

    price, _reason = _freqtrade_exit(strategy)
    assert price == pytest.approx(expected)


@pytest.mark.parametrize("key", ["gap", "orb", "range", "sdzone", "ibs", "divergence"])
def test_vsetky_freqtrade_triedy_beru_trailing_z_planu(key):
    """Žiadna stratégia nesmie trailing prepísať pevným stopom — ani nový adaptér."""
    cfg, inst = _gap_cfg(True)
    plan = _gap_plan(cfg, inst)
    own_cfg, own_inst = load_profile(get_spec(key).default_profile, strategy=key)
    strategy = _strategy(key, own_cfg, inst, plan)
    price, _ = _freqtrade_exit(strategy)
    assert price == pytest.approx(107.5)


def test_ai_posunuty_stop_posunie_trailing_viazany_na_riziko():
    """AI vrstva vzdiali stop 2× → aktivácia 1R aj odstup 0,5R sa počítajú z nového rizika."""
    cfg, inst = _gap_cfg(True)
    plan = _gap_plan(cfg, inst)
    scaled = plan.trailing.scaled(2.0)
    assert scaled.activation_price_distance == pytest.approx(10.0)
    assert scaled.offset_price_distance == pytest.approx(5.0)
    assert plan.trailing.scaled(1.0) is plan.trailing

    from tradebot.strategies.divergence.trailing import TwoStageTrailing

    pct = TwoStageTrailing(activation_price_distance=1.0, offset_price_distance=0.5,
                           activation_ticks=4.0, offset_ticks=2.0)
    assert pct.scaled(2.0) is pct  # percentá ceny od stopu nezávisia


def test_ten_isty_scenar_v_emulatore_multicharts():
    """MultiCharts runner prepočíta stop z toho istého plánu na close baru (107,5 po bare 2)
    a emulátor ho trafí v 2. minúte baru 3 — rovnaká cena ako Freqtrade po minútach."""
    from tradebot.adapters.multicharts.emulator import emulate

    for trailing, expected, reason in ((True, 107.5, "trailing_stop"), (False, 95.0, "stop_loss")):
        cfg, inst = _gap_cfg(trailing)
        plan = _gap_plan(cfg, inst)
        spec = replace(get_spec("gap"), engine_factory=lambda c, i, tf, p=plan: _ScriptedEngine(p, T0, i),
                       htf_feeder=None)
        result, _ = emulate(cfg, inst, _m1_frame(), TF, spec=spec)
        assert len(result.trades) == 1
        t = result.trades[0]
        assert t.entry == 100.0
        assert t.exit == pytest.approx(expected) and t.reason == reason


# --------------------------------------------------------------------------- #
# Interný fill model runnera: denná výhra = zisk > 0 po poplatku (aj trailing)
# --------------------------------------------------------------------------- #


def _runner_with(plan, fee: float = 0.0) -> EngineRunner:
    cfg, inst = _gap_cfg(plan.trailing is not None)
    runner = EngineRunner(cfg, inst, TF, spec=get_spec("gap"), fee=fee)
    runner.engine = _ScriptedEngine(plan, T0, inst)
    return runner


def test_ziskovy_trailing_stop_je_denna_vyhra():
    """Pine `dailyWinsCount` počíta `strategy.closedtrades.profit > 0` — trailing stop
    nad vstupom je výhra, hoci TP nezasiahol (rovnako ako `MCRunner._daily_win_limit`)."""
    cfg, inst = _gap_cfg(True)
    plan = _gap_plan(cfg, inst)
    runner = _runner_with(plan)
    for b in _chart_bars():
        runner.process(b, None)
    assert runner._position == 0.0
    assert runner.wins_today(T0) == 1


def test_bez_trailingu_ten_isty_priebeh_nie_je_vyhra():
    cfg, inst = _gap_cfg(False)
    plan = _gap_plan(cfg, inst)
    runner = _runner_with(plan)
    for b in _chart_bars():
        runner.process(b, None)
    assert runner._position == 0.0  # pevný SL 95 zasiahnutý v bare 5 — strata
    assert runner.wins_today(T0) == 0


def test_vyhra_je_po_poplatku():
    """Trailing stop o 7,5 bodu nad vstupom, ale poplatok 5 % na stranu zisk zje."""
    cfg, inst = _gap_cfg(True)
    plan = _gap_plan(cfg, inst)
    runner = _runner_with(plan, fee=0.05)
    for b in _chart_bars():
        runner.process(b, None)
    assert runner._position == 0.0
    assert runner.wins_today(T0) == 0
