"""Rozdelenie príkazov na maker a taker.

Celý zmysel tohto merania stojí na jednej otázke: ležala limitka v knihe, alebo
prekročila spread? Ak sa strana pomýli, zmiešaný poplatok vyjde nižší, než aký by
burza reálne vzala, a stratégia bude vyzerať zisková bez toho, aby bola.
"""

from __future__ import annotations

import json
import zipfile

import pytest

pd = pytest.importorskip("pandas")

from ibs.tools import fees

#: Sviečka, na ktorej sa príkazy zadávajú — otvára na 100.
CHART = pd.DataFrame(
    {
        "date": pd.to_datetime(["2026-08-24 10:00", "2026-08-24 10:03"], utc=True),
        "open": [100.0, 100.0],
        "high": [101.0, 101.0],
        "low": [99.0, 99.0],
        "close": [100.5, 100.5],
        "volume": [1.0, 1.0],
    }
)


def _trade(rate, exit_reason="roi", short=False, close=None):
    return {
        "open_date": "2026-08-24 10:00:00+00:00",
        "close_date": "2026-08-24 10:03:00+00:00",
        "open_rate": rate,
        "close_rate": close if close is not None else rate + 10.0,
        "amount": 1.0,
        "profit_abs": 10.0,
        "exit_reason": exit_reason,
        "is_short": short,
        "fee_open": 0.0,
        "fee_close": 0.0,
        "funding_fees": 0.0,
    }


def _zip(tmp_path, trades):
    stats = {
        "trades": trades,
        "timeframe": "3m",
        "starting_balance": 10_000.0,
        "stake_currency": "USDT",
        "backtest_start": "2026-08-24 00:00:00",
        "backtest_end": "2026-08-25 00:00:00",
    }
    path = tmp_path / "backtest-result-2026-08-25_10-00-00.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "backtest-result-2026-08-25_10-00-00.json",
            json.dumps({"strategy": {"IBSImbalanceStrategy": stats}}),
        )
        z.writestr("backtest-result-2026-08-25_10-00-00_config.json", "{}")
    return path


@pytest.fixture(autouse=True)
def chart(monkeypatch):
    from ibs.tools import scan_zones

    monkeypatch.setattr(scan_zones, "_load", lambda exchange, timeframe: CHART.copy())


def _classified(tmp_path, trades):
    stats, tr = fees.load(_zip(tmp_path, trades))
    return fees.classify(stats, tr)


def test_long_limitka_pod_trhom_je_maker(tmp_path):
    tr = _classified(tmp_path, [_trade(99.0)])
    assert bool(tr["entry_maker"].iloc[0]) is True


def test_long_limitka_nad_trhom_je_taker(tmp_path):
    """Prekročila by spread — burza ju vyplní okamžite, teda ako taker."""
    tr = _classified(tmp_path, [_trade(100.5)])
    assert bool(tr["entry_maker"].iloc[0]) is False


def test_short_ide_opacne(tmp_path):
    tr = _classified(tmp_path, [_trade(101.0, short=True), _trade(99.5, short=True)])
    assert list(tr["entry_maker"]) == [True, False]


def test_vystup_podla_dovodu(tmp_path):
    tr = _classified(
        tmp_path,
        [_trade(99.0, "roi"), _trade(99.0, "stop_loss"), _trade(99.0, "session_end")],
    )
    assert list(tr["exit_maker"]) == [True, False, False]


def test_neznamy_dovod_vystupu_je_taker(tmp_path):
    """Konzervatívne — radšej poplatok nadhodnotiť než podhodnotiť."""
    tr = _classified(tmp_path, [_trade(99.0, "force_exit")])
    assert bool(tr["exit_maker"].iloc[0]) is False


def test_poplatky_sa_pocitaju_kazdej_strane_zvlast(tmp_path):
    # vstup 99 (maker), vystup 109 (roi -> maker); pri 0,02 % je to 0,0416 USDT
    tr = _classified(tmp_path, [_trade(99.0, "roi")])
    s = fees.summarize(tr, maker=0.02, taker=0.05)
    assert s["fees"] == pytest.approx((99.0 + 109.0) * 0.0002)
    assert s["gross"] == pytest.approx(10.0)
    assert s["net"] == pytest.approx(10.0 - (99.0 + 109.0) * 0.0002)


def test_taker_vystup_stoji_viac_nez_maker(tmp_path):
    a = fees.summarize(_classified(tmp_path, [_trade(99.0, "roi")]))
    b = fees.summarize(_classified(tmp_path, [_trade(99.0, "stop_loss")]))
    assert b["fees"] > a["fees"]


def test_break_even_je_hruby_zisk_na_objem(tmp_path):
    tr = _classified(tmp_path, [_trade(99.0)])
    s = fees.summarize(tr)
    assert s["break_even"] == pytest.approx(10.0 / (99.0 + 109.0) * 100)


def test_short_zisk_ma_spravne_znamienko(tmp_path):
    """Short zarába, keď cena klesne — bez toho by hrubý zisk vyšiel opačne."""
    tr = _classified(tmp_path, [_trade(101.0, short=True, close=91.0)])
    assert fees.summarize(tr)["gross"] == pytest.approx(10.0)
