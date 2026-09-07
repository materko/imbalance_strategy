"""Offline simulátor nad Dukascopy CSV (`--csv`) — načítanie, vypchávka, skladanie TF."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pandas")

from tradebot.core import load_profile
from tradebot.tools import scan_trades, scan_zones

CSV = """dt,o,h,l,c,vol
2025-01-06 00:00:00,100,101,99,100.5,1
2025-01-06 00:01:00,100.5,100.5,100.5,100.5,0
2025-01-06 00:02:00,100.5,100.5,100.5,100.5,0
2025-01-06 00:03:00,100.6,100.9,100.4,100.7,2
2025-01-06 00:04:00,100.7,100.8,100.6,100.75,3
2025-01-06 00:05:00,100.75,100.75,100.75,100.75,0
2025-01-06 00:06:00,100.8,100.8,100.8,100.8,0
"""


@pytest.fixture
def csv(tmp_path: Path) -> Path:
    p = tmp_path / "X_M1.csv"
    p.write_text(CSV, encoding="utf-8")
    scan_zones._load_dukas_csv.cache_clear()
    return p


def test_csv_zdroj_sa_pozna_podla_pripony():
    assert scan_zones.is_csv_source("C:/dukas/NAS100_M1_10Y.csv")
    assert scan_zones.is_csv_source(Path("x.CSV"))
    assert not scan_zones.is_csv_source("binance")


def test_1m_z_csv_zahodi_vypchavku_a_da_ts_v_ms(csv: Path):
    df = scan_zones._load(str(csv), "1m")
    # 00:01 a 00:02 su vypchavka (plochy bar = predchadzajuce uzavretie), 00:05 tiez;
    # 00:06 je plochy, ale cena sa pohla -> ostava
    assert list(df["date"].dt.strftime("%H:%M")) == ["00:00", "00:03", "00:04", "00:06"]
    assert int(df["ts"].iloc[0]) == 1_736_121_600_000  # 2025-01-06 00:00 UTC
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "ts"]


def test_3m_sa_posklada_z_1m_v_pamati(csv: Path):
    df = scan_zones._load(csv, "3m")
    assert len(df) == 3  # 00:00, 00:03, 00:06
    first, second = df.iloc[0], df.iloc[1]
    assert (first.open, first.high, first.low, first.close, first.volume) == (100, 101, 99, 100.5, 1)
    assert (second.open, second.high, second.low, second.close, second.volume) == (100.6, 100.9, 100.4, 100.75, 5)


def test_run_nad_csv_prejde_cely_automat(csv: Path):
    cfg, inst = load_profile(Path("docs/profily_archiv/ibs/nas100_dukas_3m.json"))
    book, sim, transitions, reasons = scan_trades.run(cfg, inst, csv, 3, "2025-01-06", "2025-01-06")
    assert len(book) == 0 and sim.trades == {} and transitions == 0


def test_cli_prijme_csv_a_odmietne_csv_spolu_s_burzou(csv: Path, capsys):
    profile = "docs/profily_archiv/ibs/nas100_dukas_3m.json"
    assert scan_trades.main(["--csv", str(csv), "--profile", profile]) == 0
    assert "orderov:          0" in capsys.readouterr().out
    assert scan_zones.main(["--csv", str(csv), "--profile", profile]) == 0
    assert "barov grafu:        3" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        scan_trades.main(["--csv", str(csv), "--exchange", "binance", "--profile", profile])
