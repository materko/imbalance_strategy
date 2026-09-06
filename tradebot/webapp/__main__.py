"""`python -m tradebot.webapp` — spustí server. Pred štartom zloží dáta z archívu, ak chýbajú."""

from __future__ import annotations

import os

from tradebot.core.env import getenv
import sys


def main() -> int:
    from .runner import DATA_DIR

    if not any(DATA_DIR.glob("*-3m-futures.feather")):
        print("Pracovne data chybaju - skladam ich z data_archive/ ...", flush=True)
        from ..tools import data_archive

        data_archive.main(["merge"])

    import uvicorn

    host = getenv("WEB_HOST", "127.0.0.1")
    port = int(getenv("WEB_PORT", "8765"))
    print(f"IBS webapp: http://{host}:{port}", flush=True)
    uvicorn.run("tradebot.webapp.app:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
