"""MultiCharts adaptér — runner a mapovanie kreslenia.

Testuje sa bez MultiCharts: `runner.py` aj `drawing.py` sú zámerne bez závislosti
na PowerLanguage, ktoré existuje len vnútri tej aplikácie. `signal.py` sa sem
neimportuje.
"""

from __future__ import annotations

import pytest

from ibs.adapters.multicharts import MCDrawSink, MCRunner, hex_to_rgb
from ibs.core import Bar, DrawBox, DrawKind, DrawLabel, DrawLine, IBSConfig, LineStyle
from ibs.core.drawing import DrawBg, DrawDelete, DrawUpdate
from ibs.core.types import MNQ

MIN3 = 180_000
MIN5 = 300_000
T0 = 1_756_684_800_000


def bar(ts: int, o=100.0, h=101.0, low=99.0, c=100.5, v=100.0) -> Bar:
    return Bar(time=ts, open=o, high=h, low=low, close=c, volume=v)


def _cfg() -> IBSConfig:
    return IBSConfig(
        sess1On=True, sess1TZ="UTC", weekdaysOnly=False,
        sess1ZoneStartH=0, sess1ZoneEndH=23,
        sess1TradeStartH=0, sess1TradeEndH=23,
    )


@pytest.fixture
def runner() -> MCRunner:
    return MCRunner(_cfg(), MNQ, chart_tf_minutes=3)


# --------------------------------------------------------------------------- #
# HTF
# --------------------------------------------------------------------------- #


def test_htf_okno_potrebuje_styri_uzavrete_bary(runner):
    runner.feed_htf(bar(T0 - MIN5))
    runner.on_bar(bar(T0))
    out = runner.on_bar(bar(T0 + 2 * MIN3))
    assert out.entries == []  # bez okna nevznikne zóna, teda ani order


def test_feed_htf_ignoruje_ten_isty_bar_dvakrat(runner):
    runner.feed_htf(bar(T0, v=10.0))
    runner.feed_htf(bar(T0, v=999.0))
    assert runner.htf_bars[T0].volume == 10.0


def test_htf_historia_sa_neda_do_nekonecna(runner):
    for i in range(400):
        runner.feed_htf(bar(T0 + i * MIN5))
    keep = runner.cfg.volSmaLen + 4 + 8
    assert len(runner.htf_bars) <= keep


def test_vol_sma_je_nula_kym_nie_je_dost_barov(runner):
    for i in range(3):
        runner.feed_htf(bar(T0 + i * MIN5, v=100.0))
    assert runner.htf_vol_sma[T0] == 0.0


def test_vol_sma_je_priemer_poslednych_n(runner):
    n = runner.cfg.volSmaLen
    for i in range(n):
        runner.feed_htf(bar(T0 + i * MIN5, v=10.0))
    assert runner.htf_vol_sma[T0 + (n - 1) * MIN5] == pytest.approx(10.0)


# --------------------------------------------------------------------------- #
# Životný cyklus orderov
# --------------------------------------------------------------------------- #


def _live_order(runner, order_id="LONG_1"):
    """Podstrčí runneru živý order bez toho, aby ho musel vyrobiť engine."""
    from ibs.adapters.multicharts.runner import LiveOrder
    from ibs.core.risk import TradePlan
    from ibs.core.types import Direction

    plan = TradePlan(
        direction=Direction.LONG, entry=100.0, stop_loss=95.0,
        take_profit=105.0, qty=2.0, sl_distance=5.0,
    )
    runner._live[order_id] = LiveOrder(order_id, 1, Direction.LONG, plan)
    return plan


def test_order_sa_posiela_znova_kazdy_bar(runner):
    """V MultiCharts platí order len jeden bar — bez opakovania ticho zmizne."""
    _live_order(runner)
    ids = []
    for i in range(1, 4):
        out = runner.on_bar(bar(T0 + i * MIN3))
        ids.append([o.order_id for o in out.entries])
    assert ids == [["LONG_1"], ["LONG_1"], ["LONG_1"]]


def test_otvorena_pozicia_zastavi_posielanie_vstupov(runner):
    _live_order(runner)
    out = runner.on_bar(bar(T0 + MIN3), position_size=2.0)
    assert out.entries == []


def test_otvorena_pozicia_da_vystupny_plan(runner):
    plan = _live_order(runner)
    out = runner.on_bar(bar(T0 + MIN3), position_size=2.0)
    assert out.exit_plan is plan
    assert out.exit_plan.stop_loss == 95.0 and out.exit_plan.take_profit == 105.0


def test_po_zavreti_pozicie_sa_vystupny_plan_zahodi(runner):
    _live_order(runner)
    runner.on_bar(bar(T0 + MIN3), position_size=2.0)
    out = runner.on_bar(bar(T0 + 2 * MIN3), position_size=0.0)
    assert out.exit_plan is None


def test_ten_isty_bar_druhykrat_neurobi_nic(runner):
    """MultiCharts vie zavolať CalcBar na tom istom bare viackrát."""
    _live_order(runner)
    first = runner.on_bar(bar(T0 + MIN3))
    again = runner.on_bar(bar(T0 + MIN3))
    assert first.entries and again.entries == []


# --------------------------------------------------------------------------- #
# Kreslenie
# --------------------------------------------------------------------------- #


class FakeCanvas:
    """Zaznamená volania namiesto toho, aby vyrábala PowerLanguage objekty."""

    def __init__(self):
        self.calls = []
        self.deleted = []
        self._n = 0

    def _obj(self, kind, kw):
        self._n += 1
        o = {"id": self._n, "kind": kind, **kw}
        self.calls.append(o)
        return o

    def create_rectangle(self, **kw):
        return self._obj("rect", kw)

    def create_trendline(self, **kw):
        return self._obj("line", kw)

    def create_text(self, **kw):
        return self._obj("text", kw)

    def set_end_x(self, obj, ms):
        obj["x2_ms"] = ms

    def set_fill(self, obj, rgb):
        obj["fill"] = rgb

    def set_border(self, obj, rgb):
        obj["border"] = rgb

    def set_color(self, obj, rgb):
        obj["color"] = rgb

    def set_end_y(self, obj, p):
        obj["y2"] = p

    def set_begin_x(self, obj, ms):
        obj["x1_ms"] = ms

    def set_begin_y(self, obj, p):
        obj["y1"] = p

    def delete(self, obj):
        self.deleted.append(obj["id"])


def test_hex_bez_alfy():
    assert hex_to_rgb("#be3c46") == (190, 60, 70)


def test_hex_s_alfou_alfu_zahodi():
    """MultiCharts nepozná priehľadnosť — alfa sa musí zahodiť, nie spadnúť."""
    assert hex_to_rgb("#be3c46d9") == (190, 60, 70)


def test_nezmyselna_farba_spadne():
    with pytest.raises(ValueError):
        hex_to_rgb("#abc")


def test_box_sa_premeni_na_rectangle():
    c = FakeCanvas()
    MCDrawSink(c).apply(
        DrawBox(kind=DrawKind.SD_ZONE_POST, x1_ms=T0, y1=110.0, x2_ms=T0 + MIN3, y2=100.0,
                border_color="#be3c46d9", fill_color="#be3c4626", obj_id="z1.post")
    )
    assert c.calls[0]["kind"] == "rect"
    assert c.calls[0]["border"] == (190, 60, 70)
    assert c.calls[0]["fill"] == (190, 60, 70)


def test_ciara_a_stitok():
    c = FakeCanvas()
    sink = MCDrawSink(c)
    sink.apply(DrawLine(kind=DrawKind.STRUCTURE, x1_ms=T0, y1=100.0, x2_ms=T0 + MIN3,
                        y2=100.0, color="#334155", obj_id="s1", text="BOS"))
    sink.apply(DrawLabel(kind=DrawKind.SWING, x_ms=T0, y=101.0, text="HH",
                         color="#10b981", obj_id="w1"))
    assert [o["kind"] for o in c.calls] == ["line", "text"]
    assert c.calls[1]["text"] == "HH"


def test_update_zmeni_ten_isty_objekt():
    """Pine `box.set_right` — nesmie vzniknúť druhý obdĺžnik."""
    c = FakeCanvas()
    sink = MCDrawSink(c)
    sink.apply(DrawBox(kind=DrawKind.SD_ZONE_POST, x1_ms=T0, y1=110.0, x2_ms=T0 + 10 * MIN3,
                       y2=100.0, border_color="#be3c46", obj_id="z1.post"))
    sink.apply(DrawUpdate("z1.post", "x2_ms", T0 + MIN3))
    assert len(c.calls) == 1
    assert c.calls[0]["x2_ms"] == T0 + MIN3


def test_update_na_zmazany_objekt_je_ticho():
    c = FakeCanvas()
    sink = MCDrawSink(c)
    sink.apply(DrawBox(kind=DrawKind.TP_BOX, x1_ms=T0, y1=110.0, x2_ms=T0 + MIN3, y2=100.0,
                       border_color="#10b981", obj_id="z1.tp_box"))
    sink.apply(DrawDelete("z1.tp_box"))
    sink.apply(DrawUpdate("z1.tp_box", "x2_ms", T0 + 5 * MIN3))
    assert c.deleted == [1]


def test_pozadie_seansy_sa_standardne_preskakuje():
    """`bgcolor()` nemá v MultiCharts náprotivok — obdĺžnik cez celú výšku sa nedá."""
    c = FakeCanvas()
    MCDrawSink(c).apply(DrawBg(kind=DrawKind.SESSION, x1_ms=T0, x2_ms=T0 + MIN3,
                               color="#6366f114", obj_id="bg1.0"))
    assert c.calls == []


def test_objekt_bez_id_spadne():
    c = FakeCanvas()
    with pytest.raises(ValueError):
        MCDrawSink(c).apply(
            DrawBox(kind=DrawKind.IMB_BOX, x1_ms=T0, y1=1.0, x2_ms=T0, y2=0.0,
                    border_color="#ffffff", border_style=LineStyle.SOLID)
        )


def test_clear_zmaze_vsetko():
    c = FakeCanvas()
    sink = MCDrawSink(c)
    for i in range(3):
        sink.apply(DrawLabel(kind=DrawKind.SWING, x_ms=T0, y=1.0, text="HH",
                             color="#ffffff", obj_id=f"w{i}"))
    sink.clear()
    assert sorted(c.deleted) == [1, 2, 3] and sink.objects == {}


# --------------------------------------------------------------------------- #
# Parita s Freqtrade vetvou
# --------------------------------------------------------------------------- #


def test_multicharts_a_freqtrade_daju_rovnake_zony():
    """Obe platformy musia z tých istých barov dostať to isté — to je zmysel jadra.

    Ak sa toto rozíde, znamená to, že adaptér niekde obchádza `ibs.core`.
    """
    pytest.importorskip("pandas")
    import pandas as pd

    from ibs.adapters.freqtrade.runner import EngineRunner
    from ibs.core import load_profile
    from ibs.tools.scan_zones import _load, _to_bar

    cfg, inst = load_profile("btcusdt_3m_binance_tv")
    try:
        chart = _load("binance", "3m")
        htf_df = _load("binance", "5m")
    except SystemExit as exc:
        pytest.skip(f"dáta nie sú k dispozícii: {exc}")

    for df in (chart, htf_df):
        df["date"] = pd.to_datetime(df["date"], utc=True)
    lo, hi = pd.Timestamp("2026-08-24", tz="UTC"), pd.Timestamp("2026-08-27", tz="UTC")
    chart = chart[(chart["date"] >= lo) & (chart["date"] < hi)]
    htf_df = htf_df[(htf_df["date"] >= lo) & (htf_df["date"] < hi)]

    htf_bars = {int(r.ts): _to_bar(r) for r in htf_df.itertuples(index=False)}
    sma_series = htf_df["volume"].rolling(cfg.volSmaLen).mean()
    htf_sma = {
        int(r.ts): (float(v) if v == v else 0.0)
        for r, v in zip(htf_df.itertuples(index=False), sma_series)
    }

    ft = EngineRunner(cfg, inst, 3)
    mc = MCRunner(cfg, inst, 3)

    # MultiCharts dostáva HTF bary priebežne cez Data2, nie naraz dopredu -
    # `signal.py` berie na každom CalcBar posledný UZAVRETÝ bar Data2.
    htf_sorted = sorted(htf_bars)
    nxt = 0
    for row in chart.itertuples(index=False):
        b = _to_bar(row)
        close_ms = b.time + 180_000
        while nxt < len(htf_sorted) and htf_sorted[nxt] + 300_000 <= close_ms:
            mc.feed_htf(htf_bars[htf_sorted[nxt]])
            nxt += 1
        ft.process(b, ft.htf_window_for(b.time, htf_bars, htf_sma))
        mc.on_bar(b)

    ft_zones = [(z.uid, z.top, z.bot, z.detected_ms) for z in ft.engine.book.zones]
    mc_zones = [(z.uid, z.top, z.bot, z.detected_ms) for z in mc.engine.book.zones]
    assert ft_zones == mc_zones
    assert len(mc_zones) > 0
