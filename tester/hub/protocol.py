"""Spoločný jazyk hubu, agentov a zadávateľov: druhy výpočtov, kapacita, odhad času.

Čisté funkcie bez siete a bez disku — to, na čom sa hub a agent musia zhodnúť, aby
„voľný agent" a „ešte 20 minút" znamenali na oboch stranách to isté.

Kapacita: agent má `slots` (koľko behov naraz) a každý výpočet žiada `cores`: číslo,
alebo `"all"` (celý stroj). Hyperopt žiada všetko — Freqtrade epochy rozhodí cez joblib
na všetky jadrá a beh vedľa neho by mal cudzie časy. Backtest žiada jedno jadro, takže
na 8-jadrovom agentovi ich môže bežať osem; agent s AI vrstvou (FreqAI trénuje na
všetkých jadrách) žiada tiež všetko.

Čas: odhad **pred** štartom ide z histórie behov toho agenta (sekundy na deň okna pri
backteste, sekundy na epochu pri hyperopte); **počas** behu sa u hyperoptu číta z logu
počet hotových epoch a u backtestu sa odpočítava od odhadu. Hub potom vie, kedy sa
ktorý agent uvoľní — a to rozhoduje, či sa výpočet do fronty dá alebo nie.
"""

from __future__ import annotations

import re
import statistics
from datetime import datetime
from typing import Any, Iterable

__all__ = [
    "KIND_BACKTEST", "KIND_HYPEROPT", "KINDS", "ALL", "LIVE_STATES", "FINAL_STATES",
    "REFERENCE_VERIFY_RUNS", "kind_of", "cores_for", "window_days", "seconds_per_day",
    "seconds_per_epoch", "estimate_seconds", "progress_from_log", "progress_from_results",
    "remaining_seconds",
    "agent_slots", "busy", "fits", "eta_free",
]

KIND_BACKTEST = "backtest"
KIND_HYPEROPT = "hyperopt"
KINDS = (KIND_BACKTEST, KIND_HYPEROPT)

#: Požiadavka „celý stroj" — hyperopt, AI vrstva.
ALL = "all"

LIVE_STATES = ("queued", "assigned", "running", "cancelling")
FINAL_STATES = ("done", "failed", "cancelled")

#: Hyperopt po dobehnutí pustí víťaza na piatich referenčných oknách (`tester.hyperopt`).
REFERENCE_VERIFY_RUNS = 5

#: Štart Freqtradu (import, načítanie sviečok) — platí sa raz za beh bez ohľadu na okno,
#: takže mesiac nestojí dvanástinu roka.
STARTUP_SECONDS = 10.0
#: Keď história nič nepovie: rok backtestu s 1m detailom je ~30 s (`app.SECONDS_PER_YEAR`),
#: z toho štart je STARTUP_SECONDS.
FALLBACK_SECONDS_PER_DAY = 20.0 / 365.0
#: Bez 1m detailu je beh rádovo rýchlejší.
FALLBACK_SECONDS_PER_DAY_NO_DETAIL = 4.0 / 365.0
#: AI vrstva trénuje walk-forward — rádovo pomalšie než holý backtest.
AI_SLOWDOWN = 20.0
#: Keď o bežiacom výpočte nevieme nič (agent ešte nič nenahlásil).
DEFAULT_ETA_SECONDS = 600.0
#: Koľko posledných podobných behov sa berie do mediánu.
HISTORY_WINDOW = 20


# --------------------------------------------------------------------------- #
# druh a nároky výpočtu
# --------------------------------------------------------------------------- #


def kind_of(settings: dict[str, Any]) -> str:
    """Hyperopt sa pozná podľa `settings.hyperopt.knobs`, všetko ostatné je backtest."""
    return KIND_HYPEROPT if ((settings.get("hyperopt") or {}).get("knobs")) else KIND_BACKTEST


def cores_for(settings: dict[str, Any], kind: str | None = None) -> int | str:
    """Koľko jadier výpočet žiada: hyperopt všetky (alebo `jobs`), AI všetky, backtest jedno."""
    kind = kind or kind_of(settings)
    if kind == KIND_HYPEROPT:
        jobs = (settings.get("hyperopt") or {}).get("jobs")
        return int(jobs) if jobs else ALL
    if (settings.get("ai") or {}).get("enabled"):
        return ALL
    return 1


def window_days(timerange: str | None) -> float:
    """`20250904-20260904` → 365. Neplatný tvar → 0."""
    try:
        a, b = (datetime.strptime(x, "%Y%m%d") for x in str(timerange or "").split("-"))
    except ValueError:
        return 0.0
    return float(max((b - a).days, 0))


# --------------------------------------------------------------------------- #
# odhad času
# --------------------------------------------------------------------------- #


def _has_detail(settings: dict[str, Any]) -> bool:
    return bool(settings.get("timeframe_detail"))


def _has_ai(settings: dict[str, Any]) -> bool:
    return bool((settings.get("ai") or {}).get("enabled"))


def _similar_backtests(history: Iterable[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    """Hotové backtesty s rovnakým enginom, 1m detailom a AI vrstvou — tie majú
    porovnateľnú cenu za deň okna."""
    out = []
    for rec in history:
        s = rec.get("settings") or {}
        if rec.get("status") != "done" or kind_of(s) == KIND_HYPEROPT:
            continue
        if (s.get("engine") or "freqtrade") != (settings.get("engine") or "freqtrade"):
            continue
        if _has_detail(s) != _has_detail(settings) or _has_ai(s) != _has_ai(settings):
            continue
        dur = (rec.get("result") or {}).get("duration_s")
        days = window_days(s.get("timerange"))
        if dur and days > 0:
            out.append(rec)
    return out


def seconds_per_day(history: Iterable[dict[str, Any]], settings: dict[str, Any]) -> float:
    """Medián `(duration_s − štart) / dní okna` z posledných podobných behov, inak konštanta."""
    podobne = sorted(_similar_backtests(history, settings), key=lambda r: r.get("id", ""))[-HISTORY_WINDOW:]
    if podobne:
        return float(statistics.median(
            max(float(r["result"]["duration_s"]) - STARTUP_SECONDS, 1.0)
            / window_days(r["settings"].get("timerange"))
            for r in podobne))
    zaklad = FALLBACK_SECONDS_PER_DAY if _has_detail(settings) else FALLBACK_SECONDS_PER_DAY_NO_DETAIL
    return zaklad * (AI_SLOWDOWN if _has_ai(settings) else 1.0)


def seconds_per_epoch(history: Iterable[dict[str, Any]], settings: dict[str, Any]) -> float | None:
    """Medián `duration_s / epoch` z hotových hyperoptov s rovnakým 1m detailom; `None` bez histórie."""
    hodnoty = []
    for rec in sorted(history, key=lambda r: r.get("id", "")):
        s = rec.get("settings") or {}
        z = s.get("hyperopt") or {}
        if rec.get("status") != "done" or not z.get("knobs") or _has_detail(s) != _has_detail(settings):
            continue
        dur = (rec.get("result") or {}).get("duration_s")
        if dur and z.get("epochs_done"):
            hodnoty.append(float(dur) / float(z["epochs_done"]))
    hodnoty = hodnoty[-HISTORY_WINDOW:]
    return float(statistics.median(hodnoty)) if hodnoty else None


def estimate_seconds(settings: dict[str, Any], history: Iterable[dict[str, Any]],
                     cores: int = 1) -> float:
    """Koľko výpočet asi potrvá **na tomto stroji** (história je jeho vlastná).

    Hyperopt = epochy × čas epochy + overovacie behy víťaza. Bez histórie hyperoptov je
    epocha celý backtest ladeného okna rozdelený medzi jadrá.
    """
    history = list(history)
    days = window_days(settings.get("timerange"))
    per_day = seconds_per_day(history, settings)
    okno = max(days, 1.0) * per_day
    if kind_of(settings) == KIND_BACKTEST:
        return STARTUP_SECONDS + okno
    z = settings.get("hyperopt") or {}
    epochs = int(z.get("epochs") or 200)
    per_epoch = seconds_per_epoch(history, settings)
    if per_epoch is None:
        # epocha beží v tom istom procese (bez štartu), rozdelená medzi jadrá
        per_epoch = okno / max(1, int(z.get("jobs") or cores or 1))
    overenie = (REFERENCE_VERIFY_RUNS * (STARTUP_SECONDS + 365.0 * per_day)
                if z.get("verify", True) else 0.0)
    return STARTUP_SECONDS + epochs * per_epoch + overenie


#: `| 12/200 |` v tabuľke epoch Freqtradu — číslo za lomkou musí sedieť s počtom epoch,
#: inak je to dátum, pomer alebo čokoľvek iné.
_EPOCH_RE = re.compile(r"(?<![\d.])(\d+)/(\d+)(?![\d.])")


def progress_from_log(lines: Iterable[str], total: int | None) -> float | None:
    """Podiel hotových epoch podľa posledného `n/total` v logu; `None`, keď tam nie je."""
    if not total:
        return None
    for line in reversed(list(lines)):
        for m in _EPOCH_RE.finditer(line):
            if int(m.group(2)) == int(total):
                return min(1.0, int(m.group(1)) / float(total))
    return None


def progress_from_results(path: Any, total: int | None) -> float | None:
    """Podiel hotových epoch podľa `.fthypt` Freqtradu — jeden JSON riadok na epochu.

    Bez terminálu Freqtrade vypíše priebeh až na konci, ale výsledky epoch zapisuje
    priebežne (`_save_result`), takže súbor je jediný spoľahlivý ukazovateľ postupu.
    """
    if not total or path is None:
        return None
    try:
        with open(path, "rb") as fh:
            riadky = sum(1 for line in fh if line.strip())
    except OSError:
        return None
    return min(1.0, riadky / float(total))


def remaining_seconds(estimate: float, elapsed: float, progress: float | None = None) -> float:
    """Koľko asi ostáva: z postupu, keď je známy a nie je len rozbeh; inak odhad − uplynulé.

    Keď beh trvá dlhšie než odhad, nevráti nulu — ostane malý zvyšok, aby hub vedel, že
    stále beží, a zadávateľ nedostal „hneď", ktoré neplatí.
    """
    if progress is not None and progress >= 0.05:
        return max(0.0, elapsed * (1.0 - progress) / progress)
    zvysok = estimate - elapsed
    if zvysok > 0:
        return zvysok
    return max(30.0, 0.1 * max(estimate, 1.0))


# --------------------------------------------------------------------------- #
# kapacita agenta
# --------------------------------------------------------------------------- #


def agent_slots(agent: dict[str, Any]) -> int:
    return max(1, int(agent.get("slots") or agent.get("cores") or 1))


def _job_cores(cores: Any, slots: int) -> int:
    return slots if cores == ALL else max(1, int(cores or 1))


def busy(agent: dict[str, Any], hub_jobs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Čo agenta zamestnáva: výpočty od hubu + jeho lokálna fronta (`agent.load`).

    Lokálnu záťaž hlási agent **bez** výpočtov hubu, inak by sa počítali dvakrát.
    Vráti `used` (obsadené sloty), `exclusive` (beží niečo, čo chce celý stroj) a `etas`
    — dvojice (sekundy do konca, uvoľnené sloty), z ktorých sa počíta `eta_free`.
    """
    slots = agent_slots(agent)
    used = 0
    exclusive = False
    etas: list[tuple[float, int]] = []
    for job in hub_jobs:
        c = _job_cores(job.get("cores"), slots)
        if job.get("cores") == ALL:
            exclusive = True
        used += c
        eta = job.get("eta_seconds")
        if eta is None:
            eta = job.get("estimate_seconds") or DEFAULT_ETA_SECONDS
        etas.append((float(eta), c))
    local = agent.get("load") or {}
    n_local = int(local.get("running") or 0) + int(local.get("queued") or 0)
    if local.get("exclusive"):
        exclusive = True
        used += slots
        etas.append((float(local.get("eta_seconds") or DEFAULT_ETA_SECONDS), slots))
    elif n_local:
        used += n_local
        eta = float(local.get("eta_seconds") or DEFAULT_ETA_SECONDS)
        etas.extend((eta, 1) for _ in range(n_local))
    return {"slots": slots, "used": min(used, slots), "exclusive": exclusive, "etas": etas}


def _available(agent: dict[str, Any]) -> bool:
    return bool(agent.get("accept")) and bool(agent.get("online"))


def fits(agent: dict[str, Any], demand: int | str, hub_jobs: Iterable[dict[str, Any]]) -> bool:
    """Môže agent výpočet zobrať **teraz**? `all` chce prázdny stroj, číslo voľné sloty."""
    if not _available(agent):
        return False
    b = busy(agent, hub_jobs)
    if demand == ALL:
        return b["used"] == 0
    return not b["exclusive"] and b["slots"] - b["used"] >= int(demand)


def eta_free(agent: dict[str, Any], demand: int | str, hub_jobs: Iterable[dict[str, Any]]) -> float | None:
    """Za koľko sekúnd by agent výpočet zobrať mohol; 0 = hneď, `None` = nikdy (neprijíma, offline)."""
    if not _available(agent):
        return None
    hub_jobs = list(hub_jobs)
    if fits(agent, demand, hub_jobs):
        return 0.0
    b = busy(agent, hub_jobs)
    if not b["etas"]:
        return 0.0
    if demand == ALL:
        return max(eta for eta, _ in b["etas"])
    volne = 0 if b["exclusive"] else b["slots"] - b["used"]
    for eta, c in sorted(b["etas"]):
        volne += c
        if volne >= int(demand):
            return eta
    return max(eta for eta, _ in b["etas"])
