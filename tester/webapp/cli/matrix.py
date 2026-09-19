"""Matice trhov a základná analytika stratégie (`matrix`, `matrices`, `checkup`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from tradebot.core.paths import REPO

from .common import _run_data, _run_record
from .remote import _remote_prefetch
from .run import _execute, _fee_for, _prepare


def cmd_matrix(args: argparse.Namespace) -> int:
    """Matica trhov a timeframov: drží myšlienka aj mimo trhu, na ktorom sa ladila?"""
    from datetime import datetime, timezone
    from uuid import uuid4

    from ... import matrix as mx, sweep as sweep_mod
    from ..runner import available_pairs

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

    body = []
    for cell in bunky:
        # Poplatok patrí TOMU trhu, nie referenčnému: `settings` ich má z páru profilu,
        # takže bez tohto by matica účtovala Binance taker 0,05 % aj CFD na kávu, kde je
        # náklad polovica spreadu. Na poradie buniek to nemá vplyv (break-even od poplatku
        # nezávisí), ale PnL a profit factor každej cudzej bunky by boli nezmysel.
        beh = {**settings, "pair": cell.pair, "timeframe": cell.timeframe,
               **_fee_for(args, cell.pair, cell.timeframe),
               "matrix": {"id": matrix_id, "pair": cell.pair, "timeframe": cell.timeframe,
                          "goal": args.goal, "relative": bool(args.relative),
                          "cells": len(bunky)}}
        body.append((cell, params, beh, f"matica {matrix_id}: {cell.pair} {cell.timeframe}"
                     + (f" — {args.note}" if args.note else "")))
    _remote_prefetch(args, [b[1:] for b in body])

    zaznamy = []
    for i, (cell, params, beh, note) in enumerate(body, 1):
        print(f"[{i}/{len(bunky)}] {cell.pair} {cell.timeframe}", flush=True)
        try:
            rec = _execute(args, params, beh, note=note, quiet=True)
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

    from ... import analytics as an, checkup as ck, hyperopt as ho, montecarlo as mc
    from ..store import RunStore

    okna = ([x.strip() for x in args.windows.split(",") if x.strip()]
            if args.windows else list(ho.REFERENCE_WINDOWS))
    if not okna:
        raise SystemExit("--windows nesmie byt prazdne")
    # `_prepare` chce jedno okno; ostatné sa dosadia pri behu. Musí to byť okno zo
    # zoznamu, nech kontrola dát (páry, engine) platí o tom, čo sa naozaj spustí.
    args.timerange = okna[0]
    params, settings = _prepare(args, check_engine=not args.runs)
    store = RunStore()

    if args.runs:
        from ..store import strategy_of

        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (_run_record(store, args.url, i) for i in chcene) if r]
        if not zaznamy:
            raise SystemExit("ziadny z behov v --runs v historii nie je")
        # Dokument patri jednej strategii na jednom trhu a TF: nahoda aj charakter beru
        # sviecky jedneho paru a vzdialenosti stopu sa medzi trhmi porovnat nedaju.
        cudzie = sorted({strategy_of(r) for r in zaznamy} - {args.strategy})
        if cudzie:
            raise SystemExit(f"behy v --runs patria strategii {', '.join(cudzie)}, nie "
                             f"{args.strategy} - zadaj --strategy podla behov")
        for kluc, popis in (("pair", "paru"), ("timeframe", "timeframu"), ("engine", "enginu")):
            # Staršie záznamy `engine` nemajú (bežali vo Freqtrade); chýbajúca hodnota
            # nie je iný engine.
            hodnoty = sorted({str(v) for r in zaznamy
                              if (v := (r.get("settings") or {}).get(kluc)) is not None})
            if len(hodnoty) > 1:
                raise SystemExit(f"behy v --runs su z viacerych {popis} ({', '.join(hodnoty)}); "
                                 "analytika strategie sa meria na jednom")
        konfig = an.config_spread(zaznamy)
        if konfig["severity"] != "ok":
            print(f"POZOR: {konfig['note']}", file=sys.stderr)
        okna = [(r.get("settings") or {}).get("timerange") or "?" for r in zaznamy]
        settings = {**settings, **{k: (zaznamy[0].get("settings") or {}).get(k, settings.get(k))
                                   for k in ("pair", "timeframe", "engine", "fee", "fee_note",
                                             "wallet")}}
        args.timeframe = settings["timeframe"]
        print(f"analytika z {len(zaznamy)} hotovych behov (nic sa nespusta)")
    else:
        checkup_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        print(f"checkup {checkup_id}: {len(okna)} behov, {settings['pair']} "
              f"{settings['timeframe']}, engine {settings['engine']}"
              + (f", profil {args.profile}" if args.profile else " (Pine defaulty)"))
        print(f"  okna: {', '.join(okna)}\n", flush=True)
        body = []
        for okno in okna:
            beh = {**settings, "timerange": okno,
                   "checkup": {"id": checkup_id, "strategy": args.strategy}}
            body.append((okno, params, beh, f"checkup {checkup_id}: {okno}"
                         + (f" — {args.note}" if args.note else "")))
        _remote_prefetch(args, [b[1:] for b in body])

        zaznamy = []
        for i, (okno, params, beh, note) in enumerate(body, 1):
            print(f"[{i}/{len(okna)}] {okno}", flush=True)
            rec = _execute(args, params, beh, note=note, quiet=True)
            rec.setdefault("settings", beh)
            zaznamy.append(rec)
            r = rec.get("result") or {}
            print(f"      {rec.get('status')}  obchodov {r.get('trades', '-')}  "
                  f"PnL {r.get('pnl_pct', '-')} %  break-even {r.get('break_even_pct', '-')} %",
                  flush=True)

    # Obchody zo všetkých okien spolu: jedno okno má na delenie na skupiny málo obchodov.
    # Obohatia sa kresbami toho behu, z ktorého sú — v nich je plán obchodu (SL, TP) —
    # a sviečkami páru (stav trhu pri vstupe).
    hotove = [r for r in zaznamy if r.get("status") == "done"]
    data = {r["id"]: _run_data(store, args.url, r["id"]) for r in hotove}
    nacitane = an.trades_of(hotove, lambda i: data[i][0], lambda i: data[i][1],
                            strategy=args.strategy)
    obchody, duplicity = nacitane.trades, nacitane.duplicates

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
                        fee_note=settings.get("fee_note") or "",
                        profile=args.profile or "", engine=settings.get("engine") or "freqtrade",
                        account=float(settings.get("wallet") or 10000), risk_ref=risk_ref,
                        iterations=args.iterations, seed=args.seed, duplicates=duplicity)
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


def _checkup_command(args: argparse.Namespace, okna: list[str]) -> str:
    """Príkaz, ktorým sa tá istá analytika zopakuje — patrí do dokumentu, nie do hlavy."""
    from ... import hyperopt as ho

    cmd = ["python -m tester.webapp.cli checkup", f"--strategy {args.strategy}"]
    if args.profile:
        cmd.append(f"--profile {args.profile}")
    if args.pair:
        cmd.append(f"--pair {args.pair}")
    cmd.append(f"--timeframe {args.timeframe}")
    if args.fee is not None:
        cmd.append(f"--fee {args.fee}")
    if float(args.wallet) != 10000.0:
        cmd.append(f"--wallet {args.wallet:g}")
    if list(okna) != list(ho.REFERENCE_WINDOWS):
        cmd.append("--windows " + ",".join(okna))
    return (" \\" + "\n   ").join(cmd)


def cmd_matrices(args: argparse.Namespace) -> int:
    """Matice z histórie; s argumentom vypíše tabuľku jednej."""
    from ... import matrix as mx
    from ..store import RunStore

    skupiny: dict[str, list[dict]] = {}
    for rec in RunStore().tagged("matrix"):
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
