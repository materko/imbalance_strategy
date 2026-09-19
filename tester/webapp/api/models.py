"""Pydantic modely požiadaviek REST API webapp."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
    # Ďalšie značky, ktorými CLI aj runner spájajú behy do celkov. Musia prejsť API
    # nezmenené, inak beh z CLI cez bežiacu webapp stratí väzbu na svoj hyperopt,
    # okolie víťaza, checkup alebo maticu.
    hyperopt_run: dict[str, Any] | None = Field(None, description="overovací beh víťaza hyperoptu")
    plateau: dict[str, Any] | None = Field(None, description="sused víťaza hyperoptu")
    checkup: dict[str, Any] | None = Field(None, description="beh základnej analytiky stratégie")
    matrix: dict[str, Any] | None = Field(None, description="bunka matice trhov")
    profile: str | None = None
    note: str = ""
    user: str | None = Field(None, max_length=80, description="meno testera z hlavičky stránky")
    ai: dict[str, Any] | None = Field(None, description="AI vrstva (FreqAI): prah, okná, "
                                                        "model a čo smie meniť; None = vypnutá")


class SweepRequest(RunRequest):
    """Beh na mriežke hodnôt — inak to isté zadanie ako jeden beh."""

    space: dict[str, str] = Field(..., description="parameter -> `od:do:krok` alebo `a,b,c`")
    goal: str = Field("break_even", description="podľa čoho vybrať najlepší beh")
    max_dd: float | None = Field(None, description="strop na max drawdown v %")
    min_trades: int | None = Field(None, description="menej obchodov = bod je mimo mantinelov")


class PosudokRequest(BaseModel):
    """Posudok k uloženej analytike — text, ktorý čísla nepovedia."""

    text: str = Field("", max_length=20000)
    user: str = Field("", max_length=100)


class FillWindowsRequest(BaseModel):
    """Doplnenie chýbajúcich referenčných okien konfigurácie — podľa vzorového behu."""

    run_id: str = Field(..., description="beh konfigurácie, z ktorého sa vezmú parametre a nastavenia")
    user: str | None = Field(None, max_length=80)


class AnalyticsPrepareRequest(BaseModel):
    """Analytika profilu na trhu: ktoré referenčné okná už v histórii sú (a použijú sa)
    a ktoré sa dopočítajú. Tester zadá profil, pár a TF - behy si to nájde samo."""

    strategy: str = "ibs"
    profile: str = Field("", description="profil (repozitár, vlastný alebo cesta k JSON); prázdne = Pine defaulty")
    pair: str
    timeframe: str = "3m"
    engine: str | None = Field(None, description="freqtrade | multicharts; None = podľa dát")
    windows: list[str] | None = Field(None, description="okná YYYYMMDD-YYYYMMDD; None = referenčné")
    dry_run: bool = Field(False, description="len zistiť stav okien, nič nezaraďovať")
    user: str | None = Field(None, max_length=80)


class NoteRequest(BaseModel):
    """Poznámka k uloženej analytike — čo sa tým zisťovalo."""

    note: str = Field("", max_length=500)


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
    rules: str | list[str] = Field("ftmo2", description="predloha alebo zoznam predlôh; "
                                                        "`custom` = pravidlá z polí, `all` = všetky")
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


class ReplayRequest(BaseModel):
    """Prehratie bodu mriežky ako obyčajného behu."""

    user: str | None = Field(None, max_length=80)


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

class HubJobRequest(BaseModel):
    """Zadanie výpočtu na hub cez webapp (`/api/hub/jobs`) — tvar `tester.hub.client.submit`."""

    kind: str
    payload: dict[str, Any]
    cores: int | str | None = None
    queue: bool = False
    max_wait_seconds: float | None = None
    estimate_seconds: float | None = None
    note: str = ""
    version: str | None = None
    max_seconds: float | None = None


class HubOptions(BaseModel):
    """Voľby hubu k zadaniu z formulára: fronta, strop čakania a strop na čas behu."""

    queue: bool = True
    max_wait_minutes: float | None = None
    max_runtime_minutes: float | None = None
    cores: int | str | None = None


class HubRunRequest(RunRequest, HubOptions):
    """Beh z formulára, ale na hube — to isté zadanie ako `/api/runs`."""


class HubHyperoptRequest(HyperoptRequest, HubOptions):
    """Hyperopt z formulára na hube — to isté zadanie ako `/api/hyperopts`."""


class HubAcceptRequest(BaseModel):
    accept: bool


class HubConfigRequest(BaseModel):
    """Nastavenie agenta z karty Hub — to isté, čo `python -m tester.hub setup`."""

    name: str = Field(..., min_length=1, max_length=60)
    hub_url: str = Field(..., min_length=1)
    token: str = Field("", description="prázdne = nechať doterajší")
    accept: bool = True
    send: bool = True
    max_parallel: int = Field(0, ge=0, le=256, description="0 = podľa jadier")
