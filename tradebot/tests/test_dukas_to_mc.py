"""Prevod Dukascopy CSV na ASCII pre MultiCharts — vypchávka, čas baru, mierka, NAS100 profil."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tradebot.tools.dukas_to_mc import ConvertStats, convert, convert_lines, main, scale_reference

HEADER = "dt,o,h,l,c,vol\n"


def rows(*items: str) -> list[str]:
    return [HEADER, *(i + "\n" for i in items)]


def out(lines, **kw) -> tuple[list[str], ConvertStats]:
    st = ConvertStats()
    result = list(convert_lines(lines, reference=kw.pop("reference", None), stats=st, **kw))
    return result, st


# --------------------------------------------------------------------------- #
# vypchávka a čas baru
# --------------------------------------------------------------------------- #


def test_plochy_bar_s_cenou_predchadzajuceho_uzavretia_vypadne():
    lines = rows(
        "2025-01-03 21:59:00,100,101,99,100.5,10",
        "2025-01-03 22:00:00,100.5,100.5,100.5,100.5,0",  # vypchávka
        "2025-01-03 22:01:00,100.5,100.5,100.5,100.5,0",  # vypchávka
        "2025-01-05 22:00:00,100.5,100.5,100.5,100.5,0",  # vypchávka aj po víkende
        "2025-01-05 22:01:00,100.7,100.7,100.7,100.7,0",  # plochý, ale cena sa pohla -> ostáva
        "2025-01-05 22:02:00,100.7,100.9,100.6,100.8,5",
    )
    result, st = out(lines)
    assert st.rows_in == 6 and st.dropped_padding == 3 and st.rows_out == 3
    assert [r.split(",")[1] for r in result] == ["22:00:00", "22:02:00", "22:03:00"]


def test_cas_baru_sa_posunie_na_zatvorenie_a_open_ho_necha():
    lines = rows("2025-01-06 23:59:00,1,2,0.5,1.5,3")
    closed, _ = out(lines)
    assert closed == ["2025-01-07,00:00:00,1,2,0.5,1.5,3"]
    opened, _ = out(lines, stamp="open")
    assert opened == ["2025-01-06,23:59:00,1,2,0.5,1.5,3"]


def test_keep_padding_necha_vsetko_a_hlavicka_sa_preskoci():
    lines = rows(
        "2025-01-06 00:00:00,1,1,1,1,0",
        "2025-01-06 00:01:00,1,1,1,1,0",
    )
    result, st = out(lines, drop_padding=False)
    assert len(result) == 2 and st.dropped_padding == 0


def test_from_to_orezu_obdobie_vratane_hranic():
    lines = rows(
        "2025-01-05 23:59:00,1,2,0.5,1.5,0",
        "2025-01-06 00:00:00,1,2,0.5,1.6,0",
        "2025-01-07 23:59:00,1,2,0.5,1.7,0",
        "2025-01-08 00:00:00,1,2,0.5,1.8,0",
    )
    result, st = out(lines, date_from="2025-01-06", date_to="2025-01-07", stamp="open")
    assert [r.split(",")[0] for r in result] == ["2025-01-06", "2025-01-07"]
    assert st.dropped_range == 2 and st.first == "2025-01-06 00:00:00" and st.last == "2025-01-07 23:59:00"


def test_prvy_bar_okna_nie_je_plochy_zvysok_vikendu():
    """Vypchávka sa vyhodnocuje pred orezaním — inak by prvý bar okna bol plochý zvyšok."""
    lines = rows(
        "2025-01-05 23:58:00,1,2,0.5,1.5,0",
        "2025-01-05 23:59:00,1.5,1.5,1.5,1.5,0",
        "2025-01-06 00:00:00,1.5,1.5,1.5,1.5,0",  # stále vypchávka, hoci je už v okne
        "2025-01-06 00:01:00,1.5,1.6,1.4,1.55,2",
    )
    result, _ = out(lines, date_from="2025-01-06", stamp="open")
    assert result == ["2025-01-06,00:01:00,1.5,1.6,1.4,1.55,2"]


def test_objem_je_cele_cislo_a_da_sa_skalovat():
    """QuoteManager odmietne "0.01" — objem sa zaokrúhli, s --volume-scale sa najprv vynásobí."""
    line = rows("2025-01-06 10:00:00,1,2,0.5,1.5,0.04")
    assert out(line)[0][0].endswith(",0")
    assert out(line, volume_scale=100)[0][0].endswith(",4")
    assert out(rows("2025-01-06 10:00:00,1,2,0.5,1.5,1029361390.7"))[0][0].endswith(",1029361391")


def test_datum_vo_vlastnom_formate():
    result, _ = out(rows("2025-01-06 10:00:00,1,2,0.5,1.5,0"), date_format="%m/%d/%Y")
    assert result[0].startswith("01/06/2025,10:01:00,")


# --------------------------------------------------------------------------- #
# mierka
# --------------------------------------------------------------------------- #

SCALED = rows(
    "2015-01-05 00:00:00,2045886,2047065,2045851,2047065,0",  # ×1000
    "2015-01-05 00:01:00,2045.5,2046.4,2045.5,2046.1,0",
    "2015-01-05 00:02:00,2044.5,2046.4,2044.5,2046.3,0",
    "2015-01-05 00:03:00,2.0445,2.0464,2.0445,2.0463,0",  # ÷1000
)


def test_referencia_je_median_vzorky():
    assert scale_reference(SCALED, step=1) == 2046.3  # horný medián zo 4 vzoriek


def test_ina_mierka_sa_nahlasi_a_bez_fix_scale_ostane():
    result, st = out(SCALED, reference=2046.1)
    assert st.scale_outliers == 2 and st.scale_fixed == 0 and st.outlier_days == ["2015-01-05"]
    assert result[0].endswith(",2045886,2047065,2045851,2047065,0")


def test_fix_scale_deli_a_nasobi_tisicom():
    result, st = out(SCALED, reference=2046.1, fix_scale=True)
    assert st.scale_fixed == 2
    assert result[0].split(",")[2:6] == ["2045.886", "2047.065", "2045.851", "2047.065"]
    assert result[3].split(",")[5] == "2046.3"


# --------------------------------------------------------------------------- #
# súbory a CLI
# --------------------------------------------------------------------------- #


def test_convert_zapise_hlavicku_a_cli_vrati_2_pri_neopravenej_mierke(tmp_path: Path, capsys):
    src = tmp_path / "X_M1.csv"
    src.write_text("".join(SCALED), encoding="utf-8")
    st = convert(src, tmp_path / "x_mc.csv")
    text = (tmp_path / "x_mc.csv").read_text(encoding="utf-8").splitlines()
    assert text[0] == "Date,Time,Open,High,Low,Close,Volume" and len(text) == 5
    assert st.reference == 2046.3 and st.scale_outliers == 2

    assert main([str(src)]) == 2
    assert (tmp_path / "X_M1_mc.csv").exists()
    assert main([str(src), "--fix-scale", "--out", str(tmp_path / "ok.csv")]) == 0
    err = capsys.readouterr().err
    assert "riadky inej mierky: 2 opravene" in err


# --------------------------------------------------------------------------- #
# NAS100 inštrument a profil
# --------------------------------------------------------------------------- #


def test_nas100_profil_sedi_s_mnq_v_cenovych_bodoch():
    """Profil je odvodený z multicharts_mnq_3m: tie isté prahy v bodoch, tick polia prepočítané."""
    mnq_cfg, mnq = load_profile("multicharts_mnq_3m")
    cfg, inst = load_profile(Path("docs/profily_archiv/ibs/nas100_dukas_3m.json"))
    assert inst is INSTRUMENTS["nas100_dukascopy"]
    assert inst.has_real_volume is False and inst.tick_size == 0.01 and inst.point_value == 1.0

    for name in ("imbMaxDistTicks", "state2ConfirmTicks", "slBufferTicks"):
        mnq_price = getattr(mnq_cfg, name).value * mnq.tick_size
        assert getattr(cfg, name).unit == "abs" and getattr(cfg, name).value == pytest.approx(mnq_price)
    assert cfg.minImbSizePoints == mnq_cfg.minImbSizePoints
    assert cfg.tradeDirection == mnq_cfg.tradeDirection and cfg.enableTrailing is mnq_cfg.enableTrailing
    assert cfg.tickDollarValue == pytest.approx(inst.tick_dollar_value)

    warnings = cfg.check_instrument(inst)
    assert not [w for w in warnings if "tickDollarValue" in w or "useVolumeFilter" in w]
