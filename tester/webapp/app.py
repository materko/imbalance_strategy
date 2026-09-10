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
from tradebot.strategies import STRATEGIES, get_spec
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
from .anstore import AnalyticsStore
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
    fee: float | None = Field(None, description="poplatok na stranu ako podiel; "
                                                "bez neho podľa trhu (krypto 0.0005, CFD polovica spreadu)")
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


class AnalyticsSaveRequest(BaseModel):
    """Uloženie záveru analytiky do histórie."""

    report: dict[str, Any] = Field(..., description="celý výstup `/api/analytics`")
    note: str = Field("", max_length=500, description="čo sa tým zisťovalo")
    user: str = Field("", max_length=100)


class PropRequest(BaseModel):
    """Prop výzva nad tými istými behmi, aké má karta Analytika.

    Polia pravidiel sú `None` = nechať tak, ako ich má predloha. Čísla predlôh sú
    odpísané z verejných stránok firiem a menia sa — formulár ich preto ukazuje aj
    so zdrojom a dá sa každé prepísať.
    """

    runs: list[str] = Field(default_factory=list, description="behy; prázdne = podľa `q`")
    q: str = Field("", description="dopyt na behy (syntax ako vyhľadávanie v histórii)")
    strategy: str = Field("ibs")
    rules: str = Field("ftmo2", description="ktorá predloha pravidiel")
    limit: int = Field(40, ge=1, le=500)
    step: int = Field(1, ge=1, le=100, description="každý N-tý obchod ako štart pokusu")
    risks: list[float] = Field(default_factory=list, description="riziká v %; prázdne = default")

    account: float | None = Field(None, gt=0)
    targets: list[float] | None = Field(None, description="ciele fáz v %")
    max_daily_loss_pct: float | None = Field(None, ge=0)
    max_loss_pct: float | None = Field(None, gt=0)
    trailing: str | None = None
    trailing_freeze_at_start: bool | None = None
    min_days: int | None = Field(None, ge=0)
    max_day_share_pct: float | None = Field(None, ge=0, le=100)
    cost: float | None = Field(None, ge=0)
    payout_pct: float | None = Field(None, gt=0, le=100)
    refund: bool | None = None
    horizon_days: int | None = Field(None, ge=0)


class PaperRequest(BaseModel):
    """Zadanie merania — tie isté behy, aké má karta Analytika."""

    runs: list[str] = Field(default_factory=list, description="behy; prázdne = podľa `q`")
    q: str = Field("", description="dopyt na behy (syntax ako vyhľadávanie v histórii)")
    strategy: str = Field("ibs")
    title: str = Field("", description="nadpis dokumentu")
    name: str = Field("", description="názov súboru; inak MERANIE_<strategia>_<trh>_<datum>.md")
    risk_pct: float = Field(1.0, gt=0, le=10)
    iterations: int = Field(400, ge=50, le=5000, description="opakovaní testu proti náhode")
    limit: int = Field(40, ge=1, le=500)


class HyperoptRequest(RunRequest):
    """Hľadanie parametrov — to isté zadanie ako sweep, len sa v rozsahu hľadá."""

    space: dict[str, str] = Field(..., description="parameter -> `od:do:krok` alebo `a,b,c`")
    goal: str = Field("break_even", description="podľa čoho vybrať najlepšiu epochu")
    max_dd: float | None = Field(None, description="strop na max drawdown v %")
    min_trades: int | None = Field(None, description="minimum obchodov za rok, inak je epocha mimo")
    epochs: int = Field(200, ge=1, le=5000, description="koľko konfigurácií vyskúšať")
    seed: int | None = Field(None, description="random-state optimalizátora, na zopakovateľný beh")
    verify: bool = Field(True, description="pustiť víťaza na referenčných oknách")


class MatrixRequest(RunRequest):
    """Ten istý profil na viacerých trhoch a TF — `pair`/`timeframe` sú referenčné."""

    pairs: list[str] = Field(..., min_length=1, description="trhy matice")
    timeframes: list[str] = Field(..., min_length=1, description="timeframy matice")
    goal: str = Field("break_even", description="podľa čoho zoradiť bunky")
    min_trades: int | None = Field(10, description="pod týmto počtom je bunka označená ako šum")
    relative: bool = Field(True, description="prepočítať prahy z absolútnych bodov na atr")


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


def _plateau_note() -> str:
    return ("Susedia víťaza: o krok a o dva kroky na každom ladenom parametri. Plató znamená, "
            "že presná hodnota nie je kritická; špička, že optimum je tvar toho okna.")


def _null_note(vysledky: dict[str, Any]) -> str:
    """Rozdiel medzi dvoma náhodami je hodnota samotného výberu času.

    Keď je stratégia výrazne lepšia než náhoda kedykoľvek, ale nie než náhoda v tých
    istých hodinách, celý jej edge je v tom, KEDY obchoduje — a to sa dá mať aj bez nej.
    """
    kedykolvek = (vysledky.get("anytime") or {}).get("sigma")
    v_seanse = (vysledky.get("session") or {}).get("sigma")
    if kedykolvek is None or v_seanse is None:
        return ""
    if kedykolvek - v_seanse > 1.0:
        return ("Proti náhode kedykoľvek je stratégia výrazne lepšia, proti náhode v tých "
                "istých hodinách už nie — väčšina jej edge je v tom, KEDY obchoduje, "
                "nie na čom vstupuje.")
    return ("Obe náhody dávajú podobný výsledok, takže edge nie je len o výbere času — "
            "je v tom, na čom stratégia vstupuje.")


def _goal_note(goal: str, max_dd: float | None, min_trades: int | None) -> str:
    """Zadanie ako veta — to isté pre sweep aj hyperopt, aby sa nedali rozísť."""
    from .. import sweep as sweep_mod

    return sweep_mod.describe(goal, max_dd, min_trades)


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
    anstore = AnalyticsStore()
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
    def runs(q: str = "", limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)):
        recs = store.search(q) if q.strip() else store.all()
        return {"total": len(recs), "runs": [summarize_for_list(r, defaults_of(r)) for r in recs[offset:offset + limit]]}

    def _fee_for(fee: float | None, pair: str, timeframe: str, timerange: str) -> dict[str, Any]:
        """`{"fee": …, "fee_note": …}` — zadané číslo, alebo náklad toho trhu."""
        from .. import fees as fees_mod

        if fee is not None:
            return {"fee": fee, "fee_note": "zadané vo formulári"}
        hodnota, note = fees_mod.for_pair(pair, timeframe, timerange)
        if hodnota is None:
            return {"fee": 0.0, "fee_note": f"neznámy: {note}"}
        return {"fee": hodnota, "fee_note": note}

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
            # Jeden default pre vsetky trhy nefunguje: 0,05 % je Binance taker, kym na
            # CFD je provizia drobna a naklad je spread. Bez zadaneho `fee` sa berie
            # naklad instrumentu a ulozi sa aj to, odkial cislo je.
            **_fee_for(req.fee, req.pair, req.timeframe, req.timerange),
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

    @app.get("/api/sweeps")
    def sweeps_list(limit: int = 50, strategy: str | None = None):
        """Mriežky z histórie, od najnovšej; `strategy` obmedzí na jednu stratégiu.

        Nikde sa neukladajú zvlášť — značka `settings.sweep` je v každom behu, takže
        zoznam je len preskupená história. Vďaka tomu prežije reštart aj `git pull`
        cudzích behov a nedá sa rozísť s tým, čo je naozaj odbehnuté.

        Filter podľa stratégie nie je pohodlie: parametre sú v každej stratégii iné,
        takže mriežka cez `rrRatio` nemá v ponuke pre Donchian breakout čo robiť.
        """
        if strategy is not None and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        from .. import sweep as sweep_mod

        skupiny: dict[str, dict[str, Any]] = {}
        for rec in list(store.all()) + list(runner.snapshot()):
            tag = (rec.get("settings") or {}).get("sweep") or {}
            sweep_id = tag.get("id")
            if not sweep_id or (strategy is not None and strategy_of(rec) != strategy):
                continue
            nastavenia = rec["settings"]
            polozka = skupiny.setdefault(sweep_id, {
                "id": sweep_id,
                "goal": tag.get("goal") or "break_even",
                "goal_note": sweep_mod.describe(tag.get("goal") or "break_even",
                                                tag.get("max_dd"), tag.get("min_trades")),
                "params": list(tag.get("values") or {}),
                "pair": nastavenia.get("pair"),
                "timeframe": nastavenia.get("timeframe"),
                "timerange": nastavenia.get("timerange"),
                "strategy": strategy_of(rec),
                "user": rec.get("user") or "",
                "done": 0, "pending": 0,
            })
            if rec.get("status") in ("queued", "running"):
                polozka["pending"] += 1
            else:
                polozka["done"] += 1
        rad = sorted(skupiny.values(), key=lambda x: x["id"], reverse=True)
        return {"total": len(rad), "sweeps": rad[:limit]}

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

    @app.get("/api/hyperopt/meta")
    def hyperopt_meta(strategy: str = "ibs"):
        """Čo o ladení vie stratégia — odporúčaný priestor a varovania.

        Vedomosť je pri stratégii (`hyperopt_cls`), nie v appke; stránka ju len ukáže.
        """
        from .. import hyperopt as ho

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        znalosti = ho.knowledge_note(strategy)
        return {"strategy": strategy, "note": znalosti,
                "suggested": ho.suggested(strategy),
                "warn": dict(ho.knowledge(get_spec(strategy)).WARN),
                "windows": list(ho.REFERENCE_WINDOWS),
                "default_epochs": ho.DEFAULT_EPOCHS}

    @app.post("/api/hyperopts")
    def hyperopt_start(req: HyperoptRequest):
        """Zaradí hyperopt do tej istej fronty ako backtesty — vyťaží všetky jadrá."""
        from .. import hyperopt as ho

        if not req.space:
            raise HTTPException(422, "hyperopt potrebuje aspoň jeden parameter")
        defaults = DEFAULTS.get(req.strategy) or DEFAULTS["ibs"]
        for name in req.space:
            if name not in defaults:
                raise HTTPException(422, f"neznámy parameter {name!r}")
        try:
            plan = ho.build_plan(req.space, strategy=req.strategy, goal=req.goal,
                                 max_dd=req.max_dd, min_trades=req.min_trades, note=req.note)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

        base = _run_settings(req)
        settings = {**base, "hyperopt": {
            "knobs": dict(req.space), "goal": req.goal, "max_dd": req.max_dd,
            "min_trades": req.min_trades, "epochs": req.epochs, "seed": req.seed,
            "verify": req.verify,
        }}
        popis = ", ".join(f"{k}={v}" for k, v in req.space.items())
        note = f"hyperopt {popis}" + (f" — {req.note}" if req.note else "")
        try:
            job = runner.submit(req.params, settings, note=note, user=_clean_user(req.user))
        except (ConfigError, ValueError) as exc:
            raise HTTPException(422, str(exc))
        return {"id": job.id, "epochs": req.epochs, "goal": req.goal,
                "goal_note": _goal_note(req.goal, req.max_dd, req.min_trades),
                "warn": ho.warnings_for(req.space, req.strategy),
                "knobs": {k.name: (list(k.choices) if k.choices is not None
                                   else {"low": k.low, "high": k.high, "step": k.step})
                          for k in plan.knobs}}

    @app.get("/api/hyperopts")
    def hyperopts_list(limit: int = 50, strategy: str | None = None):
        """Hyperopty z histórie, od najnovšieho; `strategy` obmedzí na jednu stratégiu."""
        if strategy is not None and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        out = []
        for rec in list(store.all()) + list(runner.snapshot()):
            zadanie = (rec.get("settings") or {}).get("hyperopt") or {}
            if not zadanie.get("knobs"):
                continue
            if strategy is not None and strategy_of(rec) != strategy:
                continue
            nastavenia = rec["settings"]
            out.append({
                "id": rec["id"],
                "status": rec.get("status"),
                "strategy": strategy_of(rec),
                "params": list(zadanie["knobs"]),
                "goal": zadanie.get("goal"),
                "goal_note": _goal_note(zadanie.get("goal") or "break_even",
                                        zadanie.get("max_dd"), zadanie.get("min_trades")),
                "pair": nastavenia.get("pair"),
                "timeframe": nastavenia.get("timeframe"),
                "timerange": nastavenia.get("timerange"),
                "epochs": zadanie.get("epochs"),
                "epochs_done": zadanie.get("epochs_done"),
                "user": rec.get("user") or "",
            })
        out.sort(key=lambda x: x["id"], reverse=True)
        return {"total": len(out), "hyperopts": out[:limit]}

    def _plateau_of(run_id: str, zadanie: dict[str, Any]) -> dict[str, Any] | None:
        """Vyhodnotenie okolia víťaza, keď už nejakí susedia bežali."""
        from .. import montecarlo as mc, plateau as pl

        susedia = [r for r in store.all()
                   if ((r.get("settings", {}).get("plateau") or {}).get("id")) == run_id]
        bezia = [j for j in runner.snapshot()
                 if ((j.get("settings", {}).get("plateau") or {}).get("id")) == run_id]
        if not susedia and not bezia:
            return None
        ladene = [r for r in store.all()
                  if ((r.get("settings", {}).get("hyperopt_run") or {}).get("id")) == run_id
                  and (r["settings"].get("hyperopt_run") or {}).get("tuned")]
        if not ladene:
            return {"pending": len(bezia), "rows": [], "verdict": ""}
        vitaz = ladene[0]

        # Interval vitaza z Monte Carla je meradlo, ktorym sa rozhoduje, ci sused "drzi".
        interval = (None, None)
        obchody = store.trades(vitaz["id"])
        if len(obchody) >= mc.MIN_TRADES:
            vysledok = mc.analyze(obchody, fee_pct=(vitaz["settings"].get("fee") or 0) * 100,
                                  iterations=1500)
            be = vysledok["break_even"]
            interval = (be["lo"], be["hi"])
        hodnotenie = pl.assess(vitaz, susedia, interval)
        return {**hodnotenie.to_dict(), "pending": len(bezia), "note": _plateau_note()}

    @app.get("/api/hyperopts/{run_id}")
    def hyperopt_detail(run_id: str):
        """Zadanie, epochy, víťaz a overovacie behy na referenčných oknách."""
        from .. import hyperopt as ho

        rec = store.get(run_id)
        if rec is None:
            live = [j for j in runner.snapshot() if j["id"] == run_id]
            if not live:
                raise HTTPException(404, "taký hyperopt v histórii nie je")
            rec = live[0]
        zadanie = (rec.get("settings") or {}).get("hyperopt") or {}
        if not zadanie.get("knobs"):
            raise HTTPException(404, "tento beh nie je hyperopt")

        epochs = store.extra(run_id, "epochs.json") or []
        overenia = [r for r in store.all()
                    if ((r.get("settings", {}).get("hyperopt_run") or {}).get("id")) == run_id]
        overenia += [j for j in runner.snapshot()
                     if ((j.get("settings", {}).get("hyperopt_run") or {}).get("id")) == run_id]
        ladene = rec["settings"].get("timerange")
        return {
            "id": run_id,
            "status": rec.get("status"),
            "error": rec.get("error"),
            "strategy": strategy_of(rec),
            "settings": {k: rec["settings"].get(k) for k in
                         ("pair", "timeframe", "timerange", "fee", "wallet", "exchange", "profile")},
            "hyperopt": zadanie,
            "goal_note": _goal_note(zadanie.get("goal") or "break_even",
                                    zadanie.get("max_dd"), zadanie.get("min_trades")),
            "params": list(zadanie["knobs"]),
            "epochs": sorted(epochs, key=lambda e: (not e.get("usable"), e.get("loss", 0)))[:60],
            "best": zadanie.get("best"),
            "overrides": zadanie.get("overrides"),
            "verify": [{
                "id": r["id"],
                "status": r.get("status"),
                "timerange": r["settings"].get("timerange"),
                "tuned": bool((r["settings"].get("hyperopt_run") or {}).get("tuned")),
                "result": {k: (r.get("result") or {}).get(k) for k in
                           ("trades", "pnl_pct", "winrate", "max_drawdown_pct", "break_even_pct")},
            } for r in sorted(overenia, key=lambda r: r["settings"].get("timerange") or "")],
            "verdict": ho.verdict(overenia, ladene) if overenia else "",
            "plateau": _plateau_of(run_id, zadanie),
        }

    @app.get("/api/analytics")
    def analytics(q: str = "", runs: str = "", strategy: str = "ibs",
                  quantiles: int = Query(4, ge=2, le=10),
                  min_bucket: int = Query(8, ge=2, le=200),
                  limit_runs: int = Query(40, ge=1, le=500),
                  nulltest: bool = True,
                  null_iterations: int = Query(600, ge=50, le=5000),
                  portfolio: bool = True,
                  risk_pct: float = Query(1.0, gt=0, le=10),
                  decay: bool = True,
                  decay_parts: int = Query(4, ge=2, le=12)):
        """Ktorá skupina obchodov kazí výsledok — nad jedným behom alebo nad viacerými.

        `runs` je zoznam id oddelený čiarkou; bez neho sa vezmú behy podľa `q` (tá istá
        syntax ako vyhľadávanie v histórii). Obchody sa zliajú dokopy: jeden beh má rádovo
        desiatky obchodov a to je na rozdelenie na skupiny málo.
        """
        from .. import analytics as an

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        if runs.strip():
            chcene = [r.strip() for r in runs.split(",") if r.strip()]
            zaznamy = [rec for rec in (store.get(i) for i in chcene) if rec]
        else:
            vsetky = store.search(q) if q.strip() else store.all()
            zaznamy = [r for r in vsetky if strategy_of(r) == strategy
                       and r.get("status") == "done"
                       and ((r.get("result") or {}).get("trades") or 0) > 0]
        zaznamy = zaznamy[:limit_runs]
        if not zaznamy:
            raise HTTPException(404, "žiadne dobehnuté behy s obchodmi")

        obchody: list[dict[str, Any]] = []
        pouzite = []
        for rec in zaznamy:
            t = store.trades(rec["id"])
            if not t:
                continue
            # Kresby nesú plán obchodu (SL/TP úroveň), z ktorého je vzdialenosť stopu
            # a plánovaný RR — bez nich tie dve vlastnosti vypadnú.
            obchody += an.enrich([dict(x) for x in t], store.chart(rec["id"]), strategy,
                                 pair=rec["settings"].get("pair") or "",
                                 timeframe=rec["settings"].get("timeframe") or "3m")
            pouzite.append({"id": rec["id"], "pair": rec["settings"].get("pair"),
                            "timeframe": rec["settings"].get("timeframe"),
                            "timerange": rec["settings"].get("timerange"),
                            "trades": len(t), "profile": rec["settings"].get("profile"),
                            "note": rec.get("note") or ""})
        if not obchody:
            raise HTTPException(404, "vybrané behy nemajú uložené obchody")

        report = an.analyze(obchody, strategy=strategy, quantiles=quantiles,
                            min_bucket=min_bucket)
        pary = sorted({r["pair"] for r in pouzite if r["pair"]})
        report["runs"] = pouzite
        report["pairs"] = pary
        # Zliať obchody z rôznych párov ide, ale prahy v bodoch ani vzdialenosti stopu
        # nie sú medzi nimi porovnateľné - nech to je vidieť.
        report["mixed_pairs"] = len(pary) > 1
        # Z akej konfiguracie tie obchody su. Zliat behy tej istej konfiguracie na roznych
        # oknach je v poriadku; zliat rozne konfiguracie znamena miesat rozne strategie.
        report["config"] = an.config_spread(zaznamy)
        report["strategy"] = strategy

        # Charakter sa meria z tych istych obchodov: aky typ strategie to je, sa neda
        # oddelit od toho, ktora skupina obchodov kazi vysledok - jedno vysvetluje druhe.
        # Pohyb pred vstupom sa da zmerat len na jednom pare (sviecky su parove).
        from .. import character as chr_mod

        prvy = pouzite[0]
        report["character"] = chr_mod.measure(
            obchody, pair="" if len(pary) > 1 else (prvy["pair"] or ""),
            timeframe=prvy["timeframe"] or "3m").to_dict()
        report["archetypes"] = [a.__dict__ for a in chr_mod.ARCHETYPES]

        # Test proti nahode ide z tej istej vzorky obchodov: "break-even 0,064 %" je bez
        # referencie cislo, nie odpoved. Nahodne vstupy sa losuju zo sviecok, takze to ide
        # len na jednom trhu - pri zliatych paroch by sa nemalo z coho losovat.
        # Portfolio: tie iste behy ako jeden ucet. Clen je JEDEN beh - behy toho isteho
        # trhu v tom istom case su alternativy, nie clenovia, a modul to nahlasi.
        report["portfolio"] = None
        if portfolio and len(zaznamy) > 1:
            from .. import portfolio as pf_mod

            per: dict[str, list[dict[str, Any]]] = {}
            for rec in zaznamy:
                t = store.trades(rec["id"])
                if not t:
                    continue
                nast = rec["settings"]
                meno = f"{nast.get('pair')} {nast.get('timeframe')} {nast.get('timerange')}"
                per[meno] = an.enrich([dict(x) for x in t], store.chart(rec["id"]), strategy)
            if len(per) > 1:
                report["portfolio"] = pf_mod.analyze(per, records=zaznamy, risk_pct=risk_pct)

        # Slabne edge? Posledne obdobie proti tomu, co strategia robievala. Ide to aj
        # pri zliatych paroch: break-even je pomer zisku k objemu, takze sa da scitat.
        report["decay"] = None
        if decay:
            from .. import decay as dc_mod

            try:
                report["decay"] = dc_mod.analyze(obchody, parts=decay_parts).to_dict()
            except ValueError:
                report["decay"] = None

        report["nulltest"] = None
        if nulltest and not report["mixed_pairs"]:
            from .. import nulltest as nt_mod

            vysledky = {}
            for null in nt_mod.NULLS:
                try:
                    vysledky[null] = nt_mod.compare(
                        obchody, pair=pary[0], timeframe=prvy["timeframe"] or "3m",
                        iterations=null_iterations, null=null).to_dict()
                except (ValueError, FileNotFoundError):
                    vysledky = {}
                    break
            if vysledky:
                report["nulltest"] = {"nulls": vysledky,
                                      "note": _null_note(vysledky)}
        return report

    @app.get("/api/analytics/history")
    def analytics_history(strategy: str = "", limit: int = Query(50, ge=1, le=500)):
        """Uložené analytiky — per stratégia, od najnovšej.

        Vlastnosti aj parametre sú pri každej stratégii iné, takže zliať ich do jedného
        zoznamu by znamenalo porovnávať neporovnateľné.
        """
        if strategy and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        return {"items": anstore.list(strategy, limit=limit)}

    @app.get("/api/analytics/history/{an_id}")
    def analytics_history_one(an_id: str):
        zaznam = anstore.get(an_id)
        if zaznam is None:
            raise HTTPException(404, f"analytika {an_id} v histórii nie je")
        return zaznam

    @app.post("/api/analytics/history")
    def analytics_save(req: AnalyticsSaveRequest):
        """Uloží záver, nie obchody — tie ostávajú v behoch, na ktoré sa záznam odkazuje."""
        strategy = req.report.get("strategy") or "ibs"
        if strategy not in STRATEGIES:
            raise HTTPException(422, f"neznáma stratégia {strategy!r}")
        if not (req.report.get("runs") or []):
            raise HTTPException(422, "report nemá behy, z ktorých vznikol")
        return anstore.save(req.report, strategy=strategy, note=req.note.strip(),
                            user=_clean_user(req.user) or "")

    @app.delete("/api/analytics/history/{an_id}")
    def analytics_delete(an_id: str):
        if not anstore.delete(an_id):
            raise HTTPException(404, f"analytika {an_id} v histórii nie je")
        return {"deleted": an_id}

    @app.get("/api/prop/meta")
    def prop_meta():
        """Predlohy pravidiel pre formulár — vrátane toho, odkiaľ sú čísla."""
        from .. import prop as pr

        return {"presets": {k: {**v.__dict__, "targets": list(v.targets),
                                "phases": v.phases}
                            for k, v in pr.PRESETS.items()},
                "risks": list(pr.RISKS),
                "trailing": {"nie": "statický (z počiatočného zostatku)",
                             "vrchol": "trailing z vrcholu (intraday)",
                             "koniec_dna": "trailing z konca dňa (EOD)"}}

    @app.post("/api/prop")
    def prop_run(req: PropRequest):
        """Prehrá obchody vybraných behov cez pravidlá výzvy, riziko po riziku."""
        from dataclasses import replace

        from .. import analytics as an, prop as pr

        if req.strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {req.strategy!r}")
        if req.rules not in pr.PRESETS:
            raise HTTPException(422, f"neznáme pravidlá {req.rules!r}; "
                                     f"známe: {', '.join(pr.PRESETS)}")
        zmeny = {k: v for k, v in req.model_dump().items()
                 if v is not None and k in pr.Rules.__dataclass_fields__ and k != "name"}
        if req.targets:
            zmeny["targets"] = tuple(req.targets)
        try:
            pravidla = replace(pr.PRESETS[req.rules], **zmeny)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

        if req.runs:
            zaznamy = [rec for rec in (store.get(i) for i in req.runs) if rec]
        else:
            vsetky = store.search(req.q) if req.q.strip() else store.all()
            zaznamy = [r for r in vsetky if strategy_of(r) == req.strategy
                       and r.get("status") == "done"
                       and ((r.get("result") or {}).get("trades") or 0) > 0]
        zaznamy = zaznamy[:req.limit]
        if not zaznamy:
            raise HTTPException(404, "žiadne dobehnuté behy s obchodmi")

        obchody: list[dict[str, Any]] = []
        for rec in zaznamy:
            t = store.trades(rec["id"])
            if t:
                obchody += an.enrich([dict(x) for x in t], store.chart(rec["id"]), req.strategy)
        if not obchody:
            raise HTTPException(404, "vybrané behy nemajú uložené obchody")

        rizika = req.risks or list(pr.RISKS)
        vysledky = pr.risk_table(obchody, pravidla, risks=rizika, step=req.step)
        najlepsi = max(vysledky, key=lambda r: (r.ev if r.ev is not None else -1e18))
        return {"rules": {**pravidla.__dict__, "targets": list(pravidla.targets),
                          "phases": pravidla.phases},
                "trades": len(obchody), "runs": len(zaznamy),
                # Odkial su obchody: prop vyzva sa nepocita z ziadnej vlastnej
                # konfiguracie, ale z obchodov vybranych behov.
                "config": an.config_spread(zaznamy),
                "pairs": sorted({r["settings"].get("pair") for r in zaznamy
                                 if r["settings"].get("pair")}),
                "run_ids": [r["id"] for r in zaznamy],
                "results": [r.to_dict() for r in vysledky],
                "best_risk": najlepsi.risk_pct, "verdict": najlepsi.verdict}

    @app.post("/api/paper")
    def paper_write(req: PaperRequest):
        """Zapíše meranie do `docs/merania/` zo všetkého, čo o tých behoch vieme.

        Nové backtesty nespúšťa — píše sa len to, čo v histórii už je. Na čo behy
        nestačia, dokument povie nahlas aj s príkazom, ktorým sa to doplní.
        """
        from .. import paper as pp

        if req.strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {req.strategy!r}")
        if req.runs:
            zaznamy = [rec for rec in (store.get(i) for i in req.runs) if rec]
        else:
            vsetky = store.search(req.q) if req.q.strip() else store.all()
            zaznamy = [r for r in vsetky if strategy_of(r) == req.strategy
                       and r.get("status") == "done"
                       and ((r.get("result") or {}).get("trades") or 0) > 0]
        zaznamy = zaznamy[:req.limit]

        prikaz = ("python -m tester.webapp.cli paper --runs "
                  + ",".join(r["id"] for r in zaznamy))
        try:
            doc = pp.build(zaznamy, store, strategy=req.strategy, title=req.title,
                           risk_pct=req.risk_pct, null_iterations=req.iterations,
                           command=prikaz)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        cesta = pp.write(doc, req.name)
        return {"path": str(cesta.relative_to(REPO) if cesta.is_relative_to(REPO) else cesta),
                "runs": len(zaznamy),
                "sections": [{"title": x.title, "verdict": x.verdict, "gap": x.gap}
                             for x in doc.sections]}

    @app.post("/api/hyperopts/{run_id}/plateau")
    def hyperopt_plateau(run_id: str):
        """Zaradí susedov víťaza — o krok a o dva kroky na každom ladenom parametri.

        Hyperopt vráti jedno číslo a to nehovorí nič o tom, či je stredom niečoho, alebo
        náhodnou dierou v šume. Susedia to rozhodnú.
        """
        from .. import plateau as pl

        rec = store.get(run_id)
        zadanie = ((rec or {}).get("settings") or {}).get("hyperopt") or {}
        if not zadanie.get("knobs"):
            raise HTTPException(404, "taký hyperopt v histórii nie je")
        vitaz_params = zadanie.get("overrides")
        if not vitaz_params:
            raise HTTPException(422, "hyperopt nemá víťaza (žiadna epocha nesplnila mantinely)")

        ladene = [r for r in store.all()
                  if ((r.get("settings", {}).get("hyperopt_run") or {}).get("id")) == run_id
                  and (r["settings"].get("hyperopt_run") or {}).get("tuned")]
        if not ladene:
            raise HTTPException(422, "beh víťaza na ladenom okne v histórii nie je "
                                     "(hyperopt bežal bez overenia?)")
        vitaz = ladene[0]

        susedia = pl.neighbours(zadanie["knobs"], vitaz_params)
        if not susedia:
            raise HTTPException(422, "víťaz nemá v rozsahu plánu žiadnych susedov")

        base = {k: v for k, v in vitaz["settings"].items() if k != "hyperopt_run"}
        ids, preskocene = [], {}
        for sused in susedia:
            params = {**(vitaz.get("params") or {}), sused.param: sused.value}
            settings = {**base, "plateau": {"id": run_id, "param": sused.param,
                                            "value": sused.value, "step": sused.step}}
            try:
                job = runner.submit(params, settings,
                                    note=f"okolie {run_id}: {sused.param}={sused.value}",
                                    user=_clean_user(None))
            except (ConfigError, ValueError) as exc:
                preskocene[sused.label] = str(exc)
                continue
            ids.append(job.id)
        if not ids:
            raise HTTPException(422, "žiadny sused sa nezaradil: "
                                     + "; ".join(f"{k}: {v}" for k, v in preskocene.items()))
        return {"id": run_id, "runs": ids, "neighbours": len(ids), "skipped": preskocene}

    @app.get("/api/matrix/meta")
    def matrix_meta(wallet: float = 10000, timeframe: str = "3m", strategy: str = "ibs"):
        """Čo o matici treba vedieť dopredu: kde sa jeden kontrakt nezmestí do peňaženky."""
        from .. import matrix as mx

        if strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        pary = [p["pair"] for p in available_pairs()]
        male = mx.wallet_check(pary, float(wallet), timeframe=timeframe)
        return {"pairs": pary, "small_wallet": male,
                "suggested_wallet": round(max(male.values()) * 2) if male else None}

    @app.post("/api/matrices")
    def matrix_start(req: MatrixRequest):
        """Zaradí každú bunku matice ako obyčajný beh s tou istou značkou."""
        from .. import matrix as mx

        znama = {p["pair"] for p in available_pairs()}
        nezname = [p for p in req.pairs if p not in znama]
        if nezname:
            raise HTTPException(422, f"neznáme páry: {', '.join(nezname)}")
        try:
            bunky = mx.expand(req.pairs, req.timeframes)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

        params = dict(req.params)
        prepocet: list[str] = []
        if req.relative:
            params, prepocet = mx.to_relative(
                params, strategy=req.strategy, ref_pair=req.pair,
                ref_timeframe=req.timeframe, timerange=req.timerange)

        bunky, preskocene = mx.playable(
            bunky, exchange=req.exchange or engines.DEFAULT_EXCHANGE,
            engine=req.engine, params=params)
        if not bunky:
            raise HTTPException(422, "žiadna bunka matice sa spustiť nedá: "
                                     + "; ".join(f"{k}: {v}" for k, v in preskocene.items()))

        base = _run_settings(req)
        matrix_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        ids = []
        for cell in bunky:
            settings = {**base, "pair": cell.pair, "timeframe": cell.timeframe,
                        "matrix": {"id": matrix_id, "pair": cell.pair,
                                   "timeframe": cell.timeframe, "goal": req.goal,
                                   "relative": bool(req.relative),
                                   "min_trades": req.min_trades}}
            note = (f"matica {matrix_id}: {cell.pair} {cell.timeframe}"
                    + (f" — {req.note}" if req.note else ""))
            try:
                job = runner.submit(params, settings, note=note, user=_clean_user(req.user))
            except (ConfigError, ValueError) as exc:
                preskocene[cell.key] = str(exc)
                continue
            ids.append(job.id)
        if not ids:
            raise HTTPException(422, "žiadna bunka sa nezaradila: "
                                     + "; ".join(f"{k}: {v}" for k, v in preskocene.items()))
        return {"id": matrix_id, "runs": ids, "cells": len(ids), "skipped": preskocene,
                "converted": prepocet,
                "wallet_small": mx.wallet_check([c.pair for c in bunky],
                                                float(req.wallet or 10000),
                                                timeframe=req.timeframes[0])}

    @app.get("/api/matrices")
    def matrices_list(limit: int = 50, strategy: str | None = None):
        """Matice z histórie, od najnovšej."""
        if strategy is not None and strategy not in STRATEGIES:
            raise HTTPException(404, f"neznáma stratégia {strategy!r}")
        skupiny: dict[str, dict[str, Any]] = {}
        for rec in list(store.all()) + list(runner.snapshot()):
            tag = (rec.get("settings") or {}).get("matrix") or {}
            if not tag.get("id"):
                continue
            if strategy is not None and strategy_of(rec) != strategy:
                continue
            polozka = skupiny.setdefault(tag["id"], {
                "id": tag["id"], "strategy": strategy_of(rec),
                "timerange": rec["settings"].get("timerange"),
                "goal": tag.get("goal"), "relative": tag.get("relative"),
                "pairs": set(), "timeframes": set(), "done": 0, "pending": 0,
                "user": rec.get("user") or "",
            })
            polozka["pairs"].add(rec["settings"].get("pair"))
            polozka["timeframes"].add(rec["settings"].get("timeframe"))
            if rec.get("status") in ("queued", "running"):
                polozka["pending"] += 1
            else:
                polozka["done"] += 1
        rad = []
        for p in sorted(skupiny.values(), key=lambda x: x["id"], reverse=True)[:limit]:
            rad.append({**p, "pairs": sorted(x for x in p["pairs"] if x),
                        "timeframes": sorted(x for x in p["timeframes"] if x)})
        return {"total": len(skupiny), "matrices": rad}

    @app.get("/api/matrices/{matrix_id}")
    def matrix_detail(matrix_id: str):
        """Tabuľka `trh × timeframe` a verdikt — aj kým sa dopočítava."""
        from .. import matrix as mx

        zaznamy = [r for r in store.all()
                   if ((r.get("settings", {}).get("matrix") or {}).get("id")) == matrix_id]
        live = [j for j in runner.snapshot()
                if ((j.get("settings", {}).get("matrix") or {}).get("id")) == matrix_id]
        if not zaznamy and not live:
            raise HTTPException(404, "taká matica v histórii nie je")

        tag = (zaznamy or live)[0]["settings"]["matrix"]
        goal = tag.get("goal") or "break_even"
        poradie = mx.rank(zaznamy, goal, min_trades=tag.get("min_trades") or mx.MIN_TRADES)
        tabulka = mx.matrix(poradie + [{
            "id": j["id"], "status": j.get("status"), "settings": j["settings"], "result": {},
        } for j in live])
        return {
            "id": matrix_id,
            "goal": goal,
            "goal_note": _goal_note(goal, None, tag.get("min_trades")),
            "relative": bool(tag.get("relative")),
            "timerange": (zaznamy or live)[0]["settings"].get("timerange"),
            "done": len(zaznamy),
            "pending": len(live),
            "table": tabulka,
            "verdict": mx.verdict(zaznamy) if zaznamy else "",
            "best": [{"pair": r["settings"]["pair"], "timeframe": r["settings"].get("timeframe"),
                      "id": r["id"], "ok": r["sweep_ok"], "why": r["sweep_why"],
                      "result": {k: (r.get("result") or {}).get(k) for k in
                                 ("trades", "pnl_pct", "winrate", "max_drawdown_pct",
                                  "break_even_pct")}}
                     for r in poradie[:12]],
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
