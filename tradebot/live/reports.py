"""Prehľady pre Telegram agenta z denníka obchodov (docs/LIVE.md, „Telegram“): 🧾 Obchody a 📈 Výkon.

Funkcie vracajú `(text HTML, gombíky)` ako ostatné pohľady `TelegramCommands`. Gombíky (`callback_data`):
`tr:<k>` obchody, `pf:<obdobie>:<k>` výkon, `gr:<obdobie>:<k>` graf equity (`k` = `ikey` inštancie, `@<akey>`
účet alebo `*` všetky, obdobie `d` dnes / `7` / `30` / `a` všetko), `ga:<obdobie>` grafy spolu a po účtoch.
"""

from __future__ import annotations

import html
import time
from typing import Any

from . import perf

__all__ = ["PERIODS", "accounts", "trades_view", "perf_view", "perf_chart", "since_ms"]

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


def accounts(records: list[dict[str, Any]], akey: Any) -> dict[str, dict[str, Any]]:
    """`akey` → {platform, account} účtov v záznamoch, zoradené platforma → účet."""
    out: dict[str, dict[str, Any]] = {}
    for r in records:
        if r.get("instance"):
            out[akey(r.get("platform"), r.get("account"))] = {"platform": r.get("platform"), "account": r.get("account")}
    return dict(sorted(out.items(), key=lambda kv: (str(kv[1]["platform"]), str(kv[1]["account"]))))


def _acc_name(a: dict[str, Any]) -> str:
    return f"{_plat(a.get('platform'))} · {a.get('account') or '?'}"


def _who(kluc: str, inst: dict[str, dict[str, Any]], ucty: dict[str, dict[str, Any]], plat: bool = False) -> str:
    if kluc == "*":
        return "všetky účty spolu" if len(ucty) > 1 else "všetky stratégie"
    if kluc.startswith("@"):
        return "účet " + _acc_name(ucty.get(kluc[1:]) or {})
    i = inst.get(kluc) or {}
    return _name(i) + (f" · {_plat(i.get('platform'))}" if plat else "")


def _account_rows(ucty: dict[str, dict[str, Any]], prefix: str, kluc: str) -> list[list[dict[str, str]]]:
    """Gombíky účtov (len pri viac účtoch) a „Všetky účty spolu“."""
    if len(ucty) < 2:
        return []
    gomb = [{"text": ("• " if kluc == f"@{k}" else "") + "👤 " + _acc_name(a)[:34], "callback_data": f"{prefix}@{k}"}
            for k, a in ucty.items()]
    rows = [gomb[j:j + 2] for j in range(0, len(gomb), 2)]
    rows.append([{"text": ("• " if kluc == "*" else "") + "👥 Všetky účty spolu", "callback_data": f"{prefix}*"}])
    return rows


def _strategy_rows(inst: dict[str, dict[str, Any]], prefix: str, kluc: str,
                   with_all_accounts: bool = False) -> list[list[dict[str, str]]]:
    gomb = [{"text": ("• " if k == kluc else "") + _name(i)[:38], "callback_data": f"{prefix}{k}"} for k, i in inst.items()]
    rows = [gomb[j:j + 2] for j in range(0, len(gomb), 2)]
    if len(inst) > 1 and not with_all_accounts:
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


def _match(t: dict[str, Any], kluc: str, ikey: Any, akey: Any) -> bool:
    if kluc == "*":
        return True
    if kluc.startswith("@"):
        return akey is not None and akey(t.get("platform"), t.get("account")) == kluc[1:]
    return ikey(t["instance"]) == kluc


def _select(records: list[dict[str, Any]], period: str, kluc: str, ikey: Any, now: float,
            akey: Any = None) -> list[dict[str, Any]]:
    od = since_ms(period, now)
    tr = perf.trades(records)
    return [t for t in tr if _match(t, kluc, ikey, akey) and (od is None or float(t["t"]) >= od)]


def _capital(capital_cfg: Any, tr: list[dict[str, Any]], kluc: str, inst: dict[str, dict[str, Any]],
             ucty: dict[str, dict[str, Any]]) -> float | None:
    mena = {str(t.get("account")) for t in tr}
    if not mena and kluc in inst:
        mena = {str(inst[kluc].get("account"))}
    if not mena and kluc.startswith("@") and kluc[1:] in ucty:
        mena = {str(ucty[kluc[1:]].get("account"))}
    return perf.capital_for(capital_cfg, mena)


def perf_view(records: list[dict[str, Any]], period: str, kluc: str, capital_cfg: Any, ikey: Any,
              now: float, akey: Any = None) -> tuple[str, list[list[dict]]]:
    """Výkon za obdobie: súhrn ako v Testeri, pri všetkých riadok na každý účet (keď ich je viac) a na každú
    stratégiu. `kluc` = `*`, `ikey` inštancie alebo `@<akey>` účtu (`akey` = kľúč účtu, bez neho bez účtov)."""
    period = period if period in PERIODS else "30"
    inst = _instances(records, ikey)
    ucty = accounts(records, akey) if akey is not None else {}
    tr = _select(records, period, kluc, ikey, now, akey)
    s = perf.summary(tr, _capital(capital_cfg, tr, kluc, inst, ucty))
    kto = _who(kluc, inst, ucty, plat=True)
    riadky = [f"<b>📈 Výkon</b> · {PERIODS[period]} · {_e(kto)}", ""] + _summary_lines(s)
    if kluc == "*" and len(ucty) > 1:
        riadky.append("\n<b>Po účtoch</b>")
        for k, a in ucty.items():
            moje = [t for t in tr if akey(t.get("platform"), t.get("account")) == k]
            if not moje:
                continue
            si = perf.summary(moje, perf.capital_for(capital_cfg, {str(a.get("account"))}))
            pct = f" ({si['pnl_pct']:+.2f} %)" if si.get("pnl_pct") is not None else ""
            riadky.append(f"• <b>{_e(_acc_name(a))}</b> · {si['trades']} obch. · {si['winrate']:.0f} % · "
                          f"{_e(_money(si['pnl_abs'], si['unit']))}{pct}")
    if (kluc == "*" or kluc.startswith("@")) and len({t["instance"] for t in tr}) > 1:
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
    acc_rows = _account_rows(ucty, f"pf:{period}:", kluc)
    rows = [obdobia] + acc_rows + _strategy_rows(inst, f"pf:{period}:", kluc, with_all_accounts=bool(acc_rows))
    rows.append([{"text": "🖼 Graf", "callback_data": f"gr:{period}:{kluc}"},
                 {"text": "🧾 Obchody", "callback_data": f"tr:{'*' if kluc.startswith('@') else kluc}"},
                 {"text": "🔄", "callback_data": f"pf:{period}:{kluc}"}])
    if acc_rows:
        rows.append([{"text": "🖼 Grafy: spolu + po účtoch", "callback_data": f"ga:{period}"}])
    return "\n".join(riadky), rows


def perf_chart(records: list[dict[str, Any]], period: str, kluc: str, capital_cfg: Any, ikey: Any,
               now: float, akey: Any = None) -> tuple[bytes | None, str]:
    """Graf equity za obdobie a popis pod obrázkom (HTML); bez obchodov alebo bez Pillow obrázok None.
    `kluc` = `*` (všetky účty spolu), `ikey` inštancie alebo `@<akey>` účtu."""
    period = period if period in PERIODS else "30"
    inst = _instances(records, ikey)
    ucty = accounts(records, akey) if akey is not None else {}
    tr = _select(records, period, kluc, ikey, now, akey)
    kto = _who(kluc, inst, ucty)
    s = perf.summary(tr, _capital(capital_cfg, tr, kluc, inst, ucty))
    png = perf.equity_png(tr, f"{kto} · {PERIODS[period]}")
    pct = f" ({s['pnl_pct']:+.2f} %)" if s.get("pnl_pct") is not None else ""
    popis = (f"<b>📈 {_e(kto)}</b> · {PERIODS[period]}\n{s['trades']} obchodov · winrate {s['winrate']:.1f} % · "
             f"{_e(_money(s['pnl_abs'], s['unit']))}{pct}")
    return png, popis
