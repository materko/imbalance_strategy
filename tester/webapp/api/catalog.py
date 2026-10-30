"""Katalóg stratégií (`/api/catalog`) — karta Stratégie: každá stratégia s profilmi po
skupinách (prešli smernicou / repozitár / vlastné) a najlepším behom z histórie.

Všetko sa skladá z toho, čo už existuje: zoznam behov z indexu (`store.all()`), profily
z `repo_profiles` / `profiles` a krivka najlepšieho behu z jeho `run.json`. Trh a typ
stratégie (`STRATEGIA_TRH_TYP`) aj zlúčenie C# portov s predlohou robí stránka.
"""

from __future__ import annotations

import re
from pathlib import PurePath
from typing import Any

from fastapi import APIRouter

from tradebot.strategies import STRATEGIES

from .. import profiles as user_profiles
from ..repo_profiles import profile_info
from ..store import strategy_of
from .context import AppContext
from .meta import SMERNICE_PREFIXES

#: Najlepší beh stratégie: aspoň toľko obchodov, PF > 1 a znesiteľný drawdown; poradie podľa
#: zisku na jednotku drawdownu. PF nad stropom je skoro vždy pár obchodov bez strát, nie edge.
BEST_MIN_TRADES = 40
BEST_MAX_DD = 35.0
BEST_MAX_PF = 50.0

#: Krivka do karty: toľko bodov stačí na tvar, viac je len objem odpovede.
EQUITY_POINTS = 48

#: Čísla z popisu profilu, ktorý prešiel smernicou („… · PF 1,52 · WR 91 % · 154 obch/rok ·
#: … · max DD 1 113 $ · posl. rok PF 1,46"). Ranná úloha ich píše do `_title`; behy s týmto
#: profilom v histórii často nie sú, takže iné čísla profil nemá.
_TITLE_NUMS = {
    "pf": r"(?<!rok )\bPF ([\d,]+)",
    "winrate": r"\bWR ([\d,]+) ?%",
    "trades_year": r"([\d ]+) obch/rok",
    "max_dd_usd": r"max DD ([\d  ]+) ?\$",
    "pf_last_year": r"posl\. rok PF ([\d,]+)",
}


def _num(text: str) -> float | None:
    try:
        return float(re.sub(r"[\s ]", "", text).replace(",", "."))
    except ValueError:
        return None


def title_metrics(title: str) -> dict[str, float]:
    """Čísla z `_title` profilu smernice; čo v popise nie je, chýba."""
    out = {}
    for key, pattern in _TITLE_NUMS.items():
        m = re.search(pattern, title or "")
        if m and (v := _num(m.group(1))) is not None:
            out[key] = v
    return out


def profile_group(name: str, strategy: str) -> str:
    """`smernica` (prešiel smernicou), `user` (vlastný profil testera) alebo `repo`."""
    if name.startswith(SMERNICE_PREFIXES):
        return "smernica"
    return "user" if user_profiles.is_user(name, strategy) else "repo"


def _profile_stem(value: Any) -> str:
    """Meno profilu z `settings.profile` behu — býva meno aj cesta k súboru."""
    return PurePath(str(value).replace("\\", "/")).stem.lower() if value else ""


def payoff_ratio(result: dict[str, Any]) -> float | None:
    """Dosiahnuté RR: priemerný zisk / priemerná strata = PF × počet strát / počet ziskov."""
    try:
        pf, wins, losses = float(result["profit_factor"]), int(result["wins"]), int(result["losses"])
    except (KeyError, TypeError, ValueError):
        return None
    return round(pf * losses / wins, 3) if wins > 0 and losses > 0 else None


def _metrics(rec: dict[str, Any]) -> dict[str, Any]:
    s, r = rec.get("settings") or {}, rec.get("result") or {}
    return {"id": rec.get("id"), "pair": s.get("pair"), "timeframe": s.get("timeframe"),
            "timerange": s.get("timerange"), "engine": s.get("engine"),
            **{k: r.get(k) for k in ("trades", "pnl_pct", "profit_factor", "winrate",
                                     "max_drawdown_pct", "break_even_pct")},
            "rr": payoff_ratio(r)}


def _score(rec: dict[str, Any]) -> float | None:
    """Zisk na jednotku drawdownu, keď beh prejde sitom `BEST_*`; inak `None`."""
    r = rec.get("result") or {}
    try:
        trades, pf = float(r.get("trades") or 0), float(r.get("profit_factor") or 0)
        pnl, dd = float(r.get("pnl_pct") or 0), float(r.get("max_drawdown_pct") or 0)
    except (TypeError, ValueError):
        return None
    if rec.get("status") != "done" or trades < BEST_MIN_TRADES or not 1 < pf <= BEST_MAX_PF or dd >= BEST_MAX_DD:
        return None
    return pnl / max(dd, 1.0)


def equity_curve(rec: dict[str, Any] | None, points: int = EQUITY_POINTS) -> list[float]:
    """Kumulatívny zisk z `series.equity` (`[čas, zisk obchodu, súčet]`), preriedený na `points`."""
    eq = ((rec or {}).get("series") or {}).get("equity") or []
    vals = [float(p[2]) for p in eq if isinstance(p, (list, tuple)) and len(p) > 2
            and isinstance(p[2], (int, float))]
    if len(vals) > points:
        vals = [vals[round(i * (len(vals) - 1) / (points - 1))] for i in range(points)]
    return [round(v, 2) for v in vals]


def catalog(records: list[dict[str, Any]], load_run) -> list[dict[str, Any]]:
    """Karta za každú stratégiu registry. `load_run(id)` vráti celý záznam behu (so `series`)."""
    by_strategy: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_strategy.setdefault(strategy_of(rec), []).append(rec)

    out = []
    for key, spec in STRATEGIES.items():
        runs = by_strategy.get(key, [])
        scored = [(sc, rec) for rec in runs if (sc := _score(rec)) is not None]
        best = max(scored, key=lambda x: x[0])[1] if scored else None

        # najlepší beh každého profilu (podľa mena súboru, behy nesú meno aj cestu)
        best_of_profile: dict[str, tuple[float, dict[str, Any]]] = {}
        for sc, rec in scored:
            stem = _profile_stem((rec.get("settings") or {}).get("profile"))
            if stem and (stem not in best_of_profile or sc > best_of_profile[stem][0]):
                best_of_profile[stem] = (sc, rec)

        profiles = []
        for name, info in profile_info(key).items():
            group = profile_group(name, key)
            hit = best_of_profile.get(name.lower())
            profiles.append({
                "name": name, "group": group, "title": info.get("title") or "",
                "pair": info.get("pair") or "", "timeframe": info.get("timeframe") or "",
                "created": info.get("created") or "",
                "claimed": title_metrics(info.get("title") or "") if group == "smernica" else {},
                "best_run": _metrics(hit[1]) if hit else None,
            })

        best_out = None
        if best:
            best_out = {**_metrics(best), "profile": _profile_stem((best.get("settings") or {}).get("profile")),
                        "equity": equity_curve(load_run(best["id"]))}
        out.append({
            "key": key, "title": spec.title, "csharp": spec.csharp_dir is not None,
            "default_timeframe": spec.default_timeframe, "has_explainer": spec.explainer_path.is_file(),
            "runs": sum(1 for r in runs if r.get("status") == "done"),
            "last_run": max((r.get("id") or "" for r in runs), default="") or None,
            "best": best_out, "profiles": profiles,
        })
    return out


def build(ctx: AppContext) -> APIRouter:
    router = APIRouter()
    store = ctx.store

    @router.get("/api/catalog")
    def catalog_view():
        """Všetky stratégie s profilmi a najlepším behom — karta Stratégie."""
        return {"strategies": catalog(store.all(), store.get)}

    return router
