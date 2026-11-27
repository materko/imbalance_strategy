"""Finálne tabuľky VWAP: najvyšší WR na poslednom roku podľa počtu obchodov a podľa RR.
python vwfinal.py [save]"""
import json, sys, glob, subprocess, os
sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
import vwsearch as V
from vwcore import evaluate
ROOT = V.ROOT
SAVE = len(sys.argv) > 1 and sys.argv[1] == "save"
PREV = "20240904-20250904"
BANDS = [(25, 45), (45, 60), (60, 80), (80, 100), (100, 125), (125, 150), (150, 175), (175, 200), (200, 250), (250, 300), (300, 400)]
RRS = V.RRS
NAMES = {"vwaporb": ("VWO", "VWAP ORB 1.5"), "vwapdrift": ("VWS", "VWAP Session 1.0")}
if V.PURE:
    NAMES = {"vwaporb": ("VWOP", "VWAP ORB 1.5 (stop/cieľ)"), "vwapdrift": ("VWSP", "VWAP Session 1.0 (stop/cieľ)"),
             "jss": ("JSS", "JSS 1.0 (stop/cieľ)")}
KEYS = os.environ.get("VW_KEYS", "vwaporb,vwapdrift").split(",")

PURE = V.PURE

def pure(k, p):
    if k == "jss":
        return True
    if p.get("closeAtSessionEnd", True):
        return False
    return k != "vwaporb" or not (p["enableTrailing"] or p["vwapStop"] or p["vwapTp"] or p["exitMode"] != "tp" or p["emaExit"])

def load(k):
    out, seen = [], set()
    for fn in sorted(glob.glob(str(ROOT / ".nightsearch" / (os.environ.get("VW_GLOB", "vw*") + f"_{k}.jsonl")))):
        for l in open(fn):
            d = json.loads(l); r = d["r"]
            if not r or r["trades"] < 25 or r["pnl_abs"] <= 0:
                continue
            if PURE:
                if not pure(k, d["p"]):
                    continue
                if "payoff_r" not in r:
                    r.update(evaluate(V.enc(k, d["p"]), d["p"]["_tf"], V.LAST)) if r["winrate"] >= 65 else None
                if r.get("payoff_r", 0) < 0.9 * d["p"]["rrRatio"]:
                    continue
            elif r["payoff"] < 0.9:
                continue
            key = (r["trades"], r["wins"], round(r["pnl_abs"], 1))
            if key in seen:
                continue
            seen.add(key); out.append(d)
    return out

def best(rows, cond, n):
    g = [d for d in rows if cond(d)]
    g.sort(key=lambda d: (-d["r"]["winrate"], -d["r"]["profit_factor"]))
    out, seen = [], set()
    for d in g:   # takmer rovnaké výsledky (rovnaký počet obchodov a WR) len raz
        key = (d["r"]["trades"], d["r"]["winrate"])
        if key not in seen:
            seen.add(key); out.append(d)
        if len(out) >= n:
            break
    return out

def fmt(k, tag, d, prev):
    r, p = d["r"], d["p"]
    extra = []
    if k == "jss":
        extra.append(f"štruktúra {p['structTF']}m swing {p['swingLen']} {p['triggerMode']}")
        extra.append(f"zóna {p['zoneType']}/{p['zoneEdge']} impulz {p['impulseAtr']} ATR")
        extra.append(f"vstup {p['entryModel']}" + (f" {p['entryDepthPct']} %" if p['entryDepthPct'] else ""))
        extra.append(f"SL +{p['slBufferAtr']} ATR +{p['slBufferPoints']} b, cieľ {p['tpMode']}")
    elif k == "vwaporb":
        extra.append(f"range {p['nyRangeMinutes']}m" + (" + Londýn" if p.get("sessionMode") == "both" else ""))
        extra.append(f"VWAP {p['vwapRule']}/{p['entryTiming']}")
        extra.append(f"vstup {p['entryMode']}, SL {p['slMode']}, výstup {p['exitMode']}" + (", SL na VWAP" if p["vwapStop"] else "") + (", TP na VWAP" if p["vwapTp"] else "") + (", trailing" if p["enableTrailing"] else ""))
    else:
        extra.append(f"vstup {p['entryMode']}, SL {p['slMode']}")
        extra.append(("každý odraz" if p["everyBounce"] else "prvý pullback") + (" + prerazenie" if p["tradeBreakout"] else ""))
        extra.append(f"koniec {p['sessionEndH']}:{p['sessionEndM']:02d}")
    if not PURE: extra.append("koniec seansy " + ("zap." if p.get("closeAtSessionEnd", True) else "VYP."))
    return (f"| {tag} | {r['trades']} | **{r['winrate']:.1f} %** | {p['rrRatio']} | {r.get('payoff_r', r['payoff']):.2f} | {r['profit_factor']:.2f} | "
            f"{r['pnl_abs']:+.0f} $ | {r['max_drawdown_abs']:.0f} $ | {p['_tf']}m | {p['tradeDirection']} | {'; '.join(extra)} | "
            f"{prev['trades']} / {prev['winrate']:.1f} % |")

HDR = ("| | obch | WR | RR | reálny zisk:strata | PF | zisk | maxDD | TF | smer | nastavenie | predch. rok obch / WR |\n"
       "|---|---|---|---|---|---|---|---|---|---|---|---|")
md = []
profiles = []
for k in KEYS:
    rows = load(k)
    pre, title = NAMES[k]
    md.append(f"\n## {title} (`{k}`) — {len(rows)} ziskových nastavení s reálnym zisk:strata ≥ 0,9\n")
    md.append("### Podľa počtu obchodov za posledný rok\n"); md.append(HDR)
    picked = []
    for lo, hi in BANDS:
        for d in best(rows, lambda d: lo <= d["r"]["trades"] < hi, 2):
            picked.append((f"{lo}–{hi}", d))
    for tag, d in picked:
        d["prev"] = d.get("prev") or evaluate(V.enc(k, d["p"]), d["p"]["_tf"], PREV)
        md.append(fmt(k, tag, d, d["prev"]))
    md.append("\n### Podľa RR (aspoň 60 obchodov za rok)\n"); md.append(HDR)
    picked2 = []
    for rr in RRS:
        for d in best(rows, lambda d: d["p"]["rrRatio"] == rr and d["r"]["trades"] >= 60, 2):
            picked2.append((f"RR {rr}", d))
    for tag, d in picked2:
        d["prev"] = d.get("prev") or evaluate(V.enc(k, d["p"]), d["p"]["_tf"], PREV)
        md.append(fmt(k, tag, d, d["prev"]))
    uniq = {}
    for tag, d in picked + picked2:
        uniq[json.dumps(d["p"], sort_keys=True)] = d
    profiles += [(k, d) for d in uniq.values()]
out = "\n".join(md)
open(ROOT / ".nightsearch" / (("JSS" if KEYS == ["jss"] else "VWP") + "_report.md" if PURE else "VW_report.md"), "w").write(out)
print(out)
print("profilov:", len(profiles))
if SAVE:
    from tradebot.strategies import get_spec
    for k, d in profiles:
        r, p = d["r"], d["p"]
        name = f"{NAMES[k][0]}_RR{str(p['rrRatio']).replace('.', '_')}_{r['trades']}obch_WR{int(r['winrate'])}"
        prof = get_spec(k).config_cls().to_dict(); prof.update(V.enc(k, p))
        ttl = (f"{NAMES[k][1]}: posl. rok {r['trades']} obch, {r['winrate']:.1f} % WR, RR {p['rrRatio']}, "
               f"reálny zisk:strata {r.get('payoff_r', r['payoff']):.2f}, PF {r['profit_factor']:.2f}, {r['pnl_abs']:+.0f} $")
        prof.update({"_title": ttl, "_comment": [ttl, f"Predch. rok (24/25): {d['prev']['trades']} obch, {d['prev']['winrate']:.1f} % WR, {d['prev']['pnl_abs']:+.0f} $",
                     ("Bez konca seansy a trailingu, len stop a cieľ. " if PURE else "") + "Testy 28.-30.9.2026, emulátor MultiCharts, MNQ, BEZ nákladov, riziko 100 $/obchod (min. 1 kontrakt)."],
                     "_timeframe": f"{p['_tf']}m", "_timerange": V.LAST, "_fee": 0.0, "_wallet": 10000.0, "_detail": False})
        fn = ROOT / "tester" / "profiles" / f"{name}.json"
        json.dump(prof, open(fn, "w"), ensure_ascii=False, indent=2)
        res = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "tester.webapp.cli", "run", "--strategy", k,
                              "--profile", str(fn.relative_to(ROOT)), "--pair", "MNQ/USD", "--engine", "multicharts",
                              "--timeframe", f"{p['_tf']}m", "--timerange", V.LAST, "--fee", "0", "--wallet", "10000",
                              "--note", f"VWAP testy A (posledný rok): {name}"], capture_output=True, text=True, cwd=ROOT)
        line = [l for l in res.stdout.splitlines() if "obchodov" in l][-1:]
        print(name, "|", line[0][:150] if line else res.stderr[-300:])
