"""Ručný master pre MT5 exekútor (docs/ROUTING.md) — skúška `TradeBotExecutor` bez NinjaTradera.

    python -m tradebot.live.bridge execs                                   # exekútory na stroji (heartbeat, symboly, route)
    python -m tradebot.live.bridge status  --to mt5exec_5012345-FTMO-Demo --symbol US100.cash
    python -m tradebot.live.bridge send entry --to … --symbol US100.cash --dir long --ot Limit --e 20000 --sl 19980 \\
                                              --tp 20040 --q 1 --ref 20010 [--close-in 30] [--cancel-in 10] [--hold 60]
    python -m tradebot.live.bridge send cancel|close --to … --symbol … --id L-1
    python -m tradebot.live.bridge send modify --to … --symbol … --id L-1 --sl 19990 --ref 20010
    python -m tradebot.live.bridge send flatten|sync --to … --symbol …
    python -m tradebot.live.bridge tail    --to … --symbol … [-n 20]       # udalosti exekútora (evt.jsonl)
    python -m tradebot.live.bridge hb      --to … --symbol … [--seconds 300]   # heartbeat mastera (inak ho exekútor
                                                                           # po 30 s berie ako preč a preberá trailing)

Protokol nepíše druhý raz: volá ten istý C# `TradeBot.Core.BridgeMaster`, ktorý používa NinjaTrader. Inštancia
(adresár route) je predvolene `manual_<symbol>`; ceny `--e/--sl/--tp/--ref` sú v cenách mastera (napr. MNQ),
exekútor ich prepočíta cez basis. Koreň je `Common\\Files\\TradeBot` terminálov MT5 (`TRADEBOT_BRIDGE_ROOT`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .routes import PRICE_MODES, QTY_MODES


def _core():
    from tradebot.adapters.csharp import bridge

    bridge._load_clr()
    import TradeBot.Core as core

    return core


def _now() -> int:
    return int(time.time() * 1000)


def _root(args, core=None) -> str:
    """Koreň mosta: `--root`, inak `Bridge.DefaultRoot` — bez C# (`core=None`, príkazy, ktoré len čítajú súbory)
    jeho zrkadlo v Pythone (`TRADEBOT_BRIDGE_ROOT`, inak `%APPDATA%/MetaQuotes/Terminal/Common/Files/TradeBot`)."""
    if args.root:
        return args.root
    if core is not None:
        return str(core.Bridge.DefaultRoot())
    env = os.environ.get("TRADEBOT_BRIDGE_ROOT")
    if env:
        return env
    return str(Path(os.environ.get("APPDATA") or Path.home()) / "MetaQuotes" / "Terminal" / "Common" / "Files" / "TradeBot")


def _master(args, core):
    spec = core.RouteSpec()
    spec.To = args.to
    spec.Instance = args.instance or f"manual_{args.symbol}"
    spec.Deployment = "manual"
    spec.Symbol = args.symbol
    spec.Price = args.price
    spec.Scale = args.scale
    spec.QtyMode = args.qty_mode
    spec.Lots = args.lots
    spec.Magic = args.magic
    spec.NtSymbol = args.nt_symbol
    spec.NtPointValue = args.nt_point_value
    spec.NtTick = args.nt_tick
    spec.Tf = args.tf
    return core.BridgeMaster(_root(args, core), spec)


def _status(master) -> tuple[str, str]:
    from System import String

    state, detail = master.Status(_now(), String(""))
    return str(state), str(detail)


def cmd_execs(args) -> int:
    exec_dir = Path(_root(args)) / "exec"
    files = sorted(exec_dir.glob("*.hb.json")) if exec_dir.is_dir() else []
    if not files:
        print(f"žiadny exekútor v {exec_dir}")
        return 1
    for f in files:
        try:
            hb = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            print(f"{f.name}: nečitateľný ({exc})")
            continue
        age = (_now() - int(hb.get("t", 0))) / 1000
        print(f"{hb.get('id')}  pred {age:.0f} s  {hb.get('margin_mode')}  pripojený={hb.get('connected')}  "
              f"AutoTrading={hb.get('trade_allowed')}  symbolov {len(hb.get('symbols', []))}")
        for r in hb.get("routes", []):
            print(f"    route {r['id']}: {r['state']} {r.get('detail', '')}")
    return 0


def cmd_status(args) -> int:
    core = _core()
    state, detail = _status(_master(args, core))
    print(state, detail)
    return 0 if state == "ok" else 1


def cmd_send(args) -> int:
    core = _core()
    m = _master(args, core)
    now = _now()
    state, detail = _status(m)
    if state != "ok":
        print(f"pozor: route je {state} ({detail}) — príkaz sa zapíše, exekútor ho vybaví, keď bude vedieť")
    if args.action == "entry":
        d = core.Direction.Long if args.dir == "long" else core.Direction.Short
        intent = core.OrderIntent(core.OrderAction.Entry, args.id, 0, "manual")
        intent.Direction = d
        intent.OrderType = getattr(core.OrderType, args.ot)
        intent.Plan = core.TradePlan(d, args.e, args.sl, args.tp, args.q, abs(args.e - args.sl), None)
        if args.close_in or args.cancel_in or args.hold:
            life = core.OrderLife()
            life.CloseAtMs = now + int(args.close_in * 1000) if args.close_in else 0
            life.CancelAtMs = now + int(args.cancel_in * 1000) if args.cancel_in else 0
            life.HoldMs = int(args.hold * 1000) if args.hold else 0
            intent.Life = life
        cid = m.Entry(now, intent, args.ref or args.e, now + int(args.exp * 1000))
    elif args.action == "cancel":
        cid = m.Cancel(now, args.id, "manual")
    elif args.action == "close":
        cid = m.Close(now, args.id, "manual")
    elif args.action == "modify":
        cid = m.Modify(now, args.id, args.sl, args.tp, args.ref or 0.0, "manual")   # None = nemenené
    elif args.action == "flatten":
        cid = m.Flatten(now, "manual")
    else:
        cid = m.Sync(now)
    m.Heartbeat(now, "manual")
    print(f"{args.action} -> {m.Instance} (cid {cid})")
    return 0


def cmd_tail(args) -> int:
    path = Path(_root(args)) / "bridge" / (args.instance or f"manual_{args.symbol}") / "evt.jsonl"
    if not path.exists():
        print(f"{path} ešte neexistuje")
        return 1
    lines = path.read_text(encoding="utf-8").splitlines()[-args.n:]
    for line in lines:
        print(line)
    return 0


def cmd_hb(args) -> int:
    core = _core()
    m = _master(args, core)
    end = time.time() + args.seconds
    while True:
        m.Heartbeat(_now(), "manual")
        if time.time() >= end:
            return 0
        time.sleep(1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("execs", "status", "send", "tail", "hb"))
    ap.add_argument("action", nargs="?", choices=("entry", "cancel", "close", "modify", "flatten", "sync"))
    ap.add_argument("--root", help="Common\\Files\\TradeBot (predvolene terminálov MT5)")
    ap.add_argument("--to", help="id exekútora (mt5exec_<login>-<server>, pozri `execs`)")
    ap.add_argument("--symbol", default="US100.cash", help="symbol u brokera exekútora")
    ap.add_argument("--instance", help="adresár route (predvolene manual_<symbol>)")
    ap.add_argument("--price", default=PRICE_MODES[0], choices=PRICE_MODES)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--qty-mode", default=QTY_MODES[0], choices=QTY_MODES)
    ap.add_argument("--lots", type=float, default=0.0, help="qty-mode fixed: loty na kontrakt")
    ap.add_argument("--magic", type=int, default=990001)
    ap.add_argument("--nt-symbol", default="MNQ")
    ap.add_argument("--nt-point-value", type=float, default=2.0)
    ap.add_argument("--nt-tick", type=float, default=0.25)
    ap.add_argument("--tf", type=int, default=3)
    ap.add_argument("--id", default="M-1", help="id vstupu")
    ap.add_argument("--dir", choices=("long", "short"), default="long")
    ap.add_argument("--ot", choices=("Limit", "Market", "Stop"), default="Limit")
    ap.add_argument("--e", type=float, default=0.0)
    ap.add_argument("--sl", type=float)
    ap.add_argument("--tp", type=float)
    ap.add_argument("--q", type=float, default=1.0)
    ap.add_argument("--ref", type=float, default=0.0, help="posledná cena mastera (predvolene --e)")
    ap.add_argument("--exp", type=float, default=60.0, help="vstup sa smie poslať brokerovi do toľkých sekúnd")
    ap.add_argument("--close-in", type=float, default=0.0, help="life.close_at o toľko sekúnd")
    ap.add_argument("--cancel-in", type=float, default=0.0, help="life.cancel_at o toľko sekúnd")
    ap.add_argument("--hold", type=float, default=0.0, help="life.hold_ms v sekundách")
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--seconds", type=int, default=300)
    args = ap.parse_args(argv)
    if args.command == "execs":
        return cmd_execs(args)
    if not args.to:
        raise SystemExit("zadaj --to (id exekútora, pozri `execs`)")
    if args.command == "send":
        if not args.action:
            raise SystemExit("send: zadaj akciu (entry, cancel, close, modify, flatten, sync)")
        if args.action == "entry" and (not args.e or args.sl is None or args.tp is None):
            raise SystemExit("send entry: zadaj --e, --sl a --tp")
        if args.action == "modify" and args.sl is None and args.tp is None:
            raise SystemExit("send modify: zadaj --sl alebo --tp (prázdny modify nič nemení)")
        return cmd_send(args)
    return {"status": cmd_status, "tail": cmd_tail, "hb": cmd_hb}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
