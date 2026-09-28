"""Sklad udalostí live telemetrie nad sqlite — jeden kód pre hub (`live.sqlite`) aj zrkadlo webapp.

Dve tabuľky: `instances` (posledný známy stav inštancie, odvodený z `hello` a `bar`) a `events`
(každý riadok spoolu raz — `UNIQUE(instance, session, seq)`, takže opakovaná dávka od agenta
alebo opakovaný export do zrkadla nič nezdvojí). `rowid` udalostí je kurzor pre zrkadlo
(`export(after=)`) aj pre prírastkové čítanie z prehliadača (`events(after=)`).

Store nič nepočíta — snapshot len poskladá posledných N barov a to, čo k nim patrí.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable

from .schema import SchemaError, validate

__all__ = ["LiveStore"]

_DDL = """
CREATE TABLE IF NOT EXISTS instances (
    id           TEXT PRIMARY KEY,
    agent        TEXT NOT NULL DEFAULT '',
    platform     TEXT NOT NULL DEFAULT '',
    account      TEXT NOT NULL DEFAULT '',
    symbol       TEXT NOT NULL DEFAULT '',
    tf           INTEGER NOT NULL DEFAULT 0,
    strategy     TEXT NOT NULL DEFAULT '',
    profile      TEXT NOT NULL DEFAULT '',
    host         TEXT NOT NULL DEFAULT '',
    hello        TEXT NOT NULL DEFAULT '{}',
    first_seen   REAL NOT NULL,
    last_seen    REAL NOT NULL,
    last_t       INTEGER NOT NULL DEFAULT 0,
    last_bar_ms  INTEGER NOT NULL DEFAULT 0,
    last_session TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    agent    TEXT NOT NULL DEFAULT '',
    instance TEXT NOT NULL,
    session  TEXT NOT NULL,
    seq      INTEGER NOT NULL,
    t        INTEGER NOT NULL,
    kind     TEXT NOT NULL,
    bt       INTEGER,
    body     TEXT NOT NULL,
    UNIQUE (instance, session, seq)
);
CREATE INDEX IF NOT EXISTS events_instance_kind ON events (instance, kind, id);
CREATE INDEX IF NOT EXISTS events_instance_bt ON events (instance, bt);
"""

_INSTANCE_COLS = ("id", "agent", "platform", "account", "symbol", "tf", "strategy", "profile", "host",
                  "hello", "first_seen", "last_seen", "last_t", "last_bar_ms", "last_session")


class LiveStore:
    def __init__(self, path: Path | str, *, clock=time.time) -> None:
        self.path = Path(path)
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript("PRAGMA journal_mode=WAL;" + _DDL)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- zápis ---------------------------------------------------------------- #

    def ingest(self, agent: str, instance: str, session: str, events: Iterable[dict[str, Any]]) -> int:
        """Uloží udalosti jednej session; vráti, koľko bolo **nových**. Rozbitý riadok (schéma)
        sa preskočí — jeden zlý riadok nesmie zastaviť celú dávku ani posun kurzora."""
        now = self.clock()
        accepted = 0
        with self._lock, self._db:
            for ev in events:
                try:
                    validate(ev)
                except SchemaError:
                    continue
                cur = self._db.execute(
                    "INSERT OR IGNORE INTO events (agent, instance, session, seq, t, kind, bt, body) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (agent, instance, session, ev["seq"], ev["t"], ev["k"],
                     ev.get("bt") if isinstance(ev.get("bt"), int) else None,
                     json.dumps(ev, separators=(",", ":"), ensure_ascii=False)),
                )
                if cur.rowcount != 1:
                    continue
                accepted += 1
                self._touch(agent, instance, session, ev, now)
        return accepted

    def _touch(self, agent: str, instance: str, session: str, ev: dict[str, Any], now: float) -> None:
        row = self._db.execute("SELECT last_t, last_bar_ms FROM instances WHERE id = ?", (instance,)).fetchone()
        if row is None:
            self._db.execute(
                "INSERT INTO instances (id, agent, first_seen, last_seen, last_t, last_session) VALUES (?, ?, ?, ?, ?, ?)",
                (instance, agent, now, now, ev["t"], session))
            row = {"last_t": ev["t"], "last_bar_ms": 0}
        sets: dict[str, Any] = {"last_seen": now, "agent": agent}
        if ev["t"] >= row["last_t"]:
            sets.update(last_t=ev["t"], last_session=session)
        if ev["k"] == "hello":
            sets.update(platform=ev["platform"], account=ev["account"], symbol=ev["symbol"], tf=int(ev["tf"]),
                        strategy=ev["strategy"], profile=str(ev.get("profile") or ""), host=str(ev.get("host") or ""),
                        hello=json.dumps(ev, separators=(",", ":"), ensure_ascii=False))
        elif ev["k"] == "bar" and int(ev["bt"]) >= int(row["last_bar_ms"] or 0):
            sets["last_bar_ms"] = int(ev["bt"])
        cols = ", ".join(f"{k} = ?" for k in sets)
        self._db.execute(f"UPDATE instances SET {cols} WHERE id = ?", (*sets.values(), instance))

    # -- čítanie -------------------------------------------------------------- #

    @staticmethod
    def _instance_row(r: sqlite3.Row) -> dict[str, Any]:
        d = {k: r[k] for k in _INSTANCE_COLS}
        d["hello"] = json.loads(d["hello"] or "{}")
        return d

    def instances(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM instances ORDER BY last_t DESC, id").fetchall()
        return [self._instance_row(r) for r in rows]

    def instance(self, instance: str) -> dict[str, Any] | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM instances WHERE id = ?", (instance,)).fetchone()
        return self._instance_row(r) if r is not None else None

    @staticmethod
    def _event_row(r: sqlite3.Row, with_agent: bool = False) -> dict[str, Any]:
        d = {"id": r["id"], "instance": r["instance"], "session": r["session"], "seq": r["seq"],
             "event": json.loads(r["body"])}
        if with_agent:
            d["agent"] = r["agent"]
        return d

    def events(self, instance: str, *, after: int = 0, kinds: list[str] | None = None,
               limit: int = 1000) -> list[dict[str, Any]]:
        sql = "SELECT * FROM events WHERE instance = ? AND id > ?"
        args: list[Any] = [instance, int(after)]
        if kinds:
            sql += " AND kind IN (%s)" % ",".join("?" * len(kinds))
            args.extend(kinds)
        sql += " ORDER BY id LIMIT ?"
        args.append(max(1, int(limit)))
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [self._event_row(r) for r in rows]

    def export(self, after: int = 0, limit: int = 5000) -> list[dict[str, Any]]:
        """Riadky od `after` (rowid) pre zrkadlo — s menom agenta, nech ho zrkadlo zachová."""
        with self._lock:
            rows = self._db.execute("SELECT * FROM events WHERE id > ? ORDER BY id LIMIT ?",
                                    (int(after), max(1, int(limit)))).fetchall()
        return [self._event_row(r, with_agent=True) for r in rows]

    def cursor(self) -> int:
        with self._lock:
            r = self._db.execute("SELECT COALESCE(MAX(id), 0) AS m FROM events").fetchone()
        return int(r["m"])

    def snapshot(self, instance: str, *, bars: int = 500) -> dict[str, Any]:
        """Posledných `bars` barov a všetko, čo k nim patrí (ordery, udalosti, kresby, fills),
        plus posledný `stat` a posledné poznámky — na graf a tabuľky v webapp."""
        inst = self.instance(instance)
        if inst is None:
            return {"instance": None, "bars": [], "orders": [], "events": [], "draw": [], "fills": [],
                    "stats": None, "notes": []}
        bars = max(1, int(bars))
        with self._lock:
            # posledných N **rôznych** barov: ten istý bar sa po reštarte zopakuje (prehratie
            # predhistórie), platí posledný zápis — inak by okno po reštarte bolo kratšie
            bar_rows = self._db.execute(
                "SELECT body FROM events WHERE instance = ? AND kind = 'bar' AND id IN "
                "(SELECT MAX(id) FROM events WHERE instance = ? AND kind = 'bar' GROUP BY bt) "
                "ORDER BY bt DESC LIMIT ?",
                (instance, instance, bars)).fetchall()
            bar_list = [json.loads(r["body"]) for r in reversed(bar_rows)]
            # ten istý bar sa mohol zopakovať po reštarte (prehratie predhistórie) — nechaj posledný
            by_bt: dict[int, dict[str, Any]] = {}
            for b in bar_list:
                by_bt[int(b["bt"])] = b
            bar_list = [by_bt[k] for k in sorted(by_bt)]
            since = bar_list[0]["bt"] if bar_list else 0

            def kind(k: str, time_col: str = "bt") -> list[dict[str, Any]]:
                rows = self._db.execute(
                    f"SELECT body FROM events WHERE instance = ? AND kind = ? AND "
                    f"COALESCE(json_extract(body, '$.{time_col}'), 0) >= ? ORDER BY id",
                    (instance, k, since)).fetchall()
                return [json.loads(r["body"]) for r in rows]

            stat = self._db.execute(
                "SELECT body FROM events WHERE instance = ? AND kind = 'stat' ORDER BY id DESC LIMIT 1",
                (instance,)).fetchone()
            notes = self._db.execute(
                "SELECT body FROM events WHERE instance = ? AND kind IN ('note', 'bye') ORDER BY id DESC LIMIT 20",
                (instance,)).fetchall()
        # kresby toho istého objektu po reštarte prídu znova — graf ich zlúči podľa `id`
        return {
            "instance": inst,
            "bars": bar_list,
            "orders": kind("order"),
            "events": kind("event"),
            "draw": kind("draw"),
            "fills": kind("fill", "ft"),
            "stats": json.loads(stat["body"])["stats"] if stat is not None else None,
            "notes": [json.loads(r["body"]) for r in reversed(notes)],
        }
