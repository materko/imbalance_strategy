"""Prejde reálne dáta a vypíše, aké SD zóny by vznikli — smoke test kroku 2.

Nie je to backtest, orderov sa netýka. Overuje presne to, čo je v tejto fáze
hotové: session okná + detekciu SD zón na detekčnom TF + evidenciu zón.

    python -m tradebot.tools.scan_zones --exchange binance --profile golden_binance_btcusdt_3m
    python -m tradebot.tools.scan_zones --exchange coinbase --profile golden_coinbase_btcusd_3m --limit 20

Vyžaduje pandas (ťahá sa s Freqtrade), takže sa spúšťa z `.venv`, nie z jadra.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core import (
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

DATA_DIR = Path(__file__).resolve().parents[2] / "platforms" / "freqtrade" / "user_data" / "data"

#: Kde ktorá burza drží súbory a ako sa volajú.
_LAYOUT = {
    "binance": ("BTC_USDT_USDT", "futures", "-futures"),
    "coinbase": ("BTC_USD", "", ""),
}


def _load(exchange: str, timeframe: str):
    """Načíta sviečky. Ak burza daný TF neponúka, poskladá ho z 1m **v pamäti**.

    Na disk sa nikdy nič dopočítané nezapisuje — v `user_data/data` sú výhradne
    skutočné burzové sviečky. Presne to isté bude robiť aj Freqtrade stratégia
    (napr. Coinbase 3m, ktoré burza neponúka).
    """
    import pandas as pd

    pair, subdir, suffix = _LAYOUT[exchange]
    path = DATA_DIR / exchange / subdir / f"{pair}-{timeframe}{suffix}.feather"

    if not path.exists():
        minutes = int(timeframe.rstrip("m"))
        src = DATA_DIR / exchange / subdir / f"{pair}-1m{suffix}.feather"
        if not src.exists():
            raise SystemExit(
                f"Chybaju data: {path}\n"
                "Stiahni ich: ./platforms/freqtrade/scripts/download-data.sh (alebo .ps1)"
            )
        print(f"  i {exchange} neponuka {timeframe} - skladam ho z 1m v pamati", file=sys.stderr)
        base = pd.read_feather(src)
        df = (
            base.set_index("date")
            .resample(f"{minutes}min", label="left", closed="left", origin="epoch")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna(subset=["open"])
            .reset_index()
        )
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
    exchange: str,
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
    ap.add_argument("--exchange", choices=sorted(_LAYOUT), default="binance")
    ap.add_argument("--profile", default="golden_binance_btcusdt_3m")
    ap.add_argument("--chart-tf", type=int, default=3, help="timeframe grafu v minutach")
    ap.add_argument("--limit", type=int, default=15, help="kolko zon vypisat")
    args = ap.parse_args(argv)

    cfg, inst = load_profile(args.profile)
    for w in cfg.check_instrument(inst):
        print(f"  ! {w}", file=sys.stderr)

    book, stats = scan(cfg, inst, args.exchange, args.chart_tf)

    from datetime import datetime, timezone

    def fmt(ms: int) -> str:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    print(f"\nProfil {args.profile} na {args.exchange}, graf {args.chart_tf}m, detekcia {cfg.zoneDetectionTF}m")
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
