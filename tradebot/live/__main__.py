"""Ručné overenie live telemetrie na obchodnom PC.

    python -m tradebot.live status                 # korene spoolu, súbory, koľko čaká za kurzorom
    python -m tradebot.live tail [--instance X] [-n 20]   # posledné udalosti zo spoolu
    python -m tradebot.live ship [--once]          # posielať na hub z tester/agent.json (každých 5 s)

`ship` používa ten istý kurzor ako agent hubu (`tester/live/cursor.json`) — nepúšťaj ho
súbežne s bežiacim agentom, inak si kurzor prepisujú.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tradebot.core.paths import LIVE_CURSOR

from .spool import SpoolReader, default_roots

SHIP_INTERVAL = 5.0


def _fmt_t(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError, OverflowError):
        return str(ms)


def _short(ev: dict) -> str:
    k = ev.get("k")
    if k == "bar":
        return (f"bar {_fmt_t(ev.get('bt'))} o={ev.get('o')} h={ev.get('h')} l={ev.get('l')} c={ev.get('c')} "
                f"v={ev.get('v')} ready={ev.get('ready')} mb={ev.get('mb')}")
    if k == "order":
        p = ev.get("p") or {}
        return (f"order {ev.get('a')} {ev.get('id')} dir={ev.get('dir')} {ev.get('ot') or ''} "
                f"e={p.get('e')} sl={p.get('sl')} tp={p.get('tp')} q={p.get('q')} {ev.get('r') or ''}".rstrip())
    if k == "fill":
        return f"fill {ev.get('side')} {ev.get('id')} {ev.get('exit') or ''} @{ev.get('price')} x{ev.get('qty')}".replace("  ", " ")
    if k == "hello":
        return (f"hello {ev.get('platform')} {ev.get('account')} {ev.get('symbol')} {ev.get('tf')}m "
                f"{ev.get('strategy')} profil={ev.get('profile')} session={ev.get('session')} host={ev.get('host')}")
    if k == "event":
        return f"event zone={ev.get('z')} {ev.get('f')} -> {ev.get('to')} {ev.get('r') or ''}".rstrip()
    if k == "draw":
        return f"draw {len(ev.get('d') or [])} kresieb" + (" (final)" if ev.get("final") else "")
    if k == "note":
        return f"note [{ev.get('level') or 'info'}] {ev.get('text')}"
    if k == "stat":
        return "stat " + json.dumps(ev.get("stats"), ensure_ascii=False)
    if k == "bye":
        return f"bye {ev.get('reason') or ''}".rstrip()
    if k == "control":
        return f"control {ev.get('mode')} profil={ev.get('profile') or '(vstup)'} zdroj={ev.get('source') or ''}".rstrip()
    return json.dumps(ev, ensure_ascii=False)


def cmd_status(args: argparse.Namespace) -> int:
    reader = SpoolReader(default_roots(), Path(args.cursor))
    st = reader.status()
    if not st["roots"]:
        print("žiadny koreň spoolu (NinjaTrader, MT5 ani TRADEBOT_LIVE_SPOOL)")
        return 1
    print("korene:")
    for r in st["roots"]:
        print(f"  {r}")
    print(f"súbory: {len(st['files'])}, čaká za kurzorom: {st['pending_bytes']} B  (kurzor {reader.cursor_path})")
    for f in st["files"]:
        print(f"  {f['instance']}  {Path(f['path']).name}  {f['size']} B, kurzor {f['offset']}, čaká {f['pending']}")
    return 0


def cmd_tail(args: argparse.Namespace) -> int:
    # bez kurzora: prečítať celý spool a ukázať posledných n udalostí (`read` kurzor nezapisuje)
    reader = SpoolReader(default_roots(), Path(args.cursor))
    reader.cursor = {}
    posledne: list[tuple[str, dict]] = []
    for b in reader.read(max_events=10 ** 9):
        if args.instance and b.instance != args.instance:
            continue
        posledne.extend((b.instance, ev) for ev in b.events)
    posledne.sort(key=lambda t: (t[1].get("t", 0), t[1].get("seq", 0)))
    for inst, ev in posledne[-args.n:]:
        print(f"{_fmt_t(ev.get('t'))}  {inst}  #{ev.get('seq')}  {_short(ev)}")
    if not posledne:
        print("nič v spoole" + (f" pre inštanciu {args.instance}" if args.instance else ""))
    return 0


def cmd_ship(args: argparse.Namespace) -> int:
    from tester.hub import config as agent_config
    from tester.hub.client import HubHttp

    from .shipper import LiveShipper

    cfg = agent_config.load()
    if cfg is None:
        raise SystemExit("agent nie je nastavený (tester/agent.json): python -m tester.hub setup …")
    roots = default_roots()
    if not roots:
        raise SystemExit("žiadny koreň spoolu (NinjaTrader, MT5 ani TRADEBOT_LIVE_SPOOL)")
    shipper = LiveShipper(SpoolReader(roots, Path(args.cursor)), HubHttp(cfg.hub_url, cfg.token), cfg.name)
    print(f"posielam ako {cfg.name!r} na {cfg.hub_url} z {', '.join(str(r) for r in roots)}", flush=True)
    while True:
        r = shipper.pump()
        if r["sent"] or r["error"]:
            print(f"{datetime.now().strftime('%H:%M:%S')}  poslané {r['sent']}, prijaté {r['accepted']}"
                  + (f", chyba: {r['error']}" if r["error"] else ""), flush=True)
        if args.once:
            return 0 if not r["error"] else 1
        time.sleep(SHIP_INTERVAL)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tradebot.live", description="live telemetria zo spoolu platforiem")
    ap.add_argument("--cursor", default=str(LIVE_CURSOR), help="súbor kurzora (predvolene tester/live/cursor.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="korene spoolu, súbory a koľko čaká za kurzorom").set_defaults(fn=cmd_status)
    t = sub.add_parser("tail", help="posledné udalosti zo spoolu")
    t.add_argument("--instance", help="len táto inštancia (adresár spoolu)")
    t.add_argument("-n", type=int, default=20, help="koľko udalostí (20)")
    t.set_defaults(fn=cmd_tail)
    s = sub.add_parser("ship", help="posielať spool na hub podľa tester/agent.json")
    s.add_argument("--once", action="store_true", help="jedno kolo a koniec")
    s.set_defaults(fn=cmd_ship)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
