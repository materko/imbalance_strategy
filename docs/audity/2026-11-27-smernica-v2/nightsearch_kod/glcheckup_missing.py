"""Krok 7 smernice automaticky: analytika (glcheckup.sh) pre každý profil PREŠIEL SMERNICAMI č. 1,
ktorého parametre ešte nemajú checkup (nová stratégia alebo zmenené nastavenie č. 1). Volá ranná úloha."""
import glob
import json
import os
import subprocess

ROOT = "/Users/martin/IBS"
os.chdir(ROOT)


def params(path):
    return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}


for prof in sorted(glob.glob("tester/profiles/PRESIEL_SMERNICAMI_*_1.json")):
    key = json.load(open(prof))["_strategy"]
    cur = params(prof)
    done = [f for f in glob.glob(f".nightsearch/checkup/{key}_*.json") if params(f) == cur]
    doc = f"tradebot/strategies/{key}/docs/ANALYTIKA.md"
    # hotové len vtedy, keď checkup naozaj dobehol (ANALYTIKA.md je novšia než jeho profil) — 24. 10. 2026 webapp so
    # starým kódom beh odmietla, súbor profilu ostal a krok 7 sa už nikdy nespustil
    if done and os.path.exists(doc) and os.path.getmtime(doc) >= max(os.path.getmtime(f) for f in done):
        continue
    for f in done:
        os.remove(f)
    name = os.path.basename(prof)[:-5]
    print(f"analytika chýba: {key} ({name}) — spúšťam checkup", flush=True)
    subprocess.run(["sh", ".nightsearch/glcheckup.sh", key, name], check=False)
