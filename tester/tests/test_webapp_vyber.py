"""Výber stratégií a profilov pre webapp (tester/webapp_vyber.json)."""

import json

from tester.webapp import vyber


def test_bez_suboru_je_vsetko_viditelne():
    assert vyber.selection() is None
    assert vyber.strategy_visible("ibs") and vyber.profile_visible("ibs", "hocico")
    assert vyber.filter_names("ibs", ["a", "b"]) == ["a", "b"]


def test_vyber_skryje_ostatne(tmp_path, monkeypatch):
    f = tmp_path / "webapp_vyber.json"
    f.write_text(json.dumps({"strategies": {"tksnet": ["SMERNICE_CS_TKS_1", "SMERNICE_CS_TKS_2"]}}))
    monkeypatch.setattr(vyber, "WEBAPP_SELECTION", f)
    monkeypatch.setattr(vyber, "_cache", None)
    assert vyber.strategy_visible("tksnet") and not vyber.strategy_visible("ibs")
    assert vyber.filter_names("tksnet", ["SMERNICE_CS_TKS_2", "mnq_databento_3m"]) == ["SMERNICE_CS_TKS_2"]
    assert vyber.filter_map("tksnet", {"SMERNICE_CS_TKS_1": 1, "x": 2}) == {"SMERNICE_CS_TKS_1": 1}
    assert vyber.filter_names("ibs", ["a"]) == []


def test_chybny_subor_nic_neskryje(tmp_path, monkeypatch):
    f = tmp_path / "webapp_vyber.json"
    f.write_text("{nie je json")
    monkeypatch.setattr(vyber, "WEBAPP_SELECTION", f)
    monkeypatch.setattr(vyber, "_cache", None)
    assert vyber.selection() is None
