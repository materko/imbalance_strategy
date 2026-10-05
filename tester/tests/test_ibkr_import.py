"""Import IBKR exportu (americké akcie, TRADES 1m, RTH) — čas New York → UTC, vypchávka
s objemom 0 von, prekryv blokov zlúčený, 1m feather po rokoch do archívu."""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from tradebot.core.types import INSTRUMENTS
from tester import engines
from tester.ibkr_import import ImportStats, find_sources, load_ibkr_frame, main, resolve_symbol


def bars(times: list[str], close: float = 100.0, volume: float = 500.0, **override):
    rows = []
    for i, t in enumerate(times):
        c = close + i * 0.01
        rows.append({"dt": t, "open": c, "high": c + 0.05, "low": c - 0.05, "close": c, "volume": volume})
    df = pd.DataFrame(rows)
    for k, v in override.items():
        df[k] = v
    return df


def merged_parquet(tmp_path: Path, sym: str, times: list[str], **kw) -> Path:
    df = bars(times, **kw)
    df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize("America/New_York")
    p = tmp_path / f"{sym}_m1_2019_20261003.parquet"
    df.to_parquet(p)
    return p


def test_mag7_su_v_registri_ibkr_ako_multicharts_trh_s_burzovym_objemom():
    key, inst = resolve_symbol("AAPL")
    assert key == "aapl_ibkr" and inst.symbol == "AAPL/USD"
    assert inst.venue == "multicharts" and inst.data_source == "ibkr" and inst.has_real_volume
    assert inst.tick_size == 0.01 and inst.point_value == 1.0 and not inst.is_spot   # akcia sa dá shortovať
    assert inst.cost_unit == "ticks" and inst.cost > 0
    assert resolve_symbol("aapl_ibkr") == (key, inst) and resolve_symbol("AAPL/USD") == (key, inst)
    assert resolve_symbol("MNQ") is None
    assert {resolve_symbol(s)[0] for s in ("MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA")} \
        <= set(INSTRUMENTS)
    assert engines.market_kind(inst) == "cfd"          # mimo burzy: 1m na disku, beh emulátorom
    assert engines.one_minute_file(inst).name == "AAPL_USD-1m.feather"


def test_cas_new_york_ide_do_utc_aj_cez_zmenu_casu(tmp_path):
    p = merged_parquet(tmp_path, "AAPL", ["2024-01-02 09:30", "2024-07-01 09:30"])
    df = load_ibkr_frame([p])
    assert [f"{d:%Y-%m-%d %H:%M}" for d in df["date"]] == ["2024-01-02 14:30", "2024-07-01 13:30"]
    assert str(df["date"].dt.tz) == "UTC"
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]


def test_surove_bloky_naivny_cas_prekryv_a_csv_s_posunom(tmp_path):
    a = bars(["2024-03-08 09:30", "2024-03-08 09:31"]).rename(
        columns={"open": "o", "high": "h", "low": "l", "close": "c"})
    a["average"] = 1.0
    a.to_parquet(tmp_path / "NVDA_202401_202403.parquet")      # dt naivný New York
    b = bars(["2024-03-08 09:31", "2024-03-11 09:30"])           # 09:31 sa prekrýva, rovnaký obsah
    b.loc[1, ["open", "high", "low", "close"]] = [100.0, 100.05, 99.95, 100.0]
    b["dt"] = ["2024-03-08 09:31:00-05:00", "2024-03-11 09:30:00-04:00"]   # po zmene času -04:00
    b.loc[0, ["open", "high", "low", "close"]] = a.loc[1, ["o", "h", "l", "c"]].to_numpy()
    b.to_csv(tmp_path / "NVDA_patch.csv.gz", index=False)

    src = find_sources([tmp_path])
    assert list(src) == ["NVDA"] and len(src["NVDA"]) == 2
    st = ImportStats()
    df = load_ibkr_frame(src["NVDA"], stats=st)
    assert st.files == 2 and st.rows_in == 4 and st.dropped_dup == 1 and st.dup_conflicts == 0
    assert [f"{d:%m-%d %H:%M}" for d in df["date"]] == ["03-08 14:30", "03-08 14:31", "03-11 13:30"]


def test_parquet_ma_prednost_pred_rovnakym_csv(tmp_path):
    merged_parquet(tmp_path, "AAPL", ["2024-01-02 09:30"])
    (tmp_path / "AAPL_m1_2019_20261003.csv.gz").write_bytes(b"")
    (tmp_path / "README_merged.md").write_text("x", encoding="utf-8")
    assert [f.name for f in find_sources([tmp_path])["AAPL"]] == ["AAPL_m1_2019_20261003.parquet"]


def test_vypchavka_s_objemom_0_von_zle_ohlc_von_hlasenia(tmp_path):
    times = ["2024-01-02 09:30", "2024-01-02 09:31", "2024-01-02 09:32", "2024-01-02 16:05"]
    df = bars(times)
    df.loc[1, ["open", "high", "low", "close", "volume"]] = [100.0, 100.0, 100.0, 100.0, 0.0]  # vypchávka
    df.loc[2, "high"] = 90.0                                                                    # high < low
    df.loc[3, "close"] = 100.035                                                                # mimo ticku
    df.loc[3, "high"] = 101.0
    df["dt"] = pd.to_datetime(df["dt"]).dt.tz_localize("America/New_York")
    p = tmp_path / "TSLA_x.parquet"
    df.to_parquet(p)
    st = ImportStats()
    out = load_ibkr_frame([p], stats=st)
    assert st.dropped_padding == 1 and st.dropped_bad == 1 and st.rows_out == 2
    assert st.outside_rth == 1 and st.off_tick == 1 and st.days == 1
    assert len(out) == 2


def test_neupraveny_split_sa_nahlasi(tmp_path):
    p1 = merged_parquet(tmp_path, "AAPL", ["2020-08-28 09:30"], close=500.0)
    p2 = tmp_path / "AAPL_b.parquet"
    d = bars(["2020-08-31 09:30"], close=125.0)
    d["dt"] = pd.to_datetime(d["dt"]).dt.tz_localize("America/New_York")
    d.to_parquet(p2)
    st = ImportStats()
    load_ibkr_frame([p1, p2], stats=st)
    assert st.max_gap[0] == "2020-08-31" and st.max_gap[1] == pytest.approx(0.75)
    assert any("split" in n for n in st.notes)


def test_cli_zapise_roky_do_archivu_ibkr(tmp_path, capsys):
    src = tmp_path / "src"
    src.mkdir()
    merged_parquet(src, "MSFT", ["2023-12-29 15:59", "2024-01-02 09:30"])
    archive = tmp_path / "archive"
    assert main([str(src), "--archive", str(archive), "--no-merge"]) == 0
    out = sorted(p.name for p in (archive / "ibkr" / "futures").iterdir())
    assert out == ["MSFT_USD-1m.2023.feather", "MSFT_USD-1m.2024.feather"]
    y = pd.read_feather(archive / "ibkr" / "futures" / "MSFT_USD-1m.2024.feather")
    assert f"{y['date'].iloc[0]:%Y-%m-%d %H:%M}" == "2024-01-02 14:30"


def test_cli_odmietne_neznamy_symbol(tmp_path):
    merged_parquet(tmp_path, "XYZQ", ["2024-01-02 09:30"])
    err = []

    class E:
        def write(self, s):
            err.append(s)

    assert main([str(tmp_path), "--no-merge", "--archive", str(tmp_path / "a")], stderr=E()) == 1
    assert "instruments_ibkr.json" in "".join(err)
