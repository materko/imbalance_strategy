"""Čítanie spoolu platforiem od kurzora — `SpoolReader` a kde spool hľadať (`default_roots`).

Spool je `<koreň>/<instance>/<yyyyMMdd-HHmmss>_<session>.jsonl` (docs/LIVE.md), append-only,
píše ho C# `LiveSpool` v NinjaTraderi alebo MT5. Reader si drží kurzor `{cesta: offset}` v
JSON súbore a **posúva ho až po `commit(batch)`** — shipper commituje po 200 od hubu, takže
výpadok hubu znamená len, že súbory rastú a po návrate sa dopošle všetko.

Neúplný posledný riadok (bez `\\n`) sa nečíta: zapisovač môže byť uprostred riadku. Rozbitý
riadok (nie JSON, nesedí schéma) sa preskočí s varovaním, ale jeho bajty sa spotrebujú —
jeden zlý riadok nesmie zastaviť celý spool.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schema import SchemaError, parse_line

__all__ = ["Batch", "SpoolReader", "default_roots", "ENV_ROOTS"]

log = logging.getLogger(__name__)

#: Ďalšie korene spoolu (testy, iná platforma), oddelené `os.pathsep`; pridajú sa k predvoleným.
ENV_ROOTS = "TRADEBOT_LIVE_SPOOL"


def default_roots() -> list[Path]:
    """Korene spoolu na tomto stroji: NinjaTrader (`Documents\\NinjaTrader 8\\TradeBot\\spool`),
    MT5 (`<Common>\\Files\\TradeBot\\spool`) a env `TRADEBOT_LIVE_SPOOL`. Len existujúce
    adresáre, bez duplicít; nikdy nevyhodí výnimku."""
    kandidati: list[Path] = []
    try:
        from tradebot.adapters.ninjatrader.__main__ import find_nt_user_dir

        nt = find_nt_user_dir()
        if nt is not None:
            kandidati.append(nt / "TradeBot" / "spool")
    except Exception:  # noqa: BLE001 - adaptér nemusí byť použiteľný (iný OS, chýbajúce moduly)
        log.debug("live spool: NinjaTrader koreň sa nedal zistiť", exc_info=True)
    try:
        from tradebot.adapters.mt5.__main__ import find_common_files

        spolocny = find_common_files()
        if spolocny is not None:
            kandidati.append(spolocny / "TradeBot" / "spool")
    except Exception:  # noqa: BLE001
        log.debug("live spool: MT5 koreň sa nedal zistiť", exc_info=True)
    for raw in (os.environ.get(ENV_ROOTS) or "").split(os.pathsep):
        if raw.strip():
            kandidati.append(Path(raw.strip()))
    out: list[Path] = []
    videne: set[str] = set()
    for p in kandidati:
        try:
            if not p.is_dir():
                continue
            kluc = os.path.normcase(str(p.resolve()))
        except OSError:
            continue
        if kluc in videne:
            continue
        videne.add(kluc)
        out.append(p)
    return out


@dataclass
class Batch:
    """Súvislý kus jedného súboru spoolu: udalosti od `start_offset` po `end_offset`
    (bajt za posledným spotrebovaným `\\n`)."""

    instance: str
    session: str
    path: Path
    events: list[dict[str, Any]] = field(default_factory=list)
    start_offset: int = 0
    end_offset: int = 0


def _session_from_name(path: Path) -> str:
    """`<stamp>_<session>.jsonl` → `session`; keď názov nesedí, celý kmeň."""
    kmen = path.stem
    return kmen.rsplit("_", 1)[1] if "_" in kmen else kmen


class SpoolReader:
    def __init__(self, roots: list[Path], cursor_path: Path) -> None:
        self.roots = [Path(r) for r in roots]
        self.cursor_path = Path(cursor_path)
        self.cursor: dict[str, int] = self._load_cursor()
        #: session podľa prvého `hello` v súbore (cache; keď hello chýba, z názvu súboru)
        self._sessions: dict[str, str] = {}

    # -- kurzor ------------------------------------------------------------- #

    def _load_cursor(self) -> dict[str, int]:
        try:
            data = json.loads(self.cursor_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(data, dict):
            return {}
        out: dict[str, int] = {}
        for k, v in data.items():
            try:
                out[str(k)] = max(0, int(v))
            except (TypeError, ValueError):
                continue
        return out

    def _save_cursor(self) -> None:
        self.cursor_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cursor_path.with_name(self.cursor_path.name + ".tmp")
        tmp.write_text(json.dumps(self.cursor, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.cursor_path)

    def commit(self, batch: Batch) -> None:
        """Dávku hub prijal — kurzor súboru sa posunie na jej koniec a uloží."""
        kluc = str(batch.path)
        if batch.end_offset > self.cursor.get(kluc, 0):
            self.cursor[kluc] = int(batch.end_offset)
            self._save_cursor()

    # -- súbory ------------------------------------------------------------- #

    def scan(self) -> list[tuple[str, Path]]:
        """`(instance, súbor)` pre všetky `<koreň>/<instance>/*.jsonl`, v poradí (instance, názov)
        — názov začína UTC časom štartu, takže staršie súbory idú prvé."""
        najdene: list[tuple[str, Path]] = []
        for root in self.roots:
            try:
                instancie = [p for p in root.iterdir() if p.is_dir()]
            except OSError:
                continue
            for inst in instancie:
                try:
                    subory = [p for p in inst.iterdir() if p.is_file() and p.suffix == ".jsonl"]
                except OSError:
                    continue
                najdene.extend((inst.name, p) for p in subory)
        return sorted(najdene, key=lambda t: (t[0], t[1].name))

    def _session_of(self, path: Path, events: list[dict[str, Any]]) -> str:
        kluc = str(path)
        if kluc in self._sessions:
            return self._sessions[kluc]
        session = ""
        for ev in events:
            if ev.get("k") == "hello" and ev.get("session"):
                session = str(ev["session"])
                break
        if not session and self.cursor.get(kluc, 0) > 0:
            # kurzor už je za začiatkom (reštart agenta) — hello je v súbore, prečítaj ho
            session = self._peek_hello(path)
        if not session:
            session = _session_from_name(path)
        self._sessions[kluc] = session
        return session

    @staticmethod
    def _peek_hello(path: Path) -> str:
        try:
            with open(path, "rb") as fh:
                prvy = fh.readline()
            ev = parse_line(prvy) if prvy.endswith(b"\n") else None
        except (OSError, SchemaError):
            return ""
        return str(ev.get("session") or "") if ev and ev.get("k") == "hello" else ""

    # -- čítanie ------------------------------------------------------------ #

    def read(self, max_events: int = 500) -> list[Batch]:
        """Nové udalosti od kurzora, najviac `max_events` naprieč súbormi (dávka smie skončiť
        uprostred súboru). Nič neposúva — na to je `commit`."""
        out: list[Batch] = []
        zvysok = max(1, int(max_events))
        for instance, path in self.scan():
            if zvysok <= 0:
                break
            kluc = str(path)
            start = self.cursor.get(kluc, 0)
            try:
                velkost = path.stat().st_size
            except OSError:
                continue
            if velkost <= start:
                continue
            try:
                with open(path, "rb") as fh:
                    fh.seek(start)
                    data = fh.read(velkost - start)
            except OSError as exc:
                log.warning("live spool: %s sa nedá čítať: %s", path, exc)
                continue
            events: list[dict[str, Any]] = []
            offset = start
            for riadok in data.split(b"\n"):
                if offset + len(riadok) >= start + len(data):
                    break  # posledný kus bez `\n` — zapisovač je možno uprostred riadku
                offset += len(riadok) + 1
                if riadok.strip():
                    try:
                        events.append(parse_line(riadok))
                    except SchemaError as exc:
                        log.warning("live spool: %s @%d preskakujem riadok: %s", path.name, offset, exc)
                if len(events) >= zvysok:
                    break
            if offset == start:
                continue
            out.append(Batch(instance=instance, session=self._session_of(path, events), path=path,
                             events=events, start_offset=start, end_offset=offset))
            zvysok -= len(events)
        return out

    def status(self) -> dict[str, Any]:
        """Korene, súbory a koľko bajtov ešte čaká za kurzorom."""
        subory = []
        cakaju = 0
        for instance, path in self.scan():
            try:
                velkost = path.stat().st_size
            except OSError:
                continue
            offset = self.cursor.get(str(path), 0)
            pending = max(0, velkost - offset)
            cakaju += pending
            subory.append({"instance": instance, "path": str(path), "size": velkost,
                           "offset": offset, "pending": pending})
        return {"roots": [str(r) for r in self.roots], "files": subory, "pending_bytes": cakaju}
