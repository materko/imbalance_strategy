"""Report z Freqtrade backtestu vo vzhľade TradingView Strategy Testera.

    python -m tradebot.tools.report                      # posledný backtest
    python -m tradebot.tools.report vysledok.zip -o r.html
    python -m tradebot.tools.report --list

Freqtrade sype výsledky do terminálu ako ASCII tabuľky, TradingView ukazuje
kartu s Key stats a krivkou. Toto je to druhé nad prvým — rovnaké štyri čísla
hore (Total PnL, Max drawdown, Profitable trades, Profit factor), rovnaká
krivka (kumulatívny PnL + buy and hold + stĺpce za obchod) a pod tým tabuľky,
ktoré TradingView nemá.

Číta `backtest_results/*.zip`, ktorý Freqtrade zapíše po každom behu — žiadne
prepočty sa tu nerobia, len sa kreslí to, čo je v ňom.

**Percentá sú z počiatočného kapitálu**, ako v TradingView, nie z aktuálneho
zostatku. Freqtrade v termináli udáva `Tot Profit %` rovnako, ale `Avg Profit %`
je priemer z jednotlivých pozícií — tie dve čísla sa nedajú porovnávať.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "platforms" / "freqtrade" / "user_data" / "backtest_results"

#: Rovnaké farby ako Strategy Tester, aby sa dali obrázky klásť vedľa seba.
GREEN, RED, BLUE = "#089981", "#f23645", "#2962ff"


def newest(directory: Path = RESULTS) -> Path:
    """Najnovší `.zip` — po behu backtestu je to ten, čo práve vznikol."""
    zips = sorted(directory.glob("*.zip"), key=lambda p: p.stat().st_mtime)
    if not zips:
        raise SystemExit(f"V {directory} nie je ziadny vysledok backtestu.")
    return zips[-1]


def load(path: Path):
    """Vráti (stats, trades, market_change) z jedného výsledkového zipu."""
    import pandas as pd

    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        main = next(
            n for n in names if n.endswith(".json") and "config" not in n and "meta" not in n
        )
        data = json.loads(z.read(main))
        name, stats = next(iter(data["strategy"].items()))
        stats["strategy_name"] = name

        # Backtest bez obchodov je bežný výsledok (prísne prahy, krátke okno),
        # a vtedy DataFrame nemá ani stĺpce — konverzia času by spadla na KeyError.
        trades = pd.DataFrame(stats.pop("trades"))
        if not trades.empty:
            for col in ("open_date", "close_date"):
                trades[col] = pd.to_datetime(trades[col], utc=True)

        change = None
        mc = [n for n in names if n.endswith("_market_change.feather")]
        if mc:
            change = pd.read_feather(io.BytesIO(z.read(mc[0])))

    return stats, trades, change


def _fig(stats, trades, change):
    """Krivka ako v Strategy Testeri: kumulatívny PnL, buy and hold, stĺpce."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    start = float(stats["starting_balance"])
    closed = trades.sort_values("close_date")
    pct = closed["profit_abs"] / start * 100.0
    cum = pct.cumsum()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Stĺpce za jednotlivé obchody idú dozadu, krivky na ne. Šírka sa počíta
    # z dĺžky okna — inak by pri stovkách obchodov boli stĺpce užšie než pixel
    # a v grafe by po nich nezostala ani stopa.
    span_ms = (closed["close_date"].max() - closed["close_date"].min()).total_seconds() * 1000
    width = max(span_ms / max(len(closed), 1) * 0.7, 60_000)
    fig.add_bar(
        x=closed["close_date"],
        y=pct,
        name="PnL obchodu",
        marker_color=[GREEN if v >= 0 else RED for v in pct],
        marker_line_width=0,
        width=width,
        opacity=0.85,
        hovertemplate="%{x|%d.%m. %H:%M}<br>%{y:+.2f} %<extra></extra>",
        secondary_y=True,
    )
    fig.add_scatter(
        x=closed["close_date"],
        y=cum,
        name="Kumulatívny PnL",
        mode="lines+markers",
        line=dict(color=GREEN, width=2),
        marker=dict(size=4),
        fill="tozeroy",
        fillcolor="rgba(8,153,129,0.08)",
        hovertemplate="%{x|%d.%m. %H:%M}<br>%{y:+.2f} %<extra></extra>",
    )
    bh = None
    if change is not None and not change.empty:
        # `rel_mean` je zmena ceny páru od začiatku okna — TradingView "Buy and hold".
        # Zahustené 3m dáta by z toho spravili chlpatú čiaru, preto denné vzorky.
        bh = change.set_index("date")["rel_mean"].resample("1D").last().dropna()
        fig.add_scatter(
            x=bh.index,
            y=bh.to_numpy() * 100.0,
            name="Buy and hold",
            mode="lines",
            line=dict(color=BLUE, width=1.2),
            hovertemplate="%{x|%d.%m.}<br>%{y:+.2f} %<extra></extra>",
        )

    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        bargap=0.2,
    )
    # Stĺpce majú vlastnú, skrytú os — inak by jeden obchod (±1 %) stlačil krivku
    # (±50 %) do čiary. Obe osi musia mať **rovnaký pomer**, inak by nula stĺpcov
    # nesedela s nulou krivky a graf by klamal. Preto sa rozsah krivky zafixuje
    # a rozsah stĺpcov je jeho násobok zvolený tak, aby najväčší stĺpec zabral
    # zhruba šestinu výšky.
    lo, hi = float(min(cum.min(), 0.0)), float(max(cum.max(), 0.0))
    if bh is not None and len(bh):
        lo, hi = min(lo, float(bh.min()) * 100), max(hi, float(bh.max()) * 100)
    pad = (hi - lo) * 0.06 or 1.0
    lo, hi = lo - pad, hi + pad
    scale = (hi - lo) / max(float(pct.abs().max()) * 6, 1e-9)

    fig.update_yaxes(ticksuffix=" %", title=None, range=[lo, hi], secondary_y=False)
    fig.update_yaxes(
        range=[lo / scale, hi / scale],
        showgrid=False,
        showticklabels=False,
        secondary_y=True,
    )
    return fig


def _cards(stats, trades) -> str:
    start = float(stats["starting_balance"])
    cur = stats.get("stake_currency", "USDT")
    pnl = float(stats["profit_total_abs"])
    wins, total = int(stats["wins"]), int(stats["total_trades"])
    dd_abs = float(stats["max_drawdown_abs"])
    dd_pct = float(stats["max_drawdown_account"]) * 100.0
    pf = stats.get("profit_factor")

    def card(label, big, small="", cls=""):
        return (
            f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="big {cls}">{big}</div><div class="sml">{small}</div></div>'
        )

    return "".join(
        [
            card(
                "Total PnL",
                f"{pnl:+,.2f} <span class='cur'>{cur}</span>",
                f"{pnl / start * 100:+.2f} %",
                "pos" if pnl >= 0 else "neg",
            ),
            card(
                "Max drawdown",
                f"{dd_abs:,.2f} <span class='cur'>{cur}</span>",
                f"{dd_pct:.2f} %",
            ),
            card(
                "Profitable trades",
                f"{(wins / total * 100 if total else 0):.2f} %",
                f"{wins}/{total}",
            ),
            card("Profit factor", f"{pf:.3f}" if pf else "—"),
        ]
    )


def _trades_table(stats, trades) -> str:
    import pandas as pd

    start = float(stats["starting_balance"])
    rows = []
    for i, t in enumerate(trades.sort_values("open_date").itertuples(index=False), 1):
        short = bool(getattr(t, "is_short", False))
        pnl = float(t.profit_abs)
        rows.append(
            f"<tr><td>{i}</td>"
            f"<td class='{'neg' if short else 'pos'}'>{'Short' if short else 'Long'}</td>"
            f"<td>{pd.Timestamp(t.open_date):%d.%m.%Y %H:%M}</td>"
            f"<td class='num'>{t.open_rate:,.1f}</td>"
            f"<td class='num'>{t.amount:g}</td>"
            f"<td>{pd.Timestamp(t.close_date):%d.%m.%Y %H:%M}</td>"
            f"<td class='num'>{t.close_rate:,.1f}</td>"
            f"<td class='num {'pos' if pnl >= 0 else 'neg'}'>{pnl:+,.2f}</td>"
            f"<td class='num {'pos' if pnl >= 0 else 'neg'}'>{pnl / start * 100:+.2f} %</td>"
            f"<td>{t.exit_reason}</td></tr>"
        )
    head = (
        "<tr><th>#</th><th>Smer</th><th>Vstup</th><th>Cena</th><th>Množstvo</th>"
        "<th>Výstup</th><th>Cena</th><th>PnL</th><th>PnL %</th><th>Dôvod</th></tr>"
    )
    return f"<table class='trades'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def _exit_table(stats) -> str:
    rows = []
    for r in stats.get("exit_reason_summary", []):
        rows.append(
            f"<tr><td>{r['key']}</td>"
            f"<td class='num'>{r['trades']}</td>"
            f"<td class='num pos'>{r['wins']}</td>"
            f"<td class='num neg'>{r['losses']}</td>"
            f"<td class='num'>{r['profit_total_abs']:+,.2f}</td></tr>"
        )
    head = "<tr><th>Dôvod výstupu</th><th>Obchodov</th><th>W</th><th>L</th><th>PnL</th></tr>"
    return f"<table><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>"


def _summary_table(stats, trades) -> str:
    cur = stats.get("stake_currency", "USDT")
    fee = float(trades["fee_open"].iloc[0]) * 100 if len(trades) else 0.0
    funding = float(trades["funding_fees"].sum()) if "funding_fees" in trades else 0.0
    longs, shorts = int(stats["trade_count_long"]), int(stats["trade_count_short"])

    items = [
        ("Obdobie", f"{stats['backtest_start'][:16]} → {stats['backtest_end'][:16]}"),
        ("Dní", f"{stats['backtest_days']}"),
        ("Počiatočný kapitál", f"{stats['starting_balance']:,.0f} {cur}"),
        ("Konečný zostatok", f"{stats['final_balance']:,.2f} {cur}"),
        ("Obchodov (Long / Short)", f"{stats['total_trades']} ({longs} / {shorts})"),
        ("Long PnL / Short PnL", f"{stats['profit_total_long_abs']:+,.2f} / "
                                 f"{stats['profit_total_short_abs']:+,.2f} {cur}"),
        ("Poplatok", f"{fee:.3f} % na stranu"),
        ("Objem / funding", f"{stats['total_volume']:,.0f} {cur} / {funding:+,.2f} {cur}"),
        ("Buy and hold", f"{stats['market_change'] * 100:+.2f} %"),
        ("CAGR", f"{stats['cagr'] * 100:+.2f} %"),
        ("Sharpe / Sortino / Calmar",
         f"{stats['sharpe']:.2f} / {stats['sortino']:.2f} / {stats['calmar']:.2f}"),
        ("Expectancy", f"{stats['expectancy']:+,.2f} {cur} ({stats['expectancy_ratio']:+.2f})"),
        ("Najdlhšia séria W / L",
         f"{stats['max_consecutive_wins']} / {stats['max_consecutive_losses']}"),
        ("Priemerné držanie", f"{stats['holding_avg']}"),
        ("Timeframe", f"{stats['timeframe']} (detail {stats.get('timeframe_detail') or '—'})"),
    ]
    rows = "".join(f"<tr><td>{k}</td><td class='num'>{v}</td></tr>" for k, v in items)
    return f"<table><tbody>{rows}</tbody></table>"


CSS = """
:root { color-scheme: light; }
body { margin:0; padding:24px 32px; background:#fff; color:#131722;
       font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
h1 { font-size:20px; margin:0 0 2px; }
h2 { font-size:16px; margin:32px 0 10px; }
.meta { color:#787b86; font-size:13px; margin-bottom:22px; }
.cards { display:flex; flex-wrap:wrap; gap:48px; margin-bottom:8px; }
.card .lbl { color:#787b86; font-size:13px; }
.card .big { font-size:22px; font-weight:600; margin-top:2px; }
.card .sml { color:#787b86; font-size:13px; }
.card .cur { font-size:13px; font-weight:400; color:#787b86; }
.pos { color:#089981; } .neg { color:#f23645; }
table { border-collapse:collapse; font-size:13px; }
th,td { padding:5px 12px; border-bottom:1px solid #e0e3eb; text-align:left;
        white-space:nowrap; }
th { color:#787b86; font-weight:500; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
.scroll { max-height:520px; overflow:auto; border:1px solid #e0e3eb; border-radius:6px; }
.scroll table { width:100%; }
.scroll thead th { position:sticky; top:0; background:#fff; }
.cols { display:flex; gap:48px; flex-wrap:wrap; align-items:flex-start; }
"""


def render(stats, trades, change, out: Path) -> Path:
    fig = _fig(stats, trades, change)
    chart = fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displaylogo": False})

    pair = ", ".join(stats.get("pairlist", []))
    html = f"""<!doctype html><html lang="sk"><head><meta charset="utf-8">
<title>{stats['strategy_name']} — backtest</title><style>{CSS}</style></head><body>
<h1>{stats['strategy_name']}</h1>
<div class="meta">{pair} &middot; {stats['timeframe']} &middot;
{stats['backtest_start'][:10]} — {stats['backtest_end'][:10]} &middot;
{stats['starting_balance']:,.0f} {stats.get('stake_currency', 'USDT')}</div>
<h2>Key stats</h2>
<div class="cards">{_cards(stats, trades)}</div>
<h2>Performance</h2>
{chart}
<div class="cols">
  <div><h2>Dôvody výstupu</h2>{_exit_table(stats)}</div>
  <div><h2>Zhrnutie</h2>{_summary_table(stats, trades)}</div>
</div>
<h2>Zoznam obchodov</h2>
<div class="scroll">{_trades_table(stats, trades)}</div>
</body></html>"""

    out.write_text(html, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("result", nargs="?", help="cesta k backtest_results/*.zip (default: posledny)")
    ap.add_argument("-o", "--out", default=None, help="kam zapisat HTML")
    ap.add_argument("--list", action="store_true", help="vypis dostupne vysledky a skonci")
    args = ap.parse_args(argv)

    if args.list:
        for p in sorted(RESULTS.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
            print(f"  {p.name}  {p.stat().st_size / 1e6:.1f} MB")
        return 0

    path = Path(args.result) if args.result else newest()
    stats, trades, change = load(path)
    if trades.empty:
        raise SystemExit(f"{path.name}: backtest nema ziadne obchody.")

    out = Path(args.out) if args.out else path.with_suffix(".html")
    render(stats, trades, change, out)
    print(f"{path.name}  ->  {out}")
    print(
        f"  {stats['total_trades']} obchodov, "
        f"PnL {stats['profit_total_abs']:+,.2f} {stats.get('stake_currency', 'USDT')} "
        f"({stats['profit_total'] * 100:+.2f} %), PF {stats.get('profit_factor', 0):.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
