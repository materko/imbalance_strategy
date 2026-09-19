"""Rozbory nad behmi v histórii (`nulltest`, `paper`, `analytics`, `prop`, `decay`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tradebot.core.paths import REPO

from .common import _selected_runs, _trades_of


def cmd_nulltest(args: argparse.Namespace) -> int:
    """Porovná break-even stratégie s náhodným vstupom za tých istých pravidiel."""
    from ... import nulltest as nt
    from ..store import RunStore

    store = RunStore()
    zaznamy = _selected_runs(args, store)

    pary = {r["settings"].get("pair") for r in zaznamy}
    if len(pary) > 1:
        raise SystemExit("nahodne vstupy sa losuju zo sviecok jedneho paru, takze behy "
                         f"musia byt z jedneho trhu; vybrane su: {', '.join(sorted(pary))}")
    tfs = {r["settings"].get("timeframe") or "3m" for r in zaznamy}
    if len(tfs) > 1:
        raise SystemExit("dlzka drzania sa prepocitava z barov TF, takze behy musia byt "
                         f"z jedneho timeframu; vybrane su: {', '.join(sorted(tfs))}")
    pair = zaznamy[0]["settings"]["pair"]
    timeframe = tfs.pop()

    obchody = _trades_of(store, zaznamy, with_market=False)

    print(f"{len(zaznamy)} behov, {len(obchody)} obchodov, {pair} {timeframe}")
    okna = sorted({r["settings"].get("timerange") for r in zaznamy if r["settings"].get("timerange")})
    print(f"okna: {', '.join(okna)}\n")

    najprv = None
    for null in ([args.null] if args.null else list(nt.NULLS)):
        # Nahoda sa losuje z tych istych okien - z celej historie paru by niesla drift
        # rokov, v ktorych strategia nebezala.
        vysledok = nt.compare(obchody, pair=pair, timeframe=timeframe, timerange=okna or None,
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

    from ... import paper as pp
    from ..store import RunStore

    store = RunStore()
    zaznamy = _selected_runs(args, store, strategy=args.strategy)

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


def cmd_analytics(args: argparse.Namespace) -> int:
    """Ulozene analytiky - per strategia, od najnovsej."""
    from ... import analytics as an
    from .. import anstore as ast
    from ..anstore import AnalyticsStore

    st = AnalyticsStore()
    if args.analytics_id and args.posudok:
        text = args.posudok
        if text.startswith("@"):
            try:
                text = Path(text[1:]).read_text(encoding="utf-8")
            except OSError as exc:
                raise SystemExit(f"posudok sa neda precitat: {exc}")
        if st.set_posudok(args.analytics_id, text, args.user or "") is None:
            raise SystemExit(f"analytika {args.analytics_id} v historii nie je")
        print(f"posudok ulozeny k {args.analytics_id}")
        return 0
    if args.analytics_id:
        z = st.get(args.analytics_id)
        if z is None:
            raise SystemExit(f"analytika {args.analytics_id} v historii nie je")
        print(f"=== {z['id']} ({z['strategy']}) ===")
        print(f"ulozena {z['created'][:19]}"
              + (f", {z['user']}" if z.get("user") else ""))
        if z.get("note"):
            print(f"poznamka: {z['note']}")
        print(f"{z['trades']} obchodov z {len(z['run_ids'])} behov: "
              f"{', '.join(z.get('pairs') or []) or '-'}")
        print(f"behy: {', '.join(z['run_ids'])}")
        print()
        print(an.table(z["report"]))

        # Posudok je to, co cisla nepovedia. Ked chyba, vypise sa zadanie, ktore sa da
        # podat AI - namiesto toho, aby tam bolo prazdne miesto bez navodu.
        posudok = (z.get("posudok") or "").strip()
        print()
        if not posudok:
            print("=== Posudok chyba ===")
            print(ast.zadanie(z.get("report") or {}))
            print()
            print(f"Ulozit: python -m tester.webapp.cli analytics {z['id']} "
                  f"--posudok @subor.md")
        else:
            stary_p = z.get("posudok_stamp") != z.get("numbers")
            print("=== Posudok" + (" (STARY: cisla sa medzitym zmenili)" if stary_p else "")
                  + f", {z.get('posudok_at', '')[:19]} {z.get('posudok_user', '')} ===")
            print(posudok)
        return 0

    polozky = st.list(args.strategy or "", limit=args.limit)
    if not polozky:
        print("historia analytiky je prazdna"
              + (f" pre strategiu {args.strategy}" if args.strategy else ""))
        return 1
    print(f"{'analytika':<24}{'strategia':<12}{'obch.':>7}{'behov':>7}{'break-even':>12}  poznamka")
    for x in polozky:
        be = "-" if x.get("break_even_pct") is None else f"{x['break_even_pct']:+.4f}"
        print(f"{x['id']:<24}{x['strategy']:<12}{x['trades'] or 0:>7}{x['runs']:>7}{be:>12}  "
              f"{(x.get('note') or '')[:50]}")
    print("\ndetail: python -m tester.webapp.cli analytics <id>")
    return 0


def cmd_prop(args: argparse.Namespace) -> int:
    """Prop vyzva: dostane sa strategia k vyplate skor, nez ucet zhori?"""
    from ... import analytics as an, prop as pr
    from ..store import RunStore

    # Kazde pole sa da prepisat: cisla v presetoch su bezny tvar pravidiel, nie ponuka
    # konkretnej firmy - pred pouzitim patri prepisat podla zmluvy, ktoru tester ma.
    # Prepisy platia na `custom` a na jedinu vybranu predlohu; pri porovnani viacerych
    # firiem sa beru ich pravidla tak, ako su.
    zmeny = {k: v for k, v in (
        ("account", args.account), ("max_daily_loss_pct", args.daily),
        ("max_loss_pct", args.max_loss), ("min_days", args.min_days),
        ("max_day_share_pct", args.day_share), ("cost", args.cost),
        ("payout_pct", args.payout), ("horizon_days", args.horizon),
        ("trailing", args.trailing),
    ) if v is not None}
    if args.targets:
        try:
            zmeny["targets"] = tuple(float(x) for x in args.targets.split(","))
        except ValueError:
            raise SystemExit("--targets su ciele faz oddelene ciarkou, napr. 10,5")
    kluce = [x.strip() for x in str(args.rules).split(",") if x.strip()]
    if zmeny and pr.CUSTOM not in kluce:
        # Prepisy patria len vlastnym pravidlam - predlohy firiem sa nemenia. Kto zada
        # prepinac, chce ich vidiet, tak sa `custom` prida a povie sa to.
        kluce.append(pr.CUSTOM)
        print(f"prepisy ({', '.join(sorted(zmeny))}) platia len na `custom` - pridany "
              "k porovnaniu; predlohy firiem ostavaju tak, ako su", file=sys.stderr)
    try:
        predlohy = pr.rules_for(kluce, zmeny)
    except ValueError as exc:
        raise SystemExit(str(exc))

    store = RunStore()
    zaznamy = _selected_runs(args, store)
    obchody = _trades_of(store, zaznamy, with_market=False)

    pary = sorted({r["settings"].get("pair") for r in zaznamy if r["settings"].get("pair")})
    print(f"{len(zaznamy)} behov, {len(obchody)} obchodov, {', '.join(pary)}\n")
    # Vyzva sa pocita z obchodov vybranych behov, nie z nejakej vlastnej konfiguracie -
    # nech je vidiet, z ktorej.
    konfig = an.config_spread(zaznamy)
    print(f"konfiguracia: {konfig['note']}")
    if konfig["severity"] == "chyba":
        print("POZOR: zliate obchody roznych konfiguracii hovoria o kazdej z nich trochu "
              "a o ziadnej presne.", file=sys.stderr)
    print()

    rizika = [args.risk] if args.risk else list(pr.RISKS)
    varianty = []
    for kluc, pravidla in predlohy:
        vysledky = pr.risk_table(obchody, pravidla, risks=rizika, step=args.step)
        varianty.append((kluc, vysledky))
        print(pr.report(vysledky, f"{kluc} — {', '.join(pary)}"))
        print()
    if len(varianty) > 1:
        print(pr.compare(varianty))
    najlepsie = [max(v, key=lambda r: (r.ev if r.ev is not None else -1e18)) for _, v in varianty if v]
    return 0 if any((r.ev or 0) > 0 for r in najlepsie) else 1


def cmd_decay(args: argparse.Namespace) -> int:
    """Slabne edge? Posledné obdobie proti tomu, čo stratégia robievala."""
    from ... import decay as dc
    from ..store import RunStore

    store = RunStore()
    zaznamy = _selected_runs(args, store)
    obchody = _trades_of(store, zaznamy, with_market=False)

    okna = sorted({r["settings"].get("timerange") for r in zaznamy if r["settings"].get("timerange")})
    pary = sorted({r["settings"].get("pair") for r in zaznamy if r["settings"].get("pair")})
    print(f"{len(zaznamy)} behov, {len(obchody)} obchodov, {', '.join(pary)}")
    print(f"okna: {', '.join(okna)}\n")

    vysledok = dc.analyze(obchody, parts=args.parts, by=args.by,
                          iterations=args.iterations, block=args.block, seed=args.seed)
    print(dc.report(vysledok, label=", ".join(pary)))
    return 0 if vysledok.verdict != "MALO DAT" else 1
