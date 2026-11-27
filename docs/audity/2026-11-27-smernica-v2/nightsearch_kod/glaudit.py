"""Audit stratégií na stránke výsledkov (bod 5 týždňa 31. 10.–8. 11. 2026) — triedy A / B / C a najlepší trh.

gldash.compute → data["audit"] (karta Audit na stránke); `python glaudit.py` zapíše aj Markdown z dash/dashboard_data.json."""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path("/Users/martin/IBS/.nightsearch")
MK = {"NASDAQ": "Nasdaq (MNQ)", "SP 500": "S&P 500 (ES)", "GOLD": "Zlato (MGC)", "EURUSD": "EUR/USD (6E)"}
FAMILY = {"wpr": "Williams %R", "orb15": "ORB 15/5", "ivb": "IVB", "sigma": "Sigma Breakout", "lliq": "London IFVG",
          "nqprec": "NQ Precision", "flashorb": "Flash ORB", "tmr": "T-Mean Reversion", "ibsentry": "IBS Entry Zone",
          "nyva": "NY VA Breakout"}


def fam(key: str) -> str | None:
    for f in sorted(FAMILY, key=len, reverse=True):
        if key.startswith(f) and key[len(f):] in ("", "es", "mgc"):
            return f
    return None


SORTINO_MIN = 2.0          # ročný Sortino z denných výsledkov (pracovné dni 10/2021–9/2026), hranica „dobrý systém“


def sortino(trades: list) -> float | None:
    """Ročný Sortino najlepšieho nastavenia: denný zisk na každý pracovný deň obdobia (bez obchodu = 0),
    priemer / odchýlka strát (len záporné dni, voči nule) × √252."""
    import numpy as np
    import pandas as pd
    if not trades:
        return None
    days = pd.bdate_range("2021-10-01", "2026-09-04").strftime("%Y-%m-%d")
    dd = {}
    for t in trades:
        dd[t["close"][:10]] = dd.get(t["close"][:10], 0.0) + t["pnl"]
    p = np.array([dd.get(x, 0.0) for x in days])
    down = np.sqrt((np.minimum(p, 0) ** 2).mean())
    return round(float(p.mean() / down * np.sqrt(252)), 2) if down > 0 else None


def csharp_keys() -> set:
    """Kľúče stratégií, ktoré majú C# jadro (vlastné alebo port `<kľúč>net` / `<kľúč>neteod`)."""
    sys.path.insert(0, "/Users/martin/IBS")
    from tradebot.strategies import STRATEGIES
    cs = {k for k, s in STRATEGIES.items() if s.csharp_dir}
    return cs | {k for k in STRATEGIES if k + "net" in cs or k + "neteod" in cs}


def compute(d: dict, DATE: str) -> dict:
    """Audit z dát stránky (dashboard_data.json)."""
    CS = csharp_keys()
    LIVE = {i.get("strategy") for i in (d.get("live") or {}).get("instances", [])} | \
           {i.get("engine") for i in (d.get("live") or {}).get("instances", [])}
    rows = []
    for s in d["strategies"]:
        if s.get("no_audit"):         # nová stratégia mimo smernice (napr. MTK RANGE) — audit ju nehodnotí
            continue
        b = s["settings"][0]
        passed = [x for x in s["settings"] if x["status"].startswith("prešiel")]
        n = s.get("nas100") or {}
        r = s.get("robust") or {}
        if s.get("exception"):          # SPRÁVY: krok 8 a 9 na stránke sú zo starého profilu 3.0 (MNQ), pre PROFIL 1–4 nebežali
            n, r = {"passed": True, "market": "nebežal"}, {}
        v = r.get("verdict") or {}
        ys = (b.get("is") or {}).get("years") or {}
        oos = (b.get("oos") or {}).get("pf")
        worst = min(ys.values()) if ys else None
        why = []
        if passed:
            if not n.get("passed"):
                why.append(f"iný trh ({n.get('market', '?')}) neprešiel")
            if v and not v.get("fee2"):
                why.append("2× poplatok nedrží")
            if v and not v.get("delay"):
                why.append("vstup o sviečku neskôr nedrží")
            if (oos or 0) < 1.4:
                why.append(f"odložený rok PF {oos:.2f} < 1,4")
            if worst is not None and worst < 1.2:
                why.append(f"najhorší rok ladenia PF {worst:.2f}")
            cls = "A" if not why else "B"
        else:
            cls = "C"
            why.append(b["status"])
        if s.get("exception"):
            why.append("výnimka 150 obch/rok (schválil používateľ)")
        rows.append(dict(key=s["key"], name=s["name"], market=s["market"], cls=cls, why=why, passed=len(passed),
                         settings=len(s["settings"]), is_pf=(b.get("is") or {}).get("pf"), worst=worst, oos=oos,
                         oos_trades=(b.get("oos") or {}).get("trades"), tpy=(b.get("is") or {}).get("trades_per_year"),
                         wr=(b.get("is") or {}).get("winrate"), dd=(b.get("is") or {}).get("maxdd"),
                         other=f"{n.get('market', '–')} PF {n.get('pf', '–')} ({n.get('years_pos', '–')}/5)" if n else "–",
                         live=s["key"] in LIVE or (s["key"] + "net") in LIVE, family=fam(s["key"]),
                         sortino=sortino(b.get("trades") or []), csharp=s["key"] in CS))
        rows[-1]["sortino_ok"] = bool(passed) and (rows[-1]["sortino"] or 0) >= SORTINO_MIN

    order = {"A": 0, "B": 1, "C": 2}
    rows.sort(key=lambda x: (order[x["cls"]], -(x["oos"] or 0)))

    # najlepší trh rodiny (rovnaká logika na viacerých trhoch): podľa triedy, potom PF odloženého roka
    best_market = {}
    by_fam = defaultdict(list)
    for x in rows:
        if x["family"]:
            by_fam[x["family"]].append(x)
    for f, xs in by_fam.items():
        xs = sorted(xs, key=lambda x: (order[x["cls"]], -(x["oos"] or 0)))
        best_market[f] = dict(name=FAMILY[f], best=xs[0]["market"], ranking=[(x["market"], x["cls"], x["oos"]) for x in xs])

    audit = dict(date=DATE, rows=rows, families=best_market, sortino_min=SORTINO_MIN,
                 rules={"A": "Funguje — prešla smernicou, iný trh, 2× poplatok aj oneskorený vstup držia, odložený rok PF ≥ 1,4, žiadny rok ladenia pod 1,2. Na forward test / live.",
                        "B": "Funguje s výhradou — prešla smernicou, ale jedna z podmienok A chýba (je vypísaná). Forward test, menšia veľkosť.",
                        "C": "Nefunguje (zatiaľ) — neprešla smernicou (odložený rok, plató alebo počet obchodov). Nie na live."})
    return audit


def write_webapp(audit: dict) -> None:
    """tester/audit.json pre webapp (paths.STRATEGY_AUDIT): pri kľúči stratégie trieda, Sortino a či má C# jadro."""
    sys.path.insert(0, "/Users/martin/IBS")
    from tradebot.core.paths import STRATEGY_AUDIT
    out = {"date": audit["date"], "sortino_min": audit["sortino_min"], "rules": audit["rules"],
           "strategies": {r["key"]: {k: r[k] for k in ("cls", "sortino", "sortino_ok", "csharp", "why", "name", "market")}
                          for r in audit["rows"]}}
    STRATEGY_AUDIT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def write_md(audit: dict, repo: bool = False) -> str:
    """Markdown auditu do iCloudu (TYZDEN-2026-11) a do repa (docs/audity)."""
    DATE, rows, best_market = audit["date"], audit["rows"], audit["families"]

    f2 = lambda v: "–" if v is None else f"{v:.2f}".replace(".", ",")  # noqa: E731
    L = [f"# Audit stratégií na stránke výsledkov — {DATE}", "",
         "Bod 5 týždenného zadania (31. 10.–8. 11. 2026): stratégie zo stránky TradeBot výsledky roztriedené podľa toho, "
         "či fungujú (kroky smernice 4–9) a na aký trh sa najlepšie hodia. Čísla sú najlepšie nastavenie stratégie, "
         "1 kontrakt, s poplatkom; ladenie 10/2021–9/2025, odložený rok 9/2025–9/2026.", ""]
    for c, title in (("A", "A — funguje (forward test / live)"), ("B", "B — funguje s výhradou"), ("C", "C — nefunguje (zatiaľ)")):
        L += [f"## {title}", "", audit["rules"][c], "",
              "| stratégia | trh | PF ladenie | najhorší rok | PF odložený rok | obch/rok | WR | max DD $ | iný trh (krok 8) | live | prečo nie A |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in [r for r in rows if r["cls"] == c]:
            L.append(f"| {x['name']} (`{x['key']}`) | {MK.get(x['market'], x['market'])} | {f2(x['is_pf'])} | {f2(x['worst'])} | "
                     f"{f2(x['oos'])} | {x['tpy'] or '–'} | {round(x['wr'] or 0)} % | {round(x['dd'] or 0):,} | {x['other']} | "
                     f"{'● beží' if x['live'] else ''} | {'; '.join(x['why']) if c != 'A' else '–'} |".replace(",", " ", 0))
        L.append("")
    L += ["## Podľa trhu", ""]
    for m in ("NASDAQ", "SP 500", "GOLD", "EURUSD"):
        xs = [x for x in rows if x["market"] == m]
        if not xs:
            continue
        L.append(f"- **{MK[m]}:** " + ", ".join(f"{x['name']} ({x['cls']})" for x in xs))
    L += ["", "## Rovnaká logika na viacerých trhoch — kde sa hodí najlepšie", "",
          "| stratégia | najlepší trh | poradie (trh · trieda · PF odloženého roka) |", "|---|---|---|"]
    for f, v in sorted(best_market.items(), key=lambda kv: kv[1]["name"]):
        L.append(f"| {v['name']} | {MK.get(v['best'], v['best'])} | " +
                 " · ".join(f"{MK.get(m, m)} {c} {f2(p)}" for m, c, p in v["ranking"]) + " |")
    L += ["", "## Poznámky", "",
          "- Deflated Sharpe (krok 9) neprejde žiadna stratégia — pri desiatkach tisíc skúšaných kombinácií je to očakávané; "
          "je to len informácia (smernica, 29. 10.), nie kritérium triedy.",
          "- Trieda C neznamená, že logika je zlá: T-Mean Reversion má z princípu ~25–40 obchodov za rok (hranica 150), "
          "ostatné C neprešli odloženým rokom alebo plató.",
          "- Pred live: forward test 4–8 týždňov (krok 10) aj pre triedu A.", ""]
    md = "\n".join(L)
    (Path("/Users/martin/Library/Mobile Documents/com~apple~CloudDocs/TYZDEN-2026-11") / f"AUDIT_{DATE}.md").write_text(md, encoding="utf-8")
    if repo:
        (Path("/Users/martin/IBS/docs/audity") / f"AUDIT_strategie_{DATE}.md").write_text(md, encoding="utf-8")
    return md


if __name__ == "__main__":
    a = compute(json.loads((ROOT / "dash/dashboard_data.json").read_text()), sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d"))
    write_webapp(a)
    print(write_md(a, repo=True))
