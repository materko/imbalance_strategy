"""Krok 8 v rannej úlohe: iný trh (NAS100 pre Nasdaq, XAU/USD pre zlato) pre každý profil PREŠIEL_SMERNICAMI_*_1,
ktorý ešte nemá výsledok alebo sa od posledného merania zmenil (používateľ 22. 10. 2026: kroky 7–8 majú ísť samy)."""
import glob, json, subprocess, sys
from pathlib import Path
ROOT = Path("/Users/martin/IBS"); OUT = ROOT / ".nightsearch" / "nas100" / "vysledky.json"
done = json.loads(OUT.read_text()) if OUT.exists() else {}
mt = OUT.stat().st_mtime if OUT.exists() else 0
keys = []
for f in sorted(glob.glob(str(ROOT / "tester/profiles/PRESIEL_SMERNICAMI_*_1.json"))):
    k = json.load(open(f))["_strategy"]
    if k not in done or Path(f).stat().st_mtime > mt:
        keys.append(k)
keys = sorted(set(keys))
print("krok 8 chýba:", keys or "nič", flush=True)
if keys:
    subprocess.run([sys.executable, str(ROOT / ".nightsearch" / "glnas100.py"), *keys], cwd=ROOT / ".nightsearch")
