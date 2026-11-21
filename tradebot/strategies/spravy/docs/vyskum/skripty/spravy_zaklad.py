"""SPRÁVY 3.0 (spravynet) — základná sada testov na natívnom C# emulátore, 5 okien + súhrn."""
import json, sys
sys.path.insert(0, "/Users/martin/IBS")
from tradebot.core import load_profile
from tradebot.core.types import INSTRUMENTS
from tester import engines
from tester.native import NativeRunner, emulation_of
from tradebot.adapters.multicharts.emulator import rows_from_trades
from tradebot.core.money import summary_money

W = ["20211001-20221001", "20221001-20231001", "20231001-20241001", "20240904-20250904", "20250904-20260904"]
FEE = 1.755e-05
PROF = "tradebot/strategies/spravynet/configs/mgc_databento_5m.json"
ALL = ["FOMC", "CPI", "PPI", "PCE", "JOLTS"]
only = lambda ev, **kw: {**{f"use{e}": e == ev for e in ALL}, **kw}
V = {
    "celok 3.0": {},
    "len FOMC pred (p1)": only("FOMC"),
    "len CPI fade (p3)": only("CPI"),
    "len PPI fade 1:3 (p4)": only("PPI"),
    "len PCE trend (p5)": only("PCE"),
    "len JOLTS fade (p6)": only("JOLTS"),
    "bez FOMC": {"useFOMC": False},
    "bez CPI": {"useCPI": False},
    "bez PPI": {"usePPI": False},
    "bez PCE": {"usePCE": False},
    "bez JOLTS": {"useJOLTS": False},
    "+ tlačovka FOMC (p2, p1 do 14:25)": {"r2Event": "FOMC", "r1Hold": 25},
    "PPI bez cieľa": {"r4RR": 0.0},
    "PPI 1:2": {"r4RR": 2.0},
    "PPI 1:4": {"r4RR": 4.0},
    "FOMC 1:2 (stop za extrémom)": {"r1RR": 2.0, "r1Stop": 0.0},
    "CPI 1:2 (stop za extrémom)": {"r3RR": 2.0, "r3Stop": 0.0},
    "PCE 1:2": {"r5RR": 2.0},
    "JOLTS 1:2 (stop za extrémom)": {"r6RR": 2.0, "r6Stop": 0.0},
    "bez CPI a JOLTS": {"useCPI": False, "useJOLTS": False},
}


def pf(rows):
    w = sum(r["profit_abs"] for r in rows if r["profit_abs"] > 0); l = -sum(r["profit_abs"] for r in rows if r["profit_abs"] < 0)
    return w / l if l else float("inf")


def run(inst_key, variants):
    inst = INSTRUMENTS[inst_key]
    cfg, _ = load_profile(PROF, engine=engines.MULTICHARTS)
    base = cfg.to_dict()
    cls = type(cfg)
    out = {}
    with NativeRunner("spravynet", inst, 5, FEE) as r:
        tasks, keys = [], []
        for name, ov in variants.items():
            js = json.dumps(cls.from_dict({**base, **ov}).to_dict())
            for w in W:
                tasks.append((js, w)); keys.append((name, w))
        res = r.run_many(tasks)
    for (name, w), x in zip(keys, res):
        if "error" in x:
            print("CHYBA", name, w, x["error"][:200]); continue
        rows = rows_from_trades(emulation_of(x).trades, inst, FEE)
        s = summary_money(rows, 100000)
        out.setdefault(name, {})[w] = {"rows": rows, "s": s}
    return out


def table(title, out):
    print(f"\n## {title}\n")
    print("| variant | PF po oknách | obch | WR | PF spolu | zisk $ | max DD $ | posl. rok: obch · WR · PF · zisk |")
    print("|---|---|---|---|---|---|---|---|")
    for name, ws in out.items():
        rows = [r for w in W for r in ws[w]["rows"]]
        allr = summary_money(rows, 100000)
        pfs = " · ".join(f"{pf(ws[w]['rows']):.2f}" for w in W)
        L = ws[W[-1]]["rows"]; ls = ws[W[-1]]["s"]
        wr = 100 * sum(1 for r in rows if r["profit_abs"] > 0) / max(1, len(rows))
        lwr = 100 * sum(1 for r in L if r["profit_abs"] > 0) / max(1, len(L))
        print(f"| {name} | {pfs} | {len(rows)} | {wr:.0f} % | **{pf(rows):.2f}** | {sum(r['profit_abs'] for r in rows):+,.0f} | "
              f"{allr.get('max_drawdown_abs', 0):,.0f} | {len(L)} · {lwr:.0f} % · {pf(L):.2f} · {sum(r['profit_abs'] for r in L):+,.0f} |")


if __name__ == "__main__":
    table("MGC 5m (Databento), 1 kontrakt", run("mgc_databento", V))
    table("XAU/USD 5m (Dukascopy) — iný trh, 1 kontrakt", run("xau_dukascopy", {k: V[k] for k in list(V)[:6]}))
