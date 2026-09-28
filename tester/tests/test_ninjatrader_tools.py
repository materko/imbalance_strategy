"""`tester.ninjatrader` — formát exportu signálov z adaptéra a ich porovnanie s referenčným behom;
`tradebot.adapters.ninjatrader` — čo ide do prekladu a control súbor (docs/LIVE.md, fáza 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tester import ninjatrader as nt
from tradebot.adapters.ninjatrader import __main__ as ntcli

HEADER = "kind;bar_open_ms;id;a;b;entry;sl;tp;qty;ready;text\n"


def test_read_export_rozlisi_ordery_udalosti_a_statistiky(tmp_path):
    path = tmp_path / "ibsnet_MNQ.csv"
    path.write_text(
        HEADER
        + "order;1000;LONG_6;Entry;Limit;24918.25;24866.25;24970.25;3;1;\n"
        + "order;4000;LONG_6;Cancel;Limit;;;;;1;EXPIRED\n"
        + "event;1000;6;4;5;;;;;;order zadany\n"
        + "stat;0;zones;12;;;;;;;\n",
        encoding="utf-8",
    )
    data = nt.read_export(path)
    assert data["orders"] == [(1000, "LONG_6", "Entry", (24918.25, 24866.25, 24970.25, 3.0)),
                              (4000, "LONG_6", "Cancel", None)]
    assert data["events"] == [(1000, 6, 4, 5)]


def test_compare_pocita_len_to_co_nezavisi_od_fill_modelu():
    ref = {"orders": [(1000, "LONG_6", "Entry", (10.0, 9.0, 11.0, 1.0)), (2000, "SHORT_7", "Entry", (20.0, 21.0, 19.0, 1.0))],
           "events": [(500, 6, 0, 1), (900, 6, 3, 4), (1000, 6, 4, 5), (2000, 7, 4, 5), (2500, 7, 5, -1)]}
    same = nt.compare(ref, ref)
    assert same["entries"]["same_bar_and_plan"] == 2 and same["zone_events"]["only_nt"] == []

    # iné vyplnenie v NinjaTraderi zmení stavy 5 -> -1, vstupy a stavy 0-3 ostávajú
    other = {"orders": list(ref["orders"]), "events": [e for e in ref["events"] if e[2] != 5] + [(2600, 7, 5, -1)]}
    res = nt.compare(other, ref)
    assert res["entries"]["nt"] == res["entries"]["ref"] == res["entries"]["same_bar_and_plan"] == 2
    assert res["zone_events"]["nt"] == res["zone_events"]["ref"] == res["zone_events"]["same"]

    # iná cena vstupu je rozdiel
    bad = {"orders": [(1000, "LONG_6", "Entry", (10.25, 9.0, 11.0, 1.0))], "events": ref["events"]}
    assert nt.compare(bad, ref)["entries"]["different_plan"]


def test_compare_nezavisi_od_uidov_zon():
    """MT5 prehrá pred štartom predhistóriu, takže uidy zón (a s nimi id vstupov `LONG_8`) sú posunuté
    oproti Testeru, hoci signály sú tie isté — porovnanie ich musí ignorovať."""
    ref = {"orders": [(1000, "LONG_6", "Entry", (10.0, 9.0, 11.0, 1.0)), (2000, "SHORT_7", "Entry", (20.0, 21.0, 19.0, 1.0))],
           "events": [(500, 6, 0, 1), (900, 6, 1, 2), (2000, 7, 0, 1)]}
    shifted = {"orders": [(t, f"{i.rsplit('_', 1)[0]}_{int(i.rsplit('_', 1)[1]) + 2}", a, p) for t, i, a, p in ref["orders"]],
               "events": [(t, z + 2, a, b) for t, z, a, b in ref["events"]]}
    res = nt.compare(shifted, ref)
    assert res["entries"]["same_bar_and_plan"] == 2 and not res["entries"]["only_nt"] and not res["entries"]["only_ref"]
    assert res["zone_events"]["same"] == res["zone_events"]["nt"] == res["zone_events"]["ref"] == 3
    # dve zóny s rovnakým prechodom na jednom bare = dve udalosti, nie jedna
    twice = {"orders": ref["orders"], "events": ref["events"] + [(500, 9, 0, 1)]}
    assert nt.compare(twice, ref)["zone_events"]["only_nt"] == [(500, 0, 1)]


# --------------------------------------------------------------------------- #
# inštalátor: čo NinjaTrader prekladá, control súbor
# --------------------------------------------------------------------------- #


def test_check_preklada_adapter_aj_addon():
    """`check` musí prekladať to isté, čo NinjaTrader po `install`: jadro, adaptér, AddOn, šablóny."""
    files = ntcli.check_sources()
    names = [f.name for f in files]
    assert "TradeBotStrategy.cs" in names and "TradeBotLiveAddOn.cs" in names
    assert "IBSNet.cs" in names and "ORBNet.cs" in names
    assert all(f.is_file() for f in files)
    assert any(f.name == "Live.cs" for f in files)   # LiveSpool (spool + control udalosti) ide s jadrom


@pytest.fixture
def nt_dir(tmp_path: Path, monkeypatch) -> Path:
    nt = tmp_path / "NinjaTrader 8"
    (nt / "bin" / "Custom").mkdir(parents=True)
    monkeypatch.setenv("TRADEBOT_NT_DIR", str(nt))
    return nt


def test_control_zapise_a_precita_subor(nt_dir: Path, capsys):
    instance = "ninjatrader_Sim101_MNQ-12-26_3m_ibsnet"
    assert ntcli.main(["control", instance, "--mode", "paused", "--profile", "multicharts_mnq_3m", "--by", "test"]) == 0
    path = nt_dir / "TradeBot" / "control" / f"{instance}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mode"] == "paused" and data["profile"] == "multicharts_mnq_3m" and data["by"] == "test"
    assert isinstance(data["updated"], int) and data["updated"] > 1_700_000_000_000
    assert not list(path.parent.glob("*.tmp"))   # atomický zápis: tmp súbor nezostal

    # zmena len režimu ponechá profil; `read_control` číta to isté, čo číta adaptér
    assert ntcli.main(["control", instance, "--mode", "enabled"]) == 0
    again = ntcli.read_control(nt_dir, instance)
    assert again["mode"] == "enabled" and again["profile"] == "multicharts_mnq_3m" and again["by"] == "test"

    # bez prepínačov = výpis; `list` ukáže inštancie zo spoolu aj z control adresára
    capsys.readouterr()
    assert ntcli.main(["control", instance]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "enabled"
    (nt_dir / "TradeBot" / "spool" / "ninjatrader_Sim101_MNQ-12-26_3m_orbnet").mkdir(parents=True)
    rows = ntcli.list_control(nt_dir)
    assert [r["instance"] for r in rows] == [instance, "ninjatrader_Sim101_MNQ-12-26_3m_orbnet"]
    assert rows[0]["control"]["mode"] == "enabled" and rows[1]["control"] is None and rows[1]["spool"]
    assert ntcli.main(["control", "list"]) == 0
    assert "orbnet" in capsys.readouterr().out


def test_control_odmietne_zly_mode_a_instanciu(nt_dir: Path):
    with pytest.raises(SystemExit):
        ntcli.write_control(nt_dir, "x", mode="stop")
    with pytest.raises(SystemExit):
        ntcli.write_control(nt_dir, "../x", mode="paused")
    with pytest.raises(SystemExit):
        ntcli.main(["control", "x", "--mode", "off"])
