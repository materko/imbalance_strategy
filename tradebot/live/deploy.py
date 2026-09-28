"""Požadovaný stav live nasadení na hube: účty, nasadenia, audit a čo agent naposledy potvrdil.

Fáza 2b (docs/LIVE.md): hub drží, **čo má kde bežať** (`accounts`, `deployments`), agent na
obchodnom stroji to v heartbeate dostane celé (`desired_for_agent`), zosúladí so skutočnosťou
a hlási späť, čo sa mu podarilo (`report_applied` → tabuľka `applied`). Rozdiel medzi
`deployments.config_hash`/`mode` a `applied` je drift, ktorý webapp ukáže.

Ten istý sqlite súbor ako `LiveStore` (`live.sqlite`), vlastné spojenie a vlastné tabuľky —
udalosti zo spoolu a požadovaný stav ležia vedľa seba, ale jeden kód nepotrebuje druhý.

Heslo účtu hub **nikdy neukladá natrvalo**: príde raz (`upsert_account(password=…)`), leží
v `secret_pending`, odíde agentovi v najbližšom heartbeate a po potvrdení (`secret_ack`) sa
zmaže. Do žiadneho zoznamu okrem `desired_for_agent` sa nedostane.

Hub nepozná platformu menom — jediné, čo z nej potrebuje, je identita účtu do id inštancie
(`ACCOUNT_IDENTITY`: MT5 `<login>-<server>`, inak `<login>`), aby `instance` nasadenia sedelo
s adresárom spoolu, ktorý platforma založí (`schema.instance_id`).
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .schema import CONTROL_MODES, instance_id, instance_symbol

__all__ = ["DeployStore", "DeployError", "Conflict", "NotFound", "config_hash", "account_identity", "ACCOUNT_IDENTITY",
           "code_state", "CODE_STATES", "DEFAULT_MODE"]

_DDL = """
CREATE TABLE IF NOT EXISTS accounts (
    id             TEXT PRIMARY KEY,
    agent          TEXT NOT NULL,
    platform       TEXT NOT NULL,
    label          TEXT NOT NULL DEFAULT '',
    login          TEXT NOT NULL DEFAULT '',
    server         TEXT NOT NULL DEFAULT '',
    terminal       TEXT NOT NULL DEFAULT '',
    portable       INTEGER NOT NULL DEFAULT 0,
    created        REAL NOT NULL,
    updated        REAL NOT NULL,
    by             TEXT NOT NULL DEFAULT '',
    secret_pending TEXT
);
CREATE TABLE IF NOT EXISTS deployments (
    id          TEXT PRIMARY KEY,
    account     TEXT NOT NULL,
    strategy    TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    tf          INTEGER NOT NULL,
    profile     TEXT NOT NULL DEFAULT '',
    config      TEXT NOT NULL DEFAULT '{}',
    config_hash TEXT NOT NULL DEFAULT '',
    mode        TEXT NOT NULL DEFAULT 'enabled',
    active      INTEGER NOT NULL DEFAULT 1,
    instance    TEXT NOT NULL DEFAULT '',
    version     TEXT NOT NULL DEFAULT '',
    created     REAL NOT NULL,
    updated     REAL NOT NULL,
    by          TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS deployments_account ON deployments (account);
CREATE TABLE IF NOT EXISTS audit (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    by         TEXT NOT NULL DEFAULT '',
    action     TEXT NOT NULL,
    account    TEXT,
    deployment TEXT,
    old        TEXT,
    new        TEXT
);
CREATE TABLE IF NOT EXISTS applied (
    deployment  TEXT PRIMARY KEY,
    agent       TEXT NOT NULL DEFAULT '',
    config_hash TEXT NOT NULL DEFAULT '',
    mode        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT '',
    error       TEXT NOT NULL DEFAULT '',
    ts          REAL NOT NULL
);
"""

#: Ako sa z účtu spraví reťazec do id inštancie (to, čo platforma hlási v `hello.account`).
#: Jediné miesto, kde hub vie o platforme niečo viac než kľúč.
ACCOUNT_IDENTITY: dict[str, str] = {"mt5": "{login}-{server}"}
DEFAULT_IDENTITY = "{login}"

#: Stavy, ktoré agent hlási v `applied.status`.
APPLIED_STATES = ("ok", "pending", "error", "removed")
#: Režim nového nasadenia, keď ho zadávateľ neurčí: pauznuté — zapne sa ručne v tabuľke.
DEFAULT_MODE = "paused"

_ACCOUNT_FIELDS = ("agent", "platform", "label", "login", "server", "terminal", "portable")
_ACCOUNT_COLS = ("id", *_ACCOUNT_FIELDS, "created", "updated", "by")
_DEPLOYMENT_COLS = ("id", "account", "strategy", "symbol", "tf", "profile", "config", "config_hash",
                    "mode", "active", "instance", "version", "created", "updated", "by")
#: Stĺpce, ktoré pribudli po prvom vydaní — `ALTER TABLE` pri otvorení starého súboru.
_MIGRATIONS = (("deployments", "version", "TEXT NOT NULL DEFAULT ''"),)

#: Stav kódu na stroji voči tomu, čo nasadenie (alebo hub) chce — fáza 2c.
CODE_STATES = ("ok", "outdated", "unknown")


def code_state(wanted: str | None, installed: str | None, ancestor: Callable[[str, str], bool] | None = None) -> str:
    """`ok` = platforma má commit `wanted` (rovnaký sha, alebo `wanted` je v histórii nainštalovaného —
    `ancestor(wanted, installed)`, hub to vie z vlastného klonu), `unknown` = stroj marker nehlási,
    `outdated` = niečo iné."""
    if not installed:
        return "unknown"
    if not wanted:
        return "ok"
    a, b = str(wanted).strip().lower(), str(installed).strip().lower()
    if a == b or (len(a) >= 7 and len(b) >= 7 and (a.startswith(b) or b.startswith(a))):
        return "ok"
    if ancestor is not None:
        try:
            if ancestor(wanted, installed):
                return "ok"
        except Exception:  # noqa: BLE001 - git mimo nesmie zhodiť zoznam
            pass
    return "outdated"
_APPLIED_COLS = ("deployment", "agent", "config_hash", "mode", "status", "error", "ts")

_SLUG_BAD = re.compile(r"[^a-z0-9._-]+")


class DeployError(ValueError):
    """Neplatný vstup alebo zakázaná zmena (422/409 v API)."""


class Conflict(DeployError):
    """Zmena naráža na existujúci stav (duplicitná inštancia, účet s nasadeniami) — 409."""


class NotFound(KeyError):
    """Účet alebo nasadenie neexistuje."""


def config_hash(config: dict[str, Any]) -> str:
    """sha256 kanonického JSON (zoradené kľúče, bez medzier) — ten istý výpočet na hube aj u agenta."""
    return hashlib.sha256(json.dumps(config or {}, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def account_identity(account: dict[str, Any]) -> str:
    """Reťazec účtu v id inštancie: podľa `ACCOUNT_IDENTITY` platformy, inak `login`."""
    vzor = ACCOUNT_IDENTITY.get(str(account.get("platform") or ""), DEFAULT_IDENTITY)
    return vzor.format(login=str(account.get("login") or ""), server=str(account.get("server") or ""))


def _slug(text: str) -> str:
    s = _SLUG_BAD.sub("-", str(text or "").strip().lower()).strip("-._")
    return s or "ucet"


def _default_resolver(strategy: str, profile: str) -> dict[str, Any]:
    """Config z profilu stratégie: cez webapp (aj vlastné profily testera), inak z repozitára."""
    try:
        from tester.webapp.repo_profiles import default_params  # type: ignore[import-not-found]

        return default_params(profile, strategy)[0]
    except ImportError:
        from tradebot.core.config import load_profile

        return load_profile(profile, strategy=strategy)[0].to_dict()


class DeployStore:
    def __init__(self, path: Path | str, *, clock: Callable[[], float] = time.time,
                 config_resolver: Callable[[str, str], dict[str, Any]] | None = None,
                 strategy_check: Callable[[str], str] | None = None,
                 version: Callable[[], str] | str | None = None) -> None:
        self.path = Path(path)
        self.clock = clock
        self.config_resolver = config_resolver or _default_resolver
        self.strategy_check = strategy_check or _check_strategy
        #: Predvolená verzia kódu nového nasadenia (commit hubu), keď ju zadávateľ neposlal — fáza 2c.
        self._version = version if callable(version) else (lambda v=version: str(v or ""))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript("PRAGMA journal_mode=WAL;" + _DDL)
            self._migrate()

    def _migrate(self) -> None:
        for table, col, ddl in _MIGRATIONS:
            mena = {r["name"] for r in self._db.execute(f"PRAGMA table_info({table})")}
            if col not in mena:
                self._db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        # `instance` je odvodený stĺpec — keď sa zmení pravidlo (napr. NT `MNQ 12-26` → `MNQ`,
        # `instance_symbol`), staré riadky sa dorovnajú pri štarte, nie až pri zmene účtu.
        for r in self._db.execute("SELECT DISTINCT account FROM deployments"):
            try:
                self._recompute_instances(r["account"])
            except KeyError:
                continue   # nasadenie bez účtu (nemalo by nastať) — nechať tak
        self._db.commit()

    def version(self) -> str:
        """Predvolená verzia kódu pre nasadenia (commit hubu)."""
        try:
            return str(self._version() or "")
        except Exception:  # noqa: BLE001
            return ""

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- pomocné --------------------------------------------------------------- #

    @staticmethod
    def _account_row(r: sqlite3.Row) -> dict[str, Any]:
        d = {k: r[k] for k in _ACCOUNT_COLS}
        d["portable"] = bool(d["portable"])
        d["secret_pending"] = bool(r["secret_pending"])   # len či čaká — obsah nikdy
        return d

    @staticmethod
    def _deployment_row(r: sqlite3.Row) -> dict[str, Any]:
        d = {k: r[k] for k in _DEPLOYMENT_COLS}
        d["config"] = json.loads(d["config"] or "{}")
        d["active"] = bool(d["active"])
        return d

    @staticmethod
    def _applied_row(r: sqlite3.Row | None) -> dict[str, Any] | None:
        return {k: r[k] for k in _APPLIED_COLS} if r is not None else None

    def _audit(self, by: str, action: str, *, account: str | None = None, deployment: str | None = None,
               old: Any = None, new: Any = None) -> None:
        self._db.execute(
            "INSERT INTO audit (ts, by, action, account, deployment, old, new) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.clock(), by or "", action, account, deployment,
             json.dumps(old, ensure_ascii=False, sort_keys=True, default=str) if old is not None else None,
             json.dumps(new, ensure_ascii=False, sort_keys=True, default=str) if new is not None else None))

    def note(self, by: str, action: str, *, account: str | None = None, deployment: str | None = None,
             old: Any = None, new: Any = None) -> None:
        """Riadok auditu mimo účtov a nasadení (napr. požiadavka na nový kód stroja) — to isté, čo píšu mutácie."""
        with self._lock, self._db:
            self._audit(by, action, account=account, deployment=deployment, old=old, new=new)

    def _account_or_404(self, account_id: str) -> sqlite3.Row:
        r = self._db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if r is None:
            raise NotFound(f"účet {account_id!r} neexistuje")
        return r

    def _deployment_or_404(self, dep_id: str) -> sqlite3.Row:
        r = self._db.execute("SELECT * FROM deployments WHERE id = ?", (dep_id,)).fetchone()
        if r is None:
            raise NotFound(f"nasadenie {dep_id!r} neexistuje")
        return r

    # -- účty ------------------------------------------------------------------ #

    def accounts(self, agent: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM accounts", []
        if agent:
            sql += " WHERE agent = ?"
            args.append(agent)
        with self._lock:
            rows = self._db.execute(sql + " ORDER BY agent, id", args).fetchall()
        return [self._account_row(r) for r in rows]

    def account(self, account_id: str) -> dict[str, Any] | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return self._account_row(r) if r is not None else None

    def upsert_account(self, data: dict[str, Any], by: str, password: str | None = None) -> dict[str, Any]:
        """Nový účet (id zo `label`, keď chýba) alebo zmena existujúceho (podľa `id`).
        `password` ide len do `secret_pending`; prázdny reťazec = nemení sa."""
        data = dict(data or {})
        with self._lock, self._db:
            now = self.clock()
            existing = self._db.execute("SELECT * FROM accounts WHERE id = ?", (data.get("id"),)).fetchone() \
                if data.get("id") else None
            if existing is None:
                for key in ("agent", "platform"):
                    if not str(data.get(key) or "").strip():
                        raise DeployError(f"účet potrebuje {key}")
                if not str(data.get("login") or "").strip():
                    raise DeployError("účet potrebuje login (MT5 číslo účtu / NT meno účtu)")
                acc_id = str(data.get("id") or "").strip() or self._free_id(_slug(data.get("label") or data.get("login")))
                if acc_id != _slug(acc_id):
                    raise DeployError(f"id účtu {acc_id!r}: len malé písmená, číslice, '.', '-' a '_'")
                row = {"id": acc_id, "agent": str(data["agent"]).strip(), "platform": str(data["platform"]).strip(),
                       "label": str(data.get("label") or acc_id).strip(), "login": str(data["login"]).strip(),
                       "server": str(data.get("server") or "").strip(), "terminal": str(data.get("terminal") or "").strip(),
                       "portable": 1 if data.get("portable") else 0, "created": now, "updated": now, "by": by or ""}
                self._db.execute(
                    "INSERT INTO accounts (id, agent, platform, label, login, server, terminal, portable, created, "
                    "updated, by, secret_pending) VALUES (:id, :agent, :platform, :label, :login, :server, :terminal, "
                    ":portable, :created, :updated, :by, :secret)", {**row, "secret": password or None})
                self._audit(by, "account_create", account=acc_id, new={**row, "password": bool(password)})
            else:
                acc_id = existing["id"]
                old = self._account_row(existing)
                sets: dict[str, Any] = {}
                for key in _ACCOUNT_FIELDS:
                    if key in data and data[key] is not None:
                        sets[key] = (1 if data[key] else 0) if key == "portable" else str(data[key]).strip()
                if "platform" in sets and not sets["platform"]:
                    raise DeployError("platforma nesmie byť prázdna")
                if "login" in sets and not sets["login"]:
                    raise DeployError("login nesmie byť prázdny")
                if password:
                    sets["secret_pending"] = password
                if not sets:
                    return old
                sets.update(updated=now, by=by or "")
                cols = ", ".join(f"{k} = ?" for k in sets)
                self._db.execute(f"UPDATE accounts SET {cols} WHERE id = ?", (*sets.values(), acc_id))
                zmena = {k: v for k, v in sets.items() if k not in ("updated", "by", "secret_pending")}
                if password:
                    zmena["password"] = True
                self._audit(by, "account_update", account=acc_id,
                            old={k: old.get(k) for k in zmena if k != "password"}, new=zmena)
                # identita účtu je v id inštancií — keď sa zmení login/server/platforma, prepočítať
                if any(k in sets for k in ("login", "server", "platform")):
                    self._recompute_instances(acc_id)
            return self._account_row(self._account_or_404(acc_id))

    def _free_id(self, base: str) -> str:
        cand, n = base, 1
        while self._db.execute("SELECT 1 FROM accounts WHERE id = ?", (cand,)).fetchone() is not None:
            n += 1
            cand = f"{base}-{n}"
        return cand

    def _recompute_instances(self, account_id: str) -> None:
        acc = self._account_row(self._account_or_404(account_id))
        for r in self._db.execute("SELECT id, symbol, tf, strategy FROM deployments WHERE account = ?", (account_id,)):
            inst = instance_id(acc["platform"], account_identity(acc), instance_symbol(acc["platform"], r["symbol"]),
                               int(r["tf"]), r["strategy"])
            self._db.execute("UPDATE deployments SET instance = ? WHERE id = ?", (inst, r["id"]))

    def delete_account(self, account_id: str, by: str, force: bool = False) -> dict[str, Any]:
        """Zmaže účet; s nasadeniami len s `force` (zmažú sa aj tie — agent ich pri ďalšom
        heartbeate už nedostane, takže ich má odstrániť z platformy sám)."""
        with self._lock, self._db:
            old = self._account_row(self._account_or_404(account_id))
            deps = [r["id"] for r in self._db.execute("SELECT id FROM deployments WHERE account = ?", (account_id,))]
            if deps and not force:
                raise Conflict(f"účet {account_id!r} má nasadenia ({', '.join(deps)}) — najprv ich odstráň, "
                                  f"alebo to vynúť")
            for dep_id in deps:
                self._db.execute("DELETE FROM applied WHERE deployment = ?", (dep_id,))
                self._db.execute("DELETE FROM deployments WHERE id = ?", (dep_id,))
                self._audit(by, "deployment_delete", account=account_id, deployment=dep_id, old={"forced": True})
            self._db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            self._audit(by, "account_delete", account=account_id, old=old)
            return {"id": account_id, "deleted": True, "deployments": deps}

    # -- nasadenia ------------------------------------------------------------- #

    def deployments(self, agent: str | None = None, account: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT d.*, a.agent AS _agent, a.platform AS _platform FROM deployments d JOIN accounts a ON a.id = d.account"
        where, args = [], []
        if agent:
            where.append("a.agent = ?"); args.append(agent)
        if account:
            where.append("d.account = ?"); args.append(account)
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self._lock:
            rows = self._db.execute(sql + " ORDER BY a.agent, d.account, d.created", args).fetchall()
            out = []
            for r in rows:
                d = self._deployment_row(r)
                d["agent"] = r["_agent"]
                d["platform"] = r["_platform"]
                d["applied"] = self._applied_row(
                    self._db.execute("SELECT * FROM applied WHERE deployment = ?", (d["id"],)).fetchone())
                out.append(d)
        return out

    def deployment(self, dep_id: str) -> dict[str, Any] | None:
        with self._lock:
            r = self._db.execute("SELECT d.*, a.agent AS _agent, a.platform AS _platform FROM deployments d "
                                 "JOIN accounts a ON a.id = d.account WHERE d.id = ?", (dep_id,)).fetchone()
            if r is None:
                return None
            d = self._deployment_row(r)
            d["agent"] = r["_agent"]
            d["platform"] = r["_platform"]
            d["applied"] = self._applied_row(
                self._db.execute("SELECT * FROM applied WHERE deployment = ?", (dep_id,)).fetchone())
        return d

    def _resolve_config(self, strategy: str, profile: str, config: Any) -> dict[str, Any]:
        if isinstance(config, dict) and config:
            return dict(config)
        if not profile:
            raise DeployError("nasadenie potrebuje profile alebo config")
        try:
            return dict(self.config_resolver(strategy, profile))
        except Exception as exc:  # noqa: BLE001 - chyba profilu je chyba vstupu
            raise DeployError(f"profil {profile!r} stratégie {strategy!r}: {exc}") from None

    def create_deployment(self, data: dict[str, Any], by: str) -> dict[str, Any]:
        data = dict(data or {})
        account_id = str(data.get("account") or "").strip()
        strategy = self.strategy_check(str(data.get("strategy") or "").strip())
        symbol = str(data.get("symbol") or "").strip()
        if not symbol:
            raise DeployError("nasadenie potrebuje symbol")
        try:
            tf = int(data.get("tf") or 0)
        except (TypeError, ValueError):
            raise DeployError("tf musí byť celé číslo minút") from None
        if tf < 1:
            raise DeployError("tf musí byť aspoň 1 minúta")
        # nové nasadenie štartuje pauznuté (control `paused` je na disku skôr, než platforma inštanciu
        # spustí) — obchodovať začne, až keď ho človek v tabuľke zapne; výslovný `mode` sa rešpektuje
        mode = str(data.get("mode") or DEFAULT_MODE)
        if mode not in CONTROL_MODES:
            raise DeployError(f"mode musí byť {'/'.join(CONTROL_MODES)}")
        profile = str(data.get("profile") or "").strip()
        config = self._resolve_config(strategy, profile, data.get("config"))
        with self._lock, self._db:
            acc = self._account_row(self._account_or_404(account_id))
            inst = instance_id(acc["platform"], account_identity(acc), instance_symbol(acc["platform"], symbol), tf, strategy)
            dup = self._db.execute("SELECT id FROM deployments WHERE instance = ?", (inst,)).fetchone()
            if dup is not None:
                raise Conflict(f"tá istá inštancia ({inst}) už je nasadená ako {dup['id']}")
            now = self.clock()
            dep_id = str(data.get("id") or "").strip() or uuid.uuid4().hex[:12]
            row = {"id": dep_id, "account": account_id, "strategy": strategy, "symbol": symbol, "tf": tf,
                   "profile": profile, "config": json.dumps(config, ensure_ascii=False, sort_keys=True),
                   "config_hash": config_hash(config), "mode": mode, "active": 1, "instance": inst,
                   "version": str(data.get("version") or "").strip() or self.version(),
                   "created": now, "updated": now, "by": by or ""}
            self._db.execute(
                "INSERT INTO deployments (id, account, strategy, symbol, tf, profile, config, config_hash, mode, "
                "active, instance, version, created, updated, by) VALUES (:id, :account, :strategy, :symbol, :tf, "
                ":profile, :config, :config_hash, :mode, :active, :instance, :version, :created, :updated, :by)", row)
            self._audit(by, "deployment_create", account=account_id, deployment=dep_id,
                        new={k: v for k, v in row.items() if k != "config"})
        return self.deployment(dep_id)  # type: ignore[return-value]

    def update_deployment(self, dep_id: str, patch: dict[str, Any], by: str) -> dict[str, Any]:
        """Meniť sa smie `mode`, `profile` (+`config`, inak sa dopočíta z profilu), `active` a `version`
        (commit, na ktorom zadávateľ zmenu urobil); účet, stratégia, symbol a TF sú identita inštancie —
        na iné treba nové nasadenie."""
        patch = dict(patch or {})
        zakazane = [k for k in ("account", "strategy", "symbol", "tf", "instance") if k in patch and patch[k] is not None]
        if zakazane:
            raise DeployError(f"{', '.join(zakazane)} sa nemení — sprav nové nasadenie")
        with self._lock, self._db:
            old = self._deployment_row(self._deployment_or_404(dep_id))
            sets: dict[str, Any] = {}
            if patch.get("mode") is not None:
                if patch["mode"] not in CONTROL_MODES:
                    raise DeployError(f"mode musí byť {'/'.join(CONTROL_MODES)}")
                sets["mode"] = patch["mode"]
            if patch.get("active") is not None:
                sets["active"] = 1 if patch["active"] else 0
            if str(patch.get("version") or "").strip():
                sets["version"] = str(patch["version"]).strip()
            if patch.get("profile") is not None or isinstance(patch.get("config"), dict):
                profile = str(patch.get("profile") if patch.get("profile") is not None else old["profile"]).strip()
                config = self._resolve_config(old["strategy"], profile, patch.get("config"))
                sets.update(profile=profile, config=json.dumps(config, ensure_ascii=False, sort_keys=True),
                            config_hash=config_hash(config))
            zmena = {k: v for k, v in sets.items() if k != "config" and old.get(k) != (bool(v) if k == "active" else v)}
            if not zmena:
                return self.deployment(dep_id)  # type: ignore[return-value]
            sets.update(updated=self.clock(), by=by or "")
            cols = ", ".join(f"{k} = ?" for k in sets)
            self._db.execute(f"UPDATE deployments SET {cols} WHERE id = ?", (*sets.values(), dep_id))
            self._audit(by, "deployment_update", account=old["account"], deployment=dep_id,
                        old={k: old.get(k) for k in zmena}, new=zmena)
        return self.deployment(dep_id)  # type: ignore[return-value]

    def delete_deployment(self, dep_id: str, by: str, force: bool = False) -> dict[str, Any]:
        """Odstránenie: najprv `active=false` (agent inštanciu z platformy odstráni), naozaj
        zmazať sa dá, až keď to agent potvrdil (`applied` po deaktivácii) — alebo s `force`."""
        with self._lock, self._db:
            old = self._deployment_row(self._deployment_or_404(dep_id))
            applied = self._applied_row(
                self._db.execute("SELECT * FROM applied WHERE deployment = ?", (dep_id,)).fetchone())
            potvrdene = (applied is not None and applied["status"] in ("ok", "removed")
                         and float(applied["ts"]) >= float(old["updated"]))
            # nasadenie, ktoré agent nikdy nevidel (žiadny `applied`), sa smie zmazať hneď — na
            # platforme z neho nič nie je
            if force or (not old["active"] and (potvrdene or applied is None)):
                self._db.execute("DELETE FROM applied WHERE deployment = ?", (dep_id,))
                self._db.execute("DELETE FROM deployments WHERE id = ?", (dep_id,))
                self._audit(by, "deployment_delete", account=old["account"], deployment=dep_id,
                            old={k: v for k, v in old.items() if k != "config"}, new={"forced": bool(force)})
                return {"id": dep_id, "deleted": True, "active": False}
            if old["active"]:
                self._db.execute("UPDATE deployments SET active = 0, updated = ?, by = ? WHERE id = ?",
                                 (self.clock(), by or "", dep_id))
                self._audit(by, "deployment_update", account=old["account"], deployment=dep_id,
                            old={"active": True}, new={"active": False})
            return {"id": dep_id, "deleted": False, "active": False}

    # -- agent ------------------------------------------------------------------ #

    def desired_for_agent(self, agent: str) -> dict[str, Any]:
        """Celý požadovaný stav jedného agenta do heartbeatu: účty (so `secret`, keď čaká)
        a nasadenia (s `config`, aj neaktívne — tie má agent z platformy odstrániť)."""
        with self._lock:
            accs = []
            for r in self._db.execute("SELECT * FROM accounts WHERE agent = ? ORDER BY id", (agent,)):
                a = self._account_row(r)
                if r["secret_pending"]:
                    a["secret"] = r["secret_pending"]
                accs.append(a)
            deps = [self._deployment_row(r) for r in self._db.execute(
                "SELECT d.* FROM deployments d JOIN accounts a ON a.id = d.account WHERE a.agent = ? "
                "ORDER BY d.account, d.created", (agent,))]
        return {"accounts": accs, "deployments": deps}

    def report_applied(self, agent: str, applied: list[dict[str, Any]] | None,
                       secret_ack: list[str] | None = None) -> int:
        """Agent hlási, čo k nasadeniam naozaj spravil; potvrdené heslá sa z hubu zmažú.
        Cudzie nasadenia (iného agenta) sa ignorujú. Vráti počet prijatých hlásení."""
        n = 0
        with self._lock, self._db:
            now = self.clock()
            for a in applied or []:
                dep_id = str((a or {}).get("deployment") or "")
                if not dep_id:
                    continue
                r = self._db.execute("SELECT a.agent FROM deployments d JOIN accounts a ON a.id = d.account "
                                     "WHERE d.id = ?", (dep_id,)).fetchone()
                if r is None or r["agent"] != agent:
                    continue
                status = str(a.get("status") or "ok")
                if status not in APPLIED_STATES:
                    status = "error"
                self._db.execute(
                    "INSERT INTO applied (deployment, agent, config_hash, mode, status, error, ts) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(deployment) DO UPDATE SET agent = excluded.agent, "
                    "config_hash = excluded.config_hash, mode = excluded.mode, status = excluded.status, "
                    "error = excluded.error, ts = excluded.ts",
                    (dep_id, agent, str(a.get("config_hash") or ""), str(a.get("mode") or ""), status,
                     str(a.get("error") or "")[:500], now))
                n += 1
            for acc_id in secret_ack or []:
                cur = self._db.execute(
                    "UPDATE accounts SET secret_pending = NULL WHERE id = ? AND agent = ? AND secret_pending IS NOT NULL",
                    (str(acc_id), agent))
                if cur.rowcount:
                    self._audit(agent, "secret_taken", account=str(acc_id))
        return n

    # -- audit ------------------------------------------------------------------ #

    def audit(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (max(1, int(limit)),)).fetchall()
        out = []
        for r in rows:
            out.append({"id": r["id"], "ts": r["ts"], "by": r["by"], "action": r["action"],
                        "account": r["account"], "deployment": r["deployment"],
                        "old": json.loads(r["old"]) if r["old"] else None,
                        "new": json.loads(r["new"]) if r["new"] else None})
        return out

    def counts(self) -> dict[str, int]:
        with self._lock:
            a = self._db.execute("SELECT COUNT(*) AS n FROM accounts").fetchone()["n"]
            d = self._db.execute("SELECT COUNT(*) AS n FROM deployments WHERE active = 1").fetchone()["n"]
        return {"accounts": int(a), "deployments": int(d)}


def _check_strategy(key: str) -> str:
    """Kľúč stratégie z registra (aj starý alias → dnešný kľúč); neznámy je chyba vstupu."""
    if not key:
        raise DeployError("nasadenie potrebuje strategy")
    from tradebot.strategies import get_spec

    try:
        return get_spec(key).key
    except KeyError as exc:
        raise DeployError(str(exc)) from None
