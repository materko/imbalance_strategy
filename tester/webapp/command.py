"""Príprava behu Freqtradu: príkaz, dočasný profil a ukončenie stromu procesov.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tradebot.core.candles import timeframe_minutes
from tradebot.core.paths import TMP_PROFILES, FREQTRADE_USER_DIR as USER_DIR
from tradebot.core.types import INSTRUMENTS
from tradebot.strategies import get_spec

from .. import engines
from .market import instrument_for_pair


def kill_tree(pid: int) -> int:
    """Zabije proces aj **všetky jeho deti**. Vráti, koľko procesov zabil.

    `Popen.kill()` zabije len rodiča — `python -m tester.ftrun`. Hyperopt ale epochy počíta
    v samostatných procesoch (joblib/loky, jeden na jadro) a tie na Windows po smrti rodiča
    **bežia ďalej**: počítajú, držia `hyperopt.lock` (ďalší hyperopt potom odmietne štart)
    a držia otvorenú rúru so stdout, takže čítanie výstupu neskončí a beh vo fronte ostane
    „beží". Preto sa zabíja celý strom, deti ako prvé.
    """
    import psutil

    try:
        rodic = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return 0
    try:
        deti = rodic.children(recursive=True)
    except psutil.Error:
        deti = []
    zabite = 0
    for proc in [*deti, rodic]:
        try:
            proc.kill()
            zabite += 1
        except psutil.Error:
            pass
    psutil.wait_procs([*deti, rodic], timeout=5)
    return zabite


#: `3m` → 3, `4h` → 240, `1w` → 10080. Prevod je v jadre, aby ho adaptéry aj nástroje
#: mali rovnaký (a aby `4h` nepadalo tam, kde niekto parsoval len minúty).
tf_minutes = timeframe_minutes


def build_command(python: str, profile_path: Path, settings: dict[str, Any]) -> list[str]:
    """`timeframe` je TF grafu, na ktorom stratégia počíta (ako TF grafu v TradingView);
    Freqtrade ním prebije `timeframe` stratégie. 1m detail má zmysel len pod ním."""
    tf = settings.get("timeframe") or "3m"
    inst = INSTRUMENTS[instrument_for_pair(settings["pair"])]
    ai = settings.get("ai")
    if ai and not ai.get("identifier"):
        # FreqAI si v backteste modely UKLADÁ pod `identifier` a pri rovnakom páre a okne
        # ich nabudúce načíta namiesto tréningu. S jedným menom pre všetko by beh s inými
        # parametrami (alebo inou stratégiou) ticho bežal na modeli natrénovanom na
        # cudzích signáloch. Meno preto nesie stratégiu a odtlačok profilu.
        import hashlib
        import json as _json

        # Z parametrov, nie z bajtov súboru: dočasný profil nesie v `_comment` id behu,
        # takže hash súboru by bol pre každý beh iný a model by sa nikdy nepoužil znova.
        profil = _json.loads(Path(profile_path).read_text(encoding="utf-8"))
        parametre = {k: v for k, v in profil.items() if not k.startswith("_")}
        odtlacok = hashlib.sha1(_json.dumps(
            {"p": parametre, "s": settings.get("strategy") or "ibs", "tf": tf},
            sort_keys=True, default=str).encode("utf-8")).hexdigest()[:10]
        ai = {**ai, "identifier": f"tb-{settings.get('strategy') or 'ibs'}-{odtlacok}"}
    cmd = [
        # nie holy freqtrade: obal najprv zaregistruje fiktivnu burzu Tester, ktora pozna
        # nase pary aj vsetky timeframy (tester/ftexchange.py)
        python, "-m", "tester.ftrun", "backtesting",
        # Fiktivna burza dostane config s `stake_currency` podla kotacie paru - Dukascopy
        # symboly su v USD, JPY, EUR aj CAD a Freqtrade vyhodi z whitelistu kazdy par,
        # ktoreho mena nesedi so stake_currency (a hned potom skonci na "No pair in whitelist").
        # So zapnutou AI vrstvou ide config s blokom `freqai` navyše; inak je to ten istý.
        "--config", str(engines.ai_config(inst, settings.get("exchange"), tf, ai)
                        if ai else
                        engines.stake_config(inst, settings.get("exchange"))),
        "--userdir", str(USER_DIR),
        "--strategy", get_spec(settings.get("strategy") or "ibs").freqtrade_class,
        "--cache", "none",
        "--export", "trades",
        "--timerange", settings["timerange"],
        "--pairs", settings["pair"],
        "--timeframe", tf,
        "--dry-run-wallet", str(settings.get("wallet", 10000)),
    ]
    if settings.get("fee") is not None:
        cmd += ["--fee", str(settings["fee"])]
    detail = settings.get("timeframe_detail", "1m")
    if detail and tf_minutes(detail) < tf_minutes(tf):
        cmd += ["--timeframe-detail", detail]
    # Vzdy explicitne: bez `--datadir` si Freqtrade vezme `<userdir>/data/<burza>`, kde od
    # presunu dat lezia uz len stare kopie. Beh by potom ticho pocital z inych suborov,
    # nez ma zvysok Testera (a novy timeframe by tam vobec nenasiel).
    cmd += ["--datadir", str(engines.data_dir(inst, settings.get("exchange")))]
    if settings.get("ai"):
        model = (settings["ai"].get("model") or engines.AI_DEFAULTS["model"])
        cmd += ["--freqaimodel", model]
    return cmd


def effective_params(params: dict[str, Any], strategy: str = "ibs") -> dict[str, Any]:
    """Celý config behu: poslané hodnoty doplnené defaultmi stratégie, overené a v tvare
    `config.to_dict()` — presne to, s čím beh pobeží.

    Formulár posiela len polia, ktoré ukazuje (inertné Pine vstupy nie), CLI celý profil
    a stránka otvorená pred zmenou kódu nemusí nové polia poznať vôbec. Beh preto
    neukladá, čo prišlo, ale výsledok: o rok neskôr, keď sa posunie default alebo pribudne
    pole, sa z `run.json` dá beh zopakovať a uložiť ako úplný profil. Zrušené polia
    (`RETIRED_FIELDS`) config preskočí, neznáme odmietne (`ConfigError`).
    """
    cfg = get_spec(strategy).config_cls.from_dict({k: v for k, v in params.items() if not k.startswith("_")})
    return cfg.to_dict()


def write_profile(run_id: str, params: dict[str, Any], instrument: str, strategy: str = "ibs",
                  directory: Path | None = None) -> Path:
    """Dočasný profil pre `TRADEBOT_PROFILE`. Validácia configu tu spadne skôr než Freqtrade.

    `directory` inde než v `TMP_PROFILES` — prepočet grafu nesmie prepísať profil behu,
    ktorý práve beží pod tým istým id."""
    cfg = get_spec(strategy).config_cls.from_dict({k: v for k, v in params.items() if not k.startswith("_")})
    data = cfg.to_dict()
    data["_strategy"] = strategy
    data["_instrument"] = instrument
    data["_comment"] = [f"docasny profil behu {run_id} (webapp) - negeneruj rucne"]
    kam = Path(directory) if directory is not None else TMP_PROFILES
    kam.mkdir(parents=True, exist_ok=True)
    path = kam / f"{run_id}.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return path
