"""Delenie sviečok na ročné súbory.

Zmysel celého nástroja je, že rok, ktorý sa už neminul, sa v gite objaví raz
a nikdy sa nezmení. Preto sa tu testuje hlavne dvoje: že delenie je **bezstratové**
a že `split` **neprepisuje** roky, ktoré sa nezmenili — inak by git videl nový blob
aj tam, kde sa nič nestalo, a celá úspora by zmizla.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")

from ibs.tools import data_archive as da


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    data, archive = tmp_path / "data", tmp_path / "archive"
    data.mkdir()
    monkeypatch.setattr(da, "DATA", data)
    monkeypatch.setattr(da, "ARCHIVE", archive)
    return data, archive


def _frame(start: str, periods: int, freq: str = "1min") -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    return pd.DataFrame(
        {
            "date": idx,
            "open": range(periods),
            "high": range(periods),
            "low": range(periods),
            "close": range(periods),
            "volume": [1.0] * periods,
        }
    ).astype({"date": "datetime64[ms, UTC]"})


def _write(path, df):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_feather(path)


def test_rozdeli_podla_rokov(dirs):
    data, archive = dirs
    # 3 dni na prelome roka -> dva rocne subory
    _write(data / "ex" / "PAIR-1m.feather", _frame("2024-12-31 23:00", 180))
    da.split(verbose=False)
    names = sorted(p.name for p in archive.rglob("*.feather"))
    assert names == ["PAIR-1m.2024.feather", "PAIR-1m.2025.feather"]


def test_delenie_je_bezstratove(dirs):
    data, _ = dirs
    src = data / "ex" / "PAIR-1m.feather"
    before = _frame("2024-12-31 22:00", 500)
    _write(src, before)

    da.split(verbose=False)
    src.unlink()
    da.merge(verbose=False)

    assert pd.read_feather(src).equals(before)


def test_zachova_strukturu_priecinkov(dirs):
    data, archive = dirs
    _write(data / "binance" / "futures" / "P-5m-futures.feather", _frame("2025-01-01", 10, "5min"))
    da.split(verbose=False)
    assert (archive / "binance" / "futures" / "P-5m-futures.2025.feather").exists()


def test_nezmeneny_rok_sa_neprepise(dirs):
    """Toto je celá pointa — inak by git dostal nový blob aj pre starý rok."""
    data, archive = dirs
    src = data / "ex" / "PAIR-1m.feather"
    _write(src, _frame("2024-06-01", 100))
    da.split(verbose=False)

    old = archive / "ex" / "PAIR-1m.2024.feather"
    stamp = old.stat().st_mtime_ns

    written = da.split(verbose=False)
    assert written == []
    assert old.stat().st_mtime_ns == stamp


def test_novy_rok_pribudne_a_stary_ostane(dirs):
    data, archive = dirs
    src = data / "ex" / "PAIR-1m.feather"
    _write(src, _frame("2024-06-01", 100))
    da.split(verbose=False)
    stamp = (archive / "ex" / "PAIR-1m.2024.feather").stat().st_mtime_ns

    # dotiahnu sa data aj za dalsi rok
    _write(src, pd.concat([_frame("2024-06-01", 100), _frame("2025-06-01", 50)], ignore_index=True))
    written = da.split(verbose=False)

    assert [p.name for p in written] == ["PAIR-1m.2025.feather"]
    assert (archive / "ex" / "PAIR-1m.2024.feather").stat().st_mtime_ns == stamp


def test_merge_zoradi_a_odstrani_duplicity(dirs):
    data, archive = dirs
    # rocne subory zamerne v zlom poradi a s prekryvom
    _write(archive / "ex" / "P-1m.2025.feather", _frame("2025-01-01", 10))
    _write(archive / "ex" / "P-1m.2024.feather", _frame("2024-12-31 23:55", 10))
    da.merge(verbose=False)

    out = pd.read_feather(data / "ex" / "P-1m.feather")
    assert out["date"].is_monotonic_increasing
    assert not out["date"].duplicated().any()


def test_prazdny_subor_sa_preskoci(dirs):
    data, archive = dirs
    _write(data / "ex" / "P-1m.feather", _frame("2025-01-01", 0))
    da.split(verbose=False)
    assert list(archive.rglob("*.feather")) == []
