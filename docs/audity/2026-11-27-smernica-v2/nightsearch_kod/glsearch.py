"""Hľadanie podľa smernice testovania (SMERNICA-TESTOVANIA, 8. 10. 2026) — VWAP ORB, IBS Entry Zone, SPX sila.

* ladenie (in-sample) 2021-10-01 – 2025-09-04, s poplatkom 1,755e-05, emulátor MultiCharts,
* naraz najviac 4 parametre (skupina), ostatné na doterajšom najlepšom — postupne skupina po skupine, dokola,
* cieľ: PF na ladení a stabilita po rokoch (žiadny rok pod PF 0,9), min. 100 obchodov za rok — nikdy winrate,
* počíta sa, koľko kombinácií sa skúsilo (smernica: nad 1000 prísnejšie hranice),
* kandidát (PF ≥ 1,3, roky OK) → plató (susedné hodnoty ≥ 80 % PF) → odložený rok 2025-09-04 – 2026-09-04 raz.
Pravidlá používateľa: bez trailingu a bez konca seansy.

python glsearch.py — beží donekonečna; počet procesov sa číta zo súboru gl_workers.txt pri každej skupine.
Výstup: gl_<stratégia>.jsonl (každé vyhodnotenie), gl_state.json (najlepšie, kandidáti, počty)."""
from __future__ import annotations

import itertools, json, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, "/Users/martin/IBS/.nightsearch"); sys.path.insert(0, "/Users/martin/IBS")
ROOT = Path("/Users/martin/IBS/.nightsearch")
FEE = 1.755e-05
IS = "20211001-20250904"
OOS = "20250904-20260904"
WINDOWS = [("21/22", "2021-10-01", "2022-10-01"), ("22/23", "2022-10-01", "2023-10-01"),
           ("23/24", "2023-10-01", "2024-09-04"), ("24/25", "2024-09-04", "2025-09-04")]
YEARS = 3.93
#: Vlastné obdobie ladenia (používateľ 11. 11. 2026, MTK ORB na zlate): všetky dáta MGC, odložené 2 roky.
_MGC_WINDOWS = [(f"{y % 100:02d}/{(y + 1) % 100:02d}", f"{y}-10-01" if y > 2010 else "2010-11-01",
                 f"{y + 1}-10-01" if y < 2023 else "2024-09-04") for y in range(2010, 2024)]
PERIODS = {"mtkorb": ("20101101-20240904", "20240904-20260904", _MGC_WINDOWS, 13.84)}


def is_tr(key=None) -> str:
    return PERIODS[key][0] if key in PERIODS else IS


def oos_tr(key=None) -> str:
    return PERIODS[key][1] if key in PERIODS else OOS


def windows(key=None) -> list:
    return PERIODS[key][2] if key in PERIODS else WINDOWS


def years(key=None) -> float:
    return PERIODS[key][3] if key in PERIODS else YEARS
MIN_TRADES_YEAR = 75   # 8. 11. 2026 používateľ: smernica 75 obchodov za rok (predtým 150)
#: trh stratégie (inštrument, pár pre CLI); čo tu nie je, je MNQ (používateľ 20. 10. 2026: IBS EZ MGC na zlate)
INSTR = {"ibsentrymgc": ("mgc_databento", "MGC/USD"), "scalp3mamgc": ("mgc_databento", "MGC/USD"), "fibomgc": ("mgc_databento", "MGC/USD"), "ibsentryes": ("es_databento", "ES/USD"), "nyvaes": ("es_databento", "ES/USD"),
         "sdeur": ("6e_databento", "6E/USD"),
         "m2": ("es_databento", "ES/USD"), "m2mnq": ("mnq_databento", "MNQ/USD"), "m2mgc": ("mgc_databento", "MGC/USD"),
         "m2eur": ("6e_databento", "6E/USD"),
         "noaes": ("es_databento", "ES/USD"), "noamgc": ("mgc_databento", "MGC/USD")}


# Krok 8 smernice „iný trh“ a priečinok na stránke podľa inštrumentu (24. 10. 2026: nový trh = riadok sem,
# ranné nahrávanie si poradí samo). (inštrument, pár, názov na stránke, poplatok na stranu)
OTHER_MARKET = {"mnq_databento": ("nas100_dukascopy", "NAS100/USD", "NAS100", "2.5e-05"),
                "mgc_databento": ("xau_dukascopy", "XAU/USD", "XAU/USD", "3e-05"),
                "es_databento": ("us500_dukascopy", "US500/USD", "US500", "2.5e-05"),
                "6e_databento": ("eurusd_dukascopy", "EUR/USD", "EURUSD CFD", "3e-05")}
FOLDER = {"mnq_databento": "NASDAQ", "mgc_databento": "GOLD", "es_databento": "SP 500", "6e_databento": "EURUSD"}
BASE_LABEL = {"mnq_databento": "MNQ", "mgc_databento": "MGC", "es_databento": "ES", "6e_databento": "6E"}


def title(key: str) -> str:
    """Názov stratégie z registry (nová stratégia nepotrebuje zápis do NAMES)."""
    try:
        from tradebot.strategies import STRATEGIES
        return STRATEGIES[key].title
    except Exception:
        return key


def one_contract(key: str, p: dict) -> dict:
    """Výsledky smernice sú na 1 kontrakt: pevný počet zapnúť, ak ho nastavenie výslovne nemá.
    8. 11. 2026: bez neho sa veľkosť počíta z rizika a strop straty (audit N-LIVE-20) vynechá každý obchod,
    pri ktorom by aj 1 kontrakt stratil viac než `riskDollar` / `maxLossDollar` — VWAP ORB tak mal na
    stránke 24 obchodov namiesto 776 (Sortino 0,33), NY VA ES a Fibo MGC tretinu obchodov menej."""
    if key in RISK_SIZED:
        return p
    # spoločný obal veľkosti (`entry_sizing`): pevný počet `qty` aj nad vlastnou veľkosťou stratégie z rizika (Fibo MGC)
    p["fixedQty"], p["qty"], p["skipOverRisk"] = True, 1.0, False
    return p


#: Stratégie, ktorých schválené profily stoja na veľkosti z rizika (SPRÁVY: riskDollar 500, používateľ 30. 10.).
RISK_SIZED = {"spravy", "spravynet", "spravyeur", "spravyeurnet"}   # 21. 11.: SPRÁVY EUR/USD tiež riziko 500 $


def instr(key: str) -> tuple:
    return INSTR.get(key, ("mnq_databento", "MNQ/USD"))
B = [False, True]
A = lambda v: {"value": v, "unit": "atr"}   # prah v násobkoch ATR (stratégie na iných trhoch ako NQ)

NO_EXIT = {  # pravidlá používateľa: bez trailingu a konca seansy
    "vwaporb": {"closeAtSessionEnd": False, "enableTrailing": False, "vwapStop": False, "vwapTp": False, "exitMode": "tp",
                "emaExit": False},
    "ibsentry": {"closeAtSessionEnd": False, "enableTrailing": False},
    "ibsentrymgc": {"closeAtSessionEnd": False, "enableTrailing": False},
    "ibsentryes": {"closeAtSessionEnd": False, "enableTrailing": False},
    "nyva": {"useCloseTime": False},
    "nyvaes": {"useCloseTime": False},
    "sdeur": {"maxHoldHours": 0},
    "m2": {}, "m2mnq": {}, "m2mgc": {}, "m2eur": {},   # M2 nemá výstup v čase ani trailing
    "scalp3mamgc": {"beAtR": 0},
    "fibomgc": {"maxHoldBars": 0},
    "mag7": {"useEod": False},
    "jss": {"maxHoldBars": 0},
    "crt": {"maxHoldBars": 0},
    "dailyopen": {"useExit": False},
    "svp": {"closeAtWindowEnd": False},
    "voltbreak": {"useTimeExit": False},
    "vwapadx": {"useTimeExit": False},
    "onbiasorb": {"useTimeExit": False},
    "sweepfvg": {"useExitTime": False},
    "sweepengulf": {},
    "varev": {},
    "fpc": {"useCloseAfter": False},
    "range": {"enableTrailing": False, "closeAtWindowEnd": False, "maxHoldBars": 0},
    "silverbullet": {"useExitTime": False},
    "tks": {"closeAtSessionEnd": False},
    "nocpon": {},   # výstup v čase je podstata javu (nočný drift, pondelok) — nie koniec seansy na zatvorenie
    "noa": {},
    "noaes": {}, "noamgc": {},   # 11. 11. 2026: NOA na ES a MGC — výstup ako NOA   # výstup o 16:00 / cez VWAP je podstata NOA (zdroj) — trailVwap sa skúša v mriežke oboma spôsobmi
}
BASE = {
    "vwaporb": ("/Users/martin/IBS/tradebot/strategies/vwaporb/configs/mnq_databento_5m.json", 5),
    "ibsentry": ("/Users/martin/IBS/tester/profiles/NOCNE2_B_stabilny_entry.json", 3),
    "ibsentrymgc": ("/Users/martin/IBS/.nightsearch/base_ibsentrymgc.json", 3),
    "ibsentryes": ("/Users/martin/IBS/.nightsearch/base_ibsentryes.json", 3),
    "nyva": ("/Users/martin/IBS/tradebot/strategies/nyva/configs/mnq_databento_3m.json", 3),
    "nyvaes": ("/Users/martin/IBS/tradebot/strategies/nyvaes/configs/es_databento_3m.json", 3),
    "sdeur": ("/Users/martin/IBS/tradebot/strategies/sdeur/configs/eurusd_6e_5m.json", 5),
    "m2": ("/Users/martin/IBS/tradebot/strategies/m2/configs/es_databento_1m.json", 1),
    "m2mnq": ("/Users/martin/IBS/tradebot/strategies/m2mnq/configs/mnq_databento_1m.json", 1),
    "m2mgc": ("/Users/martin/IBS/tradebot/strategies/m2mgc/configs/mgc_databento_1m.json", 1),
    "m2eur": ("/Users/martin/IBS/tradebot/strategies/m2eur/configs/6e_databento_1m.json", 1),
    "scalp3mamgc": ("/Users/martin/IBS/.nightsearch/base_scalp3mamgc.json", 15),
    "fibomgc": ("/Users/martin/IBS/.nightsearch/base_fibomgc.json", 3),
    "mag7": ("/Users/martin/IBS/tradebot/strategies/mag7/configs/mnq_databento_15m.json", 15),
    "jss": ("/Users/martin/IBS/tester/profiles/R1_jss_MNQ_180obch_WR70.json", 3),
    "crt": ("/Users/martin/IBS/tester/profiles/WK_crt_MNQ_200obch_WR46_R1_7.json", 3),
    "dailyopen": ("/Users/martin/IBS/.nightsearch/base_dailyopen.json", 15),
    "svp": ("/Users/martin/IBS/.nightsearch/base_svp.json", 15),
    "voltbreak": ("/Users/martin/IBS/.nightsearch/base_voltbreak.json", 30),
    "vwapadx": ("/Users/martin/IBS/.nightsearch/base_vwapadx.json", 1),
    "onbiasorb": ("/Users/martin/IBS/.nightsearch/base_onbiasorb.json", 15),
    "sweepfvg": ("/Users/martin/IBS/.nightsearch/base_sweepfvg.json", 5),
    "sweepengulf": ("/Users/martin/IBS/.nightsearch/base_sweepengulf.json", 240),
    "varev": ("/Users/martin/IBS/.nightsearch/base_varev.json", 15),
    "fpc": ("/Users/martin/IBS/.nightsearch/base_fpc.json", 1),
    "range": ("/Users/martin/IBS/.nightsearch/base_range.json", 3),
    "noa": ("/Users/martin/IBS/.nightsearch/base_noa.json", 5),
    "noaes": ("/Users/martin/IBS/.nightsearch/base_noaes.json", 5),
    "noamgc": ("/Users/martin/IBS/.nightsearch/base_noamgc.json", 5),
    "silverbullet": ("/Users/martin/IBS/.nightsearch/base_silverbullet.json", 5),
    "tks": ("/Users/martin/IBS/.nightsearch/base_tks.json", 3),
    "nocpon": ("/Users/martin/IBS/.nightsearch/base_nocpon.json", 5),
}
GROUPS = {
    "sdeur": [   # SD ZÓNY EURUSD (26. 10. 2026): kvalita zóny je hlavná — TF zóny, odchod, výška, čas vzniku; vstup Londýn
        {"zoneTF": [15, 30, 60, 120], "depMaxBars": [2, 4, 6, 8, 12], "depMin": [A(0.5), A(1.0), A(1.5), A(2.0)], "extremeBars": [0, 2, 4, 8]},
        {"rrRatio": [1.0, 1.5, 2.0, 2.5, 3.0], "slBuffer": [A(0.0), A(0.1), A(0.25), A(0.5), A(1.0)], "entryDepthPct": [0, 25, 50],
         "baseMaxBars": [1, 2, 3, 4]},
        {"useFormWindow": B, "formStartH": [17, 18, 19, 20, 22], "formEndH": [0, 1, 2, 3, 4], "zoneMaxHours": [24, 48, 120]},
        {"entryStartH": [0, 1, 2, 3], "entryStartM": [0, 30], "entryEndH": [5, 7, 9, 11, 12], "maxTradesPerDay": [0, 1, 2]},
        {"minZoneHeight": [A(0.0), A(0.3), A(0.5), A(0.8)], "maxZoneHeight": [A(0.0), A(1.0), A(1.5), A(2.5)],
         "baseMax": [A(1.0), A(2.0), A(3.0)], "atrLen": [14, 50]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 60, 240], "volFilter": ["off", "low", "high"]},
        {"_tf": [3, 5], "allowLong": B, "allowShort": B, "zoneTF": [30, 60, 120]},
    ],
    "vwaporb": [
        {"_tf": [3, 5], "nyRangeMinutes": [5, 10, 15, 30, 45, 60], "vwapRule": ["break", "direction"], "entryTiming": ["any", "break_candle"]},
        {"slMode": ["opposite", "mid", "atr", "break_candle"], "tpMode": ["rr", "measured"], "rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0],
         "slBufferAtr": [0.0, 0.1, 0.25, 0.5]},
        {"sessionMode": ["ny", "both"], "vwapAnchor": ["ny_open", "session"], "vwapPeriod": ["15", "chart"], "closeBeyondVwap": B},
        {"entryWindowMinutes": [0, 30, 60, 120, 240], "maxTradesPerDay": [1, 2, 3], "minRangePct": [0.0, 0.1, 0.2, 0.3],
         "maxRangePct": [0.5, 1.0, 2.0, 10.0]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ],
    "ibsentry": [
        {"rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], "slLookback": [5, 10, 20], "minSlDistance": [0.0, 0.05, 0.1, 0.15],
         "slBufferTicks": [0, 2, 4]},
        {"minImbSizePoints": [2.5, 4, 6, 8, 10], "imbLookback": [5, 10, 20], "state2ConfirmTicks": [1, 3, 6, 10], "imbMaxDistTicks": [40, 100]},
        {"zoneDetectionTF": ["3", "5", "15"], "zoneValidHours": [3, 6, 12], "snapMode": ["Floor", "Ceil"], "fvgMinSize": [5, 15, 30, 50]},
        {"indAdx": B, "adxThreshold": [15.0, 20.0, 25.0], "indSupertrend": B, "stMultiplier": [3, 5]},
        {"enablePinBarEntry": B, "pbWickToBodyRatio": [4, 8], "enableFvgTrading": B, "enableIfvgTrading": B},
        {"maxDailyWins": [3, 5, 9, 99], "state4MaxBars": [5, 10, 20], "state5MaxBars": [5, 10], "state3MaxBars": [1, 2, 4]},
    ],
    "ibsentrymgc": [   # IBS Entry Zone na zlate: bodové / tickové prahy v násobkoch ATR (A)
        {"rrRatio": [0.5, 0.6, 0.75, 1.0, 1.25, 1.5, 2.0], "slLookback": [5, 10, 20], "minSlDistance": [0.0, 0.05, 0.1, 0.15],
         "slBufferTicks": [A(0.0), A(0.1), A(0.2)]},
        {"minImbSizePoints": [A(0.3), A(0.5), A(0.8), A(1.0), A(1.5)], "imbLookback": [5, 10, 20],
         "state2ConfirmTicks": [A(0.05), A(0.15), A(0.3), A(0.6)], "imbMaxDistTicks": [A(0.5), A(1.0), A(2.5)]},
        {"zoneDetectionTF": ["3", "5", "15"], "zoneValidHours": [3, 6, 12], "snapMode": ["Floor", "Ceil"], "fvgMinSize": [A(0.5), A(1.5), A(3.0), A(6.0)]},
        {"indAdx": B, "adxThreshold": [15.0, 20.0, 25.0], "indSupertrend": B, "stMultiplier": [3, 5]},
        {"enablePinBarEntry": B, "pbWickToBodyRatio": [4, 8], "enableFvgTrading": B, "enableIfvgTrading": B},
        {"maxDailyWins": [3, 5, 9, 20], "state4MaxBars": [5, 10, 20], "state5MaxBars": [5, 10], "state3MaxBars": [1, 2, 4]},
        {"pbMinRangePoints": [A(0.2), A(0.4), A(0.8)], "engMinRangePoints": [A(0.3), A(0.6), A(1.2)], "srClusterPoints": [A(0.8), A(1.5), A(3.0)], "_tf": [3, 5]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"volFilter": ["off", "low", "high"], "volLookback": [100, 500, 1000, 2000], "trendFilter": ["off", "with"], "_tf": [3, 5]},
        # časové okná podľa prieskumu MGC z MacBooku (21. 10.): COMEX 8–11 ET a Ázia 20–22 h majú najviac pohybu a objemu
        {"sess2TradeStartH": [8, 9], "sess2TradeStartM": [0, 20, 30], "sess2TradeEndH": [11, 12, 13, 16], "sess2TZ": ["America/New_York"]},
        {"sess3On": B, "sess3TradeStartH": [19, 20, 21], "sess3TradeEndH": [22, 23], "sess3ZoneStartH": [14, 18]},
        {"sess1On": B, "sess1TradeStartH": [0, 2, 3], "sess1TradeEndH": [3, 5, 8], "sess1ZoneStartH": [0, 18]},
    ],
    "ibsentryes": [   # IBS Entry Zone na ES (22. 10.): bodové / tickové prahy v násobkoch ATR (A)
        {"rrRatio": [0.5, 0.6, 0.75, 1.0, 1.25, 1.5, 2.0], "slLookback": [5, 10, 20], "minSlDistance": [0.0, 0.05, 0.1, 0.15],
         "slBufferTicks": [A(0.0), A(0.1), A(0.2)]},
        {"minImbSizePoints": [A(0.3), A(0.5), A(0.8), A(1.0), A(1.5)], "imbLookback": [5, 10, 20],
         "state2ConfirmTicks": [A(0.05), A(0.15), A(0.3), A(0.6)], "imbMaxDistTicks": [A(0.5), A(1.0), A(2.5)]},
        {"zoneDetectionTF": ["3", "5", "15"], "zoneValidHours": [3, 6, 12], "snapMode": ["Floor", "Ceil"], "fvgMinSize": [A(0.5), A(1.5), A(3.0), A(6.0)]},
        {"indAdx": B, "adxThreshold": [15.0, 20.0, 25.0], "indSupertrend": B, "stMultiplier": [3, 5]},
        {"enablePinBarEntry": B, "pbWickToBodyRatio": [4, 8], "enableFvgTrading": B, "enableIfvgTrading": B},
        {"maxDailyWins": [3, 5, 9, 20], "state4MaxBars": [5, 10, 20], "state5MaxBars": [5, 10], "state3MaxBars": [1, 2, 4]},
        {"pbMinRangePoints": [A(0.2), A(0.4), A(0.8)], "engMinRangePoints": [A(0.3), A(0.6), A(1.2)], "srClusterPoints": [A(0.8), A(1.5), A(3.0)], "_tf": [3, 5]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"volFilter": ["off", "low", "high"], "volLookback": [100, 500, 1000, 2000], "trendFilter": ["off", "with"], "_tf": [3, 5]},
        # časové okná ES (meranie 22. 10.): najviac objemu 9–11 h a 15–16 h NY (MOC), obed 12–13:30 najslabší
        {"sess2TradeStartH": [9, 10], "sess2TradeStartM": [30, 45, 0], "sess2TradeEndH": [11, 12, 15, 16], "sess2TZ": ["America/New_York"]},
        {"sess3On": B, "sess3TradeStartH": [14, 15], "sess3TradeEndH": [16], "sess3ZoneStartH": [9, 12]},
        {"sess1On": B, "sess1TradeStartH": [2, 3, 8], "sess1TradeEndH": [5, 8, 9], "sess1ZoneStartH": [0, 18]},
    ],
    "scalp3mamgc": [   # Scalping 3MA na zlate (MacBook 21. 10.: profily 5/5 rokov bez nákladov)
        {"_tf": [5, 15, 30], "ma1Len": [10, 20, 30], "ma2Len": [50, 80, 100], "ma3Len": [150, 200, 300]},
        {"rsiLen": [7, 14, 21], "rsiLevel": [50, 55, 60], "fractalLen": [2, 3, 5], "fractalSide": ["pullback", "trend", "any"]},
        {"slMode": ["atr", "fractal"], "slAtr": [1.0, 1.5, 2.0, 3.0], "rrRatio": [0.5, 0.75, 0.9, 1.0, 1.2, 1.5, 2.0], "slBufferAtr": [0.0, 0.1, 0.25]},
        {"tradeStartH": [2, 8, 9], "tradeEndH": [11, 13, 16, 20], "maxTradesPerDay": [1, 2, 3], "cooldownBars": [0, 3, 6]},
        {"requireMaOrder": B, "rsiExit": B, "tradeDirection": ["Both", "Long only", "Short only"], "weekdaysOnly": B},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60, 240], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "limitValidBars": [3, 6], "volLookback": [50, 300, 1000]},
    ],
    "fibomgc": [   # Fibo 1.0 na zlate (MacBook 21. 10.: profily 5/5 rokov bez nákladov)
        {"_tf": [3, 5], "swingTF": [5, 15, 30], "swingLen": [3, 5, 8], "legMinAtr": [1.5, 2.0, 3.0, 4.0]},
        {"use382": B, "use50": B, "use618": B, "use786": B},
        {"levelMode": ["zone", "levels"], "setupMaxBars": [20, 40, 80], "signalMaxBars": [2, 3, 5], "imbMinSizeAtr": [0.05, 0.1, 0.2]},
        {"slMode": ["leg", "pullback"], "tpMode": ["rr", "extension"], "rrRatio": [0.5, 0.75, 0.9, 1.0, 1.5], "minRR": [0.5, 1.0]},
        {"tradeDirection": ["Both", "Long only", "Short only"], "tradeStartH": [2, 8, 9], "tradeEndH": [11, 16, 20], "maxTradesPerDay": [1, 2, 3]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60, 240], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "limitValidBars": [3, 6], "volLookback": [50, 300, 1000]},
        # trend na vyššom TF (MacBook 21. 10.: smer podľa SMA 50 denných zavretí pomohol ORB na zlate), aj denný TF
        {"trendFilter": ["off", "with", "against"], "trendTF": [60, 240, 1440], "trendEmaLen": [20, 50, 100, 200], "tradeDirection": ["Both", "Long only"]},
        {"trendFilter": ["with"], "trendTF": [1440], "trendEmaLen": [10, 20, 30, 50, 75, 100], "volFilter": ["off", "low", "high"]},
        # časové okná: COMEX 8–11 ET, Londýn od 2–3 h, celý deň
        {"tradeStartH": [2, 3, 8, 9], "tradeStartM": [0, 30], "tradeEndH": [11, 12, 13, 16, 20], "weekdaysOnly": B},
    ],
    "mag7": [
        {"_tf": [5, 15, 30], "thr": [3.0, 4.0, 5.0, 6.0, 7.0], "waitMin": [10, 15, 20, 30], "entryEnd": [30, 60, 90, 120]},
        {"slMode": ["open", "points"], "slPts": [20.0, 30.0, 40.0, 60.0, 80.0], "slOpenBuf": [0.0, 2.0, 5.0, 10.0],
         "rr": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]},
        {"useVwap": B, "useEma": B, "emaLen": [20, 50, 100, 200], "useMag": B},
        {"typDays": [10, 20, 40], "zFull": [0.5, 1.0, 1.5, 2.0], "wBreadth": [0.0, 0.5, 1.0, 2.0], "magLen": [3, 5, 9]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ],
    "jss": [
        {"_tf": [3, 5], "structTF": [5, 15, 30, 60], "swingLen": [2, 3, 5, 8], "triggerMode": ["bos", "choch", "both"]},
        {"zoneType": ["ob", "base"], "zoneEdge": ["wick", "body"], "impulseAtr": [0.5, 0.75, 1.0, 1.5], "zoneMaxAtr": [1.0, 1.5, 2.25, 3.0]},
        {"entryModel": ["touch", "imbalance", "pinbar", "any"], "entryDepthPct": [0, 25, 50, 75], "confirmBars": [2, 4, 8], "zoneMaxAgeBars": [48, 100, 200, 500]},
        {"slFrom": ["refined", "htf"], "slBufferAtr": [0.0, 0.05, 0.1, 0.25], "tpMode": ["rr", "structure", "extension"], "rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]},
        {"tradeStartH": [2, 8, 9], "tradeEndH": [11, 12, 16], "maxTradesPerDay": [1, 2, 3, 5], "cooldownBars": [0, 6, 12]},
        {"useFibo": B, "fibMinPct": [38.2, 50.0, 61.8], "trendFilter": ["off", "with", "against"], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "refineTF": [0, 1, 3, 5], "tradeDirection": ["Both", "Long only", "Short only"]},
    ],
    "crt": [
        {"_tf": [3, 5], "rangeTF": [60, 120, 240], "sweepKind": ["body", "wick", "any"], "entryModel": ["model1", "cisd", "mss_fvg"]},
        {"sweepWithinBars": [1, 2, 3], "validBars": [1, 2, 4], "requireHtfClose": B, "requireOldHL": B},
        {"slBufferAtr": [0.0, 0.25, 0.5, 1.0], "tpMode": ["mid", "opposite", "rr"], "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0], "minRR": [0.5, 1.0, 1.5]},
        {"tradeStartH": [2, 3, 8, 9], "tradeEndH": [11, 12, 16, 20], "maxTradesPerDay": [1, 2, 3, 5], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"rangeMaxAtr": [0.0, 1.0, 2.0, 3.0], "sweepMaxAtr": [0.0, 0.5, 1.0], "swingLen": [2, 3, 5], "fvgValidBars": [6, 12, 24]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "dailyopen": [
        {"_tf": [5, 15, 60], "refH": [0, 8, 9], "breakPts": [0.0, 5.0, 10.0, 20.0, 30.0], "entryMode": ["stop", "close"]},
        {"slPts": [25.0, 50.0, 75.0, 100.0, 125.0], "tpPts": [5.0, 10.0, 20.0, 30.0, 50.0], "breakMode": ["any", "before"], "maxTradesPerDay": [1, 2, 3]},
        {"entryStartH": [3, 8, 9, 10], "entryEndH": [11, 12, 14, 16], "tradeDirection": ["Both", "Long only", "Short only"], "weekdaysOnly": B},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "svp": [
        {"_tf": [5, 15], "pocSource": ["previous", "developing"], "tradeMode": ["rejection", "retest", "both"], "entryModel": ["touch", "imbalance", "pinbar", "any"]},
        {"valueAreaPct": [60, 70, 80], "awayAtr": [0.5, 1.0, 1.5, 2.0], "touchTolAtr": [0.0, 0.1, 0.25], "breakBufferAtr": [0.0, 0.1, 0.25]},
        {"slMode": ["atr", "points", "leg"], "slAtr": [0.5, 1.0, 1.5, 2.0], "tpMode": ["rr", "va_edge", "extension"], "rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]},
        {"tradeStartH": [3, 8, 9, 10], "tradeEndH": [11, 12, 14, 16], "maxTradesPerDay": [1, 2, 3, 5], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"useFibo": B, "fibMinPct": [38.2, 50.0, 61.8], "retestMaxBars": [10, 30, 100], "confirmBars": [2, 4, 8]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "sessionStartH": [8, 9], "rowTicks": [4, 8, 16, 40]},
    ],
    "voltbreak": [
        {"_tf": [15, 30, 60], "noisePct": [10.0, 20.0, 30.0, 40.0, 60.0], "tpUsd": [200.0, 400.0, 800.0, 1200.0], "slUsd": [500.0, 1000.0, 1500.0, 2000.0]},
        {"startHHMM": [830, 900, 1000], "endHHMM": [1200, 1430, 1500], "maxTrades": [1, 2, 3, 5], "avgLen": [10, 15, 20]},
        {"atrSource": ["Seansa 0:00–16:00 CT (ako vo videu)", "Denné sviečky burzy"], "atrLen": [7, 14, 20], "trendFilter": ["off", "with", "against"], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "vwapadx": [
        {"_tf": [1, 2, 3], "orEndHHMM": [845, 900, 930], "vwapAnchor": ["RTH 8:30 CT", "Polnoc CT"], "adxMin": [15.0, 20.0, 25.0, 30.0]},
        {"tpBars": [5, 10, 20, 40], "slBars": [3, 5, 10, 20], "maxTrades": [1, 2, 3, 5], "exitHHMM": [1200, 1400, 1555]},
        {"adxLen": [7, 14, 20], "trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "onbiasorb": [
        {"_tf": [5, 15, 30], "slPct": [10.0, 20.0, 30.0, 50.0], "rr": [0.5, 1.0, 1.5, 2.0, 3.0], "avgLen": [10, 15, 20]},
        {"minEntryHHMM": [845, 900, 930, 1000], "exitHHMM": [1100, 1300, 1430], "adxLen": [7, 14, 20], "adxMin": [15.0, 20.0, 25.0]},
        {"atrSource": ["Seansa 0:00–16:00 CT (ako vo videu)", "Denné sviečky burzy"], "atrLen": [7, 14, 20], "trendFilter": ["off", "with", "against"], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "sweepfvg": [
        {"_tf": [3, 5, 15], "liqPivotLen": [3, 5, 10], "liqMinStrength": [1, 2, 3], "sweepReclaim": B},
        {"breakBy": ["close", "wick"], "breakType": ["any", "choch", "bos"], "breakMaxBars": [10, 30, 60, 120], "structPivotLen": [2, 3, 5]},
        {"fvgMinAtr": [0.0, 0.1, 0.25, 0.5], "fvgPick": ["nearest", "largest", "first"], "entryLevel": ["edge", "mid"], "entryMaxBars": [10, 30, 60]},
        {"slBufferAtr": [0.0, 0.1, 0.25], "maxSlAtr": [2.0, 3.0, 5.0, 10.0], "tpMode": ["rr", "liquidity"], "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0]},
        {"startH": [3, 8, 9], "endH": [11, 12, 16], "maxTradesPerDay": [1, 2, 3, 5], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"liqUse15m": B, "liqUse60m": B, "liqUse240m": B, "liqMaxAgeHours": [24, 72, 168]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
    ],
    "sweepengulf": [
        {"_tf": [15, 30, 60, 240], "engulfMode": ["range", "body"], "prevCandle": ["opposite", "same", "any"], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"slMethod": ["candle", "atr"], "slBufferAtr": [0.0, 0.1, 0.25, 0.5], "atrMult": [0.5, 1.0, 1.5, 2.0, 3.0], "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "varev": [
        {"_tf": [5, 15, 30], "profileSource": ["previous", "current"], "profileSession": ["globex", "ny"], "valueAreaPct": [60.0, 70.0, 80.0]},
        {"maxBarsOutside": [3, 6, 12, 24], "requireVolDecline": B, "reclaimVolMult": [0.0, 1.0, 1.5], "requireEngulf": B},
        {"slBufferAtr": [0.0, 0.1, 0.25, 0.5], "tpMode": ["va", "poc", "rr"], "rrRatio": [0.5, 1.0, 1.5, 2.0], "minRR": [0.0, 0.5, 1.0]},
        {"startH": [3, 8, 9], "endH": [11, 12, 16], "maxTradesPerDay": [1, 2, 3, 5], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "fpc": [
        {"useS1": B, "useS2": B, "useS3": B, "useS4": B},
        {"useCont": B, "contWin": [5, 10, 15], "contTP": [5.0, 7.5, 10.0, 15.0, 25.0, 38.0], "contSL": [10.0, 15.0, 25.0, 40.0]},
        {"useRev": B, "tpMode": ["fixed", "fair"], "revTP": [7.5, 15.0, 25.0, 38.0], "revSL": [10.0, 15.0, 25.0, 40.0]},
        {"minPct": [50.0, 80.0, 100.0], "minDist": [15.0, 25.0, 40.0, 60.0], "useDisp": B, "useBos": B},
        {"maxLossRow": [1, 2, 3, 5], "maxTrades": [2, 5, 10], "bigBar": [15.0, 25.0, 40.0, 60.0], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"pmFair": ["open", "morning"], "newsMode": ["off", "auto", "always"], "useBias": B, "useNewsWin": B},
        {"useTrend": B, "trendPts": [20.0, 40.0, 60.0], "useMaxD": B, "maxDist": [100.0, 150.0, 250.0]},
        {"usePause": B, "pauseMin": [5, 10, 20], "useRevDel": B, "revDelay": [10, 20, 30]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "range": [
        {"_tf": [3, 5, 15], "lookbackBars": [10, 15, 20, 30], "boundaryMode": ["close", "extreme"], "entryMode": ["close", "retest", "continuation"]},
        {"maxWidthAtr": [1.5, 2.0, 2.5, 3.5], "minWidthAtr": [0.25, 0.5, 1.0], "maxRangeAgeBars": [20, 40, 80], "cooldownBars": [0, 3, 6]},
        {"breakBufferAtr": [0.0, 0.1, 0.25], "requireSecondClose": B, "minClosePosPct": [0, 50, 70], "maxTradesPerDay": [1, 2, 3, 5]},
        {"slMode": ["opposite", "mid", "range_pct", "atr"], "slBufferAtr": [0.0, 0.1, 0.25], "tpMode": ["rr", "measured", "atr"], "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0, 2.5]},
        {"useTradeWindow": B, "tradeStartH": [3, 8, 9], "tradeEndH": [11, 12, 16], "tradeDirection": ["Both", "Long only", "Short only"]},
        {"retestMaxBars": [5, 10, 20], "confirmMaxBars": [3, 5, 10], "measuredMult": [0.5, 1.0, 1.5], "tpAtrMult": [1.0, 2.0, 3.0]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "noa": [
        {"_tf": [3, 5, 15], "lookbackDays": [7, 10, 14, 20], "volMult": [0.75, 1.0, 1.25, 1.5], "gapAdjust": B},
        {"checkEvery": [15, 30, 60], "lastEntryMin": [180, 270, 360], "trailVwap": B, "hardStopPct": [0.5, 1.0, 2.0]},
        {"maxTradesPerDay": [1, 2, 3, 10], "tradeDirection": ["Both", "Long only", "Short only"], "weekdaysOnly": B},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "noaes": [
        {"_tf": [3, 5, 15], "lookbackDays": [7, 10, 14, 20], "volMult": [0.75, 1.0, 1.25, 1.5], "gapAdjust": B},
        {"checkEvery": [15, 30, 60], "lastEntryMin": [180, 270, 360], "trailVwap": B, "hardStopPct": [0.5, 1.0, 2.0]},
        {"maxTradesPerDay": [1, 2, 3, 10], "tradeDirection": ["Both", "Long only", "Short only"], "weekdaysOnly": B},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "noamgc": [
        {"_tf": [3, 5, 15], "lookbackDays": [7, 10, 14, 20], "volMult": [0.75, 1.0, 1.25, 1.5], "gapAdjust": B},
        {"checkEvery": [15, 30, 60], "lastEntryMin": [180, 270, 360], "trailVwap": B, "hardStopPct": [0.5, 1.0, 2.0]},
        {"maxTradesPerDay": [1, 2, 3, 10], "tradeDirection": ["Both", "Long only", "Short only"], "weekdaysOnly": B},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "nyva": [   # NY VA BREAKOUT (23. 10.): profil prvej hodiny NY, prieraz z value area
        {"rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], "slBufferTicks": [0, 4, 10, 20], "confirmCloses": [1, 2, 3], "entryMode": ["close", "retest"]},
        {"rangeEndH": [10, 11], "rangeEndM": [0, 15, 30, 45], "entryEndH": [11, 12, 13, 16], "maxTradesPerDay": [1, 2, 3]},
        {"profileRows": [30, 60, 120], "valueAreaPct": [60.0, 70.0, 80.0], "useVwap": B, "retestBars": [5, 10, 20]},
        {"maxSlPoints": [0.0, 40.0, 60.0, 100.0], "maxSlAtr": [0.0, 3.0, 5.0, 8.0], "slCapMode": ["skip", "cap"], "vaMaxPoints": [0.0, 100.0, 150.0, 250.0]},
        {"trendFilter": ["off", "with"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"allowLong": B, "allowShort": B, "vaMinPoints": [0.0, 20.0, 40.0], "_tf": [3, 5]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ],
    "nyvaes": [   # NY VA BREAKOUT (23. 10.): profil prvej hodiny NY, prieraz z value area
        {"rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], "slBufferTicks": [0, 2, 4, 8], "confirmCloses": [1, 2, 3], "entryMode": ["close", "retest"]},
        {"rangeEndH": [10, 11], "rangeEndM": [0, 15, 30, 45], "entryEndH": [11, 12, 13, 16], "maxTradesPerDay": [1, 2, 3]},
        {"profileRows": [30, 60, 120], "valueAreaPct": [60.0, 70.0, 80.0], "useVwap": B, "retestBars": [5, 10, 20]},
        {"maxSlPoints": [0.0, 9.0, 13.0, 22.0], "maxSlAtr": [0.0, 3.0, 5.0, 8.0], "slCapMode": ["skip", "cap"], "vaMaxPoints": [0.0, 22.0, 33.0, 55.0]},
        {"trendFilter": ["off", "with"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"allowLong": B, "allowShort": B, "vaMinPoints": [0.0, 4.0, 9.0], "_tf": [3, 5]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ],
    "nocpon": [
        {"nightEntryM": [30, 40, 45, 50, 55], "nightExitH": [0, 1, 2, 3, 4, 6, 9], "nightExitM": [0, 30], "_tf": [5, 15]},
        {"useMonday": B, "monEntryM": [30, 35, 45], "monExitH": [14, 15], "monExitM": [0, 30, 55]},
        {"useTrend": B, "smaLen": [50, 75, 100, 150, 200], "closeRefH": [15, 16], "closeRefM": [0, 55]},
        {"skipRoll": B, "rollFromDay": [5, 7, 9, 11], "rollToDay": [14, 16, 18], "stopPct": [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "tks": [
        {"loLevel": [5, 10, 15, 20, 25, 30], "hiLevel": [70, 75, 80, 85, 90, 95], "nConf": [2, 3, 4, 5], "rrRatio": [0.5, 0.6, 0.75, 1.0]},
        {"rrRatio": [0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0], "pivLen": [2, 3, 4, 5, 6, 8], "lookbackDays": [7, 10, 14, 20], "_tf": [2, 3, 5]},
        {"entryStartMin": [0, 15, 30, 45, 60], "entryEndMin": [240, 270, 300, 330, 360, 390], "pauseFromMin": [0, 120, 150], "pauseToMin": [0, 180, 210]},
        {"slMode": ["swing", "atr", "points"], "slAtrMult": [2.0, 3.0, 4.0, 5.0], "slPoints": [60.0, 80.0, 100.0, 150.0], "atrLen": [14, 28]},
        {"maxSlPoints": [0.0, 100.0, 150.0, 200.0, 300.0], "maxSlAtr": [0.0, 3.0, 5.0, 8.0], "maxTradesPerSession": [0, 1, 2, 3, 5],
         "tradeDirection": ["Both", "Long only", "Short only"]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5]},
    ],
    "silverbullet": [
        {"sbStartH": [3, 9, 10, 14], "sbEndH": [11, 12, 15, 16], "liqFromH": [0, 2, 8], "maxTradesPerDay": [1, 2, 3]},
        {"liqPivotLen": [2, 3, 5], "useSwings": B, "useRangeHL": B, "sweepReclaim": B},
        {"fvgMinAtr": [0.0, 0.1, 0.25, 0.5], "fvgMaxBars": [5, 10, 20], "requireMss": B, "entryLevel": ["edge", "mid"]},
        {"tpMode": ["liquidity", "rr"], "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "minRR": [0.5, 1.0, 1.5], "slBufferAtr": [0.0, 0.1, 0.25]},
        {"_tf": [1, 3, 5], "maxSlAtr": [0.0, 1.0, 2.0, 3.0], "tradeDirection": ["Both", "Long only", "Short only"], "entryType": ["limit", "market"]},
        {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
        {"entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5], "weekdaysOnly": B, "atrLen": [7, 14, 28]},
    ],
}
# M2 (28. 10. 2026, do piatka 30. 10. 18:00): tá istá mriežka na ES, MNQ, MGC a 6E — všetky TF, kvalita M2
# (rozšírenie: potvrdenie hneď, impulz, M2 na extréme, riziko v ATR), hĺbka limitky, RR, trend EMA, okno
_M2 = [
    {"_tf": [1, 2, 3, 5, 10, 15], "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "slTicks": [0, 1, 2, 4], "entryPct": [0, 25, 50]},
    {"confirmMaxBars": [0, 1, 2, 3, 5, 10], "minImpulseAtr": [0.0, 0.3, 0.5, 0.8, 1.2], "swingBars": [0, 3, 5, 10, 20],
     "cancelAtTarget": B},
    {"minRiskAtr": [0.0, 0.3, 0.5, 0.8, 1.2], "maxRiskAtr": [0.0, 1.5, 2.5, 4.0], "slBufferAtr": [0.0, 0.1, 0.25, 0.5],
     "limitMaxBars": [0, 3, 5, 10, 30]},
    {"useEmaTrend": B, "ema1": [9, 20, 50], "ema2": [50, 100, 200], "ema5": [600, 1200, 2400]},
    {"useWindow": B, "entryStartH": [2, 3, 8, 9], "entryEndH": [11, 12, 15, 16], "maxTradesPerDay": [0, 2, 5, 10]},
    {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
    {"allowLong": B, "allowShort": B, "emaNeedClose": B, "entryStartM": [0, 30]},
    {"entryConfirm": ["none", "imbalance", "pinbar", "any"], "confirmBars": [2, 3, 5], "limitOffsetPct": [25, 50, 75]},
]
for _k in ("m2", "m2mnq", "m2mgc", "m2eur"):
    GROUPS[_k] = _M2

# Roboquant šablóny (týždeň 31. 10.–8. 11. 2026): 8 stratégií na MNQ, ES, MGC. Spoločné skupiny: trend / volatilita
# a typ vstupu (market / limit, IBS imbalance / pin bar). Bez trailingu a konca seansy, okrem stratégií, kde je výstup
# v čase podstata (Sigma 16:00, NQ Precision 8 min, T-MR streda — ako NOA / NOC + PONDELOK).
_TRF = {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]}
_ENT = {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
        "confirmBars": [2, 3, 5]}
_RQ = {
    "orb15": ({"closeAtEnd": False}, 5, [
        {"_tf": [3, 5, 15], "orMinutes": [5, 15, 30, 60], "rr": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "maxTradesPerDay": [1, 2, 3]},
        {"useDailyBias": B, "useWickFilter": B, "maxWickPct": [20.0, 35.0, 50.0, 70.0], "lastEntry": [1100, 1200, 1400, 1600]},
        {"allowLong": B, "allowShort": B, "orStart": [930, 945, 1000], "targetMode": [0]},
        _TRF, _ENT]),
    "flashorb": ({"useEodClose": False, "activateTrailing": False}, 15, [
        {"_tf": [5, 15, 30, 60], "targetHour": [13, 14, 15, 16], "targetMinute": [0, 30], "riskReward": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]},
        {"utcOffset": [0], "dayFilter": B, "tradeMonday": B, "tradeFriday": B},
        {"targetHour": [7, 8, 9, 13, 14], "targetMinute": [0, 15, 30, 45], "_tf": [5, 15]},
        _TRF, _ENT]),
    "sigma": ({}, 5, [
        {"_tf": [3, 5, 15, 30], "nSigmaDays": [7, 10, 14, 20, 30], "bandMult": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], "useVwap": B},
        {"slPct": [0.0, 0.25, 0.5, 0.75, 1.0, 1.5], "bandMult": [0.75, 1.0, 1.25, 1.5], "useCloseAtEnd": [True]},
        _TRF, _ENT]),
    "nqprec": ({}, 1, [
        {"atrSlMult": [0.5, 1.0, 1.5, 2.2, 3.0], "atrTpMult": [0.2, 0.3, 0.5, 0.75, 1.0], "closeAfterMin": [3, 5, 8, 15, 30], "useTimeClose": B},
        {"useFilters": B, "rvolMin": [0.0, 0.3, 0.5, 0.8], "rvolMax": [1.0, 1.5, 2.5, 20.0], "regimeMin": [0.0, 0.5, 0.8, 1.0]},
        {"rangeEnd": [935, 945, 1000], "triggerTime": [945, 950, 1000, 1015, 1030], "useTriggerTime": B, "tradeUntil": [1030, 1100, 1200]},
        {"_tf": [1, 2, 3, 5], "atrPeriod": [7, 14, 30], "regimeMax": [1.5, 2.5, 5.0, 20.0], "atrRegimeLen": [20, 50, 100]},
        _TRF, _ENT]),
    "lliq": ({}, 5, [
        {"_tf": [1, 3, 5, 15], "slType": [0, 1], "tpType": [0, 1, 2], "riskReward": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]},
        {"slAtrMult": [0.5, 1.0, 1.5, 2.0, 3.0], "tpAtrMult": [0.5, 0.75, 1.0, 1.5, 2.0, 3.0], "swingLookback": [3, 5, 10, 20], "atrLength": [14, 50]},
        {"sessionStart": [200, 800, 930, 1300], "sessionEnd": [500, 930, 1100, 1600, 1900], "lsStart": [930, 1000, 1600, 1915], "lsEnd": [1200, 1600, 2000, 2345]},
        {"maxIfvgAgeHours": [2, 6, 12, 24], "useDayFilter": B, "tradeMon": B, "tradeFri": B},
        _TRF, _ENT]),
    "tmr": ({}, 15, [
        {"entryDay": [1, 2], "entryHour": [13, 14, 15, 17, 20], "exitDay": [2, 3, 4, 5], "exitHour": [14, 17, 20]},
        {"requireRedFriday": B, "stopPct": [0.0, 1.0, 2.0, 3.0], "_tf": [15, 60]},
        _TRF]),
    "wpr": ({}, 15, [
        {"_tf": [1, 3, 5, 15, 30, 60], "wprLen": [5, 9, 14, 21, 30], "entryLevel": [-98.0, -95.0, -90.0, -85.0, -80.0], "exitMode": [0, 1, 2]},
        {"exitLevel": [-60.0, -50.0, -30.0, -20.0, -10.0], "stopPct": [0.0, 0.25, 0.5, 1.0, 2.0], "wprLen": [9, 14, 21]},
        _TRF, _ENT]),
    "ivb": ({"flattenEod": False}, 5, [
        {"_tf": [3, 5, 15], "maxContractionRatio": [0.6, 0.8, 0.9, 1.0, 1.2, 2.0], "volSurgeMult": [0.8, 1.0, 1.1, 1.5, 2.0], "maxTradesPerDay": [1, 2, 3, 5]},
        {"slAtrMult": [1.0, 1.5, 2.0, 3.0, 4.0], "tpAtrMult": [0.5, 1.0, 1.5, 2.0, 3.0, 4.0], "atrPeriod": [14, 30], "direction": [0, 1, 2]},
        {"ibRangeLookback": [5, 10, 20], "volAvgBars": [5, 10, 20, 50], "sessionEnd": [945, 1000, 1030], "entryWindowEnd": [1100, 1200, 1400, 1600]},
        _TRF, _ENT]),
}
_RQ_MARKET = {"": ("mnq_databento", "MNQ/USD"), "es": ("es_databento", "ES/USD"), "mgc": ("mgc_databento", "MGC/USD")}
for _b, (_ne, _tf, _groups) in _RQ.items():
    for _suf, _ins in _RQ_MARKET.items():
        _k = _b + _suf
        INSTR[_k] = _ins
        NO_EXIT[_k] = dict(_ne)
        BASE[_k] = (f"/Users/martin/IBS/.nightsearch/base_{_k}.json", _tf)
        GROUPS[_k] = _groups

# MTK ORB (11. 11. 2026): ORB 15 na zlate len v smere gapu, OR nie široký, stop order na hranici; ladí sa na všetkých
# dátach MGC (PERIODS) — `orStart` 820 = otvorenie COMEX.
INSTR["mtkorb"] = ("mgc_databento", "MGC/USD")
NO_EXIT["mtkorb"] = {"closeAtEnd": False}
BASE["mtkorb"] = ("/Users/martin/IBS/.nightsearch/base_mtkorb.json", 5)
GROUPS["mtkorb"] = [
    {"_tf": [1, 3, 5], "orMinutes": [5, 10, 15, 30], "rr": [0.5, 0.75, 1.0, 1.5, 2.0], "gapFilter": [0, 1]},
    {"maxOrWidthMult": [0.0, 1.0, 1.25, 1.5, 2.0], "orWidthLookback": [20, 60, 120], "firstBreakOnly": B, "entryAtLevel": B},
    {"useDailyBias": B, "useWickFilter": B, "maxWickPct": [20.0, 35.0, 50.0, 70.0], "lastEntry": [1100, 1200, 1400, 1600]},
    {"allowLong": B, "allowShort": B, "orStart": [820, 930, 945], "maxTradesPerDay": [1, 2]},
    _TRF, _ENT]

# MTK RANGE 1.0 (va80, 7. 11. 2026): pravidlo 80 % na MNQ 1m; výstup v čase je podstata (intraday), RR ≥ 0,5 vždy (minRR),
# hranica 150 obch/rok ako všade (smernica); viac obchodov dávajú requireOpenOutside / maxTradesPerDay
NO_EXIT["va80"] = {}
BASE["va80"] = ("/Users/martin/IBS/.nightsearch/base_va80.json", 1)
GROUPS["va80"] = [
    {"requireOpenOutside": B, "maxTradesPerDay": [1, 2, 3, 4], "returnBarMin": [5, 15, 30], "lastEntry": [1200, 1300, 1400, 1500]},
    {"vaPct": [60.0, 65.0, 70.0, 75.0, 80.0], "vaBinPct": [0.02, 0.03, 0.04, 0.05], "vaMethod": ["expand", "rank"], "returnBarMin": [5, 15, 30]},
    {"tpMode": ["rr", "opp", "poc", "mid"], "rrRatio": [1.0, 1.5, 2.0, 2.5, 3.0], "minRR": [0.5, 1.0, 1.5, 2.0], "slBufferVa": [0.0, 0.05, 0.1, 0.25]},
    {"tpMode": ["rr"], "rrRatio": [1.5, 2.0, 2.5, 3.0], "exitTime": [1400, 1500, 1555], "maxStopAtr": [0.0, 0.3, 0.5]},
    {"maxStopAtr": [0.0, 0.3, 0.4, 0.5, 0.75], "allowLong": B, "allowShort": B, "minOpenOutside": [0.0, 0.1, 0.25, 0.5]},
    {"_tf": [1, 3], "maxTradesPerDay": [2, 3, 5], "requireOpenOutside": B},
    _TRF, _ENT]
# MTK ZONE (10. 11. 2026): SD zóny z 5m / 15m (SD vzor, vrchol volume profilu, nárast klasického objemu, min. potvrdení),
# vstupy limit / IBS / pin bar na grafe 2m–5m; predloha Pine VP SD ZÓNY 50. Testuje sa len na Mac mini (gl_hub_off).
NO_EXIT["mtkzone"] = {}
BASE["mtkzone"] = ("/Users/martin/IBS/.nightsearch/base_mtkzone.json", 3)
GROUPS["mtkzone"] = [
    {"_tf": [2, 3, 5], "zoneTf1": [5, 15], "minConf": [1, 2, 3], "maxZones": [1, 2, 3, 5]},
    {"useLimit": B, "useIBS": B, "usePin": B, "modelBars": [10, 20, 30, 60]},
    {"impMult": [1.0, 1.5, 2.0], "volSpike": [1.5, 2.0, 2.5, 3.0], "impMultVol": [0.3, 0.5, 0.8], "baseMax": [1, 2, 3]},
    {"rrRatio": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0], "slBufTicks": [0, 4, 8, 16], "minScore": [30.0, 40.0, 50.0, 60.0], "maxRiskTicks": [0, 80, 160, 240]},
    {"vwapMode": ["off", "with", "against"], "vwapAnchor": ["day", "ny"], "useSess": B, "minEntryScore": [0.0, 50.0, 70.0]},
    {"trendFilter": ["off", "with", "against"], "trendEmaLen": [50, 100, 200], "trendTF": [0, 15, 60], "volFilter": ["off", "low", "high"]},
    {"useClassic": B, "usePeak": B, "useVolSurge": B, "peakMin": [2.0, 3.0, 5.0]},
    {"useZ2": B, "zoneTf2": [15, 30], "lookback": [30, 50, 100], "baseBodyMax": [0.4, 0.6, 0.8]},
]

MIN_TRADES_KEY: dict = {}   # 7. 11.: používateľ — smernica platí, 150 obch/rok aj pre MTK RANGE

# MYM — Micro Dow (12. 11. 2026, príkaz z MacBooku): 8 stratégií ladiť odznova na MYM, potom smernica. Podklady iCloud
# MYM-PRIESKUM/PRECITAJ_MA.md: v ATR vyzerá MYM ako MNQ / ES, pásmo šumu NOA ~0,65 × MNQ (hardStopPct ~0,28 %), Dow je
# najmenej trendový, v noci malý objem (IBS EZ len RTH 9:30–16:00 NY).
_MYM = ("mym_databento", "MYM/USD")
for _k in ("ibsentrymym", "noamym", "wprmym", "sweepengulfmym", "tmrmym", "lliqmym", "sigmamym", "nocponmym"):
    INSTR[_k] = _MYM
NO_EXIT["ibsentrymym"] = {"closeAtSessionEnd": False, "enableTrailing": False, "sess1On": False}   # len RTH
BASE["ibsentrymym"] = ("/Users/martin/IBS/.nightsearch/base_ibsentrymym.json", 3)
GROUPS["ibsentrymym"] = [g for g in GROUPS["ibsentryes"] if "sess1On" not in g]   # IBS EZ nemá obaly vstupov (_ENT)
NO_EXIT["noamym"] = {}
BASE["noamym"] = ("/Users/martin/IBS/.nightsearch/base_noamym.json", 5)
GROUPS["noamym"] = [dict(g, hardStopPct=[0.2, 0.28, 0.4, 0.6]) if "hardStopPct" in g else g for g in GROUPS["noaes"]]
for _b in ("wpr", "tmr", "lliq", "sigma"):
    _ne, _tf, _groups = _RQ[_b]
    NO_EXIT[_b + "mym"] = dict(_ne)
    BASE[_b + "mym"] = (f"/Users/martin/IBS/.nightsearch/base_{_b}mym.json", _tf)
    GROUPS[_b + "mym"] = _groups
NO_EXIT["sweepengulfmym"] = {}
BASE["sweepengulfmym"] = ("/Users/martin/IBS/.nightsearch/base_sweepengulfmym.json", 240)
GROUPS["sweepengulfmym"] = GROUPS["sweepengulf"]
NO_EXIT["nocponmym"] = {}
BASE["nocponmym"] = ("/Users/martin/IBS/.nightsearch/base_nocponmym.json", 5)
GROUPS["nocponmym"] = GROUPS["nocpon"]
# krok 8 (iný trh): Dow CFD v archíve nie je — glnas100 krok preskočí
FOLDER["mym_databento"] = "DOW"
BASE_LABEL["mym_databento"] = "MYM"

# BTC — BTCUSDT.P Binance futures (13. 11. 2026, používateľ: výber podľa štúdia grafu BTC, štart po nedeľných testoch MYM).
# Podklady iCloud BTC-ANALYZA: BTC je 2–3× volatilnejší ako MNQ (pomer mediánu 5m rozsahu v cene ×7,04), najživšie
# otvorenie NY, krátke TF sa vracajú; poplatok Binance maker 0,02 % na stranu (limit) — preto FEE_KEY.
_BTC = ("btcusdt_binance", "BTC/USDT:USDT")
_BTC_K = 7.04
def _btc_scale(groups, fields):
    out = []
    for g in groups:
        g = dict(g)
        for f in fields:
            if f in g:
                g[f] = [round(v * _BTC_K, 1) for v in g[f]]
        out.append(g)
    return out
for _b, _tf in (("noa", 5), ("dailyopen", 60), ("onbiasorb", 15), ("flashorb", 15), ("silverbullet", 5), ("range", 3),
                ("tmr", 15), ("sweepengulf", 240)):
    _k = _b + "btc"
    INSTR[_k] = _BTC
    NO_EXIT[_k] = dict(NO_EXIT.get(_b, {}))
    BASE[_k] = (f"/Users/martin/IBS/.nightsearch/base_{_k}.json", _tf)
    GROUPS[_k] = list(GROUPS[_b])
GROUPS["dailyopenbtc"] = _btc_scale(GROUPS["dailyopen"], ("breakPts", "slPts", "tpPts"))   # body MNQ → BTC
GROUPS["noabtc"] = [dict(g, hardStopPct=[0.5, 1.0, 2.0, 3.0]) if "hardStopPct" in g else g for g in GROUPS["noa"]]
GROUPS["tmrbtc"] = [dict(g, stopPct=[0.0, 1.0, 2.0, 3.0, 5.0]) if "stopPct" in g else g for g in GROUPS["tmr"]]
FOLDER["btcusdt_binance"] = "BTC"
BASE_LABEL["btcusdt_binance"] = "BTC"
# krok 8 (iný trh): ETH má inú cenovú hladinu (body nesedia) a Dukascopy BTC má diery — krok sa pre BTC preskočí
# EUR — 6E CME Euro FX (15. 11. 2026, používateľ: smernica pre EUR, štart po BTC ne 22. 11.). Podklady iCloud EUR-PRIESKUM:
# EUR sa vracia späť (autokorelácia 5m–60m −0,017), živé okná London 2:00–5:00 a NY 8:00–11:00 NY, Ázia mŕtva; dáta 6E
# čisté od 2016 (2010–2015 chybné ceny) → ladenie 2016-01 → 2021-09, päť referenčných okien 2021–2026 = čisté overenie (raz).
# Tickové prahy z MNQ ×0,12 (medián 5m rozsahu 6 vs 50 tickov); ATR prahy sa prispôsobia samy.
_EUR = ("6e_databento", "6E/USD")
_EUR_WINDOWS = [("16", "2016-01-01", "2016-10-01")] + [(f"{y % 100:02d}/{(y + 1) % 100:02d}", f"{y}-10-01", f"{y + 1}-10-01")
                                                       for y in range(2016, 2021)]
_EUR_OOS = [("21/22", "2021-10-01", "2022-10-01"), ("22/23", "2022-10-01", "2023-10-01"), ("23/24", "2023-10-01", "2024-09-04"),
            ("24/25", "2024-09-04", "2025-09-04"), ("25/26", "2025-09-04", "2026-09-04")]
EUR_KEYS = ("asiasweepeur", "mtkzoneeur", "lliqeur", "silverbulleteur", "wpreur", "ibsentryeur", "sweepengulfeur")
for _k in EUR_KEYS:
    INSTR[_k] = _EUR
    PERIODS[_k] = ("20160101-20211001", "20211001-20260904", _EUR_WINDOWS, 5.75, _EUR_OOS)
    _tf = {"mtkzoneeur": 3, "ibsentryeur": 3, "wpreur": 15, "sweepengulfeur": 240}.get(_k, 5)
    _tfs = {3: "3m", 5: "5m", 15: "15m", 240: "4h"}[_tf]
    BASE[_k] = (f"/Users/martin/IBS/tradebot/strategies/{_k}/configs/6e_databento_{_tfs}.json", _tf)
NO_EXIT["asiasweepeur"] = {"useExitTime": False}
GROUPS["asiasweepeur"] = [
    {"_tf": [3, 5, 15], "asiaStartH": [18, 19, 20], "sweepEndH": [4, 5, 6], "entryEndH": [6, 8, 10]},
    {"sweepMin": [A(0.0), A(0.1), A(0.25)], "maxSweep": [A(0.0), A(1.0), A(2.0)], "requireReclaim": B, "entryBars": [6, 12, 24]},
    {"slMode": ["sweep", "signal", "atr"], "slBuffer": [A(0.0), A(0.1), A(0.2), A(0.5)], "tpMode": ["rr", "range", "mid"],
     "rrRatio": [0.5, 0.75, 1.0, 1.5, 2.0]},
    {"entryModel": ["imbalance", "pinbar", "any", "close"], "imbMinSize": [A(0.0), A(0.05), A(0.15)], "maxTradesPerDay": [1, 2],
     "tradeDirection": ["Both", "Long only", "Short only"]},
    {"entryOrderType": ["market", "limit"], "rangeMaxPct": [{"value": 0.0, "unit": "pct"}, {"value": 0.3, "unit": "pct"},
                                                            {"value": 0.5, "unit": "pct"}], "weekdaysOnly": B, "atrLen": [7, 14, 28]},
    _TRF]
NO_EXIT["mtkzoneeur"] = {}
GROUPS["mtkzoneeur"] = [dict(g, slBufTicks=[0, 1, 2, 3], maxRiskTicks=[0, 10, 20, 30]) if "slBufTicks" in g else g
                        for g in GROUPS["mtkzone"]] + [
    {"useSess": B, "sessStart": [200, 300, 800], "sessEnd": [500, 1100, 1200, 1600]}]
NO_EXIT["lliqeur"] = dict(_RQ["lliq"][0])
GROUPS["lliqeur"] = [dict(g, sessionStart=[0, 200, 800, 1300], sessionEnd=[500, 800, 1100, 1600], lsStart=[200, 300, 800, 1000],
                          lsEnd=[500, 800, 1100, 1200]) if "sessionStart" in g else g for g in _RQ["lliq"][2]]
NO_EXIT["silverbulleteur"] = dict(NO_EXIT["silverbullet"])
GROUPS["silverbulleteur"] = GROUPS["silverbullet"]
NO_EXIT["wpreur"] = dict(_RQ["wpr"][0])
GROUPS["wpreur"] = [dict(g, stopPct=[0.0, 0.1, 0.2, 0.3, 0.5]) if "stopPct" in g else g for g in _RQ["wpr"][2]]
NO_EXIT["ibsentryeur"] = {"closeAtSessionEnd": False, "enableTrailing": False}
GROUPS["ibsentryeur"] = GROUPS["ibsentryes"]
NO_EXIT["sweepengulfeur"] = {}
GROUPS["sweepengulfeur"] = GROUPS["sweepengulf"]
# krok 8 (iný trh) = EURUSD CFD Dukascopy (OTHER_MARKET["6e_databento"]); priečinok EURUSD (FOLDER)
# IB RETRACE (21. 11. 2026, používateľ: ladiť na zlate, MNQ a MYM do ne 29. 11. 6:00, filtre podľa uváženia; výnimka
# z počtu obchodov schválená — 1 obchod za deň). Východisko = úrovne zo štatistiky IB (tester.initial_balance, len do
# 2025-09): stop ≈ 70.–80. percentil max retracementu, limitka 0,25 IB; long a short zvlášť.
IBRET_KEYS = ("ibret", "ibretmgc", "ibretmym")
INSTR["ibretmgc"] = ("mgc_databento", "MGC/USD")
INSTR["ibretmym"] = _MYM
_IBR_LVL = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35]
_IBR_SL = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1]
_IBR_RR = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
for _k in IBRET_KEYS:
    BASE[_k] = (f"/Users/martin/IBS/.nightsearch/base_{_k}.json", 5)
    NO_EXIT[_k] = {"closeAtEnd": False}   # pravidlo: bez konca seansy — len stop a cieľ
    MIN_TRADES_KEY[_k] = 80   # výnimka používateľa 21. 11. (najviac 1 obchod za deň)
    GROUPS[_k] = [
        {"entryRetr": _IBR_LVL, "slRetr": _IBR_SL, "rr": _IBR_RR},
        {"shortEntryRetr": _IBR_LVL, "shortSlRetr": _IBR_SL, "shortRr": _IBR_RR},
        {"breakOn": ["wick", "close", "body"], "breakTo": [1055, 1125, 1155, 1225, 1255],
         "lastEntry": [1130, 1230, 1330, 1430, 1530], "slBufferTicks": [0, 4, 8]},
        {"minIbRel": [0.0, 0.5, 0.7, 0.85], "maxIbRel": [0.0, 1.3, 1.6, 2.0, 2.5], "ibAvgDays": [10, 20, 40],
         "biasFilter": ["off", "with", "against"]},
        {"tradeMon": B, "tradeTue": B, "tradeWed": B, "tradeThu": B, "tradeFri": B},
        {"entryMode": ["pullback", "breakout"], "tradeDirection": ["Both", "Long only", "Short only"],
         "minIbPct": [0.0, 0.2, 0.4], "maxIbPct": [0.0, 1.0, 1.5, 2.5]},
        _TRF,
        {"entryOrderType": ["market", "limit"], "limitOffsetPct": [25, 50, 75], "entryConfirm": ["none", "imbalance", "pinbar", "any"],
         "confirmBars": [2, 3, 5]},
    ]
# 15. 11. 2026 používateľ: riziko 100 $ skúšané a zamietnuté (na 6E by vypadla väčšina obchodov) — BTC aj EUR na 1 kontrakte
FEE_KEY = {k: 2e-4 for k, v in INSTR.items() if v == _BTC}


def fee(key) -> float:
    """Poplatok na stranu pre stratégiu (BTC maker 0,02 %, inak FEE)."""
    return FEE_KEY.get(key, FEE)

MAX_PER_GROUP = 160
# Ktoré stratégie sa práve testujú (gl_active.txt, jedna na riadok); bez súboru všetky.

def valid(key: str, p: dict) -> bool:
    """Kombinácia, ktorú config stratégie prijme (17. 11. 2026: DAILY OPEN / SILVER BULLET BTC posielali na hub
    neplatné okná — čas úrovne po začiatku okna, koniec pred začiatkom, žiadny zdroj likvidity)."""
    from tradebot.core.config import ConfigError
    from tradebot.strategies import get_spec
    try:
        get_spec(key).config_cls.from_dict({k: v for k, v in p.items() if not k.startswith("_")})
        return True
    except ConfigError:
        return False

def active() -> list:
    f = ROOT / "gl_active.txt"
    if f.exists():
        ks = [l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")]
        return [k for k in ks if k in GROUPS]
    return list(GROUPS)


def evaluate(key: str, params: dict, timerange: str) -> dict:
    import allcore as A
    import pandas as pd
    from tradebot.core import load_profile
    from tradebot.core.types import INSTRUMENTS
    from tradebot.adapters.multicharts.emulator import emulate, rows_from_trades, summarize
    from tester.webapp.results import timerange_ms
    K = instr(key)[0]; inst = INSTRUMENTS[K]
    p = {k: v for k, v in params.items() if k != "_tf"}
    p.update({"_strategy": key, "_instrument": K})
    one_contract(key, p)
    fn = A.TMP / f"gl{os.getpid()}.json"; fn.write_text(json.dumps(p))
    cfg, _ = load_profile(fn, engine="multicharts")
    f, t = timerange_ms(timerange)
    res, _ = emulate(cfg, inst, A.m1(K), int(params["_tf"]), from_ms=f, to_ms=t, fee=fee(key))
    rows = rows_from_trades(res.trades, inst, fee(key), 1.0)
    s, _ = summarize(rows, 60000.0, res, currency="USD")
    out = {k: s.get(k) for k in ("trades", "wins", "winrate", "pnl_abs", "profit_factor", "max_drawdown_abs")}
    if timerange == is_tr(key):
        yrs = {}
        for name, a, b in windows(key):
            ys = [r["profit_abs"] for r in rows if a <= str(r["open_date"])[:10] < b]
            gw, gl = sum(x for x in ys if x > 0), -sum(x for x in ys if x < 0)
            yrs[name] = {"trades": len(ys), "pf": round(gw / gl, 3) if gl > 0 else (9.0 if gw > 0 else 0.0), "pnl": round(sum(ys), 1)}
        out["years"] = yrs
    return out


def score(r: dict, key: str | None = None) -> float:
    if not r or not r.get("trades"):
        return -1e9
    pf = min(r["profit_factor"] or 0.0, 4.0)
    per_year = r["trades"] / years(key)
    if per_year < MIN_TRADES_KEY.get(key, MIN_TRADES_YEAR):   # pod 150 obch/rok nikdy (používateľ: „neísť pod túto hranicu“)
        return -100.0 + per_year / 1000.0   # len aby sa dalo stúpať k viac obchodom
    s = pf
    ys = [y["pf"] for y in r.get("years", {}).values()]
    if ys:
        worst = min(ys)
        # ES = stabilný druhý trh k NQ (používateľ 23. 10.): najslabší rok váži viac ako celkové PF
        w, cap = (1.0, 1.5) if _stable() else (0.3, 1.3)
        s += w * min(worst, cap) - 2.0 * max(0.0, 0.9 - worst)
    return s


# Stratégie zmazané z testovania a stránky (stav v gl_state.json ostáva, nič sa nemaže)
REMOVED = {"nyva", "va80"}   # 25. 10. NY VA BREAKOUT; 8. 11. MTK RANGE — nemá edge (používateľ), mimo testov aj stránky
# 21. 11. 2026 používateľ: preč zo stránky aj z webapp stratégie s červeným Sortino (< 2) a triedou C v audite
REMOVED |= {"wpr", "wprmym", "lliqes", "lliqmym", "nqprec", "onbiasorbbtc", "silverbulletbtc", "sweepengulfmym",
            "dailyopenbtc", "tmrbtc"}

STABLE_KEYS = {"ibsentryes", "nyva", "nyvaes", "sdeur"}
_STABLE = None


def _stable() -> bool:
    global _STABLE
    if _STABLE is None:
        _STABLE = bool(active()) and set(active()) <= STABLE_KEYS
    return _STABLE


def passes_is(r: dict, key: str | None = None) -> bool:
    ys = [y["pf"] for y in r.get("years", {}).values()]
    mt = MIN_TRADES_KEY.get(key, MIN_TRADES_YEAR)
    return bool(r) and (r["profit_factor"] or 0) >= 1.3 and r["trades"] / years(key) >= mt and ys and min(ys) >= 0.9


def work(args):
    key, params = args
    try:
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            return key, params, evaluate(key, params, is_tr(key)), None
    except Exception as e:
        return key, params, None, f"{type(e).__name__}: {e}"[:300]


def workers() -> int:
    try:
        return max(1, int((ROOT / "gl_workers.txt").read_text().strip()))
    except Exception:
        return 6


def main() -> None:
    # pozastavené používateľom („pozastav testovanie“) — aj po reštarte ostať stáť, kým nepovie „zapni“
    if (ROOT / "gl_paused").exists() if "ROOT" in globals() else (G.ROOT / "gl_paused").exists():
        import signal
        os.kill(os.getpid(), signal.SIGSTOP)
    sf = ROOT / "gl_state.json"
    st = json.loads(sf.read_text()) if sf.exists() else {}
    for key, (prof, tf) in BASE.items():
        if key not in st:
            p = {k: v for k, v in json.load(open(prof)).items() if not k.startswith("_")}
            p.update(NO_EXIT[key]); p["_tf"] = tf
            st[key] = {"best": p, "best_r": None, "combos": 0, "seen": [], "candidates": [], "round": 0}
    seen = {k: set(v["seen"]) for k, v in st.items()}

    def save():
        for k in st:
            st[k]["seen"] = sorted(seen[k])
        tmp = sf.with_suffix(".tmp"); tmp.write_text(json.dumps(st, ensure_ascii=False)); tmp.replace(sf)  # atómovo — ranné nahrávanie číta počas behu

    def run(batch):
        with ProcessPoolExecutor(workers()) as ex:
            for key, params, r, err in ex.map(work, batch):
                with open(ROOT / f"gl_{key}.jsonl", "a") as fh:
                    fh.write(json.dumps({"p": params, "r": r, "err": err, "t": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False) + "\n")
                yield key, params, r

    def plateau(key, best, r_best, group):
        """Susedné hodnoty každého číselného parametra skupiny (± jeden krok): PF ≥ 80 % víťaza?"""
        batch = []
        for name, vals in group.items():
            if name not in best or isinstance(vals[0], (bool, str)) or best[name] not in vals:
                continue
            i = vals.index(best[name])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    q = dict(best); q[name] = vals[j]; batch.append((key, q))
        ratios = []
        for _, q, r in run(batch):
            st[key]["combos"] += 1
            if r and r_best["profit_factor"]:
                ratios.append(round((r["profit_factor"] or 0) / r_best["profit_factor"], 3))
        return min(ratios) if ratios else None, ratios

    while True:
        for key in active():
            S = st[key]
            if S["best_r"] is None:
                for _, _, r in run([(key, S["best"])]):
                    S["best_r"] = r; S["combos"] += 1
            if not S.get("cur_r"):
                S["cur"], S["cur_r"] = S["best"], S["best_r"]
            new_in_round, improved_in_round = 0, False
            for gi, group in enumerate(GROUPS[key]):
                names = list(group)
                combos = [dict(zip(names, vals)) for vals in itertools.product(*group.values())]
                random.shuffle(combos)
                batch = []
                for c in combos:
                    q = dict(S["cur"]); q.update(c); q.update(NO_EXIT[key])
                    sig = json.dumps(q, sort_keys=True)
                    if sig in seen[key]:
                        continue
                    seen[key].add(sig); batch.append((key, q))
                    if len(batch) >= MAX_PER_GROUP:
                        break
                improved = False
                new_in_round += len(batch)
                for _, q, r in run(batch):
                    S["combos"] += 1
                    if r and score(r, key) > score(S["cur_r"], key):
                        S["cur"], S["cur_r"], improved = q, r, True
                    if r and score(r, key) > score(S["best_r"], key):
                        S["best"], S["best_r"] = q, r
                improved_in_round |= improved
                print(time.strftime("%d. %H:%M"), key, f"skupina {gi + 1}", "zlepšenie" if improved else "bez zlepšenia",
                      f"PF {S['cur_r']['profit_factor']:.2f} obch {S['cur_r']['trades']}",
                      {k: v["pf"] for k, v in S["cur_r"].get("years", {}).items()}, f"kombinácií {S['combos']}", flush=True)
                if improved and passes_is(S["cur_r"], key):
                    sig = json.dumps(S["cur"], sort_keys=True)
                    if sig not in {json.dumps(c["p"], sort_keys=True) for c in S["candidates"]}:
                        pmin, ratios = plateau(key, S["cur"], S["cur_r"], group)
                        cand = {"p": S["cur"], "is": S["cur_r"], "plateau_min": pmin, "plateau": ratios,
                                "combos_at": S["combos"], "t": time.strftime("%Y-%m-%d %H:%M")}
                        if pmin is None or pmin >= 0.8:
                            import io, contextlib
                            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                                cand["oos"] = evaluate(key, S["cur"], oos_tr(key))      # odložený rok — raz, nikdy na ladenie
                        S["candidates"].append(cand)
                        print("   KANDIDÁT", key, "plató", pmin, "OOS", cand.get("oos", {}).get("profit_factor"), flush=True)
                save()
            S["round"] += 1
            # Zaseknuté (nič nové alebo bez zlepšenia) -> skok: pracovný bod sa presunie na náhodného
            # suseda najlepšieho (3 parametre z rôznych skupín) BEZ ohľadu na výsledok a hľadá sa odtiaľ.
            # Najlepšie nastavenie ostáva uložené v "best"; kandidáti sa berú z každého lokálneho optima.
            if new_in_round == 0 or not improved_in_round:
                # zaseknuté optimum -> do hyperoptu (glhyper.py), ak stojí za doladenie
                if (S["cur_r"].get("profit_factor") or 0) >= 1.2:
                    qsig = key + json.dumps(S["cur"], sort_keys=True)
                    qf = ROOT / "hyper_queue.jsonl"
                    known = {json.loads(l)["sig"] for l in open(qf)} if qf.exists() else set()
                    if qsig not in known:
                        with open(qf, "a") as fh:
                            fh.write(json.dumps({"sig": qsig, "key": key, "p": S["cur"], "r": S["cur_r"],
                                                 "t": time.strftime("%Y-%m-%d %H:%M")}) + "\n")
                        print(time.strftime("%d. %H:%M"), key, "-> HYPEROPT fronta", f"PF {S['cur_r']['profit_factor']:.2f}", flush=True)
                base = S["best"] if random.random() < 0.5 else S["cur"]
                for _ in range(50):
                    q = dict(base)
                    for g in random.sample(GROUPS[key], min(3, len(GROUPS[key]))):
                        n = random.choice(list(g)); q[n] = random.choice(g[n])
                    q.update(NO_EXIT[key])
                    if json.dumps(q, sort_keys=True) not in seen[key]:
                        break
                seen[key].add(json.dumps(q, sort_keys=True))
                for _, q2, r in run([(key, q)]):
                    S["combos"] += 1
                    if r:
                        S["cur"], S["cur_r"] = q2, r
                        if score(r, key) > score(S["best_r"], key):
                            S["best"], S["best_r"] = q2, r
                print(time.strftime("%d. %H:%M"), key, "SKOK na nový bod", f"PF {S['cur_r']['profit_factor']:.2f}", flush=True)
            save()


if __name__ == "__main__":
    main()
