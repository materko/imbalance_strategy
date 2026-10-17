"""`python -m tester.webapp.mc_worker <úloha.json>` — beh emulátora MultiCharts v samostatnom procese.

Emulátor je čistý Python: v procese webapp by každý beh držal GIL, takže pri viacerých
workeroch (agent hubu ich má toľko, koľko jadier) by sa behy striedali na jednom jadre
a webapp by neodpovedala ani na stránku, ani hubu na heartbeat. Preto ho `BacktestRunner`
púšťa ako podproces — tak ako Freqtrade: log ide na stdout (riadok po riadku, z neho sa
číta aj postup), výsledok `run_multicharts` sa zapíše ako pickle do súboru z úlohy a
zrušenie je zabitie procesu.

Úloha (JSON): `params`, `settings`, `profile`, `result` (kam pickle), `chart_out` (alebo null).
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("použitie: python -m tester.webapp.mc_worker <úloha.json>", file=sys.stderr)
        return 2
    task = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    from .results import run_multicharts

    out = run_multicharts(task["params"], task["settings"], Path(task["profile"]),
                          log=lambda s: print(s, flush=True),
                          chart_out=Path(task["chart_out"]) if task.get("chart_out") else None)
    tmp = Path(task["result"]).with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump(out, fh, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(task["result"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
