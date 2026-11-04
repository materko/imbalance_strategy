"""Výkon live stratégií z denníka obchodov (`tradebot.live.journal`) — tie isté čísla ako súhrn behu
v Testeri (`tester.webapp.results`): obchody, výhry / prehry / remízy, winrate, P&L $ a %, profit
factor, max drawdown $ a %, najdlhšia séria, výstupy. Plus graf equity (PNG cez Pillow).

Obchod = jedno id vstupu; čiastočné výstupy sa sčítajú a obchod je uzavretý posledným výstupom.
P&L je **hrubý** (spool poplatky nenesie). Percentá potrebujú kapitál účtu (`capital` v configu
Telegramu) — bez neho sa neukážu.
"""

from __future__ import annotations

import io
import unicodedata
from typing import Any

__all__ = ["trades", "orders", "summary", "equity_png", "capital_for"]


def trades(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Uzavreté obchody z denníka (podľa času posledného výstupu)."""
    po_id: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        if r.get("k") not in ("in", "out"):
            continue
        kluc = (str(r.get("instance")), str(r.get("id")))
        o = po_id.setdefault(kluc, {"instance": r.get("instance"), "id": r.get("id"), "strategy": r.get("strategy"),
                                    "symbol": r.get("symbol"), "platform": r.get("platform"), "account": r.get("account"),
                                    "tf": r.get("tf"), "dir": r.get("dir"), "qty": 0.0, "entry": None, "t_in": None,
                                    "usd": 0.0, "pts": 0.0, "has_usd": True, "exits": [], "t": None, "closed": False,
                                    "price_out": None})
        if r.get("k") == "in":
            o["t_in"] = o["t_in"] or r.get("t")
            o["qty"] += float(r.get("qty") or 0)
            o["entry"] = r.get("price") if o["entry"] is None else o["entry"]
            o["dir"] = o["dir"] or r.get("dir")
            o["closed"] = False
            continue
        if r.get("pts") is None:   # výstup bez známeho vstupu (denník začal uprostred obchodu)
            continue
        o["pts"] += float(r.get("pts") or 0) * float(r.get("qty") or 0)
        if r.get("usd") is None:
            o["has_usd"] = False
        else:
            o["usd"] += float(r["usd"])
        o["exits"].append(str(r.get("exit") or "?"))
        o["t"], o["price_out"] = r.get("t"), r.get("price")
        o["entry"] = r.get("entry") if r.get("entry") is not None else o["entry"]
        o["closed"] = float(r.get("left") or 0) <= 1e-9
    out = [o for o in po_id.values() if o["closed"] and o["t"] is not None]
    for o in out:
        if not o["has_usd"]:
            o["usd"] = None
    return sorted(out, key=lambda o: float(o["t"]))


def orders(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Životný cyklus orderov (podľa id vstupu): `pending` → `cancelled` | `open` → `closed` (s P&L),
    zoradené od najnovšej zmeny."""
    po_id: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        kluc = (str(r.get("instance")), str(r.get("id")))
        o = po_id.setdefault(kluc, {"instance": r.get("instance"), "id": r.get("id"), "strategy": r.get("strategy"),
                                    "symbol": r.get("symbol"), "platform": r.get("platform"), "dir": r.get("dir"),
                                    "ot": None, "e": None, "q": None, "state": "pending", "t": r.get("t"),
                                    "price_in": None, "price_out": None, "qty": 0.0, "usd": None, "pts": None,
                                    "exit": None, "reason": None})
        o["t"] = r.get("t") or o["t"]
        o["dir"] = o["dir"] or r.get("dir")
        k = r.get("k")
        if k == "entry":
            o.update(ot=r.get("ot"), e=r.get("e"), q=r.get("q"))
        elif k == "cancel":
            o.update(state="cancelled", reason=r.get("r"), ot=o["ot"] or r.get("ot"), e=o["e"] or r.get("e"))
        elif k == "in":
            o["state"] = "open"
            o["qty"] += float(r.get("qty") or 0)
            o["price_in"] = o["price_in"] if o["price_in"] is not None else r.get("price")
        elif k == "out":
            if r.get("usd") is not None:
                o["usd"] = (o["usd"] or 0.0) + float(r["usd"])
            if r.get("pts") is not None:
                o["pts"] = r["pts"]
            o.update(price_out=r.get("price"), exit=r.get("exit"))
            if r.get("entry") is not None and o["price_in"] is None:
                o["price_in"] = r.get("entry")
            o["state"] = "closed" if float(r.get("left") or 0) <= 1e-9 else "open"
    return sorted(po_id.values(), key=lambda o: float(o["t"] or 0), reverse=True)


def capital_for(cfg_capital: Any, accounts: set[str]) -> float | None:
    """Kapitál pre množinu účtov: `capital` = číslo (každý účet), alebo {"<účet alebo jeho časť>": číslo,
    "*": predvolené}. Viac účtov = súčet; účet bez kapitálu = None (percentá sa neukážu)."""
    if not accounts or cfg_capital in (None, "", {}):
        return None
    if isinstance(cfg_capital, (int, float)):
        return float(cfg_capital) * len(accounts)
    if not isinstance(cfg_capital, dict):
        return None
    spolu = 0.0
    for acc in accounts:
        hodnota = cfg_capital.get(acc)
        if hodnota is None:
            hodnota = next((v for k, v in cfg_capital.items() if k != "*" and k and k in str(acc)), None)
        if hodnota is None:
            hodnota = cfg_capital.get("*")
        if not isinstance(hodnota, (int, float)) or hodnota <= 0:
            return None
        spolu += float(hodnota)
    return spolu


def summary(tr: list[dict[str, Any]], capital: float | None = None) -> dict[str, Any]:
    """Súhrn ako v Testeri. `pnl_abs` v $ (None, keď niektorému obchodu chýba hodnota bodu)."""
    n = len(tr)
    usd_ok = all(t.get("usd") is not None for t in tr)
    hodnota = [float(t["usd"]) if usd_ok else float(t["pts"]) for t in tr]
    wins = sum(1 for v in hodnota if v > 0)
    losses = sum(1 for v in hodnota if v < 0)
    zisk = sum(v for v in hodnota if v > 0)
    strata = -sum(v for v in hodnota if v < 0)
    eq, peak, dd, dd_pct = 0.0, 0.0, 0.0, 0.0
    for v in hodnota:
        eq += v
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
        if capital:
            dd_pct = max(dd_pct, (peak - eq) / (capital + peak) * 100.0)
    seria, naj = 0, {"wins": 0, "losses": 0}
    for v in hodnota:   # + = výhry po sebe, − = prehry po sebe
        if v > 0:
            seria = seria + 1 if seria > 0 else 1
            naj["wins"] = max(naj["wins"], seria)
        elif v < 0:
            seria = seria - 1 if seria < 0 else -1
            naj["losses"] = max(naj["losses"], -seria)
        else:
            seria = 0
    exits: dict[str, int] = {}
    for t in tr:
        for x in t.get("exits") or []:
            exits[x] = exits.get(x, 0) + 1
    pnl = sum(hodnota)
    return {
        "trades": n, "wins": wins, "losses": losses, "draws": n - wins - losses,
        "winrate": round(100.0 * wins / n, 2) if n else 0.0,
        "unit": "$" if usd_ok else "b",
        "pnl_abs": round(pnl, 2),
        "pnl_pts": round(sum(float(t["pts"]) for t in tr), 2),
        "pnl_pct": round(pnl / capital * 100.0, 2) if capital and usd_ok else None,
        "profit_factor": round(zisk / strata, 2) if strata > 0 else (None if not zisk else float("inf")),
        "avg_win": round(zisk / wins, 2) if wins else None,
        "avg_loss": round(-strata / losses, 2) if losses else None,
        "best": round(max(hodnota), 2) if hodnota else None,
        "worst": round(min(hodnota), 2) if hodnota else None,
        "max_drawdown_abs": round(dd, 2),
        "max_drawdown_pct": round(dd_pct, 2) if capital and usd_ok else None,
        "starting_balance": capital, "final_balance": round(capital + pnl, 2) if capital and usd_ok else None,
        "streaks": naj, "exits": exits,
    }


#: TrueType písma s diakritikou (Windows, Linux, macOS); predvolené písmo Pillow ju nemá.
FONTS = ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/System/Library/Fonts/Supplemental/Arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf")


def _font(size: int) -> tuple[Any, bool]:
    """Písmo a či vie diakritiku (bez TrueType ide predvolené a text sa zbaví diakritiky)."""
    from PIL import ImageFont

    for f in FONTS:
        try:
            return ImageFont.truetype(f, size), True
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size), False
    except TypeError:   # Pillow < 10.1
        return ImageFont.load_default(), False


def _ascii(text: str) -> str:
    text = text.replace("→", "->").replace("·", "|")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).encode(
        "ascii", "replace").decode()


def equity_png(tr: list[dict[str, Any]], title: str = "", *, width: int = 900, height: int = 420) -> bytes | None:
    """Krivka kumulatívneho P&L po obchodoch ako PNG; bez Pillow alebo bez obchodov None."""
    if not tr:
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    usd_ok = all(t.get("usd") is not None for t in tr)
    body = [0.0]
    for t in tr:
        body.append(body[-1] + (float(t["usd"]) if usd_ok else float(t["pts"])))
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    font, unicode_ok = _font(16)
    txt = (lambda t: t) if unicode_ok else _ascii
    lavo, pravo, hore, dole = 80, 20, 40, 40
    sirka, vyska = width - lavo - pravo, height - hore - dole
    lo, hi = min(body), max(body)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad

    def xy(i: int, v: float) -> tuple[float, float]:
        return lavo + sirka * i / max(1, len(body) - 1), hore + vyska * (hi - v) / (hi - lo)

    for k in range(5):   # mriežka a popisy osi y
        v = lo + (hi - lo) * k / 4
        _, y = xy(0, v)
        d.line([(lavo, y), (width - pravo, y)], fill=(230, 230, 230))
        d.text((6, y - 8), f"{v:,.0f}".replace(",", " "), fill=(110, 110, 110), font=font)
    _, y0 = xy(0, 0.0)
    d.line([(lavo, y0), (width - pravo, y0)], fill=(150, 150, 150), width=1)
    body_xy = [xy(i, v) for i, v in enumerate(body)]
    farba = (22, 140, 70) if body[-1] >= 0 else (200, 40, 40)
    d.polygon([(body_xy[0][0], y0), *body_xy, (body_xy[-1][0], y0)], fill=(230, 245, 235) if body[-1] >= 0 else (250, 230, 230))
    d.line(body_xy, fill=farba, width=3)
    for (x, y), v0, v1 in zip(body_xy[1:], body[:-1], body[1:]):
        if len(body) <= 120:
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(22, 140, 70) if v1 >= v0 else (200, 40, 40))
    jednotka = "$" if usd_ok else "b"
    d.text((lavo, 10), txt(f"{title}  ·  {len(tr)} obchodov  ·  {body[-1]:+,.2f} {jednotka}".replace(",", " ")),
           fill=(30, 30, 30), font=font)
    d.text((lavo, height - 28), txt("obchod č. →"), fill=(110, 110, 110), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
