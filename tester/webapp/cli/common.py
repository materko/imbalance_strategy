"""Spoločné pre príkazy: prepínače `--set`, REST API webapp, výpis behu, výber behov."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

from tradebot.core.env import getenv


DEFAULT_URL = getenv("WEB_URL", "http://127.0.0.1:8765")


def parse_set(item: str) -> tuple[str, Any]:
    """`kluc=hodnota` → (kluc, typovaná hodnota)."""
    if "=" not in item:
        raise SystemExit(f"--set očakáva kluc=hodnota, dostal {item!r}")
    key, raw = item.split("=", 1)
    key, raw = key.strip(), raw.strip()
    if "@" in raw and not raw.startswith("{"):
        val, unit = raw.rsplit("@", 1)
        return key, {"value": float(val), "unit": unit}
    low = raw.lower()
    if low in ("true", "false"):
        return key, low == "true"
    if low in ("null", "none"):
        return key, None
    try:
        return key, json.loads(raw)
    except json.JSONDecodeError:
        return key, raw


def api(url: str, path: str, body: dict | None = None, timeout: float = 30) -> Any:
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ct = r.headers.get("content-type", "")
        data = r.read()
        return json.loads(data) if "json" in ct else data.decode("utf-8", "replace")


def server_alive(url: str) -> bool:
    try:
        api(url, "/api/queue", timeout=3)
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def fmt_summary(rec: dict[str, Any]) -> str:
    r = rec.get("result") or {}
    s = rec.get("settings") or {}
    if rec.get("status") != "done":
        return f"{rec.get('id')}  {rec.get('status')}  {s.get('pair')} {s.get('timerange')}  {rec.get('error') or ''}"
    be = r.get("break_even_pct")
    engine = s.get("engine")
    tail = "\n  POZOR: " + r["warning"] if r.get("warning") else ""
    return (
        f"{rec.get('id')}  {s.get('pair')} {s.get('timerange')}"
        f"{' [' + engine + ']' if engine else ''}  "
        f"obchodov {r.get('trades')}  PnL {r.get('pnl_pct'):+.2f} % ({r.get('pnl_abs'):+.0f} {r.get('stake_currency', 'USDT')})  "
        f"PF {r.get('profit_factor')}  WR {r.get('winrate')} %  maxDD {r.get('max_drawdown_pct')} %  "
        f"break-even {be if be is None else f'{be:.4f} %'}{tail}"
    )


def warn_parity(space: dict, strategy: str) -> None:
    """Upozorní na parametre, ktoré rozbijú paritu s Pine — ale nezakáže ich."""
    from ..param_meta import param_metadata

    risky = {m["name"]: m for m in param_metadata(strategy) if m.get("breaks_parity")}
    hit = [name for name in space if name in risky]
    if not hit:
        return
    print("POZOR: " + ", ".join(hit) + " mení sizing alebo časovanie prevzaté z TradingView.",
          file=sys.stderr)
    print("       Výsledok sa už nedá porovnať s Pine ani s golden testami - ak to je zámer, "
          "je to v poriadku.\n", file=sys.stderr)


def _selected_runs(args: argparse.Namespace, store: Any, *, strategy: str | None = None) -> list[dict]:
    """Behy z `--runs` alebo z dopytu — hotové, s obchodmi, najviac `--limit`."""
    if args.runs:
        chcene = [x.strip() for x in args.runs.split(",") if x.strip()]
        zaznamy = [r for r in (store.get(i) for i in chcene) if r]
    else:
        from ..store import strategy_of

        vsetky = store.search(" ".join(args.query)) if args.query else store.all()
        zaznamy = [r for r in vsetky if r.get("status") == "done"
                   and ((r.get("result") or {}).get("trades") or 0) > 0
                   and (strategy is None or strategy_of(r) == strategy)]
    zaznamy = zaznamy[:args.limit]
    if not zaznamy:
        raise SystemExit("ziadne dobehnute behy s obchodmi (skus iny dopyt)")
    return zaznamy


def _trades_of(store: Any, zaznamy: list[dict], *, with_market: bool = True) -> list[dict]:
    """Obchody vybraných behov, obohatené kresbami (a stavom trhu) a bez duplicít.

    Referenčné okná sa prekrývajú o mesiac, takže bez `analytics.dedupe` by zliate behy
    tej istej konfigurácie ten mesiac počítali dvakrát. Koľko vypadlo, sa vypíše.
    """
    from ... import analytics as an

    nacitane = an.trades_of(zaznamy, store.trades, store.chart, with_market=with_market)
    if not nacitane.trades:
        raise SystemExit("vybrane behy nemaju ulozene obchody")
    if nacitane.duplicates:
        print(f"POZOR: {nacitane.duplicates} obchodov bolo v dvoch behoch naraz (prekryvajuce "
              "sa okna) - pocitaju sa raz.", file=sys.stderr)
    return nacitane.trades


def _run_record(store: Any, url: str, run_id: str) -> dict | None:
    """Záznam behu zo skladu, a keď tam nie je, z bežiacej webapp (iný klon, iný `runs/`)."""
    rec = store.get(run_id)
    if rec is not None or not server_alive(url):
        return rec
    try:
        return (api(url, f"/api/runs/{run_id}") or {}).get("record")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _run_data(store: Any, url: str, run_id: str) -> tuple[list[dict], dict | None]:
    """Obchody a kresby behu — zo skladu, a keď tam nie sú, z bežiacej webapp.

    Beh mohol vzniknúť vo webapp, ktorá stojí nad iným klonom repozitára a má vlastný
    `runs/`. Vtedy ho lokálny sklad nevidí a jediný, kto ho má, je práve tá webapp.
    """
    trades = store.trades(run_id)
    if trades:
        return trades, store.chart(run_id)
    if not server_alive(url):
        return [], None
    try:
        det = api(url, f"/api/runs/{run_id}")
        chart = api(url, f"/api/runs/{run_id}/chart")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return [], None
    return det.get("trades") or [], {"objects": chart.get("objects") or []}


def _progress_text(progress: dict | None, status: str | None = "running") -> str:
    """`37/200 epoch, este ~12 min` - alebo len stav, kym prva epocha nie je hotova."""
    if status != "running" or not progress:
        return str(status)
    if not progress.get("done"):
        return f"pripravuje sa ({progress.get('elapsed_s', 0) // 60} min od startu)"
    text = f"{progress['done']}/{progress.get('total', '?')} epoch"
    if progress.get("eta_s") is not None:
        text += f", este ~{max(1, round(progress['eta_s'] / 60))} min"
    return text
