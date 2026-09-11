"""Import Databento exportu (CME futures po kontraktoch) — spready von, front-month podľa
objemu, roll len dopredu, 1m feather po rokoch do archívu."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from tradebot.core.types import INSTRUMENTS
from tester.bento_import import (
    ImportStats, contract_order, degraded_days, front_month, load_bento_frame, main,
    resolve_symbol,
)

HEADER = "ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol\n"


def row(ts: str, symbol: str, close: float, volume: int) -> str:
    return f"{ts},33,1,1,{close},{close + 0.25},{close - 0.25},{close},{volume},{symbol}"


def raw(tmp_path: Path, *rows: str, name: str = "glbx.ohlcv-1m.csv") -> Path:
    src = tmp_path / name
    src.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return src


# --------------------------------------------------------------------------- #
# poradie kontraktov a symbol
# --------------------------------------------------------------------------- #


def test_poradie_kontraktov_je_rok_a_mesiac():
    assert contract_order("MNQM9") == (2019, 6)
    assert contract_order("MNQU6") == (2026, 9)
    assert contract_order("MNQH26") == (2026, 3)
    assert contract_order("MNQM9-MNQU9") is None      # spread nie je kontrakt
    assert contract_order("MNQU6") < contract_order("MNQZ6") < contract_order("MNQH7")


def test_mnq_je_v_registri_databento_ako_multicharts_trh_s_burzovym_objemom():
    key, inst = resolve_symbol("MNQ")
    assert key == "mnq_databento" and inst.symbol == "MNQ/USD"
    assert inst.venue == "multicharts" and inst.data_source == "databento"
    assert inst.tick_size == 0.25 and inst.point_value == 2.0 and inst.has_real_volume
    assert inst.cost_unit == "ticks" and inst.cost > 0
    assert resolve_symbol("mnq_databento") == (key, inst) and resolve_symbol("MNQ/USD") == (key, inst)
    assert resolve_symbol("NAS100") is None            # Dukascopy symbol sem nepatrí
    assert INSTRUMENTS[key].exchange_symbol == "MNQ"


# --------------------------------------------------------------------------- #
# front-month
# --------------------------------------------------------------------------- #


def test_spready_a_cudzie_korene_vypadnu_front_month_podla_objemu(tmp_path):
    src = raw(tmp_path,
              row("2026-06-12T13:30:00.000000000Z", "MNQM6", 20000.0, 900),   # piatok: M6 vedie
              row("2026-06-12T13:31:00.000000000Z", "MNQU6", 20050.0, 100),
              row("2026-06-12T13:32:00.000000000Z", "MNQM6-MNQU6", 50.0, 3),  # spread
              row("2026-06-12T13:33:00.000000000Z", "MESM6", 5000.0, 500),    # iný koreň
              row("2026-06-15T13:30:00.000000000Z", "MNQM6", 20010.0, 400),   # pondelok: U6 vedie
              row("2026-06-15T13:31:00.000000000Z", "MNQU6", 20060.0, 600),
              row("2026-06-16T13:30:00.000000000Z", "MNQM6", 20020.0, 700),   # utorok: M6 by viedol,
              row("2026-06-16T13:31:00.000000000Z", "MNQU6", 20070.0, 650))   # ale späť sa neroluje
    st = ImportStats()
    df = load_bento_frame(src, root="MNQ", stats=st)

    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert st.rows_in == 8 and st.spreads == 1 and st.other_roots == 1
    assert df["close"].tolist() == [20000.0, 20060.0, 20070.0]
    assert st.contracts == 2 and st.rolls == [("2026-06-12", "MNQM6"), ("2026-06-15", "MNQU6")]
    assert st.first == "2026-06-12 13:30" and st.last == "2026-06-16 13:31"
    assert str(df["date"].dt.tz) == "UTC"


def test_okno_from_to_oreze_pred_skladanim(tmp_path):
    src = raw(tmp_path,
              row("2026-06-12T13:30:00.000000000Z", "MNQM6", 20000.0, 900),
              row("2026-06-15T13:30:00.000000000Z", "MNQU6", 20060.0, 600))
    st = ImportStats()
    df = load_bento_frame(src, root="MNQ", date_from="2026-06-13", stats=st)
    assert len(df) == 1 and st.dropped_range == 1 and st.rolls == [("2026-06-15", "MNQU6")]


def test_poistka_zahodi_nezmyselny_bar_a_duplicitny_cas(tmp_path):
    src = raw(tmp_path,
              row("2026-06-12T13:30:00.000000000Z", "MNQM6", 20000.0, 900),
              "2026-06-12T13:31:00.000000000Z,33,1,1,20000,19990,20010,20000,5,MNQM6",   # high < low
              "2026-06-12T13:32:00.000000000Z,33,1,1,20000,20001,19999,20000,0,MNQM6",   # bez objemu
              row("2026-06-12T13:33:00.000000000Z", "MNQM6", 20003.0, 10),
              row("2026-06-12T13:33:00.000000000Z", "MNQM6", 20004.0, 11))               # ten istý čas
    st = ImportStats()
    df = load_bento_frame(src, root="MNQ", stats=st)
    assert st.dropped_bad == 2 and st.dropped_dup == 1
    assert df["close"].tolist() == [20000.0, 20004.0]


def test_front_month_prazdny_vstup():
    df = pd.DataFrame({"date": pd.Series([], dtype="datetime64[ns, UTC]"), "open": [], "high": [],
                       "low": [], "close": [], "volume": [], "symbol": pd.Series([], dtype="string")})
    assert front_month(df).empty


def test_degraded_dni_z_condition_json(tmp_path):
    src = raw(tmp_path, row("2026-06-12T13:30:00.000000000Z", "MNQM6", 20000.0, 900))
    (tmp_path / "condition.json").write_text(json.dumps([
        {"date": "2019-01-01", "condition": "degraded"},
        {"date": "2026-06-11", "condition": "available"},
        {"date": "2026-06-12", "condition": "degraded"},
    ]), encoding="utf-8")
    assert degraded_days(src) == ["2019-01-01", "2026-06-12"]
    assert degraded_days(src, date_from="2020-01-01") == ["2026-06-12"]
    (tmp_path / "inde").mkdir()
    assert degraded_days(tmp_path / "inde" / "nie.csv") == []   # bez condition.json vedľa


# --------------------------------------------------------------------------- #
# CLI: archív po rokoch, rolly vedľa, bez merge
# --------------------------------------------------------------------------- #


def test_cli_ulozi_rocne_feathery_a_rolly(tmp_path, capsys):
    src = raw(tmp_path,
              row("2025-12-15T13:30:00.000000000Z", "MNQZ5", 20000.0, 900),
              row("2026-01-05T13:30:00.000000000Z", "MNQH6", 20100.0, 900),
              row("2026-01-05T13:31:00.000000000Z", "MNQZ5-MNQH6", 100.0, 1))
    archive = tmp_path / "archiv"
    rc = main([str(src), "--symbol", "MNQ", "--archive", str(archive), "--no-merge"])
    assert rc == 0
    out = capsys.readouterr().err
    assert "MNQ_USD (mnq_databento)" in out and "vyhodene spready: 1" in out

    cielovy = archive / "databento" / "futures"
    assert sorted(p.name for p in cielovy.glob("*.feather")) == ["MNQ_USD-1m.2025.feather", "MNQ_USD-1m.2026.feather"]
    r2026 = pd.read_feather(cielovy / "MNQ_USD-1m.2026.feather")
    assert list(r2026.columns) == ["date", "open", "high", "low", "close", "volume"] and len(r2026) == 1
    rolls = json.loads((cielovy / "MNQ_USD-1m.rolls.json").read_text(encoding="utf-8"))
    assert rolls == [{"date": "2025-12-15", "contract": "MNQZ5"}, {"date": "2026-01-05", "contract": "MNQH6"}]


def test_cli_neznamy_symbol_a_chybajuci_zdroj(tmp_path, capsys):
    assert main([str(tmp_path / "nie.csv"), "--symbol", "MNQ"]) == 1
    src = raw(tmp_path, row("2026-06-12T13:30:00.000000000Z", "MNQM6", 20000.0, 900))
    assert main([str(src), "--symbol", "NAS100", "--archive", str(tmp_path / "a"), "--no-merge"]) == 1
    assert "instruments_databento.json" in capsys.readouterr().err
