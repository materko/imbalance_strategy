"""Živé obdobie stratégie: stiahnuté sviečky + sviečky zo živého behu, skutočné obchody a simulácia.

Pre jednu inštanciu zo skladu živých dát (`tester.livedata`, `data_live/`) poskladá:

* **hranicu** — začiatok prvého živého behu s profilom inštancie; dovtedy sú to stiahnuté dáta (história),
  odtiaľ to, čo stratégia naozaj videla,
* **sviečky** — pred hranicou stiahnuté 1m trhu nastavenia (`data/…`, pár z Diverzifikácie), za ňou živé.
  Za hranicou platí po baroch TF grafu poradie *živé 1m → živý bar grafu → stiahnuté 1m*: kde je 1m zo
  živého behu (`m1`), je aj 1m detail; kde nie (staršie behy, výpadok), ide bar grafu, ako ho stratégia
  dostala, a kde nie je ani ten, doplnia sa stiahnuté. Vyšší TF sa skladá len cez `tradebot.core.candles`,
* **skutočné obchody** — vyplnenia u brokera z behov s tým istým profilom,
* **simuláciu** — ten istý engine, config a inštrument zo živého behu (`hello`) cez emulátor MultiCharts
  (`tradebot.adapters.multicharts.emulator`) nad týmito sviečkami; engine sa rozbehne `WARMUP_DAYS` pred
  hranicou na stiahnutých dátach a do výsledku idú len obchody otvorené od hranice,
* **párovanie** skutočných a simulovaných obchodov (smer a čas vstupu do `MATCH_BARS` barov grafu).

Zisk skutočných obchodov aj simulácie je hrubý (bez poplatkov), v $ podľa hodnoty bodu živého inštrumentu.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import livedata

__all__ = ["live_view", "combined_minutes", "match_trades", "WARMUP_DAYS", "MATCH_BARS"]

#: Koľko dní pred hranicou sa engine rozbieha na stiahnutých dátach (indikátory, zóny, VWAP).
WARMUP_DAYS = 10
#: Skutočný a simulovaný obchod sú ten istý, keď majú smer a vstup najviac toľko barov grafu od seba.
MATCH_BARS = 3
#: Koľko dní stiahnutých sviečok pred hranicou ide do grafu.
CHART_DAYS_BEFORE = 5
#: Najviac toľko dní pred hranicou, keď graf ukazuje aj koniec stiahnutých dát.
CHART_DAYS_MAX = 30
MIN_MS = 60_000

_cache: dict[tuple, dict[str, Any]] = {}
_lock = threading.Lock()


def _ms(iso: str | None) -> int | None:
    if not iso:
        return None
    return int(datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)


def _iso(ms: int | float | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stem(p: Any) -> str:
    return Path(str(p or "").replace("\\", "/")).stem


#: Meno symbolu u brokera / v NinjaTraderi → základ symbolu stiahnutých dát (`NAS100/USD` → `NAS100`).
SYMBOL_ALIASES = {"US100": "NAS100", "USTEC": "NAS100", "NDX": "NAS100", "NAS100": "NAS100", "NQ": "MNQ",
                  "US30": "DJ30", "SPX500": "US500", "GER40": "DAX", "DE40": "DAX", "XAUUSD": "XAU", "GOLD": "XAU",
                  "USOIL": "WTI", "MGC": "MGC", "GC": "MGC"}
#: Zdroj stiahnutých dát, ktorý k platforme sedí najlepšie (CFD u MT5 brokera, futures CME v NinjaTraderi).
PLATFORM_SOURCE = {"mt5": "dukascopy", "ninjatrader": "databento"}


def _base(symbol: str) -> str:
    return str(symbol or "").split("/")[0].split(".")[0].split()[0].upper() if str(symbol or "").strip() else ""


def _history_instrument(pair: str | None, inst: dict[str, Any]):
    """InstrumentSpec stiahnutých dát k živému behu. `pair` sú páry nastavenia z Diverzifikácie (čiarkou);
    prednosť má trh s tým istým symbolom ako živý beh (`US100.cash` → `NAS100/USD`, zdroj podľa platformy),
    potom pár nastavenia, potom `_instrument` profilu."""
    from tradebot.core.types import INSTRUMENTS

    want = SYMBOL_ALIASES.get(_base(inst.get("symbol")), _base(inst.get("symbol")))
    src = PLATFORM_SOURCE.get(str(inst.get("platform") or ""))
    pairs = [p.strip() for p in str(pair or "").split(",") if p.strip()]
    by_pair = [spec for p in pairs for spec in INSTRUMENTS.values() if spec.symbol == p]
    same = [spec for spec in INSTRUMENTS.values() if _base(spec.symbol) == want and spec.source in ("dukascopy", "databento")]
    same.sort(key=lambda spec: (spec.source != src, spec.symbol not in pairs))
    if same:
        return same[0]
    if by_pair:
        return by_pair[0]
    for cfg in (inst.get("configs") or {}).values():
        key = (cfg or {}).get("_instrument")
        if key in INSTRUMENTS:
            return INSTRUMENTS[key]
    return None


def _live_instrument(inst: dict[str, Any], fallback):
    """InstrumentSpec živého inštrumentu (tick, hodnota bodu, lot) z `hello` — simulácia ráta ako engine naživo."""
    from tradebot.core.types import InstrumentSpec

    i = inst.get("instrument") or {}
    if not i.get("tick_size") or not i.get("point_value"):
        return fallback
    return InstrumentSpec(symbol=str(i.get("symbol") or inst.get("symbol") or "?"), venue=str(i.get("venue") or inst.get("platform")),
                          tick_size=float(i["tick_size"]), point_value=float(i["point_value"]),
                          qty_step=float(i.get("qty_step") or 1.0), min_qty=float(i.get("min_qty") or 1.0),
                          has_real_volume=bool(i.get("has_real_volume", True)))


def _empty_frame():
    return livedata.load_candles("-", "-", "1m", Path("-"))   # prázdny rámec v tvare sviečok


def _layer(sources: list[tuple[str, Any]], step: str, full: int = 0) -> tuple[list[Any], dict[str, int]]:
    """Po baroch TF grafu: každý bar z prvého zdroja v poradí, ktorý ho má (zdroje sa v bare nemiešajú —
    objem ani detail by inak neseděli). Vráti kúsky rámcov a počty barov podľa zdroja.

    Zdroj s menom končiacim `!` berie len **úplné** košíky (`full` minút) — neúplný živý 1m košík (2 z 5
    minút, výpadok spojenia) nesmie prebiť úplný bar grafu (audit N-DATA-3). Rovnaký zdroj bez `!` ďalej
    v poradí berie, čo ostalo."""

    taken: set = set()
    parts, counts = [], {}
    for name, df in sources:
        uplne = name.endswith("!")
        name = name.rstrip("!")
        if df is None or not len(df):
            counts.setdefault(name, 0)
            continue
        buckets = df["date"].dt.floor(step)
        keep = ~buckets.isin(taken)
        if uplne and full > 1:
            pocet = df["date"].groupby(buckets).transform("nunique")
            keep &= pocet >= full
        chosen = df[keep]
        new = set(buckets[keep])
        counts[name] = counts.get(name, 0) + len(new)
        taken |= new
        if len(chosen):
            parts.append(chosen)
    return parts, counts


def combined_minutes(official, live_m1, live_chart, boundary_ms: int, chart_tf: int):
    """Rámec pre emulátor po baroch TF grafu. Pred hranicou stiahnuté 1m, kde chýbajú (stiahnuté končia
    skôr), živé; za hranicou úplný živý 1m košík, inak živý bar grafu, inak stiahnuté 1m, inak neúplné živé 1m. Vráti (rámec, počty barov
    grafu za hranicou podľa zdroja + `before_live`, koľko barov pred hranicou je zo živých dát)."""
    import pandas as pd

    b = pd.Timestamp(boundary_ms, unit="ms", tz="UTC")
    step = f"{int(chart_tf)}min"

    def cut(df, after: bool):
        if df is None or not len(df):
            return None
        return df[df["date"] >= b] if after else df[df["date"] < b]

    tf = int(chart_tf)
    pre, pre_counts = _layer([("official", cut(official, False)), ("live_1m!", cut(live_m1, False)),
                              ("live_chart", cut(live_chart, False)), ("live_1m", cut(live_m1, False))], step, tf)
    post, counts = _layer([("live_1m!", cut(live_m1, True)), ("live_chart", cut(live_chart, True)),
                           ("official", cut(official, True)), ("live_1m", cut(live_m1, True))], step, tf)
    counts["before_live"] = pre_counts.get("live_1m", 0) + pre_counts.get("live_chart", 0)
    frames = pre + post
    if not frames:
        return _empty_frame(), counts
    df = pd.concat(frames, ignore_index=True).sort_values("date", kind="stable").reset_index(drop=True)
    return df, counts


def _exit_kind(t: dict[str, Any]) -> str:
    """Druh výstupu na porovnanie: MT5 hlási SL aj TP ako `sltp` — rozhodne znamienko zisku; trailing je stop."""
    r = str(t.get("reason") or "").lower()
    if r == "sltp":
        return "take_profit" if (t.get("pts") or 0) > 0 else "stop_loss"
    if "trailing" in r or "stop" in r:
        return "stop_loss"
    return r


def match_trades(real: list[dict[str, Any]], sim: list[dict[str, Any]], tf_minutes: int) -> dict[str, Any]:
    """Páry (rovnaký smer, vstup do `MATCH_BARS` barov), skutočné bez simulácie a simulácia bez skutočného."""
    tol = MATCH_BARS * max(1, int(tf_minutes)) * MIN_MS
    free = list(range(len(sim)))
    pairs, only_real = [], []
    for ri, r in enumerate(real):
        rt = _ms(r["open"])
        best, gap = None, None
        for si in free:
            s = sim[si]
            if s["dir"] != r["dir"]:
                continue
            d = abs(_ms(s["open"]) - rt)
            if d <= tol and (gap is None or d < gap):
                best, gap = si, d
        if best is None:
            only_real.append(ri)
            continue
        free.remove(best)
        s = sim[best]
        pairs.append({"real": ri, "sim": best, "dt_min": round((rt - _ms(s["open"])) / MIN_MS, 1),
                      "d_entry": None if r.get("entry") is None or s.get("entry") is None else round((r["entry"] - s["entry"]) * (1 if r["dir"] == "long" else -1), 4),
                      "d_pnl": None if r.get("pnl") is None or s.get("pnl") is None else round(r["pnl"] - s["pnl"], 2),
                      "same_exit": _exit_kind(r) == _exit_kind(s)})
    return {"pairs": pairs, "only_real": only_real, "only_sim": free}


def _simulate(inst: dict[str, Any], profile: str, frame, chart_tf: int, from_ms: int, to_ms: int, live_spec, log) -> list[dict[str, Any]]:
    from tradebot.adapters.multicharts.emulator import emulate
    from tradebot.strategies import get_spec

    cfg_dict = dict((inst.get("configs") or {}).get(profile) or {})
    if not cfg_dict:
        raise ValueError(f"inštancia nemá config profilu {profile}")
    spec = get_spec(str(cfg_dict.get("_strategy") or inst["engine"]))
    overrides = (cfg_dict.get("_engine_overrides") or {}).get("multicharts") or {}
    cfg = spec.config_cls.from_dict({**cfg_dict, **overrides})
    result, _ = emulate(cfg, live_spec, frame, chart_tf, from_ms=from_ms, to_ms=to_ms, log=log, spec=spec)
    out = []
    pv = float(live_spec.point_value)
    for t in result.trades:
        if t.exit is None or t.close_ms is None:
            continue
        pts = (t.exit - t.entry) * (1 if t.is_long else -1)
        sd = abs(t.entry - t.stop_initial) if t.stop_initial else None
        out.append({"id": t.order_id, "open": _iso(t.open_ms), "close": _iso(t.close_ms),
                    "dir": "long" if t.is_long else "short", "qty": t.qty, "entry": round(t.entry, 6),
                    "exit": round(t.exit, 6), "sl": t.stop_initial, "tp": t.take_profit, "sd": sd,
                    "pts": round(pts, 6), "pnl": round(pts * t.qty * pv, 2), "r": round(pts / sd, 3) if sd else None,
                    "reason": t.reason, "order_type": "market" if t.market else "limit"})
    return out


def _chart_bars(df, tf: int) -> list[list[Any]]:
    from tradebot.core.candles import resample_ohlcv

    if df is None or not len(df):
        return []
    r = resample_ohlcv(df, tf)
    ts = (r["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).tolist()
    return [[_iso(t), round(float(o), 6), round(float(h), 6), round(float(l), 6), round(float(c), 6)]
            for t, o, h, l, c in zip(ts, r["open"], r["high"], r["low"], r["close"])]


def live_view(inst_id: str, *, profile: str | None = None, pair: str | None = None, root: Path | str | None = None,
              simulate: bool = True, chart: bool = True) -> dict[str, Any]:
    """Všetko pre Diverzifikáciu k jednej živej inštancii (pozri docstring modulu). Výsledok sa cache-uje
    podľa súborov `data_live`, ktoré doň vstúpili — nový bar alebo obchod znamená nový výpočet."""
    import pandas as pd

    roots = livedata._roots(root)   # git + to, čo je len na hube; alebo zadaný strom
    inst = livedata.instance(inst_id, root)
    if inst is None:
        raise KeyError(f"živá inštancia {inst_id} v živých dátach ({', '.join(map(str, roots))}) nie je")
    files = [p for r in roots for top in ("candles", "trades", "instances") for p in sorted((r / top).rglob("*"))
             if p.is_file() and (top == "candles" or inst_id in p.as_posix())]
    stamp = tuple((str(p), p.stat().st_mtime_ns) for p in files)
    key = (inst_id, profile, pair, tuple(map(str, roots)), simulate, chart, stamp)
    with _lock:
        if key in _cache:
            return _cache[key]

    tf = int(inst["tf"] or 1)
    profile = profile or inst.get("profile") or ""
    sessions = [s for s in inst.get("sessions") or [] if _stem(s.get("profile")) == profile] or inst.get("sessions") or []
    boundary = min((_ms(s["start"]) for s in sessions if s.get("start")), default=None)
    real = [t for t in livedata.trades(inst_id, root) if not t.get("profile") or t["profile"] == profile]
    hist = _history_instrument(pair, inst)
    profile_end = max((_ms(s.get("end") or s["start"]) for s in sessions if s.get("start")), default=None)
    out: dict[str, Any] = {"instance": {k: v for k, v in inst.items() if k != "configs"}, "profile": profile, "tf": tf, "boundary": _iso(boundary),
                           "history": {"pair": getattr(hist, "symbol", None)}, "real": real, "sim": [], "match": None,
                           "sources": None, "chart": None, "notes": []}
    if boundary is None:
        out["notes"].append("inštancia nemá živý beh s profilom — nie je od čoho počítať")
        return out

    live_m1 = livedata.load_candles(inst["platform"], inst["symbol"], "1m", root)
    live_chart = livedata.load_candles(inst["platform"], inst["symbol"], f"{tf}m", root) if tf > 1 else live_m1
    ends = [d["date"].iloc[-1] for d in (live_m1, live_chart) if len(d)]
    end_ms = int(max(ends).value // 1_000_000) + tf * MIN_MS if ends else None
    if end_ms is not None and profile_end is not None:   # profil sa neskôr vymenil — ďalej už nie je jeho beh
        end_ms = min(end_ms, profile_end + tf * MIN_MS)
    official = None
    if hist is not None:
        from tester import engines

        path = engines.one_minute_file(hist)
        if path.exists():
            official = pd.read_feather(path)
            official = official[official["date"] >= pd.Timestamp(boundary - (WARMUP_DAYS + 5) * 86_400_000, unit="ms", tz="UTC")]
            out["history"].update(file=path.name, last=official["date"].iloc[-1].strftime("%Y-%m-%dT%H:%M:%SZ") if len(official) else None)
        else:
            out["notes"].append(f"stiahnuté 1m {path.name} na tomto stroji nie sú — pred hranicou nie je história")
    else:
        out["notes"].append("k inštancii sa nenašiel trh stiahnutých dát (pár nastavenia ani _instrument profilu)")
    frame, counts = combined_minutes(official, live_m1, live_chart, boundary, tf)
    out["sources"] = counts
    if end_ms is None and len(frame):
        end_ms = int(frame["date"].iloc[-1].value // 1_000_000) + MIN_MS
    out["end"] = _iso(end_ms)
    if counts["live_chart"] and not counts["live_1m"]:
        out["notes"].append("živý beh nemá 1m bary (staršie verzie adaptérov) — simulácia za hranicou ide po baroch grafu bez 1m detailu")
    elif counts["live_chart"]:
        out["notes"].append(f"{counts['live_chart']} barov grafu za hranicou nemá 1m — tam simulácia ide bez 1m detailu")
    if counts["official"]:
        out["notes"].append(f"{counts['official']} barov grafu za hranicou chýba v živých dátach — doplnené zo stiahnutých")
    if counts["before_live"]:
        out["notes"].append(f"{counts['before_live']} barov grafu pred hranicou nie je v stiahnutých dátach — sú zo živých "
                            "(predošlé behy, predhistória platformy)")

    if simulate and len(frame) and end_ms:
        live_spec = _live_instrument(inst, hist)
        if live_spec is None:
            out["notes"].append("simulácia: chýba inštrument (tick, hodnota bodu)")
        else:
            log_lines: list[str] = []
            try:
                sim = _simulate(inst, profile, frame, tf, boundary - WARMUP_DAYS * 86_400_000, end_ms, live_spec, log_lines.append)
                # force_exit = koniec dát s otvorenou pozíciou (emulátor ju zavrie na poslednom close) — nie je to obchod
                out["sim"] = [t for t in sim if _ms(t["open"]) >= boundary and t["reason"] != "force_exit"]
                out["match"] = match_trades(real, out["sim"], tf)
            except Exception as exc:  # noqa: BLE001 - simulácia nesmie zhodiť zvyšok pohľadu
                out["notes"].append(f"simulácia zlyhala: {type(exc).__name__}: {exc}")

    if chart:
        # okno: pár dní pred hranicou, a keď stiahnuté dáta končia skôr, aj ich koniec (najviac CHART_DAYS_MAX)
        start = boundary - CHART_DAYS_BEFORE * 86_400_000
        off_last = int(official["date"].iloc[-1].value // 1_000_000) if official is not None and len(official) else None
        if off_last is not None and off_last < start:
            start = max(boundary - CHART_DAYS_MAX * 86_400_000, off_last - 2 * 86_400_000)
        part = frame[frame["date"] >= pd.Timestamp(start, unit="ms", tz="UTC")] if len(frame) else frame
        if end_ms is not None and len(part):
            part = part[part["date"] < pd.Timestamp(end_ms, unit="ms", tz="UTC")]
        b = pd.Timestamp(boundary, unit="ms", tz="UTC")
        pre = part[part["date"] < b]
        from_off = pre["date"].isin(official["date"]) if official is not None and len(official) and len(pre) else pd.Series(False, index=pre.index)
        out["chart"] = {"before": _chart_bars(pre[from_off], tf), "before_live": _chart_bars(pre[~from_off], tf),
                        "after": _chart_bars(part[part["date"] >= b], tf)}
    with _lock:
        if len(_cache) > 64:
            _cache.clear()
        _cache[key] = out
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m tester.livesim", description=__doc__.split("\n\n")[0])
    ap.add_argument("instance")
    ap.add_argument("--profile", help="profil živého behu (inak posledný profil inštancie)")
    ap.add_argument("--pair", help="trh stiahnutých dát, napr. MNQ/USD (inak _instrument profilu)")
    ap.add_argument("--root", default=None, help="strom živých dát (predvolene git data_live + čo je len na hube)")
    args = ap.parse_args(argv)
    v = live_view(args.instance, profile=args.profile, pair=args.pair, root=args.root, chart=False)
    m = v["match"] or {"pairs": [], "only_real": [], "only_sim": []}
    print(json.dumps({"boundary": v["boundary"], "end": v.get("end"), "history": v["history"], "sources": v["sources"],
                      "real": len(v["real"]), "sim": len(v["sim"]), "pairs": len(m["pairs"]),
                      "only_real": len(m["only_real"]), "only_sim": len(m["only_sim"]), "notes": v["notes"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
