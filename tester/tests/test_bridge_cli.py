"""Ručný master `python -m tradebot.live.bridge` bez pythonnet a identita exekútora Python ↔ C#.

* `execs` a `tail` len čítajú súbory mosta — musia ísť aj bez pythonnet/CLR;
* `send modify` bez `--sl` aj `--tp` je chyba (prázdny modify by exekútor len zbytočne spracoval);
* `routes.executor_id` (hub, `route.to`) = `TradeBot.Core.Bridge.ExecutorId` (EA exekútora píše heartbeat pod
  týmto id a AddOn podľa neho hľadá exekútora) — aj login s nulou na začiatku a server s medzerami či inou
  veľkosťou písmen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.live import bridge as cli
from tradebot.live.routes import executor_id


@pytest.fixture
def bez_clr(monkeypatch):
    def nie(*a, **k):
        raise AssertionError("príkaz, ktorý len číta súbory, nesmie volať pythonnet")

    monkeypatch.setattr(cli, "_core", nie)


def test_execs_a_tail_bez_pythonnet(tmp_path: Path, capsys, bez_clr):
    root = tmp_path / "TradeBot"
    assert cli.main(["execs", "--root", str(root)]) == 1 and "žiadny exekútor" in capsys.readouterr().out
    (root / "exec").mkdir(parents=True)
    hb = {"t": cli._now(), "id": "mt5exec_5-S", "margin_mode": "hedging", "connected": True, "trade_allowed": True,
          "symbols": [{"name": "US100.cash"}], "routes": [{"id": "inst-1", "state": "ok"}]}
    (root / "exec" / "mt5exec_5-S.hb.json").write_text(json.dumps(hb), encoding="utf-8")
    (root / "exec" / "zly.hb.json").write_text("{", encoding="utf-8")
    assert cli.main(["execs", "--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "mt5exec_5-S" in out and "symbolov 1" in out and "route inst-1: ok" in out and "nečitateľný" in out

    base = ["--root", str(root), "--to", "mt5exec_5-S", "--symbol", "US100.cash"]
    assert cli.main(["tail", *base]) == 1 and "neexistuje" in capsys.readouterr().out
    evt = root / "bridge" / "manual_US100.cash" / "evt.jsonl"
    evt.parent.mkdir(parents=True)
    evt.write_text("\n".join(json.dumps({"seq": i}) for i in range(5)) + "\n", encoding="utf-8")
    assert cli.main(["tail", *base, "-n", "2"]) == 0
    assert capsys.readouterr().out.split() == ['{"seq":', "3}", '{"seq":', "4}"]


def test_root_bez_pythonnet_z_prostredia(tmp_path: Path, monkeypatch, capsys, bez_clr):
    monkeypatch.setenv("TRADEBOT_BRIDGE_ROOT", str(tmp_path / "env-root"))
    assert cli.main(["execs"]) == 1 and str(tmp_path / "env-root") in capsys.readouterr().out


def test_prazdny_modify_je_chyba(tmp_path: Path, bez_clr):
    with pytest.raises(SystemExit, match="--sl alebo --tp"):
        cli.main(["send", "modify", "--root", str(tmp_path), "--to", "mt5exec_5-S", "--id", "M-1"])


@pytest.fixture(scope="module")
def core():
    from tradebot.adapters.csharp import bridge

    try:
        bridge._load_clr()
    except bridge.BridgeError as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    import TradeBot.Core as core

    return core


@pytest.mark.parametrize("login, server", [
    ("1514750898", "FTMO-Demo"), ("007", "FTMO-Demo"), (" 42 ", "ICMarketsSC-MT5-2"), ("5012345", "FTMO Demo"),
    ("5012345", "ftmo-demo"), ("5012345", "  Server / s medzerou  "), ("5012345", "Broker.Live_3"),
    ("5012345", "Šrv-ä"), ("5012345", ""), ("5012345", "a😀b"),
])
def test_executor_id_rovnake_ako_csharp(core, login, server):
    assert executor_id(login, server) == str(core.Bridge.ExecutorId(int(login), server))
