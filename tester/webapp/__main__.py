"""`python -m tester.webapp` — spustí server. Pred štartom zloží dáta z archívu, ak chýbajú."""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import sys


def main() -> int:
    from .. import data_archive, timeframes

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

    import uvicorn

    host = getenv("WEB_HOST", "127.0.0.1")
    port = int(getenv("WEB_PORT", "8765"))
    print(f"TradeBot Tester: http://{host}:{port}", flush=True)
    uvicorn.run("tester.webapp.app:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
