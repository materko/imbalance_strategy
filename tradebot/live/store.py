"""Sklad udalostí live telemetrie nad sqlite — jeden kód pre hub (`live.sqlite`) aj zrkadlo webapp.

Dve tabuľky: `instances` (posledný známy stav inštancie, odvodený z `hello` a `bar`) a `events`
(každý riadok spoolu raz — `UNIQUE(instance, session, seq)`, takže opakovaná dávka od agenta
alebo opakovaný export do zrkadla nič nezdvojí). `rowid` udalostí je kurzor pre zrkadlo
(`export(after=)`) aj pre prírastkové čítanie z prehliadača (`events(after=)`).

Store nič nepočíta — snapshot len poskladá posledných N barov a to, čo k nim patrí.

Každý štart stratégie je nová **session** (beh): `sessions(instance)` dá prehľad behov
(štart z `hello`, koniec z `bye`, počty), `snapshot`/`events` so `session=` čítajú len ten
jeden beh — v webapp je to výber „Beh“ v detaile inštancie.

**Ping `hb`** (platforma žije, aj keď bary nechodia) nečísluje `seq` — nesie posledné pridelené
číslo. Sklad z pingov behu drží **len posledný**: riadok v `events` so `seq = 0` (skutočné
udalosti majú `seq` od 1, takže `UNIQUE` aj `gaps` ostávajú bez zmeny), ktorý sa pri novšom
pingu zmaže a vloží znova — dostane nový `rowid`, takže ho zrkadlo dostane cez `export`, a tabuľka
nenarastie o 1440 riadkov denne na inštanciu. Stav inštancie nesie `last_hb` (a telo pingu `hb`);
`liveness` z toho povie `live` / `closed` (pinguje, ale bary nechodia — trh zatvorený) / `silent`.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable

from .schema import SchemaError, validate

__all__ = ["LiveStore", "liveness", "HB_ALIVE_MS", "LIVE_BARS"]

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
    last_session TEXT NOT NULL DEFAULT '',
    last_hb      INTEGER NOT NULL DEFAULT 0,
    hb           TEXT NOT NULL DEFAULT '{}'
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
CREATE INDEX IF NOT EXISTS events_instance_session_kind ON events (instance, session, kind, id);
"""

#: Koľko barov dá snapshot bez / s vybranou session, keď volajúci počet neurčí.
DEFAULT_BARS = 500
SESSION_BARS = 5000
#: Beh je „živý“, kým od poslednej udalosti neprešlo viac než toľko barov jeho TF (ako chip v webapp).
LIVE_BARS = 3
#: Inštancia, ktorá pinguje (`hb` každých 60 s), je živá, kým od poslednej udalosti neprešlo toľko ms —
#: nezávisle od TF; bez pingov (starý kód, Tester) platí `LIVE_BARS`.
HB_ALIVE_MS = 180_000

_INSTANCE_COLS = ("id", "agent", "platform", "account", "symbol", "tf", "strategy", "profile", "host",
                  "hello", "first_seen", "last_seen", "last_t", "last_bar_ms", "last_session", "last_hb", "hb")
#: Stĺpce pridané po prvej verzii — starý súbor dostane `ALTER TABLE`.
_ADDED_COLS = {"last_hb": "INTEGER NOT NULL DEFAULT 0", "hb": "TEXT NOT NULL DEFAULT '{}'"}


def liveness(inst: dict[str, Any], now_ms: float) -> str:
    """Stav inštancie pre kartu Live, Telegram aj nasadenia: `live`, `closed` alebo `silent`.

    Pinguje (posledný `hb` nie je o viac než `HB_ALIVE_MS` starší než posledná udalosť) → živá, kým
    posledná udalosť nie je staršia než `HB_ALIVE_MS`; a keď bar neprišiel dlhšie než `LIVE_BARS + 1`
    barov TF, je to `closed` (platforma beží, trh stojí). Nepinguje → starý rozsah `LIVE_BARS` barov TF
    a `closed` sa poznať nedá. `inst` stačí s `last_t`, `last_bar_ms`, `tf` a `last_hb`."""
    last_t = int(inst.get("last_t") or 0)
    if not last_t:
        return "silent"
    tf_ms = max(1, int(inst.get("tf") or 1)) * 60_000
    last_hb = int(inst.get("last_hb") or 0)
    pinguje = last_hb > 0 and last_t - last_hb <= HB_ALIVE_MS
    if now_ms - last_t > (HB_ALIVE_MS if pinguje else LIVE_BARS * tf_ms):
        return "silent"
    bar = int(inst.get("last_bar_ms") or 0)
    if pinguje and (not bar or now_ms - bar > (LIVE_BARS + 1) * tf_ms):
        return "closed"
    return "live"


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
            mam = {r["name"] for r in self._db.execute("PRAGMA table_info(instances)")}
            for col, typ in _ADDED_COLS.items():
                if col not in mam:
                    self._db.execute(f"ALTER TABLE instances ADD COLUMN {col} {typ}")
            self._db.commit()

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
            stav: dict[str, Any] | None = None   # riadok inštancie počas dávky — do DB raz na konci
            for ev in events:
                try:
                    validate(ev)
                except SchemaError:
                    continue
                if ev["k"] == "hb":
                    if self._ping(agent, instance, session, ev):
                        accepted += 1
                        stav = self._touch(stav, agent, instance, session, ev, now)
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
                stav = self._touch(stav, agent, instance, session, ev, now)
            if stav is not None and stav["sets"]:
                sets = stav["sets"]
                cols = ", ".join(f"{k} = ?" for k in sets)
                self._db.execute(f"UPDATE instances SET {cols} WHERE id = ?", (*sets.values(), instance))
        return accepted

    def _ping(self, agent: str, instance: str, session: str, ev: dict[str, Any]) -> bool:
        """Posledný ping behu: starší alebo ten istý (opakovaná dávka) nič nezmení; novší nahradí
        predošlý riadok (`seq = 0`) novým, nech má nový `rowid` pre `export`."""
        old = self._db.execute("SELECT id, t FROM events WHERE instance = ? AND session = ? AND seq = 0",
                               (instance, session)).fetchone()
        if old is not None and int(old["t"]) >= int(ev["t"]):
            return False
        if old is not None:
            self._db.execute("DELETE FROM events WHERE id = ?", (old["id"],))
        self._db.execute(
            "INSERT INTO events (agent, instance, session, seq, t, kind, bt, body) VALUES (?, ?, ?, 0, ?, 'hb', NULL, ?)",
            (agent, instance, session, ev["t"], json.dumps(ev, separators=(",", ":"), ensure_ascii=False)))
        return True

    def _touch(self, stav: dict[str, Any] | None, agent: str, instance: str, session: str, ev: dict[str, Any],
               now: float) -> dict[str, Any]:
        """Nová udalosť do riadku inštancie — v pamäti (`stav`: posledné hodnoty a čo zapísať); `ingest` ho zapíše
        jedným UPDATE za dávku. Predtým SELECT + UPDATE pri každej udalosti — po reštarte platforiem desaťtisíce
        a hub na NAS-e dávku 2000 udalostí nestihol do timeoutu agenta."""
        if stav is None:
            row = self._db.execute("SELECT last_t, last_bar_ms, last_hb FROM instances WHERE id = ?", (instance,)).fetchone()
            if row is None:
                self._db.execute(
                    "INSERT INTO instances (id, agent, first_seen, last_seen, last_t, last_session) VALUES (?, ?, ?, ?, ?, ?)",
                    (instance, agent, now, now, ev["t"], session))
                row = {"last_t": ev["t"], "last_bar_ms": 0, "last_hb": 0}
            stav = {"last_t": row["last_t"], "last_bar_ms": int(row["last_bar_ms"] or 0),
                    "last_hb": int(row["last_hb"] or 0), "sets": {}}
        sets: dict[str, Any] = stav["sets"]
        sets.update(last_seen=now, agent=agent)
        if ev["t"] >= stav["last_t"]:
            sets.update(last_t=ev["t"], last_session=session)
            stav["last_t"] = ev["t"]
        if ev["k"] == "hello":
            sets.update(platform=ev["platform"], account=ev["account"], symbol=ev["symbol"], tf=int(ev["tf"]),
                        strategy=ev["strategy"], profile=str(ev.get("profile") or ""), host=str(ev.get("host") or ""),
                        hello=json.dumps(ev, separators=(",", ":"), ensure_ascii=False))
        elif ev["k"] == "hb" and ev["t"] >= stav["last_hb"]:
            sets.update(last_hb=ev["t"], hb=json.dumps(ev, separators=(",", ":"), ensure_ascii=False))
            stav["last_hb"] = ev["t"]
        elif ev["k"] == "bar" and int(ev["bt"]) >= stav["last_bar_ms"]:
            sets["last_bar_ms"] = stav["last_bar_ms"] = int(ev["bt"])
        return stav

    # -- čítanie -------------------------------------------------------------- #

    @staticmethod
    def _instance_row(r: sqlite3.Row) -> dict[str, Any]:
        d = {k: r[k] for k in _INSTANCE_COLS}
        d["hello"] = json.loads(d["hello"] or "{}")
        d["hb"] = json.loads(d["hb"] or "{}")
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
               limit: int = 1000, session: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM events WHERE instance = ? AND id > ?"
        args: list[Any] = [instance, int(after)]
        if session:
            sql += " AND session = ?"
            args.append(session)
        if kinds:
            sql += " AND kind IN (%s)" % ",".join("?" * len(kinds))
            args.extend(kinds)
        sql += " ORDER BY id LIMIT ?"
        args.append(max(1, int(limit)))
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [self._event_row(r) for r in rows]

    def gaps(self, instance: str | None = None) -> list[dict[str, Any]]:
        """Diery v `seq`: platforma čísluje udalosti behu (session) od 1 bez medzier, takže
        chýbajúci kus je `{"instance", "session", "first", "last", "missing"}` (seq `first`..`last`
        vrátane). Chýbajúci začiatok behu (prvé seq > 1) je diera od 1; koniec behu sa
        z čísiel poznať nedá. Najprv lacný `GROUP BY` (počet ≠ rozsah), okno `LAG` len nad
        behmi, kde niečo chýba. Ping (`seq = 0`) sa nepočíta."""
        where, args = ("WHERE seq > 0 AND instance = ?", [instance]) if instance else ("WHERE seq > 0", [])
        with self._lock:
            podozrive = self._db.execute(
                f"SELECT instance, session FROM events {where} GROUP BY instance, session "
                "HAVING COUNT(*) != MAX(seq) - MIN(seq) + 1 OR MIN(seq) > 1", args).fetchall()
            out: list[dict[str, Any]] = []
            for r in podozrive:
                rows = self._db.execute(
                    "SELECT seq, LAG(seq) OVER (ORDER BY seq) AS prev FROM events "
                    "WHERE instance = ? AND session = ? AND seq > 0 ORDER BY seq", (r["instance"], r["session"])).fetchall()
                for x in rows:
                    prev = 0 if x["prev"] is None else int(x["prev"])
                    if int(x["seq"]) - prev > 1:
                        first, last = prev + 1, int(x["seq"]) - 1
                        out.append({"instance": r["instance"], "session": r["session"], "first": first,
                                    "last": last, "missing": last - first + 1})
        return out

    def events_range(self, instance: str, session: str, first: int, last: int,
                     limit: int = 5000) -> list[dict[str, Any]]:
        """Udalosti jedného behu so `seq` v `first..last` (vrátane) v tvare `export` — na
        doplnenie diery v zrkadle."""
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM events WHERE instance = ? AND session = ? AND seq BETWEEN ? AND ? "
                "ORDER BY seq LIMIT ?", (instance, session, int(first), int(last), max(1, int(limit)))).fetchall()
        return [self._event_row(r, with_agent=True) for r in rows]

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

    def sessions(self, instance: str) -> list[dict[str, Any]]:
        """Behy (sessions) inštancie, najnovší prvý: štart (`t` z `hello`, inak prvej udalosti),
        koniec (`t` z `bye`, inak None), posledná udalosť, počty barov/fillov/orderov, rozsah
        barov, profil z `hello`, dôvod ukončenia a `live` — bez `bye` a `liveness` behu (posledná
        udalosť vrátane pingu) nie je `silent` podľa hodín store."""
        inst = self.instance(instance)
        if inst is None:
            return []
        now_ms = self.clock() * 1000.0
        with self._lock:
            rows = self._db.execute(
                "SELECT session, MIN(t) AS first_t, MAX(t) AS last_t, MAX(agent) AS agent, "
                "SUM(kind = 'bar') AS bars, SUM(kind = 'fill') AS fills, SUM(kind = 'order') AS orders, "
                "MIN(CASE WHEN kind = 'bar' THEN bt END) AS first_bar_ms, "
                "MAX(CASE WHEN kind = 'bar' THEN bt END) AS last_bar_ms, "
                "MAX(CASE WHEN kind = 'hb' THEN t END) AS last_hb "
                "FROM events WHERE instance = ? GROUP BY session",
                (instance,)).fetchall()
            out: list[dict[str, Any]] = []
            for r in rows:
                hello = self._db.execute(
                    "SELECT body FROM events WHERE instance = ? AND session = ? AND kind = 'hello' ORDER BY id LIMIT 1",
                    (instance, r["session"])).fetchone()
                bye = self._db.execute(
                    "SELECT body FROM events WHERE instance = ? AND session = ? AND kind = 'bye' ORDER BY id DESC LIMIT 1",
                    (instance, r["session"])).fetchone()
                h = json.loads(hello["body"]) if hello is not None else {}
                b = json.loads(bye["body"]) if bye is not None else None
                last_t = int(r["last_t"])
                out.append({
                    "session": r["session"],
                    "agent": r["agent"] or "",
                    "started": int(h["t"]) if h else int(r["first_t"]),
                    "ended": int(b["t"]) if b is not None else None,
                    "last_t": last_t,
                    "bars": int(r["bars"] or 0),
                    "fills": int(r["fills"] or 0),
                    "orders": int(r["orders"] or 0),
                    "first_bar_ms": int(r["first_bar_ms"]) if r["first_bar_ms"] is not None else None,
                    "last_bar_ms": int(r["last_bar_ms"]) if r["last_bar_ms"] is not None else None,
                    "profile": str(h.get("profile") or "") if h else "",
                    "reason": str(b.get("reason") or "") if b is not None else None,
                    "live": b is None and liveness({"last_t": last_t, "last_bar_ms": r["last_bar_ms"], "tf": inst["tf"],
                                                    "last_hb": r["last_hb"]}, now_ms) != "silent",
                })
        out.sort(key=lambda s: (s["started"], s["last_t"]), reverse=True)
        return out

    def snapshot(self, instance: str, *, bars: int | None = None, session: str | None = None) -> dict[str, Any]:
        """Posledných `bars` barov a všetko, čo k nim patrí (ordery, udalosti, kresby, fills),
        plus posledný `stat` a posledné poznámky — na graf a tabuľky v webapp.

        So `session=` sa všetko číta len z toho jedného behu (predvolene až `SESSION_BARS`
        barov, nech je vidieť celý beh); bez nej je to posledných `DEFAULT_BARS` barov
        inštancie naprieč behmi ako doteraz."""
        if bars is None:
            bars = SESSION_BARS if session else DEFAULT_BARS
        inst = self.instance(instance)
        if inst is None:
            return {"instance": None, "session": session or None, "bars": [], "orders": [], "events": [],
                    "draw": [], "fills": [], "stats": None, "notes": []}
        bars = max(1, int(bars))
        # filter na session ide do každého dopytu rovnako; bez session je prázdny
        ses_sql = " AND session = ?" if session else ""
        ses_args: tuple[Any, ...] = (session,) if session else ()
        with self._lock:
            # posledných N **rôznych** barov: ten istý bar sa po reštarte zopakuje (prehratie
            # predhistórie), platí posledný zápis — inak by okno po reštarte bolo kratšie
            bar_rows = self._db.execute(
                f"SELECT body FROM events WHERE instance = ? AND kind = 'bar'{ses_sql} AND id IN "
                f"(SELECT MAX(id) FROM events WHERE instance = ? AND kind = 'bar'{ses_sql} GROUP BY bt) "
                "ORDER BY bt DESC LIMIT ?",
                (instance, *ses_args, instance, *ses_args, bars)).fetchall()
            bar_list = [json.loads(r["body"]) for r in reversed(bar_rows)]
            # ten istý bar sa mohol zopakovať po reštarte (prehratie predhistórie) — nechaj posledný
            by_bt: dict[int, dict[str, Any]] = {}
            for b in bar_list:
                by_bt[int(b["bt"])] = b
            bar_list = [by_bt[k] for k in sorted(by_bt)]
            since = bar_list[0]["bt"] if bar_list else 0

            def kind(k: str, time_col: str = "bt") -> list[dict[str, Any]]:
                rows = self._db.execute(
                    f"SELECT body FROM events WHERE instance = ? AND kind = ?{ses_sql} AND "
                    f"COALESCE(json_extract(body, '$.{time_col}'), 0) >= ? ORDER BY id",
                    (instance, k, *ses_args, since)).fetchall()
                return [json.loads(r["body"]) for r in rows]

            stat = self._db.execute(
                f"SELECT body FROM events WHERE instance = ? AND kind = 'stat'{ses_sql} ORDER BY id DESC LIMIT 1",
                (instance, *ses_args)).fetchone()
            notes = self._db.execute(
                f"SELECT body FROM events WHERE instance = ? AND kind IN ('note', 'bye'){ses_sql} "
                "ORDER BY id DESC LIMIT 20",
                (instance, *ses_args)).fetchall()
        # kresby toho istého objektu po reštarte prídu znova — graf ich zlúči podľa `id`
        return {
            "instance": inst,
            "session": session or None,
            "bars": bar_list,
            "orders": kind("order"),
            "events": kind("event"),
            "draw": kind("draw"),
            "fills": kind("fill", "ft"),
            "stats": json.loads(stat["body"])["stats"] if stat is not None else None,
            "notes": [json.loads(r["body"]) for r in reversed(notes)],
        }
