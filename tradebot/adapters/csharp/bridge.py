"""Transport medzi Pythonom a C# jadrom — dva spôsoby, jeden protokol.

`EngineHost` (csharp/TradeBot.Core/EngineHost.cs) berie jednoduché typy a vracia jeden JSON
na bar. Volá sa buď **v procese** cez pythonnet (rýchle, ~µs na bar), alebo ako **samostatný
proces** `TradeBot.Host.exe` cez stdin/stdout (bez závislosti; na macOS/Linuxe pod Mono).
Výber: `TRADEBOT_CSHARP_BRIDGE=inproc|stdio`, inak pythonnet, keď je nainštalovaný.

Čísla idú dnu ako natívne `double` (pythonnet) alebo ako bitový vzor (stdio) a von ako `G17`,
takže sa cestou nezmení ani posledný bit — porovnanie s Python enginom je na rovnosť.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import struct
import subprocess
import sys
import threading
from typing import Any, Sequence

from tradebot.core.clr import tame_shutdown
from tradebot.core.paths import CSHARP_DLL, CSHARP_HOST

from .build import ensure_built

__all__ = ["BridgeError", "Transport", "InprocTransport", "StdioTransport", "open_transport", "bridge_mode"]

_log = logging.getLogger(__name__)


class BridgeError(RuntimeError):
    """C# engine sa nepodarilo spustiť alebo vrátil chybu."""


def bridge_mode() -> str:
    """`inproc` (pythonnet) alebo `stdio` (TradeBot.Host.exe)."""
    mode = os.environ.get("TRADEBOT_CSHARP_BRIDGE", "").strip().lower()
    if mode in ("inproc", "stdio"):
        return mode
    if mode:
        raise BridgeError(f"TRADEBOT_CSHARP_BRIDGE={mode!r}: povolené sú 'inproc' a 'stdio'")
    try:
        import pythonnet  # noqa: F401
    except ImportError:
        return "stdio"
    if sys.platform != "win32" and shutil.which("mono") is None:
        return "stdio"  # pythonnet bez Mono nemá čo načítať; stdio povie, čo nainštalovať
    return "inproc"


class Transport:
    """Jeden C# engine. Metódy vracajú už rozparsovaný JSON."""

    info: dict[str, Any]

    def on_bar(self, t: int, ohlcv: Sequence[float], htf: tuple[list[int], list[float], float] | None,
               position: float, daily_limit: bool, open_ids: str) -> dict[str, Any]:
        raise NotImplementedError

    def final_drawings(self, t: int, ohlcv: Sequence[float]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def seed(self, name: str, times: list[int], values: list[float], has_partial: bool) -> int:
        raise NotImplementedError

    def stats(self) -> dict[str, float]:
        raise NotImplementedError

    def close(self) -> None:
        pass


# --------------------------------------------------------------------------- #
# v procese — pythonnet
# --------------------------------------------------------------------------- #

_clr_lock = threading.Lock()
_clr_host_cls = None


def _load_clr():
    """Načíta `TradeBot.dll` do procesu raz. Z bajtov, nie zo súboru — .NET Framework by si
    inak DLL zamkol a ďalší preklad (iný beh, vývoj) by ju nemal ako prepísať."""
    global _clr_host_cls
    with _clr_lock:
        if _clr_host_cls is not None:
            return _clr_host_cls
        dll = ensure_built()
        try:
            import pythonnet

            if pythonnet.get_runtime_info() is None:
                runtime = os.environ.get("TRADEBOT_CSHARP_RUNTIME") or ("netfx" if sys.platform == "win32" else "mono")
                pythonnet.load(runtime)
            import clr  # noqa: F401

            tame_shutdown()  # inak koniec procesu trvá minúty — viď tradebot/core/clr.py
            from System.IO import File
            from System.Reflection import Assembly

            Assembly.Load(File.ReadAllBytes(str(dll)))
            from TradeBot.Core import EngineHost
        except Exception as exc:  # pythonnet hlási všeličo: chýbajúci runtime, zlá architektúra...
            raise BridgeError(f"pythonnet nevie načítať {dll}: {exc}") from exc
        _clr_host_cls = EngineHost
        return _clr_host_cls


class InprocTransport(Transport):
    def __init__(self, key: str, config_json: str, instrument_json: str, chart_tf_minutes: int) -> None:
        host_cls = _load_clr()
        from System import Array, Double, Int64

        self._longs = Array[Int64]
        self._doubles = Array[Double]
        try:
            self._host = host_cls(key, config_json, instrument_json, int(chart_tf_minutes))
        except Exception as exc:
            raise BridgeError(f"C# engine {key!r} sa nepodarilo vytvoriť: {exc}") from exc
        self.info = json.loads(self._host.Info())

    def on_bar(self, t, ohlcv, htf, position, daily_limit, open_ids):
        o, h, lo, c, v = ohlcv
        if htf is None:
            ht = hv = None
            sma = 0.0
        else:
            ht, hv, sma = self._longs(htf[0]), self._doubles(htf[1]), htf[2]
        return json.loads(self._host.OnBar(int(t), o, h, lo, c, v, ht, hv, sma, position, daily_limit, open_ids))

    def final_drawings(self, t, ohlcv):
        o, h, lo, c, v = ohlcv
        return json.loads(self._host.FinalDrawings(int(t), o, h, lo, c, v))

    def seed(self, name, times, values, has_partial):
        return int(self._host.Seed(name, self._longs(times), self._doubles(values), has_partial))

    def stats(self):
        return json.loads(self._host.Stats())


# --------------------------------------------------------------------------- #
# samostatný proces — stdin/stdout
# --------------------------------------------------------------------------- #


def _bits(x: float) -> str:
    return struct.pack(">d", float(x)).hex()


def _host_command() -> list[str]:
    ensure_built()
    if sys.platform == "win32":
        return [str(CSHARP_HOST)]
    mono = shutil.which("mono")
    if mono is None:
        raise BridgeError("na spustenie C# enginu treba Mono (`brew install mono`) alebo pythonnet")
    return [mono, str(CSHARP_HOST)]


class StdioTransport(Transport):
    def __init__(self, key: str, config_json: str, instrument_json: str, chart_tf_minutes: int) -> None:
        self._proc = subprocess.Popen(_host_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      cwd=str(CSHARP_DLL.parent), encoding="utf-8", bufsize=1)
        self.info = self._call({"op": "create", "key": key, "config": config_json,
                                "instrument": instrument_json, "tf": int(chart_tf_minutes)})

    def _call(self, req: dict[str, Any]) -> Any:
        proc = self._proc
        if proc is None or proc.poll() is not None:
            raise BridgeError("C# hostiteľ nebeží")
        proc.stdin.write(json.dumps(req, separators=(",", ":")) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            raise BridgeError(f"C# hostiteľ skončil (kód {proc.poll()})")
        reply = json.loads(line)
        if isinstance(reply, dict) and "error" in reply:
            raise BridgeError(reply["error"])
        return reply

    def on_bar(self, t, ohlcv, htf, position, daily_limit, open_ids):
        req: dict[str, Any] = {"op": "bar", "t": int(t), "b": [_bits(x) for x in ohlcv],
                               "pos": _bits(position), "dl": bool(daily_limit), "ids": open_ids}
        if htf is not None:
            req["htf"] = {"t": htf[0], "v": [_bits(x) for x in htf[1]], "sma": _bits(htf[2])}
        return self._call(req)

    def final_drawings(self, t, ohlcv):
        return self._call({"op": "final", "t": int(t), "b": [_bits(x) for x in ohlcv]})

    def seed(self, name, times, values, has_partial):
        return int(self._call({"op": "seed", "name": name, "t": times, "v": [_bits(x) for x in values],
                               "partial": bool(has_partial)})["closed"])

    def stats(self):
        return self._call({"op": "stats"})

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.stdin.write('{"op":"quit"}\n')
            proc.stdin.flush()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def open_transport(key: str, config_json: str, instrument_json: str, chart_tf_minutes: int) -> Transport:
    cls = InprocTransport if bridge_mode() == "inproc" else StdioTransport
    return cls(key, config_json, instrument_json, chart_tf_minutes)
