"""Dáva C# jadro na inom stroji / runtime (Mono na macOS a Linuxe) to isté čo na Windows?

    # 1. na stroji, kde je parita overená (Windows): nahraj volania enginu aj s odpoveďami
    python -m tester.compare.csharp_replay record --from 2026-08-24 --to 2026-09-04 --out replay.jsonl
    # 2. na druhom stroji (stačí holý Python 3 + Mono, netreba pandas ani Freqtrade): prehraj a porovnaj
    python3 -m tester.compare.csharp_replay verify replay.jsonl

`record` pustí bežné porovnanie `csharp_parity` a popri tom zapíše každé volanie transportu
(vytvorenie enginu, seeding, každý bar, `final_drawings`) spolu s odpoveďou. `verify` tie isté
volania pošle enginu na tomto stroji — preloží si ho (`mcs`), spustí pod Mono — a odpovede porovná
**na rovnosť**. Čísla idú ako bitové vzory, takže rozdiel v poslednom bite výpočtu by sa ukázal;
rovnako iné pravidlá letného času v časových pásmach seáns.

`verify` zámerne importuje len `tradebot.adapters.csharp` (štandardná knižnica), aby sa dal pustiť
na čistom stroji ešte pred inštaláciou zvyšku.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

__all__ = ["record", "verify", "main"]


def _hex(x: float) -> str:
    return struct.pack(">d", float(x)).hex()


def _unhex(s: str) -> float:
    return struct.unpack(">d", bytes.fromhex(s))[0]


def record(out: Path, profile: str, exchange: str, timeframe: str, date_from: str | None, date_to: str | None,
           overrides: dict[str, Any]) -> int:
    from tradebot.adapters.csharp import bridge
    from tradebot.core.candles import timeframe_minutes

    from . import csharp_parity

    original = bridge.open_transport
    lines: list[str] = []

    def dump(obj: dict[str, Any]) -> None:
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=True))

    def recording(key, config_json, instrument_json, chart_tf_minutes):
        t = original(key, config_json, instrument_json, chart_tf_minutes)
        engine_id = len([1 for ln in lines if ln.startswith('{"op":"create"')])
        dump({"op": "create", "e": engine_id, "key": key, "config": config_json, "instrument": instrument_json,
              "tf": chart_tf_minutes, "reply": t.info})
        on_bar, final, seed = t.on_bar, t.final_drawings, t.seed

        def rec_bar(ts, ohlcv, htf, position, daily_limit, open_ids):
            reply = on_bar(ts, ohlcv, htf, position, daily_limit, open_ids)
            dump({"op": "bar", "e": engine_id, "t": ts, "b": [_hex(x) for x in ohlcv],
                  "htf": None if htf is None else [htf[0], [_hex(x) for x in htf[1]], _hex(htf[2])],
                  "pos": _hex(position), "dl": bool(daily_limit), "ids": open_ids, "reply": reply})
            return reply

        def rec_final(ts, ohlcv):
            reply = final(ts, ohlcv)
            dump({"op": "final", "e": engine_id, "t": ts, "b": [_hex(x) for x in ohlcv], "reply": reply})
            return reply

        def rec_seed(name, times, values, has_partial):
            reply = seed(name, times, values, has_partial)
            dump({"op": "seed", "e": engine_id, "name": name, "t": list(times), "v": [_hex(x) for x in values],
                  "partial": bool(has_partial), "reply": reply})
            return reply

        t.on_bar, t.final_drawings, t.seed = rec_bar, rec_final, rec_seed
        return t

    # `CSharpEngine` si funkciu berie z modulu enginu, nie z bridge
    from tradebot.adapters.csharp import engine as engine_mod

    engine_mod.open_transport = recording
    try:
        res = csharp_parity.compare("ibs", "ibsninja", profile, exchange, timeframe_minutes(timeframe),
                                    date_from, date_to, overrides)
    finally:
        engine_mod.open_transport = original
    if res["mismatches"]:
        raise SystemExit(f"C# a Python engine sa na tomto stroji rozchádzajú ({len(res['mismatches'])}×) — nahrávka by nič nedokázala")
    out.write_text("\n".join(lines) + "\n", encoding="ascii")
    return len(lines)


def verify(path: Path, limit: int = 10) -> list[str]:
    from tradebot.adapters.csharp.bridge import bridge_mode, open_transport

    engines: dict[int, Any] = {}
    diffs: list[str] = []
    calls = 0
    with open(path, encoding="ascii") as fh:
        for line in fh:
            if not line.strip():
                continue
            c = json.loads(line)
            op, eid = c["op"], c["e"]
            if op == "create":
                engines[eid] = open_transport(c["key"], c["config"], c["instrument"], c["tf"])
                got = engines[eid].info
            elif op == "bar":
                htf = c["htf"]
                window = None if htf is None else (htf[0], [_unhex(x) for x in htf[1]], _unhex(htf[2]))
                got = engines[eid].on_bar(c["t"], [_unhex(x) for x in c["b"]], window, _unhex(c["pos"]), c["dl"], c["ids"])
            elif op == "final":
                got = engines[eid].final_drawings(c["t"], [_unhex(x) for x in c["b"]])
            else:
                got = engines[eid].seed(c["name"], c["t"], [_unhex(x) for x in c["v"]], c["partial"])
            calls += 1
            if got != c["reply"]:
                diffs.append(f"{op} t={c.get('t')}: čakal {json.dumps(c['reply'])[:300]}\n      dostal {json.dumps(got)[:300]}")
                if len(diffs) >= limit:
                    break
    for t in engines.values():
        t.close()
    print(f"{calls} volaní enginu cez most '{bridge_mode()}' na {sys.platform}: "
          + ("ZHODA so záznamom" if not diffs else f"{len(diffs)} ROZDIELOV"))
    return diffs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("record")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--profile", default="golden_binance_btcusdt_3m")
    r.add_argument("--exchange", default="binance")
    r.add_argument("--timeframe", default="3m")
    r.add_argument("--from", dest="date_from")
    r.add_argument("--to", dest="date_to")
    r.add_argument("--set", action="append", default=[], metavar="POLE=HODNOTA")
    v = sub.add_parser("verify")
    v.add_argument("file", type=Path)
    args = ap.parse_args(argv)

    if args.command == "record":
        from .csharp_parity import _value

        overrides = {k: _value(val) for k, val in (item.split("=", 1) for item in args.set)}
        n = record(args.out, args.profile, args.exchange, args.timeframe, args.date_from, args.date_to, overrides)
        print(f"OK: {n} volaní -> {args.out}")
        return 0
    diffs = verify(args.file)
    for d in diffs:
        print("  " + d)
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
