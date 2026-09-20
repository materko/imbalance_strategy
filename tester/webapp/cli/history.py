"""Práca s históriou a stav.

`replay`, `chart`, `prune`, `list`, `show`, `recompute`, `status`, `pull`, `push`, `params`.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from tradebot.core.env import getenv

from .common import api, fmt_summary, server_alive
from .run import _execute


def cmd_replay(args: argparse.Namespace) -> int:
    """Bod mriežky, bunku matice alebo overenie prehrá ako obyčajný beh do histórie.

    Bod nesie celý efektívny config, takže beh je ten istý — len dostane obchody, log
    a graf. Funguje aj na beh z histórie (zopakovanie s dnešným kódom a dátami).
    """
    from ..batches import strip_tag
    from ..store import RunStore

    rec = RunStore().find(args.run_id)
    if rec is None and server_alive(args.url):
        try:
            rec = (api(args.url, f"/api/runs/{args.run_id}") or {}).get("record")
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
            rec = None
    if rec is None or not rec.get("params"):
        raise SystemExit(f"bod ani beh {args.run_id} sa nenasiel (zoznam bodov: `cli sweeps <mriezka>`)")
    batch = rec.get("batch") or {}
    povod = f"{batch.get('kind')} {batch.get('id')}" if batch else f"beh {args.run_id}"
    settings = strip_tag(dict(rec.get("settings") or {}))
    settings.pop("instrument", None)  # runner ho doplní z páru
    note = args.note or f"prehratý bod ({povod}): {rec.get('note') or ''}".strip()
    print(f"prehravam {povod}: {settings.get('pair')} {settings.get('timeframe')} "
          f"{settings.get('timerange')} [{settings.get('engine') or 'freqtrade'}]")
    novy = _execute(args, rec["params"], settings, note)
    if novy.get("status") == "queued":
        return 0
    print(fmt_summary(novy))
    be_bod = (rec.get("result") or {}).get("break_even_pct")
    be_beh = (novy.get("result") or {}).get("break_even_pct")
    if be_bod is not None and be_beh is not None and abs(float(be_bod) - float(be_beh)) > 1e-9:
        print(f"POZOR: break-even bodu bol {be_bod}, prehraty beh ma {be_beh} - zmenil sa kod "
              "alebo data od casu mriezky", file=sys.stderr)
    return 0 if novy.get("status") == "done" else 1


def cmd_chart(args: argparse.Namespace) -> int:
    """Prepočíta kresby behu do lokálnej cache grafov (to isté, čo webapp pri otvorení grafu)."""
    from .. import replay
    from ..store import RunStore

    store = RunStore()
    if store.has_chart(args.run_id) and not args.force:
        check = store.chart_check(args.run_id) or {}
        print(f"graf behu {args.run_id} uz je ({check.get('source') or 'legacy'})"
              + (f"\nPOZOR: {check['warning']}" if check.get("warning") else ""))
        return 0
    try:
        check = replay.compute(store, args.run_id, log=lambda t: print(t, flush=True))
    except (LookupError, ValueError) as exc:
        raise SystemExit(str(exc))
    return 0 if check.get("match") else 1


def cmd_prune(args: argparse.Namespace) -> int:
    """Odpratanie histórie do tvaru, ktorý patrí do gitu. Bez `--apply` len vypíše plán."""
    from .. import prune
    from ..store import RunStore

    store = RunStore()
    plan = prune.plan(store)
    print(prune.report(plan))
    if not args.apply:
        print("\nnic sa nezmenilo (suchy beh); vykonat: python -m tester.webapp.cli prune --apply"
              + (" --keep-charts" if args.keep_charts else ""))
        return 0
    vysledok = prune.apply(store, plan, keep_charts=args.keep_charts,
                           log=lambda t: print(t, flush=True))
    print(f"\nhotovo: {json.dumps(vysledok, ensure_ascii=False)}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    """Odloženie behov z histórie do gzipovaného archívu. Bez `--apply` len vypíše plán."""
    from .. import archive
    from ..store import RunStore

    store = RunStore()
    if args.restore:
        d = archive.restore(store, args.restore)
        if d is None:
            print(f"beh {args.restore} v archíve nie je")
            return 1
        archive.forget(args.restore)
        print(f"beh {args.restore} je späť v histórii: {d}")
        return 0

    recs = store.search(" ".join(args.query)) if args.query else store.all()
    if args.before:
        recs = [r for r in recs if r["id"][:8] < args.before]
    if args.empty_note:
        recs = [r for r in recs if not (r.get("note") or "").strip()]
    plan = archive.plan(store, recs)
    print(archive.report(plan))
    if not args.apply:
        print("\nnic sa nezmenilo (suchy beh); vykonat: rovnaky prikaz s --apply")
        return 0
    if not plan.ids:
        return 0
    vysledok = archive.apply(store, plan, log=lambda t: print(t, flush=True))
    print(f"\nhotovo: {json.dumps(vysledok, ensure_ascii=False)}")
    return 0 if not vysledok["failed"] else 1


def cmd_reindex(args: argparse.Namespace) -> int:
    """Postav index histórie odznova (`tester.webapp.index`) — zoznam behov ho používa."""
    import time

    from ..store import RunStore

    store = RunStore()
    if args.rebuild:
        store.index.close()
        for p in store.index.path.parent.glob("runs.sqlite3*"):
            p.unlink(missing_ok=True)
    t = time.time()
    if not store.index.sync(force=True):
        print("index sa nepodarilo otvoriť — webapp bude čítať súbory (pomaly)")
        return 1
    print(f"index hotový za {time.time() - t:.1f} s: {store.index.count('1', [])} behov, "
          f"{store.index.path.stat().st_size / 1e6:,.0f} MB".replace(",", " "))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    from ..store import RunStore

    recs = RunStore().search(" ".join(args.query)) if args.query else RunStore().all()
    for rec in recs[: args.limit]:
        note = f"  „{rec.get('note')}“" if rec.get("note") else ""
        print(fmt_summary(rec) + f"  [{rec.get('user', '')}]" + note)
    print(f"({len(recs)} behov)")
    return 0


def _print_streaks(rec: dict, trades: list[dict], currency: str) -> None:
    """Najdlhšia séria ziskov a strát behu aj s obchodmi, z ktorých je zložená.

    Starší beh série v súhrne nemá — dopočítajú sa z obchodov (`tradebot.core.money`),
    rovnako ako ich dopočíta detail behu vo webapp.
    """
    from tradebot.core.money import streaks as _streaks

    serie = (rec.get("result") or {}).get("streaks") or (_streaks(trades) if trades else {})
    for kind, nazov in (("win", "najdlhšia séria ziskov"), ("loss", "najdlhšia séria strát")):
        s = (serie or {}).get(kind)
        if not s or not s.get("n"):
            print(f"{nazov}: —")
            continue
        viac = f", rovnako dlhých sérií {s['count']}" if s.get("count", 1) > 1 else ""
        print(f"{nazov}: {s['n']} obchodov  {str(s.get('start') or '')[:16]} -> "
              f"{str(s.get('end') or '')[:16]}  spolu {s['pnl_abs']:+.2f} {currency}{viac}")
        for i, t in enumerate(trades[s["from_i"]: s["to_i"] + 1], start=s["from_i"] + 1):
            print(f"    {i:>5}. {str(t.get('open_date') or '')[:16]} -> {str(t.get('close_date') or '')[:16]}  "
                  f"{float(t.get('profit_abs') or 0.0):+10.2f} {currency}  "
                  f"{float(t.get('profit_ratio') or 0.0) * 100:+7.2f} %  {t.get('exit_reason') or ''}")


def cmd_show(args: argparse.Namespace) -> int:
    from tradebot.strategies import get_spec
    from ..store import RunStore, diff_from_defaults, strategy_of

    store = RunStore()
    rec = store.get(args.run_id)
    if rec is None:
        raise SystemExit(f"beh {args.run_id} neexistuje")
    print(fmt_summary(rec))
    print("nastavenia:", json.dumps(rec.get("settings"), ensure_ascii=False))
    defaults = get_spec(strategy_of(rec)).config_cls().to_dict()
    print("odchýlky od Pine defaultov:", json.dumps(diff_from_defaults(rec.get("params") or {}, defaults), ensure_ascii=False))
    r = rec.get("result") or {}
    if r.get("exits"):
        print("výstupy:", json.dumps(r["exits"], ensure_ascii=False))
    _print_streaks(rec, store.trades(args.run_id), r.get("stake_currency") or "USDT")
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2, default=str))
    return 0


def cmd_recompute(args: argparse.Namespace) -> int:
    """Prepočet súhrnov z `trades.json` a hodnoty bodu (`tester.recompute`)."""
    from ... import recompute

    argv = ["--examples", str(args.examples)] + (["--pair", args.pair] if args.pair else [])
    return recompute.main(argv + (["--write"] if args.write else []))


def cmd_status(args: argparse.Namespace) -> int:
    from .. import gitsync

    alive = server_alive(args.url)
    print(f"webapp {args.url}: {'beží' if alive else 'nebeží'}")
    if alive:
        q = api(args.url, "/api/queue")
        print(f"fronta: {len(q)} " + ", ".join(f"{j['id']} {j['status']}" for j in q))
    st = gitsync.status()
    print(f"git: vetva {st['branch']} → {st.get('target', 'main')}, "
          f"necommitnuté behy, mriežky a profily {st['uncommitted']}, "
          f"ahead {st['ahead']}, behind {st['behind']}")
    if st.get("ignored"):
        print(f"POZOR: git ignoruje {len(st['ignored'])} súborov histórie, Push ich neodošle "
              f"a zastaví sa: {', '.join(st['ignored'][:3])}")
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    from .. import gitsync

    r = gitsync.pull()
    print(r["output"])
    return 0 if r["ok"] else 1


def cmd_push(args: argparse.Namespace) -> int:
    from .. import gitsync

    r = gitsync.push(author=args.user or getenv("USER") or None)
    print(r["output"] or "nič na commit, nič na push")
    return 0 if r["ok"] else 1


def cmd_params(args: argparse.Namespace) -> int:
    from ..param_meta import param_metadata

    for m in param_metadata(args.strategy):
        if args.filter and args.filter.lower() not in f"{m['name']} {m['title']} {m['tooltip']}".lower():
            continue
        rng = f"  [{m['min']}–{m['max']}]" if m.get("min") is not None else ""
        opts = f"  {m['options']}" if m.get("options") else ""
        unit = f"  (size, jednotka {m['base_unit']})" if m["type"] == "size" else f"  ({m['type']})"
        print(f"{m['name']:<24} {m['group']} · {m['title']}{unit}{rng}{opts}")
    return 0
