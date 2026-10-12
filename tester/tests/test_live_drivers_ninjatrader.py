"""Driver NinjaTrader: prečo inštancia nasadenia nenabehla (`instance_issue`) z najnovšieho
`TradeBot\\logs\\addon_*.txt` — riadky v tvare, ako ich píše `TradeBotLiveAddOn.Say` a `LiveInstance.Log`
(značka `[<nasadenie>]` do `Setup` po id inštancie, potom `[<inštancia>]`; riadky AddOnu bez značky)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradebot.live.drivers import ninjatrader as nt_mod
from tradebot.live.drivers.base import Account, Deployment
from tradebot.live.drivers.ninjatrader import NinjaTraderDriver

ACC = Account.from_dict({"id": "sim", "platform": "ninjatrader", "login": "Sim101", "server": "Simulated Data Feed"})
INST = "ninjatrader_Sim101_MNQ_3m_ibsnet"


def nt_dep(i: str = "n1", **over) -> Deployment:
    d = {"id": i, "account": "sim", "strategy": "ibsnet", "symbol": "MNQ 12-26", "tf": 3, "profile": "multicharts_mnq_3m",
         "config": {}, "config_hash": "h", "mode": "enabled", "active": True}
    d.update(over)
    return Deployment.from_dict(d)


START = "n1: ibsnet MNQ 12-26 3m na Sim101 (Simulated Data Feed, profil 'multicharts_mnq_3m')"


@pytest.fixture
def drv(tmp_path: Path):
    nt = tmp_path / "NinjaTrader 8"
    (nt / "bin" / "Custom").mkdir(parents=True)
    logs = nt / "TradeBot" / "logs"
    logs.mkdir(parents=True)

    def write(lines: list[str], name: str = "addon_20261012-170000.txt") -> Path:
        path = logs / name
        path.write_text("".join(f"2026-10-12 {line}\n" for line in lines), encoding="utf-8")
        return path

    return NinjaTraderDriver(nt_dir=nt, is_running=lambda: True), write


def test_bez_logu_a_bez_riadkov_nasadenia_nic(drv):
    d, write = drv
    assert d.log_path() is None and d.instance_issue(ACC, nt_dep()) is None
    write(["15:00:00.000 start generacia abcd1234", "15:00:03.000 deploy.json: 0 instancii",
           "15:00:04.000 [n2] ucet Sim101 sa do 60 s nepripojil"])      # cudzie nasadenie
    assert d.instance_issue(ACC, nt_dep()) is None


def test_ucet_sa_nepripojil_a_pokus_v_behu_drzi_predosly_dovod(drv):
    d, write = drv
    lines = ["15:00:03.000 deploy.json: 1 instancii", f"15:00:03.000   {START}",
             f"15:00:03.100 [n1] start {START}",
             "15:01:03.200 [n1] ucet Sim101 sa do 60 s nepripojil"]
    write(lines)
    assert d.instance_issue(ACC, nt_dep()) == "ucet Sim101 sa do 60 s nepripojil (15:01:03 UTC)"
    # AddOn skúša znova o 60 s; kým nový pokus nedobehne, platí predošlý dôvod
    lines.append(f"15:02:03.300 [n1] start {START}")
    write(lines)
    assert d.instance_issue(ACC, nt_dep()) == "ucet Sim101 sa do 60 s nepripojil (15:01:03 UTC)"
    # nový pokus prešiel Setup (po id inštancie sa značka mení na inštanciu) → nabehla
    lines += ["15:02:04.000 [n1] ucet Sim101 je Connected (Simulated Data Feed)",
              f"15:02:05.000 [{INST}] instancia {INST}, spool C:\\x",
              f"15:02:09.000 [{INST}] predhistoria prehrata: 500 barov grafu"]
    write(lines)
    assert d.instance_issue(ACC, nt_dep()) is None


def test_pripojenie_s_detailom_addonu_a_ostatne_dovody(drv):
    d, write = drv
    write([f"15:00:03.100 [n1] start {START}",
           "15:00:03.200 pripojenie 'Simulated Data Feed' v Core.Globals.ConnectOptions nie je (su: Rithmic, Kinetick)",
           "15:00:03.300 [n1] pripojenie 'Simulated Data Feed' nie je Connected - skusim znova neskor"])
    issue = d.instance_issue(ACC, nt_dep())
    assert issue.startswith("pripojenie 'Simulated Data Feed' nie je Connected - skusim znova neskor — pripojenie "
                            "'Simulated Data Feed' v Core.Globals.ConnectOptions nie je (su: Rithmic, Kinetick)")
    assert issue.endswith("(15:00:03 UTC)")

    for riadok, tag in [("profil 'multicharts_mnq_3m' sa nenasiel v C:\\TradeBot\\profiles - preskakujem", "n1"),
                        ("instrument 'MNQ 12-26' NinjaTrader nepozna", "n1"),
                        ("neuplny zaznam v deploy.json (strategy, instrument, account, tf) - preskakujem", "n1"),
                        ("engine 'ibsnet' z profilu 'multicharts_mnq_3m' sa nepostavil - chyba v configu", INST),
                        ("BarsRequest 3m bez odpovede 120 s", INST),
                        ("vlakno instancie spadlo: System.NullReferenceException", INST)]:
        write([f"15:10:00.000 [n1] start {START}", f"15:10:01.000 [{tag}] {riadok}"])
        assert d.instance_issue(ACC, nt_dep()) == f"{riadok} (15:10:01 UTC)", riadok
    # úspešný BarsRequest nie je zlyhanie
    write([f"15:10:00.000 [n1] start {START}", f"15:10:01.000 [{INST}] BarsRequest MNQ 12-26 3m: 500 barov (chcel 405)"])
    assert d.instance_issue(ACC, nt_dep()) is None


def test_najnovsi_log_a_koniec_velkeho_logu(drv, monkeypatch):
    d, write = drv
    write([f"15:00:00.000 [n1] start {START}", "15:01:00.000 [n1] ucet Sim101 sa do 60 s nepripojil"],
          name="addon_20261011-090000.txt")
    write(["16:00:00.000 start generacia ffff0000"], name="addon_20261012-160000.txt")
    assert d.log_path().name == "addon_20261012-160000.txt"
    assert d.instance_issue(ACC, nt_dep()) is None                 # starý log (iný štart NT) sa nečíta
    # z veľkého logu len koniec; odrezaný prvý riadok sa zahodí
    monkeypatch.setattr(nt_mod, "LOG_TAIL_BYTES", 200)
    filler = [f"16:00:{i % 60:02d}.000 [n9] nieco ine {'x' * 40}" for i in range(50)]
    write(filler + [f"16:05:00.000 [n1] start {START}", "16:05:01.000 [n1] instrument 'MNQ 12-26' NinjaTrader nepozna"],
          name="addon_20261012-160000.txt")
    assert d.instance_issue(ACC, nt_dep()) == "instrument 'MNQ 12-26' NinjaTrader nepozna (16:05:01 UTC)"
