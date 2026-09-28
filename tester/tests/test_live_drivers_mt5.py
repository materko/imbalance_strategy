"""Driver MetaTrader 5 (`tradebot.live.drivers.mt5`) nad dočasnými adresármi: štartovací ini, profil
grafov `chartNN.chr` + `order.wnd` (text presne ako terminál build 6230, UTF-16 LE s BOM, CRLF), magic
z id nasadenia, šablóna EA z `deploy/mt5`, profil do `Common\\Files\\TradeBot\\profiles`, control súbor,
(re)štart terminálu len pri zmene množiny grafov, odobratie grafu, heslo cez DPAPI; a driver
NinjaTrader (`deploy.json`, control, profil) pod `TRADEBOT_NT_DIR`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tradebot.live.drivers import secrets
from tradebot.live.drivers.base import Account, Deployment
from tradebot.live.drivers.mt5 import (Mt5Driver, chart_text, ea_inputs, magic_for, parse_chart, period_of,
                                       templates)
from tradebot.live.drivers.ninjatrader import NinjaTraderDriver
from tradebot.live.schema import instance_id

ACC = Account.from_dict({"id": "ftmo", "platform": "mt5", "label": "FTMO demo", "login": "1514750898",
                         "server": "FTMO-Demo"})
CFG = {"_strategy": "ibsnet", "_instrument": "mnq", "rrRatio": 3.0}


def dep(i: str, **over) -> Deployment:
    d = {"id": i, "account": "ftmo", "strategy": "ibsnet", "symbol": "US100.cash", "tf": 1,
         "profile": "golden_binance_btcusdt_3m", "config": CFG, "config_hash": "h1", "mode": "paused", "active": True}
    d.update(over)
    out = Deployment.from_dict(d)
    out.instance = instance_id("mt5", "1514750898-FTMO-Demo", out.symbol, out.tf, out.strategy)
    return out


class FakeProcesses:
    def __init__(self) -> None:
        self.alive_pids: set[int] = set()
        self.foreign: list[int] = []
        self.started: list[list[str]] = []
        self.closed: list[tuple[int, bool]] = []
        self.next_pid = 4000

    def alive(self, pid):
        return pid in self.alive_pids

    def find(self, exe):
        return list(self.foreign)

    def close(self, pid, force=False):
        self.closed.append((pid, force))
        self.alive_pids.discard(pid)
        if pid in self.foreign:
            self.foreign.remove(pid)

    def start(self, cmd, cwd):
        self.started.append(cmd)
        self.next_pid += 1
        self.alive_pids.add(self.next_pid)
        return self.next_pid


class Clock:
    def __init__(self) -> None:
        self.t = 1_790_000_000.0

    def __call__(self):
        return self.t


@pytest.fixture
def drv(tmp_path: Path):
    exe = tmp_path / "MetaTrader 5" / "terminal64.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    data = tmp_path / "Terminal" / "HASH"
    (data / "MQL5" / "Experts").mkdir(parents=True)
    common = tmp_path / "Terminal" / "Common" / "Files"
    common.mkdir(parents=True)
    procs = FakeProcesses()
    clock = Clock()
    d = Mt5Driver(root=tmp_path / "live" / "mt5", secrets_root=tmp_path / "live" / "secrets", exe=exe, data_dir=data,
                  common=common, processes=procs, sleep=lambda s: None, allow_live_trading=False, clock=clock)
    return d, procs, clock, data, common


def _utf16(path: Path) -> str:
    raw = path.read_bytes()
    assert raw.startswith(b"\xff\xfe")
    return raw[2:].decode("utf-16-le")


def test_templates_magic_period_and_inputs():
    assert templates() == {"ibsnet": "IBSNet", "orbnet": "ORBNet"}
    m = magic_for("d1")
    assert m == magic_for("d1") and m != magic_for("d2") and 100_000 <= m < 2**31
    assert period_of(1) == (0, 1) and period_of(5) == (0, 5) and period_of(60) == (1, 1) and period_of(240) == (1, 4)
    assert period_of(1440) == (2, 1) and period_of(90) == (0, 90)
    names = [n for _t, n, _v in ea_inputs()]
    assert names[:3] == ["InpProfile", "InpServerGmtOffsetMin", "InpMagic"] and "InpTelemetry" in names


def test_ini_text(drv):
    d, *_ = drv
    assert d.ini_text(ACC, None) == (
        "; TradeBot live driver: ucet ftmo (FTMO demo) - generovane, neupravovat\n"
        "[Common]\nLogin=1514750898\nServer=FTMO-Demo\n"
        "[Charts]\nProfileLast=tradebot\n"
        "[Experts]\nAllowLiveTrading=0\nAllowDllImport=1\nEnabled=1\n")
    assert "Password=tajne\n[Charts]" in d.ini_text(ACC, "tajne")
    d.allow_live_trading = True
    assert "AllowLiveTrading=1" in d.ini_text(ACC, None)


EXPECTED_CHART = """<chart>
id={id}
symbol=US100.cash
period_type=0
period_size=1
scale_fix=0
scale_fixed_min=0.000000
scale_fixed_max=0.000000
scale_fix11=0
scale_bar=0
scale_bar_val=0.000000
scale=4
mode=1
fore=0
grid=1
volume=0
scroll=1
shift=1
shift_size=20.000000
fixed_pos=0.000000
ticker=1
ohlc=0
one_click=0
one_click_btn=1
bidline=1
askline=0
lastline=0
days=0
descriptions=0
tradelines=1
tradehistory=1
window_left=0
window_top=0
window_right=1400
window_bottom=300
window_type=1
floating=0
floating_left=0
floating_top=0
floating_right=0
floating_bottom=0
floating_type=1
floating_toolbar=1
floating_tbstate=
background_color=0
foreground_color=16777215
barup_color=65280
bardown_color=65280
bullcandle_color=0
bearcandle_color=16777215
chartline_color=65280
volumes_color=3329330
grid_color=10061943
bidline_color=10061943
askline_color=255
lastline_color=49152
stops_color=255
windows_total=1

<expert>
name=IBSNet
path=Experts\\TradeBot\\IBSNet.ex5
expertmode=4
<inputs>
InpProfile=golden_binance_btcusdt_3m
InpServerGmtOffsetMin=180
InpMagic={magic}
InpExportSignals=false
InpLogEvents=true
InpShowDrawings=true
InpShowSessionBg=false
InpReplayBars=0
InpScreenshotFile=
InpCloseAfterShot=false
InpPointValueOverride=0.0
InpTelemetry=true
InpTelemetryInTester=false
</inputs>
</expert>

<window>
height=100.000000
objects=0

<indicator>
name=Main
path=
apply=1
show_data=1
scale_inherit=0
scale_line=0
scale_line_percent=50
scale_line_value=0.000000
scale_fix_min=0
scale_fix_min_val=0.000000
scale_fix_max=0
scale_fix_max_val=0.000000
expertmode=0
fixed_height=-1
</indicator>

</window>
</chart>"""


def test_chart_profile_text_matches_terminal_format(drv):
    d, procs, clock, data, common = drv
    d1 = dep("d1")
    d.ensure_instance(ACC, [d1])
    folder = data / "MQL5" / "Profiles" / "Charts" / "tradebot"
    text = _utf16(folder / "chart01.chr")
    from tradebot.live.drivers.mt5 import chart_id

    expected = EXPECTED_CHART.format(id=chart_id(d1.instance), magic=magic_for("d1")).replace("\n", "\r\n")
    assert text == expected
    assert _utf16(folder / "order.wnd") == "chart01.chr\r\n"
    parsed = parse_chart(folder / "chart01.chr")
    assert parsed["symbol"] == "US100.cash" and parsed["path"] == "Experts\\TradeBot\\IBSNet.ex5"
    assert parsed["inputs"]["InpMagic"] == str(magic_for("d1")) and parsed["inputs"]["InpProfile"] == "golden_binance_btcusdt_3m"
    # text pre druhý graf sa dlaždicuje pod prvý
    assert "window_top=300" in chart_text(d._charts(ACC, [d1])[0], 1)


def test_ensure_instance_starts_once_restarts_on_change_and_removes(drv):
    d, procs, clock, data, common = drv
    d1, d2 = dep("d1"), dep("d2", symbol="EURUSD", tf=5, profile="multicharts_mnq_3m")
    d.ensure_instance(ACC, [d1, d2])
    assert len(procs.started) == 1
    cmd = procs.started[0]
    assert cmd[0].endswith("terminal64.exe") and cmd[1].startswith("/config:") and cmd[1].endswith("start.ini") and "/portable" not in cmd
    folder = data / "MQL5" / "Profiles" / "Charts" / "tradebot"
    assert sorted(p.name for p in folder.iterdir()) == ["chart01.chr", "chart02.chr", "order.wnd"]
    assert _utf16(folder / "order.wnd") == "chart02.chr\r\nchart01.chr\r\n"
    st = d.status(ACC)
    assert st["running"] and st["pid"] == procs.next_pid and [c["symbol"] for c in st["charts"]] == ["US100.cash", "EURUSD"]
    assert st["charts"][1]["magic"] == magic_for("d2") and st["exe"].endswith("terminal64.exe") and st["portable"] is False

    # to isté znova: nič (žiadny reštart, profil nedotknutý)
    stamp = (folder / "chart01.chr").stat().st_mtime_ns
    d.ensure_instance(ACC, [d2, d1])
    assert len(procs.started) == 1 and procs.closed == [] and (folder / "chart01.chr").stat().st_mtime_ns == stamp

    # terminál si profil pri vypnutí prepíše (objekty, iné poradie) — stále sedí, keď má tie isté grafy
    text = _utf16(folder / "chart02.chr").replace("objects=0", "objects=5")
    (folder / "chart02.chr").write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))
    d.ensure_instance(ACC, [d1, d2])
    assert len(procs.started) == 1

    # terminál spadol → spustí sa znova bez prepisovania profilu
    procs.alive_pids.clear()
    d.ensure_instance(ACC, [d1, d2])
    assert len(procs.started) == 2 and "objects=5" in _utf16(folder / "chart02.chr")

    # zmena configu profilu (config_hash) = reštart, EA si profil načíta nanovo
    d1b = dep("d1", config_hash="h2")
    d.ensure_instance(ACC, [d1b, d2])
    assert len(procs.started) == 3 and procs.closed[-1] == (procs.next_pid - 1, False)

    # odobratie d2: graf zmizne, reštart
    d.ensure_instance(ACC, [d1b])
    assert len(procs.started) == 4 and sorted(p.name for p in folder.iterdir()) == ["chart01.chr", "order.wnd"]
    assert parse_chart(folder / "chart01.chr")["symbol"] == "US100.cash"

    # bez nasadení: terminál sa zavrie, profil bez grafov, nič sa nespúšťa
    d.ensure_instance(ACC, [])
    assert len(procs.started) == 4 and not procs.alive_pids and list(folder.glob("*.chr")) == []
    assert d.status(ACC)["running"] is False
    d.ensure_instance(ACC, [])
    assert len(procs.started) == 4

    # cudzí terminál z toho istého exe (spustený človekom) sa slušne zavrie pred štartom s ini
    procs.foreign = [77]
    d.ensure_instance(ACC, [d1b])
    assert (77, False) in procs.closed and len(procs.started) == 5
    log = (d.account_dir(ACC) / "driver.log").read_text(encoding="utf-8")
    assert "zatváram terminál PID 77" in log and "profil grafov `tradebot`" in log

    # zaseknutý terminál: po CLOSE_TIMEOUT sa zabije natvrdo
    class Stuck(FakeProcesses):
        def close(self, pid, force=False):
            self.closed.append((pid, force))
            if force:
                self.alive_pids.discard(pid)

    stuck = Stuck()
    stuck.alive_pids = set(procs.alive_pids)
    d.processes = stuck
    running = d.status(ACC)["pid"]

    def tick(_s):
        clock.t += 30

    d.sleep = tick
    d.ensure_instance(ACC, [])
    # slušné zavretie sa opakuje (terminál v štarte prvé nevidí), natvrdo až po CLOSE_TIMEOUT
    assert stuck.closed[0] == (running, False) and stuck.closed[-1] == (running, True)
    assert all(c == (running, False) for c in stuck.closed[1:-1]) and len(stuck.closed) >= 3


def test_profile_control_secret_and_password_scrub(drv, tmp_path: Path):
    d, procs, clock, data, common = drv
    d1 = dep("d1")
    path = d.ensure_profile(d1)
    assert path == common / "TradeBot" / "profiles" / "ibsnet" / "golden_binance_btcusdt_3m.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == {"_strategy": "ibsnet", "_instrument": "mnq", "_source": "hub:d1", "rrRatio": 3.0}
    stamp = path.stat().st_mtime_ns
    assert d.ensure_profile(d1) == path and path.stat().st_mtime_ns == stamp   # rovnaký obsah = bez zápisu
    # starý kľúč (alias) ide do dnešného adresára
    assert d.ensure_profile(dep("d9", strategy="ibsninja")).parent.name == "ibsnet"

    ctl = d.write_control(d1)
    assert ctl == common / "TradeBot" / "control" / f"{d1.instance}.json"
    data1 = json.loads(ctl.read_text(encoding="utf-8"))
    assert data1["mode"] == "paused" and data1["profile"] == "golden_binance_btcusdt_3m" and data1["by"] == "hub"
    d.write_control(d1)
    assert json.loads(ctl.read_text(encoding="utf-8")) == data1   # nezmenené = nepíše sa (mtime = správa pre EA)
    d.write_control(dep("d1", mode="enabled"))
    assert json.loads(ctl.read_text(encoding="utf-8"))["mode"] == "enabled"
    # zrušenie: control sa nemaže hneď (chýbajúci = enabled pre EA), prepne sa na paused a zmaže ho až
    # ensure_instance, keď terminál s tým grafom nebeží
    d.remove_instance(ACC, d1)
    zrusene = json.loads(ctl.read_text(encoding="utf-8"))
    assert zrusene["mode"] == "paused" and zrusene["profile"] == "golden_binance_btcusdt_3m"
    d.remove_instance(ACC, d1)   # druhýkrát nič (už je paused — mtime = správa pre EA)
    assert json.loads(ctl.read_text(encoding="utf-8")) == zrusene
    d.ensure_instance(ACC, [])
    assert not ctl.exists()
    d.remove_instance(ACC, d1)   # bez súboru nič

    # heslo: DPAPI na Windows (inak čitateľne s varovaním), ide do ini len na štart a potom sa zmaže
    d.store_secret(ACC, "tajne-heslo")
    blob = secrets.secret_path("ftmo", d.secrets_root).read_bytes()
    assert b"tajne-heslo" not in blob if sys.platform == "win32" else blob.startswith(b"TBPLAIN1")
    assert secrets.load("ftmo", d.secrets_root) == "tajne-heslo"
    assert secrets.load("iny", d.secrets_root) is None
    d.ensure_instance(ACC, [d1])
    ini = d.account_dir(ACC) / "start.ini"
    assert "Password=tajne-heslo" in ini.read_text(encoding="utf-8")
    assert json.loads(ctl.read_text(encoding="utf-8"))["mode"] == "paused"   # poistka: chýbajúci control sa dopísal pred štartom
    d.ensure_instance(ACC, [d1])                       # hneď po štarte ešte ostáva
    assert "Password=" in ini.read_text(encoding="utf-8")
    clock.t += 60
    d.ensure_instance(ACC, [d1])
    assert "Password=" not in ini.read_text(encoding="utf-8") and len(procs.started) == 1
    assert secrets.delete("ftmo", d.secrets_root) and not secrets.delete("ftmo", d.secrets_root)


def test_control_je_na_disku_pred_startom_terminalu(drv, tmp_path: Path):
    """Reconciler → driver: v momente, keď sa terminál spúšťa, má každý graf control súbor s režimom
    nasadenia (nové = paused) — EA by bez neho naštartovala `enabled`."""
    from tradebot.adapters.mt5.__main__ import control_dir
    from tradebot.live.apply import Reconciler

    d, procs, clock, data, common = drv
    videne: list[tuple[str, str]] = []

    class Watch(FakeProcesses):
        def start(self, cmd, cwd):
            for p in sorted(control_dir(common).glob("*.json")):
                videne.append((p.name, json.loads(p.read_text(encoding="utf-8"))["mode"]))
            return super().start(cmd, cwd)

    d.processes = Watch()
    rec = Reconciler({"mt5": d}, tmp_path / "apply.json")
    acc = {"id": "ftmo", "platform": "mt5", "label": "FTMO demo", "login": "1514750898", "server": "FTMO-Demo"}
    novy = {"id": "d1", "account": "ftmo", "strategy": "ibsnet", "symbol": "US100.cash", "tf": 1,
            "profile": "golden_binance_btcusdt_3m", "config": CFG, "config_hash": "h1", "mode": "paused", "active": True}
    out = rec.run({"accounts": [acc], "deployments": [novy]})
    inst = dep("d1").instance
    assert out["applied"][0]["status"] == "ok" and len(d.processes.started) == 1
    assert videne == [(f"{inst}.json", "paused")]
    assert json.loads((tmp_path / "apply.json").read_text(encoding="utf-8"))["applied"]["d1"]["control"] \
        == str(control_dir(common) / f"{inst}.json")

    # poistka drivera: keď control chýba (niekto ho zmazal) a terminál treba spustiť znova, dopíše ho pred štartom
    (control_dir(common) / f"{inst}.json").unlink()
    d.processes.alive_pids.clear()
    videne.clear()
    d.ensure_instance(ACC, [dep("d1")])
    assert videne == [(f"{inst}.json", "paused")] and "dopísaný pred štartom" in (d.account_dir(ACC) / "driver.log").read_text(encoding="utf-8")


def test_zrusene_nasadenie_pauza_pred_zavretim_control_prec_az_po(drv):
    """Poradie pri zrušení: control → paused (EA neotvorí nový vstup), terminál sa zavrie s grafom, control
    sa zmaže až potom; `flatten` sa neprebíja; iný login účtu = reštart terminálu."""
    from tradebot.adapters.mt5.__main__ import control_dir, read_control

    d, procs, clock, data, common = drv
    d1, d2 = dep("d1", mode="enabled"), dep("d2", symbol="EURUSD", tf=5, mode="enabled")
    for x in (d1, d2):
        d.write_control(x)
    d.ensure_instance(ACC, [d1, d2])
    ctl2 = control_dir(common) / f"{d2.instance}.json"
    pri_zavreti: list[str | None] = []

    class Watch(FakeProcesses):
        def close(self, pid, force=False):
            c = read_control(common, d2.instance)
            pri_zavreti.append(c["mode"] if c else None)
            super().close(pid, force)

    w = Watch()
    w.alive_pids = set(procs.alive_pids)
    d.processes = w
    d.remove_instance(ACC, d2)
    assert read_control(common, d2.instance)["mode"] == "paused" and ctl2.exists()
    d.ensure_instance(ACC, [d1])
    assert pri_zavreti == ["paused"]                      # pri zatváraní terminálu control ešte bol, s pauzou
    assert not ctl2.exists() and read_control(common, d1.instance)["mode"] == "enabled"
    assert len(w.started) == 1 and len(w.closed) == 1

    # flatten ostáva flatten; zmazanie až keď terminál bez grafu zavrel
    d.write_control(dep("d1", mode="flatten"))
    d.remove_instance(ACC, d1)
    assert read_control(common, d1.instance)["mode"] == "flatten"
    d.ensure_instance(ACC, [])
    assert not (control_dir(common) / f"{d1.instance}.json").exists() and not w.alive_pids

    # nasadenie, ktoré nikdy nemalo control (ani graf), nič nezapisuje
    d.remove_instance(ACC, dep("d9", symbol="XAUUSD"))
    assert not list(control_dir(common).glob("*XAUUSD*"))
    d.ensure_instance(ACC, [])
    assert not list(control_dir(common).glob("*XAUUSD*"))

    # iný login toho istého účtu (id inštancií aj ini sa menia) = nie je to ten istý terminál: reštart
    d.ensure_instance(ACC, [d1])
    n = len(w.started)
    iny = Account.from_dict({**ACC.raw, "login": "999"})
    d.ensure_instance(iny, [Deployment.from_dict({**d1.raw})])
    assert len(w.started) == n + 1 and "Login=999" in (d.account_dir(iny) / "start.ini").read_text(encoding="utf-8")
    assert json.loads((d.account_dir(iny) / "charts.json").read_text(encoding="utf-8"))["account"] == "999-FTMO-Demo"
    d.ensure_instance(iny, [Deployment.from_dict({**d1.raw})])
    assert len(w.started) == n + 1                        # a potom už nič


def test_terminal_resolution_and_errors(drv, tmp_path: Path):
    d, procs, clock, data, common = drv
    # účet s vlastnou portable cestou: dátový adresár = adresár exe, štart s /portable
    port = tmp_path / "port"
    port.mkdir()
    (port / "terminal64.exe").write_bytes(b"MZ")
    acc = Account.from_dict({"id": "p", "platform": "mt5", "login": "1", "server": "S", "terminal": str(port), "portable": True})
    exe, ddir, portable = d.terminal_for(acc)
    assert exe == port / "terminal64.exe" and ddir == port and portable
    d.ensure_instance(acc, [dep("x", account="p")])
    assert procs.started[-1][-1] == "/portable" and (port / "MQL5" / "Profiles" / "Charts" / "tradebot" / "chart01.chr").exists()
    # neexistujúci terminál = zrozumiteľná chyba
    with pytest.raises(ValueError, match="nie je"):
        d.terminal_for(Account.from_dict({"id": "q", "platform": "mt5", "terminal": str(tmp_path / "nic")}))
    # neznáma stratégia nemá šablónu
    with pytest.raises(ValueError, match="šablónu"):
        d.ensure_instance(ACC, [dep("z", strategy="ibs")])


# --------------------------------------------------------------------------- #
# NinjaTrader: len súbory
# --------------------------------------------------------------------------- #

NT_ACC = Account.from_dict({"id": "sim", "platform": "ninjatrader", "login": "Sim101", "server": "Simulated Data Feed"})


def nt_dep(i: str, **over) -> Deployment:
    d = {"id": i, "account": "sim", "strategy": "ibsnet", "symbol": "MNQ 12-26", "tf": 3, "profile": "multicharts_mnq_3m",
         "config": CFG, "config_hash": "h", "mode": "enabled", "active": True}
    d.update(over)
    return Deployment.from_dict(d)


def test_ninjatrader_driver_writes_deploy_json_control_and_profile(tmp_path: Path, monkeypatch):
    nt = tmp_path / "NinjaTrader 8"
    (nt / "bin" / "Custom").mkdir(parents=True)
    monkeypatch.setenv("TRADEBOT_NT_DIR", str(nt))
    running = {"value": False}
    launched: list[Path] = []
    d = NinjaTraderDriver(exe=tmp_path / "NinjaTrader.exe", is_running=lambda: running["value"], launcher=launched.append)
    assert d.available() and d.nt_dir() == nt
    assert not NinjaTraderDriver(nt_dir=tmp_path / "nie").available()

    a = nt_dep("n1")
    a.instance = d.instance_of(NT_ACC, a)
    assert a.instance == "ninjatrader_Sim101_MNQ_3m_ibsnet"   # ako AddOn: MasterInstrument.Name, nie `MNQ 12-26`
    assert d.ensure_profile(a) == nt / "TradeBot" / "profiles" / "ibsnet" / "multicharts_mnq_3m.json"
    assert json.loads(d.ensure_profile(a).read_text(encoding="utf-8"))["_strategy"] == "ibsnet"
    ctl = d.write_control(a)
    assert json.loads(ctl.read_text(encoding="utf-8"))["mode"] == "enabled" and ctl.name == f"{a.instance}.json"
    d.store_secret(NT_ACC, "x")   # no-op

    d.ensure_instance(NT_ACC, [a])
    deploy = json.loads((nt / "TradeBot" / "deploy.json").read_text(encoding="utf-8"))
    assert deploy["instances"] == [{"deployment": "n1", "instance": a.instance, "connection": "Simulated Data Feed",
                                    "account": "Sim101", "instrument": "MNQ 12-26", "tf": 3, "strategy": "ibsnet",
                                    "profile": "multicharts_mnq_3m"}]
    assert deploy["by"] == "hub" and launched == [tmp_path / "NinjaTrader.exe"]   # NT nebežal → spustený
    assert not list((nt / "TradeBot").glob(".deploy*"))                             # atomicky, bez tmp zvyšku

    # bez zmeny sa nepíše; keď beží, nespúšťa sa
    running["value"] = True
    stamp = (nt / "TradeBot" / "deploy.json").stat().st_mtime_ns
    d.ensure_instance(NT_ACC, [a])
    assert (nt / "TradeBot" / "deploy.json").stat().st_mtime_ns == stamp and len(launched) == 1

    # inštancie iného účtu v deploy.json ostávajú
    other = Account.from_dict({"id": "live", "platform": "ninjatrader", "login": "Live1", "server": "Rithmic"})
    b = nt_dep("n2", account="live", symbol="ES 12-26")
    d.ensure_instance(other, [b])
    deploy = json.loads((nt / "TradeBot" / "deploy.json").read_text(encoding="utf-8"))
    assert [e["deployment"] for e in deploy["instances"]] == ["n1", "n2"]
    d.ensure_instance(NT_ACC, [])
    deploy = json.loads((nt / "TradeBot" / "deploy.json").read_text(encoding="utf-8"))
    assert [e["deployment"] for e in deploy["instances"]] == ["n2"]
    # zrušenie (poradie ako v reconcileri: remove_instance, potom ensure_instance): control → paused, nie preč;
    # zmaže sa, až keď inštancia nebola v deploy.json už pred týmto kolom (AddOn ju stihol zastaviť)
    d.ensure_instance(NT_ACC, [a])                       # n1 znova beží
    d.remove_instance(NT_ACC, a)
    assert json.loads(ctl.read_text(encoding="utf-8"))["mode"] == "paused"
    d.ensure_instance(NT_ACC, [])                        # deploy.json bez n1; control ešte ostáva (AddOn zastavuje)
    deploy = json.loads((nt / "TradeBot" / "deploy.json").read_text(encoding="utf-8"))
    assert [e["deployment"] for e in deploy["instances"]] == ["n2"] and ctl.exists()
    d.remove_instance(NT_ACC, a)                         # ďalšie kolo (hub ju stále posiela ako active=false)
    d.ensure_instance(NT_ACC, [])
    assert not ctl.exists()
    d.remove_instance(NT_ACC, a)                         # bez súboru nič
    # flatten sa neprebíja; nasadenie, ktoré sa medzitým vrátilo, o control nepríde
    d.write_control(a)
    d.ensure_instance(NT_ACC, [a])
    from tradebot.adapters.ninjatrader.__main__ import write_control as nt_write_control
    nt_write_control(nt, a.instance, mode="flatten", by="test")
    d.remove_instance(NT_ACC, a)
    assert json.loads(ctl.read_text(encoding="utf-8"))["mode"] == "flatten"
    d.ensure_instance(NT_ACC, [a])                       # vrátilo sa: control ostáva
    assert ctl.exists()
    d.ensure_instance(NT_ACC, [])
    assert ctl.exists()                                  # nič odložené — bez remove_instance sa nemaže
    st = d.status(other)
    assert st["running"] and [e["deployment"] for e in st["instances"]] == ["n2"] and st["deploy"].endswith("deploy.json")


# --------------------------------------------------------------------------- #
# nový kód na stroji (docs/LIVE.md, fáza 2c): marker a install_code drivera MT5
# --------------------------------------------------------------------------- #


def test_mt5_install_code_zavrie_terminaly_nainstaluje_a_zapise_marker(drv, monkeypatch):
    from tradebot.adapters.mt5 import __main__ as mt5cli

    d, procs, clock, data, common = drv
    assert d.installed_version() is None
    volania = []
    monkeypatch.setattr(mt5cli, "install", lambda mql5, extra, **kw: (volania.append((mql5, kw.get("common"))), {"compiled": ["IBSNet"]})[1])
    # terminál účtu beží (spustený driverom) + cudzí z toho istého exe
    d.ensure_instance(ACC, [dep("d1")])
    pid = d._running_pid(ACC)
    assert pid is not None
    procs.foreign = [777]
    out = d.install_code("abc1234", [ACC])
    assert sorted(out["closed"]) == sorted([pid, 777]) and [p for p, f in procs.closed] == [pid, 777]
    assert volania == [(data / "MQL5", common)]                     # jeden dátový adresár = jedna inštalácia
    assert out["installed_to"][0]["mql5"] == str(data / "MQL5") and out["installed_to"][0]["compiled"] == ["IBSNet"]
    assert d.installed_version() == "abc1234" and json.loads((common / "TradeBot" / "installed.json").read_text())["by"] == "hub"
    assert d.status(ACC)["installed"] == "abc1234" and d.status(ACC)["running"] is False
    # ďalšie kolo reconcilera terminál spustí znova (grafy sedia, pid nie je)
    n = len(procs.started)
    d.ensure_instance(ACC, [dep("d1")])
    assert len(procs.started) == n + 1
    # bez účtov sa inštaluje aspoň do nainštalovaného terminálu stroja
    volania.clear()
    d.install_code("def5678", [])
    assert volania == [(data / "MQL5", common)] and d.installed_version() == "def5678"
