"""VWAP OP: engine na syntetických baroch.

Testuje sa mechanika doslovného portu: či drift na HTF (nie na grafe) určí smer, či sa
pullback počíta až po odchode od VWAP (`armed`), `firstOnly`/`maxTrades`, `needClose`,
breakeven (`useBE`) a zatvorenie na konci seansy (`closeEOD`).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core import MNQ, Bar, MarketContext, OrderAction
from tradebot.core.types import Direction
from tradebot.strategies.vwapop import VwapOpConfig, VwapOpEngine

NY = ZoneInfo("America/New_York")
#: utorok 2025-09-02, 9:30 New York
OPEN_MS = int(datetime(2025, 9, 2, 9, 30, tzinfo=NY).timestamp() * 1000)
MIN = 60_000
STEP = 5 * MIN
OKNO = MarketContext(in_trade_window=True)

#: 14 bodov (70 min od otvorenia) — dosť na 3 uzavreté 15m periódy (drift) aj na odchod od VWAP.
UP = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]
DOWN = [99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86]


def bar(ts, c, rng=1.0, v=10.0, low=None, high=None) -> Bar:
    return Bar(time=ts, open=c, high=c + rng / 2 if high is None else high,
               low=c - rng / 2 if low is None else low, close=c, volume=v)


def engine(**kw) -> VwapOpEngine:
    return VwapOpEngine(VwapOpConfig(**kw), MNQ, 5)


def warm(e: VwapOpEngine, bars: int = 200) -> None:
    """Bary pred otvorením seansy — chart aj HTF ATR sa ustália na ~1.0, VWAP sa ich nedotkne."""
    for i in range(bars, 0, -1):
        e.on_bar(bar(OPEN_MS - i * STEP, 100.0))


def trend(e: VwapOpEngine, closes, start_i: int = 0) -> int:
    """Bary seansy s danými close (mimo tolerancie VWAP); vráti index ďalšieho baru."""
    outs = [e.on_bar(bar(OPEN_MS + (start_i + k) * STEP, c), ctx=OKNO) for k, c in enumerate(closes)]
    assert not any(o.orders for o in outs), "počas odchodu od VWAP nemá vzniknúť vstup"
    return start_i + len(closes)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def armed_long(**kw):
    e = engine(**kw)
    warm(e)
    i = trend(e, UP)
    assert e._state.armed_long
    return e, i


def armed_short(**kw):
    e = engine(**kw)
    warm(e)
    i = trend(e, DOWN)
    assert e._state.armed_short
    return e, i


# --------------------------------------------------------------------------- #


def test_defaulty_su_ako_v_pine_skripte():
    cfg = VwapOpConfig()
    assert cfg.htf == "15" and cfg.rthSess == "0930-1600" and cfg.tradeWin == "0945-1530"
    assert cfg.driftLen == 2 and cfg.firstOnly and cfg.maxTrades == 2
    assert cfg.rr == 2.0 and not cfg.useBE and not cfg.closeEOD


def test_pullback_v_stupajucom_drifte_je_long_so_stopom_za_vwap():
    e, i = armed_long()
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    (intent,) = entries(out)
    plan = intent.plan
    assert plan.direction is Direction.LONG
    assert plan.stop_loss < vwap < plan.take_profit   # SL = VWAP - slAtr*ATR grafu, pod VWAP
    # TP aj SL sú zaokrúhlené na tick (MNQ 0,25) — rozdiel od RR najviac o pár tickov
    assert abs((plan.take_profit - plan.entry) - 2.0 * plan.sl_distance) <= 0.6


def test_klesajuci_drift_je_short():
    e, i = armed_short()
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap - 0.6, high=vwap + 0.4, low=vwap - 0.8), ctx=OKNO)
    assert [o.plan.direction for o in entries(out)] == [Direction.SHORT]


def test_bez_odchodu_od_vwap_sa_dotyk_nepocita():
    e = engine()
    warm(e)
    i = trend(e, [100.0] * 10)   # cena ostáva pri VWAP — nikdy "mimo tolerancie"
    assert not e._state.armed_long and not e._state.armed_short
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.05, low=vwap - 0.02, high=vwap + 0.1), ctx=OKNO)
    assert not entries(out)


def test_needclose_zabrani_vstupu_ked_zavrie_na_spravnej_strane_ale_pod_vwap():
    e, i = armed_long()
    vwap = e.vwap.value
    # dotkne sa VWAP, ale zavrie POD ním -> needClose=True zablokuje vstup
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap - 0.2, low=vwap - 0.4, high=vwap + 0.3), ctx=OKNO)
    assert not entries(out)


def test_first_only_zablokuje_druhy_pullback_v_tom_smere():
    e, i = armed_long()
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    assert entries(out) and e._state.done_long
    i = trend(e, [c + 20 for c in UP[:4]], i + 1)   # nový odchod od VWAP
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8),
                   ctx=MarketContext(in_trade_window=True, position_size=0.0))
    assert not entries(out), "firstOnly: druhý pullback dňa v tom smere sa neobchoduje"


def test_max_trades_je_strop_na_oba_smery_spolu():
    e, i = armed_long(firstOnly=False, maxTrades=1)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    assert entries(out) and e._state.n_day == 1
    i = trend(e, [c + 20 for c in UP[:4]], i + 1)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    assert not entries(out), "maxTrades=1: druhý obchod dňa už nemá vzniknúť"


def test_allow_long_off_zahodi_long_signal():
    e, i = armed_long(allowLong=False)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    assert not entries(out)


def test_useBE_prida_jednorazovy_breakeven_trailing():
    e, i = armed_long(useBE=True)
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    (intent,) = entries(out)
    plan = intent.plan
    assert plan.trailing is not None
    # pred +1R sa stop nehýbe
    assert plan.trailing.stop_price(Direction.LONG, plan.entry, plan.stop_loss,
                                    plan.entry + 0.5 * plan.sl_distance) == plan.stop_loss
    # presne na +1R skočí na vstup a nad ním zamrzne (nie kontinuálny trailing)
    be = plan.trailing.stop_price(Direction.LONG, plan.entry, plan.stop_loss,
                                  plan.entry + plan.sl_distance)
    assert be == plan.entry
    assert plan.trailing.stop_price(Direction.LONG, plan.entry, plan.stop_loss,
                                    plan.entry + 5 * plan.sl_distance) == plan.entry


def test_bez_useBE_nema_trailing():
    e, i = armed_long()
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    (intent,) = entries(out)
    assert intent.plan.trailing is None


def test_close_eod_zatvara_len_ked_je_zapnute():
    end = int(datetime(2025, 9, 2, 15, 57, tzinfo=NY).timestamp() * 1000)
    ctx = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=("vop:1",))

    e_off = engine()
    warm(e_off)
    out_off = e_off.on_bar(bar(end, 100), ctx=ctx)
    assert not out_off.close_session, "closeEOD=False (default): pozícia ostáva otvorená"

    e_on = engine(closeEOD=True)
    warm(e_on)
    out_on = e_on.on_bar(bar(end, 100), ctx=ctx)
    assert out_on.close_session and [o.action for o in out_on.orders] == [OrderAction.CLOSE]


def test_vwap_sa_kresli_ako_ciara_farbena_driftom():
    e = engine()
    warm(e)
    outs = [e.on_bar(bar(OPEN_MS + k * STEP, c), ctx=OKNO) for k, c in enumerate(UP)]
    lines = [d for o in outs for d in o.drawings if d.kind.value == "vop_vwap"]
    assert lines, "VWAP by sa mal kresliť aspoň raz po prvej uzavretej 15m perióde"
    assert lines[-1].color == "#22c55e"   # drift hore = colUp


def test_tp_sl_boxy_sa_kreslia_pri_vstupe():
    e, i = armed_long()
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    kinds = {d.kind.value for d in out.drawings}
    assert {"tp_box", "sl_box", "vop_entry"} <= kinds
