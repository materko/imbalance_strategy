"""Čítanie feather v C# (`csharp/TradeBot.Backtest/Feather.cs`) musí dať bit po bite to, čo pyarrow.

Natívny backtest v C# číta sviečky priamo z `data/` a `data_archive/` — keby sa čítač v čomkoľvek
rozišiel s pyarrow (jednotka času, null, LZ4 blok cez hranicu), C# beh by počítal nad inými
dátami než Python emulátor a parita by nič neznamenala.
"""

from __future__ import annotations

import glob

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.feather as feather
import pytest

from tradebot.core.paths import REPO


@pytest.fixture(scope="module")
def cs():
    from tradebot.adapters.csharp import bridge

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    from TradeBot.Backtest import Feather

    return Feather


def _np(arr, dtype) -> np.ndarray:
    """System.Double[] / Int64[] -> numpy bez prechodu cez Python zoznam (milióny prvkov)."""
    from System import IntPtr
    from System.Runtime.InteropServices import Marshal

    out = np.empty(arr.Length, dtype=dtype)
    if arr.Length:
        Marshal.Copy(arr, 0, IntPtr(int(out.ctypes.data)), arr.Length)
    return out


def _expected_ms(col: pa.ChunkedArray) -> np.ndarray:
    unit = col.type.unit
    raw = pc.cast(col, pa.int64()).to_numpy()
    if unit == "s":
        return raw * 1000
    return np.floor_divide(raw, {"ms": 1, "us": 1000, "ns": 1_000_000}[unit])


def _assert_same(table, path: str) -> None:
    """Každý stĺpec zo súboru proti pyarrow — hodnoty, platnosť aj presné bity doublov."""
    want = feather.read_table(path)
    assert table.Rows == want.num_rows
    for i, field in enumerate(want.schema):
        col = table.Columns[i]
        assert col.Name == field.name
        arr = want.column(i)
        t = field.type
        if pa.types.is_string(t) or pa.types.is_large_string(t) or pa.types.is_binary(t):
            assert str(col.Kind) == "Skipped"
            continue
        valid = ~arr.is_null().to_numpy(zero_copy_only=False)
        if col.Valid is not None:
            assert np.array_equal(np.array(list(col.Valid), dtype=bool), valid), field.name
        else:
            assert valid.all(), field.name
        if pa.types.is_floating(t):
            got = _np(col.Doubles, np.float64)
            exp = arr.to_numpy(zero_copy_only=False).astype(np.float64)
            assert np.array_equal(got.view(np.int64)[valid], exp.view(np.int64)[valid]), field.name
            assert np.isnan(got[~valid]).all()
        elif pa.types.is_timestamp(t):
            got = _np(table.TimesMs(field.name), np.int64)
            assert np.array_equal(got[valid], _expected_ms(arr)[valid]), field.name
        else:
            got = _np(col.Longs, np.int64)
            exp = pc.cast(arr, pa.int64()).to_numpy(zero_copy_only=False)
            assert np.array_equal(got[valid], exp[valid].astype(np.int64)), field.name
            assert (got[~valid] == 0).all()


def _synthetic(n: int = 70_000) -> pa.Table:
    rng = np.random.default_rng(7)
    t0 = 1_609_459_200_000
    nulls = rng.random(n) < 0.05
    return pa.table({
        "date": pa.array(t0 + 60_000 * np.arange(n), pa.timestamp("ms", tz="UTC")),
        "date_ns": pa.array((t0 + 60_000 * np.arange(n)) * 1_000_000 + 999_999, pa.timestamp("ns", tz="UTC")),
        "pred_s": pa.array(np.arange(n) - 5, pa.timestamp("s")),
        "close": rng.normal(40_000, 500, n),                      # náhodné = LZ4 skoro nekomprimuje
        "flat": np.repeat(np.arange(n // 1000 + 1, dtype=np.float64), 1000)[:n],  # veľké zhody
        "f32": rng.random(n).astype(np.float32),
        "with_null": pa.array(rng.random(n), mask=nulls),
        "i8": pa.array(rng.integers(-128, 127, n), pa.int8()),
        "u16": pa.array(rng.integers(0, 65535, n), pa.uint16()),
        "i32_null": pa.array(rng.integers(-2**31, 2**31 - 1, n), pa.int32(), mask=nulls),
        "u32": pa.array(rng.integers(0, 2**32 - 1, n, dtype=np.uint64), pa.uint32()),
        "i64": rng.integers(-2**62, 2**62, n),
        "flag": pa.array(rng.random(n) < 0.3),
        "text": pa.array([f"r{i}" for i in range(n)], pa.large_string()),
        "volume": rng.random(n) * 10,
    })


@pytest.mark.parametrize("compression", ["lz4", "uncompressed"])
def test_synthetic_columns(cs, tmp_path, compression):
    path = str(tmp_path / f"t_{compression}.feather")
    feather.write_feather(_synthetic(), path, compression=compression, chunksize=25_000)  # 3 record batche
    _assert_same(cs.Read(path), path)


def test_empty_table(cs, tmp_path):
    path = str(tmp_path / "empty.feather")
    feather.write_feather(_synthetic(10).slice(0, 0), path)
    assert cs.Read(path).Rows == 0


def test_zstd_is_refused_clearly(cs, tmp_path):
    path = str(tmp_path / "z.feather")
    feather.write_feather(_synthetic(100), path, compression="zstd")
    with pytest.raises(Exception, match="ZSTD"):
        cs.Read(path)


def _archive_samples() -> list[str]:
    """Jeden reálny súbor z každého zdroja (jednotky času ms/us/ns, 1m s viac blokmi LZ4)."""
    out: dict[str, str] = {}
    for root in ("data_archive/tester", "data/tester"):
        for path in sorted(glob.glob(str(REPO / root / "*" / "*" / "*-1m*.feather"))):
            out.setdefault(path.replace("\\", "/").split("/")[-3], path)
    return sorted(out.values())


@pytest.mark.parametrize("path", _archive_samples() or [pytest.param(None, marks=pytest.mark.skip("bez dát"))])
def test_real_candles(cs, path):
    _assert_same(cs.Read(path), path)
    c = cs.ReadCandles(path)
    df = feather.read_feather(path)
    want_ms = df["date"].astype("datetime64[ms, UTC]").astype("int64").to_numpy()
    assert np.array_equal(_np(c.Time, np.int64), want_ms)
    for name, arr in (("open", c.Open), ("high", c.High), ("low", c.Low), ("close", c.Close), ("volume", c.Volume)):
        assert np.array_equal(_np(arr, np.float64), df[name].to_numpy(np.float64), equal_nan=True), name
