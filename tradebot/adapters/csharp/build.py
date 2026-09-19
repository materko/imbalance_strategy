"""Zostavenie C# jadra — `csharp/bin/TradeBot.dll` a `TradeBot.Host.exe`.

Zdrojáky sú zámerne C# 5 bez NuGet závislostí, takže na Windows stačí `csc.exe`, ktorý je
súčasťou .NET Frameworku (netreba .NET SDK ani Visual Studio); na macOS/Linuxe to isté
preloží Mono (`mcs`). Tá istá DLL ide do NinjaTradera aj pod most do Freqtrade.

    python -m tradebot.adapters.csharp.build          # zostav, ak sú zdrojáky novšie
    python -m tradebot.adapters.csharp.build --force

Most volá `ensure_built()` sám pred prvým použitím, takže ručne to treba len po chybe prekladu.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tradebot.core.paths import CSHARP_BIN, CSHARP_DIR, CSHARP_DLL, CSHARP_HOST

__all__ = ["BuildError", "find_compiler", "sources", "is_stale", "build", "ensure_built"]

_log = logging.getLogger(__name__)

#: Adresáre so zdrojákmi knižnice (jadro + stratégie) a hostiteľa pre stdio most.
LIBRARY_DIRS = ("TradeBot.Core", "TradeBot.Strategies")
HOST_DIR = "TradeBot.Host"


class BuildError(RuntimeError):
    """C# jadro sa nepodarilo preložiť (chýba kompilátor alebo chyba v zdrojáku)."""


def find_compiler() -> list[str]:
    """Príkaz kompilátora: `csc.exe` z .NET Frameworku (Windows) alebo Mono `mcs`/`csc`."""
    override = os.environ.get("TRADEBOT_CSC")
    if override:
        return [override]
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        for fw in ("Framework64", "Framework"):
            csc = windir / "Microsoft.NET" / fw / "v4.0.30319" / "csc.exe"
            if csc.exists():
                return [str(csc)]
    for name in ("mcs", "csc"):
        found = shutil.which(name)
        if found:
            return [found]
    raise BuildError(
        "nenašiel sa C# kompilátor: na Windows je `csc.exe` súčasťou .NET Frameworku 4.x, "
        "na macOS/Linuxe nainštaluj Mono (`brew install mono`); cestu sa dá vnútiť cez TRADEBOT_CSC"
    )


def sources(*dirs: str) -> list[Path]:
    out: list[Path] = []
    for d in dirs:
        out.extend(sorted((CSHARP_DIR / d).rglob("*.cs")))
    return out


def _stamp() -> str:
    """Čím je preklad urobený. DLL z Mono `mcs` sa viaže na metódy, ktoré .NET Framework nemá
    (a naopak to nikto nesľubuje), takže preklad z iného systému v zdieľanom adresári
    (WSL a Windows nad tým istým klonom, synchronizovaný priečinok) sa berie ako zastaraný."""
    return f"{sys.platform}:{Path(find_compiler()[0]).name}"


def is_stale() -> bool:
    """Chýba výstup, je z iného kompilátora, alebo je niektorý zdroják novší než on."""
    targets = (CSHARP_DLL, CSHARP_HOST)
    if not all(t.exists() for t in targets):
        return True
    marker = CSHARP_BIN / ".built-by"
    if not marker.exists() or marker.read_text(encoding="utf-8").strip() != _stamp():
        return True
    built = min(t.stat().st_mtime for t in targets)
    return any(s.stat().st_mtime > built for s in sources(*LIBRARY_DIRS, HOST_DIR))


def _compile(compiler: list[str], target: str, out: Path, files: list[Path], refs: list[Path]) -> None:
    # Zoznam súborov ide cez response súbor — príkazový riadok má na Windows limit dĺžky.
    # `-codepage:65001`: zdrojáky sú UTF-8 bez BOM a obsahujú znaky mimo ASCII (šípky v štítkoch).
    lines = ["-nologo", "-optimize+", "-debug-", "-codepage:65001", f"-target:{target}", f'-out:"{out}"']
    lines += [f'-reference:"{r}"' for r in refs]
    lines += [f'"{f}"' for f in files]
    with tempfile.NamedTemporaryFile("w", suffix=".rsp", delete=False, encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        rsp = fh.name
    try:
        done = subprocess.run([*compiler, f"@{rsp}"], capture_output=True, text=True)
    finally:
        os.unlink(rsp)
    if done.returncode != 0:
        raise BuildError(f"preklad {out.name} zlyhal:\n{done.stdout}\n{done.stderr}".strip())


def build() -> None:
    """Preloží knižnicu aj hostiteľa do dočasných súborov a až potom ich vymení (atomicky)."""
    compiler = find_compiler()
    CSHARP_BIN.mkdir(parents=True, exist_ok=True)
    # dočasný adresár VEDĽA cieľa: `os.replace` je atomický len v rámci jedného zväzku a systémový
    # /tmp býva inde (Linux/macOS: "Invalid cross-device link")
    tmp = Path(tempfile.mkdtemp(prefix=".build-", dir=CSHARP_BIN))
    try:
        dll, exe = tmp / CSHARP_DLL.name, tmp / CSHARP_HOST.name
        _compile(compiler, "library", dll, sources(*LIBRARY_DIRS), [])
        _compile(compiler, "exe", exe, sources(HOST_DIR), [dll])
        for built, final in ((dll, CSHARP_DLL), (exe, CSHARP_HOST)):
            try:
                os.replace(built, final)
            except PermissionError:
                # beží iný beh cez stdio hostiteľa a súbor drží; ostáva stará verzia
                if not final.exists():
                    raise
                _log.warning("C# jadro: %s je práve používaný, ostáva predošlý preklad", final.name)
        (CSHARP_BIN / ".built-by").write_text(_stamp(), encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def ensure_built(force: bool = False) -> Path:
    """Vráti cestu k `TradeBot.dll`; ak treba, najprv ju zostaví."""
    if force or is_stale():
        _log.info("C# jadro: prekladám %s", CSHARP_DLL)
        build()
    return CSHARP_DLL


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        ensure_built(force="--force" in sys.argv)
    except BuildError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: {CSHARP_DLL}\nOK: {CSHARP_HOST}")
