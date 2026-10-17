"""Prehľady pre Telegram agenta z denníka obchodov (docs/LIVE.md, „Telegram“): 🧾 Obchody a 📈 Výkon.

Funkcie vracajú `(text HTML, gombíky)` ako ostatné pohľady `TelegramCommands`. Gombíky (`callback_data`):
`tr:<k>` obchody, `pf:<obdobie>:<k>` výkon, `gr:<obdobie>:<k>` graf equity (`k` = `ikey` inštancie alebo
`*` všetky, obdobie `d` dnes / `7` / `30` / `a` všetko).
"""

from __future__ import annotations

import html
import time
from typing import Any

from . import perf

__all__ = ["PERIODS", "trades_view", "perf_view", "perf_chart", "since_ms"]

PERIODS = {"d": "Dnes", "7": "7 dní", "30": "30 dní", "a": "Všetko"}
#: Koľko orderov ukáže 🧾 Obchody.
TRADES_SHOWN = 15


def _e(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=False)


def _num(x: Any) -> str:
    if not isinstance(x, (int, float)):
        return "—"
    return f"{x:.2f}".rstrip("0").rstrip(".") if abs(x) >= 1 else f"{x:.6g}"


def _money(x: Any, unit: str = "$") -> str:
    if not isinstance(x, (int, float)):
        return "—"
    return f"{x:+,.2f} {unit}".replace(",", " ")


def _side(d: Any) -> str:
    return "LONG" if d == 1 else "SHORT" if d == -1 else "?"


def _sym(symbol: Any) -> str:
    return str(symbol or "?").split(" ", 1)[0].split(".", 1)[0]


def _plat(p: Any) -> str:
    return {"ninjatrader": "NT8", "mt5": "MT5"}.get(str(p), str(p or "?"))


def _when(ms: Any) -> str:
    if not isinstance(ms, (int, float)):
        return "—"
    return time.strftime("%d.%m. %H:%M", time.localtime(float(ms) / 1000.0))


def since_ms(period: str, now: float) -> float | None:
    if period == "d":
        lt = time.localtime(now)
        return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)) * 1000.0
    if period in ("7", "30"):
        return (now - int(period) * 86400) * 1000.0
    return None


def _instances(records: list[dict[str, Any]], ikey: Any) -> dict[str, dict[str, Any]]:
    """`ikey` → popis inštancie (z posledného záznamu), v poradí platforma, symbol, stratégia."""
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        if r.get("instance"):
            out[ikey(r["instance"])] = {f: r.get(f) for f in ("instance", "platform", "account", "symbol", "tf", "strategy")}
    return dict(sorted(out.items(), key=lambda kv: (str(kv[1]["platform"]), str(kv[1]["symbol"]), str(kv[1]["strategy"]))))


def _name(i: dict[str, Any]) -> str:
    return f"{_sym(i.get('symbol'))} {i.get('strategy') or '?'}"


def _strategy_rows(inst: dict[str, dict[str, Any]], prefix: str, kluc: str) -> list[list[dict[str, str]]]:
    gomb = [{"text": ("• " if k == kluc else "") + _name(i)[:38], "callback_data": f"{prefix}{k}"} for k, i in inst.items()]
    rows = [gomb[j:j + 2] for j in range(0, len(gomb), 2)]
    if len(inst) > 1:
        rows.append([{"text": ("• " if kluc == "*" else "") + "Všetky stratégie", "callback_data": f"{prefix}*"}])
    return rows


def trades_view(records: list[dict[str, Any]], kluc: str, ikey: Any) -> tuple[str, list[list[dict]]]:
    """Posledné ordery: uzavreté s P&L, otvorené, čakajúce a zrušené."""
    inst = _instances(records, ikey)
    vyber = records if kluc == "*" else [r for r in records if r.get("instance") and ikey(r["instance"]) == kluc]
    kto = "všetky stratégie" if kluc == "*" else _name(inst.get(kluc) or {})
    riadky = [f"<b>🧾 Obchody</b> · {_e(kto)} · posledných {TRADES_SHOWN}"]
    ords = perf.orders(vyber)[:TRADES_SHOWN]
    for o in ords:
        meno = f"<b>{_e(_sym(o.get('symbol')))}</b> {_e(o.get('strategy'))}"
        if kluc != "*":
            meno = ""
        smer = _side(o.get("dir"))
        if o["state"] == "closed":
            usd = o.get("usd")
            ikona = "✅" if (usd if usd is not None else o.get("pts") or 0) > 0 else \
                "❌" if (usd if usd is not None else o.get("pts") or 0) < 0 else "⚪"
            vysl = _money(usd) if usd is not None else f"{_num(o.get('pts'))} b"
            riadky.append(f"{ikona} {_when(o.get('t'))} {meno} {smer} × {_num(o.get('qty'))} "
                          f"{_num(o.get('price_in'))} → {_num(o.get('price_out'))} · <b>{_e(vysl)}</b>"
                          + (f" ({_e(o.get('exit'))})" if o.get("exit") else ""))
        elif o["state"] == "open":
            riadky.append(f"🟢 {_when(o.get('t'))} {meno} {smer} × {_num(o.get('qty'))} @ {_num(o.get('price_in'))} · otvorený")
        elif o["state"] == "cancelled":
            riadky.append(f"🚫 {_when(o.get('t'))} {meno} zrušený {smer} {_e(o.get('ot') or '')} @ {_num(o.get('e'))}"
                          + (f" ({_e(o.get('reason'))})" if o.get("reason") and o.get("reason") != "cancel" else ""))
        else:
            riadky.append(f"⏳ {_when(o.get('t'))} {meno} čaká {smer} {_e(o.get('ot') or '')} @ {_num(o.get('e'))}"
                          f" × {_num(o.get('q'))}")
    if not ords:
        riadky.append("\nZatiaľ žiadne ordery v denníku.")
    riadky.append("\n<i>Z telemetrie stratégií (spool); P&L hrubý, bez poplatkov.</i>")
    rows = _strategy_rows(inst, "tr:", kluc)
    rows.append([{"text": "🔄 Obnoviť", "callback_data": f"tr:{kluc}"}, {"text": "📈 Výkon", "callback_data": f"pf:30:{kluc}"}])
    return "\n".join(r.replace("  ", " ") for r in riadky), rows


def _summary_lines(s: dict[str, Any]) -> list[str]:
    u = s["unit"]
    pct = f" ({s['pnl_pct']:+.2f} %)" if s.get("pnl_pct") is not None else ""
    pf = s.get("profit_factor")
    pf_t = "∞" if pf == float("inf") else _num(pf) if pf is not None else "—"
    dd_pct = f" ({-s['max_drawdown_pct']:.2f} %)" if s.get("max_drawdown_pct") is not None else ""
    out = [f"Obchody <b>{s['trades']}</b> · ✅ {s['wins']} / ❌ {s['losses']} / ⚪ {s['draws']} · winrate <b>{s['winrate']:.1f} %</b>",
           f"P&L <b>{_e(_money(s['pnl_abs'], u))}</b>{pct} · PF {pf_t}",
           f"Max DD {_e(_money(-s['max_drawdown_abs'], u))}{dd_pct} · séria {s['streaks']['wins']} výhier / "
           f"{s['streaks']['losses']} prehier"]
    if s["trades"]:
        out.append(f"Priemer výhra {_e(_money(s.get('avg_win'), u))} / prehra {_e(_money(s.get('avg_loss'), u))} · "
                   f"najlepší {_e(_money(s.get('best'), u))} / najhorší {_e(_money(s.get('worst'), u))}")
    if s.get("starting_balance") and s.get("final_balance") is not None:
        out.append(f"Kapitál {s['starting_balance']:,.0f} → {s['final_balance']:,.2f} $".replace(",", " "))
    if s.get("exits"):
        out.append("Výstupy: " + ", ".join(f"{_e(k)} {v}" for k, v in sorted(s["exits"].items(), key=lambda kv: -kv[1])))
    return out


def _select(records: list[dict[str, Any]], period: str, kluc: str, ikey: Any, now: float) -> list[dict[str, Any]]:
    od = since_ms(period, now)
    tr = perf.trades(records)
    return [t for t in tr if (kluc == "*" or ikey(t["instance"]) == kluc) and (od is None or float(t["t"]) >= od)]


def perf_view(records: list[dict[str, Any]], period: str, kluc: str, capital_cfg: Any, ikey: Any,
              now: float) -> tuple[str, list[list[dict]]]:
    """Výkon za obdobie: súhrn ako v Testeri a pri všetkých stratégiách riadok na každú."""
    period = period if period in PERIODS else "30"
    inst = _instances(records, ikey)
    tr = _select(records, period, kluc, ikey, now)
    ucty = {str(t.get("account")) for t in tr} or ({str(inst[kluc].get("account"))} if kluc in inst else set())
    s = perf.summary(tr, perf.capital_for(capital_cfg, ucty))
    kto = "všetky stratégie" if kluc == "*" else _name(inst.get(kluc) or {}) + f" · {_plat((inst.get(kluc) or {}).get('platform'))}"
    riadky = [f"<b>📈 Výkon</b> · {PERIODS[period]} · {_e(kto)}", ""] + _summary_lines(s)
    if kluc == "*" and len({t["instance"] for t in tr}) > 1:
        riadky.append("\n<b>Po stratégiách</b>")
        for k, i in inst.items():
            moje = [t for t in tr if t["instance"] == i["instance"]]
            if not moje:
                continue
            si = perf.summary(moje, perf.capital_for(capital_cfg, {str(i.get("account"))}))
            pct = f" ({si['pnl_pct']:+.2f} %)" if si.get("pnl_pct") is not None else ""
            riadky.append(f"• <b>{_e(_sym(i.get('symbol')))}</b> {_e(i.get('strategy'))} {_e(_plat(i.get('platform')))} · "
                          f"{si['trades']} obch. · {si['winrate']:.0f} % · {_e(_money(si['pnl_abs'], si['unit']))}{pct}")
    if not tr:
        riadky.append("\nV tomto období žiadny uzavretý obchod.")
    riadky.append("\n<i>Z telemetrie (spool); P&L hrubý, bez poplatkov"
                  + ("" if s.get("pnl_pct") is not None or not tr else "; % chce „capital“ v telegram.json") + ".</i>")
    obdobia = [{"text": ("• " if p == period else "") + t, "callback_data": f"pf:{p}:{kluc}"} for p, t in PERIODS.items()]
    rows = [obdobia] + _strategy_rows(inst, f"pf:{period}:", kluc)
    rows.append([{"text": "🖼 Graf", "callback_data": f"gr:{period}:{kluc}"},
                 {"text": "🧾 Obchody", "callback_data": f"tr:{kluc}"},
                 {"text": "🔄", "callback_data": f"pf:{period}:{kluc}"}])
    return "\n".join(riadky), rows


def perf_chart(records: list[dict[str, Any]], period: str, kluc: str, capital_cfg: Any, ikey: Any,
               now: float) -> tuple[bytes | None, str]:
    """Graf equity za obdobie a popis pod obrázkom (HTML); bez obchodov alebo bez Pillow obrázok None."""
    period = period if period in PERIODS else "30"
    inst = _instances(records, ikey)
    tr = _select(records, period, kluc, ikey, now)
    kto = "všetky stratégie" if kluc == "*" else _name(inst.get(kluc) or {})
    s = perf.summary(tr, perf.capital_for(capital_cfg, {str(t.get("account")) for t in tr}))
    png = perf.equity_png(tr, f"{kto} · {PERIODS[period]}")
    pct = f" ({s['pnl_pct']:+.2f} %)" if s.get("pnl_pct") is not None else ""
    popis = (f"<b>📈 {_e(kto)}</b> · {PERIODS[period]}\n{s['trades']} obchodov · winrate {s['winrate']:.1f} % · "
             f"{_e(_money(s['pnl_abs'], s['unit']))}{pct}")
    return png, popis
