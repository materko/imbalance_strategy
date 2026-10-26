"""Smerovanie orderov nasadenia do MT5 exekútora (docs/ROUTING.md, fáza 4): mapovanie inštrumentov a kontrola route.

Stratégia beží v NinjaTraderi (dáta), ordery vykoná `TradeBotExecutor` v MT5 na tom istom stroji. Nasadenie
nesie `route`:

    {"via": "mt5", "account": "<id MT5 účtu v hube>", "symbol": "US100.cash", "price": "basis", "scale": 1.0,
     "qty": {"mode": "value"}}

Symbol u brokera sa skladá z troch vrstiev, každá prepíše predošlú:

1. predvolená tabuľka (`DEFAULT_CFD`) — koreň CME kontraktu → meno CFD (`MNQ` → `NAS100`);
2. aliasy brokera pri MT5 účte (`account.symbols`, napr. `{"NAS100": "US100.cash"}`, aj priamo na koreň
   futures `{"MNQ": "USTEC"}` — ten vyhrá nad tabuľkou);
3. `route.symbol` v nasadení.

Symbol sa vyrieši pri vytvorení nasadenia a uloží sa do route — neskoršia zmena aliasov účtu platí pre nové
nasadenia, bežiace route nemení (exekútor hľadá pozície route podľa jej symbolu a magic; zmena symbolu pod
otvorenou pozíciou by ju nechala bez správy).

Identita exekútora (`executor_id`) musí dať to isté, čo `TradeBot.Core.Bridge.ExecutorId` — podľa nej AddOn
nájde heartbeat exekútora a exekútor route, ktoré patria jemu.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

__all__ = ["DEFAULT_CFD", "PRICE_MODES", "QTY_MODES", "RouteError", "executor_id", "cfd_symbol", "normalize_route",
           "normalize_aliases", "bridge_root", "executor_symbols", "EXEC_HB_MAX_AGE"]

#: Koreň futures kontraktu (NinjaTrader `MasterInstrument.Name`) → meno CFD u väčšiny brokerov a mierka cien.
DEFAULT_CFD: dict[str, tuple[str, float]] = {
    "MNQ": ("NAS100", 1.0), "NQ": ("NAS100", 1.0),
    "MES": ("US500", 1.0), "ES": ("US500", 1.0),
    "MYM": ("US30", 1.0), "YM": ("US30", 1.0),
    "M2K": ("US2000", 1.0), "RTY": ("US2000", 1.0),
    "MGC": ("XAUUSD", 1.0), "GC": ("XAUUSD", 1.0),
    "M6E": ("EURUSD", 1.0), "6E": ("EURUSD", 1.0),
}
PRICE_MODES = ("basis", "same")
QTY_MODES = ("value", "fixed")

_CLEAN = re.compile(r"[^A-Za-z0-9._-]")


class RouteError(ValueError):
    """Neplatná route nasadenia (422 v API)."""


#: Heartbeat exekútora starší než toto (s) sa do hubu nehlási — symboly z neho môžu byť staré.
EXEC_HB_MAX_AGE = 600.0


def executor_id(login: str | int, server: str) -> str:
    """`mt5exec_<login>-<server>`, znaky mimo `[A-Za-z0-9._-]` → `-` — presne `Bridge.ExecutorId(long, string)`:
    login je tam číslo (`007` → `7`, medzery okolo preč), server sa berie ako je (veľkosť písmen ostáva) a znak
    mimo BMP je v C# dvojica UTF-16 znakov, teda dve pomlčky."""
    text = str(login).strip()
    if re.fullmatch(r"[+-]?[0-9]+", text):
        text = str(int(text))
    raw = f"mt5exec_{text}-{server or ''}"
    return "".join(ch if _CLEAN.fullmatch(ch) is None else ("--" if ord(ch) > 0xFFFF else "-") for ch in raw)


def _root(nt_symbol: str) -> str:
    """`MNQ 12-26` → `MNQ`."""
    return str(nt_symbol or "").strip().split(" ")[0].upper()


def normalize_aliases(raw: Any) -> dict[str, str]:
    """Aliasy symbolov MT5 účtu: `{"NAS100": "US100.cash"}`; prázdne hodnoty sa vynechajú."""
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise RouteError("symbols účtu musí byť objekt {\"NAS100\": \"US100.cash\", …}")
    out = {}
    for k, v in raw.items():
        k, v = str(k or "").strip(), str(v or "").strip()
        if k and v:
            out[k] = v
    return out


def cfd_symbol(nt_symbol: str, aliases: dict[str, str] | None = None) -> tuple[str | None, float]:
    """Symbol u brokera a mierka pre futures NinjaTradera: tabuľka → alias účtu. `None` = nevieme.
    Alias napísaný priamo na koreň futures (`{"MNQ": "USTEC"}`) vyhrá nad tabuľkou aj nad aliasom jej CFD."""
    root = _root(nt_symbol)
    base, scale = DEFAULT_CFD.get(root, (None, 1.0))
    aliases = aliases or {}
    if aliases.get(root):
        return aliases[root], scale
    if base is None:
        return None, 1.0
    return aliases.get(base, base), scale


def normalize_route(route: Any, *, nt_symbol: str, nt_platform: str, mt5_account: dict[str, Any] | None) -> dict[str, Any] | None:
    """Skontroluje a doplní route nasadenia. `None`/prázdne = ordery na účet nasadenia. Vráti uložiteľný tvar
    `{via, account, symbol, price, scale, qty}`; chyba = `RouteError` s textom pre človeka."""
    if route in (None, "", {}):
        return None
    if not isinstance(route, dict):
        raise RouteError("route musí byť objekt")
    via = str(route.get("via") or "mt5").strip()
    if via != "mt5":
        raise RouteError(f"route via {via!r}: podporované je len mt5")
    if nt_platform != "ninjatrader":
        raise RouteError("ordery do MT5 exekútora vie smerovať len nasadenie NinjaTradera (stratégia beží tam, MT5 vykonáva)")
    account = str(route.get("account") or "").strip()
    if not account:
        raise RouteError("route potrebuje MT5 účet (account)")
    if mt5_account is None:
        raise RouteError(f"MT5 účet {account!r} neexistuje")
    if mt5_account.get("platform") != "mt5":
        raise RouteError(f"účet {account!r} nie je MetaTrader 5")
    symbol = str(route.get("symbol") or "").strip()
    scale = route.get("scale")
    if not symbol:
        found, dflt_scale = cfd_symbol(nt_symbol, mt5_account.get("symbols") or {})
        if not found:
            raise RouteError(f"pre {nt_symbol} nepoznám symbol u MT5 brokera — zadaj ho (napr. US100.cash) "
                             f"alebo alias pri MT5 účte")
        symbol = found
        if scale in (None, ""):
            scale = dflt_scale
    try:
        scale = float(scale if scale not in (None, "") else 1.0)
    except (TypeError, ValueError):
        raise RouteError("scale musí byť číslo") from None
    if not math.isfinite(scale):
        raise RouteError("scale musí byť konečné číslo")
    if scale <= 0:
        raise RouteError("scale musí byť kladné")
    price = str(route.get("price") or "basis").strip()
    if price not in PRICE_MODES:
        raise RouteError(f"price musí byť {' alebo '.join(PRICE_MODES)}")
    qty_raw = route.get("qty") if isinstance(route.get("qty"), dict) else {}
    mode = str(qty_raw.get("mode") or "value").strip()
    if mode not in QTY_MODES:
        raise RouteError(f"qty.mode musí byť {' alebo '.join(QTY_MODES)}")
    qty: dict[str, Any] = {"mode": mode}
    if mode == "fixed":
        try:
            lots = float(qty_raw.get("lots") or 0)
        except (TypeError, ValueError):
            lots = 0.0
        if not math.isfinite(lots):
            raise RouteError("qty lots musí byť konečné číslo")
        if lots <= 0:
            raise RouteError("qty fixed potrebuje lots > 0 (loty na kontrakt)")
        qty["lots"] = lots
    return {"via": "mt5", "account": account, "symbol": symbol, "price": price, "scale": scale, "qty": qty}


def bridge_root() -> Path | None:
    """`Common/Files/TradeBot` terminálov MT5 (tam píše exekútor `exec/<id>.hb.json`) — to isté, čo
    `Bridge.DefaultRoot` (`TRADEBOT_BRIDGE_ROOT` ho presmeruje), inak Common MT5 drivera; `None` = MT5 tu nie je."""
    env = os.environ.get("TRADEBOT_BRIDGE_ROOT")
    if env:
        return Path(env)
    from tradebot.adapters.mt5.__main__ import find_common_files

    common = find_common_files()
    return common / "TradeBot" if common is not None else None


def executor_symbols(exec_id: str, root: Path | str | None = None, *, now: float | None = None,
                     max_age: float = EXEC_HB_MAX_AGE) -> list[str] | None:
    """Mená symbolov (Market Watch) z heartbeatu exekútora `exec/<exec_id>.hb.json`; `None`, keď súbor nie je,
    nedá sa prečítať alebo je starší než `max_age` s (podľa `t` v ňom). Nikdy nevyhodí výnimku."""
    try:
        base = Path(root) if root is not None else bridge_root()
        if base is None or not exec_id:
            return None
        hb = json.loads((base / "exec" / f"{exec_id}.hb.json").read_text(encoding="utf-8-sig"))
        t = float(hb.get("t") or 0) / 1000.0
        if (time.time() if now is None else now) - t > max_age:
            return None
        names = [str(x.get("name") or "").strip() for x in hb.get("symbols") or [] if isinstance(x, dict)]
        return sorted({n for n in names if n})
    except (OSError, ValueError, TypeError, AttributeError):
        return None
