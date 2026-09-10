"""História analytiky — čo sa nad ktorými behmi spočítalo a čo z toho vyšlo.

### Načo to je
Analytika sa počíta nad výberom behov a výsledok zmizne, len čo sa stránka obnoví.
Pritom je to presne ten typ zistenia, ku ktorému sa treba vrátiť: „minulý týždeň mi
vyšlo, že najhoršia skupina je poloha v rozsahu — platí to ešte?" Bez histórie sa to
nedá ani porovnať, ani nikomu ukázať.

Uloží sa **záver, nie obchody**: hlavička, verdikty testov a rozdelenia. Obchody ostávajú
v behoch, na ktoré sa záznam odkazuje `run_ids` — keby sa kopírovali sem, tá istá vec by
bola v repozitári dvakrát a súbor by mal desiatky megabajtov.

### Prečo per stratégia
Rovnako ako mriežky a matice: vlastnosti, parametre aj to, čo je „normálne", sú pri každej
stratégii iné, takže zliať ich do jedného zoznamu by znamenalo porovnávať neporovnateľné.
`list()` preto berie kľúč stratégie.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from tradebot.core.paths import ANALYTICS_DIR

__all__ = ["AnalyticsStore", "ANALYTICS_DIR"]

#: Koľko znakov z hlavičky ide do zoznamu. Celá veta je v detaile.
HEADLINE_CHARS = 300


class AnalyticsStore:
    """Súbor na záznam, meno = jeho id. Rovnaký tvar ako `RunStore`, len jednoduchší."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or ANALYTICS_DIR)

    def _path(self, an_id: str) -> Path:
        return self.root / f"{an_id}.json"

    def save(self, report: dict[str, Any], *, strategy: str, note: str = "",
             user: str = "") -> dict[str, Any]:
        """Uloží záver analytiky. Vráti hlavičku záznamu (bez rozdelení)."""
        self.root.mkdir(parents=True, exist_ok=True)
        teraz = datetime.now(timezone.utc)
        an_id = f"{teraz:%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        zaznam = {
            "id": an_id,
            "created": teraz.isoformat(),
            "strategy": strategy,
            "note": note,
            "user": user,
            "run_ids": [r.get("id") for r in (report.get("runs") or []) if r.get("id")],
            "pairs": report.get("pairs") or [],
            "trades": report.get("trades"),
            "break_even_pct": report.get("break_even_pct"),
            "winrate": report.get("winrate"),
            "headline": report.get("headline") or "",
            "report": _bez_obchodov(report),
        }
        self._path(an_id).write_text(json.dumps(zaznam, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        return summary(zaznam)

    def get(self, an_id: str) -> dict[str, Any] | None:
        path = self._path(an_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def delete(self, an_id: str) -> bool:
        path = self._path(an_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self, strategy: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Hlavičky od najnovšej. Bez `strategy` sa vrátia všetky."""
        out = []
        for path in sorted(self.root.glob("*.json"), reverse=True):
            try:
                zaznam = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if strategy and zaznam.get("strategy") != strategy:
                continue
            out.append(summary(zaznam))
            if len(out) >= limit:
                break
        return out


def summary(zaznam: dict[str, Any]) -> dict[str, Any]:
    """Hlavička do zoznamu — bez rozdelení, tie sú až v detaile."""
    return {k: v for k, v in zaznam.items() if k != "report"} | {
        "runs": len(zaznam.get("run_ids") or []),
        "headline": (zaznam.get("headline") or "")[:HEADLINE_CHARS],
    }


def _bez_obchodov(report: dict[str, Any]) -> dict[str, Any]:
    """Z reportu sa uloží všetko okrem toho, čo sa dá dopočítať z behov.

    Histogramy testu proti náhode a krivka portfólia sú desiatky kilobajtov na záznam
    a v detaile ich nepotrebujeme — to, čo z nich plynie, je vo verdikte.
    """
    out = dict(report)
    nt = out.get("nulltest")
    if isinstance(nt, dict) and isinstance(nt.get("nulls"), dict):
        out["nulltest"] = {**nt, "nulls": {k: {kk: vv for kk, vv in v.items()
                                               if kk not in ("histogram", "sample")}
                                           for k, v in nt["nulls"].items()}}
    pf = out.get("portfolio")
    if isinstance(pf, dict):
        out["portfolio"] = {k: v for k, v in pf.items() if k != "curve"}
    mc = out.get("montecarlo")
    if isinstance(mc, dict):
        out["montecarlo"] = {k: v for k, v in mc.items() if k != "hist"}
    return out
