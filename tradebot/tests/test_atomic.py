"""`tradebot.core.atomic`: zápis, ktorý nenechá rozbitý súbor, zámok medzi procesmi a čítanie, ktoré
pokazený JSON nezahodí potichu (audit 9. 11. 2026, M-CORE-4, N-HUB-8, N-HUB-9)."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

import pytest

from tradebot.core import atomic, derived


def test_preruseny_zapis_necha_povodny_subor_a_ziadny_docasny(tmp_path: Path, monkeypatch):
    cesta = tmp_path / "state.json"
    atomic.write_json_atomic(cesta, {"a": 1})
    atomic.write_bytes_atomic(tmp_path / "vysledok.zip", b"PK-stary")

    def pad(*a, **k):
        raise OSError("plný disk")

    monkeypatch.setattr(atomic.os, "replace", pad)
    with pytest.raises(OSError):
        atomic.write_json_atomic(cesta, {"a": 2})
    with pytest.raises(OSError):
        atomic.write_bytes_atomic(tmp_path / "vysledok.zip", b"PK-novy")
    with pytest.raises(RuntimeError):
        with atomic.atomic_path(tmp_path / "data.feather") as tmp:
            tmp.write_bytes(b"pol suboru")
            raise RuntimeError("pád uprostred zápisu")
    assert json.loads(cesta.read_text(encoding="utf-8")) == {"a": 1}
    assert (tmp_path / "vysledok.zip").read_bytes() == b"PK-stary"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json", "vysledok.zip"]


def test_zamknuty_ciel_sa_skusi_znova(tmp_path: Path, monkeypatch):
    """Windows: cieľ má na okamih otvorený čitateľ — `os.replace` vráti PermissionError a o chvíľu prejde."""
    cesta = tmp_path / "control.json"
    povodny, pokusy = os.replace, []

    def raz_zamknute(src, dst):
        pokusy.append(1)
        if len(pokusy) < 3:
            raise PermissionError("súbor používa iný proces")
        povodny(src, dst)

    monkeypatch.setattr(atomic.os, "replace", raz_zamknute)
    monkeypatch.setattr(atomic, "_REPLACE_WAIT", 0.0)
    atomic.write_text_atomic(cesta, "ok")
    assert cesta.read_text(encoding="utf-8") == "ok" and len(pokusy) == 3


def test_pokazeny_json_sa_odlozi_a_zaloguje(tmp_path: Path, caplog):
    cesta = tmp_path / "state.json"
    assert atomic.read_json(cesta, {"prazdny": True}) == {"prazdny": True}      # chýba — bez hluku
    assert caplog.records == []
    cesta.write_text('{"jobs": {"a": 1', encoding="utf-8")                       # zápis prerušený v polovici
    with caplog.at_level(logging.ERROR):
        assert atomic.read_json(cesta, None, what="stav hubu") is None
    assert "stav hubu" in caplog.text and "corrupt" in caplog.text
    odlozene = [p for p in tmp_path.iterdir() if ".corrupt-" in p.name]
    assert len(odlozene) == 1 and odlozene[0].read_text(encoding="utf-8") == '{"jobs": {"a": 1'
    assert not cesta.exists()                                                    # ďalší zápis začne načisto


def test_zamok_pusti_len_jedneho_a_stary_prevezme(tmp_path: Path):
    cesta = tmp_path / "manifest.json"
    vnutri, najviac = [0], [0]

    def praca():
        with atomic.file_lock(cesta):
            vnutri[0] += 1
            najviac[0] = max(najviac[0], vnutri[0])
            time.sleep(0.01)
            vnutri[0] -= 1

    vlakna = [threading.Thread(target=praca) for _ in range(8)]
    for v in vlakna:
        v.start()
    for v in vlakna:
        v.join()
    assert najviac[0] == 1 and not (tmp_path / "manifest.json.lock").exists()

    # zámok po spadnutom procese: starší než `stale` sa prevezme, nečaká sa naň donekonečna
    zamok = tmp_path / "manifest.json.lock"
    zamok.write_text("", encoding="utf-8")
    stary = time.time() - 600
    os.utime(zamok, (stary, stary))
    with atomic.file_lock(cesta, timeout=1.0, stale=60.0):
        assert zamok.exists()
    assert not zamok.exists()


def test_manifest_odvodenych_tf_nestrati_zapis_pri_subehu(tmp_path: Path):
    """M-CORE-4: webapp a podproces Freqtrade píšu ten istý zoznam; stratený zápis by dopočítaný súbor
    pustil do archívu a gitu."""
    manifest = tmp_path / "derived.json"
    subory = [tmp_path / f"NAS100_USD-{i}m.feather" for i in range(2, 14)]
    for s in subory:
        s.write_bytes(b"x")
    vlakna = [threading.Thread(target=derived.remember, args=([s], manifest)) for s in subory]
    for v in vlakna:
        v.start()
    for v in vlakna:
        v.join()
    assert sorted(p.name for p in derived.derived(manifest)) == sorted(s.name for s in subory)
    derived.forget(subory, manifest)
    assert not manifest.exists()
