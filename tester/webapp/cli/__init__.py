"""Príkazový riadok nad webapp — pre Claude Code a skripty, výsledky idú do histórie.

    python -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \\
        --set rrRatio=4 --set minSlDistance=0.25@pct --timerange 20250904-20260904 \\
        --note "RR 4 namiesto 5"
    python -m tester.webapp.cli list "rrRatio>=4 pnl>0"
    python -m tester.webapp.cli show 20260905-160921-0310ba
    python -m tester.webapp.cli status          # beží webapp? čo je vo fronte? stav gitu
    python -m tester.webapp.cli pull | push     # história behov z/na GitHub
    python -m tester.webapp.cli replay <id>     # bod mriežky/matice ako obyčajný beh
    python -m tester.webapp.cli chart <id>      # prepočítaj kresby behu do cache grafov
    python -m tester.webapp.cli prune           # čo odpratať z histórie (bez --apply nič nemaže)

`run` ide cez REST API bežiacej webapp (ak beží — beh sa objaví vo fronte aj
testerovi v prehliadači); keď webapp nebeží, spustí backtest priamo a uloží ho
do toho istého adresára `runs/`, takže história je rovnaká. Backtest cez holý
Freqtrade CLI sa do histórie NEdostane — preto tento nástroj.

`--set` hodnoty: `true`/`false`, čísla, text, JSON (`'{"value":0.2,"unit":"pct"}'`)
alebo skratka `hodnota@jednotka` pre veľkostné polia (`minSlDistance=0.2@pct`).
"""

from __future__ import annotations

import sys

from .common import DEFAULT_URL, api, fmt_summary, parse_set, server_alive  # noqa: F401
from .parser import build_parser
from .remote import _REMOTE_BATCH, _remote_prefetch, _webapp_hub_ready  # noqa: F401
from .run import _execute, _fee_for, _prepare  # noqa: F401


def main(argv: list[str] | None = None) -> int:
    # Windows konzola je cp1250 a log Freqtradu má znaky, ktoré v nej nie sú —
    # bez tohto padne celý príkaz na UnicodeEncodeError uprostred behu.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser(__doc__).parse_args(argv)
    return args.func(args)
