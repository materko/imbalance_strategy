"""NinjaTrader 8 — dáta dnu, signály von.

    python -m tester.ninjatrader export --instrument mnq_databento --contract "MNQ 12-26" --from 2026-06-01 --to 2026-09-10
    python -m tester.ninjatrader compare --instrument mnq_databento --profile multicharts_mnq_3m \
        --from 2026-06-01 --to 2026-09-10 [--csv cesta\\k\\exportu.csv]

### export
NinjaTrader si históriu berie od poskytovateľa dát, alebo z textového súboru (*Tools → Import →
Historical Data*). Tu sa ten súbor vyrobí z **toho istého skladu 1m sviečok**, na akom bežia backtesty
v Testeri, takže beh v Strategy Analyzeri sa dá porovnať s behom emulátora na rovnakých dátach.
Formát minútových barov NinjaTradera: `yyyyMMdd HHmmss;open;high;low;close;volume`, čas **zatvorenia**
baru; pri importe zvoľ časové pásmo **UTC**. Súbor sa musí volať ako inštrument v NinjaTraderi
(`MNQ 12-26.Last.txt`) — náš rad je front-month bez back-adjustmentu, takže ceny sú skutočné, len
celý leží pod jedným kontraktom.

### compare
Adaptér s parametrom „Exportovat signaly" zapíše zámery enginu a prechody stavov do
`Documents\\NinjaTrader 8\\TradeBot\\logs\\*.csv`. `compare` prehrá ten istý C# engine nad tými istými
barmi v `EngineRunner` Testera a porovná, **čo engine chcel**: vstupy (bar, cena, SL, TP, veľkosť)
a prechody stavov zón. Fill model je iný (NinjaTrader plní po svojom), takže po prvom inak vyplnenom
orderi sa môžu rozísť stavy 4–5; stavy 0–3 a plány vstupov na fill modeli nezávisia a majú sedieť.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

from tradebot.core import load_profile
from tradebot.core.candles import resample_ohlcv, timeframe_minutes
from tradebot.core.paths import NINJATRADER_DATA
from tradebot.core.types import INSTRUMENTS, Bar
from tradebot.strategies import get_spec

from . import engines
from .quotemanager import num

__all__ = ["export", "reference", "read_export", "compare", "main"]


def _frame(inst_key: str, date_from: str | None, date_to: str | None):
    import pandas as pd

    inst = INSTRUMENTS[inst_key]
    src = engines.one_minute_file(inst)
    if not src.exists():
        raise SystemExit(f"chýbajú 1m sviečky {src} (python -m tester.data_archive merge)")
    df = pd.read_feather(src)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    if date_from:
        df = df[df["date"] >= pd.Timestamp(date_from, tz="UTC")]
    if date_to:
        df = df[df["date"] < pd.Timestamp(date_to, tz="UTC") + pd.Timedelta(days=1)]
    return inst, df.reset_index(drop=True)


def export(inst_key: str, contract: str, date_from: str | None, date_to: str | None, out: Path | None = None) -> Path:
    """1m sviečky zo skladu → textový súbor na import do NinjaTradera (čas zatvorenia baru, UTC)."""
    import pandas as pd

    _inst, df = _frame(inst_key, date_from, date_to)
    if df.empty:
        raise SystemExit("v zadanom okne nie sú žiadne sviečky")
    dst = out or NINJATRADER_DATA / f"{contract}.Last.txt"
    dst.parent.mkdir(parents=True, exist_ok=True)
    stamp = (df["date"] + pd.Timedelta(minutes=1)).dt.strftime("%Y%m%d %H%M%S")
    with open(dst, "w", encoding="ascii", newline="\r\n") as fh:
        for t, o, h, lo, c, v in zip(stamp, df["open"], df["high"], df["low"], df["close"], df["volume"]):
            fh.write(f"{t};{num(o)};{num(h)};{num(lo)};{num(c)};{int(round(v))}\n")
    return dst


def reference(strategy: str, profile: str, inst_key: str, timeframe: str,
              date_from: str | None, date_to: str | None) -> dict[str, list[tuple]]:
    """Čo chce engine nad barmi zo skladu — rovnaký tvar ako export adaptéra NinjaTrader."""
    from tradebot.adapters.freqtrade.runner import EngineRunner

    spec = get_spec(strategy)
    cfg, _profile_inst = load_profile(profile, strategy=strategy)
    inst, base = _frame(inst_key, date_from, date_to)
    minutes = timeframe_minutes(timeframe)

    def bars(tf_minutes: int):
        df = base if tf_minutes == 1 else resample_ohlcv(base, tf_minutes)
        ts = (df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()
        return [Bar(int(t), float(r.open), float(r.high), float(r.low), float(r.close), float(r.volume))
                for t, r in zip(ts, df.itertuples(index=False))]

    runner = EngineRunner(cfg, inst, minutes, spec=spec)
    if runner.htf is not None:
        # NinjaTrader kŕmi feeder uzavretými barmi po jednom, SMA objemu je obyčajný priemer
        for b in bars(timeframe_minutes(spec.informative_tfs(cfg)[0])):
            runner.htf.feed(b)

    captured: list = [None]
    original = runner.engine.on_bar

    def on_bar(bar, htf=None, ctx=None):
        captured[0] = original(bar, htf, ctx)
        return captured[0]

    runner.engine.on_bar = on_bar
    orders: list[tuple] = []
    events: list[tuple] = []
    for bar in bars(minutes):
        runner.process(bar, runner.htf.window_for(bar.time) if runner.htf is not None else None)
        out = captured[0]
        for i in out.orders:
            p = i.plan
            orders.append((bar.time, i.order_id, i.action.name.capitalize(),
                           None if p is None else (p.entry, p.stop_loss, p.take_profit, p.qty)))
        for e in out.events:
            events.append((bar.time, e.zone_uid, e.from_state, e.to_state))
    return {"orders": orders, "events": events}


def read_export(path: Path) -> dict[str, list[tuple]]:
    orders: list[tuple] = []
    events: list[tuple] = []
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            if row["kind"] == "order":
                plan = None if not row["entry"] else tuple(float(row[k]) for k in ("entry", "sl", "tp", "qty"))
                orders.append((int(row["bar_open_ms"]), row["id"], row["a"], plan))
            elif row["kind"] == "event":
                events.append((int(row["bar_open_ms"]), int(row["id"]), int(row["a"]), int(row["b"])))
    return {"orders": orders, "events": events}


def _latest_export() -> Path:
    logs = Path.home() / "Documents" / "NinjaTrader 8" / "TradeBot" / "logs"
    files = sorted(logs.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"v {logs} nie je žiadny export — zapni v stratégii „Exportovat signaly“ a spusti beh")
    return files[-1]


def compare(nt: dict[str, list[tuple]], ref: dict[str, list[tuple]]) -> dict:
    """Vstupy a prechody stavov: čo sedí, čo je len v jednom z behov (orezané na spoločné obdobie)."""
    def span(rows):
        return (min(r[0] for r in rows), max(r[0] for r in rows)) if rows else None

    # okno z udalostí aj orderov — stratégia bez stavového automatu (ORB) udalosti nemá
    a, b = span(nt["events"] + nt["orders"]), span(ref["events"] + ref["orders"])
    if a is None or b is None:
        return {"error": "jeden z behov nemá žiadne udalosti ani ordery", "nt": a, "ref": b}
    lo, hi = max(a[0], b[0]), min(a[1], b[1])

    def cut(rows):
        return [r for r in rows if lo <= r[0] <= hi]

    # Uid zóny v id vstupu (`LONG_8`) a v udalostiach je poradové číslo od štartu engine-u — platforma
    # s inou predhistóriou (MT5 prehrá 2×RequiredHistory barov pred štartom) má uidy posunuté, hoci
    # signály sú tie isté. Porovnáva sa preto bez uidu: vstup = (bar, strana, poradie v bare), udalosť
    # = (bar, zo stavu, do stavu) ako multimnožina.
    def entries(rows):
        out: dict = {}
        seen: dict = {}
        for r in cut(rows):
            if r[2] != "Entry":
                continue
            side = r[1].rsplit("_", 1)[0]
            n = seen.get((r[0], side), 0)
            seen[(r[0], side)] = n + 1
            out[(r[0], side, n)] = r[3]
        return out

    nt_e, ref_e = entries(nt["orders"]), entries(ref["orders"])
    same_plan = [k for k in nt_e if k in ref_e and _close(nt_e[k], ref_e[k])]
    # stavy 0-3 na fill modeli nezávisia; 4-5 áno (vyplnenie, OCO, timeout po vyplnení)
    early = lambda rows: Counter((r[0], r[2], r[3]) for r in cut(rows)  # noqa: E731
                                 if r[3] in (1, 2, 3, 4) or (r[3] == -1 and r[2] in (0, 1, 2, 3)))
    nt_ev, ref_ev = early(nt["events"]), early(ref["events"])
    return {
        "window_ms": (lo, hi),
        "entries": {"nt": len(nt_e), "ref": len(ref_e), "same_bar_and_plan": len(same_plan),
                    "only_nt": sorted(set(nt_e) - set(ref_e))[:10], "only_ref": sorted(set(ref_e) - set(nt_e))[:10],
                    "different_plan": [(k, nt_e[k], ref_e[k]) for k in nt_e if k in ref_e and not _close(nt_e[k], ref_e[k])][:10]},
        "zone_events": {"nt": sum(nt_ev.values()), "ref": sum(ref_ev.values()), "same": sum((nt_ev & ref_ev).values()),
                        "only_nt": sorted((nt_ev - ref_ev).elements())[:10], "only_ref": sorted((ref_ev - nt_ev).elements())[:10]},
    }


def _close(a, b, tol: float = 1e-9) -> bool:
    if a is None or b is None:
        return a is b
    return all(abs(x - y) <= tol * max(1.0, abs(x), abs(y)) for x, y in zip(a, b))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("export", "compare"):
        p = sub.add_parser(name)
        p.add_argument("--instrument", default="mnq_databento", help="kľúč inštrumentu v sklade sviečok")
        p.add_argument("--from", dest="date_from")
        p.add_argument("--to", dest="date_to")
        if name == "export":
            p.add_argument("--contract", default="MNQ 12-26", help="meno inštrumentu v NinjaTraderi")
            p.add_argument("--out", type=Path)
        else:
            p.add_argument("--strategy", default="ibsnet")
            p.add_argument("--profile", default="multicharts_mnq_3m")
            p.add_argument("--timeframe", default="3m")
            p.add_argument("--csv", type=Path, help="export z NinjaTradera (default: najnovší v TradeBot\\logs)")
    args = ap.parse_args(argv)

    if args.command == "export":
        dst = export(args.instrument, args.contract, args.date_from, args.date_to, args.out)
        print(f"OK: {dst}\nNinjaTrader: Tools > Import > Historical Data, Format NinjaTrader (end of bar), Time zone UTC")
        return 0

    path = args.csv or _latest_export()
    res = compare(read_export(path), reference(args.strategy, args.profile, args.instrument, args.timeframe,
                                               args.date_from, args.date_to))
    print(f"NinjaTrader export: {path}")
    if "error" in res:
        print(res)
        return 1
    e, z = res["entries"], res["zone_events"]
    print(f"vstupy:   NinjaTrader {e['nt']}, Tester {e['ref']}, zhodný bar aj plán {e['same_bar_and_plan']}")
    print(f"stavy zón (0-3): NinjaTrader {z['nt']}, Tester {z['ref']}, zhodných {z['same']}")
    for label, rows in (("vstupy len v NinjaTraderi", e["only_nt"]), ("vstupy len v Testeri", e["only_ref"]),
                        ("iný plán", e["different_plan"]), ("stavy len v NinjaTraderi", z["only_nt"]),
                        ("stavy len v Testeri", z["only_ref"])):
        if rows:
            print(f"  {label}: {rows}")
    return 0 if e["nt"] == e["ref"] == e["same_bar_and_plan"] and z["nt"] == z["ref"] == z["same"] else 1


if __name__ == "__main__":
    sys.exit(main())
