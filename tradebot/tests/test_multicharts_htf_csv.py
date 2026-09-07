"""Informatívny TF z 1m Dukascopy CSV — záloha za Data2 v MultiCharts x Python."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradebot.adapters.multicharts.htf_csv import CsvHtfFeed, aggregate_csv
from tradebot.adapters.multicharts.runner import BarOutput
from tradebot.tests.test_multicharts_signal import FakeBars, FakeCtx, closed, fake_dotnet, make_signal  # noqa: F401

MIN = 60_000
T0 = 1_736_121_600_000  # 2025-01-06 00:00 UTC

CSV = """dt,o,h,l,c,vol
2025-01-06 00:00:00,100,101,99,100.5,1
2025-01-06 00:01:00,100.5,102,100,101,2
2025-01-06 00:02:00,101,101,101,101,0
2025-01-06 00:03:00,101,101,101,101,0
2025-01-06 00:04:00,101,103,100.5,102,3
2025-01-06 00:05:00,102,102.5,101.5,102.2,4
2025-01-06 00:07:00,102.2,104,102,103,5
2025-01-06 00:10:00,103.5,103.5,103.5,103.5,0
"""


@pytest.fixture
def csv(tmp_path: Path) -> Path:
    p = tmp_path / "X_M1.csv"
    p.write_text(CSV, encoding="utf-8")
    return p


def test_aggregate_5m_zarovna_na_epochu_a_zahodi_vypchavku(csv: Path):
    bars = aggregate_csv(csv, 5)
    assert [b.time for b in bars] == [T0, T0 + 5 * MIN, T0 + 10 * MIN]
    first = bars[0]
    # 00:02 a 00:03 su vypchavka (plochy bar = predchadzajuce uzavretie) -> nepocitaju sa
    assert (first.open, first.high, first.low, first.close, first.volume) == (100, 103, 99, 102, 6)
    second = bars[1]
    assert (second.open, second.high, second.low, second.close, second.volume) == (102, 104, 101.5, 103, 9)
    assert bars[2].open == 103.5 and bars[2].volume == 0  # plochy bar, ale cena sa pohla -> ostava


def test_feed_until_pusti_len_uzavrete_bary(csv: Path):
    feed = CsvHtfFeed(csv, 5)
    fed: list = []
    runner = type("R", (), {"feed_htf": lambda self, b: fed.append(b.time)})()
    assert len(feed) == 3
    assert feed.feed_until(runner, T0 + 3 * MIN) == 0  # prvy 5m bar sa zavrie az 00:05
    assert feed.feed_until(runner, T0 + 5 * MIN) == 1 and fed == [T0]
    assert feed.feed_until(runner, T0 + 6 * MIN) == 0  # nic nove
    assert feed.feed_until(runner, T0 + 60 * MIN) == 2 and fed == [T0, T0 + 5 * MIN, T0 + 10 * MIN]
    assert "3 barov 5m" in feed.describe()


def test_studia_bez_data2_krmi_htf_z_csv(csv: Path, fake_dotnet, monkeypatch):
    from tradebot.adapters.multicharts import signal as sig_mod

    monkeypatch.setattr(sig_mod.TradebotSignal, "HTF_CSV", str(csv))
    ctx = FakeCtx(FakeBars(3, [closed(T0 + 3 * MIN, 3)]))  # bez Data2; bar grafu zavrety 00:06
    s = make_signal(monkeypatch, ctx)
    assert any("sklada z CSV" in line for line in ctx.lines)
    assert not any("nie je Data2" in line for line in ctx.lines)
    fed: list = []
    monkeypatch.setattr(s.runner, "feed_htf", lambda bar: fed.append(bar.time))
    monkeypatch.setattr(s.runner, "on_bar", lambda bar, position_size=0.0, **kw: BarOutput())
    s.CalcBar()
    assert fed == [T0] and s._stats["htf"] == 1  # len 5m bar zavrety do 00:06


def test_bez_data2_a_bez_csv_ostava_chyba(fake_dotnet, monkeypatch):
    from tradebot.adapters.multicharts import signal as sig_mod

    monkeypatch.setattr(sig_mod.TradebotSignal, "HTF_CSV", None)
    monkeypatch.delenv("TRADEBOT_MC_HTF_CSV", raising=False)
    ctx = FakeCtx(FakeBars(3, [closed(T0, 3)]))
    make_signal(monkeypatch, ctx)
    assert any("CHYBA - na grafe nie je Data2" in line and "HTF_CSV" in line for line in ctx.lines)
