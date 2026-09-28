"""Seansový VWAP (`tradebot.core.vwap`): vzorec, kotva, perióda a nulovanie dňa."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from tradebot.core import Bar
from tradebot.core.vwap import SessionVwap, session_vwap

NY = ZoneInfo("America/New_York")
MIN = 60_000


def ny_ms(y, mo, d, h, m) -> int:
    return int(datetime(y, mo, d, h, m, tzinfo=NY).timestamp() * 1000)


def bar(ts, h, low, c, v) -> Bar:
    return Bar(time=ts, open=c, high=h, low=low, close=c, volume=v)


def test_vzorec_hlc3_vazeny_objemom_a_nic_pred_kotvou():
    ind = SessionVwap(5)
    assert ind.push(bar(ny_ms(2025, 9, 2, 9, 25), 200, 100, 150, 1e6)) is None  # pred 9:30
    t = ny_ms(2025, 9, 2, 9, 30)
    ind.push(bar(t, 102, 98, 100, 10))           # hlc3 100
    v = ind.push(bar(t + 5 * MIN, 111, 105, 108, 30))  # hlc3 108
    assert v == pytest.approx((100 * 10 + 108 * 30) / 40)
    assert ind.updated and list(ind.history) == [100, v]


def test_nulty_objem_hodnotu_nemeni():
    ind = SessionVwap(5)
    t = ny_ms(2025, 9, 2, 9, 30)
    ind.push(bar(t, 102, 98, 100, 10))
    assert ind.push(bar(t + 5 * MIN, 300, 290, 295, 0)) == pytest.approx(100)
    assert not ind.updated


def test_perioda_15m_z_5m_barov_sa_meni_len_pri_zatvoreni():
    ind = SessionVwap(5, period_minutes=15)
    t = ny_ms(2025, 9, 2, 9, 30)
    assert ind.push(bar(t, 101, 99, 100, 10)) is None
    assert ind.push(bar(t + 5 * MIN, 104, 100, 103, 10)) is None
    # 9:40 zatvára periódu 9:30–9:45: high 106, low 99, close 105, objem 30
    v = ind.push(bar(t + 10 * MIN, 106, 102, 105, 10))
    assert ind.updated and v == pytest.approx((106 + 99 + 105) / 3)
    ind.push(bar(t + 15 * MIN, 200, 190, 195, 10))
    assert not ind.updated and ind.value == pytest.approx(v)


def test_novy_den_zacina_od_nuly():
    ind = SessionVwap(5)
    ind.push(bar(ny_ms(2025, 9, 2, 9, 30), 102, 98, 100, 10))
    assert ind.push(bar(ny_ms(2025, 9, 3, 9, 30), 202, 198, 200, 10)) == pytest.approx(200)
    assert len(ind.history) == 1


def test_klasicka_seansa_cez_polnoc_patri_k_nasledujucemu_dnu():
    ind = SessionVwap(60, start_minutes=18 * 60, end_minutes=17 * 60)
    ind.push(bar(ny_ms(2025, 9, 2, 18, 0), 102, 98, 100, 10))    # večer patrí k 3. 9.
    assert ind.day == (2025, 9, 3)
    v = ind.push(bar(ny_ms(2025, 9, 3, 10, 0), 111, 105, 108, 10))
    assert v == pytest.approx(104)                                 # ešte ten istý deň
    assert ind.push(bar(ny_ms(2025, 9, 3, 17, 0), 500, 400, 450, 10)) == pytest.approx(104)  # prestávka


def test_change_meria_zmenu_za_n_periodov():
    ind = SessionVwap(5)
    t = ny_ms(2025, 9, 2, 9, 30)
    for i, c in enumerate([100, 110, 120]):
        ind.push(bar(t + i * 5 * MIN, c, c, c, 10))
    assert ind.change(2) == pytest.approx(110 - 100)
    assert ind.change(3) is None


def test_session_vwap_nad_dataframe_je_to_iste_ako_push():
    pd = pytest.importorskip("pandas")
    t = ny_ms(2025, 9, 2, 9, 30)
    rows = [(t + i * 5 * MIN, 100 + i, 98 + i, 99 + i, 10 + i) for i in range(6)]
    df = pd.DataFrame(rows, columns=["ms", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["ms"], unit="ms", utc=True)
    s = session_vwap(df)
    ind = SessionVwap(5)
    expected = [ind.push(bar(ms, h, lo, c, v)) for ms, h, lo, c, v in rows]
    assert list(s) == pytest.approx(expected)
