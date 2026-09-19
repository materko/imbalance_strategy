"""Mriežky, portfólio a okolie víťaza (`sweep`, `sweeps`, `portfolio`, `plateau`)."""

from __future__ import annotations

import argparse
import sys

from .common import warn_parity
from .remote import _remote_prefetch
from .run import _execute, _prepare


def cmd_sweeps(args: argparse.Namespace) -> int:
    """Zoznam mriežok z histórie, alebo tabuľka jednej z nich.

    Body mriežky sú v `tester/sweeps/sweep-<id>.json` (staršie mriežky ešte ako behy
    v histórii — `tagged` spojí oboje). Aj mriežka spustená vo webapp sa dá otvoriť tu
    a naopak; bod sa prehrá ako obyčajný beh príkazom `replay <id>`.
    """
    from ... import sweep as sweep_mod
    from ..store import RunStore

    zaznamy = RunStore().tagged("sweep")
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
                                max_dd=tag.get("max_dd"), min_trades=tag.get("min_trades"),
                                per_year=bool(tag.get("per_year")))
        nastavenia = rows[0]["settings"]
        print(f"=== sweep {args.sweep_id} - {zadanie} ===")
        print(f"{nastavenia.get('pair')} {nastavenia.get('timeframe')} "
              f"{nastavenia.get('timerange')}, behov {len(rows)}\n")
        print(sweep_mod.table(ranked, list(tag.get("values") or {}), tag.get("goal")))
        if ranked and ranked[0].get("sweep_ok"):
            print(f"\nnajlepsi bod: {ranked[0]['id']}  (ako beh do historie: "
                  f"python -m tester.webapp.cli replay {ranked[0]['id']})")
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

    from ... import sweep as sweep_mod

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

    body = []
    for point in points:
        popis = ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in point.items())
        run_settings = {**settings, "sweep": {"id": sweep_id, "values": point, "goal": args.goal,
                                              "max_dd": args.max_dd, "min_trades": args.min_trades,
                                              "per_year": True, "points": len(points)}}
        body.append((popis, {**params, **point}, run_settings,
                     f"sweep {sweep_id}: {popis}" + (f" — {args.note}" if args.note else "")))
    _remote_prefetch(args, [b[1:] for b in body])

    records = []
    for i, (popis, bod_params, run_settings, note) in enumerate(body, 1):
        print(f"[{i}/{len(points)}] {popis}", flush=True)
        rec = _execute(args, bod_params, run_settings, note=note, quiet=True)
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
        print("\nnajlepsi bod: " + best["id"])
        print("  " + ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in values.items()))
        print("  body mriezky sa do historie neukladaju (len vysledok v tester/sweeps/); ako "
              f"beh s grafom: python -m tester.webapp.cli replay {best['id']}")
        print("  over ho na dalsich referencnych oknach, nez z neho spravis profil "
              "(jedno okno o strategii nic nepovie)")
    else:
        print("\nziadny beh nepresiel mantinelmi - uvolni --max-dd/--min-trades alebo zmen rozsah")
    return 0


def cmd_portfolio(args: argparse.Namespace) -> int:
    """Vybrané behy ako jedno portfólio: cena rizika, rok po roku, korelácie."""
    from ... import analytics as an, portfolio as pf
    from ..store import RunStore

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
    from ... import montecarlo as mc, plateau as pl
    from ..batches import strip_tag
    from ..store import RunStore

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
    overenia = store.tagged("hyperopt_run", args.hyperopt_id)
    ladene = [r for r in overenia if (r["settings"].get("hyperopt_run") or {}).get("tuned")]
    if not ladene:
        raise SystemExit("beh vitaza na ladenom okne v historii nie je (spustil sa hyperopt "
                         "s --no-verify?)")
    vitaz = ladene[0]

    # Starý overovací beh v histórii má obchody; bod v `sweeps/` nesie interval spočítaný
    # pri uložení (pl.MC_ITERATIONS, pl.MC_SEED) a --iterations/--seed sa naň nevzťahujú.
    obchody = store.trades(vitaz["id"]) if "batch" not in vitaz else []
    interval = pl.winner_ci(vitaz, obchody or None, iterations=args.iterations, seed=args.seed)
    if interval[0] is None:
        pocet = len(obchody) or int((vitaz.get("result") or {}).get("trades") or 0)
        print(f"POZOR: vitaz ma len {pocet} obchodov, interval spolahlivosti sa "
              f"nepocita (treba aspon {mc.MIN_TRADES}).", file=sys.stderr)

    susedia = pl.neighbours(zadanie["knobs"], vitaz_params)
    if not susedia:
        raise SystemExit("vitaz nema ziadnych susedov v rozsahu planu")

    zaklad = {k: v for k, v in (vitaz.get("params") or {}).items()}
    settings_zaklad = strip_tag(vitaz["settings"])
    print(f"okolie vitaza {args.hyperopt_id}: {len(susedia)} susedov, okno "
          f"{settings_zaklad.get('timerange')}")
    print(f"  vitaz: {', '.join(f'{k}={v}' for k, v in vitaz_params.items())}\n", flush=True)

    body = []
    for sused in susedia:
        params = {**zaklad, sused.param: sused.value}
        settings = {**settings_zaklad,
                    "plateau": {"id": args.hyperopt_id, "param": sused.param,
                                "value": sused.value, "step": sused.step}}
        body.append((sused, params, settings, f"okolie {args.hyperopt_id}: {sused.param}={sused.value}"))
    _remote_prefetch(args, [b[1:] for b in body])

    zaznamy = []
    for i, (sused, params, settings, note) in enumerate(body, 1):
        print(f"[{i}/{len(susedia)}] {sused.label} = {sused.value}", flush=True)
        try:
            rec = _execute(args, params, settings, note=note, quiet=True)
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
