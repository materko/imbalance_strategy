"""Triedenie pre záložku SMERNICE vo webapp (používateľ 11. 10. 2026).

Stratégia, ktorá má aspoň jeden profil PREŠIEL SMERNICAMI, patrí do záložky SMERNICE (webapp ju tam dá sama
podľa profilov). Pri takej stratégii má vo webapp ostať LEN to, čo prešlo smernicou:

* profily v tester/profiles: ostatné sa presunú do .nightsearch/dash/vyradene/profily/<stratégia>/ (nemažú sa),
* behy v histórii: ostatné sa presunú do archívu (cli archive, vratné cez --restore).
  Ostávajú behy s poznámkou „PREŠIEL SMERNICAMI …“ alebo „Smernica <id> (prešiel …)“.

Profily repozitára (tradebot/strategies/<kľúč>/configs) sa nemenia — stratégia ich potrebuje ako východisko;
webapp ich pri stratégii zo SMERNICE vo výbere profilov neukáže.

python glsmernice.py [--apply]   (bez --apply len vypíše, čo by spravil)
"""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path("/Users/martin/IBS")
sys.path.insert(0, str(ROOT))
PROF = ROOT / "tester" / "profiles"
OUT = ROOT / ".nightsearch" / "dash" / "vyradene" / "profily"
PREFIX = "PRESIEL_SMERNICAMI_"


def passed_keys() -> set[str]:
    keys = set()
    for f in PROF.glob(PREFIX + "*.json"):
        try:
            keys.add(json.loads(f.read_text()).get("_strategy"))
        except Exception:
            pass
    return {k for k in keys if k}


def keep_run(note: str) -> bool:
    n = note or ""
    return (n.startswith("PREŠIEL SMERNICAMI") or (n.startswith("Smernica ") and "(prešiel" in n)
            or "Smernica krok" in n)          # analytika (checkup) a ďalšie kroky smernice ostávajú


def main(apply: bool) -> None:
    from tester.webapp.index import RunIndex
    from tradebot.core.paths import RUNS_DIR
    keys = passed_keys()
    print("v SMERNICE:", sorted(keys))
    moved = 0
    for f in sorted(PROF.glob("*.json")):
        if f.name.startswith(PREFIX):
            continue
        try:
            k = json.loads(f.read_text()).get("_strategy")
        except Exception:
            continue
        if k in keys:
            moved += 1
            if apply:
                (OUT / k).mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(OUT / k / f.name))
    print("profilov mimo smernice", "presunutých" if apply else "na presun", moved)
    idx = RunIndex(RUNS_DIR)
    idx.sync()
    drop = []
    for k in sorted(keys):
        sql, vals, _ = idx.where([("strategy", "=", k)])
        for r in idx.records(sql, vals):
            if not keep_run(r.get("note") or ""):
                drop.append(r["id"])
    print("behov mimo smernice", "na archiváciu" if not apply else "archivujem", len(drop))
    if apply:
        for rid in drop:
            subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "archive", f"id={rid}", "--apply"],
                           cwd=ROOT, capture_output=True, text=True)


if __name__ == "__main__":
    main("--apply" in sys.argv)
