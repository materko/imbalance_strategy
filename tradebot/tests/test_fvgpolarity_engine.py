"""FVG POLARITY: engine na syntetických baroch.

Testuje sa zadanie z nákresu (1. 10. 2026): po medvedom FVG long k medzere, TP na jej dotyk
(spodná hrana), SL 20 bodov; po býčom zrkadlovo; veľkosť FVG a SL sú nastaviteľné; kým beží
obchod, ďalšie FVG sa neobchodujú.
"""

from __future__ import annotations

from tradebot.core import Bar, MarketContext, OrderAction
from tradebot.core.types import INSTRUMENTS, Direction, SizeSpec
from tradebot.strategies.fvgpolarity import FvgPolarityConfig, FvgPolarityEngine, TpLevel

MNQ = INSTRUMENTS["mnq_databento"]
T0 = 1_759_300_000_000
STEP = 15 * 60_000
OKNO = MarketContext(in_trade_window=True)


def candle(i: int, o: float, h: float, low: float, c: float) -> Bar:
    return Bar(time=T0 + i * STEP, open=o, high=h, low=low, close=c, volume=100.0)


def engine(**kw) -> FvgPolarityEngine:
    return FvgPolarityEngine(FvgPolarityConfig(**kw), MNQ, 15)


def entries(out):
    return [o for o in out.orders if o.action is OrderAction.ENTRY]


def bear_fvg(e, ctx=OKNO):
    """Ako na nákrese: c1 low 24000, veľká červená, c3 high 23960 -> medzera 23960–24000."""
    e.on_bar(candle(0, 24020, 24030, 24000, 24005), ctx=ctx)
    e.on_bar(candle(1, 24005, 24008, 23900, 23910), ctx=ctx)
    return e.on_bar(candle(2, 23910, 23960, 23905, 23940), ctx=ctx)


def test_medvedi_fvg_je_long_k_medzere_tp_na_dotyk_sl_20_bodov():
    out = bear_fvg(engine())
    (intent,) = entries(out)
    plan = intent.plan
    assert plan.direction is Direction.LONG
    assert plan.entry == 23940                     # zavretie 3. sviečky -> fill na otvorení ďalšej
    assert plan.take_profit == 23960               # prvý dotyk FVG = spodná hrana medzery
    assert plan.stop_loss == 23920                 # 20 bodov
    assert [d.kind.value for d in out.drawings] == ["fp_fvg", "fp_entry"]


def test_bychi_fvg_je_short_k_medzere():
    e = engine()
    e.on_bar(candle(0, 23980, 24000, 23970, 23995), ctx=OKNO)
    e.on_bar(candle(1, 23995, 24100, 23990, 24090), ctx=OKNO)
    (intent,) = entries(e.on_bar(candle(2, 24090, 24110, 24040, 24070), ctx=OKNO))  # medzera 24000–24040
    assert intent.plan.direction is Direction.SHORT
    assert intent.plan.take_profit == 24040 and intent.plan.stop_loss == 24090


def test_tp_v_medzere_stred_a_vzdialena_hrana():
    assert entries(bear_fvg(engine(tpLevel=TpLevel.MID)))[0].plan.take_profit == 23980
    assert entries(bear_fvg(engine(tpLevel=TpLevel.FAR)))[0].plan.take_profit == 24000


def test_nastavitelny_sl_a_velkost_fvg():
    assert entries(bear_fvg(engine(slPoints=SizeSpec(35.0, "abs"))))[0].plan.stop_loss == 23905
    assert not entries(bear_fvg(engine(fvgMinSize=SizeSpec(50.0, "abs"))))     # medzera 40 < 50
    assert not entries(bear_fvg(engine(fvgMaxSize=SizeSpec(30.0, "abs"))))     # medzera 40 > 30
    assert entries(bear_fvg(engine(fvgMinSize=SizeSpec(40.0, "abs"), fvgMaxSize=SizeSpec(40.0, "abs"))))


def test_pocas_obchodu_sa_dalsi_fvg_neobchoduje_ale_kresli():
    out = bear_fvg(engine(), ctx=MarketContext(in_trade_window=True, position_size=1.0))
    assert not entries(out) and [d.kind.value for d in out.drawings] == ["fp_fvg"]


def test_bez_medzery_nic_a_smer():
    e = engine()
    for i, c in enumerate((100.0, 101.0, 100.5)):
        out = e.on_bar(candle(i, c, c + 1, c - 1, c), ctx=OKNO)
    assert not entries(out)
    assert not entries(bear_fvg(engine(tradeDirection="Short only")))
