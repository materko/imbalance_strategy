"""Simulátor porúch adaptéra NinjaTradera.

Parita bar po bare overuje signály, nie exekúciu: že adaptér po odmietnutom orderi, neskorej výplni
alebo výpadku spojenia nenechá pozíciu bez stopu, ju nenájde. Tu beží **skutočný** `LiveInstance`
(`tradebot/adapters/ninjatrader/TradeBotLiveInstance.cs`) nad náhradnými typmi NinjaTradera s falošným
brokerom (`NtStubs.cs`) a enginom, ktorý robí presne to, čo mu scenár predpíše (`FaultSim.cs`).
Čas je simulovaný (`LiveClock`), slučka inštancie sa volá po krokoch (`Step`) — beh je deterministický
a sekundy čakania nič nestoja.

    from tester.faultsim import run
    out = run({"engine": [{"bar": 1, "action": "entry", "id": "L1", "type": "limit", "entry": 100}],
               "steps": [{"do": "bar"}, {"do": "fill", "order": "L1"}]})
    out["trace"][-1]["naked"]     # pozícia u brokera bez stopu?

Scenár, kroky, pravidlá porúch a model brokera: docs/SIMULATOR_PORUCH.md. MetaTrader 5 tu nie je —
MQL5 mimo terminálu nebeží.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tradebot.adapters.csharp.build import BuildError, _compile, ensure_built, find_compiler
from tradebot.core.paths import CSHARP_DLL, FAULTSIM_DIR, FAULTSIM_EXE, REPO

#: Zdrojáky adaptéra, ktoré sa prekladajú proti náhradným typom: inštancia a jej feed pre graf. AddOn
#: (okno, deploy.json, WPF) a stratégia do grafu sem nepatria — AddOn nahrádza trieda v `NtStubs.cs`.
ADAPTER_SOURCES = (REPO / "tradebot" / "adapters" / "ninjatrader" / "TradeBotLiveInstance.cs",
                   REPO / "tradebot" / "adapters" / "ninjatrader" / "TradeBotLiveFeed.cs")


class SimError(RuntimeError):
    """Simulátor sa nepreložil alebo scenár nedobehol."""


def sim_sources() -> list[Path]:
    return [*sorted(FAULTSIM_DIR.glob("*.cs")), *ADAPTER_SOURCES]


def is_stale() -> bool:
    if not FAULTSIM_EXE.exists():
        return True
    built = FAULTSIM_EXE.stat().st_mtime
    return CSHARP_DLL.stat().st_mtime > built or any(s.stat().st_mtime > built for s in sim_sources())


def ensure_sim(force: bool = False) -> Path:
    """Preloží simulátor (a pred ním C# jadro), ak treba. `BuildError`, keď chýba kompilátor."""
    dll = ensure_built()
    if force or is_stale():
        tmp = Path(tempfile.mkdtemp(prefix=".faultsim-", dir=FAULTSIM_EXE.parent))
        try:
            exe = tmp / FAULTSIM_EXE.name
            _compile(find_compiler(), "exe", exe, sim_sources(), [dll])
            os.replace(exe, FAULTSIM_EXE)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return FAULTSIM_EXE


def _command(exe: Path) -> list[str]:
    if sys.platform == "win32":
        return [str(exe)]
    mono = shutil.which("mono")
    if mono is None:
        raise SimError("na spustenie simulátora treba Mono (`brew install mono`)")
    return [mono, str(exe)]


def run(scenario: dict[str, Any], *, timeout: float = 120.0) -> dict[str, Any]:
    """Prehrá scenár a vráti výpis: `trace` (stav po každom kroku), `requests` (čo adaptér chcel od brokera),
    `seen_position` (pozícia, akú adaptér hlásil enginu na každom živom bare), `log` a `error`."""
    exe = ensure_sim()
    with tempfile.TemporaryDirectory(prefix="faultsim-") as work:
        path = Path(work) / "scenario.json"
        path.write_text(json.dumps(scenario), encoding="utf-8")
        done = subprocess.run([*_command(exe), str(path), work], capture_output=True, timeout=timeout)
    text = done.stdout.decode("utf-8", errors="replace").strip()
    try:
        out = json.loads(text[text.index("{"):])
    except ValueError:
        raise SimError(f"simulátor nevrátil výpis (kód {done.returncode}):\n{text}\n"
                       f"{done.stderr.decode('utf-8', errors='replace')}") from None
    return out


def naked_steps(out: dict[str, Any]) -> list[str]:
    """Kroky, po ktorých ostala u brokera pozícia bez stopu aj bez trhového výstupu na ceste."""
    return [f"{i}: {s['step']}" for i, s in enumerate(out["trace"]) if s["naked"]]


__all__ = ["ADAPTER_SOURCES", "BuildError", "SimError", "ensure_sim", "is_stale", "naked_steps", "run", "sim_sources"]
