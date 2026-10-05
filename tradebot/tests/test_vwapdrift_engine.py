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
    base = dict(ruleSet="custom", vwapPeriod=VwapPeriod.CHART, entryDelayMinutes=0, entryWindowMinutes=0,
                maxTradesPerDay=1)
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
    assert e.drift(e.history.atr) == 0 and e._state.bias == 0
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


def test_odchod_skor_nez_ma_vwap_smer_sa_zaeviduje_a_dotyk_potom_obchoduje():
    """Váš graf: cena je nad VWAP skôr, než je drift z 15m známy (10:15) — dotyk po ňom sa má obchodovať."""
    e = engine(vwapPeriod=VwapPeriod.M15)
    warm(e)
    closes = [102, 103, 104, 105, 106, 107, 108, 109, 110]   # 9:30–10:10, VWAP z 15m od 9:45
    for k, c in enumerate(closes):
        e.on_bar(bar(OPEN_MS + k * STEP, c), ctx=OKNO)
    assert e._state.long_armed and e._state.bias > 0
    vwap = e.vwap.value
    i = len(closes)
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=OKNO)
    assert [o.plan.direction for o in entries(out)] == [Direction.LONG]


def test_vstup_drzi_smer_dna_aj_ked_sa_vwap_v_pullbacku_splosti():
    e, i = armed_long(entryMode=EntryMode.REACTION)
    vwap = e.vwap.value
    t = OPEN_MS + i * STEP
    for k in range(2):  # pullback pri VWAP — VWAP sa takmer nehýbe
        e.on_bar(candle(t + k * STEP, vwap + 0.2, vwap + 0.3, vwap - 0.3, vwap + 0.1), ctx=OKNO)
    assert e.drift(e.history.atr) == 0 and e._state.bias == 1


def test_stop_pod_reakcnu_sviecku():
    e, i = armed_long(entryMode=EntryMode.REACTION, slMode=SlMode.CANDLE,
                      slBufferAtr=SizeSpec(0.0, "atr"))
    vwap = e.vwap.value
    t = OPEN_MS + i * STEP
    e.on_bar(candle(t, vwap + 1.0, vwap + 1.1, vwap - 0.8, vwap + 0.2), ctx=OKNO)   # hlboký knôt dotyku
    out = e.on_bar(candle(t + STEP, vwap + 0.2, vwap + 0.9, vwap - 0.1, vwap + 0.8), ctx=OKNO)
    (intent,) = entries(out)
    # stop pod low reakčnej sviečky (vwap - 0.1), nie pod celý pullback (vwap - 0.8)
    assert abs(intent.plan.stop_loss - (vwap - 0.1)) <= 0.1


def test_graf_testera_dotyk_zavrie_kusok_pod_vwap_a_reakcna_sviecka_je_vstup():
    """Graf z 28. 9. 2026: červená sviečka sa dotkne VWAP a zavrie kúsok POD ním, ďalšia zelená
    zavrie nad ním. To je pullback a vstup — nie prerazenie. Platí pre `close` aj `reaction`."""
    for mode in (EntryMode.CLOSE, EntryMode.REACTION):
        e, i = armed_long(entryMode=mode)
        vwap = e.vwap.value
        atr = e.history.atr
        t = OPEN_MS + i * STEP
        below = vwap - 0.3 * atr          # pod VWAP, ale menej než failCloseAtr (0,5 ATR)
        out = e.on_bar(candle(t, vwap + 0.5, vwap + 0.6, vwap - 0.6 * atr, below), ctx=OKNO)
        assert not entries(out), mode
        out = e.on_bar(candle(t + STEP, below, vwap + 0.9, vwap - 0.5 * atr, vwap + 0.8), ctx=OKNO)
        assert [o.plan.direction for o in entries(out)] == [Direction.LONG], mode


def test_zavretie_hlboko_za_vwap_je_prerazenie():
    e, i = armed_long(entryMode=EntryMode.REACTION)
    vwap = e.vwap.value
    atr = e.history.atr
    t = OPEN_MS + i * STEP
    e.on_bar(candle(t, vwap + 0.5, vwap + 0.6, vwap - 1.5 * atr, vwap - 1.0 * atr), ctx=OKNO)
    out = e.on_bar(candle(t + STEP, vwap - atr, vwap + 0.9, vwap - atr, vwap + 0.8), ctx=OKNO)
    assert not entries(out)


# ---- každý odraz a prerazenie --------------------------------------------- #


def _bounce(e, i, ctx=OKNO):
    """Dotyk VWAP zhora a zavretie nad ním (vstup `close`); vráti výstup a ďalší index."""
    vwap = e.vwap.value
    out = e.on_bar(bar(OPEN_MS + i * STEP, vwap + 0.6, low=vwap - 0.4, high=vwap + 0.8), ctx=ctx)
    return out, i + 1


def test_bez_every_bounce_sa_druhy_odraz_neobchoduje_a_s_nim_ano():
    for every, expected in ((False, 0), (True, 1)):
        e, i = armed_long(everyBounce=every)
        out, i = _bounce(e, i)
        assert len(entries(out)) == 1
        i = trend(e, [e.vwap.value + 1.0, e.vwap.value + 1.2], i)   # nový odchod ~1 ATR
        out, i = _bounce(e, i)
        assert len(entries(out)) == expected, every


def test_every_bounce_chce_novy_odchod_a_drzi_strop():
    e, i = armed_long(everyBounce=True, maxBouncesPerDay=2,
                      bounceAwayAtr=SizeSpec(0.25, "atr"))
    out, i = _bounce(e, i)
    assert entries(out)
    out, i = _bounce(e, i)                        # hneď ďalší dotyk bez odchodu — nie je odraz
    assert not entries(out)
    i = trend(e, [e.vwap.value + 1.0], i)
    out, i = _bounce(e, i)
    assert entries(out)                           # druhý odraz
    i = trend(e, [e.vwap.value + 1.0], i)
    out, i = _bounce(e, i)
    assert not entries(out)                       # strop 2 odrazy za deň


def test_prerazenie_vwap_zdola_je_long_a_zhora_short():
    for with_bias, expected in ((False, [Direction.SHORT]), (True, [])):
        e, i = armed_long(tradeBreakout=True, breakoutWithBias=with_bias, entryMode=EntryMode.REACTION)
        vwap, atr = e.vwap.value, e.history.atr
        # zo strany nad VWAP zavrie 1 ATR pod ním — prerazenie nadol (proti rastúcemu dňu)
        out = e.on_bar(candle(OPEN_MS + i * STEP, vwap + 0.5, vwap + 0.6, vwap - 1.3 * atr,
                              vwap - 1.0 * atr), ctx=OKNO)
        assert [o.plan.direction for o in entries(out)] == expected, with_bias


def test_prerazenie_v_smere_dna_po_navrate_zdola():
    e, i = armed_long(tradeBreakout=True, breakoutWithBias=True)
    vwap, atr = e.vwap.value, e.history.atr
    e.on_bar(candle(OPEN_MS + i * STEP, vwap + 0.5, vwap + 0.6, vwap - 1.3 * atr, vwap - 1.0 * atr), ctx=OKNO)
    vwap = e.vwap.value
    out = e.on_bar(candle(OPEN_MS + (i + 1) * STEP, vwap - 0.9 * atr, vwap + 1.2 * atr, vwap - 1.0 * atr,
                          vwap + 1.0 * atr), ctx=OKNO)
    (intent,) = entries(out)
    assert intent.plan.direction is Direction.LONG and intent.reason == "prerazenie VWAP"
    assert e._state.breakouts == 1


# --------------------------------------------------------------------------- #
# pravidlá z videa (ruleSet = video)
# --------------------------------------------------------------------------- #


def vbar(i: int, o: float, c: float, low: float | None = None, high: float | None = None) -> Bar:
    return Bar(time=OPEN_MS + i * STEP, open=o, high=max(o, c) + 0.01 if high is None else high,
               low=min(o, c) - 0.01 if low is None else low, close=c, volume=10.0)


def video(**kw) -> VwapDriftEngine:
    e = VwapDriftEngine(VwapDriftConfig(**kw), BTCUSDT_BINANCE, 5)
    warm(e)
    return e


def climb(e, n: int, start: float = 100.0, step: float = 0.05, first: int = 0, sign: int = 1):
    """`n` sviečok v smere (`sign` +1 zelené hore, -1 červené dole); vráti (ďalší index, cena)."""
    px = start
    for i in range(first, first + n):
        out = e.on_bar(vbar(i, px, px + sign * step), ctx=OKNO)
        assert not entries(out), "sviečka v smere trendu nie je spúšťač"
        px += sign * step
    return first + n, px


def test_video_defaulty():
    cfg = VwapDriftConfig()
    assert cfg.ruleSet.value == "video"
    assert (cfg.slPointsLong.value, cfg.tpPointsLong.value) == (80, 40)
    assert (cfg.slPointsShort.value, cfg.tpPointsShort.value) == (80, 50)
    assert cfg.trendMovePct == 0.1 and cfg.trendLookbackMinutes == 60 and cfg.vwapRisePeriods == 1
    assert cfg.entryDelayMinutes == 60 and cfg.entryWindowMinutes == 360     # 10:30 až 15:30
    assert cfg.maxTradesPerDay == 4 and cfg.maxLossesPerDay == 2
    assert cfg.end_minutes == 15 * 60 + 55 and cfg.closeAtSessionEnd


def test_stary_profil_bez_ruleset_ostava_custom():
    cfg = VwapDriftConfig.from_dict({"awayAtr": 1.0, "entryMode": "limit"})
    assert cfg.ruleSet.value == "custom" and cfg.maxTradesPerDay == 1 and cfg.entryDelayMinutes == 15


def test_video_long_prva_cervena_sviecka_po_prvej_hodine_stop_80_ciel_40():
    e = video()
    i, px = climb(e, 9)                                            # 9:30–10:15, trend hore
    assert not entries(e.on_bar(vbar(i, px, px - 0.02), ctx=OKNO)), "červená o 10:15 — vstup by bol pred 10:30"
    i, px = climb(e, 2, start=px - 0.02, first=i + 1)              # do 10:30, 15m otázka: áno
    assert e._state.trend == 1
    out = e.on_bar(vbar(i, px, px - 0.02), ctx=OKNO)               # 10:30–10:35 červená = spúšťač
    o = entries(out)[0]
    assert o.direction is Direction.LONG and o.order_type.value == "Market"
    assert abs(o.plan.entry - (px - 0.02)) < 0.06          # zaokrúhlené na tick
    assert abs(o.plan.entry - o.plan.stop_loss - 80) < 1e-6 and abs(o.plan.take_profit - o.plan.entry - 40) < 1e-6


def test_video_short_prva_zelena_sviecka_stop_80_ciel_50():
    e = video()
    i, px = climb(e, 12, sign=-1)
    assert e._state.trend == -1
    o = entries(e.on_bar(vbar(i, px, px + 0.02), ctx=OKNO))[0]
    assert o.direction is Direction.SHORT
    assert abs(o.plan.stop_loss - o.plan.entry - 80) < 1e-6 and abs(o.plan.entry - o.plan.take_profit - 50) < 1e-6


def test_video_bez_pohybu_ceny_o_desatinu_percenta_za_hodinu_nie_je_trend():
    e = video()
    i, px = climb(e, 12, step=0.005)                               # +0,06 % za hodinu
    assert e._state.trend == 0
    assert not entries(e.on_bar(vbar(i, px, px - 0.02), ctx=OKNO))


def test_video_po_dvoch_stratach_sa_v_ten_den_konci():
    e = video(slPointsLong=0.5, tpPointsLong=5.0)
    i, px = climb(e, 12)
    for n in range(2):
        o = entries(e.on_bar(vbar(i, px, px - 0.02), ctx=OKNO))[0]
        drzi = MarketContext(in_trade_window=True, position_size=1.0, open_order_ids=frozenset({o.order_id}))
        e.on_bar(vbar(i + 1, px - 0.02, px + 0.05), ctx=drzi)
        e.on_bar(vbar(i + 2, px + 0.05, px + 0.1, low=o.plan.stop_loss - 0.1), ctx=OKNO)   # stop zasiahnutý
        assert e._state.losses == n + 1
        i, px = climb(e, 3, start=px + 0.1, first=i + 3)           # ďalšia 15m otázka: stále trend
    assert e._state.trend == 1
    assert not entries(e.on_bar(vbar(i, px, px - 0.02), ctx=OKNO)), "po dvoch stratách už žiadny obchod"


def test_video_po_okne_uz_ziadny_novy_obchod():
    e = video(entryWindowMinutes=70)                               # vstup najneskôr 10:40
    i, px = climb(e, 15)                                           # do 10:45
    assert e._state.trend == 1
    assert not entries(e.on_bar(vbar(i, px, px - 0.02), ctx=OKNO))
