"""`python -m tester.hub …` — hub, headless agent, nastavenie a stav.

    python -m tester.hub serve --host 0.0.0.0 --port 8790         # hub (TRADEBOT_HUB_TOKEN=…)
    python -m tester.hub setup --name srv-01 --hub-url https://hub:8790 --token … --accept --send
    python -m tester.hub agent                                    # headless agent tohto klonu
    python -m tester.hub status                                   # agenti, fronta, kapacita
    python -m tester.hub jobs [--all]                             # výpočty na hube
    python -m tester.hub cancel <job_id>                          # zrušiť výpočet
    python -m tester.hub forget <meno> [--with-token]             # vyhodiť agenta z hubu
    python -m tester.hub sparse --no-history [--data binance]     # chudý klon (netiahne dáta)
    python -m tester.hub token add srv-01 [--local]               # token agenta (správca)
    python -m tester.hub events [--job ID] [--agent MENO] [--local]  # log udalostí hubu

`--local` pracuje priamo so stavom hubu na disku (`tester/hub_data`) — pre príkazy
spúšťané na stroji hubu (v kontajneri cez `docker compose exec hub …`), kde nie je
nastavený agent. Bez neho idú cez API s tokenom z `tester/agent.json`.

Výpočty sa **posielajú** z webapp CLI: `python -m tester.webapp.cli run --remote …` a
`… hyperopt --remote …` (s `--queue`, `--max-wait`).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from tradebot.core.env import getenv

from . import config as agent_config
from .client import fmt_eta as _fmt_eta
from .server import DEFAULT_PORT


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import HubState, create_hub_app

    token = args.token or getenv("HUB_TOKEN") or ""
    if args.host not in ("127.0.0.1", "localhost", "::1") and not token:
        raise SystemExit("hub na verejnej adrese potrebuje token: --token alebo TRADEBOT_HUB_TOKEN")
    state = HubState(token=token or None, heartbeat_seconds=args.heartbeat)
    app = create_hub_app(state)
    print(f"TradeBot hub: http://{args.host}:{args.port}  (stav v {state.root}, "
          f"tokenov agentov {len(state.token_names())})", flush=True)
    updater = _start_updater(args, state)
    if not token and not state.token_names():
        # Bind na localhost nič neznamená, keď pred hubom stojí reverse proxy: hub je
        # potom verejný a bez tokenu ho smie ovládať ktokoľvek, kto sa naň dostane.
        print("POZOR: hub beží bez jediného tokenu — je otvorený každému, kto sa naň "
              "dostane (aj cez reverse proxy). Token: --token / TRADEBOT_HUB_TOKEN.", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    if updater is not None:
        updater.stop()
    return 0


def _start_updater(args: argparse.Namespace, state: Any):
    """Samoaktualizácia: `--update MIN` (alebo TRADEBOT_HUB_UPDATE) — hub si pullne kód a
    keď sa zmenil, skončí; v kontajneri ho `restart: unless-stopped` zdvihne na novom."""
    from .update import Updater, from_env

    minuty = args.update
    if minuty is not None and minuty <= 0:
        return None
    u = (Updater(state, interval=minuty * 60, branch=args.branch,
                 max_wait=(args.update_max_wait or 0) * 60)
         if minuty is not None else from_env(state))
    if u is None:
        return None
    u.start()
    print(f"Samoaktualizacia: kazdych {u.interval / 60:.0f} min fetch origin/{u.branch}, "
          f"restart po zmene kodu "
          + ("hned, ked nic nepocita" if not u.max_wait
             else f"ked nic nepocita, najneskor o {u.max_wait / 60:.0f} min")
          + f" (kod {u.start_version or '?'})", flush=True)
    return u


def cmd_setup(args: argparse.Namespace) -> int:
    stary = agent_config.load()
    cfg = agent_config.AgentConfig(
        name=args.name or (stary.name if stary else None) or __import__("socket").gethostname(),
        hub_url=args.hub_url or (stary.hub_url if stary else ""),
        token=args.token if args.token is not None else (stary.token if stary else ""),
        accept=stary.accept if (args.accept is None and stary) else bool(args.accept if args.accept is not None else True),
        send=stary.send if (args.send is None and stary) else bool(args.send if args.send is not None else True),
        max_parallel=args.max_parallel if args.max_parallel is not None else (stary.max_parallel if stary else 0),
        heartbeat_seconds=args.heartbeat or (stary.heartbeat_seconds if stary else agent_config.DEFAULT_HEARTBEAT),
    )
    if not cfg.hub_url:
        raise SystemExit("chyba --hub-url")
    cesta = agent_config.save(cfg)
    print(f"agent {cfg.name!r}: hub {cfg.hub_url}, prijima={cfg.accept}, posiela={cfg.send}, "
          f"slotov {cfg.slots()}  -> {cesta}")
    return 0


def _cfg_or_die() -> agent_config.AgentConfig:
    cfg = agent_config.load()
    if cfg is None:
        raise SystemExit("agent nie je nastaveny: python -m tester.hub setup --name … --hub-url … --token …")
    return cfg


def cmd_agent(args: argparse.Namespace) -> int:
    """Headless agent: vlastný runner s toľkými workermi, koľko je slotov, a slučka heartbeatu."""
    import time

    from .. import data_archive, timeframes
    from ..webapp.runner import BacktestRunner
    from ..webapp.store import RunStore
    from .agent import HubAgent

    cfg = _cfg_or_die()
    if data_archive.missing():
        print("Skladam data z data_archive/ ...", flush=True)
        data_archive.main(["merge"])
    if timeframes.missing():
        print("Skladam chybajuce timeframy z 1m ...", flush=True)
        timeframes.ensure()

    import os

    store = RunStore()
    agent = HubAgent(cfg, None, store)
    agent.restart_on_pull = True
    runner = BacktestRunner(store, workers=agent.slots)
    agent.runner = runner
    runner.start()
    agent.start()
    print(f"agent {cfg.name!r} -> {cfg.hub_url}: prijima={cfg.accept}, posiela={cfg.send}, "
          f"jadier {agent.cores}, slotov {agent.slots}, kod {agent.version or '?'}", flush=True)
    try:
        while True:
            for _ in range(30):
                time.sleep(1)
                if agent.needs_restart:
                    break
            if agent.needs_restart:
                # Po git pulle je kód v tomto procese starý; nový proces si pridelený
                # výpočet vezme (hub ho po `bye` podrží).
                print(f"kod sa zmenil (git pull) -> restart agenta na {agent.version}", flush=True)
                agent.stop()
                agent.bye()
                os.execv(sys.executable, [sys.executable, "-m", "tester.hub", "agent"])
            st = agent.public()
            caka = (f"  caka na hub {st['pending_upload']}" if st.get("pending_upload") else "")
            tahanie = f"  tiahnem kod {st['updating']}" if st.get("updating") else ""
            nedorucene = (f"  NEODOVZDANE {len(st['undelivered'])}" if st.get("undelivered") else "")
            print(f"  … {'ok' if st['registered'] else 'bez spojenia'}"
                  f"{' (' + st['last_error'] + ')' if st['last_error'] else ''}"
                  f"  pocita {len(st['computing'])}{caka}{nedorucene}{tahanie}"
                  f"  kod {st['version'] or '?'}", flush=True)
    except KeyboardInterrupt:
        agent.stop()
        return 0


def _client(cfg: agent_config.AgentConfig):
    from .client import HubClient, HubHttp

    return HubClient(HubHttp(cfg.hub_url, cfg.token), cfg.name)


def cmd_status(args: argparse.Namespace) -> int:
    cfg = _cfg_or_die()
    client = _client(cfg)
    st = client.status()
    print(f"hub {cfg.hub_url}: agentov online {st['online']}, vo fronte {st['queued']}, "
          f"pocita sa {st['running']}")
    print(f"\n{'agent':<18}{'stav':<12}{'kod':<9}{'jadra':>6}{'sloty':>6}{'obsad.':>7}  prijima  posiela  volny(1)  volny(all)")
    for a in st["agents"]:
        stav = "tiahne kod" if a.get("updating") else ("online" if a["online"] else "offline")
        print(f"{a['name']:<18}{stav:<12}{str(a.get('version') or '-'):<9}"
              f"{a['cores']:>6}{a['slots']:>6}"
              f"{a['used']:>7}  {'ano' if a['accept'] else 'nie':<8} {'ano' if a['send'] else 'nie':<8} "
              f"{_fmt_eta(a['eta_free_1']):>8}  {_fmt_eta(a['eta_free_all']):>10}")
    verzie = {a.get("version") for a in st["agents"] if a.get("online")}
    if len(verzie) > 1:
        print("\nagenti online stoja na roznom kode - vypocet nesie commit zadavatela a agent "
              "si ho pred behom pullne")
    for a in st["agents"]:
        if a.get("online") and a.get("needs_restart"):
            print(f"POZOR: agent {a['name']} si pullol novy kod a caka na restart (webapp)")
    if st["jobs"]:
        print(f"\n{'vypocet':<14}{'druh':<10}{'stav':<11}{'agent':<16}{'zadal':<14}{'kod':<9}{'postup':>7}{'zostava':>9}  co")
        for j in st["jobs"]:
            s = j.get("summary") or {}
            postup = f"{100 * j['progress']:.0f} %" if j.get("progress") is not None else "-"
            if j.get("eta_seconds") is not None:
                zostava = _fmt_eta(j["eta_seconds"])
            else:
                zostava = "~" + _fmt_eta(j["estimate_seconds"]) if j.get("estimate_seconds") else "-"
            print(f"{j['id']:<14}{j['kind']:<10}{j['status']:<11}{str(j.get('agent') or '-'):<16}"
                  f"{str(j.get('submitter') or '-'):<14}{str(j.get('version') or '-'):<9}"
                  f"{postup:>7}{zostava:>9}  "
                  f"{s.get('pair')} {s.get('timeframe')} {s.get('timerange')}")
    return 0


def cmd_jobs(args: argparse.Namespace) -> int:
    cfg = _cfg_or_die()
    client = _client(cfg)
    for j in client.jobs(live=not args.all, mine=args.mine)[:args.limit]:
        s = j.get("summary") or {}
        print(f"{j['id']:<14}{j['kind']:<10}{j['status']:<11}{str(j.get('agent') or '-'):<16}"
              f"{str(j.get('submitter') or '-'):<14}{s.get('pair')} {s.get('timerange')}"
              f"{'  ' + j['error'] if j.get('error') else ''}")
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    """Zapnúť/vypnúť prijímanie na agentovi cez hub (agent si to prevezme v heartbeate)."""
    cfg = _cfg_or_die()
    hodnota = args.value.lower() in ("on", "true", "1", "ano", "yes")
    a = _client(cfg).set_accept(args.agent, hodnota)
    print(f"{a['name']}: prijima teraz {'ano' if a['accept'] else 'nie'}, "
          f"po heartbeate {'ano' if hodnota else 'nie'}")
    return 0


def _local_state():
    from .server import HubState

    return HubState()


def cmd_token(args: argparse.Namespace) -> int:
    """Tokeny agentov: `add` vydá (vypíše ho raz — potom je v tokens.json len hash-like hint),
    `rm` odoberie, `list` vypíše mená. Správcovská vec: cez API s hlavným tokenom, alebo
    `--local` priamo na stroji hubu."""
    if args.local:
        st = _local_state()
        if args.action == "add":
            print(st.add_token(args.name, by="local"))
        elif args.action == "rm":
            print("odobrany" if st.remove_token(args.name, by="local") else f"{args.name}: token nema")
        else:
            for t in st.token_names():
                print(f"{t['name']:<20}{t['token_hint']:<8}{'registrovany' if t['registered'] else ''}")
        return 0
    client = _client(_cfg_or_die())
    if args.action == "add":
        print(client.add_token(args.name))
    elif args.action == "rm":
        client.remove_token(args.name)
        print("odobrany")
    else:
        for t in client.tokens():
            print(f"{t['name']:<20}{t['token_hint']:<8}{'registrovany' if t['registered'] else ''}")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    """Vyhodiť agenta z hubu: premenovaný stroj, zrušený agent, preklep v mene."""
    if args.local:
        st = _local_state()
        try:
            r = st.forget(args.agent, force=args.force, with_token=args.with_token, by="local")
        except KeyError:
            raise SystemExit(f"agent {args.agent!r} na hube nie je")
        except ValueError as exc:
            raise SystemExit(str(exc))
    else:
        from .client import HubError

        try:
            r = _client(_cfg_or_die()).forget_agent(args.agent, force=args.force,
                                                    with_token=args.with_token)
        except HubError as exc:
            raise SystemExit(str(exc))
    print(f"{r['name']}: odstraneny z hubu"
          + (f", vypocty spat do fronty alebo zlyhali: {', '.join(r['jobs'])}" if r["jobs"] else "")
          + (", token odobrany" if r.get("token_removed")
             else (f" (token mu ostal: python -m tester.hub token rm {r['name']})" if r.get("token") else "")))
    return 0


def cmd_sparse(args: argparse.Namespace) -> int:
    """Chudý klon: čo sa má z repozitára ťahať a čo nie (archív, cudzia história behov)."""
    from . import sparse

    if args.off:
        r = sparse.off()
        print("sparse-checkout vypnuty - dalsi pull dotiahne cely strom"
              if r["ok"] else f"nepodarilo sa: {r['output']}")
        return 0 if r["ok"] else 1
    if args.data is None and args.no_data is False and args.history is None:
        st = sparse.show()
        if not st["on"]:
            print("klon je plny (bez sparse-checkoutu). Skus:\n"
                  "  python -m tester.hub sparse --no-history         # bez cudzich behov\n"
                  "  python -m tester.hub sparse --data binance       # archiv len z binance\n"
                  "  python -m tester.hub sparse --no-data            # bez archivu")
            return 0
        print(f"sparse-checkout je zapnuty, obsah mimo neho sa "
              f"{'NEstahuje (' + st['filter'] + ')' if st['filter'] else 'stahuje'}:")
        for pravidlo in st["rules"]:
            print(f"  {pravidlo}")
        return 0
    data = None if args.data is None and not args.no_data else [
        z for z in (args.data or "").split(",") if z.strip()]
    history = True if args.history is None else args.history
    rules = sparse.build_rules(data, history=history)
    if not history:
        print("POZOR: tester/runs a archiv behov zmiznu z pracovneho stromu (v gite ostavaju;\n"
              "       spat sa daju `python -m tester.hub sparse --off`). Na stroji, ktory je aj\n"
              "       tester, to nerob.")
    r = sparse.apply(rules)
    for pravidlo in rules:
        print(f"  {pravidlo}")
    print("hotovo - dalsi pull uz vyradene subory nestahuje" if r["ok"]
          else f"nepodarilo sa: {r['output']}")
    return 0 if r["ok"] else 1


def cmd_events(args: argparse.Namespace) -> int:
    """Log udalostí hubu: kto sa prihlásil, kto čo zadal, komu to išlo, ako skončilo."""
    if args.local:
        udalosti = _local_state().events(limit=args.limit, job=args.job, agent=args.agent, event=args.event)
    else:
        udalosti = _client(_cfg_or_die()).events(limit=args.limit, job=args.job, agent=args.agent,
                                                 event=args.event)
    for e in reversed(udalosti):
        zvysok = {k: v for k, v in e.items() if k not in ("ts", "event")}
        print(f"{e.get('ts', ''):<26}{e.get('event', ''):<16}"
              + "  ".join(f"{k}={v}" for k, v in zvysok.items()))
    if not udalosti:
        print("ziadne udalosti")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    cfg = _cfg_or_die()
    j = _client(cfg).cancel(args.job_id)
    print(f"{j['id']}: {j['status']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="python -m tester.hub", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("serve", help="spusti hub")
    p.add_argument("--host", default=getenv("HUB_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(getenv("HUB_PORT", str(DEFAULT_PORT))))
    p.add_argument("--token", help="zdieľaný token (inak TRADEBOT_HUB_TOKEN); na verejnej adrese povinný")
    p.add_argument("--heartbeat", type=int,
                   default=int(getenv("HUB_HEARTBEAT", str(agent_config.DEFAULT_HEARTBEAT))),
                   help="interval heartbeatu agentov v sekundách (default 10, alebo TRADEBOT_HUB_HEARTBEAT)")
    p.add_argument("--update", type=float, default=None, metavar="MIN",
                   help="samoaktualizácia: každých MIN minút fetch origin a reštart po zmene "
                        "kódu (0 = vypnuté; bez prepínača platí TRADEBOT_HUB_UPDATE)")
    p.add_argument("--update-max-wait", dest="update_max_wait", type=float, default=None,
                   metavar="MIN", help="ako dlho čakať na dobehnutie výpočtov pred reštartom "
                                       "(0 = koľko treba)")
    p.add_argument("--branch", default="main", help="vetva pre samoaktualizáciu (default main)")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("token", help="tokeny agentov: add | rm | list (správca hubu)")
    p.add_argument("action", choices=("add", "rm", "list"))
    p.add_argument("name", nargs="?", help="meno agenta (pre add a rm)")
    p.add_argument("--local", action="store_true", help="priamo v stave hubu na tomto stroji")
    p.set_defaults(func=cmd_token)

    p = sub.add_parser("events", help="log udalostí hubu")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--job", help="len udalosti tohto výpočtu")
    p.add_argument("--agent", help="len udalosti tohto agenta (ako agent, zadávateľ alebo pôvodca)")
    p.add_argument("--event", help="len tento druh udalosti (job_finished, agent_offline, …)")
    p.add_argument("--local", action="store_true", help="priamo zo stavu hubu na tomto stroji")
    p.set_defaults(func=cmd_events)

    p = sub.add_parser("setup", help="zapíš tester/agent.json (meno, hub, token, čo prijíma a posiela)")
    p.add_argument("--name", help="statické, jednoznačné meno agenta (default hostname)")
    p.add_argument("--hub-url", dest="hub_url", help="adresa hubu, napr. https://hub.example.com:8790")
    p.add_argument("--token", help="token hubu")
    p.add_argument("--accept", dest="accept", action="store_true", default=None, help="prijímať výpočty")
    p.add_argument("--no-accept", dest="accept", action="store_false", help="neprijímať výpočty")
    p.add_argument("--send", dest="send", action="store_true", default=None, help="smie posielať výpočty")
    p.add_argument("--no-send", dest="send", action="store_false", help="nesmie posielať výpočty")
    p.add_argument("--max-parallel", dest="max_parallel", type=int, help="strop behov naraz (0 = podľa jadier)")
    p.add_argument("--heartbeat", type=int, help="interval heartbeatu v sekundách")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("agent", help="headless agent: počíta pre hub bez webapp")
    p.set_defaults(func=cmd_agent)

    p = sub.add_parser("status", help="agenti, fronta a kapacita hubu")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("jobs", help="výpočty na hube (živé; --all aj hotové)")
    p.add_argument("--all", action="store_true")
    p.add_argument("--mine", action="store_true", help="len tie, ktoré zadal tento agent")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_jobs)

    p = sub.add_parser("sparse", help="chudý klon: neťahať archív a cudziu históriu behov")
    p.add_argument("--data", help="ktoré zdroje archívu ťahať (binance,dukascopy,…); "
                                  "bez prepínača sa nemení")
    p.add_argument("--no-data", dest="no_data", action="store_true",
                   help="neťahať `data_archive` vôbec (sklad `data/` na disku ostáva)")
    p.add_argument("--history", dest="history", action="store_true", default=None,
                   help="ťahať aj cudziu históriu behov (default, keď sa nepovie inak)")
    p.add_argument("--no-history", dest="history", action="store_false",
                   help="neťahať tester/runs, archive, analytics, sweeps ani projekty")
    p.add_argument("--off", action="store_true", help="späť celý strom")
    p.set_defaults(func=cmd_sparse)

    p = sub.add_parser("forget", help="vyhodiť agenta z hubu (premenovaný stroj, zrušený agent)")
    p.add_argument("agent", help="meno agenta, ako ho hub ukazuje")
    p.add_argument("--force", action="store_true", help="aj keď je online (prihlási sa späť, kým beží)")
    p.add_argument("--with-token", dest="with_token", action="store_true",
                   help="odobrať mu aj token (pri premenovaní ho starý názov už nepotrebuje)")
    p.add_argument("--local", action="store_true", help="priamo v stave hubu na tomto stroji")
    p.set_defaults(func=cmd_forget)

    p = sub.add_parser("accept", help="zapnúť/vypnúť prijímanie výpočtov na agentovi (bez reštartu)")
    p.add_argument("agent", help="meno agenta")
    p.add_argument("value", help="on | off")
    p.set_defaults(func=cmd_accept)

    p = sub.add_parser("cancel", help="zrušiť výpočet (hub to povie počítajúcemu aj zadávajúcemu agentovi)")
    p.add_argument("job_id")
    p.set_defaults(func=cmd_cancel)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
