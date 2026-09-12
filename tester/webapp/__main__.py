"""`python -m tester.webapp` — spustí server. Pred štartom zloží dáta z archívu, ak chýbajú."""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import sys


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

    # Cache záznamov behov a ponuky párov sa naplní na pozadí už teraz, nie až pri prvom
    # dopyte zo stránky: pri tisíckach behov trvá prvé čítanie sekundy a tester by ich
    # čakal pri každom štarte. uvicorn ten istý modul (a store) použije znova.
    from .app import app as _app
    from .runner import available_pairs

    def _zahrej() -> None:
        try:
            _app.state.store.all()
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
        from ..hub.agent import HubAgent

        hub_agent = HubAgent(hub_cfg, _app.state.runner, _app.state.store)
        if hub_cfg.accept:
            _app.state.runner.workers = hub_agent.slots
        hub_agent.start()
        _app.state.hub_agent = hub_agent
        print(f"Hub agent {hub_cfg.name!r} -> {hub_cfg.hub_url}: prijima={hub_cfg.accept}, "
              f"posiela={hub_cfg.send}, slotov {hub_agent.slots}", flush=True)

    host = getenv("WEB_HOST", "127.0.0.1")
    port = int(getenv("WEB_PORT", "8765"))
    print(f"TradeBot Tester: http://{host}:{port}", flush=True)
    uvicorn.run("tester.webapp.app:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
