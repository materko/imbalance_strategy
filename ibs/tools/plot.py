"""Vykreslí to, čo engine nakreslil — na porovnanie s grafom v TradingView.

    python -m ibs.tools.plot --profile golden_binance_btcusdt_3m --exchange binance \
        --from 2026-08-24 --to 2026-09-04 -o graf.html

Engine sám nekreslí — vracia `DrawCommand`. Tento nástroj ich prehrá cez
`DrawRegistry` (takže vidno finálny stav vrátane `box.set_*` zmien, presne ako
v Pine) a vysype do samostatného HTML.

Zámerne to **nie je** kópia vzhľadu TradingView. Presnosť sa meria číselne
golden testom proti Pine logom; obrázok je na rýchlu kontrolu okom.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ..core import (
    Bar,
    DrawBg,
    DrawBox,
    DrawKind,
    DrawLabel,
    DrawLine,
    DrawRegistry,
    HTFWindow,
    IBSEngine,
    MarketContext,
    SessionClock,
    htf_window_opens,
    load_profile,
)
from .scan_zones import _load, _to_bar

#: Poradie vykreslenia — čo je nižšie, kreslí sa navrch.
_LAYER = {
    DrawKind.SESSION: 0,
    DrawKind.SD_ZONE_PRE: 1,
    DrawKind.SD_ZONE_POST: 1,
    DrawKind.SR_GOLDEN: 1,
    DrawKind.SR_LEVEL: 1,
    DrawKind.TP_BOX: 2,
    DrawKind.SL_BOX: 2,
}


def run(profile: str, exchange: str, chart_tf: int, date_from: str | None, date_to: str | None):
    """Prehrá engine a vráti (sviečky, registry)."""
    import pandas as pd

    cfg, inst = load_profile(profile)
    htf_minutes = int(cfg.zoneDetectionTF)

    chart = _load(exchange, f"{chart_tf}m")
    htf_df = _load(exchange, f"{htf_minutes}m")
    if date_from:
        start = pd.Timestamp(date_from, tz="UTC")
        chart = chart[chart["date"] >= start]
        htf_df = htf_df[htf_df["date"] >= start]
    if date_to:
        end = pd.Timestamp(date_to, tz="UTC") + pd.Timedelta(days=1)
        chart = chart[chart["date"] < end]
        htf_df = htf_df[htf_df["date"] < end]
    if chart.empty:
        raise SystemExit("V zadanom rozsahu nie su ziadne sviecky.")

    htf_df = htf_df.copy()
    htf_df["vol_sma"] = htf_df["volume"].rolling(cfg.volSmaLen).mean()
    htf_bars = {int(r.ts): _to_bar(r) for r in htf_df.itertuples(index=False)}
    htf_sma = {
        int(r.ts): (float(r.vol_sma) if r.vol_sma == r.vol_sma else 0.0)
        for r in htf_df.itertuples(index=False)
    }

    clock = SessionClock(cfg)
    engine = IBSEngine(cfg, inst, chart_tf)
    registry = DrawRegistry()
    htf_ms = htf_minutes * 60_000
    step = chart_tf * 60_000

    bars: list[Bar] = []
    prev_htf_open: int | None = None
    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        bars.append(bar)

        window = None
        htf_open = bar.time // htf_ms * htf_ms
        if prev_htf_open is not None and htf_open != prev_htf_open:
            opens = htf_window_opens(bar.time, step, htf_ms)
            if all(o in htf_bars for o in opens):
                window = HTFWindow(tuple(htf_bars[o] for o in opens), htf_sma[opens[0]])
        prev_htf_open = htf_open

        st = clock.state(bar.time)
        out = engine.on_bar(bar, window, MarketContext(in_trade_window=st.in_trade_window))
        registry.extend(out.drawings)

    # Pine `barstate.islast` — S/R a Elliott sa kreslia až na poslednom bare.
    registry.extend(engine.final_drawings(bars[-1]))
    return bars, registry, cfg


def _ts(ms: int):
    import pandas as pd

    return pd.Timestamp(ms, unit="ms", tz="UTC")


def render(bars, registry: DrawRegistry, title: str, out_path: Path) -> None:
    import plotly.graph_objects as go

    fig = go.Figure(
        go.Candlestick(
            x=[_ts(b.time) for b in bars],
            open=[b.open for b in bars],
            high=[b.high for b in bars],
            low=[b.low for b in bars],
            close=[b.close for b in bars],
            name="cena",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        )
    )

    objects = sorted(registry.objects(), key=lambda o: _LAYER.get(o.kind, 3))
    shapes, annotations = [], []

    for o in objects:
        if isinstance(o, DrawBg):
            # Pás pozadia cez celú výšku - v plotly `yref="paper"`.
            shapes.append(
                dict(
                    type="rect", xref="x", yref="paper", layer="below",
                    x0=_ts(o.x1_ms), x1=_ts(o.x2_ms), y0=0, y1=1,
                    fillcolor=o.color, line=dict(width=0),
                )
            )
        elif isinstance(o, DrawBox):
            shapes.append(
                dict(
                    type="rect", xref="x", yref="y",
                    layer="below" if _LAYER.get(o.kind, 3) <= 1 else "above",
                    x0=_ts(o.x1_ms), x1=_ts(o.x2_ms), y0=o.y2, y1=o.y1,
                    fillcolor=o.fill_color or "rgba(0,0,0,0)",
                    line=dict(
                        color=o.border_color,
                        width=o.border_width,
                        dash={"dotted": "dot", "dashed": "dash"}.get(o.border_style.value, "solid"),
                    ),
                )
            )
        elif isinstance(o, DrawLine):
            shapes.append(
                dict(
                    type="line", xref="x", yref="y",
                    x0=_ts(o.x1_ms), x1=_ts(o.x2_ms), y0=o.y1, y1=o.y2,
                    line=dict(
                        color=o.color, width=o.width,
                        dash={"dotted": "dot", "dashed": "dash"}.get(o.style.value, "solid"),
                    ),
                )
            )
        elif isinstance(o, DrawLabel):
            annotations.append(
                dict(
                    x=_ts(o.x_ms), y=o.y, text=o.text.replace("\n", "<br>"),
                    showarrow=False, font=dict(size=9, color=o.color),
                    bgcolor=o.bg_color, borderpad=2,
                    yanchor="bottom" if o.above else "top",
                )
            )

    fig.update_layout(
        title=title,
        shapes=shapes,
        annotations=annotations,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=900,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    # Bez toho plotly dokresli aj vikendy/medzery, kde ziadne sviecky nie su.
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])] if _has_weekend_gap(bars) else [])
    fig.write_html(str(out_path), include_plotlyjs="cdn")


def _has_weekend_gap(bars) -> bool:
    """Krypto beží nonstop — rangebreak by tam len zbytočne rezal graf."""
    import pandas as pd

    days = {pd.Timestamp(b.time, unit="ms", tz="UTC").dayofweek for b in bars}
    return not ({5, 6} <= days)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--exchange", default="binance", choices=["binance", "coinbase"])
    ap.add_argument("--profile", default="golden_binance_btcusdt_3m")
    ap.add_argument("--chart-tf", type=int, default=3)
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vratane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vratane")
    ap.add_argument("-o", "--out", default="graf.html")
    args = ap.parse_args(argv)

    bars, registry, cfg = run(
        args.profile, args.exchange, args.chart_tf, args.date_from, args.date_to
    )

    counts: dict[str, int] = {}
    for o in registry.objects():
        counts[o.kind.value] = counts.get(o.kind.value, 0) + 1
    print(f"sviecok: {len(bars)}   objektov: {len(registry)}")
    for k, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<16} {n}")

    out = Path(args.out)
    render(bars, registry, f"{args.profile} · {args.exchange} · {args.chart_tf}m", out)
    print(f"\n-> {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
