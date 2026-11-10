"""Most do C# jadra a jeho preklad pri poruche (audit M-LIVE-9, N-CS-9) — bez kompilátora aj bez .NET.

Hostiteľa tu hrá malý Python skript, takže testy bežia všade: ide o to, čo most povie, keď hostiteľ
skončí, a čo ostane na disku, keď sa výstup prekladu nedá vymeniť.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.adapters.csharp import bridge, build

# --------------------------------------------------------------------------- #
# stdio most: hostiteľ, ktorý skončí
# --------------------------------------------------------------------------- #


def _fake_host(monkeypatch, code: str) -> None:
    monkeypatch.setattr(bridge, "_host_command", lambda: [sys.executable, "-c", code])


def test_host_ktory_spadne_pri_starte_da_bridge_error_so_stderr(monkeypatch):
    """Hostiteľ skončí skôr, než prečíta príkaz: `BrokenPipeError` ani prázdna odpoveď nesmú vyjsť von holé."""
    _fake_host(monkeypatch, "import sys; sys.stderr.write('Unhandled Exception: bum v hostiteli\\n'); sys.exit(3)")
    with pytest.raises(bridge.BridgeError) as err:
        bridge.StdioTransport("ibsnet", "{}", "{}", 3)
    text = str(err.value)
    assert "bum v hostiteli" in text and "3" in text


def test_host_ktory_spadne_uprostred_behu(monkeypatch):
    """Prvý príkaz prejde, potom hostiteľ skončí: ďalšie volanie je `BridgeError` s jeho stderr."""
    code = ("import sys\n"
            "sys.stdin.readline(); print('{\"key\": \"x\"}', flush=True)\n"
            "sys.stdin.readline(); sys.stderr.write('OutOfMemoryException\\n'); sys.exit(7)\n")
    _fake_host(monkeypatch, code)
    t = bridge.StdioTransport("ibsnet", "{}", "{}", 3)
    assert t.info == {"key": "x"}
    with pytest.raises(bridge.BridgeError, match="OutOfMemoryException"):
        t.stats()
    with pytest.raises(bridge.BridgeError, match="OutOfMemoryException"):      # už nebeží — stále s dôvodom
        t.stats()
    t.close()


def test_zapis_do_zavretej_rury_je_bridge_error(monkeypatch):
    """Zápis do rúry skončeného hostiteľa (`BrokenPipeError` / `OSError`) sa zabalí do `BridgeError`."""
    code = "import sys\nsys.stdin.readline(); print('{}', flush=True)\nsys.stdin.readline()\n"
    _fake_host(monkeypatch, code)
    t = bridge.StdioTransport("ibsnet", "{}", "{}", 3)

    class Zavreta:
        def write(self, _s):
            raise BrokenPipeError(32, "Broken pipe")

        def flush(self):
            pass

    stdin, t._proc.stdin = t._proc.stdin, Zavreta()
    try:
        with pytest.raises(bridge.BridgeError, match="neprijal príkaz 'stats'"):
            t.stats()
    finally:
        stdin.close()
        t._proc.kill()
        t._proc.wait(timeout=5)


def test_inproc_po_close_uz_nepocita():
    """N-CS-9: `InprocTransport.close()` engine pustí; volanie po ňom je chyba, nie beh na starom stave."""
    t = bridge.InprocTransport.__new__(bridge.InprocTransport)
    t._host = object()
    t.close()
    with pytest.raises(bridge.BridgeError, match="zatvorený"):
        t.stats()


def test_zmenena_dll_po_nacitani_sa_ohlasi(monkeypatch, tmp_path, caplog):
    """N-CS-9: proces s načítanou assembly upozorní (raz), že na disku je už iný preklad."""
    dll = tmp_path / "TradeBot.dll"
    dll.write_bytes(b"stara")
    monkeypatch.setattr(bridge, "CSHARP_DLL", dll)
    monkeypatch.setattr(bridge, "_clr_host_cls", object())
    monkeypatch.setattr(bridge, "_clr_loaded_stamp", bridge._dll_stamp())
    monkeypatch.setattr(bridge, "_clr_warned_stamp", None)
    assert bridge.loaded_dll_is_stale() is False
    dll.write_bytes(b"novy preklad")
    with caplog.at_level(logging.WARNING):
        assert bridge.loaded_dll_is_stale() is True
        assert bridge.loaded_dll_is_stale() is True
    assert caplog.text.count("STARÁ verzia") == 1


# --------------------------------------------------------------------------- #
# preklad: výmena výstupu a timeout kompilátora
# --------------------------------------------------------------------------- #


@pytest.fixture
def bin_dir(tmp_path, monkeypatch):
    """Adresár výstupu so „starým" prekladom a falošným kompilátorom, ktorý píše „nový"."""
    out = tmp_path / "bin"
    out.mkdir()
    dll, exe = out / "TradeBot.dll", out / "TradeBot.Host.exe"
    dll.write_text("stara dll")
    exe.write_text("stary host")
    (out / ".built-by").write_text("stary-preklad")
    monkeypatch.setattr(build, "CSHARP_BIN", out)
    monkeypatch.setattr(build, "CSHARP_DLL", dll)
    monkeypatch.setattr(build, "CSHARP_HOST", exe)
    monkeypatch.setattr(build, "find_compiler", lambda: ["csc-test"])
    monkeypatch.setattr(build, "_compile", lambda _c, target, o, _f, _r: Path(o).write_text(f"novy {target}"))
    return out


def test_preklad_vymeni_oba_subory_a_zapise_znacku(bin_dir):
    build.build()
    assert (bin_dir / "TradeBot.dll").read_text() == "novy library"
    assert (bin_dir / "TradeBot.Host.exe").read_text() == "novy exe"
    assert (bin_dir / ".built-by").read_text() == build._stamp()
    assert not list(bin_dir.glob(".build-*"))


def test_zamknuty_host_necha_cely_stary_preklad_bez_znacky(bin_dir, monkeypatch, caplog):
    """M-LIVE-9: `Host.exe` drží bežiaci beh → nová DLL sa vráti späť, značka nového prekladu sa nezapíše."""
    replace = os.replace

    def zamknute(src, dst):
        if Path(dst).name == "TradeBot.Host.exe":
            raise PermissionError(13, "súbor používa iný proces", str(dst))
        return replace(src, dst)

    monkeypatch.setattr(build.os, "replace", zamknute)
    with caplog.at_level(logging.WARNING):
        build.build()
    assert (bin_dir / "TradeBot.dll").read_text() == "stara dll"
    assert (bin_dir / "TradeBot.Host.exe").read_text() == "stary host"
    assert (bin_dir / ".built-by").read_text() == "stary-preklad"
    assert "TradeBot.Host.exe" in caplog.text and not list(bin_dir.glob(".build-*"))


def test_zamknuty_vystup_bez_stareho_prekladu_je_chyba(bin_dir, monkeypatch):
    (bin_dir / "TradeBot.Host.exe").unlink()

    def zamknute(_src, dst):
        raise PermissionError(13, "prístup odmietnutý", str(dst))

    monkeypatch.setattr(build.os, "replace", zamknute)
    with pytest.raises(build.BuildError, match="nedá zapísať"):
        build.build()
    assert not (bin_dir / "TradeBot.Host.exe").exists()


def test_uviaznuty_kompilator_je_build_error(monkeypatch, tmp_path):
    def uviazol(cmd, **kw):
        assert kw.get("timeout") == build.COMPILE_TIMEOUT
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(build.subprocess, "run", uviazol)
    with pytest.raises(build.BuildError, match="neskončil"):
        build._compile(["csc-test"], "library", tmp_path / "x.dll", [], [])


# --------------------------------------------------------------------------- #
# C# jadro: drobnosti z auditu N-CS-7 (čas v hodine zmeny, EMA, TF grafu)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def core():
    try:
        bridge._load_clr()
    except (bridge.BridgeError, build.BuildError) as exc:
        pytest.skip(f"pythonnet/CLR nie je k dispozícii: {exc}")
    import TradeBot.Core as core

    return core


def test_miestny_cas_na_utc_ako_python_aj_v_hodine_zmeny(core):
    """`SessionClock.LocalToUtcMs` = Python `datetime(..., tzinfo=ZoneInfo)` (`fold=0`): neexistujúci čas
    na jar nehodí výnimku, dvojznačný na jeseň je prvý (letný) výskyt. `ConvertTimeToUtc` robil oboje inak."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from System import DateTime

    for zona in ("America/New_York", "Europe/London", "Europe/Prague"):
        tz = core.TimeZones.Get(zona)
        for y, mo, d in ((2026, 3, 8), (2026, 11, 1), (2026, 3, 29), (2026, 10, 25), (2026, 7, 15), (2026, 1, 15)):
            for h, mi in ((0, 30), (1, 0), (1, 30), (2, 0), (2, 30), (3, 0), (3, 30), (8, 30), (15, 58)):
                py = int(datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(zona)).timestamp() * 1000)
                assert int(core.SessionClock.LocalToUtcMs(tz, DateTime(y, mo, d, h, mi, 0))) == py, (zona, y, mo, d, h, mi)


def test_ema_s_nulovou_dlzkou_ma_alpha_z_orezanej(core):
    from tradebot.core.ma import EMA, RMA

    assert core.Ema(0).Alpha == EMA(0).alpha == 1.0 and EMA(-3).alpha == 1.0 and RMA(0).alpha == 1.0
    for n in (1, 2, 9, 14, 200):
        assert core.Ema(n).Alpha == EMA(n).alpha == 2.0 / (n + 1)
        assert RMA(n).alpha == 1.0 / n


def test_tf_grafu_pod_minutu_je_chyba(core):
    with pytest.raises(bridge.BridgeError, match="TF grafu"):
        bridge.InprocTransport("noanet", "{}", '{"symbol": "MNQ/USD", "tick_size": 0.25, "point_value": 2.0}', 0)
