"""`python -m ibs.webapp` — spustí server. Pred štartom zloží dáta z archívu, ak chýbajú."""

from __future__ import annotations

import os
import sys


def main() -> int:
    from .runner import DATA_DIR

    if not any(DATA_DIR.glob("*-3m-futures.feather")):
        print("Pracovne data chybaju - skladam ich z data_archive/ ...", flush=True)
        from ..tools import data_archive

        data_archive.main(["merge"])

    import uvicorn

    host = os.environ.get("IBS_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("IBS_WEB_PORT", "8765"))
    print(f"IBS webapp: http://{host}:{port}", flush=True)
    uvicorn.run("ibs.webapp.app:app", host=host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
