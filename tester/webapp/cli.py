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
from tradebot.core.paths import REPO
from pathlib import Path
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


def cmd_sweeps(args: argparse.Namespace) -> int:
    """Zoznam mriežok z histórie, alebo tabuľka jednej z nich.

    Mriežky sa nikde neukladajú zvlášť — značka je v každom behu, takže zoznam je len
    preskupená história. Aj mriežka spustená vo webapp sa dá otvoriť tu a naopak.
    """
    from .. import sweep as sweep_mod
    from .store import RunStore

    zaznamy = RunStore().all()
    skupiny: dict[str, list[dict]] = {}
    for rec in zaznamy:
        tag = (rec.get("settings") or {}).get("sweep") or {}
        # Parametre su v kazdej strategii ine, takze mriezka cez rrRatio nema pri
        # Donchian breakoute co robit - zoznam patri strategii.
        if args.strategy and (rec.get("settings") or {}).get("strategy", "ibs") != args.strategy:
            continue
        if tag.get("id"):
            skupiny.setdefault(tag["id"], []).append(rec)
    if not skupiny:
        kde = f" pre strategiu {args.strategy}" if args.strategy else ""
        print(f"v historii nie je ziadna mriezka (sweep){kde}")
        return 0

    if args.sweep_id:
        rows = skupiny.get(args.sweep_id)
        if rows is None:
            raise SystemExit(f"mriezka {args.sweep_id} v historii nie je; "
                             "zoznam vypise `cli sweeps` bez argumentu")
        tag = rows[0]["settings"]["sweep"]
        zadanie = sweep_mod.describe(tag.get("goal") or "break_even",
                                     tag.get("max_dd"), tag.get("min_trades"))
        ranked = sweep_mod.rank(rows, tag.get("goal") or "break_even",
                                max_dd=tag.get("max_dd"), min_trades=tag.get("min_trades"))
        nastavenia = rows[0]["settings"]
        print(f"=== sweep {args.sweep_id} - {zadanie} ===")
        print(f"{nastavenia.get('pair')} {nastavenia.get('timeframe')} "
              f"{nastavenia.get('timerange')}, behov {len(rows)}\n")
        print(sweep_mod.table(ranked, list(tag.get("values") or {}), tag.get("goal")))
        return 0

    print(f"{'mriezka':<24} {'behov':>6}  parametre / par / obdobie")
    for sweep_id in sorted(skupiny, reverse=True)[:args.limit]:
        rows = skupiny[sweep_id]
        tag = rows[0]["settings"]["sweep"]
        nastavenia = rows[0]["settings"]
        popis = " x ".join(tag.get("values") or {})
        print(f"{sweep_id:<24} {len(rows):>6}  {popis} | {nastavenia.get('pair')} "
              f"{nastavenia.get('timeframe')} {nastavenia.get('timerange')}")
    print("\ndetail: python -m tester.webapp.cli sweeps <mriezka>")
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """Mriežka behov cez zadané parametre a výber podľa kritéria."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from tradebot.core.config import ConfigError
    from tradebot.strategies import STRATEGIES

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
    if args.max_runs and len(points) > args.max_runs:
        raise SystemExit(
            f"mriežka má {len(points)} behov, strop je {args.max_runs} (--max-runs). "
            "Zúž rozsah alebo krok - každý bod je celý backtest.")

    # Celá mriežka sa overí naraz: keby hodnota mimo Pine rozsahu vypadla až v piatom
    # bode, tester by mal za sebou štyri hotové backtesty a sweep by skončil na výnimke.
    config_cls = STRATEGIES[args.strategy].config_cls
    for point in points:
        merged = {**params, **point}
        try:
            config_cls.from_dict({k: v for k, v in merged.items() if not k.startswith("_")})
        except ConfigError as exc:
            popis = ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in point.items())
            raise SystemExit(f"bod {popis}: {exc}")

    zadanie = sweep_mod.describe(args.goal, args.max_dd, args.min_trades)
    # Sekunda nestačí: dva sweepy rýchlo za sebou by mali tú istú značku a v tabuľke
    # by sa zliali do jednej mriežky.
    sweep_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
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


def cmd_portfolio(args: argparse.Namespace) -> int:
    """Vybrané behy ako jedno portfólio: cena rizika, rok po roku, korelácie."""
    from .. import analytics as an, portfolio as pf
    from .store import RunStore

    store = RunStore()
    if args.runs:
        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (store.get(i) for i in chcene) if r]
    else:
        vsetky = store.search(" ".join(args.query)) if args.query else store.all()
        zaznamy = [r for r in vsetky if r.get("status") == "done"
                   and ((r.get("result") or {}).get("trades") or 0) >= args.min_trades]
    zaznamy = zaznamy[:args.limit]
    if not zaznamy:
        raise SystemExit("ziadne dobehnute behy s obchodmi (skus iny dopyt)")

    per: dict[str, list] = {}
    for rec in zaznamy:
        t = store.trades(rec["id"])
        if not t:
            continue
        # Clen je JEDEN beh. Zlucovat behy podla paru by znamenalo scitat obchody
        # z prekryvajucich sa okien, teda zapocitat to iste obdobie viackrat.
        meno = (f"{rec['settings'].get('pair')} {rec['settings'].get('timeframe')} "
                f"{rec['settings'].get('timerange')}")
        per[meno] = an.enrich([dict(x) for x in t], store.chart(rec["id"]),
                              rec["settings"].get("strategy") or "ibs")

    risks = [float(x) for x in args.risks.split(",") if x.strip()] if args.risks else pf.RISKS
    vysledok = pf.analyze(per, records=zaznamy, account=args.account, risks=risks,
                          risk_pct=args.risk)
    print(f"behov {len(zaznamy)}, clenov {len(per)}\n")
    print(pf.report(vysledok))
    return 0


def cmd_plateau(args: argparse.Namespace) -> int:
    """Okolie víťaza hyperoptu: susedné hodnoty ako test robustnosti."""
    from .. import montecarlo as mc, plateau as pl
    from .store import RunStore

    store = RunStore()
    hyper = store.get(args.hyperopt_id)
    if hyper is None:
        raise SystemExit(f"beh {args.hyperopt_id} v historii nie je")
    zadanie = (hyper.get("settings") or {}).get("hyperopt") or {}
    if not zadanie.get("knobs"):
        raise SystemExit(f"beh {args.hyperopt_id} nie je hyperopt")
    vitaz_params = zadanie.get("overrides")
    if not vitaz_params:
        raise SystemExit("hyperopt nema vitaza (ziadna epocha nesplnila mantinely)")

    # Vitaz uz raz bezal ako obycajny beh na ladenom okne - z neho su obchody aj interval.
    overenia = [r for r in store.all()
                if ((r.get("settings", {}).get("hyperopt_run") or {}).get("id")) == args.hyperopt_id]
    ladene = [r for r in overenia if (r["settings"].get("hyperopt_run") or {}).get("tuned")]
    if not ladene:
        raise SystemExit("beh vitaza na ladenom okne v historii nie je (spustil sa hyperopt "
                         "s --no-verify?)")
    vitaz = ladene[0]

    interval = (None, None)
    obchody = store.trades(vitaz["id"])
    if len(obchody) >= mc.MIN_TRADES:
        vysledok = mc.analyze(obchody, fee_pct=(vitaz["settings"].get("fee") or 0) * 100,
                              iterations=args.iterations, seed=args.seed)
        be = vysledok["break_even"]
        interval = (be["lo"], be["hi"])
    else:
        print(f"POZOR: vitaz ma len {len(obchody)} obchodov, interval spolahlivosti sa "
              f"nepocita (treba aspon {mc.MIN_TRADES}).", file=sys.stderr)

    susedia = pl.neighbours(zadanie["knobs"], vitaz_params)
    if not susedia:
        raise SystemExit("vitaz nema ziadnych susedov v rozsahu planu")

    zaklad = {k: v for k, v in (vitaz.get("params") or {}).items()}
    settings_zaklad = {k: v for k, v in vitaz["settings"].items() if k != "hyperopt_run"}
    print(f"okolie vitaza {args.hyperopt_id}: {len(susedia)} susedov, okno "
          f"{settings_zaklad.get('timerange')}")
    print(f"  vitaz: {', '.join(f'{k}={v}' for k, v in vitaz_params.items())}\n", flush=True)

    zaznamy = []
    for i, sused in enumerate(susedia, 1):
        params = {**zaklad, sused.param: sused.value}
        settings = {**settings_zaklad,
                    "plateau": {"id": args.hyperopt_id, "param": sused.param,
                                "value": sused.value, "step": sused.step}}
        print(f"[{i}/{len(susedia)}] {sused.label} = {sused.value}", flush=True)
        try:
            rec = _execute(args, params, settings,
                           note=f"okolie {args.hyperopt_id}: {sused.param}={sused.value}",
                           quiet=True)
        except SystemExit as exc:
            print(f"      neslo spustit: {exc}", flush=True)
            continue
        rec.setdefault("settings", settings)
        zaznamy.append(rec)
        r = rec.get("result") or {}
        print(f"      {rec.get('status')}  obchodov {r.get('trades', '-')}  "
              f"break-even {r.get('break_even_pct', '-')} %", flush=True)

    hodnotenie = pl.assess(vitaz, zaznamy, interval)
    print(f"\n=== okolie vitaza {args.hyperopt_id} ===")
    print(pl.table(hodnotenie))
    return 0


def cmd_nulltest(args: argparse.Namespace) -> int:
    """Porovná break-even stratégie s náhodným vstupom za tých istých pravidiel."""
    from .. import analytics as an, nulltest as nt
    from .store import RunStore

    store = RunStore()
    if args.runs:
        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (store.get(i) for i in chcene) if r]
    else:
        vsetky = store.search(" ".join(args.query)) if args.query else store.all()
        zaznamy = [r for r in vsetky if r.get("status") == "done"
                   and ((r.get("result") or {}).get("trades") or 0) > 0]
    zaznamy = zaznamy[:args.limit]
    if not zaznamy:
        raise SystemExit("ziadne dobehnute behy s obchodmi (skus iny dopyt)")

    pary = {r["settings"].get("pair") for r in zaznamy}
    if len(pary) > 1:
        raise SystemExit("nahodne vstupy sa losuju zo sviecok jedneho paru, takze behy "
                         f"musia byt z jedneho trhu; vybrane su: {', '.join(sorted(pary))}")
    pair = zaznamy[0]["settings"]["pair"]
    timeframe = zaznamy[0]["settings"].get("timeframe") or "3m"

    obchody = []
    for rec in zaznamy:
        t = store.trades(rec["id"])
        if t:
            obchody += an.enrich([dict(x) for x in t], store.chart(rec["id"]),
                                 rec["settings"].get("strategy") or "ibs")
    if not obchody:
        raise SystemExit("vybrane behy nemaju ulozene obchody")

    print(f"{len(zaznamy)} behov, {len(obchody)} obchodov, {pair} {timeframe}")
    okna = sorted({r["settings"].get("timerange") for r in zaznamy if r["settings"].get("timerange")})
    print(f"okna: {', '.join(okna)}\n")

    najprv = None
    for null in ([args.null] if args.null else list(nt.NULLS)):
        vysledok = nt.compare(obchody, pair=pair, timeframe=timeframe,
                              iterations=args.iterations, null=null, seed=args.seed)
        print(nt.report(vysledok, label=null))
        print()
        if najprv is None:
            najprv = vysledok
        elif (najprv.sigma is not None and vysledok.sigma is not None
              and najprv.sigma - vysledok.sigma > 1.0):
            print("Rozdiel medzi tymi dvoma je hodnota samotneho vyberu casu: proti nahode "
                  "kedykolvek je strategia vyrazne lepsia, proti nahode v tych istych "
                  "hodinach uz nie. Cely jej edge je v tom, KEDY obchoduje.\n")
    return 0 if (najprv and najprv.sigma is not None) else 1


def cmd_paper(args: argparse.Namespace) -> int:
    """Meranie, ktore sa napise samo — z behov v historii do docs/merania/."""
    import shlex

    from .. import paper as pp
    from .store import RunStore, strategy_of

    store = RunStore()
    if args.runs:
        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (store.get(i) for i in chcene) if r]
    else:
        vsetky = store.search(" ".join(args.query)) if args.query else store.all()
        zaznamy = [r for r in vsetky if strategy_of(r) == args.strategy
                   and r.get("status") == "done"
                   and ((r.get("result") or {}).get("trades") or 0) > 0]
    zaznamy = zaznamy[:args.limit]
    if not zaznamy:
        raise SystemExit("ziadne dobehnute behy s obchodmi (skus iny dopyt)")

    # Prikaz ide do dokumentu, aby sa dal zopakovat - bez neho je meranie neoveritelne.
    prikaz = "python -m tester.webapp.cli " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    print(f"{len(zaznamy)} behov, pocitam...", flush=True)
    try:
        doc = pp.build(zaznamy, store, strategy=args.strategy, title=args.title,
                       risk_pct=args.risk_pct, null_iterations=args.iterations,
                       command=prikaz)
    except ValueError as exc:
        raise SystemExit(str(exc))

    if args.stdout:
        print(pp.render(doc))
        return 0
    cesta = pp.write(doc, args.name)
    print(f"zapisane: {cesta.relative_to(REPO) if cesta.is_relative_to(REPO) else cesta}")
    for sek in doc.sections:
        stav = f"CHYBA: {sek.gap}" if sek.gap else (sek.verdict or "ok")
        print(f"  {sek.title:<36} {stav}")
    return 0


def cmd_decay(args: argparse.Namespace) -> int:
    """Slabne edge? Posledné obdobie proti tomu, čo stratégia robievala."""
    from .. import analytics as an, decay as dc
    from .store import RunStore

    store = RunStore()
    if args.runs:
        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (store.get(i) for i in chcene) if r]
    else:
        vsetky = store.search(" ".join(args.query)) if args.query else store.all()
        zaznamy = [r for r in vsetky if r.get("status") == "done"
                   and ((r.get("result") or {}).get("trades") or 0) > 0]
    zaznamy = zaznamy[:args.limit]
    if not zaznamy:
        raise SystemExit("ziadne dobehnute behy s obchodmi (skus iny dopyt)")

    obchody = []
    for rec in zaznamy:
        t = store.trades(rec["id"])
        if t:
            obchody += an.enrich([dict(x) for x in t], store.chart(rec["id"]),
                                 rec["settings"].get("strategy") or "ibs")
    if not obchody:
        raise SystemExit("vybrane behy nemaju ulozene obchody")

    # Zliate behy z prekryvajucich sa okien by tie iste obchody zapocitali viackrat a
    # obdobie by vyzeralo hustejsie, nez bolo. Nech je to aspon vidiet.
    okna = sorted({r["settings"].get("timerange") for r in zaznamy if r["settings"].get("timerange")})
    pary = sorted({r["settings"].get("pair") for r in zaznamy if r["settings"].get("pair")})
    print(f"{len(zaznamy)} behov, {len(obchody)} obchodov, {', '.join(pary)}")
    print(f"okna: {', '.join(okna)}\n")

    vysledok = dc.analyze(obchody, parts=args.parts, by=args.by,
                          iterations=args.iterations, block=args.block, seed=args.seed)
    print(dc.report(vysledok, label=", ".join(pary)))
    return 0 if vysledok.verdict != "MALO DAT" else 1


def cmd_matrix(args: argparse.Namespace) -> int:
    """Matica trhov a timeframov: drží myšlienka aj mimo trhu, na ktorom sa ladila?"""
    from datetime import datetime, timezone
    from uuid import uuid4

    from .. import matrix as mx, sweep as sweep_mod
    from .runner import available_pairs

    params, settings = _prepare(args)

    vsetky = [p["pair"] for p in available_pairs()]
    if args.pairs.strip().lower() in ("all", "vsetky", "*"):
        pary = vsetky
    else:
        pary = [x.strip() for x in args.pairs.split(",") if x.strip()]
        nezname = [x for x in pary if x not in vsetky]
        if nezname:
            raise SystemExit(f"neznáme páry: {', '.join(nezname)}\nznáme: {', '.join(vsetky)}")
    tfs = [x.strip() for x in args.timeframes.split(",") if x.strip()]

    try:
        bunky = mx.expand(pary, tfs)
    except ValueError as exc:
        raise SystemExit(str(exc))
    bunky, preskocene = mx.playable(bunky, exchange=settings.get("exchange") or "tester",
                                    engine=args.engine, params=params)
    if not bunky:
        raise SystemExit("žiadna bunka matice sa spustiť nedá:\n  "
                         + "\n  ".join(f"{k}: {v}" for k, v in preskocene.items()))

    # Prahy v absolútnych cenových bodoch sa medzi trhmi preniesť nedajú. Bez prepočtu by
    # tabuľka nehovorila „na forexe to nefunguje", ale „profil je tam nezmysel".
    if args.relative:
        params, zmeny = mx.to_relative(params, strategy=args.strategy,
                                       ref_pair=settings["pair"],
                                       ref_timeframe=settings.get("timeframe") or "3m",
                                       timerange=settings["timerange"])
        for riadok in zmeny:
            print(f"  {riadok}")
        if zmeny:
            print()
    else:
        for pair, problemy in mx.warnings_for(params, pary, strategy=args.strategy).items():
            print(f"POZOR {pair}: {problemy[0]}", file=sys.stderr)

    # Jeden lot EURUSD je 100 000 jednotiek bazy, teda ~108 000 USD. S penazenkou 10 000
    # sa nezmesti, velkost sa oreze na nulu a bunka skonci s nula obchodmi - co vyzera
    # ako "tu to nefunguje". Break-even od penazenky nezavisi, takze ju zvysit sa smie.
    male = mx.wallet_check([c.pair for c in bunky], float(settings.get("wallet") or 10000),
                           timeframe=tfs[0], timerange=settings["timerange"])
    if male:
        print(f"POZOR: penazenka {settings.get('wallet')} je mala na jeden kontrakt na "
              f"{len(male)} trhoch:", file=sys.stderr)
        for pair, nominal in sorted(male.items(), key=lambda kv: -kv[1])[:8]:
            print(f"  {pair}: 1 kontrakt = {nominal:,.0f}".replace(",", " "), file=sys.stderr)
        print(f"  Tie bunky skoncia s nula obchodmi. Break-even od penazenky nezavisi, "
              f"tak ju zvys: --wallet {max(male.values()) * 2:,.0f}".replace(",", " "),
              file=sys.stderr)
        print(file=sys.stderr)

    matrix_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
    print(f"matica {matrix_id}: {len(bunky)} behov "
          f"({len(pary)} trhov x {len(tfs)} TF), okno {settings['timerange']}")
    if preskocene:
        print(f"  preskocene: {len(preskocene)} buniek "
              f"({', '.join(sorted(preskocene)[:3])}{'...' if len(preskocene) > 3 else ''})")
    print(f"  kriterium: {sweep_mod.describe(args.goal, args.max_dd, args.min_trades)}\n",
          flush=True)

    zaznamy = []
    for i, cell in enumerate(bunky, 1):
        beh = {**settings, "pair": cell.pair, "timeframe": cell.timeframe,
               "matrix": {"id": matrix_id, "pair": cell.pair, "timeframe": cell.timeframe,
                          "goal": args.goal, "relative": bool(args.relative)}}
        print(f"[{i}/{len(bunky)}] {cell.pair} {cell.timeframe}", flush=True)
        try:
            rec = _execute(args, params, beh,
                           note=f"matica {matrix_id}: {cell.pair} {cell.timeframe}"
                                + (f" — {args.note}" if args.note else ""),
                           quiet=True)
        except SystemExit as exc:
            print(f"      neslo spustit: {exc}", flush=True)
            continue
        rec.setdefault("settings", beh)
        zaznamy.append(rec)
        r = rec.get("result") or {}
        print(f"      {rec.get('status')}  obchodov {r.get('trades', '-')}  "
              f"PnL {r.get('pnl_pct', '-')} %  break-even {r.get('break_even_pct', '-')} %",
              flush=True)

    poradie = mx.rank(zaznamy, args.goal, max_dd=args.max_dd, min_trades=args.min_trades)
    print(f"\n=== matica {matrix_id} — break-even poplatok (% na stranu) ===")
    print(mx.table(mx.matrix(poradie)))
    print(f"\n{mx.verdict(zaznamy)}")
    print(f"cele porovnanie: python -m tester.webapp.cli matrices {matrix_id}")
    return 0


def cmd_checkup(args: argparse.Namespace) -> int:
    """Základná analytika stratégie: päť okien a nad nimi celá batéria meraní."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from .. import analytics as an, checkup as ck, hyperopt as ho, montecarlo as mc
    from .store import RunStore

    okna = ([x.strip() for x in args.windows.split(",") if x.strip()]
            if args.windows else list(ho.REFERENCE_WINDOWS))
    if not okna:
        raise SystemExit("--windows nesmie byt prazdne")
    # `_prepare` chce jedno okno; ostatné sa dosadia pri behu. Musí to byť okno zo
    # zoznamu, nech kontrola dát (páry, engine) platí o tom, čo sa naozaj spustí.
    args.timerange = okna[0]
    params, settings = _prepare(args)
    store = RunStore()

    if args.runs:
        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (_run_record(store, args.url, i) for i in chcene) if r]
        if not zaznamy:
            raise SystemExit("ziadny z behov v --runs v historii nie je")
        okna = [(r.get("settings") or {}).get("timerange") or "?" for r in zaznamy]
        settings = {**settings, **{k: (zaznamy[0].get("settings") or {}).get(k, settings.get(k))
                                   for k in ("pair", "timeframe", "engine", "fee", "wallet")}}
        print(f"analytika z {len(zaznamy)} hotovych behov (nic sa nespusta)")
    else:
        checkup_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        print(f"checkup {checkup_id}: {len(okna)} behov, {settings['pair']} "
              f"{settings['timeframe']}, engine {settings['engine']}"
              + (f", profil {args.profile}" if args.profile else " (Pine defaulty)"))
        print(f"  okna: {', '.join(okna)}\n", flush=True)
        zaznamy = []
        for i, okno in enumerate(okna, 1):
            beh = {**settings, "timerange": okno,
                   "checkup": {"id": checkup_id, "strategy": args.strategy}}
            print(f"[{i}/{len(okna)}] {okno}", flush=True)
            rec = _execute(args, params, beh,
                           note=f"checkup {checkup_id}: {okno}"
                                + (f" — {args.note}" if args.note else ""),
                           quiet=True)
            rec.setdefault("settings", beh)
            zaznamy.append(rec)
            r = rec.get("result") or {}
            print(f"      {rec.get('status')}  obchodov {r.get('trades', '-')}  "
                  f"PnL {r.get('pnl_pct', '-')} %  break-even {r.get('break_even_pct', '-')} %",
                  flush=True)

    # Obchody zo všetkých okien spolu: jedno okno má na delenie na skupiny málo obchodov.
    # Obohatia sa kresbami toho behu, z ktorého sú — v nich je plán obchodu (SL, TP).
    obchody: list[dict] = []
    for rec in zaznamy:
        if rec.get("status") != "done":
            continue
        t, kresby = _run_data(store, args.url, rec["id"])
        if t:
            obchody += an.enrich([dict(x) for x in t], kresby, args.strategy)

    hotove = [r for r in zaznamy if r.get("status") == "done"]
    if not obchody and any((r.get("result") or {}).get("trades") for r in hotove):
        raise SystemExit("\n".join([
            "behy dobehli a obchody majú, ale nedajú sa načítať: sklad `tester/runs/` ich nemá.",
            "Typicky beží webapp nad INÝM klonom repozitára a beh sa uložil do jeho histórie.",
            "Spusti ju odtiaľto, alebo zadaj `--url` na tú správnu (prípadne adresu, na ktorej",
            "nič nepočúva, nech beh ide priamo).",
        ]))
    risk_ref = mc.sizing_of(hotove[-1]) if hotove else None
    report = ck.measure(zaznamy, obchody, strategy=args.strategy, pair=settings["pair"],
                        timeframe=settings["timeframe"], fee_pct=float(settings.get("fee") or 0) * 100,
                        profile=args.profile or "", engine=settings.get("engine") or "freqtrade",
                        account=float(settings.get("wallet") or 10000), risk_ref=risk_ref,
                        iterations=args.iterations, seed=args.seed)
    print()
    print(ck.table(report))

    if args.no_write:
        print("\ndokument sa nezapisal (--no-write)")
        return 0
    cesta = Path(args.out) if args.out else ck.doc_path(args.strategy)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    # Posudok je jediná časť dokumentu, ktorú generátor nevyrobí — prenesie sa z predošlej
    # verzie a označí sa, keď sa čísla medzitým zmenili.
    stary, odtlacok = (ck.extract_posudok(cesta.read_text(encoding="utf-8"))
                       if cesta.exists() else ("", ""))
    cesta.write_text(ck.markdown(report, command=_checkup_command(args, okna),
                                 posudok=stary, posudok_stamp=odtlacok),
                     encoding="utf-8", newline="\n")
    try:
        kde = cesta.relative_to(REPO)
    except ValueError:
        kde = cesta
    print(f"\nzapisane: {kde}")
    print(_posudok_status(stary, odtlacok, ck.fingerprint(report), kde))
    return 0


def _posudok_status(stary: str, odtlacok: str, teraz: str, kde: Any) -> str:
    """Čo na dokumente ešte chýba: posudok od AI. Bez neho je to len tabuľka čísel."""
    if stary.strip() and odtlacok == teraz:
        return "posudok od AI: aktualny"
    stav = ("chyba" if not stary.strip()
            else f"je k inej vzorke ({odtlacok or '?'} vs {teraz}), treba prepisat")
    return "\n".join([
        f"posudok od AI: {stav}",
        f"  Precitaj {kde}, odpovedz na sest otazok v sekcii `Posudok (AI)`",
        "  a zapis odpoved medzi znacky POSUDOK (docs/ANALYTIKA.md).",
    ])


def _run_record(store: Any, url: str, run_id: str) -> dict | None:
    """Záznam behu zo skladu, a keď tam nie je, z bežiacej webapp (iný klon, iný `runs/`)."""
    rec = store.get(run_id)
    if rec is not None or not server_alive(url):
        return rec
    try:
        return (api(url, f"/api/runs/{run_id}") or {}).get("record")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _run_data(store: Any, url: str, run_id: str) -> tuple[list[dict], dict | None]:
    """Obchody a kresby behu — zo skladu, a keď tam nie sú, z bežiacej webapp.

    Beh mohol vzniknúť vo webapp, ktorá stojí nad iným klonom repozitára a má vlastný
    `runs/`. Vtedy ho lokálny sklad nevidí a jediný, kto ho má, je práve tá webapp.
    """
    trades = store.trades(run_id)
    if trades:
        return trades, store.chart(run_id)
    if not server_alive(url):
        return [], None
    try:
        det = api(url, f"/api/runs/{run_id}")
        chart = api(url, f"/api/runs/{run_id}/chart")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return [], None
    return det.get("trades") or [], {"objects": chart.get("objects") or []}


def _checkup_command(args: argparse.Namespace, okna: list[str]) -> str:
    """Príkaz, ktorým sa tá istá analytika zopakuje — patrí do dokumentu, nie do hlavy."""
    from .. import hyperopt as ho

    cmd = ["python -m tester.webapp.cli checkup", f"--strategy {args.strategy}"]
    if args.profile:
        cmd.append(f"--profile {args.profile}")
    if args.pair:
        cmd.append(f"--pair {args.pair}")
    cmd.append(f"--timeframe {args.timeframe}")
    if args.fee != 0.0005:
        cmd.append(f"--fee {args.fee}")
    if float(args.wallet) != 10000.0:
        cmd.append(f"--wallet {args.wallet:g}")
    if list(okna) != list(ho.REFERENCE_WINDOWS):
        cmd.append("--windows " + ",".join(okna))
    return (" \\" + "\n   ").join(cmd)


def cmd_matrices(args: argparse.Namespace) -> int:
    """Matice z histórie; s argumentom vypíše tabuľku jednej."""
    from .. import matrix as mx
    from .store import RunStore

    skupiny: dict[str, list[dict]] = {}
    for rec in RunStore().all():
        tag = (rec.get("settings") or {}).get("matrix") or {}
        if not tag.get("id"):
            continue
        if args.strategy and (rec.get("settings") or {}).get("strategy", "ibs") != args.strategy:
            continue
        skupiny.setdefault(tag["id"], []).append(rec)
    if not skupiny:
        print("v historii nie je ziadna matica")
        return 0

    if args.matrix_id:
        rows = skupiny.get(args.matrix_id)
        if rows is None:
            raise SystemExit(f"matica {args.matrix_id} v historii nie je")
        poradie = mx.rank(rows, (rows[0]["settings"]["matrix"].get("goal") or "break_even"))
        print(f"=== matica {args.matrix_id} — break-even poplatok (% na stranu) ===")
        print(f"okno {rows[0]['settings'].get('timerange')}, behov {len(rows)}\n")
        print(mx.table(mx.matrix(poradie)))
        print(f"\n{mx.verdict(rows)}")
        return 0

    print(f"{'matica':<24} {'behov':>6}  okno / trhy")
    for matrix_id in sorted(skupiny, reverse=True)[:args.limit]:
        rows = skupiny[matrix_id]
        pary = sorted({r["settings"]["pair"] for r in rows})
        print(f"{matrix_id:<24} {len(rows):>6}  {rows[0]['settings'].get('timerange')} | "
              f"{len(pary)} trhov")
    print("\ndetail: python -m tester.webapp.cli matrices <matica>")
    return 0


def cmd_hyperopt(args: argparse.Namespace) -> int:
    """Hyperopt na tom istom zadaní ako sweep, plus overenie na ďalších oknách."""
    import subprocess
    from datetime import datetime, timezone
    from uuid import uuid4

    from tradebot.core.types import INSTRUMENTS

    from .. import engines, hyperopt as ho, sweep as sweep_mod
    from .runner import USER_DIR, instrument_for_pair

    params, settings = _prepare(args)

    space = ho.suggested(args.strategy) if args.suggested else {}
    for item in args.param or []:
        if "=" not in item:
            raise SystemExit(f"--param chce NAZOV=HODNOTY, dostal {item!r}")
        name, spec = item.split("=", 1)
        name = name.strip()
        if name not in params:
            raise SystemExit(f"neznámy parameter {name!r} (pozri `python -m tester.webapp.cli params`)")
        space[name] = spec.strip()
    if not space:
        raise SystemExit("hyperopt potrebuje aspoň jeden --param (alebo --suggested pre "
                         "priestor, ktorý stratégia odporúča)")
    warn_parity(space, args.strategy)

    try:
        plan = ho.build_plan(space, strategy=args.strategy, goal=args.goal, max_dd=args.max_dd,
                             min_trades=args.min_trades, note=args.note or "")
    except ValueError as exc:
        raise SystemExit(str(exc))

    znalosti = ho.knowledge_note(args.strategy)
    if znalosti:
        print(f"POZNAMKA k {args.strategy}: {znalosti}\n", file=sys.stderr)
    for varovanie in ho.warnings_for(space, args.strategy):
        print(f"POZOR: {varovanie}", file=sys.stderr)

    hyper_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
    zadanie = sweep_mod.describe(args.goal, args.max_dd, args.min_trades)
    plan_file = ho.plan_path(hyper_id, plan)

    inst = INSTRUMENTS[instrument_for_pair(settings["pair"])]
    cmd = ho.command(
        sys.executable, plan=plan_file,
        config=engines.stake_config(inst, settings.get("exchange")),
        userdir=USER_DIR, datadir=engines.data_dir(inst),
        strategy_class=get_spec_class(args.strategy), pair=settings["pair"],
        timerange=settings["timerange"], timeframe=settings["timeframe"],
        epochs=args.epochs, detail=settings.get("timeframe_detail"),
        wallet=settings.get("wallet", 10000), fee=settings.get("fee"),
        seed=args.seed, jobs=args.jobs,
    )

    print(f"hyperopt {hyper_id}: {args.epochs} epoch, kriterium: {zadanie}")
    print(f"  ladi sa: {', '.join(f'{k} = {v}' for k, v in space.items())}")
    print(f"  okno:    {settings['timerange']}  ({settings['pair']} {settings['timeframe']})")
    print(f"  plan:    {plan_file.relative_to(REPO)}\n", flush=True)

    from .runner import write_profile
    # Východiskový profil: hodnoty, na ktorých optimalizátor stojí. Ladené polia z neho
    # prepíše plán, ostatné (sizing, seansy, entry modely) ostávajú z profilu testera.
    zaklad = write_profile(f"hyperopt-{hyper_id}", params, instrument_for_pair(settings["pair"]),
                           args.strategy)
    prostredie = {**os.environ, "TRADEBOT_HYPEROPT_PLAN": str(plan_file),
                  "TRADEBOT_PROFILE": str(zaklad)}
    start = time.time()
    code = subprocess.call(cmd, env=prostredie)
    if code != 0:
        raise SystemExit(f"freqtrade hyperopt skoncil s kodom {code}")

    results = ho.latest_results(start)
    if results is None:
        raise SystemExit(f"hyperopt nezapisal ziadne epochy do {ho.RESULTS_DIR}")
    epochs = ho.read_results(results)
    print(f"\n=== hyperopt {hyper_id} — {zadanie} ===")
    print(ho.table(epochs, plan))

    vitaz = ho.best(epochs)
    if vitaz is None:
        print("\nZIADNA epocha nesplnila mantinely (min. obchodov, strop na drawdown).")
        print("Zniz --min-trades, uvolni --max-dd, alebo daj sirsi rozsah.")
        return 1

    najdene = ho.overrides(plan, vitaz.params)
    print("\nnajlepsia epocha: " + str(vitaz.number))
    for k, v in najdene.items():
        print(f"  {k} = {sweep_mod._fmt(v)}")

    if args.no_verify:
        print("\nOverenie na dalsich oknach preskocene (--no-verify). Vysledok jedneho okna "
              "o strategii nepovie nic - hyperopt nasiel optimum PRAVE toho okna.")
        return 0

    okna = [settings["timerange"]] + [w for w in ho.REFERENCE_WINDOWS if w != settings["timerange"]]
    print(f"\nOverujem vitaza na {len(okna)} oknach (ladene okno je prve)...", flush=True)
    zaznamy = []
    for i, okno in enumerate(okna, 1):
        beh = {**settings, "timerange": okno,
               "hyperopt": {"id": hyper_id, "values": najdene, "goal": args.goal,
                            "max_dd": args.max_dd, "min_trades": args.min_trades,
                            "tuned": okno == settings["timerange"]}}
        popis = ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in najdene.items())
        print(f"[{i}/{len(okna)}] {okno}", flush=True)
        rec = _execute(args, {**params, **najdene}, beh,
                       note=f"hyperopt {hyper_id}: {popis}" + (f" — {args.note}" if args.note else ""),
                       quiet=True)
        rec.setdefault("settings", beh)
        zaznamy.append(rec)
        r = rec.get("result") or {}
        znacka = " (ladene)" if okno == settings["timerange"] else ""
        print(f"      {rec.get('status')}  obchodov {r.get('trades', '-')}  "
              f"PnL {r.get('pnl_pct', '-')} %  break-even {r.get('break_even_pct', '-')} %{znacka}",
              flush=True)

    print(f"\n{ho.verdict(zaznamy, settings['timerange'])}")
    print(f"cele porovnanie: python -m tester.webapp.cli hyperopts {hyper_id}")
    return 0


def get_spec_class(strategy: str) -> str:
    from tradebot.strategies import get_spec

    return get_spec(strategy).freqtrade_class


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


def _run_args(p: argparse.ArgumentParser, *, timerange: bool = True) -> None:
    """Argumenty spoločné pre `run` aj `sweep` — nech sa nemôžu rozísť.

    `checkup` beží na piatich oknách naraz, takže jediné `--timerange` nemá; všetko
    ostatné (profil, pár, poplatok, peňaženka) má rovnaké, a preto to je tu.
    """
    p.add_argument("--strategy", default="ibs", help="stratégia z registry (default ibs)")
    p.add_argument("--profile", help="východiskový profil z tradebot/strategies/<stratégia>/configs/ alebo cesta k JSON (bez neho Pine defaulty)")
    p.add_argument("--set", action="append", metavar="KLUC=HODNOTA", help="zmena parametra, opakovateľné")
    p.add_argument("--pair", help="napr. BTC/USDT:USDT alebo ETH/USDT:USDT (default podľa profilu)")
    if timerange:
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
    p.add_argument("--max-runs", type=int, default=0,
                   help="strop na veľkosť mriežky; 0 (default) = bez stropu, sweep smie bežať "
                        "cez noc. Cena je čas: rok backtestu je asi 30 s na bod")
    _run_args(p)
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("portfolio", help="vybrané behy ako portfólio: koľko a za aký drawdown")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--account", type=float, default=10000.0, help="účet (default 10000)")
    p.add_argument("--risk", type=float, default=1.0,
                   help="riziko na obchod v %% pre rozpis po rokoch (default 1)")
    p.add_argument("--risks", help="riziká do tabuľky oddelené čiarkou (default 0.25,0.5,1,2,3)")
    p.add_argument("--min-trades", type=int, default=10, help="beh s menej obchodmi sa vynechá")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_portfolio)

    p = sub.add_parser("plateau", help="okolie víťaza hyperoptu — je to plató alebo špička?")
    p.add_argument("hyperopt_id", help="beh hyperoptu z histórie")
    p.add_argument("--iterations", type=int, default=2000, help="opakovaní Monte Carla (default 2000)")
    p.add_argument("--seed", type=int, default=12345)
    # Nastavenie behu (par, okno, poplatok, profil) sa berie z vitaza, nie z prikazu -
    # sused sa musi lisit LEN v tom jednom parametri, inak sa neporovnava okolie.
    p.add_argument("--note", default="", help="poznámka k susedným behom")
    p.add_argument("--user", help="meno testera (inak TRADEBOT_USER)")
    p.add_argument("--no-wait", action="store_true", help="nečakať na dobehnutie")
    p.set_defaults(func=cmd_plateau)

    p = sub.add_parser("nulltest", help="je edge odlíšiteľný od náhody? (porovnanie s náhodným vstupom)")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--null", choices=("anytime", "session"),
                   help="typ náhody; bez neho sa spočítajú obe a porovnajú")
    p.add_argument("--iterations", type=int, default=1000, help="koľko náhodných behov (default 1000)")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.set_defaults(func=cmd_nulltest)

    p = sub.add_parser("paper", help="meranie do docs/merania/ zo všetkého, čo vieme")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--strategy", default="ibs", help="stratégia (default ibs)")
    p.add_argument("--title", default="", help="nadpis dokumentu")
    p.add_argument("--name", default="", help="názov súboru (inak MERANIE_<strategia>_<trh>_<datum>.md)")
    p.add_argument("--risk-pct", type=float, default=1.0, dest="risk_pct",
                   help="riziko na obchod pre portfólio v %% (default 1)")
    p.add_argument("--iterations", type=int, default=400,
                   help="opakovaní testu proti náhode (default 400)")
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.add_argument("--stdout", action="store_true", help="vypísať, nezapisovať súbor")
    p.set_defaults(func=cmd_paper)

    p = sub.add_parser("decay", help="slabne edge? posledné obdobie proti vlastnej minulosti")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--parts", type=int, default=4, help="na koľko období deliť (default 4)")
    p.add_argument("--by", choices=("time", "count"), default="time",
                   help="rovnako dlhé kalendárne úseky (default) alebo rovnako početné")
    p.add_argument("--iterations", type=int, default=2000, help="koľko vzoriek (default 2000)")
    p.add_argument("--block", type=int, default=10,
                   help="dĺžka bloku pri losovaní; 1 = nezávislé obchody (default 10)")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.set_defaults(func=cmd_decay)

    p = sub.add_parser("matrix", help="ten istý profil na viacerých trhoch a TF (drží myšlienka?)")
    p.add_argument("--pairs", default="all",
                   help="`all` (default) alebo zoznam párov oddelený čiarkou")
    p.add_argument("--timeframes", default="3m",
                   help="zoznam timeframov oddelený čiarkou (default 3m)")
    p.add_argument("--goal", choices=tuple(_GOALS), default="break_even",
                   help="podľa čoho zoradiť bunky (default break-even poplatok)")
    p.add_argument("--max-dd", type=float, help="strop na max drawdown v %%")
    p.add_argument("--min-trades", type=int, default=10,
                   help="pod týmto počtom obchodov je bunka označená ako šum (default 10)")
    p.add_argument("--no-relative", dest="relative", action="store_false",
                   help="neprepočítavať prahy z absolútnych bodov na atr (závery z toho "
                        "nepatria nikam - prah v bodoch znamená na každom trhu inú vec)")
    _run_args(p)
    p.set_defaults(func=cmd_matrix, relative=True)

    p = sub.add_parser("checkup", help="základná analytika stratégie: päť okien a celá batéria meraní")
    p.add_argument("--windows", help="okná oddelené čiarkou (default päť referenčných)")
    p.add_argument("--runs", help="poskladať dokument z hotových behov namiesto nových "
                                  "(id oddelené čiarkou)")
    p.add_argument("--iterations", type=int, default=1000,
                   help="koľko náhodných behov v teste proti náhode (default 1000)")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--out", help="kam zapísať dokument (default "
                                 "tradebot/strategies/<stratégia>/docs/ANALYTIKA.md)")
    p.add_argument("--no-write", action="store_true", help="len vypísať, dokument nezapisovať")
    _run_args(p, timerange=False)
    p.set_defaults(func=cmd_checkup)

    p = sub.add_parser("matrices", help="matice z histórie; s argumentom vypíše tabuľku jednej")
    p.add_argument("matrix_id", nargs="?", help="značka matice (bez nej sa vypíše zoznam)")
    p.add_argument("--strategy", help="len matice tejto stratégie")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_matrices)

    p = sub.add_parser("hyperopt", help="hľadanie parametrov optimalizátorom (to isté zadanie ako sweep)")
    p.add_argument("--param", action="append", metavar="NAZOV=HODNOTY",
                   help="rozsah `od:do:krok` (hľadá sa v ňom spojito) alebo zoznam `a,b,c` "
                        "(hľadá sa medzi nimi); dá sa opakovať")
    p.add_argument("--suggested", action="store_true",
                   help="priestor podľa odporúčania stratégie (`hyperopt_cls.SUGGESTED`) — "
                        "to, čo na nej prežilo out-of-sample")
    p.add_argument("--goal", choices=tuple(_GOALS), default="break_even",
                   help="podľa čoho vybrať najlepšiu epochu (default break-even poplatok)")
    p.add_argument("--max-dd", type=float, help="strop na max drawdown v %%")
    p.add_argument("--min-trades", type=int, help="minimálny počet obchodov za rok, inak je epocha mimo")
    p.add_argument("--epochs", type=int, default=200,
                   help="koľko konfigurácií vyskúšať (default 200; každá je celý backtest)")
    p.add_argument("--seed", type=int, help="`--random-state` optimalizátora, na zopakovateľný beh")
    p.add_argument("--jobs", type=int, help="koľko epoch paralelne (default všetky jadrá)")
    p.add_argument("--no-verify", action="store_true",
                   help="nespúšťať víťaza na ďalších referenčných oknách (do záverov to nepatrí)")
    _run_args(p)
    p.set_defaults(func=cmd_hyperopt)

    p = sub.add_parser("sweeps", help="mriežky z histórie; s argumentom vypíše tabuľku jednej")
    p.add_argument("sweep_id", nargs="?", help="značka mriežky (bez nej sa vypíše zoznam)")
    p.add_argument("--strategy", help="len mriežky tejto stratégie (parametre sú v každej iné)")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_sweeps)

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
