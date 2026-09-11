"""Import Databento exportu (CME futures, ohlcv-1m): kontrakty → front-month → 1m feather po rokoch.

    python -m tester.bento_import C:/bento/glbx-mdp3-20100606-20260910.ohlcv-1m.csv --symbol MNQ
    python -m tester.bento_import export.csv --symbol MNQ --from 2020-01-01 --no-merge

### Čo prichádza
Databento batch job, dataset `GLBX.MDP3` (CME Globex), schéma `ohlcv-1m`, rodičovský
symbol `MNQ.FUT` — teda **každý kontrakt zvlášť** (MNQM9, MNQU9, …) a k tomu kalendárne
spready (MNQM9-MNQU9). Čas je UTC, **začiatok** minúty, ceny v bodoch, objem v kontraktoch:

```
ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol
2026-09-10T23:59:00.000000000Z,33,1,42004800,29066.00,29067.00,29062.25,29064.75,889,MNQU6
```

Bary sú len tam, kde sa obchodovalo — žiadna vypchávka ako v Dukascopy. Vedľa CSV býva
`condition.json` (dostupnosť po dňoch); dni `degraded` sa vypíšu, nič sa s nimi nerobí.

### Čo import robí
1. **Vyhodí spready** (symbol s pomlčkou) — majú nulové aj záporné ceny a nie sú trh.
2. **Front-month podľa denného objemu.** Každý (UTC) deň patrí kontraktu s najväčším
   objemom; roll sa nikdy nevracia k staršiemu kontraktu. Na MNQ to vychádza vždy
   v pondelok týždeň pred expiráciou (marec, jún, september, december).
3. **Bez back-adjustmentu.** Pri rolle je v rade skok ceny (rozdiel kontraktov, desiatky
   bodov). Stratégie tu sú intradenné a zavierajú na konci seansy, signály sa počítajú
   v rámci dňa, takže skok nevadí; pozíciu cez deň rollu by ale zasiahol. Dni rollov sú
   v štatistike importu a v `<stem>-1m.rolls.json` vedľa archívu.
4. **Čas baru** ostáva časom otvorenia (UTC), ako v jadre a v Pine.
5. **Objem** je burzový — inštrument má `has_real_volume=True`, objemový filter má zmysel.

Ďalej je to tá istá cesta ako pri Dukascopy: feather po rokoch do `data_archive/tester/
databento/futures/`, `tester.data_archive merge` zloží pracovný súbor, vyššie TF si Tester
dopočíta, `tester.quotemanager` spraví ASCII pre MultiCharts. Symbol musí byť v
`tradebot/core/instruments_databento.json` (tick, hodnota bodu, náklad).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from tradebot.core.paths import TESTER_ARCHIVE
from tradebot.core.types import INSTRUMENTS, InstrumentSpec

from .dukas_import import store

__all__ = ["ImportStats", "load_bento_frame", "front_month", "resolve_symbol", "degraded_days"]

#: Riadny kontrakt: koreň + mesačný kód + rok (MNQU6, MNQH26). Všetko ostatné sú spready.
CONTRACT_RE = re.compile(r"^([A-Z0-9]+?)([FGHJKMNQUVXZ])(\d{1,2})$")
MONTH_CODES = "FGHJKMNQUVXZ"


@dataclass
class ImportStats:
    rows_in: int = 0
    rows_out: int = 0
    spreads: int = 0            #: riadky kalendárnych spreadov (vyhodené)
    other_roots: int = 0        #: riadky kontraktov iného koreňa (vyhodené)
    contracts: int = 0          #: koľko kontraktov sa do rady dostalo
    dropped_bad: int = 0        #: bary s nezmyselným OHLC (high < low, cena <= 0) alebo bez objemu
    dropped_dup: int = 0        #: druhý bar s tým istým časom (ostáva posledný)
    dropped_range: int = 0
    first: str | None = None
    last: str | None = None
    #: (deň, kontrakt) — kedy sa rada prepla na ďalší kontrakt
    rolls: list[tuple[str, str]] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"riadkov: {self.rows_in} -> {self.rows_out}",
            f"vyhodene spready: {self.spreads}, iny koren: {self.other_roots}",
            f"kontraktov v rade: {self.contracts}, rollov: {max(len(self.rolls) - 1, 0)}",
            f"vyhodene zle bary (OHLC/cena/objem): {self.dropped_bad}, duplicitne casy: {self.dropped_dup}",
            f"mimo --from/--to: {self.dropped_range}",
            f"obdobie: {self.first} .. {self.last}",
        ]
        if self.rolls:
            posledne = ", ".join(f"{d} {s}" for d, s in self.rolls[-4:])
            lines.append(f"posledne rolly: {posledne}")
        if self.degraded:
            dni = ", ".join(self.degraded[:8]) + (" ..." if len(self.degraded) > 8 else "")
            lines.append(f"dni oznacene Databento ako degraded: {len(self.degraded)}: {dni}")
        return "\n".join(lines)


def contract_order(symbol: str) -> tuple[int, int] | None:
    """`MNQU6` → (2026, 9): poradie kontraktu v čase; `None` = nie je riadny kontrakt.

    Jednociferný rok Databento píše ako posledná číslica dekády; dekáda sa berie tá,
    v ktorej MNQ existuje (2019+): 9 → 2019, 0–8 → 2020–2028. Dvojciferný rok je celý.
    """
    m = CONTRACT_RE.match(symbol)
    if not m:
        return None
    rok = m.group(3)
    year = 2000 + int(rok) if len(rok) == 2 else (2019 if rok == "9" else 2020 + int(rok))
    return year, MONTH_CODES.index(m.group(2)) + 1


def resolve_symbol(symbol: str) -> tuple[str, InstrumentSpec] | None:
    """`MNQ`, `MNQ/USD` alebo kľúč `mnq_databento` → (kľúč, inštrument) zo zdroja databento."""
    want = symbol.strip()
    for key, inst in INSTRUMENTS.items():
        if inst.data_source != "databento":
            continue
        if want in (key, inst.symbol, inst.symbol.split("/")[0]):
            return key, inst
    return None


def degraded_days(csv_path: Path, date_from: str | None = None) -> list[str]:
    """Dni z `condition.json` vedľa exportu, ktoré Databento neoznačilo `available`."""
    p = Path(csv_path).with_name("condition.json")
    if not p.exists():
        return []
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out = [r["date"] for r in rows if isinstance(r, dict) and r.get("condition") != "available"
           and r.get("date") and (not date_from or r["date"] >= date_from)]
    return sorted(out)


def front_month(df, stats: ImportStats | None = None):
    """Z barov všetkých kontraktov jedna rada: každý UTC deň patrí kontraktu s najväčším
    objemom, roll ide len dopredu (nikdy späť k staršiemu kontraktu).

    `df` má stĺpce `date, open, high, low, close, volume, symbol` (len riadne kontrakty).
    Vráti DataFrame bez `symbol`, zoradený podľa času.
    """
    import pandas as pd

    st = stats if stats is not None else ImportStats()
    if df.empty:
        return df.drop(columns=["symbol"])
    den = df["date"].dt.floor("D")
    denne = df.assign(_den=den).groupby(["_den", "symbol"], observed=True)["volume"].sum().reset_index()
    denne["_poradie"] = denne["symbol"].map(contract_order)
    vyber: dict[pd.Timestamp, str] = {}
    aktualny: tuple[int, int] | None = None
    for d, skupina in denne.groupby("_den", sort=True):
        # Kandidát = najväčší objem dňa, ale nie starší než to, na čom rada už je:
        # v deň rollu má starý kontrakt ešte objem a deň po rolle nesmie preskočiť späť.
        kand = skupina.sort_values(["volume", "_poradie"], ascending=[False, True])
        vybrany = None
        for _, r in kand.iterrows():
            if aktualny is None or r["_poradie"] >= aktualny:
                vybrany = r
                break
        if vybrany is None:
            vybrany = kand.iloc[0]
        vyber[d] = str(vybrany["symbol"])
        aktualny = vybrany["_poradie"]
    mapa = pd.Series(vyber)
    zvoleny = den.map(mapa)
    out = df[df["symbol"].astype(str) == zvoleny.astype(str)].drop(columns=["symbol"])
    out = out.sort_values("date").reset_index(drop=True)
    st.contracts = len(set(vyber.values()))
    predosly = None
    for d in sorted(vyber):
        if vyber[d] != predosly:
            st.rolls.append((f"{d:%Y-%m-%d}", vyber[d]))
            predosly = vyber[d]
    return out


def load_bento_frame(path: str | Path, *, root: str, date_from: str | None = None,
                     date_to: str | None = None, stats: ImportStats | None = None):
    """Databento `ohlcv-1m` CSV → front-month rada `date, open, high, low, close, volume`.

    `root` je koreň kontraktu (`MNQ`); riadky iných koreňov a spready vypadnú.
    """
    import pandas as pd

    st = stats if stats is not None else ImportStats()
    df = pd.read_csv(
        path, usecols=["ts_event", "open", "high", "low", "close", "volume", "symbol"],
        dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64",
               "volume": "float64", "symbol": "string"},
    )
    st.rows_in = len(df)
    df = df.rename(columns={"ts_event": "date"})
    df["date"] = pd.to_datetime(df["date"], utc=True)

    sym = df["symbol"].fillna("")
    spread = sym.str.contains("-", regex=False)
    st.spreads = int(spread.sum())
    df = df[~spread]
    sym = df["symbol"]
    korene = sym.str.extract(CONTRACT_RE.pattern)[0]
    cudzi = (korene != root) | korene.isna()
    st.other_roots = int(cudzi.sum())
    df = df[~cudzi]

    before = len(df)
    if date_from:
        df = df[df["date"] >= f"{date_from} 00:00:00+00:00"]
    if date_to:
        df = df[df["date"] <= f"{date_to} 23:59:59+00:00"]
    st.dropped_range = before - len(df)

    df = front_month(df.reset_index(drop=True), stats=st)
    # Poistka, nie čistenie ako pri Dukascopy (vypchávka a ×1000 tu nebývajú): bar, ktorý
    # nemôže byť pravda, do rady nejde, a jeden čas je jeden bar.
    zly = ((df["high"] < df["low"]) | (df["high"] < df[["open", "close"]].max(axis=1))
           | (df["low"] > df[["open", "close"]].min(axis=1))
           | (df[["open", "high", "low", "close"]] <= 0).any(axis=1) | (df["volume"] <= 0))
    st.dropped_bad = int(zly.sum())
    df = df[~zly]
    dup = df.duplicated("date", keep="last")
    st.dropped_dup = int(dup.sum())
    df = df[~dup]
    df = df[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
    st.rows_out = len(df)
    if len(df):
        st.first = f"{df['date'].iloc[0]:%Y-%m-%d %H:%M}"
        st.last = f"{df['date'].iloc[-1]:%Y-%m-%d %H:%M}"
    return df


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m tester.bento_import",
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("src", type=Path, help="Databento CSV (schéma ohlcv-1m, parent symbol, UTC)")
    ap.add_argument("--symbol", required=True,
                    help="koreň kontraktu (MNQ) alebo kľúč inštrumentu (mnq_databento) "
                         "z tradebot/core/instruments_databento.json")
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vrátane")
    ap.add_argument("--archive", type=Path, default=TESTER_ARCHIVE,
                    help="kam ročné feather súbory (default data_archive/tester/)")
    ap.add_argument("--no-merge", action="store_true", help="nezložiť pracovný súbor pre Tester")
    return ap


def main(argv: list[str] | None = None, stderr: TextIO | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    args = _build_parser().parse_args(argv)
    err = stderr or sys.stderr

    if not args.src.exists():
        print(f"zdroj neexistuje: {args.src}", file=err)
        return 1
    found = resolve_symbol(args.symbol)
    if found is None:
        zname = ", ".join(sorted(k for k, i in INSTRUMENTS.items() if i.data_source == "databento"))
        print(f"symbol {args.symbol!r} nie je v tradebot/core/instruments_databento.json; "
              f"zname: {zname or '(nic)'}. Dopis ho tam (tick, hodnota bodu, naklad) a spusti znova.",
              file=err)
        return 1
    key, inst = found
    root = inst.symbol.split("/")[0]

    stats = ImportStats()
    df = load_bento_frame(args.src, root=root, date_from=args.date_from, date_to=args.date_to, stats=stats)
    stats.degraded = degraded_days(args.src, date_from=stats.first[:10] if stats.first else None)
    print(f"\n{args.src.name} -> {inst.data_stem} ({key})", file=err)
    print(stats.summary(), file=err)
    if df.empty:
        print("po filtrovani neostal ziadny bar", file=err)
        return 1

    print("\narchiv (commitni ho):", file=err)
    files = store(df, inst, archive=args.archive, merge=not args.no_merge)
    rolls_path = files[0].with_name(f"{inst.data_stem}-1m.rolls.json")
    rolls_path.write_text(json.dumps([{"date": d, "contract": s} for d, s in stats.rolls],
                                     indent=1), encoding="utf-8")
    print(f"  {rolls_path.name}  {len(stats.rolls)} zaznamov (den, kontrakt)", file=err)
    if not args.no_merge:
        print("\npracovny subor pre Tester je zlozeny; vyssie TF dopocita `python -m tester.timeframes` "
              "alebo start webapp", file=err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
