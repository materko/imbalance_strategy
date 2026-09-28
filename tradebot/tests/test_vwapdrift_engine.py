"""Drift VWAP: engine na syntetických baroch.

Testuje sa mechanika, nie edge: či drift určí smer, či sa pullback počíta až po odchode
od VWAP, čo sa stane, keď pullback VWAP prerazí, že sa obchoduje len prvý, kam ide stop
a čo sa stane na konci seansy.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import BTCUSDT_BINANCE, Bar, MarketContext, OrderAction
from tradebot.core.types import Direction, SizeSpec
from tradebot.strategies.vwapdrift import (VwapAnchor, VwapDriftConfig, VwapDriftEngine,
                                           VwapPeriod)

NY = ZoneInfo("America/New_York")
#: utorok 2025-09-02, 9:30 New York
OPEN_MS = int(datetime(2025, 9, 2, 9, 30, tzinfo=NY).timestamp() * 1000)
MIN = 60_000
STEP = 5 * MIN
OKNO = MarketContext(in_trade_window=True)


def bar(ts, c, rng=1.0, v=10.0, low=None, high=None) -> Bar:
    return Bar(time=ts, open=c, high=c + rng / 2 if high is None else high,
               low=c - rng / 2 if low is None else low, close=c, volume=v)


def engine(**kw) -> VwapDriftEngine:
    base = dict(vwapPeriod=VwapPeriod.CHART, entryDelayMinutes=0)
    base.update(kw)
    return VwapDriftEngine(VwapDriftConfig(**base), BTCUSDT_BINANCE, 5)


def warm(e: VwapDriftEngine, bars: int = 40) -> None:
    """Bary pred otvorením seansy — ATR ≈ 1, do VWAP sa nepočítajú."""
    for i in range(bars, 0, -1):
        e.on_bar(bar(OPEN_MS - i * STEP, 100.0))


def trend(e: VwapDriftEngine, closes, start_i: int = 0) -> int:
    """Bary seansy s danými close; vráti index ďalšieho baru."""
    outs = []
    for k, c in enumerate(closes):
        outs.append(e.on_bar(bar(OPEN_MS + (start_i + k) * STEP, c), ctx=OKNO))
    if e.cfg.entryMode.value != "limit":  # limitka sa kladie už počas odchodu
        assert not any(o.orders for o in outs), "počas odchodu od VWAP nemá vzniknúť vstup"
    return start_i + len(closes)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


UP = [100, 101, 102, 103, 104, 105, 106, 107]


# --------------------------------------------------------------------------- #


def test_defaulty_su_ako_vo_videu():
    cfg = VwapDriftConfig()
    assert cfg.vwapAnchor is VwapAnchor.NY_OPEN and cfg.vwapPeriod is VwapPeriod.M15
    assert cfg.start_minutes == 9 * 60 + 30 and cfg.firstPullbackOnly


def test_pullback_v_stupajucom_vwap_je_long_so_stopom_za_pullback():
    e = engine()
    warm(e)
    i = trend(e, UP)
    assert e.drift(e.history.atr) == 1 and e._state.long_armed
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    (intent,) = entries(out)
    plan = intent.plan
    assert plan.direction is Direction.LONG
    assert plan.stop_loss < vwap - 0.4                         # za extrém pullbacku + rezerva
    # TP aj SL sú zaokrúhlené na tick (0.1) — rozdiel najviac o dva ticky
    assert abs((plan.take_profit - plan.entry) - 2.0 * (plan.entry - plan.stop_loss)) <= 0.3


def test_bez_odchodu_od_vwap_sa_dotyk_nepocita():
    e = engine(awayAtr=SizeSpec(10.0, "atr"))
    warm(e)
    i = trend(e, UP)
    assert not e._state.long_armed
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4), ctx=OKNO)
    assert not entries(out)


def test_prerazeny_pullback_obchod_nema_a_druhy_sa_uz_nepocita():
    e = engine()
    warm(e)
    i = trend(e, UP)
    vwap = e.vwap.value
    # zavrie hlboko pod VWAP — pullback prerazil
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap - 3, low=vwap - 3.5, high=vwap + 0.2), ctx=OKNO)
    assert not entries(out) and e._state.long_done
    i = trend(e, [112, 114, 116, 118], i + 1)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4), ctx=OKNO)
    assert not entries(out), "firstPullbackOnly: druhý pullback dňa sa neobchoduje"


def test_bez_first_pullback_only_sa_po_novom_odchode_obchoduje_dalsi():
    e = engine(firstPullbackOnly=False)
    warm(e)
    i = trend(e, UP)
    vwap = e.vwap.value
    e.on_bar(bar(OPEN_MS + i * STEP, vwap - 3, low=vwap - 3.5, high=vwap + 0.2), ctx=OKNO)
    i = trend(e, [112, 114, 116, 118], i + 1)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4), ctx=OKNO)
    assert [o.plan.direction for o in entries(out)] == [Direction.LONG]


def test_klesajuci_vwap_je_short_a_long_only_ho_zahodi():
    for direction, expected in (("Both", [Direction.SHORT]), ("Long only", [])):
        e = engine(tradeDirection=direction)
        warm(e)
        i = trend(e, [100, 99, 98, 97, 96, 95, 94, 93])
        assert e.drift(e.history.atr) == -1
        vwap = e.vwap.value
        out = e.on_bar(bar(OPEN_MS + i * STEP, vwap - 0.6, high=vwap + 0.4, low=vwap - 0.8), ctx=OKNO)
        assert [o.plan.direction for o in entries(out)] == expected


def test_bez_driftu_sa_neobchoduje():
    e = engine(driftMinAtr=SizeSpec(5.0, "atr"))
    warm(e)
    i = trend(e, UP)
    assert e.drift(e.history.atr) == 0 and not e._state.long_armed
    vwap = e.vwap.value
    assert not entries(e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4), ctx=OKNO))


def test_koniec_seansy_zatvara_poziciu():
    e = engine()
    warm(e)
    end = int(datetime(2025, 9, 2, 15, 55, tzinfo=NY).timestamp() * 1000)
    out = e.on_bar(bar(end, 100), ctx=MarketContext(in_trade_window=True, position_size=1.0,
                                                    open_order_ids=("vd:1",)))
    assert out.close_session and [o.action for o in out.orders] == [OrderAction.CLOSE]


def test_vwap_sa_kresli_ako_ciara_farbena_driftom():
    e = engine()
    warm(e)
    outs = [e.on_bar(bar(OPEN_MS + k * STEP, c), ctx=OKNO) for k, c in enumerate(UP)]
    lines = [d for o in outs for d in o.drawings if d.kind.value == "vd_vwap"]
    assert len(lines) == len(UP) - 1          # prvý bod seansy je len začiatok čiary
    assert lines[-1].color == "#10b981"       # VWAP stúpa


# ---- druhy vstupu ----------------------------------------------------------- #

from tradebot.core.types import OrderType  # noqa: E402
from tradebot.strategies.vwapdrift import EntryMode, SlMode  # noqa: E402


def candle(ts, o, h, low, c, v=10.0) -> Bar:
    return Bar(time=ts, open=o, high=h, low=low, close=c, volume=v)


def armed_long(**kw):
    e = engine(**kw)
    warm(e)
    i = trend(e, UP)
    assert e._state.long_armed
    return e, i


def test_limit_lezi_na_vwap_a_obnovuje_sa_kym_nepride_dotyk():
    e, i = armed_long(entryMode=EntryMode.LIMIT)
    out = e.on_bar(bar(OPEN_MS + i * STEP, 110), ctx=OKNO)          # stále ďaleko nad VWAP
    lim = entries(out)[-1]
    assert lim.order_type is OrderType.LIMIT
    assert abs(lim.plan.entry - (e.vwap.value + 0.1 * e.history.atr)) <= 0.1
    out = e.on_bar(bar(OPEN_MS + (i + 1) * STEP, 111), ctx=OKNO)
    acts = [o.action for o in out.orders]
    assert acts == [OrderAction.CANCEL, OrderAction.ENTRY]          # nová cena VWAP
    # adaptér limitku vyplnil -> engine to vidí cez pozíciu, ráta obchod a ďalšiu nedáva
    out = e.on_bar(bar(OPEN_MS + (i + 2) * STEP, e.vwap.value + 0.2, low=e.vwap.value - 0.2),
                   ctx=MarketContext(in_trade_window=True, position_size=1.0))
    assert not entries(out) and e._state.trades == 1


def test_stop_nad_pullbackovou_sviecku_a_zrusi_sa_po_platnosti():
    e, i = armed_long(entryMode=EntryMode.STOP, stopValidBars=2)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.3, low=vwap - 0.4, high=vwap + 0.9), ctx=OKNO)
    (st,) = entries(out)
    assert st.order_type is OrderType.STOP and st.plan.entry > vwap + 0.9
    e.on_bar(bar(OPEN_MS + (i + 1) * STEP, vwap + 0.5), ctx=OKNO)
    e.on_bar(bar(OPEN_MS + (i + 2) * STEP, vwap + 0.5), ctx=OKNO)
    out = e.on_bar(bar(OPEN_MS + (i + 3) * STEP, vwap + 0.5), ctx=OKNO)
    assert [o.action for o in out.orders] == [OrderAction.CANCEL]


def test_reaction_vstup_na_close_prvej_byčej_sviecky_po_dotyku():
    e, i = armed_long(entryMode=EntryMode.REACTION)
    vwap = e.vwap.value
    t = OPEN_MS + i * STEP
    # dotyk medvedou sviečkou — ešte nie
    assert not entries(e.on_bar(candle(t, vwap + 1.0, vwap + 1.1, vwap - 0.3, vwap + 0.2), ctx=OKNO))
    # prvá býčia sviečka -> vstup na jej close, stop pod najnižší low od dotyku
    out = e.on_bar(candle(t + STEP, vwap + 0.2, vwap + 0.9, vwap - 0.5, vwap + 0.8), ctx=OKNO)
    (intent,) = entries(out)
    assert intent.order_type is OrderType.MARKET and intent.plan.direction is Direction.LONG
    assert intent.plan.entry == BTCUSDT_BINANCE.round_price(vwap + 0.8)
    assert intent.plan.stop_loss < vwap - 0.5


def test_reaction_po_prerazeni_vwap_sa_zrusi():
    e, i = armed_long(entryMode=EntryMode.REACTION)
    vwap = e.vwap.value
    t = OPEN_MS + i * STEP
    e.on_bar(candle(t, vwap + 1.0, vwap + 1.1, vwap - 0.3, vwap + 0.2), ctx=OKNO)
    e.on_bar(candle(t + STEP, vwap, vwap + 0.1, vwap - 3.0, vwap - 2.5), ctx=OKNO)   # zavrie pod VWAP
    assert not entries(e.on_bar(candle(t + 2 * STEP, vwap - 2.5, vwap, vwap - 2.6, vwap - 0.5), ctx=OKNO))


def test_pinbar_a_engulfing():
    e, i = armed_long(entryMode=EntryMode.PINBAR)
    vwap = e.vwap.value
    # pin bar: dlhý spodný knôt, malé telo hore
    out = e.on_bar(candle(OPEN_MS + i * STEP, vwap + 0.8, vwap + 1.0, vwap - 1.0, vwap + 0.9), ctx=OKNO)
    assert [o.plan.direction for o in entries(out)] == [Direction.LONG]

    e, i = armed_long(entryMode=EntryMode.ENGULFING)
    vwap = e.vwap.value
    t = OPEN_MS + i * STEP
    assert not entries(e.on_bar(candle(t, vwap + 0.6, vwap + 0.7, vwap - 0.2, vwap + 0.1), ctx=OKNO))
    out = e.on_bar(candle(t + STEP, vwap + 0.05, vwap + 0.9, vwap - 0.1, vwap + 0.8), ctx=OKNO)
    assert [o.plan.direction for o in entries(out)] == [Direction.LONG]


def test_druhy_stopu():
    atr_stop = {}
    for mode in SlMode:
        e, i = armed_long(slMode=mode, slBufferAtr=SizeSpec(0.0, "atr"))
        vwap = e.vwap.value
        out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
        (intent,) = entries(out)
        atr_stop[mode] = (intent.plan, vwap, e.history.atr)
    plan, vwap, _ = atr_stop[SlMode.PULLBACK]
    assert abs(plan.stop_loss - (vwap - 0.4)) <= 0.1
    plan, vwap, _ = atr_stop[SlMode.VWAP]
    assert abs(plan.stop_loss - vwap) <= 0.1
    plan, _, atr = atr_stop[SlMode.ATR]
    assert abs((plan.entry - plan.stop_loss) - 1.5 * atr) <= 0.1
    plan, _, _ = atr_stop[SlMode.SWING]
    assert plan.stop_loss <= atr_stop[SlMode.PULLBACK][0].stop_loss
