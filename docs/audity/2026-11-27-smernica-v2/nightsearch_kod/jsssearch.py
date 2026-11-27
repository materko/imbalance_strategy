"""JSS 1.0: najvyšší WR na poslednom roku pri RR 1-2, len stop a cieľ (bez konca seansy a trailingu).
VW_TAG=j VW_PURE=1 VW_FREQ=1 VW_WORKERS=4 python jsssearch.py <hodiny>  — výstup vwj_jss.jsonl"""
import sys
sys.path.insert(0, "/Users/martin/IBS/.nightsearch")
import vwsearch as V
B = [True, False]
V.SPACES = {"jss": {
    "_tf": [2, 3, 5, 5], "structTF": [5, 5, 10, 15, 15, 30], "swingLen": [2, 3, 3, 4, 5, 8],
    "triggerMode": ["bos", "choch", "both"], "zoneType": ["ob", "ob", "base"], "zoneEdge": ["wick", "body"],
    "impulseAtr": [0.3, 0.5, 0.75, 1.0, 1.5], "baseMaxBars": [1, 2, 3, 5], "zoneMinAtr": [0, 0, 0.1, 0.25],
    "zoneMaxAtr": [0, 1.0, 1.5, 2.0, 3.0], "zoneMaxAgeBars": [0, 12, 24, 48, 100, 200],
    "entryModel": ["touch", "touch", "imbalance", "pinbar", "any"], "entryDepthPct": [0, 0, 25, 50],
    "confirmBars": [2, 4, 6, 10], "imbMinSizeAtr": [0, 0.05, 0.1, 0.2], "pbWickPct": [50, 60, 70], "pbBodyPct": [20, 30],
    "tradeDirection": ["Both", "Both", "Long only", "Short only"], "maxTradesPerDay": [1, 2, 3, 5, 10],
    "cooldownBars": [0, 3, 6, 12], "useTradeWindow": [False, True, True], "tradeStartH": [2, 3, 8, 9, 10],
    "tradeStartM": [0, 30], "tradeEndH": [11, 12, 15, 16], "tradeEndM": [0, 30],
    "slBufferAtr": [0, 0.05, 0.1, 0.25, 0.5], "slBufferPoints": [0, 0, 2, 5, 10, 20],
    "tpMode": ["rr", "rr", "rr", "structure"], "rrRatio": V.RRS, "minRR": [1.0, 1.5],
}}
_fix = V.fix
def fix(key, c):
    if key != "jss":
        return _fix(key, c)
    if c["tradeEndH"] * 60 + c["tradeEndM"] <= c["tradeStartH"] * 60 + c["tradeStartM"]:
        c["tradeEndH"] = 16
    if c["zoneMaxAtr"] and c["zoneMinAtr"] > c["zoneMaxAtr"]:
        c["zoneMinAtr"] = 0
    if c["tpMode"] == "structure":
        c["rrRatio"] = 1.0   # cieľ je extrém nohy; hodnotí sa pomer v R voči 1R
    return c
V.fix = fix
if __name__ == "__main__":
    V.HOURS = float(sys.argv[1]); import time; V.DEADLINE = time.time() + V.HOURS * 3600
    V.main()
