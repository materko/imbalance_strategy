"""Prejde reálne dáta a vypíše, aké SD zóny by vznikli — smoke test kroku 2.

Nie je to backtest, orderov sa netýka. Overuje presne to, čo je v tejto fáze
hotové: session okná + detekciu SD zón na detekčnom TF + evidenciu zón.

    python -m tester.compare.scan_zones --exchange binance --profile golden_binance_btcusdt_3m
    python -m tester.compare.scan_zones --exchange coinbase --profile golden_coinbase_btcusd_3m --limit 20
    python -m tester.compare.scan_zones --csv C:/dukas/NAS100_M1_10Y.csv --profile docs/profily_archiv/ibs/nas100_dukas_3m.json

Zdroj dát je buď burza z `data_archive/` (`--exchange`), alebo Dukascopy 1m CSV
(`--csv`, formát `dt,o,h,l,c,vol`, UTC, čas otvorenia) — z neho sa graf aj detekčný
TF skladajú v pamäti rovnako ako z 1m feather súborov. Vypchávka Dukascopy exportu
(plochý bar s cenou predchádzajúceho uzavretia, víkendy a prestávky) sa zahodí,
presne ako pri prevode pre MultiCharts (`tester.dukas_import`).

Vyžaduje pandas (ťahá sa s Freqtrade), takže sa spúšťa z `.venv`, nie z jadra.
"""

from __future__ import annotations

import argparse
import sys
from functools import lru_cache
from pathlib import Path

from tradebot.core import (
    BarHistory,
    htf_window_opens,
    Bar,
    HTFWindow,
    IBSConfig,
    InstrumentSpec,
    SessionClock,
    ZoneBook,
    detect_sd_pattern,
    load_profile,
)
from tradebot.core.candles import resample_ohlcv as _resample
from tradebot.core.types import INSTRUMENTS

from .. import engines

#: Referenčný pár každej burzy. Kde jeho súbor leží, vie `engines` — tu sa cesta
#: neskladá, aby sa pri zmene rozloženia dát nedalo zabudnúť práve na toto miesto.
_PAIRS = {
    "binance": "btcusdt_binance",
    "coinbase": "btcusd_coinbase",
}


def is_csv_source(source: str | Path) -> bool:
    """`--csv` zdroj sa od kľúča burzy pozná podľa prípony."""
    return str(source).lower().endswith(".csv")


@lru_cache(maxsize=2)
def _load_dukas_csv(path: str):
    """Dukascopy 1m export ako DataFrame v tvare Freqtrade sviečok (`date` UTC, OHLCV).

    Cache je tu preto, že jeden beh pýta ten istý súbor trikrát (graf, detekčný TF,
    1m detail) a 375 MB CSV sa číta ~20 s.
    """
    import pandas as pd

    df = pd.read_csv(
        path, usecols=[0, 1, 2, 3, 4, 5], header=0,
        names=["date", "open", "high", "low", "close", "volume"],
        dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64", "volume": "float64"},
    )
    df["date"] = pd.to_datetime(df["date"], utc=True)
    # vypchávka: plochý bar s cenou rovnou predchádzajúcemu uzavretiu — rovnaké
    # pravidlo ako v dukas_import, aby simulátor videl tie isté bary ako MultiCharts
    flat = (df["open"] == df["close"]) & (df["high"] == df["low"]) & (df["open"] == df["high"])
    padding = flat & (df["close"] == df["close"].shift(1))
    dropped = int(padding.sum())
    df = df[~padding].reset_index(drop=True)
    print(f"  i {Path(path).name}: {len(df)} 1m barov, vyhodena vypchavka {dropped}", file=sys.stderr)
    return df


def _load(exchange: str | Path, timeframe: str):
    """Načíta sviečky. Ak burza daný TF neponúka, poskladá ho z 1m **v pamäti**.

    `exchange` je kľúč burzy z `_PAIRS`, alebo cesta k Dukascopy 1m CSV (`--csv`);
    z CSV sa každý TF okrem 1m skladá v pamäti.

    Na disk sa nikdy nič dopočítané nezapisuje — v sklade `data/tester/` sú výhradne
    skutočné burzové sviečky. Presne to isté bude robiť aj Freqtrade stratégia
    (napr. Coinbase 3m, ktoré burza neponúka).
    """
    import pandas as pd

    minutes = int(timeframe.rstrip("m"))
    if is_csv_source(exchange):
        base = _load_dukas_csv(str(exchange))
        df = base.copy() if minutes == 1 else _resample(base, minutes)
        df["ts"] = df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000
        return df

    inst = INSTRUMENTS[_PAIRS[exchange]]
    path = engines.freqtrade_file(inst, timeframe)

    if not path.exists():
        src = engines.freqtrade_file(inst, "1m")
        if not src.exists():
            raise SystemExit(
                f"Chybaju data: {path}\n"
                "Stiahni ich: ./deploy/freqtrade/scripts/download-data.sh (alebo .ps1)"
            )
        print(f"  i {exchange} neponuka {timeframe} - skladam ho z 1m v pamati", file=sys.stderr)
        df = _resample(pd.read_feather(src), minutes)
    else:
        df = pd.read_feather(path)
    # Freqtrade uklada datetime64[ms]; pretypovanie na ns je tu zamerne, aby //1e6
    # dalo milisekundy bez ohladu na to, v akej jednotke pride stlpec.
    df["ts"] = df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000
    return df


def _to_bar(row) -> Bar:
    return Bar(
        time=int(row.ts),
        open=float(row.open),
        high=float(row.high),
        low=float(row.low),
        close=float(row.close),
        volume=float(row.volume),
    )


def scan(
    cfg: IBSConfig,
    inst: InstrumentSpec,
    exchange: str | Path,
    chart_tf_minutes: int,
) -> tuple[ZoneBook, dict[str, int]]:
    htf_minutes = int(cfg.zoneDetectionTF)
    htf_ms = htf_minutes * 60_000

    chart = _load(exchange, f"{chart_tf_minutes}m")
    htf = _load(exchange, f"{htf_minutes}m")

    # SMA volume na detekcnom TF, posunuta o 1 - Pine ta.sma(volume, volSmaLen)[1].
    htf["vol_sma"] = htf["volume"].rolling(cfg.volSmaLen).mean()

    htf_bars: dict[int, Bar] = {}
    htf_vol_sma: dict[int, float] = {}
    for row in htf.itertuples(index=False):
        htf_bars[int(row.ts)] = _to_bar(row)
        htf_vol_sma[int(row.ts)] = float(row.vol_sma) if row.vol_sma == row.vol_sma else 0.0

    clock = SessionClock(cfg)
    book = ZoneBook(cfg, inst, chart_tf_minutes)
    # Drzime historiu len kvoli ATR - parametre v jednotke `atr` by inak vysli 0.
    history = BarHistory(maxlen=cfg.atrLen + 8, atr_len=cfg.atrLen)

    stats = {"bars": 0, "in_zone_window": 0, "htf_closes": 0, "patterns": 0, "zones": 0}
    prev_htf_open: int | None = None

    for row in chart.itertuples(index=False):
        ts = int(row.ts)
        history.append(_to_bar(row))
        stats["bars"] += 1

        htf_open = ts // htf_ms * htf_ms
        new_htf_period = prev_htf_open is not None and htf_open != prev_htf_open
        prev_htf_open = htf_open

        state = clock.state(ts)
        if state.in_zone_window:
            stats["in_zone_window"] += 1

        if not new_htf_period:
            continue
        stats["htf_closes"] += 1

        # bars[0] pocitame z CASU UZAVRETIA baru grafu - viz htf_window_opens().
        opens = htf_window_opens(ts, chart_tf_minutes * 60_000, htf_ms)
        if any(o not in htf_bars for o in opens):
            continue

        win = HTFWindow(
            bars=tuple(htf_bars[o] for o in opens),
            vol_sma=htf_vol_sma[opens[0]],
        )

        if not state.in_zone_window:
            continue  # Pine patternDetected = first5mTick and inZoneWindow

        pattern = detect_sd_pattern(win, cfg, inst, atr=history.atr)
        if pattern is None:
            continue
        stats["patterns"] += 1

        if book.create_from_pattern(pattern, now_ms=ts) is not None:
            stats["zones"] += 1

    return book, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--exchange", choices=sorted(_PAIRS), default="binance")
    src.add_argument("--csv", type=Path, help="Dukascopy 1m CSV (dt,o,h,l,c,vol; UTC) namiesto burzy")
    ap.add_argument("--profile", default="golden_binance_btcusdt_3m")
    ap.add_argument("--chart-tf", type=int, default=3, help="timeframe grafu v minutach")
    ap.add_argument("--limit", type=int, default=15, help="kolko zon vypisat")
    args = ap.parse_args(argv)

    cfg, inst = load_profile(args.profile)
    for w in cfg.check_instrument(inst):
        print(f"  ! {w}", file=sys.stderr)

    source = args.csv or args.exchange
    book, stats = scan(cfg, inst, source, args.chart_tf)

    from datetime import datetime, timezone

    def fmt(ms: int) -> str:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    print(f"\nProfil {args.profile} na {source}, graf {args.chart_tf}m, detekcia {cfg.zoneDetectionTF}m")
    print(f"  barov grafu:        {stats['bars']}")
    print(f"  v zone okne:        {stats['in_zone_window']}")
    print(f"  uzavretych HTF:     {stats['htf_closes']}")
    print(f"  najdenych patternov:{stats['patterns']}")
    print(f"  vytvorenych zon:    {stats['zones']}  (v evidencii {len(book)}, vyhodenych {book.evicted})")

    if book.zones:
        print(f"\n  {'uid':>4}  {'smer':<5} {'variant':<9} {'od':<16} {'do':<16} {'top':>10} {'bot':>10}")
        for z in book.zones[-args.limit :]:
            direction = "LONG" if int(z.direction) == 1 else "SHORT"
            print(
                f"  {z.uid:>4}  {direction:<5} {z.variant:<9} {fmt(z.created_ms):<16} "
                f"{fmt(z.expires_ms):<16} {z.top:>10.2f} {z.bot:>10.2f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
