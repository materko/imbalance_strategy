"""FastAPI aplikácia — REST API nad `store`, `runner` a `gitsync` + statická stránka.

    python -m tester.webapp                    # 127.0.0.1:8765
    TRADEBOT_WEB_HOST=0.0.0.0 TRADEBOT_WEB_PORT=8765  # v Dockeri

Žiadne prihlásenie: aplikácia je určená na lokálne spustenie (alebo za reverse
proxy s vlastnou autentifikáciou). Meno testera si tester nastaví v hlavičke
stránky (drží sa v prehliadači) a posiela sa s každým behom aj s Push; predvolené
je `TRADEBOT_USER`, inak `git config user.name`.
"""

from __future__ import annotations

import json
import os

from tradebot.core.env import getenv
import re
from collections import OrderedDict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tradebot.core.config import ConfigError
from tradebot.strategies import STRATEGIES
from . import chart as chart_data
from . import gitsync
from . import profiles as user_profiles
from .pine_meta import param_metadata
from tradebot.core.types import INSTRUMENTS
from .. import engines
from .. import montecarlo
from .runner import (
    REPO, BacktestRunner, available_pairs, check_market_rules, default_params, instrument_for_pair,
    list_profiles, profile_instruments, profile_titles, tf_minutes,
)
from .store import RunStore, strategy_of, summarize_for_list

STATIC = Path(__file__).resolve().parent / "static"
_TIMERANGE_RE = re.compile(r"^\d{8}-\d{8}$")

#: Posledné výsledky Monte Carla. Beh sa po dokončení už nemení, takže rovnaký dopyt
#: dá vždy to isté (seed je fixný) — a pri behu s tisíckami obchodov to trvá sekundy.
_MC_CACHE: "OrderedDict[tuple, dict[str, Any]]" = OrderedDict()
_MC_CACHE_MAX = 32


def montecarlo_cached(run_id: str, trades: list[dict[str, Any]], opts: dict[str, Any]) -> dict[str, Any]:
    key = (run_id, *(round(v, 6) if isinstance(v, float) else v for v in opts.values()))
    if key not in _MC_CACHE:
        result = montecarlo.analyze(trades, **opts)
        result["run_id"] = run_id
        _MC_CACHE[key] = result
        while len(_MC_CACHE) > _MC_CACHE_MAX:
            _MC_CACHE.popitem(last=False)
    _MC_CACHE.move_to_end(key)
    return _MC_CACHE[key]


def _asset_version() -> str:
    """Odtlačok skriptu a štýlov — mení sa s každou zmenou súboru, inak je stály."""
    stamp = 0.0
    for name in ("app.js", "app.css"):
        try:
            stamp = max(stamp, (STATIC / name).stat().st_mtime)
        except OSError:
            continue
    return format(int(stamp), "x")


class _NoCacheStatic(StaticFiles):
    """Stránka a skript sa po aktualizácii nesmú ťahať z cache prehliadača.

    Bez toho tester po `git pull` a reštarte vidí starú stránku (a nové pole jednoducho
    chýba), kým si nespraví hard refresh. Súbory sú lokálne a malé, takže revalidácia
    pri každom načítaní nič nestojí.
    """

    def is_not_modified(self, response_headers, request_headers) -> bool:  # noqa: D102
        return False

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


def current_user() -> str:
    return getenv("USER") or gitsync.user_name() or os.environ.get("USERNAME", "") or "tester"


class RunRequest(BaseModel):
    params: dict[str, Any]
    pair: str
    strategy: str = Field("ibs", description="kľúč stratégie z registry (tradebot.strategies.STRATEGIES)")
    timeframe: str = Field("3m", description="TF grafu, na ktorom stratégia počíta (ako v TradingView)")
    timerange: str = Field(..., description="YYYYMMDD-YYYYMMDD")
    fee: float | None = Field(0.0005, description="poplatok na stranu ako podiel (0.0005 = 0,05 %)")
    wallet: float = 10000
    timeframe_detail: str | None = "1m"
    engine: str | None = Field(None, description="freqtrade | multicharts (emulátor); None = podľa dát")
    exchange: str | None = Field(None, description="burza pre Freqtrade beh; None = fiktívna Tester")
    sweep: dict[str, Any] | None = Field(None, description="značka behu z mriežky: id, hodnoty, kritérium")
    profile: str | None = None
    note: str = ""
    user: str | None = Field(None, max_length=80, description="meno testera z hlavičky stránky")


class SweepRequest(RunRequest):
    """Beh na mriežke hodnôt — inak to isté zadanie ako jeden beh."""

    space: dict[str, str] = Field(..., description="parameter -> `od:do:krok` alebo `a,b,c`")
    goal: str = Field("break_even", description="podľa čoho vybrať najlepší beh")
    max_dd: float | None = Field(None, description="strop na max drawdown v %")
    min_trades: int | None = Field(None, description="menej obchodov = bod je mimo mantinelov")


class GitPushRequest(BaseModel):
    author: str | None = Field(None, max_length=80)
    message: str | None = Field(None, max_length=200)


class ProfileSaveRequest(BaseModel):
    """Nový vlastný profil — buď z behu (`from_run`), alebo priamo z parametrov."""

    name: str = Field(..., max_length=48)
    strategy: str = Field("ibs", description="stratégia profilu; pri `from_run` sa berie z behu")
    from_run: str | None = None
    params: dict[str, Any] | None = None
    instrument: str | None = None
    timeframe: str | None = Field(None, description="TF grafu, na ktorom je profil ladený")
    timerange: str | None = None
    fee: float | None = None
    wallet: float | None = None
    timeframe_detail: str | None = None
    base: str | None = Field(None, max_length=200, description="profil, z ktorého sa vychádzalo")
    note: str = Field("", max_length=200)
    overwrite: bool = False


class ProfileRenameRequest(BaseModel):
    name: str = Field(..., max_length=48)


def _fmt_value(value: Any) -> str:
    """Hodnota bodu mriežky do poznámky behu."""
    if isinstance(value, dict):
        return f"{value.get('value')}@{value.get('unit')}"
    return f"{value:g}" if isinstance(value, float) else str(value)


def _clean_user(name: str | None) -> str:
    name = (name or "").strip()
    return name[:80] if name else current_user()


def create_app(store: RunStore | None = None, runner: BacktestRunner | None = None) -> FastAPI:
    store = store or RunStore()
    runner = runner or BacktestRunner(store)
    app = FastAPI(title="TradeBot backtest webapp", version="0.2")
    app.state.store = store
    app.state.runner = runner
    #: Pine defaulty každej stratégie — proti nim sa počítajú odchýlky behu.
    DEFAULTS = {key: spec.config_cls().to_dict() for key, spec in STRATEGIES.items()}
    #: Metadáta formulára stratégie. Parametre a defaulty sú kód (nemenia sa za behu),
    #: zoznam profilov sa číta vždy nanovo — tester si ich cez API ukladá, premenúva a maže.
    PARAM_META = {key: param_metadata(spec) for key, spec in STRATEGIES.items()}

    def strategy_meta(key: str) -> dict[str, Any]:
        return {
            "params": PARAM_META[key],
            "defaults": DEFAULTS[key],
            "profiles": list_profiles(key),
            "profile_titles": profile_titles(key),
            "profile_instruments": profile_instruments(key),
            "user_profiles": user_profiles.user_names(key),
        }

    def defaults_of(rec: dict[str, Any]) -> dict[str, Any]:
        return DEFAULTS.get(strategy_of(rec), DEFAULTS["ibs"])

    @app.get("/")
    def index():
        # Stránka bez cache a odkazy na skript a štýly s verziou. `no-cache` samo nestačí:
        # prehliadač, ktorý si súbor uložil ešte PREDTÝM, než sme hlavičku pridali, ho
        # považuje za čerstvý podľa vlastnej heuristiky a znova sa nepýta (Chrome to robí,
        # Edge nie). Verzia v URL je iný kľúč cache, takže stará kópia sa nemá ako použiť.
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        v = _asset_version()
        html = html.replace('href="/static/app.css"', f'href="/static/app.css?v={v}"')
        html = html.replace('src="/static/app.js"', f'src="/static/app.js?v={v}"')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})

    @app.get("/api/meta")
    def meta():
        pairs = available_pairs()
        by_key = {key: strategy_meta(key) for key in STRATEGIES}
        return {
            # `params`/`defaults`/`profiles`… na najvyššej úrovni = stratégia "ibs" (spätná
            # kompatibilita pre CLI a testy); stránka pracuje so `strategy_meta[key]`.
            **by_key["ibs"],
            "strategies": [spec.public() for spec in STRATEGIES.values()],
            "exchanges": [{"key": e, "title": engines.EXCHANGE_TITLES.get(e, e)}
                          for e in engines.EXCHANGES],
            "default_exchange": engines.DEFAULT_EXCHANGE,
            # Strop mriežky a cena jedného roka behu — stránka z toho poskladá odhad času.
            "max_sweep_runs": MAX_SWEEP_RUNS,
            "sweep_seconds_per_year": SECONDS_PER_YEAR,
            "strategy_meta": by_key,
            "pairs": pairs,
            "user": current_user(),
            "branch": gitsync.branch(),
            "queue": runner.snapshot(),
        }

    @app.get("/api/profiles")
    def profiles_list(strategy: str = Query("ibs")):
        """Profily stratégie do formulára: z repozitára (nemenné) a vlastné (menné aj mazateľné)."""
        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        return {"strategy": strategy, "profiles": list_profiles(strategy), "user_profiles": user_profiles.user_names(strategy),
                "profile_titles": profile_titles(strategy), "profile_instruments": profile_instruments(strategy)}

    @app.post("/api/profiles")
    def profile_save(req: ProfileSaveRequest):
        params, instrument, comment = req.params, req.instrument, req.note or None
        strategy = req.strategy
        setup = {"timeframe": req.timeframe, "timerange": req.timerange, "fee": req.fee,
                 "wallet": req.wallet, "detail": req.timeframe_detail}
        base = req.base
        if req.from_run:
            rec = store.get(req.from_run)
            if rec is None:
                raise HTTPException(404, "beh neexistuje")
            params = rec["params"]
            settings = rec.get("settings", {})
            strategy = strategy_of(rec)
            instrument = instrument or instrument_for_pair(settings["pair"])
            # beh vie všetko, čo profil potrebuje — čo prišlo v requeste, má prednosť
            for key, src in (("timeframe", "timeframe"), ("timerange", "timerange"),
                             ("fee", "fee"), ("wallet", "wallet"), ("detail", "timeframe_detail")):
                setup[key] = setup[key] if setup[key] is not None else settings.get(src)
            base = base or settings.get("profile")
            popis = f"z behu {req.from_run} ({settings.get('pair')}, {settings.get('timerange')})"
            comment = f"{comment} — {popis}" if comment else popis
        if params is None:
            raise HTTPException(422, "chýbajú parametre: pošli `from_run` alebo `params`")
        # vypnutý 1m detail je tiež informácia, nie „nič" — ulož ho ako false
        setup["detail"] = setup["detail"] or False
        if not instrument:
            raise HTTPException(422, "chýba `instrument` profilu")
        try:
            if strategy not in STRATEGIES:
                raise HTTPException(422, f"neznáma stratégia {strategy!r}")
            user_profiles.save(req.name, params, instrument, comment=comment,
                               title=req.note or None, base=base, settings=setup,
                               overwrite=req.overwrite, strategy=strategy)
        except FileExistsError as exc:
            raise HTTPException(409, str(exc))
        except (user_profiles.ProfileError, ConfigError) as exc:
            raise HTTPException(422, str(exc))
        return {"name": req.name.strip(), **profiles_list(strategy)}

    @app.patch("/api/profiles/{name}")
    def profile_rename(name: str, req: ProfileRenameRequest, strategy: str = Query("ibs")):
        try:
            user_profiles.rename(name, req.name)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc))
        except FileExistsError as exc:
            raise HTTPException(409, str(exc))
        except user_profiles.ProfileError as exc:
            raise HTTPException(422, str(exc))
        return {"name": req.name.strip(), **profiles_list(strategy)}

    @app.delete("/api/profiles/{name}")
    def profile_delete(name: str, strategy: str = Query("ibs")):
        try:
            if not user_profiles.delete(name):
                raise HTTPException(404, f"profil {name} neexistuje")
        except user_profiles.ProfileError as exc:
            raise HTTPException(422, str(exc))
        return {"ok": True, **profiles_list(strategy)}

    @app.get("/api/profiles/{name:path}")
    def profile(name: str, strategy: str = Query("ibs")):
        """Názov profilu stratégie (`golden_binance_btcusdt_3m` alebo `ibs/golden_binance_btcusdt_3m`),
        alebo cesta k JSON v repozitári (napr. `docs/profily_archiv/ibs/x.json`)."""
        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        target: str | Path = name
        if name.endswith(".json"):
            path = (REPO / name).resolve()
            if not path.is_relative_to(REPO) or path.suffix != ".json" or not path.exists():
                raise HTTPException(404, f"profil {name!r} nie je JSON v repozitári")
            target = path
        elif "/" in name:
            strategy = name.split("/", 1)[0]  # "ibs/golden_..." nesie stratégiu v názve
            if strategy not in STRATEGIES:
                raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        try:
            params, instrument = default_params(target, strategy)
        except (ConfigError, FileNotFoundError) as exc:
            raise HTTPException(404, str(exc))
        setup = user_profiles.settings_of(name, strategy)
        return {"name": name, "strategy": strategy, "params": params, "instrument": instrument,
                "timeframe": setup.get("timeframe"), "settings": setup,
                "base": user_profiles.base_of(name, strategy),
                "kind": "user" if user_profiles.is_user(name, strategy) else "builtin"}

    @app.get("/api/runs")
    def runs(q: str = "", limit: int = 500):
        recs = store.search(q) if q.strip() else store.all()
        return {"total": len(recs), "runs": [summarize_for_list(r, defaults_of(r)) for r in recs[:limit]]}

    def _run_settings(req: RunRequest) -> dict[str, Any]:
        """Overí zadanie a poskladá `settings` behu. Spoločné pre jeden beh aj pre sweep."""
        if not _TIMERANGE_RE.match(req.timerange):
            raise HTTPException(422, "timerange musí byť YYYYMMDD-YYYYMMDD")
        a, b = req.timerange.split("-")
        if a >= b:
            raise HTTPException(422, "začiatok obdobia musí byť pred koncom")
        if req.strategy not in STRATEGIES:
            raise HTTPException(422, f"neznáma stratégia {req.strategy!r}; známe: {sorted(STRATEGIES)}")
        if req.timeframe not in chart_data.TIMEFRAMES:
            raise HTTPException(422, f"timeframe {req.timeframe!r} nie je podporovaný ({', '.join(chart_data.TIMEFRAMES)})")
        if req.timeframe not in chart_data.available_timeframes(req.pair):
            raise HTTPException(422, f"pre {req.pair} nie sú stiahnuté {req.timeframe} dáta")
        detail = req.timeframe_detail or None
        if detail and tf_minutes(detail) >= tf_minutes(req.timeframe):
            detail = None  # detail fillov musí byť jemnejší než TF grafu, inak ho Freqtrade odmietne
        # Pravidlá trhu (spot: bez shortov a páky) sa kontrolujú skôr než engine —
        # nezmyselný beh má povedať, čo je zle na ňom, nie na výbere engine.
        try:
            check_market_rules(req.pair, req.params)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        try:
            inst = INSTRUMENTS[instrument_for_pair(req.pair)]
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        engine = req.engine or engines.default_engine(inst, req.timeframe)
        if engine not in engines.ENGINES:
            raise HTTPException(422, f"neznámy engine {engine!r}; známe: {', '.join(engines.ENGINES)}")
        exchange = req.exchange or engines.DEFAULT_EXCHANGE
        if engine == engines.FREQTRADE and exchange not in engines.EXCHANGES:
            raise HTTPException(422, f"neznáma burza {exchange!r}; známe: {', '.join(engines.EXCHANGES)}")
        possible = engines.available(inst, req.timeframe, exchange)
        if engine not in possible:
            preco = (engines.freqtrade_blocker(inst, req.timeframe, exchange)
                     if engine == engines.FREQTRADE else "chýbajú 1m sviečky")
            raise HTTPException(422, (
                f"engine {engines.ENGINE_TITLES[engine]} sa na {req.pair} {req.timeframe} "
                f"spustiť nedá ({preco}); dostupné: "
                f"{', '.join(engines.ENGINE_TITLES[e] for e in possible) or 'žiadne'}"))
        return {
            "strategy": req.strategy,
            "exchange": exchange if engine == engines.FREQTRADE else None,
            "sweep": req.sweep,
            "pair": req.pair,
            "engine": engine,
            "timeframe": req.timeframe,
            "timerange": req.timerange,
            "fee": req.fee,
            "wallet": req.wallet,
            "timeframe_detail": detail,
            "profile": req.profile,
        }

    @app.post("/api/runs")
    def submit(req: RunRequest):
        settings = _run_settings(req)
        try:
            job = runner.submit(req.params, settings, note=req.note, user=_clean_user(req.user))
        except (ConfigError, ValueError) as exc:
            raise HTTPException(422, str(exc))
        return job.public()

    #: Mriežka nemá strop: sweep má zmysel púšťať cez noc alebo na serveri a číslo,
    #: ktoré by sme vymysleli, by len prekážalo. Namiesto obmedzenia dostane tester
    #: odhad času vopred a tlačidlo, ktorým celú mriežku zruší naraz.
    #: `TRADEBOT_MAX_SWEEP_RUNS` strop zapne tomu, kto ho chce (0 = bez stropu).
    MAX_SWEEP_RUNS = max(0, int(getenv("MAX_SWEEP_RUNS", "0") or 0))

    #: Meraný čas jedného roka backtestu s 1m detailom na tomto stroji (~30 s).
    #: Slúži len na odhad „ako dlho to pobeží", nie na rozhodovanie.
    SECONDS_PER_YEAR = 30

    def _sweep_minutes(points: int, timerange: str) -> int:
        """Hrubý odhad, ako dlho mriežka pobeží — behy idú za sebou, jeden po druhom."""
        try:
            a, b = (datetime.strptime(x, "%Y%m%d") for x in timerange.split("-"))
        except ValueError:
            return 0
        years = max((b - a).days, 1) / 365.0
        return max(1, round(points * years * SECONDS_PER_YEAR / 60))

    def _point_note(point: dict[str, Any]) -> str:
        return ", ".join(f"{k}={_fmt_value(v)}" for k, v in point.items())

    @app.post("/api/sweeps")
    def sweep_start(req: SweepRequest):
        """Rozbalí mriežku a zaradí každý bod ako samostatný beh s tou istou značkou."""
        from .. import sweep as sweep_mod

        if req.goal not in sweep_mod.GOALS:
            raise HTTPException(422, f"neznáme kritérium {req.goal!r}; "
                                     f"známe: {', '.join(sweep_mod.GOALS)}")
        defaults = DEFAULTS.get(req.strategy) or DEFAULTS["ibs"]
        space = {}
        for name, spec in req.space.items():
            if name not in defaults:
                raise HTTPException(422, f"neznámy parameter {name!r}")
            try:
                values = sweep_mod.parse_values(spec)
            except ValueError as exc:
                raise HTTPException(422, f"{name}: {exc}")
            if not values:
                raise HTTPException(422, f"{name}: žiadne hodnoty")
            space[name] = values
        if not space:
            raise HTTPException(422, "sweep potrebuje aspoň jeden parameter")

        points = sweep_mod.expand(space)
        minutes = _sweep_minutes(len(points), req.timerange)
        if MAX_SWEEP_RUNS and len(points) > MAX_SWEEP_RUNS:
            raise HTTPException(422, (
                f"mriežka má {len(points)} behov (odhadom {minutes} min), strop je {MAX_SWEEP_RUNS} — "
                "zúž rozsah alebo krok; strop sa dá zdvihnúť premennou TRADEBOT_MAX_SWEEP_RUNS"))

        # Celá mriežka sa overí ešte pred zaradením: keby prvý bod prešiel a piaty mal
        # hodnotu mimo Pine rozsahu, tester by mal vo fronte štyri behy a chybu k tomu.
        config_cls = STRATEGIES[req.strategy].config_cls
        for point in points:
            merged = {**req.params, **point}
            try:
                config_cls.from_dict({k: v for k, v in merged.items() if not k.startswith("_")})
                check_market_rules(req.pair, merged)
            except (ConfigError, ValueError) as exc:
                raise HTTPException(422, f"bod {_point_note(point)}: {exc}")

        base = _run_settings(req)
        # Kým mriežka čaká vo fronte, nič sa v tabuľke nedeje — a tester klikne znova.
        # Rovnaké zadanie preto odmietneme a povieme, kde ho má hľadať.
        podpis = json.dumps([base, points], sort_keys=True, default=str)
        for job in runner.snapshot():
            tag = (job.get("settings") or {}).get("sweep") or {}
            if tag.get("signature") == podpis:
                raise HTTPException(409, (
                    f"tá istá mriežka už čaká vo fronte ({tag['id']}) — nedokončené body "
                    "sa dopočítavajú, výsledky pribúdajú v tabuľke. Zruš ich vo fronte, "
                    "ak si to rozmyslel."))
        # Sekunda nestačí: dva sweepy spustené rýchlo za sebou by mali tú istú značku
        # a v tabuľke by sa zliali do jednej mriežky.
        sweep_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        goal_note = sweep_mod.describe(req.goal, req.max_dd, req.min_trades)
        ids = []
        for point in points:
            settings = {**base, "sweep": {"id": sweep_id, "values": point, "goal": req.goal,
                                          "max_dd": req.max_dd, "min_trades": req.min_trades,
                                          "signature": podpis}}
            note = f"sweep {sweep_id}: {_point_note(point)}" + (f" — {req.note}" if req.note else "")
            try:
                job = runner.submit({**req.params, **point}, settings, note=note,
                                    user=_clean_user(req.user))
            except (ConfigError, ValueError) as exc:  # sieť pod sieťou, keby overenie niečo minulo
                raise HTTPException(422, f"bod {_point_note(point)}: {exc}")
            ids.append(job.id)
        return {"id": sweep_id, "runs": ids, "points": len(points), "goal": req.goal,
                "goal_note": goal_note, "minutes": minutes}

    @app.get("/api/sweeps/{sweep_id}")
    def sweep_detail(sweep_id: str):
        """Stav a poradie mriežky — vidno ju od zaradenia, nie až od prvého výsledku."""
        from .. import sweep as sweep_mod

        records = [r for r in store.all()
                   if (r.get("settings", {}).get("sweep") or {}).get("id") == sweep_id]
        fronta = runner.snapshot()
        live = [j for j in fronta
                if (j.get("settings", {}).get("sweep") or {}).get("id") == sweep_id]
        if not records and not live:
            raise HTTPException(404, "taký sweep v histórii nie je")

        tag = (records or live)[0]["settings"]["sweep"]
        ranked = sweep_mod.rank(records, tag.get("goal") or "break_even",
                                max_dd=tag.get("max_dd"), min_trades=tag.get("min_trades"))
        names = list(tag.get("values") or {})
        prazdny = dict.fromkeys(
            ("trades", "pnl_pct", "winrate", "max_drawdown_pct", "break_even_pct"))

        # Koľko cudzích behov je pred prvým bodom tejto mriežky. Bez toho vyzerá čakanie
        # ako zaseknutá appka — pritom pred ňou môže stáť iná mriežka.
        prve = next((i for i, j in enumerate(fronta) if j in live), None)
        pred = 0 if prve is None else sum(1 for j in fronta[:prve] if j not in live)
        bezi = next((j for j in live if j.get("status") == "running"), None)

        return {
            "id": sweep_id,
            "goal": tag.get("goal"),
            "goal_note": sweep_mod.describe(tag.get("goal") or "break_even",
                                            tag.get("max_dd"), tag.get("min_trades")),
            "params": names,
            "done": len(records),
            "running": len(live),
            "ahead": pred,
            "running_values": (bezi or {}).get("settings", {}).get("sweep", {}).get("values"),
            "rows": [{
                "id": r["id"],
                "values": r["settings"]["sweep"]["values"],
                "status": r.get("status"),
                "ok": r["sweep_ok"],
                "why": r["sweep_why"],
                "result": {k: (r.get("result") or {}).get(k) for k in prazdny},
            } for r in ranked] + [{
                "id": j["id"],
                "values": j["settings"]["sweep"]["values"],
                "status": j.get("status"),
                "ok": True,
                "why": "",
                "result": dict(prazdny),
            } for j in live],
        }

    @app.get("/api/queue")
    def queue():
        return runner.snapshot()

    @app.post("/api/queue/{job_id}/cancel")
    def cancel(job_id: str):
        if not runner.cancel(job_id):
            raise HTTPException(404, "beh nie je vo fronte ani nebeží")
        return {"ok": True}

    @app.post("/api/sweeps/{sweep_id}/cancel")
    def sweep_cancel(sweep_id: str):
        """Zruší všetky nedobehnuté body mriežky naraz.

        Toto je náhrada za strop na veľkosť: preklep v kroku sa opraví jedným klikom
        namiesto toho, aby sa mriežky zhora orezávali.
        """
        ids = [j["id"] for j in runner.snapshot()
               if (j.get("settings", {}).get("sweep") or {}).get("id") == sweep_id]
        if not ids:
            raise HTTPException(404, "z tejto mriežky už nič nebeží ani nečaká")
        return {"cancelled": sum(1 for i in ids if runner.cancel(i))}

    @app.get("/api/runs/{run_id}")
    def run(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            job = runner.job(run_id)
            if job is None:
                raise HTTPException(404, "beh neexistuje")
            return {"record": job.public(), "trades": [], "live": True}
        defaults = defaults_of(rec)
        rec["overrides"] = {k: v for k, v in rec.get("params", {}).items()
                            if not k.startswith("_") and defaults.get(k) != v}
        rec["has_chart"] = store.has_chart(run_id)
        return {"record": rec, "trades": store.trades(run_id), "live": False}

    @app.get("/api/runs/{run_id}/chart")
    def run_chart(run_id: str, start: int | None = Query(None, alias="from"),
                  end: int | None = Query(None, alias="to")):
        """Kresby enginu z behu, orezané na okno `from`–`to` (ms epoch)."""
        data = store.chart(run_id)
        if data is None:
            if store.get(run_id) is None:
                raise HTTPException(404, "beh neexistuje")
            raise HTTPException(404, "beh nemá uložené kresby (spustený staršou verziou)")
        objects = data["objects"] if start is None or end is None else chart_data.window(data, start, end)
        return {"meta": chart_data.summary(data), "objects": objects}

    @app.get("/api/candles")
    def candles(pair: str, tf: str = "3m", start: int = Query(..., alias="from"),
                end: int = Query(..., alias="to")):
        """Sviečky páru v okne `from`–`to` (ms epoch), najviac `MAX_CANDLES`."""
        if end <= start:
            raise HTTPException(422, "to musí byť väčšie než from")
        try:
            return chart_data.candles(pair, tf, start, end)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc))

    @app.get("/api/runs/{run_id}/montecarlo")
    def run_montecarlo(run_id: str, fee: float | None = None, account: float | None = None,
                       risk: float | None = None, risk_pct: float | None = None,
                       block: int = montecarlo.DEFAULT_BLOCK,
                       iterations: int = 10_000, seed: int = 0):
        """Bootstrap nad obchodmi behu — interval okolo výsledku a riziko účtu.

        Ráta sa až na vyžiadanie (rozbalenie sekcie v detaile), lebo pri behu s
        tisíckami obchodov to trvá jednotky sekúnd. Beh je nemenný, takže sa
        výsledok pamätá.
        """
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        trades = store.trades(run_id)
        if not trades:
            raise HTTPException(422, "beh nemá obchody, nie je čo premiešavať")
        settings = rec.get("settings") or {}
        risk_ref = montecarlo.sizing_of(rec)
        opts = {
            "fee_pct": fee if fee is not None else float(settings.get("fee") or 0.0) * 100.0,
            "account": account if account else float(settings.get("wallet") or 10_000.0),
            "risk_ref": risk_ref,
            "risk": risk if risk else risk_ref,
            "risk_pct": risk_pct or None,
            "block": max(1, min(int(block), 200)),
            "iterations": max(200, min(int(iterations), 50_000)),
            "seed": int(seed),
        }
        return montecarlo_cached(run_id, trades, opts)

    @app.get("/api/runs/{run_id}/log", response_class=PlainTextResponse)
    def run_log(run_id: str):
        job = runner.job(run_id)
        if job is not None and job.status in ("queued", "running"):
            return "\n".join(job.log_lines[-400:])
        return store.log(run_id)

    @app.get("/api/runs/{run_id}/profile.json")
    def run_profile(run_id: str):
        rec = store.get(run_id)
        if rec is None:
            raise HTTPException(404, "beh neexistuje")
        params = dict(rec["params"])
        params["_comment"] = [f"profil z behu {run_id} ({rec.get('settings', {}).get('pair')}, "
                              f"{rec.get('settings', {}).get('timerange')}) - export z webapp"]
        params["_strategy"] = strategy_of(rec)
        params["_instrument"] = instrument_for_pair(rec["settings"]["pair"])
        return JSONResponse(params, headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'})

    @app.delete("/api/runs/{run_id}")
    def delete(run_id: str):
        if not store.delete(run_id):
            raise HTTPException(404, "beh neexistuje")
        return {"ok": True}

    @app.get("/api/git/status")
    def git_status():
        return gitsync.status()

    @app.post("/api/git/pull")
    def git_pull():
        return gitsync.pull()

    @app.post("/api/git/push")
    def git_push(req: GitPushRequest | None = None):
        req = req or GitPushRequest()
        return gitsync.push(message=req.message, author=_clean_user(req.author))

    app.mount("/static", _NoCacheStatic(directory=str(STATIC)), name="static")
    return app


def default_timerange(pairs: list[dict[str, Any]]) -> str:
    """Posledných 365 dní dostupných dát — rozumný štart pre tabuľku."""
    to = max((p["to"] for p in pairs), default=str(date.today()))
    end = datetime.strptime(to, "%Y-%m-%d")
    start = end - timedelta(days=365)
    return f"{start:%Y%m%d}-{end:%Y%m%d}"


app = create_app()
