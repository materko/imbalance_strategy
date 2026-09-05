"""Príkazový riadok nad webapp — pre Claude Code a skripty, výsledky idú do histórie.

    python -m ibs.webapp.cli run --profile btcusdt_3m_binance_ny_sl_risk1 \\
        --set rrRatio=4 --set minSlDistance=0.25@pct --timerange 20250904-20260904 \\
        --note "RR 4 namiesto 5"
    python -m ibs.webapp.cli list "rrRatio>=4 pnl>0"
    python -m ibs.webapp.cli show 20260905-160921-0310ba
    python -m ibs.webapp.cli status          # beží webapp? čo je vo fronte? stav gitu
    python -m ibs.webapp.cli pull | push     # história behov z/na GitHub

`run` ide cez REST API bežiacej webapp (ak beží — beh sa objaví vo fronte aj
testerovi v prehliadači); keď webapp nebeží, spustí backtest priamo a uloží ho
do toho istého adresára `runs/`, takže história je rovnaká. Backtest cez holý
Freqtrade CLI sa do histórie NEdostane — preto tento nástroj.

`--set` hodnoty: `true`/`false`, čísla, text, JSON (`'{"value":0.2,"unit":"pct"}'`)
alebo skratka `hodnota@jednotka` pre veľkostné polia (`minSlDistance=0.2@pct`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = os.environ.get("IBS_WEB_URL", "http://127.0.0.1:8765")


# --------------------------------------------------------------------------- #
# pomocné
# --------------------------------------------------------------------------- #


def parse_set(item: str) -> tuple[str, Any]:
    """`kluc=hodnota` → (kluc, typovaná hodnota)."""
    if "=" not in item:
        raise SystemExit(f"--set očakáva kluc=hodnota, dostal {item!r}")
    key, raw = item.split("=", 1)
    key, raw = key.strip(), raw.strip()
    if "@" in raw and not raw.startswith("{"):
        val, unit = raw.rsplit("@", 1)
        return key, {"value": float(val), "unit": unit}
    low = raw.lower()
    if low in ("true", "false"):
        return key, low == "true"
    if low in ("null", "none"):
        return key, None
    try:
        return key, json.loads(raw)
    except json.JSONDecodeError:
        return key, raw


def api(url: str, path: str, body: dict | None = None, timeout: float = 30) -> Any:
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ct = r.headers.get("content-type", "")
        data = r.read()
        return json.loads(data) if "json" in ct else data.decode("utf-8", "replace")


def server_alive(url: str) -> bool:
    try:
        api(url, "/api/queue", timeout=3)
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def fmt_summary(rec: dict[str, Any]) -> str:
    r = rec.get("result") or {}
    s = rec.get("settings") or {}
    if rec.get("status") != "done":
        return f"{rec.get('id')}  {rec.get('status')}  {s.get('pair')} {s.get('timerange')}  {rec.get('error') or ''}"
    be = r.get("break_even_pct")
    return (
        f"{rec.get('id')}  {s.get('pair')} {s.get('timerange')}  "
        f"obchodov {r.get('trades')}  PnL {r.get('pnl_pct'):+.2f} % ({r.get('pnl_abs'):+.0f} {r.get('stake_currency', 'USDT')})  "
        f"PF {r.get('profit_factor')}  WR {r.get('winrate')} %  maxDD {r.get('max_drawdown_pct')} %  "
        f"break-even {be if be is None else f'{be:.4f} %'}"
    )


# --------------------------------------------------------------------------- #
# príkazy
# --------------------------------------------------------------------------- #


def cmd_run(args: argparse.Namespace) -> int:
    from ..core import IBSConfig
    from .runner import default_params, instrument_for_pair

    params, instrument = default_params(args.profile) if args.profile else (IBSConfig().to_dict(), None)
    for item in args.set or []:
        k, v = parse_set(item)
        if k not in params:
            raise SystemExit(f"neznámy parameter {k!r} (pozri `python -m ibs.webapp.cli params`)")
        params[k] = v

    pair = args.pair
    if pair is None:
        from ..core.types import INSTRUMENTS

        pair = INSTRUMENTS[instrument].symbol if instrument else "BTC/USDT:USDT"
    pair_instrument = instrument_for_pair(pair)
    if instrument and pair_instrument != instrument:
        print(f"POZOR: profil {args.profile} je pre {instrument}, ale pár {pair} je {pair_instrument}. "
              f"Prahy v bodoch/tickoch nesedia - použi profil pre tento nástroj (napr. {pair_instrument.split('_')[0]}_3m_binance_ny_sl_risk1).",
              file=sys.stderr)

    settings = {
        "pair": pair, "timeframe": args.timeframe, "timerange": args.timerange, "fee": args.fee,
        "wallet": args.wallet, "timeframe_detail": None if args.no_detail else "1m", "profile": args.profile,
    }
    user = args.user or os.environ.get("IBS_USER") or ""

    if server_alive(args.url):
        body = {"params": params, "note": args.note or "", "user": user or None, **settings}
        try:
            job = api(args.url, "/api/runs", body)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"webapp odmietla beh: {exc.read().decode('utf-8', 'replace')}")
        print(f"zaradené do fronty webapp: {job['id']}  ({args.url})")
        if args.no_wait:
            return 0
        while True:
            time.sleep(3)
            det = api(args.url, f"/api/runs/{job['id']}")
            rec = det["record"]
            if not det.get("live") and rec.get("status") in ("done", "failed"):
                break
            tail = (rec.get("log_tail") or [""])[-1]
            print(f"  … {rec.get('status')}  {tail[:100]}", flush=True)
        print(fmt_summary(rec))
        return 0 if rec.get("status") == "done" else 1

    # webapp nebeží → priamo, do toho istého adresára runs/
    from .runner import BacktestRunner
    from .store import RunStore

    store = RunStore()
    runner = BacktestRunner(store)
    job = runner.submit(params, settings, note=args.note or "", user=user)
    print(f"webapp nebeží, spúšťam priamo: {job.id}")
    while job.status in ("queued", "running"):
        time.sleep(2)
        if job.log_lines:
            print(f"  … {job.log_lines[-1][:100]}", flush=True)
    rec = store.get(job.id) or {"id": job.id, "status": job.status, "error": job.error, "settings": settings}
    print(fmt_summary(rec))
    return 0 if job.status == "done" else 1


def cmd_list(args: argparse.Namespace) -> int:
    from .store import RunStore

    recs = RunStore().search(" ".join(args.query)) if args.query else RunStore().all()
    for rec in recs[: args.limit]:
        note = f"  „{rec.get('note')}“" if rec.get("note") else ""
        print(fmt_summary(rec) + f"  [{rec.get('user', '')}]" + note)
    print(f"({len(recs)} behov)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from ..core import IBSConfig
    from .store import RunStore, diff_from_defaults

    rec = RunStore().get(args.run_id)
    if rec is None:
        raise SystemExit(f"beh {args.run_id} neexistuje")
    print(fmt_summary(rec))
    print("nastavenia:", json.dumps(rec.get("settings"), ensure_ascii=False))
    print("odchýlky od Pine defaultov:", json.dumps(diff_from_defaults(rec.get("params") or {}, IBSConfig().to_dict()), ensure_ascii=False))
    r = rec.get("result") or {}
    if r.get("exits"):
        print("výstupy:", json.dumps(r["exits"], ensure_ascii=False))
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2, default=str))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from . import gitsync

    alive = server_alive(args.url)
    print(f"webapp {args.url}: {'beží' if alive else 'nebeží'}")
    if alive:
        q = api(args.url, "/api/queue")
        print(f"fronta: {len(q)} " + ", ".join(f"{j['id']} {j['status']}" for j in q))
    st = gitsync.status()
    print(f"git: vetva {st['branch']}, necommitnuté behy {st['uncommitted_runs']}, "
          f"ahead {st['ahead']}, behind {st['behind']}")
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    from . import gitsync

    r = gitsync.pull()
    print(r["output"])
    return 0 if r["ok"] else 1


def cmd_push(args: argparse.Namespace) -> int:
    from . import gitsync

    r = gitsync.push(author=args.user or os.environ.get("IBS_USER") or None)
    print(r["output"] or "nič na commit, nič na push")
    return 0 if r["ok"] else 1


def cmd_params(args: argparse.Namespace) -> int:
    from .pine_meta import param_metadata

    for m in param_metadata():
        if args.filter and args.filter.lower() not in f"{m['name']} {m['title']} {m['tooltip']}".lower():
            continue
        rng = f"  [{m['min']}–{m['max']}]" if m.get("min") is not None else ""
        opts = f"  {m['options']}" if m.get("options") else ""
        unit = f"  (size, Pine {m['pine_unit']})" if m["type"] == "size" else f"  ({m['type']})"
        print(f"{m['name']:<24} {m['group']} · {m['title']}{unit}{rng}{opts}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ibs.webapp.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL, help="adresa webapp (default %(default)s, alebo IBS_WEB_URL)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="spusti backtest (cez webapp, alebo priamo) a ulož do histórie")
    p.add_argument("--profile", help="východiskový profil z ibs/configs (bez neho Pine defaulty)")
    p.add_argument("--set", action="append", metavar="KLUC=HODNOTA", help="zmena parametra, opakovateľné")
    p.add_argument("--pair", help="napr. BTC/USDT:USDT alebo ETH/USDT:USDT (default podľa profilu)")
    p.add_argument("--timerange", required=True, help="YYYYMMDD-YYYYMMDD")
    p.add_argument("--timeframe", default="3m", help="TF grafu, na ktorom stratégia počíta (default 3m; ako TF grafu v TradingView)")
    p.add_argument("--fee", type=float, default=0.0005, help="poplatok na stranu ako podiel (default 0.0005 = 0,05 %%)")
    p.add_argument("--wallet", type=float, default=10000)
    p.add_argument("--no-detail", action="store_true", help="bez 1m detailu fillov (rýchlejšie, hrubšie)")
    p.add_argument("--note", help="poznámka do histórie — napíš, čo beh testuje")
    p.add_argument("--user", help="meno testera (default IBS_USER)")
    p.add_argument("--no-wait", action="store_true", help="len zaradiť do fronty webapp, nečakať")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list", help="história behov, voliteľne s dopytom (rovnaká syntax ako vo webapp)")
    p.add_argument("query", nargs="*")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="detail behu")
    p.add_argument("run_id")
    p.add_argument("--json", action="store_true", help="vypíš celý záznam")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("status", help="beží webapp, čo je vo fronte, stav gitu")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("pull", help="stiahni históriu behov z GitHubu (git pull --rebase)")
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("push", help="commitni LEN runs/ a pushni")
    p.add_argument("--user", help="autor commitu (default IBS_USER)")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("params", help="zoznam parametrov (názov, skupina, titulok, typ, rozsah)")
    p.add_argument("filter", nargs="?")
    p.set_defaults(func=cmd_params)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
