"""Priebežné výsledky ladenia SPRÁV EUR/USD do iCloudu (SPRAVY-EUR/vyskum/LADENIE_<dátum>.md + PRECITAJ_MA odkaz)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

D = Path("/Users/martin/IBS/.nightsearch/spravyeur")
ST = D / "out" / "state.json"
IC = Path("/Users/martin/Library/Mobile Documents/com~apple~CloudDocs/SPRAVY-EUR")
W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
OOS = W[-1]


def pfs(e: dict) -> str:
    return " · ".join(f"{e[w]['pf']:.2f}" for w in W)


def row(name: str, e: dict) -> str:
    s, o = e["spolu"], e[OOS]
    return (f"| {name} | {pfs(e)} | **{e['is_min']:.2f}** | **{s['pf']:.2f}** | {s['trades']} | {s['wr']:.0f} % | "
            f"{s['pnl']:+,.0f} | {s.get('dd', 0):,.0f} | {o['trades']} · {o['wr']:.0f} % · {o['pf']:.2f} · {o['pnl']:+,.0f} |")


HEAD = ("| | PF po oknách (21/22 … 25/26) | najhoršie okno ladenia | PF spolu | obch | WR | zisk $ | max DD $ | "
        "posledný rok: obch · WR · PF · zisk |\n|---|---|---|---|---|---|---|---|---|")


def params(p: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in p.items())


def main() -> None:
    if not ST.exists():
        return
    st = json.loads(ST.read_text())
    done = st["done"]
    L = [f"# SPRÁVY — ladenie (Mac mini), stav {datetime.now():%d. %m. %Y %H:%M}", "",
         "Natívne C# jadro `spravyeurnet`, 6E 5m, riziko 500 $ na obchod, poplatok 1,755e-05. Kritérium **profit faktor najhoršieho okna** "
         "zo štyroch okien ladenia (2021-10 – 2025-09), víťaz podľa okolia (plató), 3 seedy; posledný rok 2025-09 – 2026-09 "
         f"je odložený (len overenie). Skúšok spolu: {st.get('trials', 0)}. Postup a skript: `.nightsearch/spravyeur/ladenie.py`.", ""]
    if "D" in done or "C" in done:
        fin = done.get("D") or done["C"]
        base = (done["C"]["steps"][0]["eval"])
        bp = json.loads(Path("/Users/martin/IBS/tradebot/strategies/spravyeurnet/configs/6e_databento_5m.json").read_text())
        L += ["## Celok — východisko vs. najlepší doteraz", "", HEAD, row("východisko", base), row("**najlepší**", fin["eval"]), "",
              "Zmeny oproti východisku: " + (params({k: v for k, v in fin["profile"].items()
                                              if not k.startswith("_") and v != bp.get(k)}) or "žiadne"), ""]
        if "C" in done:
            L += ["### Skladanie po krokoch (prijaté len to, čo nezhorší PF spolu ani najhoršie okno)", "", HEAD]
            for s in done["C"]["steps"][1:]:
                L.append(row(f"{s['krok']} — {'✓ prijaté' if s.get('prijaté') else '✗'}", s["eval"]))
            L.append("")
    if "E" in done:
        E = done["E"]
        L += ["## Overenie víťaza", "", "| | EUR/USD CFD PF po oknách | CFD PF spolu | 2× poplatok | o sviečku neskôr | DSR (skúšok) |",
              "|---|---|---|---|---|---|"]
        for n in ("3.0", "víťaz"):
            x, r = E["xau"][n], E["robust"][n]
            L.append(f"| {n} | {pfs(x)} | {x['spolu']['pf']:.2f} | {r['total']['pf_fee2']:.2f} ({r['total']['win_fee2']}/5) | "
                     f"{r['total']['pf_delay']:.2f} ({r['total']['win_delay']}/5) | {r['dsr'].get('dsr', 0):.3f} |")
        L.append("")
    a = {k: v for k, v in done.items() if v.get("stage") == "A"}
    if a:
        L += ["## Etapa A — pravidlá východiska samostatne (len tá správa)", "", HEAD]
        for k, d in a.items():
            if d.get("base"):
                L.append(row(f"{k} — východisko", d["base"]))
            if d.get("eval"):
                L.append(row(f"{k} — vyladené", d["eval"]))
                L.append(f"| | `{params(d['params'])}` | | | | | | | |")
        L.append("")
    b = {k: v for k, v in done.items() if v.get("stage") == "B"}
    if b:
        L += ["## Etapa B — nové pravidlá (správy, ktoré východisko neobchoduje, a drift pred správou)", "",
              "Prejde, keď najhoršie okno ladenia ≥ 1,0 a posledný rok ≥ 1,2 a ≥ 70 % najhoršieho okna ladenia. Pri etape A to isté s hranicou 1,0.", "", HEAD]
        for k, d in sorted(b.items(), key=lambda x: -(x[1].get("eval") or {}).get("is_min", 0)):
            if d.get("eval"):
                ok = d["eval"]["is_min"] >= 1.0 and d["eval"][OOS]["pf"] >= max(1.2, 0.7 * d["eval"]["is_min"])
                L.append(row(f"{k} {'✓' if ok else ''}", d["eval"]))
                L.append(f"| | `{params(d['params'])}` | | | | | | | |")
        L.append("")
    out = IC / "vyskum" / f"LADENIE_{datetime.now():%Y-%m-%d}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    (D / "out" / "LADENIE_posledne.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
