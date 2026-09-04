"""Koľko z obchodov by sa vyplnilo ako maker — a čo to spraví s výsledkom.

    python -m ibs.tools.fees                       # posledny backtest
    python -m ibs.tools.fees vysledok.zip
    python -m ibs.tools.fees --maker 0.02 --taker 0.05

### Načo to je
Edge tejto stratégie je zhruba rovnako veľký ako poplatky. Pri takom pomere už nie
je exekúcia detail — rozdiel medzi maker (0,02 %) a taker (0,05 %) poplatkom na
Binance je rozdiel medzi nulou a ziskom. Tento nástroj zisťuje, koľko z príkazov by
reálne ležalo v knihe, a prepočítava výsledok zmiešanou sadzbou.

### Ako sa rozhoduje
**Vstup** je limitka na cene medzery. Je pasívna (maker) vtedy, keď v okamihu
zadania leží na správnej strane trhu — pre LONG pod aktuálnou cenou. Porovnáva sa
s **otváracou cenou sviečky, na ktorej bol príkaz zadaný**; presne tú cenu dostane
`custom_entry_price()` ako `proposed_rate`, takže je to tá istá informácia, akú má
stratégia v reálnom čase. Žiadny pohľad dopredu.

**Výstupy** sa rozdeľujú podľa dôvodu:

* `roi` — take profit je odpočívajúca limitka, teda **maker**;
* `stop_loss` — stop sa spúšťa trhovým príkazom, teda **taker**;
* `session_end` — trhový príkaz, **taker**.

### Čo to zámerne NErieši
Post-only príkaz, ktorý by prekročil spread, burza odmietne — obchod by teda
nevznikol vôbec, nie sa vyplnil drahšie. Tu sa taký prípad počíta ako taker, čo je
konzervatívnejšie: reálne by tie obchody odpadli aj s ich ziskom aj stratou.
Rovnako sa neuvažuje slippage ani to, že limitka v knihe sa nemusí vyplniť celá.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

#: Binance USDⓈ-M futures, VIP 0 (% z objemu na jednu stranu).
MAKER_PCT = 0.02
TAKER_PCT = 0.05

#: Dôvod výstupu -> je to maker? `roi` je limitka, zvyšok ide trhom.
_EXIT_IS_MAKER = {"roi": True, "stop_loss": False, "session_end": False}


def load(path: Path):
    """(stats, trades) z výsledkového zipu — rovnaký tvar ako v `ibs.tools.report`."""
    import pandas as pd

    with zipfile.ZipFile(path) as z:
        main = next(
            n for n in z.namelist()
            if n.endswith(".json") and "config" not in n and "meta" not in n
        )
        name, stats = next(iter(json.loads(z.read(main))["strategy"].items()))
        stats["strategy_name"] = name
        trades = pd.DataFrame(stats.pop("trades"))
    for col in ("open_date", "close_date"):
        trades[col] = pd.to_datetime(trades[col], utc=True)
    return stats, trades


def classify(stats, trades, exchange: str = "binance"):
    """Doplní stĺpce `entry_maker` a `exit_maker`."""
    import pandas as pd

    from .scan_zones import _load

    chart = _load(exchange, stats["timeframe"])
    chart = chart.copy()
    chart["date"] = pd.to_datetime(chart["date"], utc=True)
    opens = chart.set_index("date")["open"]

    # Pozor: `open_date` je čas ZADANIA limitky, nie jej vyplnenia — presne to,
    # čo tu potrebujeme. (Overené na golden okne: obchod zadaný 17:09 sa vyplnil
    # až 17:15, a TradingView hlási 17:15.)
    idx = opens.index.searchsorted(trades["open_date"], side="right") - 1
    ref = pd.Series(opens.to_numpy()[idx.clip(min=0)], index=trades.index)
    ref[idx < 0] = float("nan")

    long = ~trades["is_short"].astype(bool)
    trades = trades.copy()
    trades["ref_price"] = ref
    trades["entry_maker"] = (
        (long & (trades["open_rate"] < ref)) | (~long & (trades["open_rate"] > ref))
    ).fillna(False)
    trades["exit_maker"] = trades["exit_reason"].map(_EXIT_IS_MAKER).fillna(False)
    return trades


def summarize(trades, maker: float = MAKER_PCT, taker: float = TAKER_PCT) -> dict:
    """Hrubý zisk, poplatky pri zmiešanej sadzbe a čistý výsledok."""
    direction = trades["is_short"].map({True: -1.0, False: 1.0})
    gross = ((trades["close_rate"] - trades["open_rate"]) * trades["amount"] * direction).sum()

    entry_vol = trades["open_rate"] * trades["amount"]
    exit_vol = trades["close_rate"] * trades["amount"]
    rate = lambda flag: (flag.map({True: maker, False: taker})) / 100.0  # noqa: E731
    fees = (entry_vol * rate(trades["entry_maker"]) + exit_vol * rate(trades["exit_maker"])).sum()
    volume = (entry_vol + exit_vol).sum()

    return {
        "n": len(trades),
        "gross": gross,
        "volume": volume,
        "break_even": gross / volume * 100 if volume else float("nan"),
        "entry_maker_pct": 100 * trades["entry_maker"].mean(),
        "exit_maker_pct": 100 * trades["exit_maker"].mean(),
        "fees": fees,
        "blended": fees / volume * 100 if volume else float("nan"),
        "net": gross - fees,
        "net_all_taker": gross - volume * taker / 100.0,
    }


def _report(label: str, s: dict, cur: str = "USDT") -> None:
    print(f"\n=== {label} ===")
    print(f"  obchodov              {s['n']}")
    print(f"  vstup ako maker       {s['entry_maker_pct']:.1f} %")
    print(f"  vystup ako maker      {s['exit_maker_pct']:.1f} %")
    print(f"  hruby zisk            {s['gross']:+,.0f} {cur}")
    print(f"  break-even poplatok   {s['break_even']:.4f} % na stranu")
    print(f"  zmiesany poplatok     {s['blended']:.4f} % na stranu")
    print(f"  poplatky spolu        {s['fees']:,.0f} {cur}")
    print(f"  CISTY (zmiesany)      {s['net']:+,.0f} {cur}")
    print(f"  cisty (len taker)     {s['net_all_taker']:+,.0f} {cur}")


def main(argv: list[str] | None = None) -> int:
    from .report import newest

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("result", nargs="*", help="backtest_results/*.zip (default: posledny)")
    ap.add_argument("--maker", type=float, default=MAKER_PCT, help="maker poplatok v %%")
    ap.add_argument("--taker", type=float, default=TAKER_PCT, help="taker poplatok v %%")
    ap.add_argument("--exchange", default="binance")
    args = ap.parse_args(argv)

    import pandas as pd

    paths = [Path(p) for p in args.result] or [newest()]
    pooled = []
    for path in paths:
        stats, trades = load(path)
        if trades.empty:
            print(f"{path.name}: ziadne obchody")
            continue
        trades = classify(stats, trades, args.exchange)
        pooled.append(trades)
        _report(
            f"{stats['backtest_start'][:10]} -> {stats['backtest_end'][:10]}",
            summarize(trades, args.maker, args.taker),
            stats.get("stake_currency", "USDT"),
        )

    if len(pooled) > 1:
        _report("VSETKY OKNA SPOLU", summarize(pd.concat(pooled, ignore_index=True),
                                               args.maker, args.taker))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
