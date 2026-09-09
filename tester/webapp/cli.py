"""Príkazový riadok nad webapp — pre Claude Code a skripty, výsledky idú do histórie.

    python -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \\
        --set rrRatio=4 --set minSlDistance=0.25@pct --timerange 20250904-20260904 \\
        --note "RR 4 namiesto 5"
    python -m tester.webapp.cli list "rrRatio>=4 pnl>0"
    python -m tester.webapp.cli show 20260905-160921-0310ba
    python -m tester.webapp.cli status          # beží webapp? čo je vo fronte? stav gitu
    python -m tester.webapp.cli pull | push     # história behov z/na GitHub

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

from tradebot.core.env import getenv
import sys
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = getenv("WEB_URL", "http://127.0.0.1:8765")


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
    engine = s.get("engine")
    tail = "\n  POZOR: " + r["warning"] if r.get("warning") else ""
    return (
        f"{rec.get('id')}  {s.get('pair')} {s.get('timerange')}"
        f"{' [' + engine + ']' if engine else ''}  "
        f"obchodov {r.get('trades')}  PnL {r.get('pnl_pct'):+.2f} % ({r.get('pnl_abs'):+.0f} {r.get('stake_currency', 'USDT')})  "
        f"PF {r.get('profit_factor')}  WR {r.get('winrate')} %  maxDD {r.get('max_drawdown_pct')} %  "
        f"break-even {be if be is None else f'{be:.4f} %'}{tail}"
    )



# --------------------------------------------------------------------------- #
# príkazy
# --------------------------------------------------------------------------- #


def _prepare(args: argparse.Namespace) -> tuple[dict, dict]:
    """(parametre, nastavenia behu) z argumentov — spoločné pre `run` aj `sweep`."""
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import STRATEGIES

    from .. import engines
    from .runner import default_params, instrument_for_pair

    if args.strategy not in STRATEGIES:
        raise SystemExit(f"neznáma stratégia {args.strategy!r}; známe: {', '.join(sorted(STRATEGIES))}")
    params, instrument = default_params(args.profile, args.strategy)
    for item in args.set or []:
        k, v = parse_set(item)
        if k not in params:
            raise SystemExit(f"neznámy parameter {k!r} (pozri `python -m tester.webapp.cli params`)")
        params[k] = v

    pair = args.pair
    if pair is None:
        pair = INSTRUMENTS[instrument].symbol if instrument else "BTC/USDT:USDT"
    pair_instrument = instrument_for_pair(pair)
    if instrument and pair_instrument != instrument:
        print(f"POZOR: profil {args.profile} je pre {instrument}, ale pár {pair} je {pair_instrument}. "
              "Prahy v bodoch/tickoch nesedia - použi profil pre tento nástroj.",
              file=sys.stderr)

    inst = INSTRUMENTS[pair_instrument]
    engine = args.engine or engines.default_engine(inst, args.timeframe)
    exchange = args.exchange or engines.DEFAULT_EXCHANGE
    possible = engines.available(inst, args.timeframe, exchange)
    if engine not in possible:
        preco = (engines.freqtrade_blocker(inst, args.timeframe, exchange)
                 if engine == engines.FREQTRADE else "chýbajú 1m sviečky")
        raise SystemExit(
            f"engine {engines.ENGINE_TITLES[engine]} sa na {pair} {args.timeframe} spustiť nedá "
            f"({preco}); dostupné: "
            f"{', '.join(engines.ENGINE_TITLES[e] for e in possible) or 'žiadne'}")

    settings = {
        "strategy": args.strategy, "pair": pair, "engine": engine, "timeframe": args.timeframe,
        "exchange": exchange if engine == engines.FREQTRADE else None,
        "timerange": args.timerange, "fee": args.fee,
        "wallet": args.wallet, "timeframe_detail": None if args.no_detail else "1m",
        "profile": args.profile,
    }
    return params, settings


def _execute(args: argparse.Namespace, params: dict, settings: dict, note: str,
             quiet: bool = False) -> dict:
    """Spustí jeden beh (cez frontu webapp, alebo priamo) a vráti jeho záznam."""
    user = args.user or getenv("USER") or ""

    if server_alive(args.url):
        body = {"params": params, "note": note, "user": user or None, **settings}
        try:
            job = api(args.url, "/api/runs", body)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"webapp odmietla beh: {exc.read().decode('utf-8', 'replace')}")
        if not quiet:
            print(f"zaradené do fronty webapp: {job['id']}  ({args.url})")
        if getattr(args, "no_wait", False):
            return {"id": job["id"], "status": "queued", "settings": settings}
        while True:
            time.sleep(3)
            det = api(args.url, f"/api/runs/{job['id']}")
            rec = det["record"]
            if not det.get("live") and rec.get("status") in ("done", "failed"):
                return rec
            if not quiet:
                tail = (rec.get("log_tail") or [""])[-1]
                print(f"  … {rec.get('status')}  {tail[:100]}", flush=True)

    # webapp nebeží → priamo, do toho istého adresára runs/
    from .runner import BacktestRunner
    from .store import RunStore

    store = RunStore()
    runner = BacktestRunner(store)
    job = runner.submit(params, settings, note=note, user=user)
    if not quiet:
        print(f"webapp nebeží, spúšťam priamo: {job.id}")
    while job.status in ("queued", "running"):
        time.sleep(2)
        if not quiet and job.log_lines:
            print(f"  … {job.log_lines[-1][:100]}", flush=True)
    return store.get(job.id) or {"id": job.id, "status": job.status, "error": job.error,
                                 "settings": settings}


def cmd_run(args: argparse.Namespace) -> int:
    params, settings = _prepare(args)
    rec = _execute(args, params, settings, args.note or "")
    if rec.get("status") == "queued":
        return 0
    print(fmt_summary(rec))
    return 0 if rec.get("status") == "done" else 1


def cmd_sweep(args: argparse.Namespace) -> int:
    """Mriežka behov cez zadané parametre a výber podľa kritéria."""
    from datetime import datetime, timezone

    from .. import sweep as sweep_mod

    params, settings = _prepare(args)
    space = {}
    for item in args.param:
        if "=" not in item:
            raise SystemExit(f"--param očakáva nazov=hodnoty, dostal {item!r}")
        name, spec = item.split("=", 1)
        name = name.strip()
        if name not in params:
            raise SystemExit(f"neznámy parameter {name!r} (pozri `python -m tester.webapp.cli params`)")
        try:
            space[name] = sweep_mod.parse_values(spec)
        except ValueError as exc:
            raise SystemExit(str(exc))

    warn_parity(space, args.strategy)
    points = sweep_mod.expand(space)
    if len(points) > args.max_runs:
        raise SystemExit(
            f"mriežka má {len(points)} behov, limit je {args.max_runs} (--max-runs). "
            "Zúž rozsah alebo krok - každý bod je celý backtest.")

    zadanie = sweep_mod.describe(args.goal, args.max_dd, args.min_trades)
    sweep_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    print(f"sweep {sweep_id}: {len(points)} behov, kriterium: {zadanie}")
    print(f"  {', '.join(f'{k} = {v}' for k, v in space.items())}\n")

    records = []
    for i, point in enumerate(points, 1):
        popis = ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in point.items())
        print(f"[{i}/{len(points)}] {popis}", flush=True)
        run_settings = {**settings, "sweep": {"id": sweep_id, "values": point, "goal": args.goal}}
        rec = _execute(args, {**params, **point}, run_settings,
                       note=f"sweep {sweep_id}: {popis}" + (f" — {args.note}" if args.note else ""),
                       quiet=True)
        rec.setdefault("settings", run_settings)
        records.append(rec)
        result = rec.get("result") or {}
        print(f"      {rec.get('status')}  obchodov {result.get('trades', '-')}  "
              f"PnL {result.get('pnl_pct', '-')} %  break-even {result.get('break_even_pct', '-')} %",
              flush=True)

    ranked = sweep_mod.rank(records, args.goal, max_dd=args.max_dd, min_trades=args.min_trades)
    print(f"\n=== sweep {sweep_id} — {zadanie} ===")
    print(sweep_mod.table(ranked, list(space), args.goal))
    best = ranked[0] if ranked and ranked[0].get("sweep_ok") else None
    if best:
        values = best["settings"]["sweep"]["values"]
        print("\nnajlepsi beh: " + best["id"])
        print("  " + ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in values.items()))
        print("  over ho na dalsich referencnych oknach, nez z neho spravis profil "
              "(jedno okno o strategii nic nepovie)")
    else:
        print("\nziadny beh nepresiel mantinelmi - uvolni --max-dd/--min-trades alebo zmen rozsah")
    return 0


def warn_parity(space: dict, strategy: str) -> None:
    """Upozorní na parametre, ktoré rozbijú paritu s Pine — ale nezakáže ich."""
    from .pine_meta import param_metadata

    risky = {m["name"]: m for m in param_metadata(strategy) if m.get("breaks_parity")}
    hit = [name for name in space if name in risky]
    if not hit:
        return
    print("POZOR: " + ", ".join(hit) + " mení sizing alebo časovanie prevzaté z TradingView.",
          file=sys.stderr)
    print("       Výsledok sa už nedá porovnať s Pine ani s golden testami - ak to je zámer, "
          "je to v poriadku.\n", file=sys.stderr)


def cmd_list(args: argparse.Namespace) -> int:
    from .store import RunStore

    recs = RunStore().search(" ".join(args.query)) if args.query else RunStore().all()
    for rec in recs[: args.limit]:
        note = f"  „{rec.get('note')}“" if rec.get("note") else ""
        print(fmt_summary(rec) + f"  [{rec.get('user', '')}]" + note)
    print(f"({len(recs)} behov)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from tradebot.strategies import get_spec
    from .store import RunStore, diff_from_defaults, strategy_of

    rec = RunStore().get(args.run_id)
    if rec is None:
        raise SystemExit(f"beh {args.run_id} neexistuje")
    print(fmt_summary(rec))
    print("nastavenia:", json.dumps(rec.get("settings"), ensure_ascii=False))
    defaults = get_spec(strategy_of(rec)).config_cls().to_dict()
    print("odchýlky od Pine defaultov:", json.dumps(diff_from_defaults(rec.get("params") or {}, defaults), ensure_ascii=False))
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
    print(f"git: vetva {st['branch']} → {st.get('target', 'main')}, "
          f"necommitnuté behy a profily {st['uncommitted']}, "
          f"ahead {st['ahead']}, behind {st['behind']}")
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    from . import gitsync

    r = gitsync.pull()
    print(r["output"])
    return 0 if r["ok"] else 1


def cmd_push(args: argparse.Namespace) -> int:
    from . import gitsync

    r = gitsync.push(author=args.user or getenv("USER") or None)
    print(r["output"] or "nič na commit, nič na push")
    return 0 if r["ok"] else 1


def cmd_params(args: argparse.Namespace) -> int:
    from .pine_meta import param_metadata

    for m in param_metadata(args.strategy):
        if args.filter and args.filter.lower() not in f"{m['name']} {m['title']} {m['tooltip']}".lower():
            continue
        rng = f"  [{m['min']}–{m['max']}]" if m.get("min") is not None else ""
        opts = f"  {m['options']}" if m.get("options") else ""
        unit = f"  (size, Pine {m['pine_unit']})" if m["type"] == "size" else f"  ({m['type']})"
        print(f"{m['name']:<24} {m['group']} · {m['title']}{unit}{rng}{opts}")
    return 0


#: kritériá výberu pre `sweep` (definícia je v `tester/sweep.py`)
_GOALS = ("break_even", "profit", "winrate", "drawdown")


def _run_args(p: argparse.ArgumentParser) -> None:
    """Argumenty spoločné pre `run` aj `sweep` — nech sa nemôžu rozísť."""
    p.add_argument("--strategy", default="ibs", help="stratégia z registry (default ibs)")
    p.add_argument("--profile", help="východiskový profil z tradebot/strategies/<stratégia>/configs/ alebo cesta k JSON (bez neho Pine defaulty)")
    p.add_argument("--set", action="append", metavar="KLUC=HODNOTA", help="zmena parametra, opakovateľné")
    p.add_argument("--pair", help="napr. BTC/USDT:USDT alebo ETH/USDT:USDT (default podľa profilu)")
    p.add_argument("--timerange", required=True, help="YYYYMMDD-YYYYMMDD")
    p.add_argument("--timeframe", default="3m", help="TF grafu, na ktorom stratégia počíta (default 3m; ako TF grafu v TradingView)")
    p.add_argument("--exchange", choices=("tester", "binance", "coinbase", "dukascopy"),
                   help="burza pre Freqtrade beh (predvolene fiktivna 'tester', ktora pozna "
                        "vsetky nase timeframy)")
    p.add_argument("--engine", choices=("freqtrade", "multicharts"),
                   help="čím beh prehrať: freqtrade alebo multicharts (emulátor); "
                        "bez neho podľa toho, aké dáta pár má")
    p.add_argument("--fee", type=float, default=0.0005, help="poplatok na stranu ako podiel (default 0.0005 = 0,05 %%)")
    p.add_argument("--wallet", type=float, default=10000)
    p.add_argument("--no-detail", action="store_true", help="bez 1m detailu fillov (rýchlejšie, hrubšie)")
    p.add_argument("--note", help="poznámka do histórie — napíš, čo beh testuje")
    p.add_argument("--user", help="meno testera (default TRADEBOT_USER)")


def main(argv: list[str] | None = None) -> int:
    # Windows konzola je cp1250 a log Freqtradu má znaky, ktoré v nej nie sú —
    # bez tohto padne celý príkaz na UnicodeEncodeError uprostred behu.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="python -m tester.webapp.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL, help="adresa webapp (default %(default)s, alebo TRADEBOT_WEB_URL)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="spusti backtest (cez webapp, alebo priamo) a ulož do histórie")
    _run_args(p)
    p.add_argument("--no-wait", action="store_true", help="len zaradiť do fronty webapp, nečakať")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("sweep", help="mriežka behov cez hodnoty parametra a výber podľa kritéria")
    p.add_argument("--param", action="append", required=True, metavar="NAZOV=HODNOTY",
                   help="rozsah `od:do:krok` alebo zoznam `a,b,c`; dá sa opakovať")
    p.add_argument("--goal", choices=tuple(_GOALS), default="break_even",
                   help="podľa čoho vybrať najlepší beh (default break-even poplatok)")
    p.add_argument("--max-dd", type=float, help="strop na max drawdown v %%")
    p.add_argument("--min-trades", type=int, help="minimálny počet obchodov, inak je bod mimo")
    p.add_argument("--max-runs", type=int, default=40, help="poistka na veľkosť mriežky (default 40)")
    _run_args(p)
    p.set_defaults(func=cmd_sweep)

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

    p = sub.add_parser("push", help="commitni LEN runs/ a profiles/ a pushni")
    p.add_argument("--user", help="autor commitu (default TRADEBOT_USER)")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("params", help="zoznam parametrov (názov, skupina, titulok, typ, rozsah)")
    p.add_argument("filter", nargs="?")
    p.add_argument("--strategy", default="ibs", help="stratégia z registry (default ibs)")
    p.set_defaults(func=cmd_params)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
