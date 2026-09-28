"""`python -m tradebot.adapters.mt5 control …` — zápis a čítanie control súboru (docs/LIVE.md, fáza 2).

Common adresár MT5 je podstrčený cez `TRADEBOT_MT5_COMMON` (`find_common_files`), terminál netreba.
"""

from __future__ import annotations

import json

import pytest

from tradebot.adapters.mt5 import __main__ as mt5

INSTANCE = "mt5_1514750898-FTMO-Demo_US100.cash_1m_ibsnet"


@pytest.fixture
def common(tmp_path, monkeypatch):
    root = tmp_path / "Common" / "Files"
    root.mkdir(parents=True)
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(root))
    monkeypatch.delenv("TRADEBOT_MT5_DIR", raising=False)
    return root


def test_zapis_je_atomicky_a_polia_ostavaju(common):
    assert mt5.read_control(common, INSTANCE) is None
    data = mt5.write_control(common, INSTANCE, mode="paused", profile="golden_binance_btcusdt_3m", by="test")
    path = common / "TradeBot" / "control" / f"{INSTANCE}.json"
    assert path.is_file() and not path.with_suffix(".json.tmp").exists()   # tmp + os.replace, bez zvyšku
    assert json.loads(path.read_text(encoding="utf-8")) == data
    assert data["mode"] == "paused" and data["profile"] == "golden_binance_btcusdt_3m" and data["by"] == "test"
    assert isinstance(data["updated"], int) and data["updated"] > 1_700_000_000_000

    # len --mode: profil ostáva; len --profile: režim ostáva
    again = mt5.write_control(common, INSTANCE, mode="enabled")
    assert again["mode"] == "enabled" and again["profile"] == "golden_binance_btcusdt_3m"
    third = mt5.write_control(common, INSTANCE, profile="")
    assert third["mode"] == "enabled" and third["profile"] == ""
    assert mt5.read_control(common, INSTANCE) == third

    with pytest.raises(SystemExit):
        mt5.write_control(common, INSTANCE, mode="stop")
    assert mt5.read_control(common, INSTANCE) == third   # neplatný režim nič neprepísal


def test_cli_zapise_ukaze_a_vypise_zoznam(common, capsys):
    assert mt5.main(["control", INSTANCE, "--mode", "flatten", "--profile", "multicharts_mnq_3m", "--by", "hub"]) == 0
    out = capsys.readouterr().out
    assert "OK:" in out and '"mode": "flatten"' in out and f"{INSTANCE}.json" in out

    assert mt5.main(["control", INSTANCE]) == 0            # bez --mode/--profile len ukáže
    assert '"mode": "flatten"' in capsys.readouterr().out
    assert mt5.main(["control", "ina_instancia"]) == 0
    assert "nie je" in capsys.readouterr().out

    # spool inštancia bez control súboru sa v zozname ukáže tiež
    spool = common / "TradeBot" / "spool" / "mt5_1514750898-FTMO-Demo_EURUSD_5m_ibsnet"
    spool.mkdir(parents=True)
    (spool / "20260928-100000_abcdef12.jsonl").write_text('{"seq":1,"t":1,"k":"hello"}\n', encoding="utf-8")
    assert mt5.main(["control", "list"]) == 0
    out = capsys.readouterr().out
    assert INSTANCE in out and "mode=flatten profile=multicharts_mnq_3m" in out and "by=hub" in out
    assert "mt5_1514750898-FTMO-Demo_EURUSD_5m_ibsnet" in out and "bez control súboru" in out
    assert "1 súborov, posledný 20260928-100000_abcdef12.jsonl" in out

    rows = {r["instance"]: r for r in mt5.list_control(common)}
    assert rows[INSTANCE]["mode"] == "flatten" and rows["mt5_1514750898-FTMO-Demo_EURUSD_5m_ibsnet"]["mode"] == "-"

    with pytest.raises(SystemExit):
        mt5.main(["control"])                                # chýba inštancia


def test_neplatny_json_sa_ukaze_ako_chyba(common, capsys):
    ctl = common / "TradeBot" / "control"
    ctl.mkdir(parents=True)
    (ctl / f"{INSTANCE}.json").write_text("{nie json", encoding="utf-8")
    data = mt5.read_control(common, INSTANCE)
    assert data["mode"] == "?" and "neplatný JSON" in data["error"]
    assert mt5.main(["control", "list"]) == 0
    assert "CHYBA: neplatný JSON" in capsys.readouterr().out
    # zápis neplatný súbor prepíše platným
    assert mt5.write_control(common, INSTANCE, mode="paused")["mode"] == "paused"


def test_bez_common_adresara_skonci_zrozumitelne(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEBOT_MT5_COMMON", str(tmp_path / "nie-je"))
    with pytest.raises(SystemExit, match="TRADEBOT_MT5_COMMON"):
        mt5.main(["control", "list"])
