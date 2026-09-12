"""`python -m tester.hub …` — hub, headless agent, nastavenie a stav.

    python -m tester.hub serve --host 0.0.0.0 --port 8790         # hub (TRADEBOT_HUB_TOKEN=…)
    python -m tester.hub setup --name srv-01 --hub-url https://hub:8790 --token … --accept --send
    python -m tester.hub agent                                    # headless agent tohto klonu
    python -m tester.hub status                                   # agenti, fronta, kapacita
    python -m tester.hub jobs [--all]                             # výpočty na hube
    python -m tester.hub cancel <job_id>                          # zrušiť výpočet

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
    print(f"TradeBot hub: http://{args.host}:{args.port}  (stav v {state.root})", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


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
            print(f"  … {'ok' if st['registered'] else 'bez spojenia'}"
                  f"{' (' + st['last_error'] + ')' if st['last_error'] else ''}"
                  f"  pocita {len(st['computing'])}  kod {st['version'] or '?'}", flush=True)
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
    print(f"\n{'agent':<18}{'stav':<9}{'kod':<9}{'jadra':>6}{'sloty':>6}{'obsad.':>7}  prijima  posiela  volny(1)  volny(all)")
    for a in st["agents"]:
        print(f"{a['name']:<18}{'online' if a['online'] else 'offline':<9}{str(a.get('version') or '-'):<9}"
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
    p.add_argument("--heartbeat", type=int, default=agent_config.DEFAULT_HEARTBEAT,
                   help="interval heartbeatu agentov v sekundách (default 10)")
    p.set_defaults(func=cmd_serve)

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
