"""Index histórie behov — aby zoznam nemusel prečítať celú `tester/runs/`.

    tester/runs/.index/runs.sqlite3     odvodený, gitignored, kedykoľvek zahoditeľný

Prečo vznikol: história narástla na desaťtisíce behov (11 GB, z toho 2 GB samotné
`run.json`) a `RunStore.all()` parsoval pri každom dopyte **všetky** — 30 s procesora na
prvé načítanie a 24 GB v pamäti na cache záznamov, hoci stránka histórie ukazuje 50
riadkov. Index to obracia: raz sa behy prečítajú do sqlite a odvtedy sa stránka histórie
pýta `ORDER BY id DESC LIMIT 50 OFFSET …` — teda číta presne tých 50 behov.

Disk ostáva pravda. Index je len odvodenina: drží `(mtime, veľkosť)` každého `run.json`,
pri každom dopyte sa porovná zoznam adresárov a raz za `SYNC_EVERY` aj časy súborov, takže
čo pribudlo, zmizlo alebo sa prepísalo (aj cez `git pull` alebo `cli recompute --write`),
sa načíta nanovo. Keď sa index poškodí alebo zmení schéma, zmaže sa a postaví znova —
nič sa tým nestratí.

Čo je v ňom uložené: celý záznam behu **bez `series`** (equity krivka je väčšina bajtov
`run.json` a v zozname ani vo vyhľadávaní netreba — detail behu si ju prečíta zo súboru).
Vyhľadávanie preto funguje ďalej aj nad parametrami (`rrRatio>=5`): tie v indexe sú.

Podmienky dopytu, ktoré vie sqlite (pár, stratégia, timeframe, metriky výsledku, text),
sa preložia do `WHERE` a stránka sa vyreže priamo v ňom. Čo sqlite nevie (podmienky nad
parametrami stratégie), dofiltruje Python nad záznamami, ktoré prešli `WHERE` — teda nad
zlomkom histórie, nie nad celou.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable

__all__ = ["RunIndex"]

#: Zvýš pri zmene schémy alebo obsahu `slim` — index sa postaví odznova.
SCHEMA = 1

#: Ako často sa okrem zoznamu adresárov kontrolujú aj časy súborov (sekundy). Pribudnutý
#: a zmiznutý beh sa nájde vždy, toto je len na prepis existujúceho `run.json` cudzím
#: procesom (`cli recompute --write`, `git pull`); `sync(force=True)` to spraví hneď.
SYNC_EVERY = 30.0

#: Textové stĺpce: kľúč dopytu (po `ALIASES`) -> stĺpec. Ukladajú sa malými písmenami,
#: lebo `_match` porovnáva bez ohľadu na veľkosť; na zobrazenie slúži `slim`.
TEXT_COLS = {
    "settings.strategy": "strategy",
    "settings.pair": "pair",
    "settings.timeframe": "timeframe",
    "settings.engine": "engine",
    "settings.exchange": "exchange",
    "settings.profile": "profile",
    "settings.timerange": "timerange",
    "status": "status",
    "user": "usr",
    "note": "note",
    "id": "id",
}

#: Číselné stĺpce výsledku — `NULL`, keď ich beh nemá (potom nesadne žiadna podmienka,
#: rovnako ako `_match` nad chýbajúcim poľom).
NUM_COLS = {
    "result.trades": "trades",
    "result.pnl_pct": "pnl_pct",
    "result.pnl_abs": "pnl_abs",
    "result.profit_factor": "profit_factor",
    "result.winrate": "winrate",
    "result.max_drawdown_pct": "max_drawdown_pct",
    "result.break_even_pct": "break_even_pct",
    "result.duration_s": "duration_s",
}

_OPS = {"=": "=", "!=": "!=", ">": ">", "<": "<", ">=": ">=", "<=": "<="}

_DDL = f"""
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    mtime INTEGER NOT NULL,
    size INTEGER NOT NULL,
    {", ".join(f"{c} TEXT" for c in TEXT_COLS.values() if c != "id")},
    hay TEXT,
    {", ".join(f"{c} REAL" for c in NUM_COLS.values())},
    slim TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_strategy ON runs(strategy);
CREATE INDEX IF NOT EXISTS runs_pair ON runs(pair);
"""

_COLS = ["id", "mtime", "size", *[c for c in TEXT_COLS.values() if c != "id"], "hay",
         *NUM_COLS.values(), "slim"]


def _txt(v: Any) -> str | None:
    """Text do filtrovacieho stĺpca — malými písmenami, prázdne ako `NULL`."""
    if v is None or isinstance(v, (dict, list)):
        return None
    s = str(v)
    return s.lower() if s else None


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _like(raw: str) -> str:
    """Vzor pre `LIKE …  ESCAPE '\\'` — `%` a `_` v hľadanom texte sú obyčajné znaky."""
    escaped = raw.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def row_of(record: dict[str, Any], mtime: int, size: int) -> tuple:
    """Riadok indexu zo záznamu behu. `slim` = celý záznam bez `series`."""
    settings = record.get("settings") or {}
    result = record.get("result") or {}
    slim = {k: v for k, v in record.items() if k != "series"}
    # To isté sitko ako `_match` pre holý token dopytu (id, poznámka, používateľ, pár,
    # profil, stratégia) — aby hľadanie textu vedela spraviť sqlite.
    hay = " ".join(str(x) for x in (
        record.get("id"), record.get("note"), record.get("user"), settings.get("pair"),
        settings.get("profile"), settings.get("strategy")) if x).lower()
    hodnoty: dict[str, Any] = {"id": record.get("id"), "mtime": mtime, "size": size, "hay": hay,
                               "slim": json.dumps(slim, ensure_ascii=False, default=str)}
    for kluc, stlpec in TEXT_COLS.items():
        if stlpec == "id":
            continue
        hodnoty[stlpec] = _txt(record.get(kluc) if "." not in kluc
                               else settings.get(kluc.split(".", 1)[1]))
    for kluc, stlpec in NUM_COLS.items():
        hodnoty[stlpec] = _num(result.get(kluc.split(".", 1)[1]))
    return tuple(hodnoty[c] for c in _COLS)


class RunIndex:
    """Sqlite index nad adresárom behov. Všetko, čo sa pokazí, je len strata rýchlosti:
    `ok` spadne na `False` a sklad sa vráti k čítaniu súborov."""

    def __init__(self, runs_dir: Path, db_path: Path | None = None) -> None:
        self.root = Path(runs_dir)
        self.path = Path(db_path) if db_path else self.root / ".index" / "runs.sqlite3"
        self.ok = True
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._synced = 0.0
        self._deep = 0.0

    # -- spojenie ----------------------------------------------------------- #

    def _db(self) -> sqlite3.Connection | None:
        if not self.ok:
            return None
        if self._conn is not None:
            return self._conn
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, check_same_thread=False, timeout=10.0)
            conn.execute("PRAGMA journal_mode=WAL")      # webapp a CLI píšu do toho istého
            conn.execute("PRAGMA synchronous=NORMAL")    # index je odvodený, fsync netreba
            verzia = conn.execute("SELECT v FROM meta WHERE k='schema'").fetchone() \
                if conn.execute("SELECT name FROM sqlite_master WHERE name='meta'").fetchone() else None
            if verzia is not None and int(verzia[0]) != SCHEMA:
                conn.executescript("DROP TABLE IF EXISTS runs; DROP TABLE IF EXISTS meta;")
            conn.executescript(_DDL)
            conn.execute("INSERT OR REPLACE INTO meta(k, v) VALUES ('schema', ?)", (str(SCHEMA),))
            conn.commit()
        except (sqlite3.Error, OSError, ValueError):
            self.ok = False
            return None
        self._conn = conn
        return conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except sqlite3.Error:
                    pass
                self._conn = None

    # -- zosúladenie s diskom ------------------------------------------------ #

    def forget(self, run_id: str) -> None:
        """Zabudni beh — nabudúce sa prečíta zo súboru. Pre cudzie zápisy do `run.json`."""
        with self._lock:
            conn = self._db()
            if conn is None:
                return
            try:
                conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
                conn.commit()
            except sqlite3.Error:
                self.ok = False

    def put(self, run_id: str) -> None:
        """Načítaj (alebo odstráň) jeden beh — volá sklad hneď po zápise behu."""
        with self._lock:
            conn = self._db()
            if conn is None:
                return
            try:
                self._upsert(conn, [run_id])
                conn.commit()
            except sqlite3.Error:
                self.ok = False

    def sync(self, force: bool = False) -> bool:
        """Dorovnaj index s diskom. `force` = pozri aj časy súborov, nielen zoznam adresárov.

        Vracia `False`, keď index nefunguje a treba čítať súbory.
        """
        with self._lock:
            conn = self._db()
            if conn is None:
                return False
            teraz = time.monotonic()
            hlboko = force or (teraz - self._deep) > SYNC_EVERY
            try:
                na_disku = {e.name for e in os.scandir(self.root)
                            if not e.name.startswith(".") and e.is_dir()}
            except OSError:
                return False
            try:
                v_indexe = {r[0]: (r[1], r[2]) for r in conn.execute("SELECT id, mtime, size FROM runs")}
                zmazat = [i for i in v_indexe if i not in na_disku]
                nacitat = [i for i in na_disku if i not in v_indexe]
                if hlboko:
                    for run_id in na_disku:
                        podpis = v_indexe.get(run_id)
                        if podpis is None:
                            continue
                        try:
                            st = os.stat(self.root / run_id / "run.json")
                        except OSError:
                            zmazat.append(run_id)
                            continue
                        if (st.st_mtime_ns, st.st_size) != podpis:
                            nacitat.append(run_id)
                    self._deep = teraz
                if zmazat:
                    conn.executemany("DELETE FROM runs WHERE id = ?", [(i,) for i in zmazat])
                if nacitat:
                    self._upsert(conn, nacitat)
                if zmazat or nacitat:
                    conn.commit()
            except sqlite3.Error:
                self.ok = False
                return False
            self._synced = teraz
            return True

    def _upsert(self, conn: sqlite3.Connection, ids: Iterable[str]) -> None:
        riadky = []
        for run_id in ids:
            cesta = self.root / run_id / "run.json"
            try:
                st = os.stat(cesta)
                with open(cesta, encoding="utf-8") as fh:
                    rec = json.load(fh)
            except (OSError, json.JSONDecodeError):
                conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
                continue      # rozbitý či zmiznutý súbor nemá zhodiť celý index
            if not isinstance(rec, dict) or rec.get("id") != run_id:
                conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
                continue
            from .store import _with_strategy      # kruhový import len tu, nie pri načítaní

            _with_strategy(rec)      # chýbajúci a starý kľúč stratégie presne ako sklad pri čítaní
            riadky.append(row_of(rec, st.st_mtime_ns, st.st_size))
        if riadky:
            conn.executemany(
                f"INSERT OR REPLACE INTO runs ({', '.join(_COLS)}) "
                f"VALUES ({', '.join('?' * len(_COLS))})", riadky)

    # -- dopyty -------------------------------------------------------------- #

    def where(self, conds: list[tuple[str, str, str]]) -> tuple[str, list[Any], list[tuple[str, str, str]]]:
        """Podmienky dopytu na `(WHERE, hodnoty, zvyšok pre Python)`.

        Do sqlite ide len to, čo sa správa presne ako `store._match`; čokoľvek iné
        (podmienky nad parametrami stratégie) ostáva Pythonu.
        """
        from .store import ALIASES, _coerce      # kruhový import len tu, nie pri načítaní

        casti: list[str] = []
        hodnoty: list[Any] = []
        zvysok: list[tuple[str, str, str]] = []
        for cond in conds:
            key, op, raw = cond
            if key == "*":
                casti.append("hay LIKE ? ESCAPE '\\'")
                hodnoty.append(_like(raw))
                continue
            kluc = ALIASES.get(key, key)
            stlpec = TEXT_COLS.get(kluc)
            if stlpec is not None:
                if op == "~":
                    casti.append(f"{stlpec} LIKE ? ESCAPE '\\'")
                    hodnoty.append(_like(raw))
                    continue
                # `=`/`!=` nad textom platí, len keď hodnota nie je číslo ani bool:
                # `tf=3` znamená v `_match` porovnanie čísel, a to by tu vyšlo inak.
                if op in ("=", "!=") and isinstance(_coerce(raw), str):
                    # `id` sa ukladá tak, ako je (je to aj kľúč a poradie), ostatné texty
                    # už malé sú — porovnanie musí byť v oboch prípadoch bez veľkosti.
                    casti.append(f"{'lower(id)' if stlpec == 'id' else stlpec} {op} ?")
                    hodnoty.append(raw.lower())
                    continue
                zvysok.append(cond)
                continue
            stlpec = NUM_COLS.get(kluc)
            if stlpec is not None and op in _OPS and isinstance(_coerce(raw), float):
                casti.append(f"{stlpec} {_OPS[op]} ?")
                hodnoty.append(float(raw))
                continue
            zvysok.append(cond)
        return (" AND ".join(casti) if casti else "1"), hodnoty, zvysok

    # Čítanie je pod zámkom ako zápis: uvicorn púšťa endpointy vo vláknach a jedno
    # sqlite spojenie neznesie dva kurzory naraz. Keď sa čítanie nepodarí, `ok` spadne
    # na False a volajúci (sklad) sa vráti k súborom.
    def count(self, sql: str, hodnoty: list[Any]) -> int:
        with self._lock:
            conn = self._db()
            if conn is None:
                raise sqlite3.Error("index nie je k dispozícii")
            try:
                return int(conn.execute(f"SELECT COUNT(*) FROM runs WHERE {sql}", hodnoty).fetchone()[0])
            except sqlite3.Error:
                self.ok = False
                raise

    def page(self, sql: str, hodnoty: list[Any], offset: int, limit: int) -> list[dict[str, Any]]:
        """Záznamy (bez `series`) zoradené od najnovšieho — presne jedna stránka."""
        return self._read(f"SELECT slim FROM runs WHERE {sql} ORDER BY id DESC LIMIT ? OFFSET ?",
                          [*hodnoty, limit, offset])

    def records(self, sql: str = "1", hodnoty: list[Any] | None = None) -> list[dict[str, Any]]:
        """Všetky záznamy (bez `series`), od najnovšieho — pre analytiku a dofiltrovanie."""
        return self._read(f"SELECT slim FROM runs WHERE {sql} ORDER BY id DESC", hodnoty or [])

    def _read(self, sql: str, hodnoty: list[Any]) -> list[dict[str, Any]]:
        with self._lock:
            conn = self._db()
            if conn is None:
                raise sqlite3.Error("index nie je k dispozícii")
            try:
                return [json.loads(r[0]) for r in conn.execute(sql, hodnoty)]
            except (sqlite3.Error, json.JSONDecodeError):
                self.ok = False
                raise sqlite3.Error("index sa nepodarilo prečítať")
