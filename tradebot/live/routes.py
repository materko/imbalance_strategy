"""Smerovanie orderov nasadenia do MT5 exekútora (docs/ROUTING.md, fáza 4): mapovanie inštrumentov a kontrola route.

Stratégia beží v NinjaTraderi (dáta), ordery vykoná `TradeBotExecutor` v MT5 na tom istom stroji. Nasadenie
nesie `route`:

    {"via": "mt5", "account": "<id MT5 účtu v hube>", "symbol": "US100.cash", "price": "basis", "scale": 1.0,
     "qty": {"mode": "value"}}

Symbol u brokera sa skladá z troch vrstiev, každá prepíše predošlú:

1. predvolená tabuľka (`DEFAULT_CFD`) — koreň CME kontraktu → meno CFD (`MNQ` → `NAS100`);
2. aliasy brokera pri MT5 účte (`account.symbols`, napr. `{"NAS100": "US100.cash"}`);
3. `route.symbol` v nasadení.

Identita exekútora (`executor_id`) musí dať to isté, čo `TradeBot.Core.Bridge.ExecutorId` — podľa nej AddOn
nájde heartbeat exekútora a exekútor route, ktoré patria jemu.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["DEFAULT_CFD", "PRICE_MODES", "QTY_MODES", "RouteError", "executor_id", "cfd_symbol", "normalize_route",
           "normalize_aliases"]

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


def executor_id(login: str | int, server: str) -> str:
    """`mt5exec_<login>-<server>`, znaky mimo `[A-Za-z0-9._-]` → `-` (ako `Bridge.ExecutorId`)."""
    return _CLEAN.sub("-", f"mt5exec_{login}-{server or ''}")


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
    """Symbol u brokera a mierka pre futures NinjaTradera: tabuľka → alias účtu. `None` = nevieme."""
    base, scale = DEFAULT_CFD.get(_root(nt_symbol), (None, 1.0))
    aliases = aliases or {}
    if base is None:
        # alias môže byť napísaný priamo na koreň futures (`{"MNQ": "USTEC"}`)
        hit = aliases.get(_root(nt_symbol))
        return (hit, 1.0) if hit else (None, 1.0)
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
        if lots <= 0:
            raise RouteError("qty fixed potrebuje lots > 0 (loty na kontrakt)")
        qty["lots"] = lots
    return {"via": "mt5", "account": account, "symbol": symbol, "price": price, "scale": scale, "qty": qty}
