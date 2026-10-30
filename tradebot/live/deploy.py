"""Požadovaný stav live nasadení na hube: účty, nasadenia, audit a čo agent naposledy potvrdil.

Fáza 2b (docs/LIVE.md): hub drží, **čo má kde bežať** (`accounts`, `deployments`), agent na
obchodnom stroji to v heartbeate dostane celé (`desired_for_agent`), zosúladí so skutočnosťou
a hlási späť, čo sa mu podarilo (`report_applied` → tabuľka `applied`). Rozdiel medzi
`deployments.config_hash`/`mode` a `applied` je drift, ktorý webapp ukáže.

Ten istý sqlite súbor ako `LiveStore` (`live.sqlite`), vlastné spojenie a vlastné tabuľky —
udalosti zo spoolu a požadovaný stav ležia vedľa seba, ale jeden kód nepotrebuje druhý.

Účet **nie je viazaný na stroj**: je to prihlásenie do platformy (MT5: číslo účtu, server,
heslo; NinjaTrader: meno účtu a pripojenie). Stroj (agent) a pri MT5 terminál určuje až
nasadenie — ten istý účet môže bežať na viacerých strojoch. Agent dostane v `desired_for_agent`
účty, ktoré používajú jeho nasadenia, s terminálom z týchto nasadení.

Heslo hub drží **šifrované** (`tradebot.live.vault`, kľúč `secret.key` vedľa databázy): každý
stroj s nasadením na účte ho dostane v heartbeate raz za verziu hesla (`secret_rev`) a potvrdí
(`secret_ack` → `secret_sent`); nové heslo odíde znova všetkým. Do žiadneho zoznamu okrem
`desired_for_agent` sa nedostane. `rev` účtu sa mení so zmenou prihlásenia (login, server,
heslo) — driver podľa neho bežiacu inštanciu zastaví a spustí s novými údajmi.

Hub nepozná platformu menom — jediné, čo z nej potrebuje, je identita účtu do id inštancie
(`ACCOUNT_IDENTITY`: MT5 `<login>-<server>`, inak `<login>`), aby `instance` nasadenia sedelo
s adresárom spoolu, ktorý platforma založí (`schema.instance_id`).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .routes import EXECUTOR_KIND, MT5_IDENTITY, RouteError, executor_id, normalize_aliases, normalize_route
from .schema import CONTROL_MODES, SLOT_RE, instance_id, instance_symbol
from .vault import Vault, VaultError

log = logging.getLogger(__name__)

__all__ = ["DeployStore", "DeployError", "Conflict", "NotFound", "config_hash", "account_identity", "ACCOUNT_IDENTITY",
           "code_state", "CODE_STATES", "DEFAULT_MODE", "PLATFORMS"]

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
    slot        TEXT NOT NULL DEFAULT '',
    own_terminal INTEGER NOT NULL DEFAULT 0,
    version     TEXT NOT NULL DEFAULT '',
    created     REAL NOT NULL,
    updated     REAL NOT NULL,
    by          TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS deployments_account ON deployments (account);
CREATE TABLE IF NOT EXISTS secret_sent (
    account  TEXT NOT NULL,
    agent    TEXT NOT NULL,
    rev      TEXT NOT NULL DEFAULT '',
    sent_rev TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (account, agent)
);
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
ACCOUNT_IDENTITY: dict[str, str] = {"mt5": MT5_IDENTITY}
DEFAULT_IDENTITY = "{login}"

#: Stavy, ktoré agent hlási v `applied.status`.
APPLIED_STATES = ("ok", "pending", "error", "removed")
#: Režim nového nasadenia, keď ho zadávateľ neurčí: pauznuté — zapne sa ručne v tabuľke.
DEFAULT_MODE = "paused"

#: Platformy účtov a čo k prihláseniu potrebujú. `password` = heslo ide na stroj (MT5); NinjaTrader sa
#: prihlasuje zapamätaným loginom NT, heslo účtu nemá. Terminál (MT5) je vec stroja — je v nasadení.
#: `slot` = platforma vie rozlíšiť viac nasadení tej istej stratégie na účte, symbole a TF (EA `InpSlot`);
#: `own_terminal` = nasadenie môže bežať vo vlastnom (portable) termináli.
PLATFORMS: dict[str, dict[str, Any]] = {
    "mt5": {"title": "MetaTrader 5", "password": True, "terminal": True, "slot": True, "own_terminal": True},
    "ninjatrader": {"title": "NinjaTrader 8", "password": False, "terminal": False, "slot": False, "own_terminal": False},
}

_ACCOUNT_FIELDS = ("platform", "label", "login", "server")
#: Zmena týchto polí (a hesla) = nové prihlásenie: nový `rev`, stroje inštanciu reštartujú.
_LOGIN_FIELDS = ("platform", "login", "server")
_ACCOUNT_COLS = ("id", *_ACCOUNT_FIELDS, "rev", "created", "updated", "by")
_DEPLOYMENT_COLS = ("id", "account", "agent", "strategy", "symbol", "tf", "profile", "config", "config_hash",
                    "mode", "active", "instance", "slot", "own_terminal", "version", "terminal", "portable", "route",
                    "created", "updated", "by")
#: Kľúč a id virtuálneho nasadenia MT5 exekútora (docs/ROUTING.md) — hub ho do `desired_for_agent` pridá sám
#: pre každý MT5 účet, na ktorý na danom stroji smeruje aspoň jedno nasadenie NinjaTradera.
EXECUTOR_STRATEGY = EXECUTOR_KIND
EXECUTOR_PREFIX = "exec-"
#: Stĺpce, ktoré pribudli po prvom vydaní — `ALTER TABLE` pri otvorení starého súboru.
_MIGRATIONS = (("deployments", "version", "TEXT NOT NULL DEFAULT ''"),
               ("deployments", "agent", "TEXT NOT NULL DEFAULT ''"),
               ("deployments", "terminal", "TEXT NOT NULL DEFAULT ''"),
               ("deployments", "portable", "INTEGER NOT NULL DEFAULT 0"),
               ("deployments", "slot", "TEXT NOT NULL DEFAULT ''"),
               ("deployments", "own_terminal", "INTEGER NOT NULL DEFAULT 0"),
               ("accounts", "rev", "TEXT NOT NULL DEFAULT ''"),
               ("accounts", "secret_enc", "TEXT"),
               ("accounts", "secret_rev", "TEXT NOT NULL DEFAULT ''"),
               ("deployments", "route", "TEXT NOT NULL DEFAULT ''"),
               ("accounts", "symbols", "TEXT NOT NULL DEFAULT ''"),
               ("accounts", "exec_symbols", "TEXT NOT NULL DEFAULT ''"))
#: Ako často sa smie prepísať nezmenený zoznam symbolov exekútora (len čas hlásenia) — nie v každom heartbeate.
EXEC_SYMBOLS_REFRESH = 300.0

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


def ticks_to_points(strategy: str, config: dict[str, Any], instrument_key: str | None) -> dict[str, Any]:
    """Prahy v tickoch (`SizeSpec` s jednotkou ``ticks``) prepočíta na body nástroja, na ktorom bol profil ladený.

    25. 10. 2026: IBS EZ ladená na MNQ (tick 0,25) bežala na MT5 US100.cash (tick 0,01) s `imbMaxDistTicks` 40 a
    `state2ConfirmTicks` 6 — jadro násobí ticky tickom nástroja, na ktorom beží, takže z 10 a 1,5 bodu bolo 0,4 a
    0,06 bodu a na CFD obchodovala iná stratégia, než aká prešla testom. V bodoch je config nezávislý od ticku
    platformy (NQ ↔ US100, ES ↔ US500, MGC ↔ XAU majú tie isté body); na nástroji ladenia sa nič nemení.
    Bez známeho nástroja ladenia ostane config bez zmeny."""
    from tradebot.core.types import INSTRUMENTS
    from tradebot.strategies import get_spec

    inst = INSTRUMENTS.get(instrument_key or "")
    if inst is None:
        return config
    size_fields = getattr(get_spec(strategy).config_cls, "SIZE_FIELDS", {}) or {}
    out = dict(config)
    for name, unit in size_fields.items():
        if name not in out:
            continue
        raw = out[name]
        default_unit = getattr(unit, "value", unit)
        if isinstance(raw, dict) and raw.get("unit") == "ticks":
            out[name] = {"value": round(float(raw["value"]) * inst.tick_size, 10), "unit": "abs"}
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool) and default_unit == "ticks":
            out[name] = {"value": round(float(raw) * inst.tick_size, 10), "unit": "abs"}
    out["_instrument"] = instrument_key
    return out


def _default_resolver(strategy: str, profile: str) -> dict[str, Any]:
    """Config z profilu stratégie: cez webapp (aj vlastné profily testera), inak z repozitára; prahy v tickoch
    v bodoch nástroja ladenia (`ticks_to_points`)."""
    try:
        from tester.webapp.repo_profiles import default_params  # type: ignore[import-not-found]

        cfg, key = default_params(profile, strategy)
        return ticks_to_points(strategy, cfg, key)
    except ImportError:
        from tradebot.core.config import load_profile
        from tradebot.core.types import INSTRUMENTS

        cfg, inst = load_profile(profile, strategy=strategy)
        key = next((k for k, v in INSTRUMENTS.items() if v is inst), None)
        return ticks_to_points(strategy, cfg.to_dict(), key)


class DeployStore:
    def __init__(self, path: Path | str, *, clock: Callable[[], float] = time.time,
                 config_resolver: Callable[[str, str], dict[str, Any]] | None = None,
                 strategy_check: Callable[[str], str] | None = None,
                 version: Callable[[], str] | str | None = None, vault: Vault | None = None) -> None:
        self.path = Path(path)
        #: Šifrovanie hesiel účtov — kľúč `secret.key` vedľa databázy (vznikne, keď príde prvé heslo).
        self.vault = vault or Vault(self.path.parent / "secret.key")
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
        pridane = set()
        for table, col, ddl in _MIGRATIONS:
            mena = {r["name"] for r in self._db.execute(f"PRAGMA table_info({table})")}
            if col not in mena:
                self._db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                pridane.add((table, col))
        self._db.execute("CREATE INDEX IF NOT EXISTS deployments_agent ON deployments (agent)")
        # Účet bol kedysi viazaný na stroj (`accounts.agent`, aj terminál MT5): nasadenia ho zdedia —
        # tie isté hodnoty, aké agent dostával doteraz, takže sa na strojoch nič nereštartuje.
        self._db.execute("UPDATE deployments SET agent = (SELECT a.agent FROM accounts a WHERE a.id = deployments.account) "
                         "WHERE agent = '' AND EXISTS (SELECT 1 FROM accounts a WHERE a.id = deployments.account "
                         "AND a.agent != '')")
        if ("deployments", "terminal") in pridane:
            self._db.execute("UPDATE deployments SET terminal = COALESCE((SELECT a.terminal FROM accounts a "
                             "WHERE a.id = deployments.account), ''), portable = COALESCE((SELECT a.portable FROM "
                             "accounts a WHERE a.id = deployments.account), 0)")
        # Heslo čakajúce po starom (čitateľné `secret_pending`) → šifrované; doručí sa znova.
        for r in self._db.execute("SELECT id, secret_pending FROM accounts WHERE secret_pending IS NOT NULL").fetchall():
            self._db.execute("UPDATE accounts SET secret_enc = ?, secret_rev = ?, secret_pending = NULL WHERE id = ?",
                             (self.vault.encrypt(r["secret_pending"]), uuid.uuid4().hex[:12], r["id"]))
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

    def _account_row(self, r: sqlite3.Row) -> dict[str, Any]:
        """Účet pre zoznamy: bez hesla — len či je uložené a ktoré stroje ho ešte neprevzali."""
        d = {k: r[k] for k in _ACCOUNT_COLS}
        d["symbols"] = json.loads(r["symbols"]) if r["symbols"] else {}
        ex = _exec_symbols_of(r)
        # symboly v Market Watch MT5 účtu z heartbeatu exekútora (hlási agent); None = ešte nikto nehlásil
        d["exec_symbols"] = ex["symbols"] if ex else None
        d["exec_symbols_at"] = ex["ts"] if ex else None
        d["secret"] = bool(r["secret_enc"])
        d["secret_waiting"] = self._secret_waiting(r) if r["secret_enc"] else []
        d["secret_pending"] = bool(d["secret_waiting"])
        return d

    def _account_agents(self, account_id: str) -> list[str]:
        """Stroje, ktoré účet používajú (majú s ním nasadenie, aj neaktívne — tam ešte niečo odstraňujú)."""
        return [r["agent"] for r in self._db.execute(
            "SELECT DISTINCT agent FROM deployments WHERE account = ? AND agent != '' ORDER BY agent", (account_id,))]

    def _routed_to(self, account_id: str, agent: str | None = None) -> list[sqlite3.Row]:
        """Nasadenia (aj neaktívne), ktorých route smeruje ordery na tento MT5 účet; s `agent` len z toho stroja."""
        out = []
        for r in self._db.execute("SELECT * FROM deployments WHERE route != '' ORDER BY created"):
            try:
                route = json.loads(r["route"])
            except ValueError:
                continue
            acc = route.get("account") if isinstance(route, dict) else None
            if acc == account_id and (agent is None or r["agent"] == agent):
                out.append(r)
        return out

    def _executor_applied(self, route: dict[str, Any] | None, agent: str) -> dict[str, Any] | None:
        """Čo agent naposledy hlásil k exekútoru MT5 účtu route (status/chyba grafu `TradeBotExecutor`)."""
        if not route or not route.get("account"):
            return None
        return self._applied_row(self._db.execute("SELECT * FROM applied WHERE deployment = ?",
                                                  (_executor_key(route["account"], agent),)).fetchone())

    def _secret_waiting(self, r: sqlite3.Row) -> list[str]:
        prevzate = {x["agent"] for x in self._db.execute(
            "SELECT agent FROM secret_sent WHERE account = ? AND rev = ?", (r["id"], r["secret_rev"]))}
        return [a for a in self._account_agents(r["id"]) if a not in prevzate]

    @staticmethod
    def _deployment_row(r: sqlite3.Row) -> dict[str, Any]:
        d = {k: r[k] for k in _DEPLOYMENT_COLS}
        d["config"] = json.loads(d["config"] or "{}")
        d["active"] = bool(d["active"])
        d["portable"] = bool(d["portable"])
        d["own_terminal"] = bool(d["own_terminal"])
        d["route"] = _route_of(d["id"], d["route"])
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
        """Všetky účty; s `agent` len tie, ktoré jeho nasadenia používajú."""
        sql, args = "SELECT * FROM accounts", []
        if agent:
            sql += " WHERE id IN (SELECT account FROM deployments WHERE agent = ?)"
            args.append(agent)
        with self._lock:
            rows = self._db.execute(sql + " ORDER BY id", args).fetchall()
            return [self._account_row(r) for r in rows]

    def account(self, account_id: str) -> dict[str, Any] | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
            return self._account_row(r) if r is not None else None

    def upsert_account(self, data: dict[str, Any], by: str, password: str | None = None) -> dict[str, Any]:
        """Nový účet (id zo `label`, keď chýba) alebo zmena existujúceho (podľa `id`).
        `password` sa uloží šifrované a odíde strojom, ktoré účet používajú; prázdny = nemení sa.
        Zmena prihlásenia (login, server, heslo) dá účtu nový `rev` — stroje inštancie reštartujú.
        `terminal`/`portable` v dátach sú pozostatok účtu viazaného na stroj a ignorujú sa; `agent` od starého
        klienta ostane len ako predvolený stroj pre nasadenie, ktoré stroj neurčí."""
        data = dict(data or {})
        with self._lock, self._db:
            now = self.clock()
            existing = self._db.execute("SELECT * FROM accounts WHERE id = ?", (data.get("id"),)).fetchone() \
                if data.get("id") else None
            if existing is None:
                platform = str(data.get("platform") or "").strip()
                if platform not in PLATFORMS:
                    raise DeployError(f"platforma účtu musí byť {' alebo '.join(PLATFORMS)}")
                if not str(data.get("login") or "").strip():
                    raise DeployError("účet potrebuje login (MT5 číslo účtu / NT meno účtu)")
                acc_id = str(data.get("id") or "").strip() or self._free_id(_slug(data.get("label") or data.get("login")))
                if acc_id != _slug(acc_id):
                    raise DeployError(f"id účtu {acc_id!r}: len malé písmená, číslice, '.', '-' a '_'")
                heslo = password if (password and PLATFORMS[platform]["password"]) else None
                row = {"id": acc_id, "platform": platform,
                       "label": str(data.get("label") or acc_id).strip(), "login": str(data["login"]).strip(),
                       "server": str(data.get("server") or "").strip(), "rev": uuid.uuid4().hex[:12],
                       "created": now, "updated": now, "by": by or ""}
                self._db.execute(
                    "INSERT INTO accounts (id, agent, platform, label, login, server, rev, created, updated, by, "
                    "secret_enc, secret_rev) VALUES (:id, :legacy_agent, :platform, :label, :login, :server, :rev, "
                    ":created, :updated, :by, :secret, :secret_rev)",
                    # `agent` od starého klienta: len predvolený stroj pre jeho nasadenie bez stroja
                    {**row, "legacy_agent": str(data.get("agent") or "").strip(),
                     "secret": self.vault.encrypt(heslo) if heslo else None,
                     "secret_rev": uuid.uuid4().hex[:12] if heslo else ""})
                self._audit(by, "account_create", account=acc_id,
                            new={**{k: v for k, v in row.items() if k != "rev"}, "password": bool(heslo)})
                if data.get("symbols"):
                    self._set_symbols(acc_id, data["symbols"], by)
            else:
                acc_id = existing["id"]
                old = self._account_row(existing)
                sets: dict[str, Any] = {}
                for key in _ACCOUNT_FIELDS:
                    if key in data and data[key] is not None and str(data[key]).strip() != str(existing[key]):
                        sets[key] = str(data[key]).strip()
                if "platform" in sets:
                    if sets["platform"] not in PLATFORMS:
                        raise DeployError(f"platforma účtu musí byť {' alebo '.join(PLATFORMS)}")
                    if self._account_agents(acc_id):
                        raise Conflict("platforma účtu s nasadeniami sa nemení — sprav nový účet")
                    if self._routed_to(acc_id):
                        # exekútor by z neho ďalej robil `exec-…` a NT driver „inštanciu“ stratégie executor (audit H4)
                        raise Conflict("na účet smerujú ordery NinjaTrader nasadení — platforma sa nemení, sprav nový účet")
                if "login" in sets and not sets["login"]:
                    raise DeployError("login nesmie byť prázdny")
                platform = sets.get("platform") or existing["platform"]
                heslo = password if (password and PLATFORMS.get(platform, {}).get("password")) else None
                if heslo:
                    sets["secret_enc"] = self.vault.encrypt(heslo)
                    sets["secret_rev"] = uuid.uuid4().hex[:12]
                elif "platform" in sets and not PLATFORMS[platform]["password"]:
                    sets.update(secret_enc=None, secret_rev="")   # NinjaTrader heslo nemá
                if data.get("symbols") is not None:
                    try:
                        aliases = normalize_aliases(data["symbols"])
                    except RouteError as exc:
                        raise DeployError(str(exc)) from None
                    if aliases != old.get("symbols"):
                        self._set_symbols(acc_id, data["symbols"], by)
                if not sets:
                    return self._account_row(self._account_or_404(acc_id))
                if heslo or any(k in sets for k in _LOGIN_FIELDS):
                    sets["rev"] = uuid.uuid4().hex[:12]
                sets.update(updated=now, by=by or "")
                cols = ", ".join(f"{k} = ?" for k in sets)
                self._db.execute(f"UPDATE accounts SET {cols} WHERE id = ?", (*sets.values(), acc_id))
                zmena = {k: v for k, v in sets.items() if k in _ACCOUNT_FIELDS}
                if heslo:
                    zmena["password"] = True
                if zmena:
                    self._audit(by, "account_update", account=acc_id,
                                old={k: old.get(k) for k in zmena if k != "password"}, new=zmena)
                # identita účtu je v id inštancií — keď sa zmení login/server/platforma, prepočítať
                if any(k in sets for k in _LOGIN_FIELDS):
                    self._recompute_instances(acc_id)
            return self._account_row(self._account_or_404(acc_id))

    def _set_symbols(self, acc_id: str, raw: Any, by: str) -> None:
        """Aliasy symbolov MT5 účtu pre route (`{"NAS100": "US100.cash"}`) — nové prihlásenie to nie je (bez `rev`)."""
        try:
            aliases = normalize_aliases(raw)
        except RouteError as exc:
            raise DeployError(str(exc)) from None
        old = self._db.execute("SELECT symbols FROM accounts WHERE id = ?", (acc_id,)).fetchone()
        self._db.execute("UPDATE accounts SET symbols = ?, updated = ?, by = ? WHERE id = ?",
                         (json.dumps(aliases, ensure_ascii=False, sort_keys=True) if aliases else "", self.clock(),
                          by or "", acc_id))
        self._audit(by, "account_update", account=acc_id,
                    old={"symbols": json.loads(old["symbols"]) if old and old["symbols"] else {}}, new={"symbols": aliases})

    def _free_id(self, base: str) -> str:
        cand, n = base, 1
        while self._db.execute("SELECT 1 FROM accounts WHERE id = ?", (cand,)).fetchone() is not None:
            n += 1
            cand = f"{base}-{n}"
        return cand

    def _recompute_instances(self, account_id: str) -> None:
        acc = dict(self._account_or_404(account_id))
        for r in self._db.execute("SELECT id, symbol, tf, strategy, slot FROM deployments WHERE account = ?", (account_id,)):
            inst = instance_id(acc["platform"], account_identity(acc), instance_symbol(acc["platform"], r["symbol"]),
                               int(r["tf"]), r["strategy"], r["slot"] or "")
            self._db.execute("UPDATE deployments SET instance = ? WHERE id = ?", (inst, r["id"]))

    def delete_account(self, account_id: str, by: str, force: bool = False) -> dict[str, Any]:
        """Zmaže účet — len keď na ňom nič nebeží (žiadne aktívne nasadenie na žiadnom stroji).
        Neaktívne nasadenia (odstránené z platformy, čakajúce na zmazanie) sa zmažú s ním. `force`
        aktívne nasadenia **neprebíja**: najprv ich treba odstrániť (agent ich zastaví na platforme)."""
        with self._lock, self._db:
            old = self._account_row(self._account_or_404(account_id))
            bezi = [f"{r['strategy']} {r['symbol']} {r['tf']}m na {r['agent'] or '?'}" for r in self._db.execute(
                "SELECT strategy, symbol, tf, agent FROM deployments WHERE account = ? AND active = 1 ORDER BY created",
                (account_id,))]
            if bezi:
                raise Conflict(f"na účte {account_id!r} ešte beží: {', '.join(bezi)} — najprv tie nasadenia odstráň")
            # aj neaktívne: po reaktivácii by nasadenie bez exekútora obchodovalo na účte NinjaTradera
            smeruju = [f"{r['strategy']} {r['symbol']} {r['tf']}m ({r['id']}{'' if r['active'] else ', neaktívne'})"
                       for r in self._routed_to(account_id)]
            if smeruju:
                raise Conflict(f"na MT5 účet {account_id!r} smerujú ordery: {', '.join(smeruju)} — najprv tie nasadenia zmaž")
            deps = [r["id"] for r in self._db.execute("SELECT id FROM deployments WHERE account = ?", (account_id,))]
            for dep_id in deps:
                self._db.execute("DELETE FROM applied WHERE deployment = ?", (dep_id,))
                self._db.execute("DELETE FROM deployments WHERE id = ?", (dep_id,))
                self._audit(by, "deployment_delete", account=account_id, deployment=dep_id, old={"with_account": True})
            self._db.execute("DELETE FROM secret_sent WHERE account = ?", (account_id,))
            prefix = _executor_key(account_id, "")
            self._db.execute("DELETE FROM applied WHERE substr(deployment, 1, ?) = ?", (len(prefix), prefix))
            self._db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            self._audit(by, "account_delete", account=account_id, old=old)
            return {"id": account_id, "deleted": True, "deployments": deps}

    # -- nasadenia ------------------------------------------------------------- #

    def deployments(self, agent: str | None = None, account: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT d.*, a.platform AS _platform FROM deployments d JOIN accounts a ON a.id = d.account"
        where, args = [], []
        if agent:
            where.append("d.agent = ?"); args.append(agent)
        if account:
            where.append("d.account = ?"); args.append(account)
        if where:
            sql += " WHERE " + " AND ".join(where)
        with self._lock:
            rows = self._db.execute(sql + " ORDER BY d.agent, d.account, d.created", args).fetchall()
            out = []
            for r in rows:
                d = self._deployment_row(r)
                d["platform"] = r["_platform"]
                d["applied"] = self._applied_row(
                    self._db.execute("SELECT * FROM applied WHERE deployment = ?", (d["id"],)).fetchone())
                if d["route"]:
                    d["executor"] = self._executor_applied(d["route"], d["agent"])
                out.append(d)
        return out

    def deployment(self, dep_id: str) -> dict[str, Any] | None:
        with self._lock:
            r = self._db.execute("SELECT d.*, a.platform AS _platform FROM deployments d "
                                 "JOIN accounts a ON a.id = d.account WHERE d.id = ?", (dep_id,)).fetchone()
            if r is None:
                return None
            d = self._deployment_row(r)
            d["platform"] = r["_platform"]
            d["applied"] = self._applied_row(
                self._db.execute("SELECT * FROM applied WHERE deployment = ?", (dep_id,)).fetchone())
            if d["route"]:
                d["executor"] = self._executor_applied(d["route"], d["agent"])
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
        slot = str(data.get("slot") or "").strip()
        if slot and not SLOT_RE.match(slot):
            raise DeployError(f"slot {slot!r}: písmená, číslice a pomlčka, najviac 16 znakov (napr. b, agresivny)")
        own_terminal = bool(data.get("own_terminal"))
        config = self._resolve_config(strategy, profile, data.get("config"))
        with self._lock, self._db:
            acc = dict(self._account_or_404(account_id))
            schopnosti = PLATFORMS.get(acc["platform"], {})
            route_in = data.get("route")
            route = None
            if route_in not in (None, "", {}):
                mt5_id = str(route_in.get("account") or "").strip() if isinstance(route_in, dict) else ""
                mt5 = self.account(mt5_id) if mt5_id else None
                try:
                    route = normalize_route(route_in, nt_symbol=symbol, nt_platform=acc["platform"], mt5_account=mt5)
                except RouteError as exc:
                    raise DeployError(str(exc)) from None
                self._check_exec_symbol(mt5, route)
            if slot and not schopnosti.get("slot"):
                raise DeployError(f"slot vie len MetaTrader 5 — účet {account_id!r} je {acc['platform']}")
            if own_terminal and not schopnosti.get("own_terminal"):
                raise DeployError(f"vlastný terminál vie len MetaTrader 5 — účet {account_id!r} je {acc['platform']}")
            # stroj z nasadenia; starý klient ho neposiela — vtedy stroj, na ktorý bol účet kedysi viazaný
            agent = str(data.get("agent") or "").strip() or str(acc.get("agent") or "").strip()
            if not agent:
                raise DeployError("nasadenie potrebuje stroj (agenta), na ktorom má bežať")
            terminal, portable = "", 0
            if schopnosti.get("terminal") and not own_terminal:
                terminal = str(data.get("terminal") or "").strip()
                portable = 1 if data.get("portable") else 0
                # jeden účet = jeden spoločný terminál na stroji: ďalšie nasadenie musí ísť do toho istého
                # (nasadenia s vlastným terminálom sa nepočítajú — každé má svoju portable kópiu)
                iny = self._db.execute("SELECT terminal, portable FROM deployments WHERE account = ? AND agent = ? "
                                       "AND active = 1 AND own_terminal = 0 AND (terminal != ? OR portable != ?) LIMIT 1",
                                       (account_id, agent, terminal, portable)).fetchone()
                if iny is not None:
                    raise Conflict(f"účet {account_id!r} už na stroji {agent} beží v termináli "
                                   f"{iny['terminal'] or 'nainštalovanom'}{' (portable)' if iny['portable'] else ''} — "
                                   f"ďalšie nasadenie musí ísť do toho istého")
            inst = instance_id(acc["platform"], account_identity(acc), instance_symbol(acc["platform"], symbol), tf, strategy,
                               slot)
            dup = self._db.execute("SELECT id, agent, profile, active, slot FROM deployments WHERE instance = ?",
                                   (inst,)).fetchone()
            if dup is not None:
                raise Conflict(self._duplicate_text(dup, agent, strategy, symbol, tf, inst, bool(schopnosti.get("slot"))))
            now = self.clock()
            dep_id = str(data.get("id") or "").strip() or uuid.uuid4().hex[:12]
            row = {"id": dep_id, "account": account_id, "agent": agent, "strategy": strategy, "symbol": symbol,
                   "tf": tf, "profile": profile, "config": json.dumps(config, ensure_ascii=False, sort_keys=True),
                   "config_hash": config_hash(config), "mode": mode, "active": 1, "instance": inst,
                   "slot": slot, "own_terminal": 1 if own_terminal else 0,
                   "version": str(data.get("version") or "").strip() or self.version(),
                   "terminal": terminal, "portable": portable,
                   "route": json.dumps(route, ensure_ascii=False, sort_keys=True) if route else "",
                   "created": now, "updated": now, "by": by or ""}
            self._db.execute(
                "INSERT INTO deployments (id, account, agent, strategy, symbol, tf, profile, config, config_hash, "
                "mode, active, instance, slot, own_terminal, version, terminal, portable, route, created, updated, by) "
                "VALUES (:id, :account, :agent, :strategy, :symbol, :tf, :profile, :config, :config_hash, :mode, "
                ":active, :instance, :slot, :own_terminal, :version, :terminal, :portable, :route, :created, :updated, "
                ":by)", row)
            self._audit(by, "deployment_create", account=account_id, deployment=dep_id,
                        new={k: v for k, v in row.items() if k != "config"})
        return self.deployment(dep_id)  # type: ignore[return-value]

    @staticmethod
    def _check_exec_symbol(mt5: dict[str, Any] | None, route: dict[str, Any] | None) -> None:
        """Symbol route musí byť medzi symbolmi, ktoré exekútor MT5 účtu hlási (Market Watch); kým ich nikto
        nehlásil, kontrola nie je (docs/ROUTING.md, audit H5)."""
        known = (mt5 or {}).get("exec_symbols")
        if not route or not known or route.get("symbol") in known:
            return
        sym = str(route.get("symbol") or "")
        podobne = [k for k in known if k.lower() == sym.lower()]
        rada = f" — myslel si {podobne[0]}?" if podobne else (
            " — skontroluj meno, alebo ho pridaj do Market Watch terminálu účtu (exekútor hlási len symboly v ňom)")
        raise DeployError(f"MT5 účet {mt5.get('id')!r} nemá symbol {sym!r} (exekútor hlási "
                          f"{len(known)} symbolov){rada}")

    @staticmethod
    def _duplicate_text(dup: sqlite3.Row, agent: str, strategy: str, symbol: str, tf: int, inst: str,
                        slots: bool = False) -> str:
        """Prečo druhé nasadenie tej istej inštancie nejde a čo s tým — inštancia nepozná stroj, ten istý účet
        so stratégiou na symbole a TF by na dvoch strojoch obchodoval dvakrát a spool by sa zlial do jedného.
        Druhé nasadenie s iným profilom ide so slotom (platforma, ktorá ho vie)."""
        co = f"{strategy} {symbol} {tf}m{' slot ' + dup['slot'] if dup['slot'] else ''} na tomto účte"
        slot_rada = (" Ak má bežať popri ňom (napr. s iným profilom), zadaj nasadeniu slot (napr. b)." if slots else "")
        kde = f"na stroji {dup['agent'] or '?'}"
        if not dup["active"]:
            rada = (f"je odstránené {kde} (nasadenie {dup['id']}) — v tabuľke Nasadenia ho zmaž (tlačidlo „zmazať“) "
                    f"a potom nasaď znova")
        elif dup["agent"] == agent:
            rada = (f"už beží {kde} (nasadenie {dup['id']}, profil {dup['profile'] or '—'}) — iný profil mu zmeníš "
                    f"v tabuľke Nasadenia.{slot_rada}")
        else:
            rada = (f"už beží {kde} (nasadenie {dup['id']}, profil {dup['profile'] or '—'}) — na jednom účte môže bežať "
                    f"len raz, inak by obchodovalo dvakrát; na presun na stroj {agent} ho najprv v tabuľke Nasadenia "
                    f"odstráň (a po potvrdení strojom {dup['agent'] or '?'} zmaž), potom nasaď tu.{slot_rada}")
        return f"{co} {rada} (inštancia {inst})"

    def update_deployment(self, dep_id: str, patch: dict[str, Any], by: str) -> dict[str, Any]:
        """Meniť sa smie `mode`, `profile` (+`config`, inak sa dopočíta z profilu), `active` a `version`
        (commit, na ktorom zadávateľ zmenu urobil); účet, stratégia, symbol a TF sú identita inštancie,
        stroj a terminál miesto behu — na iné treba nové nasadenie."""
        patch = dict(patch or {})
        zakazane = [k for k in ("account", "agent", "strategy", "symbol", "tf", "instance", "terminal", "portable",
                                "slot", "own_terminal", "route")
                    if k in patch and patch[k] is not None]
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
                route = old.get("route")
                if sets["active"] and isinstance(route, dict) and route.get("error"):
                    raise Conflict(str(route["error"]))
                if sets["active"] and isinstance(route, dict) and route.get("account"):
                    acc = self._db.execute("SELECT id, platform FROM accounts WHERE id = ?", (route["account"],)).fetchone()
                    if acc is None or acc["platform"] != "mt5":
                        raise Conflict(f"nasadenie smeruje ordery na MT5 účet {route['account']!r}, ktorý v hube "
                                       f"{'nie je' if acc is None else 'už nie je MT5'} — bez exekútora sa neaktivuje")
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
        zmazať sa dá, až keď to agent potvrdil (`applied` `removed` po deaktivácii) — alebo s `force`.
        Potvrdené `ok` = agent graf drží pre otvorenú pozíciu → `Conflict` s radou (flatten, alebo force)."""
        with self._lock, self._db:
            old = self._deployment_row(self._deployment_or_404(dep_id))
            applied = self._applied_row(
                self._db.execute("SELECT * FROM applied WHERE deployment = ?", (dep_id,)).fetchone())
            po_zmene = applied is not None and float(applied["ts"]) >= float(old["updated"])
            potvrdene = po_zmene and applied["status"] == "removed"
            if not force and not old["active"] and po_zmene and applied["status"] == "ok":
                # agent vypnuté nasadenie potvrdil, ale z platformy neodstránil: inštancia má otvorenú pozíciu a graf
                # drží v pauze (`Reconciler._hold_open`), kým sa nezavrie
                raise Conflict(f"nasadenie {old['symbol']} {old['tf']}m ({old['strategy']}) má otvorenú pozíciu — agent ho "
                               "drží na platforme, kým sa nezavrie; najprv flatten a potom zmazať, alebo zmazať aj s "
                               "otvorenou pozíciou (force)")
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
        """Celý požadovaný stav jedného agenta do heartbeatu: jeho nasadenia (s `config`, aj neaktívne —
        tie má z platformy odstrániť) a účty, ktoré používajú. Účet nesie terminál MT5 z nasadení na tomto
        stroji, `rev` (verzia prihlásenia) a `secret`, kým stroj aktuálnu verziu hesla nepotvrdil."""
        with self._lock, self._db:
            deps = [self._deployment_row(r) for r in self._db.execute(
                "SELECT * FROM deployments WHERE agent = ? ORDER BY account, created", (agent,))]
            deps += self._executors(agent, deps)
            accs = []
            for acc_id in sorted({d["account"] for d in deps}):
                r = self._db.execute("SELECT * FROM accounts WHERE id = ?", (acc_id,)).fetchone()
                if r is None:
                    continue
                a: dict[str, Any] = {k: r[k] for k in ("id", "platform", "label", "login", "server", "rev")}
                vlastne = [d for d in deps if d["account"] == acc_id]
                # terminál účtu = spoločný terminál; nasadenia s vlastným terminálom ho neurčujú
                spolocne = [d for d in vlastne if not d["own_terminal"]] or vlastne
                miesto = next((d for d in spolocne if d["active"]), spolocne[0])
                a["terminal"], a["portable"] = miesto["terminal"], miesto["portable"]
                if r["secret_enc"]:
                    sent = self._db.execute("SELECT rev FROM secret_sent WHERE account = ? AND agent = ?",
                                            (acc_id, agent)).fetchone()
                    if sent is None or sent["rev"] != r["secret_rev"]:
                        try:
                            a["secret"] = self.vault.decrypt(r["secret_enc"])
                        except VaultError as exc:
                            a["secret_error"] = str(exc)
                        else:
                            self._db.execute(
                                "INSERT INTO secret_sent (account, agent, rev, sent_rev) VALUES (?, ?, '', ?) "
                                "ON CONFLICT(account, agent) DO UPDATE SET sent_rev = excluded.sent_rev",
                                (acc_id, agent, r["secret_rev"]))
                accs.append(a)
        return {"accounts": accs, "deployments": deps}

    def _executors(self, agent: str, deps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Route nasadení NinjaTradera tohto stroja: doplní im `route.to` (id exekútora z prihlásenia MT5 účtu)
        a pre každý MT5 účet, na ktorý smerujú, vráti virtuálne nasadenie exekútora (jeden graf
        `TradeBotExecutor` na účet). Aktívne je, kým naň smeruje aspoň jedno aktívne nasadenie; terminál
        z vlastných nasadení MT5 účtu na tomto stroji, inak nainštalovaný."""
        targets: dict[str, dict[str, Any]] = {}
        for d in deps:
            route = d.get("route")
            if not route:
                continue
            r = self._db.execute("SELECT * FROM accounts WHERE id = ?", (route.get("account"),)).fetchone()
            if r is None:
                continue
            route["to"] = executor_id(r["login"], r["server"])
            t = targets.setdefault(r["id"], {"row": r, "active": False, "first": None, "created": d["created"]})
            t["active"] = t["active"] or bool(d["active"])
            # graf exekútora na symbole najstaršej route: nová route (ani s abecedne menším symbolom či preklepom)
            # graf nezmení a spoločný terminál sa kvôli nej nereštartuje (audit H5)
            if route.get("symbol") and (t["first"] is None or d["created"] < t["first"][0]):
                t["first"] = (d["created"], route["symbol"])
        out = []
        for acc_id, t in sorted(targets.items()):
            r = t["row"]
            vlastne = [d for d in deps if d["account"] == acc_id and not d["own_terminal"] and d["active"]]
            terminal, portable = (vlastne[0]["terminal"], vlastne[0]["portable"]) if vlastne else ("", False)
            out.append({"id": EXECUTOR_PREFIX + acc_id, "account": acc_id, "agent": agent, "kind": EXECUTOR_KIND,
                        "strategy": EXECUTOR_STRATEGY, "symbol": t["first"][1] if t["first"] else "",
                        "tf": 1, "profile": EXECUTOR_STRATEGY, "config": {}, "config_hash": config_hash({}),
                        "mode": "enabled", "active": t["active"], "instance": executor_id(r["login"], r["server"]),
                        "slot": "", "own_terminal": False, "version": "", "terminal": terminal, "portable": portable,
                        "route": None, "created": t["created"], "updated": t["created"], "by": "hub"})
        return out

    def report_applied(self, agent: str, applied: list[dict[str, Any]] | None,
                       secret_ack: list[str] | None = None, exec_symbols: dict[str, Any] | None = None) -> int:
        """Agent hlási, čo k nasadeniam naozaj spravil, a ktoré heslá prevzal (platí verzia, ktorá mu
        naposledy odišla), a symboly exekútorov MT5 účtov (`{účet: [symbol, …]}` z ich heartbeatu). Cudzie
        nasadenia (iného agenta) a exekútory účtov, na ktoré z neho nič nesmeruje, sa ignorujú. Vráti počet
        prijatých hlásení nasadení."""
        n = 0
        with self._lock, self._db:
            now = self.clock()
            if isinstance(exec_symbols, dict):
                self._store_exec_symbols(agent, exec_symbols, now)
            for a in applied or []:
                dep_id = str((a or {}).get("deployment") or "")
                if not dep_id:
                    continue
                if dep_id.startswith(EXECUTOR_PREFIX):
                    # exekútor MT5 účtu nemá riadok v deployments: hlásenie sa drží pod účtom a strojom, aby chyba
                    # jeho grafu (chýba MT5 driver, terminál) bola vidno pri nasadeniach, ktoré naň smerujú (audit H6)
                    acc_id = dep_id[len(EXECUTOR_PREFIX):]
                    if not self._routed_to(acc_id, agent):
                        continue
                    dep_id = _executor_key(acc_id, agent)
                else:
                    r = self._db.execute("SELECT agent FROM deployments WHERE id = ?", (dep_id,)).fetchone()
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
                    "UPDATE secret_sent SET rev = sent_rev WHERE account = ? AND agent = ? AND sent_rev != '' "
                    "AND rev != sent_rev", (str(acc_id), agent))
                if cur.rowcount:
                    self._audit(agent, "secret_taken", account=str(acc_id))
        return n

    def _store_exec_symbols(self, agent: str, reported: dict[str, Any], now: float) -> None:
        for acc_id, names in reported.items():
            if not isinstance(names, list):
                continue
            r = self._db.execute("SELECT * FROM accounts WHERE id = ?", (str(acc_id),)).fetchone()
            if r is None or r["platform"] != "mt5" or not self._routed_to(r["id"], agent):
                continue
            symbols = sorted({str(x).strip() for x in names if str(x or "").strip()})[:5000]
            if not symbols:
                continue   # prázdny Market Watch (terminál ešte nenačítal) — známy zoznam neprepisovať
            old = _exec_symbols_of(r)
            if old and old["symbols"] == symbols and now - float(old.get("ts") or 0) < EXEC_SYMBOLS_REFRESH:
                continue
            self._db.execute("UPDATE accounts SET exec_symbols = ? WHERE id = ?",
                             (json.dumps({"symbols": symbols, "agent": agent, "ts": now}, ensure_ascii=False), r["id"]))

    def apply_overrides(self, agent: str, overrides: list[dict[str, Any]] | None) -> int:
        """Režimy, ktoré agent prepol lokálne (Telegram), do nasadení: aktívne nasadenie toho agenta s tou
        inštanciou dostane `mode`, ak ho hub od prepnutia (`ts`) sám nezmenil — novšia zmena na hube vyhráva
        a agent prekrytie zahodí. Vráti počet zmenených nasadení (audit `by` = `<kto>@<agent>`)."""
        n = 0
        for o in overrides or []:
            inst, mode = str((o or {}).get("instance") or ""), (o or {}).get("mode")
            try:
                ts = float(o.get("ts") or 0)
            except (TypeError, ValueError):
                continue
            if not inst or mode not in CONTROL_MODES:
                continue
            with self._lock:
                r = self._db.execute("SELECT id, mode, updated FROM deployments WHERE agent = ? AND instance = ? "
                                     "AND active = 1", (agent, inst)).fetchone()
            if r is None or r["mode"] == mode or float(r["updated"]) >= ts:
                continue
            self.update_deployment(r["id"], {"mode": mode}, by=f"{o.get('by') or 'telegram'}@{agent}")
            n += 1
        return n

    def agents(self) -> list[str]:
        """Stroje s aspoň jedným nasadením (aj pozastaveným) — obchodné stroje, hub im nepridelí výpočet."""
        with self._lock:
            rows = self._db.execute("SELECT DISTINCT agent FROM deployments WHERE agent != ''").fetchall()
        return sorted(r["agent"] for r in rows)

    def active_agents(self) -> list[str]:
        """Stroje, na ktorých je aspoň jedno aktívne nasadenie — tie stráži Telegram hubu."""
        with self._lock:
            rows = self._db.execute("SELECT DISTINCT agent FROM deployments WHERE active = 1 AND agent != ''").fetchall()
        return sorted(r["agent"] for r in rows)

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


def _route_of(dep_id: str, raw: str | None) -> dict[str, Any] | None:
    """Route zo stĺpca `route`. Poškodený JSON nezhodí celý požadovaný stav stroja a NIKDY nie je „bez route“
    (to by obchodovalo na účte NinjaTradera, audit H1): je to route s `error` — agent nasadenie nezapíše."""
    if not raw:
        return None
    try:
        route = json.loads(raw)
        if not isinstance(route, dict) or not route:
            raise ValueError("nie je objekt")
    except ValueError as exc:
        log.warning("deploy: nasadenie %s má poškodenú route v hube (%s)", dep_id, exc)
        return {"error": f"route nasadenia je v hube poškodená ({exc}) — ordery by išli na účet NinjaTradera, "
                         "nasadenie sa nezapisuje; zmaž ho a sprav nové"}
    return route


def _exec_symbols_of(r: sqlite3.Row) -> dict[str, Any] | None:
    """`{symbols, agent, ts}` — posledné hlásenie symbolov exekútora MT5 účtu, alebo None."""
    try:
        d = json.loads(r["exec_symbols"]) if r["exec_symbols"] else None
    except (ValueError, IndexError, KeyError):
        return None
    return d if isinstance(d, dict) and isinstance(d.get("symbols"), list) else None


def _executor_key(account_id: str, agent: str) -> str:
    """Kľúč hlásenia exekútora v `applied`: `exec-<účet>@<stroj>` (virtuálne nasadenie nemá riadok v deployments)."""
    return f"{EXECUTOR_PREFIX}{account_id}@{agent}"


def _check_strategy(key: str) -> str:
    """Kľúč stratégie z registra (aj starý alias → dnešný kľúč); neznámy je chyba vstupu."""
    if not key:
        raise DeployError("nasadenie potrebuje strategy")
    from tradebot.strategies import get_spec

    try:
        return get_spec(key).key
    except KeyError as exc:
        raise DeployError(str(exc)) from None
