"""`python -m tester.webapp` — spustí server. Pred štartom zloží dáta z archívu, ak chýbajú."""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import sys


def main() -> int:
    from tradebot.core.paths import TESTER_DATA

    # sviečky sú v data/tester/<zdroj>/<trh>/; stačí, že tam nejaká je
    if not any(TESTER_DATA.rglob("*.feather")):
        print("Pracovne data chybaju - skladam ich z data_archive/tester/ ...", flush=True)
        from .. import data_archive

        data_archive.main(["merge"])

    import uvicorn

    host = getenv("WEB_HOST", "127.0.0.1")
    port = int(getenv("WEB_PORT", "8765"))
    print(f"TradeBot Tester: http://{host}:{port}", flush=True)
    uvicorn.run("tester.webapp.app:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
