"""Import Dukascopy CSV — čistenie (vypchávka, mierka, okno), 1m feather do archívu.

Importér má jedinú úlohu: zo surového exportu spraviť čisté 1m sviečky a rozdeliť ich po
rokoch do `data_archive/`. Vyššie timeframy ani ASCII pre QuoteManager tu už nevznikajú —
tie si Tester vyrobí z archívu (`tester.timeframes`, `tester.quotemanager`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tester.dukas_import import ImportStats, load_dukas_frame, main, scale_reference, store

HEADER = "dt,o,h,l,c,vol\n"


def raw(tmp_path: Path, *items: str, name: str = "X_M1.csv") -> Path:
    src = tmp_path / name
    src.write_text(HEADER + "".join(i + "\n" for i in items), encoding="utf-8")
    return src


def frame(tmp_path: Path, *items: str, **kw):
    st = ImportStats()
    df = load_dukas_frame(raw(tmp_path, *items), stats=st, **kw)
    return df, st


# --------------------------------------------------------------------------- #
# vypchávka a okno
# --------------------------------------------------------------------------- #


def test_plochy_bar_s_cenou_predchadzajuceho_uzavretia_vypadne(tmp_path):
    df, st = frame(
        tmp_path,
        "2025-01-03 21:59:00,100,101,99,100.5,10",
        "2025-01-03 22:00:00,100.5,100.5,100.5,100.5,0",  # vypchávka
        "2025-01-03 22:01:00,100.5,100.5,100.5,100.5,0",  # vypchávka
        "2025-01-05 22:00:00,100.5,100.5,100.5,100.5,0",  # vypchávka aj po víkende
        "2025-01-05 22:01:00,100.7,100.7,100.7,100.7,0",  # plochý, ale cena sa pohla -> ostáva
        "2025-01-05 22:02:00,100.7,100.9,100.6,100.8,5",
    )
    assert st.rows_in == 6 and st.dropped_padding == 3 and st.rows_out == 3
    assert [f"{t:%H:%M}" for t in df["date"]] == ["21:59", "22:01", "22:02"]


def test_cas_baru_ostava_casom_otvorenia(tmp_path):
    """Posun na čas zatvorenia je konvencia MultiCharts a rieši ho až export CSV."""
    df, _ = frame(tmp_path, "2025-01-06 23:59:00,1,2,0.5,1.5,3")
    assert f"{df['date'].iloc[0]:%Y-%m-%d %H:%M}" == "2025-01-06 23:59"


def test_keep_padding_necha_vsetko(tmp_path):
    df, st = frame(tmp_path, "2025-01-06 00:00:00,1,1,1,1,0", "2025-01-06 00:01:00,1,1,1,1,0",
                   drop_padding=False)
    assert len(df) == 2 and st.dropped_padding == 0


def test_from_to_orezu_obdobie_vratane_hranic(tmp_path):
    df, st = frame(
        tmp_path,
        "2025-01-05 23:59:00,1,2,0.5,1.5,0",
        "2025-01-06 00:00:00,1,2,0.5,1.6,0",
        "2025-01-07 23:59:00,1,2,0.5,1.7,0",
        "2025-01-08 00:00:00,1,2,0.5,1.8,0",
        date_from="2025-01-06", date_to="2025-01-07",
    )
    assert [f"{t:%Y-%m-%d}" for t in df["date"]] == ["2025-01-06", "2025-01-07"]
    assert st.dropped_range == 2
    assert st.first == "2025-01-06 00:00" and st.last == "2025-01-07 23:59"


def test_prvy_bar_okna_nie_je_plochy_zvysok_vikendu(tmp_path):
    """Vypchávka sa vyhodnocuje pred orezaním — inak by prvý bar okna bol plochý zvyšok."""
    df, _ = frame(
        tmp_path,
        "2025-01-05 23:58:00,1,2,0.5,1.5,0",
        "2025-01-05 23:59:00,1.5,1.5,1.5,1.5,0",
        "2025-01-06 00:00:00,1.5,1.5,1.5,1.5,0",  # stále vypchávka, hoci je už v okne
        "2025-01-06 00:01:00,1.5,1.6,1.4,1.55,2",
        date_from="2025-01-06",
    )
    assert len(df) == 1 and f"{df['date'].iloc[0]:%H:%M}" == "00:01"


# --------------------------------------------------------------------------- #
# mierka
# --------------------------------------------------------------------------- #

SCALED = (
    "2015-01-05 00:00:00,2045886,2047065,2045851,2047065,0",  # ×1000
    "2015-01-05 00:01:00,2045.5,2046.4,2045.5,2046.1,0",
    "2015-01-05 00:02:00,2044.5,2046.4,2044.5,2046.3,0",
    "2015-01-05 00:03:00,2.0445,2.0464,2.0445,2.0463,0",  # ÷1000
)


def test_referencia_je_horny_median():
    assert scale_reference([2046.1, 2047065.0, 2046.3, 2.0463]) == 2046.3


def test_ina_mierka_sa_nahlasi_a_bez_fix_scale_ostane(tmp_path):
    df, st = frame(tmp_path, *SCALED)
    assert st.scale_outliers == 2 and st.scale_fixed == 0 and st.outlier_days == ["2015-01-05"]
    assert df["close"].iloc[0] == 2047065.0


def test_fix_scale_deli_a_nasobi_tisicom(tmp_path):
    """Opravuje sa to, čo sa ukladá — predtým sa mierka čistila len v ASCII výstupe."""
    df, st = frame(tmp_path, *SCALED, fix_scale=True)
    assert st.scale_fixed == 2
    assert list(df.iloc[0][["open", "high", "low", "close"]]) == [2045.886, 2047.065, 2045.851, 2047.065]
    assert df["close"].iloc[3] == pytest.approx(2046.3)


# --------------------------------------------------------------------------- #
# archív a CLI
# --------------------------------------------------------------------------- #


def test_store_rozdeli_po_rokoch_a_zlozi_pracovny_subor(tmp_path):
    """Archív je zrkadlo skladu: `data_archive/tester/<zdroj>/<trh>/` ↔ `data/tester/…`."""
    df, _ = frame(
        tmp_path,
        "2024-12-31 23:59:00,1,2,0.5,1.5,1",
        "2025-01-01 00:00:00,1.5,2,1,1.9,1",
        "2025-01-01 00:01:00,1.9,2,1,1.7,1",
    )
    work = tmp_path / "data" / "tester"
    archive = tmp_path / "archive" / "tester"
    inst = INSTRUMENTS["nas100_dukascopy"]

    files = store(df, inst, archive=archive, verbose=False,
                  roots=((tmp_path / "archive", tmp_path / "data"),))

    assert [f.name for f in files] == ["NAS100_USD-1m.2024.feather", "NAS100_USD-1m.2025.feather"]
    assert files[0].parent == archive / "dukascopy" / "futures"
    zlozene = work / "dukascopy" / "futures" / "NAS100_USD-1m.feather"
    assert len(pd.read_feather(zlozene)) == 3


def test_cli_vrati_2_pri_neopravenej_mierke_a_0_po_oprave(tmp_path, capsys):
    src = raw(tmp_path, *SCALED)
    args = [str(src), "--symbol", "NAS100", "--archive", str(tmp_path / "archive"), "--no-merge"]

    assert main(args) == 2
    assert (tmp_path / "archive" / "dukascopy" / "futures" / "NAS100_USD-1m.2015.feather").exists()

    assert main([*args, "--fix-scale"]) == 0
    err = capsys.readouterr().err
    assert "riadky inej mierky: 2 opravene" in err
    assert "python -m tester.quotemanager" in err     # CSV robí iný nástroj


def test_cli_odmietne_prazdny_vysledok(tmp_path, capsys):
    src = raw(tmp_path, "2025-01-06 10:00:00,1,2,0.5,1.5,0")
    assert main([str(src), "--symbol", "NAS100", "--from", "2030-01-01",
                 "--archive", str(tmp_path / "archive")]) == 1
    assert "neostal ziadny bar" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# NAS100 inštrument a profil
# --------------------------------------------------------------------------- #


def test_nas100_profil_sedi_s_mnq_v_cenovych_bodoch():
    cfg, inst = load_profile("docs/profily_archiv/ibs/nas100_dukas_3m.json")
    assert inst.symbol == "NAS100/USD" and inst.venue == "multicharts"
    assert cfg.tickDollarValue == pytest.approx(inst.tick_dollar_value)


def test_archiv_je_zrkadlom_skladu_sviecok():
    """Import píše do `data_archive/tester/`, nie o úroveň vyššie.

    Regresia: importér písal do `data_archive/<zdroj>/`, kam sa `merge` (ktorý mapuje
    `data_archive/` na `data/`) nikdy nepozrel — dáta boli v archíve, ale Tester ich nevidel.
    """
    import inspect

    from tradebot.core.paths import DATA_ARCHIVE, TESTER_ARCHIVE, TESTER_DATA
    from tester import dukas_import

    assert TESTER_ARCHIVE == DATA_ARCHIVE / TESTER_DATA.name
    for func in (dukas_import.store, dukas_import.write_years):
        assert inspect.signature(func).parameters["archive"].default == TESTER_ARCHIVE, func.__name__
