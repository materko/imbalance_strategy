"""`python -m tester.webapp` — spustí server. Pred štartom zloží dáta z archívu, ak chýbajú."""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import sys


#: Súbory, ktorých zmena si vyžaduje reštart (kód a jeho statické súbory), a čo sa nepočíta —
#: história behov, profily a archív sa menia pri každom Pushi a reštart nepotrebujú.
_CODE_EXT = (".py", ".js", ".html", ".css", ".json")
_NOT_CODE = ("tester/runs/", "tester/profiles/", "tester/archive/", "data_archive/", "docs/")


def code_signature() -> str | None:
    """Odtlačok kódu v HEAD (bez histórie behov a profilov); `None`, keď git nie je k dispozícii."""
    import hashlib
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    try:
        p = subprocess.run(["git", "ls-tree", "-r", "HEAD"], cwd=repo, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    h = hashlib.sha1()
    for line in p.stdout.splitlines():
        path = line.split("\t", 1)[-1]
        if path.endswith(_CODE_EXT) and not path.startswith(_NOT_CODE):
            h.update(line.encode())
    return h.hexdigest()


def _watch_code(interval: float = 20.0) -> None:
    import json
    import time
    import urllib.request

    start = code_signature()
    if start is None:
        return
    port = int(getenv("WEB_PORT", "8765"))
    while True:
        time.sleep(interval)
        if code_signature() in (start, None):
            continue
        try:   # beh, ktorý práve počíta, sa nepreruší — reštart počká
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/queue", timeout=10) as r:
                if json.load(r):
                    continue
        except Exception:  # noqa: BLE001 — server ešte nebeží / neodpovedá: skús neskôr
            continue
        print("Kód v gite sa zmenil (pull) — reštartujem webapp, aby načítala nové stratégie ...", flush=True)
        os.execv(sys.executable, [sys.executable, "-m", "tester.webapp"])


def main() -> int:
    from .. import data_archive, quotemanager, timeframes

    # Pozerá sa na KAZDY subor z archivu, nie len na to, ci je v data/ nieco: s jednym
    # rozbalenym zdrojom by webapp nabehla s poloprazdnou ponukou parov a backtest by
    # spadol az na "No history for ... found".
    chyba = data_archive.missing()
    if chyba:
        print(f"Chyba {len(chyba)} pracovnych suborov - skladam ich z data_archive/ ...", flush=True)
        data_archive.main(["merge"])

    # Vyssie timeframy si Freqtrade z 1m nedopocita, chce subor na disku. Zoznam je
    # v tester/timeframes.json; doplni sa len to, co chyba (prvy start po pridani TF
    # preto trva dlhsie).
    chybajuce_tf = timeframes.missing()
    if chybajuce_tf:
        print(f"Chyba {len(chybajuce_tf)} timeframov - skladam ich z 1m ...", flush=True)
        timeframes.ensure()

    # ASCII pre QuoteManager (MultiCharts) - predvolene len symboly, ktore v nom naozaj
    # bezia; `TRADEBOT_QUOTEMANAGER=all` aj krypto, `=off` nic.
    if quotemanager.missing(quotemanager.scope()):
        print("Vyrabam export pre QuoteManager ...", flush=True)
        quotemanager.ensure()

    import threading

    import uvicorn

    # Index behov a ponuka párov sa dorovnajú na pozadí už teraz, nie až pri prvom dopyte
    # zo stránky. Po prvom štarte je index hotový, takže je to lacné; prvý raz (alebo po
    # zmazaní indexu) sa tu prečíta celá história. uvicorn ten istý modul (a store) použije
    # znova.
    from .app import app as _app
    from .runner import available_pairs

    def _zahrej() -> None:
        try:
            _app.state.store.index.sync(force=True)
            available_pairs()
        except Exception:  # noqa: BLE001 - zahriatie je len úspora, nie podmienka behu
            pass

    threading.Thread(target=_zahrej, name="warm-cache", daemon=True).start()

    # Agent hubu (tester.hub): keď má klon tester/agent.json, webapp sa hlási hubu,
    # počíta, čo jej pridelí (toľko behov naraz, koľko má slotov), a vyzdvihuje
    # výsledky toho, čo odtiaľto odišlo cez `cli run --remote`.
    from ..hub import config as hub_config

    hub_cfg = hub_config.load()
    if hub_cfg is not None:
        hub_agent = _app.state.start_hub_agent(hub_cfg)
        print(f"Hub agent {hub_cfg.name!r} -> {hub_cfg.hub_url}: prijima={hub_cfg.accept}, "
              f"posiela={hub_cfg.send}, slotov {hub_agent.slots}", flush=True)
    else:
        print("Hub: nenastaveny - karta Hub vo webapp (alebo python -m tester.hub setup)", flush=True)

    # Zrkadlo live telemetrie (docs/LIVE.md): každých 5 s stiahne nové udalosti z hubu
    # (ak je nastavený) a z lokálneho spoolu platforiem (ak tu nejaký je) — karta Live.
    _app.state.start_live_mirror()

    # Pull (tlačidlo Pull, Push aj `cli push`) stiahne nový kód, ale bežiaci proces ho nenačíta —
    # nová stratégia by vo webapp chýbala až do ručného reštartu. Keď sa kód v gite zmení,
    # webapp sa reštartuje sama, hneď ako nebeží žiadny beh. `TRADEBOT_AUTO_RESTART=0` to vypne.
    if getenv("AUTO_RESTART", "1") != "0":
        threading.Thread(target=_watch_code, name="code-watch", daemon=True).start()

    host = getenv("WEB_HOST", "127.0.0.1")
    port = int(getenv("WEB_PORT", "8765"))
    print(f"TradeBot Tester: http://{host}:{port}", flush=True)
    uvicorn.run("tester.webapp.app:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
