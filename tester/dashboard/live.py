"""Live sekcia stránky TradeBot výsledky — čo stratégie nasadené naživo (NinjaTrader, MT5) naozaj robia.

Zdroj je zrkadlo live telemetrie webapp (`tradebot.live.store.LiveStore`, `LIVE_MIRROR`), to isté, čo
číta karta **Live** vo webapp (docs/LIVE.md). Z neho sa pre každú inštanciu (platforma × účet × symbol ×
stratégia) poskladá:

* **obchody** — vyplnenia u brokera (`fill`) spárované podľa id orderu: ``in`` = vstup, ``out`` = výstup
  (aj po častiach); smer, SL, TP a vzdialenosť SL sa berú zo zámeru enginu (`order`, ``a=entry``) s tým
  istým id. Zisk je hrubý (bez poplatkov a swapov): ``(výstup − vstup) × smer × množstvo × hodnota bodu``,
  hodnota bodu je z ``hello`` (inštrument platformy),
* **otvorené pozície** — vstup bez (úplného) výstupu,
* **signály** — zámery vstupu enginu naživo (``ready``; prehrávanie histórie pri štarte sa nepočíta)
  a čo sa s nimi stalo: vyplnený, zrušený (s dôvodom enginu) alebo bez odozvy brokera,
* **stav** a posledné varovania platformy (``note``).

Stránka (`tester/dashboard/index.html`, karta Live) to porovná s tým, čo profil sľuboval v backteste
(nastavenie stránky podľa čísla profilu, napr. ``PRESIEL_SMERNICAMI_VWAP_ORB_CS_1`` → ``vwaporb-1``).

Použitie z generátora stránky::

    from tester.dashboard.live import build_live
    data["live"] = build_live()

alebo z príkazového riadka (pridá sekciu ``live`` do hotového JSON s dátami stránky)::

    python -m tester.dashboard.live --into dashboard_data.json
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.core.paths import LIVE_MIRROR

__all__ = ["build_live", "base_strategy", "setting_id", "main"]

#: Inštancia je „ticho“, keď od poslednej udalosti prešlo viac (a nerozlúčila sa `bye`).
QUIET_MS = 30 * 60_000
#: Inštancie bez obchodu a bez udalosti za toľko dní sa označia ako staré (stránka ich zbalí).
STALE_DAYS = 7
#: Koľko posledných signálov a varovaní na inštanciu ide na stránku.
MAX_SIGNALS = 300
MAX_NOTES = 15


def _iso(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def base_strategy(engine_key: str) -> str:
    """Kľúč stratégie na stránke: C# port → jeho Python predloha (``vwaporbnet`` → ``vwaporb``); EOD kópia
    (``vwaporbneteod``, všetko zavreté o 15:59 NY) patrí tej istej predlohe."""
    key = str(engine_key or "")
    if key.endswith("neteod"):
        key = key[:-3]
    try:
        from tradebot.strategies import ALIASES, STRATEGIES
        key = ALIASES.get(key, key)
        if key.endswith("net") and key[:-3] in STRATEGIES:
            return key[:-3]
    except Exception:  # registry nie je nevyhnutná — stačí pravidlo s príponou
        if key.endswith("net"):
            return key[:-3]
    return key


def setting_id(engine_key: str, profile: str) -> str | None:
    """Id nastavenia na stránke z mena profilu, ktorý prešiel smernicou (číslo na konci)."""
    name = Path(str(profile or "").replace("\\", "/")).stem
    if not re.match(r"^(PRESIEL_SMERNICAMI_|SMERNICE_CS_)", name):
        return None
    m = re.search(r"_(\d+)$", name)
    return f"{base_strategy(engine_key)}-{int(m.group(1))}" if m else None


def _strategy_title(engine_key: str) -> str:
    try:
        from tradebot.strategies import STRATEGIES
        spec = STRATEGIES.get(base_strategy(engine_key))
        if spec is not None:
            title = re.sub(r"\s*\(C# jadro\)$", "", spec.title)
            return title + " EOD" if str(engine_key or "").endswith("neteod") else title
    except Exception:
        pass
    return engine_key


def _rows(db: sqlite3.Connection, instance: str, kinds: tuple[str, ...]) -> list[tuple[str, dict[str, Any]]]:
    q = "SELECT session, body FROM events WHERE instance = ? AND kind IN (%s) ORDER BY t, id" % ",".join("?" * len(kinds))
    return [(r[0], json.loads(r[1])) for r in db.execute(q, (instance, *kinds))]


def _instance(db: sqlite3.Connection, inst: dict[str, Any], now_ms: int) -> dict[str, Any]:
    iid = inst["id"]
    hello = json.loads(inst["hello"] or "{}")
    pv = float(((hello.get("instrument") or {}).get("point_value")) or 1.0)
    orders = _rows(db, iid, ("order",))
    fills = _rows(db, iid, ("fill",))
    notes = _rows(db, iid, ("note",))

    # zámery vstupu naživo: (session, id) -> udalosť; posledný zámer s daným id pre párovanie fillov
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    by_id: dict[str, list[dict[str, Any]]] = {}
    cancels: dict[tuple[str, str], str] = {}
    for ses, ev in orders:
        if not ev.get("ready"):
            continue
        key = (ses, str(ev.get("id")))
        if ev.get("a") == "entry":
            entries.setdefault(key, ev)
            by_id.setdefault(str(ev.get("id")), []).append(ev)
        elif ev.get("a") == "cancel":
            cancels.setdefault(key, str(ev.get("r") or ""))

    def plan_for(oid: str, at_ms: int) -> dict[str, Any] | None:
        best = None
        for ev in by_id.get(oid, []):
            if ev["t"] <= at_ms + 5_000 and (best is None or ev["t"] > best["t"]):
                best = ev
        return best

    # obchody z fillov
    open_: dict[str, dict[str, Any]] = {}
    trades: list[dict[str, Any]] = []
    filled_keys: set[tuple[str, str]] = set()
    orphans = 0
    for ses, ev in fills:
        oid = str(ev.get("id"))
        ft = int(ev.get("ft") or ev.get("t"))
        qty = float(ev.get("qty") or 0.0)
        price = float(ev.get("price") or 0.0)
        if qty <= 0:
            continue
        if ev.get("side") == "in":
            filled_keys.add((ses, oid))
            tr = open_.get(oid)
            if tr is None or tr["out_qty"] > 0:
                order = plan_for(oid, ft) or {}
                plan = order.get("p") or {}
                tr = open_[oid] = {"id": oid, "open_ms": ft, "dir": int(order.get("dir") or plan.get("dir") or 0),
                                   "in_qty": 0.0, "in_val": 0.0, "out_qty": 0.0, "out_val": 0.0, "reason": "",
                                   "sl": plan.get("sl"), "tp": plan.get("tp"), "sd": plan.get("sd"),
                                   "signal_ms": order.get("bt"), "order_type": order.get("ot")}
            tr["in_qty"] += qty
            tr["in_val"] += qty * price
            continue
        tr = open_.get(oid)
        if tr is None:
            orphans += 1
            continue
        tr["out_qty"] += qty
        tr["out_val"] += qty * price
        tr["reason"] = str(ev.get("exit") or tr["reason"])
        tr["close_ms"] = ft
        if tr["out_qty"] >= tr["in_qty"] - 1e-9:
            del open_[oid]
            trades.append(tr)

    def finish(tr: dict[str, Any], closed: bool) -> dict[str, Any]:
        entry = tr["in_val"] / tr["in_qty"] if tr["in_qty"] else None
        out = {"id": tr["id"], "open": _iso(tr["open_ms"]), "signal": _iso(tr["signal_ms"]),
               "dir": "long" if tr["dir"] > 0 else "short" if tr["dir"] < 0 else "?",
               "entry": round(entry, 6) if entry is not None else None, "qty": round(tr["in_qty"], 6),
               "sl": tr["sl"], "tp": tr["tp"], "order_type": tr["order_type"]}
        if closed:
            exit_ = tr["out_val"] / tr["out_qty"]
            pts = (exit_ - entry) * tr["dir"] if tr["dir"] else None
            out.update(close=_iso(tr["close_ms"]), exit=round(exit_, 6), reason=_reason(tr["reason"]),
                       pts=round(pts, 6) if pts is not None else None,
                       pnl=round(pts * tr["in_qty"] * pv, 2) if pts is not None else None,
                       r=round(pts / tr["sd"], 3) if pts is not None and tr["sd"] else None)
        return out

    # signály a ich osud
    signals = []
    for (ses, oid), ev in sorted(entries.items(), key=lambda kv: kv[1]["t"]):
        plan = ev.get("p") or {}
        if (ses, oid) in filled_keys:
            res = "vyplnený"
        elif (ses, oid) in cancels:
            res = "zrušený: " + (cancels[(ses, oid)] or "bez dôvodu")
        elif now_ms - int(ev["t"]) < QUIET_MS:
            res = "čaká"
        else:
            res = "bez vyplnenia"
        signals.append({"t": _iso(ev.get("bt") or ev["t"]), "id": oid, "dir": "long" if int(ev.get("dir") or 0) > 0 else "short",
                        "type": str(ev.get("ot") or ""), "entry": plan.get("e"), "sl": plan.get("sl"), "tp": plan.get("tp"),
                        "qty": plan.get("q"), "why": str(ev.get("r") or ""), "result": res})

    # stav
    last = db.execute("SELECT kind, t FROM events WHERE instance = ? AND session = ? ORDER BY t DESC, id DESC LIMIT 1",
                      (iid, inst["last_session"])).fetchone()
    first = db.execute("SELECT MIN(t) FROM events WHERE instance = ?", (iid,)).fetchone()[0]
    last_t = int(inst["last_t"] or 0)
    if last is not None and last[0] == "bye":
        status = "zastavená"
    elif now_ms - last_t <= QUIET_MS:
        status = "beží"
    else:
        status = "ticho"
    closed = [finish(t, True) for t in sorted(trades, key=lambda t: t["close_ms"])]
    stale = not closed and not open_ and now_ms - last_t > STALE_DAYS * 86_400_000
    return {
        "id": iid, "engine": inst["strategy"], "strategy": base_strategy(inst["strategy"]),
        "name": _strategy_title(inst["strategy"]), "setting": setting_id(inst["strategy"], inst["profile"]),
        "profile": Path(str(inst["profile"] or "").replace("\\", "/")).stem,
        "platform": inst["platform"], "account": inst["account"], "symbol": inst["symbol"], "tf": inst["tf"],
        "host": inst["host"], "agent": inst["agent"], "point_value": pv,
        "since": _iso(first), "last_event": _iso(last_t), "last_bar": _iso(inst["last_bar_ms"] or None),
        "status": status, "stale": stale, "orphan_fills": orphans,
        "trades": closed, "open": [finish(t, False) for t in open_.values()],
        "signals": signals[-MAX_SIGNALS:],
        "notes": [{"t": _iso(ev["t"]), "level": ev.get("level", ""), "text": ev.get("text", "")}
                  for _, ev in notes[-MAX_NOTES:]],
    }


def _reason(exit_name: str) -> str:
    e = exit_name.lower()
    if "profit" in e or e in ("tp", "take profit"):
        return "take_profit"
    if "stop" in e or e in ("sl",):
        return "stop_loss"
    return exit_name or "exit"


def build_live(mirror: Path | str = LIVE_MIRROR, *, now_ms: int | None = None) -> dict[str, Any]:
    """Sekcia ``live`` pre dáta stránky. Bez zrkadla vráti prázdny zoznam (stránka to povie)."""
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    out: dict[str, Any] = {"generated": _iso(now_ms), "instances": []}
    path = Path(mirror)
    if not path.exists():
        out["error"] = f"zrkadlo live telemetrie {path.name} na tomto stroji nie je"
        return out
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        insts = [dict(r) for r in db.execute("SELECT * FROM instances ORDER BY id")]
        out["instances"] = [_instance(db, i, now_ms) for i in insts if i.get("strategy")]
    finally:
        db.close()
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tester.dashboard.live", description=__doc__.split("\n\n")[0])
    ap.add_argument("--mirror", default=str(LIVE_MIRROR), help="zrkadlo live telemetrie (default tester/live/mirror.sqlite)")
    ap.add_argument("--into", help="JSON s dátami stránky — pridá/prepíše v ňom kľúč live")
    ap.add_argument("--out", help="zapíše len sekciu live do tohto súboru (bez --into a --out ide na stdout)")
    args = ap.parse_args(argv)
    live = build_live(args.mirror)
    if args.into:
        p = Path(args.into)
        data = json.loads(p.read_text(encoding="utf-8"))
        data["live"] = live
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if args.out:
        Path(args.out).write_text(json.dumps(live, ensure_ascii=False, indent=1), encoding="utf-8")
    if not args.into and not args.out:
        print(json.dumps(live, ensure_ascii=False, indent=1))
    n = sum(len(i["trades"]) for i in live["instances"])
    print(f"live: {len(live['instances'])} inštancií, {n} uzavretých obchodov", file=__import__("sys").stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
