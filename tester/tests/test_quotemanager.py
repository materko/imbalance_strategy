"""ASCII export pre QuoteManager zo skladu 1m sviečok — `tester.quotemanager`.

Pointa je, že v MultiCharts je presne to, na čom bežali backtesty: CSV sa robí z toho
istého feather súboru, aký číta Freqtrade aj emulátor, nie druhou cestou zo surového
exportu.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core.types import INSTRUMENTS
from tester import quotemanager as qm

INST = INSTRUMENTS["nas100_dukascopy"]


def m1(rows: list[tuple[str, float, float, float, float, float]]):
    return pd.DataFrame({
        "date": pd.to_datetime([r[0] for r in rows], utc=True),
        "open": [r[1] for r in rows], "high": [r[2] for r in rows],
        "low": [r[3] for r in rows], "close": [r[4] for r in rows],
        "volume": [r[5] for r in rows],
    })


def lines(dst: Path) -> list[str]:
    return dst.read_text(encoding="utf-8").splitlines()


def test_hlavicka_a_cas_zatvorenia(tmp_path):
    dst = tmp_path / "x.csv"
    qm.write_csv(m1([("2025-01-06 23:59:00", 1, 2, 0.5, 1.5, 0.03)]), dst)

    assert lines(dst)[0] == "Date,Time,Open,High,Low,Close,Volume"
    assert lines(dst)[1] == "2025-01-07,00:00:00,1,2,0.5,1.5,3"


def test_stamp_open_necha_cas_zo_skladu(tmp_path):
    dst = tmp_path / "x.csv"
    qm.write_csv(m1([("2025-01-06 23:59:00", 1, 2, 0.5, 1.5, 0)]), dst, stamp="open")
    assert lines(dst)[1].startswith("2025-01-06,23:59:00,")


def test_objem_je_cele_cislo_a_da_sa_skalovat(tmp_path):
    """QuoteManager odmietne „0.01" — objem sa zaokrúhli, `volume_scale` ho najprv vynásobí."""
    df = m1([("2025-01-06 10:00:00", 1, 2, 0.5, 1.5, 0.04)])
    qm.write_csv(df, tmp_path / "a.csv", volume_scale=1.0)
    qm.write_csv(df, tmp_path / "b.csv", volume_scale=100.0)
    qm.write_csv(m1([("2025-01-06 10:00:00", 1, 2, 0.5, 1.5, 1029361390.7)]), tmp_path / "c.csv",
                 volume_scale=1.0)

    assert lines(tmp_path / "a.csv")[1].endswith(",0")
    assert lines(tmp_path / "b.csv")[1].endswith(",4")
    assert lines(tmp_path / "c.csv")[1].endswith(",1029361391")


def test_datum_vo_vlastnom_formate(tmp_path):
    dst = tmp_path / "x.csv"
    qm.write_csv(m1([("2025-01-06 10:00:00", 1, 2, 0.5, 1.5, 0)]), dst, date_format="%m/%d/%Y")
    assert lines(dst)[1].startswith("01/06/2025,10:01:00,")


def test_cislo_bez_exponentu_a_bez_zbytocnych_nul():
    assert qm.num(24271.599) == "24271.599"
    assert qm.num(0.0) == "0"
    assert qm.num(0.00001) == "1e-05" or qm.num(0.00001) == "1.0e-05" or "e" in qm.num(0.00001)


def test_neznamy_stamp_sa_odmietne(tmp_path):
    with pytest.raises(ValueError, match="stamp"):
        qm.write_csv(m1([("2025-01-06 10:00:00", 1, 2, 0.5, 1.5, 0)]), tmp_path / "x.csv",
                     stamp="middle")


# --------------------------------------------------------------------------- #
# export zo skladu
# --------------------------------------------------------------------------- #


@pytest.fixture
def sklad(tmp_path, monkeypatch):
    """1m sviečky NAS100 v sklade a prázdny adresár na exporty."""
    from tester import engines

    src = tmp_path / "tester" / "dukascopy" / "futures"
    src.mkdir(parents=True)
    m1([(f"2025-01-06 10:0{i}:00", 1, 2, 0.5, 1.5, 1.0) for i in range(5)]).to_feather(
        src / "NAS100_USD-1m.feather")
    monkeypatch.setattr(engines, "TESTER_DATA", tmp_path / "tester")
    monkeypatch.setattr(qm, "QUOTEMANAGER_DATA", tmp_path / "quotemanager")
    return tmp_path


def test_export_ide_vedla_ostatnych_exportov_zdroja(sklad):
    out = qm.export(INST, verbose=False)
    assert out == sklad / "quotemanager" / "dukascopy" / "NAS100_USD-1m.csv"
    assert len(lines(out)) == 6                      # hlavička + 5 barov


def test_hotovy_export_sa_neprepise_bez_force(sklad):
    first = qm.export(INST, verbose=False)
    first.write_text("rucna zmena\n", encoding="utf-8")

    assert qm.export(INST, verbose=False) is None
    assert first.read_text(encoding="utf-8") == "rucna zmena\n"
    assert qm.export(INST, verbose=False, force=True) is not None


def test_bez_1m_sviecok_sa_nic_nevyrobi(tmp_path, monkeypatch):
    from tester import engines

    monkeypatch.setattr(engines, "TESTER_DATA", tmp_path / "prazdne")
    monkeypatch.setattr(qm, "QUOTEMANAGER_DATA", tmp_path / "quotemanager")
    assert qm.export(INST, verbose=False) is None
    assert qm.targets("all") == {}


def test_rozsah_multicharts_berie_len_dukascopy_symboly(sklad):
    assert list(qm.targets("multicharts")) == ["nas100_dukascopy"]
    assert qm.targets("off") == {}
    with pytest.raises(ValueError, match="rozsah"):
        qm.targets("nieco")


def test_ensure_doplni_co_chyba_a_druhy_raz_uz_nic(sklad):
    assert [p.name for p in qm.ensure("multicharts", verbose=False)] == ["NAS100_USD-1m.csv"]
    assert qm.ensure("multicharts", verbose=False) == []
    assert qm.missing("multicharts") == []


def test_cli_symbol_a_vlastny_vystup(sklad, capsys):
    out = sklad / "inde" / "nas.csv"
    assert qm.main(["--symbol", "NAS100", "--out", str(out)]) == 0
    assert out.exists()
    assert qm.main(["--symbol", "NECO"]) == 1
