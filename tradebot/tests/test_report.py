"""Report z Freqtrade backtestu.

Testuje sa to, čo sa v praxi rozbije: že sa výsledok načíta z toho istého zipu,
aký Freqtrade zapisuje, že sa čísla vezmú **z neho** a neprepočítajú sa niekde
cestou, a že sa stĺpce a krivka delia o rovnakú nulu — inak by graf klamal.
"""

from __future__ import annotations

import json
import zipfile

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("plotly")

from tradebot.tools import report


def _zip(tmp_path, trades, **over):
    """Napodobní `backtest_results/*.zip` — rovnaké mená súborov aj tvar JSON-u."""
    stats = {
        "trades": trades,
        "starting_balance": 10_000.0,
        "final_balance": 10_000.0 + sum(t["profit_abs"] for t in trades),
        "stake_currency": "USDT",
        "profit_total_abs": sum(t["profit_abs"] for t in trades),
        "profit_total": sum(t["profit_abs"] for t in trades) / 10_000.0,
        "profit_total_long_abs": 0.0,
        "profit_total_short_abs": 0.0,
        "total_trades": len(trades),
        "trade_count_long": sum(not t["is_short"] for t in trades),
        "trade_count_short": sum(t["is_short"] for t in trades),
        "wins": sum(t["profit_abs"] > 0 for t in trades),
        "profit_factor": 1.5,
        "max_drawdown_abs": 100.0,
        "max_drawdown_account": 0.01,
        "backtest_start": "2026-08-24 00:00:00",
        "backtest_end": "2026-08-26 00:00:00",
        "backtest_days": 2,
        "total_volume": 1000.0,
        "market_change": 0.05,
        "cagr": 0.1,
        "sharpe": 1.0,
        "sortino": 1.0,
        "calmar": 1.0,
        "expectancy": 1.0,
        "expectancy_ratio": 0.1,
        "max_consecutive_wins": 1,
        "max_consecutive_losses": 1,
        "holding_avg": "0:10:00",
        "timeframe": "3m",
        "timeframe_detail": "1m",
        "pairlist": ["BTC/USDT:USDT"],
        "exit_reason_summary": [
            {"key": "roi", "trades": 1, "wins": 1, "losses": 0, "profit_total_abs": 10.0}
        ],
        **over,
    }
    path = tmp_path / "backtest-result-2026-08-26_10-00-00.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(
            "backtest-result-2026-08-26_10-00-00.json",
            json.dumps({"strategy": {"IBSImbalanceStrategy": stats}}),
        )
        z.writestr("backtest-result-2026-08-26_10-00-00_config.json", "{}")
    return path


def _trade(opened, closed, rate, close_rate, pnl, short=False):
    return {
        "open_date": opened,
        "close_date": closed,
        "open_rate": rate,
        "close_rate": close_rate,
        "amount": 1.0,
        "profit_abs": pnl,
        "exit_reason": "roi" if pnl > 0 else "stop_loss",
        "is_short": short,
        "fee_open": 0.0005,
        "fee_close": 0.0005,
        "funding_fees": 0.0,
    }


TRADES = [
    _trade("2026-08-24 10:00:00+00:00", "2026-08-24 10:30:00+00:00", 100.0, 110.0, 10.0),
    _trade("2026-08-25 10:00:00+00:00", "2026-08-25 10:30:00+00:00", 110.0, 105.0, -5.0, True),
]


@pytest.fixture
def result(tmp_path):
    return report.load(_zip(tmp_path, TRADES))


def test_nacita_obchody_aj_statistiky(result):
    stats, trades, _ = result
    assert stats["strategy_name"] == "IBSImbalanceStrategy"
    assert len(trades) == 2
    assert str(trades["open_date"].dt.tz) == "UTC"


def test_cisla_su_zo_zipu_neprepocitane(tmp_path):
    """Profit factor sa nedopočítava — berie sa ten, čo vypočítal Freqtrade."""
    stats, trades, change = report.load(_zip(tmp_path, TRADES, profit_factor=9.99))
    html = report.render(stats, trades, change, tmp_path / "r.html").read_text(encoding="utf-8")
    assert "9.990" in html
    assert "+5.00" in html  # Total PnL = 10 - 5


def test_stlpce_a_krivka_maju_spolocnu_nulu(result):
    """Bez toho by stĺpce vyzerali ako zisk tam, kde je strata."""
    stats, trades, change = result
    fig = report._fig(stats, trades, change)
    lo, hi = fig.layout.yaxis.range
    lo2, hi2 = fig.layout.yaxis2.range
    assert lo2 / lo == pytest.approx(hi2 / hi)


def test_smer_obchodu_je_v_tabulke(result):
    stats, trades, _ = result
    html = report._trades_table(stats, trades)
    assert html.count("Long") == 1
    assert html.count("Short") == 1


def test_prazdny_vysledok_skonci_zrozumitelne(tmp_path):
    path = _zip(tmp_path, [])
    with pytest.raises(SystemExit, match="ziadne obchody"):
        report.main([str(path), "-o", str(tmp_path / "r.html")])
