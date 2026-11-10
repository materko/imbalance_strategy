"""`python -m tester.faultsim scenar.json [-v]` — prehrá scenár porúch a vypíše stav po každom kroku.

Návratový kód 1, keď scenár nedobehol alebo po poslednom kroku ostala pozícia bez stopu, order bez pozície
či pozícia, o ktorej inštancia nevie. Scenár: docs/SIMULATOR_PORUCH.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import BuildError, SimError, ensure_sim, run


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.faultsim", description=__doc__.splitlines()[0])
    ap.add_argument("scenario", nargs="?", help="JSON so scenárom (`engine`, `steps`); bez neho sa simulátor len preloží")
    ap.add_argument("-v", "--verbose", action="store_true", help="aj požiadavky na brokera a log inštancie")
    ap.add_argument("--build", action="store_true", help="preložiť simulátor znova")
    args = ap.parse_args(argv)
    try:
        exe = ensure_sim(force=args.build)
        if not args.scenario:
            print(f"OK: {exe}")
            return 0
        out = run(json.loads(Path(args.scenario).read_text(encoding="utf-8")))
    except (BuildError, SimError, OSError, ValueError) as exc:
        print(f"CHYBA: {exc}", file=sys.stderr)
        return 2
    for s in out["trace"]:
        flags = [name for name in ("naked", "orphans", "unknown") if s[name]]
        orders = ", ".join(f"{w['name']} {w['type']} x{w['qty']} @{w['price']}" for w in s["working"]) or "-"
        tracked = ", ".join(f"{t['id']}:{t['open']}" + (" parked" if t["parked"] else "") + (f" {t['closing']}" if t["closing"] else "")
                            for t in s["tracked"]) or "-"
        print(f"{s['t']} {s['step']:<28} pozícia {s['position']:>2} | u brokera: {orders} | sleduje: {tracked}"
              + (f" | ruší sa {s['dying']}" if s["dying"] else "") + (f" | POZOR {' '.join(flags)}" if flags else ""))
    if args.verbose:
        print("\npožiadavky na brokera:\n  " + "\n  ".join(out["requests"]))
        print("\nlog inštancie:\n  " + "\n  ".join(out["log"]))
    if out["error"]:
        print(f"\nCHYBA: {out['error']}", file=sys.stderr)
        return 1
    last = out["trace"][-1]
    return 1 if last["naked"] or last["orphans"] or last["unknown"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
