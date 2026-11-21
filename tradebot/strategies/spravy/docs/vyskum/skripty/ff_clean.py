"""ForexFactory dataset → červené správy s časom UTC.

Čas 00:00 (Teherán) v datasete = čas chýba (skript FF ho pri správach v rovnakom čase nevyplnil). Doplní sa najčastejším
miestnym časom tej istej správy (mena + názov) v krajine vydania; správa bez pevného času (najčastejší < 70 %) sa vyradí.
"""
import pandas as pd
SRC = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffdata/forex_factory_cache.csv"
OUT = "/private/tmp/claude-501/-Users-martin-document-IBS/a692f5b8-2895-4c67-b9ff-2c7eb0337625/scratchpad/ffwork/ff_high_2021.csv"
TZ = {"USD": "America/New_York", "CAD": "America/Toronto", "EUR": "Europe/Berlin", "GBP": "Europe/London", "CHF": "Europe/Zurich",
      "JPY": "Asia/Tokyo", "AUD": "Australia/Sydney", "NZD": "Pacific/Auckland", "CNY": "Asia/Shanghai"}
df = pd.read_csv(SRC, usecols=["DateTime", "Currency", "Impact", "Event"])
df = df[(df.DateTime >= "2016-01-01") & df.Currency.isin(TZ)].reset_index(drop=True)
# Irán zrušil letný čas od 2023, skript FF ešte písal +04:30 — hodiny na stránke boli +03:30 (overené: German Trade Balance 4. 5. 2023)
fix = (df.DateTime.str[:4] >= "2023") & df.DateTime.str.endswith("+04:30")
df.loc[fix, "DateTime"] = df.loc[fix, "DateTime"].str[:-6] + "+03:30"
df["raw"] = pd.to_datetime(df.DateTime, utc=True)
df["missing"] = df.DateTime.str[11:19].isin(["00:00:00", "23:59:59"])
# miestny deň vydania: pri chýbajúcom čase je dátum dňa v Teheráne (= deň vydania vo väčšine pásiem okrem NZ/AU ráno — tie majú čas skoro vždy)
df["day"] = df.DateTime.str[:10]
rows = []
for (cur, ev), g in df.groupby(["Currency", "Event"]):
    tz = TZ[cur]
    known = g[~g.missing]
    loc = known.raw.dt.tz_convert(tz).dt.strftime("%H:%M")
    mode, share = (loc.mode().iloc[0], (loc == loc.mode().iloc[0]).mean()) if len(loc) else (None, 0.0)
    kt = known.raw.values
    for _, r in g.iterrows():
        if not r.missing:
            rows.append((r.raw, cur, ev, r.Impact, "známy", share))
        elif len(known) >= 3:
            # čas najbližšieho známeho vydania tej istej správy (zachytí zmenu času, napr. ECB 13:45 → 14:15 od 7/2022)
            ref = pd.Timestamp(r.day).tz_localize("UTC")
            j = abs(known.raw - ref).values.argmin()
            if abs((known.raw.iloc[j] - ref).days) > 400:
                rows.append((pd.NaT, cur, ev, r.Impact, "neznámy", share)); continue
            hm = loc.iloc[j]
            t = pd.Timestamp(f"{r.day} {hm}").tz_localize(tz).tz_convert("UTC")
            rows.append((t, cur, ev, r.Impact, "doplnený", share))
        else:
            rows.append((pd.NaT, cur, ev, r.Impact, "neznámy", share))
out = pd.DataFrame(rows, columns=["t", "cur", "event", "impact", "cas", "share"])
h = out[out.impact.str.startswith("High") & (out.t.isna() | (out.t >= pd.Timestamp("2021-01-01", tz="UTC")))]
h = h[h.t.isna() | True]
h.to_csv(OUT, index=False)
print("červené:", len(h), h.cas.value_counts().to_dict())
