"""`[trade]` riadky z logu študie → tabuľka obchodov MultiCharts (mc_log_trades)."""

from __future__ import annotations

from pathlib import Path

from tester.compare.mc_log_trades import main, parse_trades

LOG = """2026-09-07 09:00:00 ibs: prvy bar grafu Time[0]=... (stary beh)
09:00:01 [trade] n=1 bar=2024-12-01 10:00 order=LONG_1 lots=1 entry=100.000 pnl=5.00 intrabar=0
2026-09-07 09:55:06 ibs: prvy bar grafu Time[0]=6. 1. 2025 1:33:00 (3m) -> otvorenie ...
09:55:06 [trace] Send market long_market_0 name=LONG_9 lots=27
09:55:06 [trade] n=1 bar=2025-01-06 16:30 order=LONG_9 lots=27 entry=21674.909 pnl=342.90 intrabar=1
09:55:07 [trade] n=2 bar=2025-01-13 17:00 order=LONG_49 lots=6 entry=20634.686 pnl=-341.72 intrabar=0
09:55:07 [trade] n=3 bar=2025-02-05 09:33 order=LONG_159 lots=26 entry=nan pnl=0.00 intrabar=1
"""


def test_parse_berie_len_posledny_beh_a_cita_polia():
    trades = parse_trades(LOG.splitlines())
    assert [t.order for t in trades] == ["LONG_9", "LONG_49", "LONG_159"]
    first = trades[0]
    assert first.n == 1 and first.bar == "2025-01-06 16:30" and first.lots == 27 and first.intrabar
    assert first.outcome == "WIN" and trades[1].outcome == "LOSS" and trades[2].outcome == "FLAT"
    assert len(parse_trades(LOG.splitlines(), last_run_only=False)) == 4


def test_cli_filtruje_datum_a_vypise_tabulku(tmp_path: Path, capsys):
    log = tmp_path / "multicharts.log"
    log.write_text(LOG, encoding="utf-8")
    assert main(["--log", str(log), "--from", "2025-01-01", "--to", "2025-01-31"]) == 0
    out = capsys.readouterr().out
    assert "MultiCharts obchody z multicharts.log: 2  (1W / 1L" in out
    assert "LONG_49" in out and "LONG_159" not in out and "(intrabar)" in out
    assert main(["--log", str(tmp_path / "nie.log")]) == 1
