"""Červené správy iných mien než USD → typy udalostí (mena, čas UTC), bez prejavov a duplicít v tú istú minútu."""
import re
import pandas as pd
IN = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_high_2021.csv"
OUT = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_types.csv"
RULES = [  # (mena, regex názvu, typ) — prvé, čo sedí
    ("EUR", r"Main Refinancing|Monetary Policy Statement|Deposit Facility", "ECB"), ("EUR", r"ECB Press Conference", "ECB_TK"),
    ("EUR", r"Flash .*PMI", "EZ_PMI"), ("EUR", r"CPI", "EZ_CPI"),
    ("GBP", r"Official Bank Rate|Monetary Policy Summary|MPC Official", "BOE"), ("GBP", r"CPI", "UK_CPI"),
    ("GBP", r"Flash .*PMI", "UK_PMI"), ("GBP", r"GDP", "UK_GDP"), ("GBP", r"Claimant|Average Earnings|Unemployment", "UK_JOBS"),
    ("CAD", r"Overnight Rate|BOC Rate Statement|Monetary Policy Report", "BOC"), ("CAD", r"BOC Press", "BOC_TK"),
    ("CAD", r"Employment|Unemployment", "CA_JOBS"), ("CAD", r"CPI", "CA_CPI"), ("CAD", r"GDP", "CA_GDP"),
    ("AUD", r"Cash Rate|RBA Rate Statement", "RBA"), ("AUD", r"Employment|Unemployment", "AU_JOBS"), ("AUD", r"CPI", "AU_CPI"),
    ("AUD", r"GDP", "AU_GDP"), ("AUD", r"Minutes", "RBA_MIN"),
    ("NZD", r"Official Cash Rate|RBNZ Rate Statement|Monetary Policy Statement", "RBNZ"), ("NZD", r"CPI", "NZ_CPI"),
    ("NZD", r"Employment|Unemployment", "NZ_JOBS"), ("NZD", r"GDP", "NZ_GDP"),
    ("CHF", r"SNB Monetary|Libor|SNB Policy Rate", "SNB"), ("CHF", r"CPI", "CH_CPI"),
    ("JPY", r"BOJ Outlook|Monetary Policy Statement|Policy Rate", "BOJ"), ("JPY", r"BOJ Press", "BOJ_TK"),
    ("CNY", r"PMI", "CN_PMI"), ("CNY", r"GDP|Industrial|CPI", "CN_DATA"),
]
h = pd.read_csv(IN); h["t"] = pd.to_datetime(h.t, utc=True, format="ISO8601")
h = h.dropna(subset=["t"]); h = h[(h.t >= pd.Timestamp("2021-01-01", tz="UTC")) & (h.cur != "USD") & ~h.event.str.contains("Speaks|Testif|Hearing")]
def typ(r):
    for cur, rx, name in RULES:
        if r.cur == cur and re.search(rx, r.event):
            return name
    return None
h["typ"] = h.apply(typ, axis=1)
other = h[h.typ.isna()].groupby(["cur", "event"]).size().sort_values(ascending=False)
h = h.dropna(subset=["typ"]).drop_duplicates(["typ", "t"])
h[["t", "typ", "cur", "event", "cas"]].sort_values("t").to_csv(OUT, index=False)
print(h.groupby("typ").agg(n=("t", "size"), od=("t", "min"), do=("t", "max"), dopl=("cas", lambda s: int((s == "doplnený").sum()))).to_string())
print("\nnezaradené červené:", other.head(15).to_dict())
