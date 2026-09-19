"""Jeden beh: poskladanie parametrov a `settings`, spustenie cez webapp, priamo alebo na hube."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request

from tradebot.core.env import getenv

from .common import api, fmt_summary, parse_set, server_alive
from .remote import _remote_execute


def _prepare(args: argparse.Namespace, *, check_engine: bool = True) -> tuple[dict, dict]:
    """(parametre, nastavenia behu) z argumentov — spoločné pre `run` aj `sweep`.

    `check_engine=False` preskočí kontrolu, či sa dá engine na páre a TF spustiť —
    pre príkazy, ktoré nič nespúšťajú (`checkup --runs`), by inak klon bez dát padol
    skôr, než sa dostane k hotovým behom.
    """
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import STRATEGIES

    from ... import engines
    from ..runner import default_params, instrument_for_pair

    if args.strategy not in STRATEGIES:
        raise SystemExit(f"neznáma stratégia {args.strategy!r}; známe: {', '.join(sorted(STRATEGIES))}")
    # TF grafu bez prepínača je TF, na ktorom stratégia bežala v TradingView — nie 3m
    # pre všetky. `checkup --strategy structure` by inak ticho meral 5m stratégiu na 3m.
    if not getattr(args, "timeframe", None):
        args.timeframe = STRATEGIES[args.strategy].default_timeframe
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
    # Syntetický trh dedí mierku zo zdroja, takže prahy v bodoch na ňom platia —
    # varovanie by tam bolo falošné.
    mierka = INSTRUMENTS[pair_instrument].scale_of or pair_instrument
    if instrument and mierka != instrument:
        print(f"POZOR: profil {args.profile} je pre {instrument}, ale pár {pair} je {pair_instrument}. "
              "Prahy v bodoch/tickoch nesedia - použi profil pre tento nástroj.",
              file=sys.stderr)

    inst = INSTRUMENTS[pair_instrument]
    engine = args.engine or engines.default_engine(inst, args.timeframe)
    exchange = args.exchange or engines.DEFAULT_EXCHANGE
    possible = engines.available(inst, args.timeframe, exchange) if check_engine else [engine]
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
        "timerange": args.timerange, **_fee_for(args, pair), "ai": _ai_for(args),
        "wallet": args.wallet, "timeframe_detail": None if args.no_detail else "1m",
        "profile": args.profile,
    }
    return params, settings


def _ai_for(args: argparse.Namespace) -> dict | None:
    """Nastavenie AI vrstvy z prepínačov, alebo `None`, keď je vypnutá."""
    from tradebot.strategies import get_spec
    from tradebot.strategies.hyperopt import StrategyHyperopt

    zapnute = {k: v for k, v in (
        ("min_probability", args.ai_min_prob), ("train_period_days", args.ai_train_days),
        ("backtest_period_days", args.ai_backtest_days), ("model", args.ai_model),
    ) if v is not None}

    # Ktore kluce ta strategia dovoli menit, vie len ona sama - generická vrstva ich
    # menom nepozna.
    povolene = (get_spec(args.strategy).hyperopt_cls or StrategyHyperopt).ai_adjustable()
    adjust: dict[str, list[float]] = {}
    for polozka in args.ai_adjust or []:
        kluc, _, rozsah = polozka.partition("=")
        kluc = kluc.strip()
        if kluc not in povolene:
            zoznam = "\n  ".join(\
                f"{k:<6} {v[1]}" + (f"  (staticky: {v[0]})" if v[0] else "")
                for k, v in povolene.items())
            raise SystemExit(
                f"{kluc!r} sa modelom menit neda. Strategia {args.strategy} dovoli:\n  {zoznam}\n"
                f"Ostatne parametre rozhoduju, ci signal VOBEC vznikne - v case, ked model "
                f"predpoveda, engine uz dobehol. Tam je jedina odpoved 'ber / neber' a to "
                f"robi filter (--ai-min-prob).")
        try:
            a, b = (float(x) for x in rozsah.split(":"))
        except ValueError:
            raise SystemExit(f"--ai-adjust {kluc} chce tvar {kluc}=OD:DO, napr. {kluc}=0.5:1.5")
        if a <= 0 or b <= 0:
            raise SystemExit(f"--ai-adjust {kluc}: nasobok musi byt kladny")
        adjust[kluc] = [a, b]

    if not (args.ai or zapnute or adjust):
        return None
    return {"enabled": True, **zapnute, **({"adjust": adjust} if adjust else {})}


def _fee_for(args: argparse.Namespace, pair: str, timeframe: str | None = None) -> dict:
    """`{"fee": …, "fee_note": …}` — zadané číslo, alebo náklad toho trhu.

    Jeden default pre všetky trhy nefunguje: 0,05 % je Binance taker, kým na CFD je
    provízia drobná a náklad je spread. Preto sa default berie z inštrumentu a do behu
    sa uloží aj to, odkiaľ číslo je — bez toho sa o mesiac nedá zistiť, či bolo zmerané.
    """
    from ... import fees as fees_mod

    if args.fee is not None:
        return {"fee": args.fee, "fee_note": "zadané cez --fee"}
    fee, note = fees_mod.for_pair(pair, timeframe or args.timeframe, args.timerange)
    if fee is None:
        print(f"POZOR: naklad na {pair} nepozname ({note}); bezi sa s nulou, "
              f"break-even sa proti nicomu neposudzuje", file=sys.stderr)
        return {"fee": 0.0, "fee_note": f"neznámy: {note}"}
    return {"fee": fee, "fee_note": note}


def _execute(args: argparse.Namespace, params: dict, settings: dict, note: str,
             quiet: bool = False) -> dict:
    """Spustí jeden beh (cez frontu webapp, alebo priamo) a vráti jeho záznam."""
    user = args.user or getenv("USER") or ""

    if getattr(args, "remote", False):
        return _remote_execute(args, params, settings, note, quiet)

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
    from ..runner import BacktestRunner
    from ..store import RunStore

    store = RunStore()
    runner = BacktestRunner(store)
    job = runner.submit(params, settings, note=note, user=user)
    if not quiet:
        print(f"webapp nebeží, spúšťam priamo: {job.id}")
    while job.status in ("queued", "running"):
        time.sleep(2)
        if not quiet and job.log_lines:
            print(f"  … {job.log_lines[-1][:100]}", flush=True)
    # bod mriežky/matice nie je v histórii, ale v `sweeps/` — `find` nájde oboje
    return store.find(job.id) or {"id": job.id, "status": job.status, "error": job.error,
                                  "settings": settings}


def cmd_run(args: argparse.Namespace) -> int:
    params, settings = _prepare(args)
    rec = _execute(args, params, settings, args.note or "")
    if rec.get("status") == "queued":
        return 0
    print(fmt_summary(rec))
    return 0 if rec.get("status") == "done" else 1
