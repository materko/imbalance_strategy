"""Skutočný spread u brokera zo živých dát (bod 2 zadania z 28. 11. 2026, docs/DATA.md §D).

Zdroj je sklad spreadu `data/live/spread/<platforma>/<symbol>/<YYYY-MM>.feather` (`tester.livedata`), ktorý plní
telemetria `m1` (docs/LIVE.md). Zapisuje ho MT5 EA z `CopyRates(PERIOD_M1)` (spread sviečky od brokera, aj 3 dni
predhistórie) a naživo z tikov, NinjaTrader AddOn z L1 kotácií. Report spread rozdelí:

* po **hodinách dňa** v pásme `--zone` (predvolene New York): medián, 90. percentil a maximum za minútu,
* **pri správach** (±`--news-min` minút od udalosti z kalendára SPRÁV, NFP/CPI/FOMC…) a mimo nich.

Výstup `--json` je vstup pre spread v emulátore (bod 3): `hours[h]` = rozdelenie spreadu v hodine `h`.

    python -m tester.spread list                                  # čo je v sklade (git + hub)
    python -m tester.spread report --platform mt5 --symbol US100.cash
    python -m tester.spread report --platform mt5 --symbol US100.cash --json spread_us100.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

__all__ = ["profile", "available", "main"]

#: Ktorý stĺpec skladu je meradlo: priemer z tikov, keď je, inak spread sviečky od brokera.
COLUMNS = ("spread_avg", "spread")


def available(root: Path | str | None = None) -> list[dict[str, Any]]:
    """Symboly so spreadom v sklade: platforma, symbol, prvá a posledná minúta, počet minút."""
    from tester import livedata

    seen: dict[tuple[str, str], None] = {}
    for r in livedata._roots(root):
        base = Path(r) / "spread"
        if base.is_dir():
            for plat in sorted(p for p in base.iterdir() if p.is_dir()):
                for sym in sorted(p for p in plat.iterdir() if p.is_dir()):
                    seen[(plat.name, sym.name)] = None
    out = []
    for plat, sym in seen:
        df = livedata.load_spread(plat, sym, root)
        if df.empty:
            continue
        out.append({"platform": plat, "symbol": sym, "from": df["date"].iloc[0].isoformat(),
                    "to": df["date"].iloc[-1].isoformat(), "minutes": len(df)})
    return out


def _stats(values) -> dict[str, Any]:
    v = values.dropna()
    if v.empty:
        return {"n": 0}
    return {"n": int(len(v)), "median": float(v.median()), "p90": float(v.quantile(0.9)), "max": float(v.max()),
            "mean": float(v.mean())}


def _news_mask(dates, minutes: int):
    """Minúty do `minutes` od udalosti kalendára SPRÁV (čas v UTC ms); bez kalendára nič."""
    import numpy as np

    try:
        from tradebot.strategies.spravy import calendar as cal
        events = np.array(sorted(ms for ms, _ in cal.events_utc()), dtype="int64")
    except Exception:  # noqa: BLE001 - kalendár je doplnok reportu, bez neho len hodiny
        return None
    if events.size == 0:
        return None
    ms = dates.astype("int64").to_numpy() // 1_000_000
    idx = np.clip(np.searchsorted(events, ms), 1, events.size - 1)
    near = np.minimum(np.abs(ms - events[idx - 1]), np.abs(ms - events[idx]))
    return near <= minutes * 60_000


def profile(platform: str, symbol: str, *, zone: str = "America/New_York", news_min: int = 5,
            root: Path | str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    """Rozdelenie spreadu symbolu po hodinách dňa v pásme `zone` a pri správach (v cene, nie v bodoch)."""
    import pandas as pd

    from tester import livedata

    df = livedata.load_spread(platform, symbol, root)
    if start:
        df = df[df["date"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["date"] < pd.Timestamp(end, tz="UTC")]
    out: dict[str, Any] = {"platform": platform, "symbol": symbol, "zone": zone, "minutes": int(len(df))}
    if df.empty:
        return out
    # meradlo po minútach: priemer z tikov, kde je, inak spread sviečky
    value = df["spread_avg"].where(df["spread_avg"].notna(), df["spread"])
    out.update({"from": df["date"].iloc[0].isoformat(), "to": df["date"].iloc[-1].isoformat(),
                "ticks_share": float(df["spread_avg"].notna().mean()),
                "all": _stats(value), "max_tick": _stats(df["spread_max"])})
    local = df["date"].dt.tz_convert(zone)
    out["hours"] = {str(h): _stats(value[local.dt.hour == h]) for h in range(24)}
    out["weekdays"] = {str(d): _stats(value[local.dt.dayofweek == d]) for d in range(7)}
    mask = _news_mask(df["date"], news_min)
    if mask is not None:
        out["news"] = {"window_min": news_min, "near": _stats(value[mask]), "other": _stats(value[~mask]),
                       "near_max_tick": _stats(df["spread_max"][mask])}
    return out


# -- U3: história tikov brokera (TradeBotSpreadExport.mq5) ------------------- #

#: Tabuľka CFD v §3 SMERNICE V2 (O = voľba / odhad): S hlavnej seansy v cene a násobky pre okná. Meranie z histórie
#: tikov ju má nahradiť; rozdiel p75 > 0,5 S znamená návrh novej tabuľky (schvaľuje používateľ, ZADANIE U3.4).
CFD_TABLE: dict[str, dict[str, float]] = {
    "US100.cash": {"S": 2.0, "off": 2.0, "open": 2.0, "news": 4.0},
    "US500.cash": {"S": 0.8, "off": 2.0, "open": 2.0, "news": 4.0},
    "XAUUSD": {"S": 0.40, "off": 2.0, "open": 2.0, "news": 5.0},
}
#: hlavná seansa a otvorenie New Yorku (minúty od polnoci NY)
RTH = (9 * 60 + 30, 16 * 60)
NY_OPEN = (9 * 60 + 30, 9 * 60 + 40)


def _header(line: str) -> dict[str, str]:
    return dict(kv.split("=", 1) for kv in line.lstrip("#").strip().split(";") if "=" in kv)


def read_tick_histogram(path: Path | str):
    """`<symbol>_ticks.csv` z TradeBotSpreadExport → (hlavička, DataFrame `date` UTC, `spread` v cene, `n` tikov)."""
    import pandas as pd

    path = Path(path)
    with path.open(encoding="utf-8", errors="replace") as f:
        head = _header(f.readline())
        point = float(head.get("point") or 0) or 1.0
        dates, spreads, counts = [], [], []
        for line in f:
            parts = line.strip().split(";")
            if len(parts) < 3 or not parts[2]:
                continue
            for item in parts[2].split("|"):
                v, _, c = item.partition(":")
                try:
                    spreads.append(int(v) * point)
                    counts.append(int(c))
                except ValueError:
                    continue
                dates.append(parts[0])
    df = pd.DataFrame({"date": pd.to_datetime(dates, format="%Y.%m.%d %H:%M", utc=True), "spread": spreads, "n": counts})
    return head, df


def read_m1(path: Path | str):
    """`<symbol>_m1.csv` → DataFrame `date` UTC, `spread` v cene (spread sviečky od brokera)."""
    import pandas as pd

    path = Path(path)
    with path.open(encoding="utf-8", errors="replace") as f:
        head = _header(f.readline())
    point = float(head.get("point") or 0) or 1.0
    df = pd.read_csv(path, sep=";", skiprows=1, names=["date", "spread"])
    df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d %H:%M", utc=True)
    df["spread"] = df["spread"] * point
    return df


def _wpct(values, weights, qs=(0.5, 0.75, 0.95)) -> dict[str, float]:
    import numpy as np

    v = np.asarray(values, dtype="float64")
    w = np.asarray(weights, dtype="float64")
    if v.size == 0 or w.sum() <= 0:
        return {}
    order = np.argsort(v)
    v, w = v[order], w[order]
    cum = np.cumsum(w) / w.sum()
    return {f"p{int(q * 100)}": float(v[min(np.searchsorted(cum, q), v.size - 1)]) for q in qs}


def _window(df, mask) -> dict[str, Any]:
    part = df[mask]
    out: dict[str, Any] = {"ticks": int(part["n"].sum()), "minutes": int(part["date"].nunique())}
    out.update(_wpct(part["spread"], part["n"]))
    return out


def news_events(minutes: int = 5) -> dict[str, list[int]]:
    """Udalosti `calendar_us.json` po typoch (FOMC, CPI, NFP…) ako UTC ms."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from tester import calendar as cal

    ny = ZoneInfo("America/New_York")
    out: dict[str, list[int]] = {}
    for key, blok in (cal._raw().get("events") or {}).items():
        hh, mm = (blok.get("time_et") or "08:30").split(":")
        for d in blok.get("dates") or ():
            try:
                y, m, dd = (int(x) for x in d.split("-"))
            except ValueError:
                continue
            t = datetime(y, m, dd, int(hh), int(mm), tzinfo=ny)
            out.setdefault(key, []).append(int(t.timestamp() * 1000))
    return {k: sorted(v) for k, v in out.items()}


def history_profile(ticks_csv: Path | str, m1_csv: Path | str | None = None, *, news_min: int = 5) -> dict[str, Any]:
    """Tabuľka U3 pre jeden symbol: p50/p75/p95 spreadu a počet tikov po 30-min úsekoch času New York, v hlavnej
    seanse 9:30–16:00, pri otvorení 9:30–9:40, ±`news_min` min okolo správ (po type) a mimo hlavnej seansy."""
    import numpy as np

    head, df = read_tick_histogram(ticks_csv)
    sym = head.get("symbol") or Path(ticks_csv).stem.replace("_ticks", "")
    out: dict[str, Any] = {"symbol": sym, "header": head, "ticks": int(df["n"].sum())}
    if df.empty:
        return out
    out.update({"from": df["date"].min().isoformat(), "to": df["date"].max().isoformat()})
    local = df["date"].dt.tz_convert("America/New_York")
    mins = (local.dt.hour * 60 + local.dt.minute).to_numpy()
    weekday = (local.dt.dayofweek < 5).to_numpy()
    rth = weekday & (mins >= RTH[0]) & (mins < RTH[1])
    out["slots"] = {}
    for start in range(0, 24 * 60, 30):
        w = _window(df, (mins >= start) & (mins < start + 30))
        if w["ticks"]:
            out["slots"][f"{start // 60:02d}:{start % 60:02d}"] = w
    out["rth"] = _window(df, rth)
    out["open"] = _window(df, weekday & (mins >= NY_OPEN[0]) & (mins < NY_OPEN[1]))
    out["off"] = _window(df, ~rth)
    ms = df["date"].astype("int64").to_numpy() // 1_000_000
    out["news"] = {}
    for key, events in news_events().items():
        ev = np.asarray(events, dtype="int64")
        if ev.size == 0:
            continue
        idx = np.clip(np.searchsorted(ev, ms), 1, ev.size - 1)
        near = np.minimum(np.abs(ms - ev[idx - 1]), np.abs(ms - ev[idx])) <= news_min * 60_000
        w = _window(df, near)
        if w["ticks"]:
            out["news"][key] = w
    if m1_csv and Path(m1_csv).exists():
        m1 = read_m1(m1_csv)
        lm = m1["date"].dt.tz_convert("America/New_York")
        mm = (lm.dt.hour * 60 + lm.dt.minute)
        r = (lm.dt.dayofweek < 5) & (mm >= RTH[0]) & (mm < RTH[1])
        out["m1"] = {"bars": int(len(m1)), "rth": _wpct(m1["spread"][r], np.ones(int(r.sum()))),
                     "off": _wpct(m1["spread"][~r], np.ones(int((~r).sum())))}
    out["compare"] = compare_table(out)
    return out


def compare_table(p: dict[str, Any]) -> list[dict[str, Any]]:
    """Nameraný p75 proti tabuľke §3 (S, S×2 mimo seansy, S×2 pri otvorení, S×4/5 pri správach); `propose` = rozdiel
    väčší ako 0,5 S (ZADANIE U3.4 — zmenu tabuľky schvaľuje používateľ)."""
    t = CFD_TABLE.get(str(p.get("symbol")))
    if not t:
        return []
    s = t["S"]
    rows = []
    news = [w for w in (p.get("news") or {}).values() if w.get("p75") is not None]
    news_p75 = max((w["p75"] for w in news), default=None)
    for name, measured, table in (("hlavná seansa", (p.get("rth") or {}).get("p75"), s),
                                  ("mimo seansy", (p.get("off") or {}).get("p75"), s * t["off"]),
                                  ("NY open 9:30–9:40", (p.get("open") or {}).get("p75"), s * t["open"]),
                                  ("správy ±5 min (najhorší typ)", news_p75, s * t["news"])):
        rows.append({"window": name, "table": table, "p75": measured,
                     "propose": measured is not None and abs(measured - table) > 0.5 * s})
    return rows


def history_markdown(profiles: list[dict[str, Any]], *, command: str = "") -> str:
    from datetime import date

    def f(v: Any) -> str:
        return "—" if v is None else f"{v:.4g}".replace(".", ",")

    lines = [f"# Spread CFD z histórie tikov brokera ({date.today().isoformat()})", "",
             "*SMERNICA V2 §3, zadanie U3. Zdroj: `TradeBotSpreadExport.mq5` (CopyTicks bid/ask, spread M1), spracované "
             "`python -m tester.spread history`. Spread je v cene (body indexu, $ pri zlate). Okná v čase New York.*", ""]
    if command:
        lines += ["```", command, "```", ""]
    for p in profiles:
        lines += [f"## {p['symbol']}", "", f"{p.get('ticks', 0):,} tikov, {p.get('from', '—')[:10]} – {p.get('to', '—')[:10]}"
                  .replace(",", " "), ""]
        lines += ["| okno | tikov | p50 | p75 | p95 |", "|---|---|---|---|---|"]
        for name, key in (("hlavná seansa 9:30–16:00", "rth"), ("otvorenie 9:30–9:40", "open"), ("mimo hlavnej seansy", "off")):
            w = p.get(key) or {}
            lines.append(f"| {name} | {w.get('ticks', 0)} | {f(w.get('p50'))} | {f(w.get('p75'))} | {f(w.get('p95'))} |")
        for k, w in sorted((p.get("news") or {}).items()):
            lines.append(f"| správy {k} ±5 min | {w.get('ticks', 0)} | {f(w.get('p50'))} | {f(w.get('p75'))} | {f(w.get('p95'))} |")
        lines += ["", "Po 30-min úsekoch (New York):", "", "| úsek | tikov | p50 | p75 | p95 |", "|---|---|---|---|---|"]
        for k, w in (p.get("slots") or {}).items():
            lines.append(f"| {k} | {w['ticks']} | {f(w.get('p50'))} | {f(w.get('p75'))} | {f(w.get('p95'))} |")
        if p.get("m1"):
            m = p["m1"]
            lines += ["", f"Spread M1 sviečok ({m['bars']} sviečok): hlavná seansa p75 {f(m['rth'].get('p75'))}, "
                          f"mimo p75 {f(m['off'].get('p75'))}."]
        if p.get("compare"):
            lines += ["", "Proti tabuľke §3:", "", "| okno | tabuľka | nameraný p75 | rozdiel > 0,5 S |", "|---|---|---|---|"]
            for r in p["compare"]:
                lines.append(f"| {r['window']} | {f(r['table'])} | {f(r['p75'])} | {'**áno – návrh novej hodnoty**' if r['propose'] else 'nie'} |")
        lines.append("")
    lines += ["## Záver", "", "_(dopíše človek: či sa tabuľka §3 mení — schvaľuje používateľ)_", ""]
    return "\n".join(lines)


def _fmt(v: Any) -> str:
    return "—" if v is None else f"{v:.5g}"


def _print(p: dict[str, Any]) -> None:
    print(f"{p['platform']} {p['symbol']}: {p['minutes']} minút", end="")
    if not p["minutes"]:
        print(" — spread v sklade nie je (telemetria m1 bez `sp`/`spa`; starý EA alebo DLL?)")
        return
    print(f" ({p['from'][:16]} – {p['to'][:16]} UTC), z tikov {p['ticks_share'] * 100:.0f} %")
    a = p["all"]
    print(f"  celkom: medián {_fmt(a.get('median'))}, p90 {_fmt(a.get('p90'))}, max {_fmt(a.get('max'))}"
          f" (max z tikov {_fmt(p['max_tick'].get('max'))})")
    print(f"  po hodinách ({p['zone']}):  hod   minút   medián      p90      max")
    for h in range(24):
        s = p["hours"][str(h)]
        if s["n"]:
            print(f"                          {h:>3} {s['n']:>7} {_fmt(s['median']):>8} {_fmt(s['p90']):>8} {_fmt(s['max']):>8}")
    if "news" in p:
        n, o = p["news"]["near"], p["news"]["other"]
        print(f"  správy ±{p['news']['window_min']} min: {n['n']} minút, medián {_fmt(n.get('median'))}, p90 {_fmt(n.get('p90'))},"
              f" max z tikov {_fmt(p['news']['near_max_tick'].get('max'))}; mimo správ medián {_fmt(o.get('median'))},"
              f" p90 {_fmt(o.get('p90'))}")


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.spread", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("list", help="symboly so spreadom v sklade (git + hub)")
    rp = sub.add_parser("report", help="spread po hodinách a pri správach")
    rp.add_argument("--platform", required=True, help="mt5 / ninjatrader")
    rp.add_argument("--symbol", required=True, help="symbol u brokera (napr. US100.cash)")
    rp.add_argument("--zone", default="America/New_York", help="pásmo hodín dňa (IANA)")
    rp.add_argument("--news-min", type=int, default=5, help="okno okolo správy v minútach")
    rp.add_argument("--from", dest="start", help="od dátumu (UTC, YYYY-MM-DD)")
    rp.add_argument("--to", dest="end", help="do dátumu (UTC, bez neho)")
    rp.add_argument("--json", help="zapísať rozdelenie do súboru (vstup pre emulátor)")
    for p in (lp, rp):
        p.add_argument("--root", help="koreň stromu data/live (predvolene git + hub)")
    hp = sub.add_parser("history", help="U3: spread z histórie tikov brokera (TradeBotSpreadExport.mq5)")
    hp.add_argument("--dir", required=True, help="adresár s <symbol>_ticks.csv a <symbol>_m1.csv (MT5 Common/Files/TradeBot/spread)")
    hp.add_argument("--symbols", help="symboly oddelené čiarkou (predvolene všetko v adresári)")
    hp.add_argument("--news-min", type=int, default=5)
    hp.add_argument("--json", help="zapísať profily do JSON (vstup pre fill v2 CFD)")
    hp.add_argument("--write", action="store_true", help="zapísať docs/merania/<dnes>-cfd-spread.md")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "history":
        from datetime import date

        from tradebot.core.paths import MERANIA_DIR

        d = Path(args.dir)
        syms = [s.strip() for s in args.symbols.split(",")] if args.symbols else             sorted(p.name[: -len("_ticks.csv")] for p in d.glob("*_ticks.csv"))
        profs = []
        for s in syms:
            ticks = d / f"{s}_ticks.csv"
            if not ticks.exists():
                print(f"{s}: {ticks} chýba")
                continue
            pr = history_profile(ticks, d / f"{s}_m1.csv", news_min=args.news_min)
            profs.append(pr)
            r, o, op = pr.get("rth") or {}, pr.get("off") or {}, pr.get("open") or {}
            print(f"{pr['symbol']}: {pr['ticks']} tikov; hlavná seansa p50/p75/p95 {_fmt(r.get('p50'))}/{_fmt(r.get('p75'))}/"
                  f"{_fmt(r.get('p95'))}, otvorenie p75 {_fmt(op.get('p75'))}, mimo seansy p75 {_fmt(o.get('p75'))}")
            for c in pr.get("compare") or []:
                if c["propose"]:
                    print(f"  {c['window']}: tabuľka {_fmt(c['table'])}, nameraný p75 {_fmt(c['p75'])} -> návrh novej hodnoty")
        if args.json:
            Path(args.json).write_text(json.dumps(profs, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.write and profs:
            out = MERANIA_DIR / f"{date.today().isoformat()}-cfd-spread.md"
            out.write_text(history_markdown(profs, command="python -m tester.spread history --dir <adresár> --write"),
                           encoding="utf-8")
            print(f"zapísané: {out}")
        return 0 if profs else 1
    if args.cmd == "list":
        rows = available(args.root)
        if not rows:
            print("sklad spreadu je prázdny")
        for r in rows:
            print(f"{r['platform']:<12} {r['symbol']:<16} {r['minutes']:>8} minút  {r['from'][:10]} – {r['to'][:10]}")
        return 0
    p = profile(args.platform, args.symbol, zone=args.zone, news_min=args.news_min, root=args.root,
                start=args.start, end=args.end)
    _print(p)
    if args.json:
        Path(args.json).write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"zapísané: {args.json}")
    return 0 if p["minutes"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
