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

__all__ = ["AnalyticsStore", "ANALYTICS_DIR", "POSUDOK_OTAZKY",
           "fingerprint", "zadanie"]

#: Koľko znakov z hlavičky ide do zoznamu. Celá veta je v detaile.
HEADLINE_CHARS = 300


class AnalyticsStore:
    """Súbor na záznam, meno = jeho id. Rovnaký tvar ako `RunStore`, len jednoduchší."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or ANALYTICS_DIR)

    def _path(self, an_id: str) -> Path:
        return self.root / f"{an_id}.json"

    def _next_seq(self) -> int:
        """O jedna viac než najvyššie poradové číslo v sklade."""
        najvyssie = 0
        for path in self.root.glob("*.json"):
            try:
                najvyssie = max(najvyssie,
                                int(json.loads(path.read_text(encoding="utf-8")).get("seq") or 0))
            except (json.JSONDecodeError, OSError, TypeError, ValueError):
                continue
        return najvyssie + 1

    def save(self, report: dict[str, Any], *, strategy: str, note: str = "",
             user: str = "") -> dict[str, Any]:
        """Uloží záver analytiky. Vráti hlavičku záznamu (bez rozdelení)."""
        self.root.mkdir(parents=True, exist_ok=True)
        teraz = datetime.now(timezone.utc)
        an_id = f"{teraz:%Y%m%d-%H%M%S}-{uuid4().hex[:4]}"
        zaznam = {
            "id": an_id,
            "created": teraz.isoformat(),
            # Poradové číslo, lebo hodiny nestačia: Windows dáva čas po ~15 ms krokoch,
            # takže dva záznamy uložené rýchlo po sebe majú ten istý `created` a zoznam
            # by ich zoradil náhodne.
            "seq": self._next_seq(),
            "strategy": strategy,
            "note": note,
            "user": user,
            "run_ids": [r.get("id") for r in (report.get("runs") or []) if r.get("id")],
            "pairs": report.get("pairs") or [],
            "trades": report.get("trades"),
            "break_even_pct": report.get("break_even_pct"),
            "winrate": report.get("winrate"),
            "headline": report.get("headline") or "",
            # Odtlačok čísel: posudok sa píše ku konkrétnej vzorke a musí byť vidieť,
            # keď sa od nej odtrhol.
            "numbers": fingerprint(report),
            "posudok": "",
            "posudok_stamp": "",
            "posudok_at": "",
            "posudok_user": "",
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

    def set_posudok(self, an_id: str, text: str, user: str = "") -> dict[str, Any] | None:
        """Pripíše posudok k záznamu. `None`, keď taký záznam nie je.

        Odtlačok sa berie **z uložených čísel**, nie z aktuálnych — posudok patrí k tomu,
        čo mal pisateľ pred očami.
        """
        zaznam = self.get(an_id)
        if zaznam is None:
            return None
        zaznam["posudok"] = text.strip()
        zaznam["posudok_stamp"] = zaznam.get("numbers") or ""
        zaznam["posudok_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        zaznam["posudok_user"] = user
        self._path(an_id).write_text(json.dumps(zaznam, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
        return summary(zaznam)

    def delete(self, an_id: str) -> bool:
        path = self._path(an_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list(self, strategy: str = "", limit: int = 50) -> list[dict[str, Any]]:
        """Hlavičky od najnovšej. Bez `strategy` sa vrátia všetky.

        Radí sa podľa času uloženia, nie podľa mena súboru: dva záznamy z tej istej
        sekundy sa v mene líšia len náhodnou príponou, takže by vyšli v ľubovoľnom
        poradí. Pri zhode času rozhodne poradové číslo, až potom čas súboru.
        """
        najdene: list[tuple[str, float, dict[str, Any]]] = []
        for path in self.root.glob("*.json"):
            try:
                zaznam = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if strategy and zaznam.get("strategy") != strategy:
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = 0.0
            najdene.append((str(zaznam.get("created") or ""),
                            int(zaznam.get("seq") or 0), mtime, summary(zaznam)))
        najdene.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return [x[3] for x in najdene[:limit]]


def summary(zaznam: dict[str, Any]) -> dict[str, Any]:
    """Hlavička do zoznamu — bez rozdelení, tie sú až v detaile."""
    return {k: v for k, v in zaznam.items() if k != "report"} | {
        "runs": len(zaznam.get("run_ids") or []),
        "headline": (zaznam.get("headline") or "")[:HEADLINE_CHARS],
        "has_posudok": bool((zaznam.get("posudok") or "").strip()),
        # Posudok napísaný k iným číslam nie je nepravdivý, len starý — a to musí byť vidieť.
        "posudok_stale": bool((zaznam.get("posudok") or "").strip())
                         and zaznam.get("posudok_stamp") != zaznam.get("numbers"),
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


# --------------------------------------------------------------------------- #
# posudok od AI
# --------------------------------------------------------------------------- #
#
# Čísla povedia, čo sa stalo. Nepovedia, čo z toho plynie — či je najhoršia skupina
# príležitosť alebo vlastnosť vzorky, čo tomu v tom istom výpise protirečí a čo pustiť
# ďalej. To je práca, ktorú spraví človek alebo AI nad hotovými číslami; ukladá sa
# k záznamu, aby sa k nej dalo vrátiť.
#
# Posudok patrí ku **konkrétnym číslam**, preto sa k nemu ukladá ich odtlačok. Keď sa
# analytika prepočíta na inej vzorke, starý text ostane (písať ho znova je práca), ale je
# označený za starý — inak by o mesiac nikto nevedel, o čom hovorí.

#: Na čo má posudok odpovedať. Zámerne to nie sú otázky na čísla — tie sú vo výpise.
POSUDOK_OTAZKY: tuple[str, ...] = (
    "**Čo je tu zistenie a čo je vlastnosť vzorky?** Ktoré číslo by vydržalo na iných "
    "dátach a ktoré vzniklo tým, že skupina má dvanásť obchodov.",
    "**Ktorá skupina sa oplatí odfiltrovať** — a ktorá je len iné nastavenie parametra? "
    "Filter má zmysel vtedy, keď sa dá poznať pri vstupe.",
    "**Čo tomu protirečí?** V tom istom výpise býva číslo, ktoré hovorí opak; napíš ktoré.",
    "**Čo otestovať ďalej** — konkrétny príkaz (`cli sweep`, `cli matrix`, `cli prop`, "
    "iné okno) a čo by jeho výsledok rozhodol.",
    "**Dá sa na tom stavať, alebo je to o ničom?** Odpoveď má byť jednoznačná; „ešte "
    "uvidíme“ platí len vtedy, keď je za ňou konkrétny test.",
)


def fingerprint(report: dict[str, Any]) -> str:
    """Odtlačok čísel, ku ktorým posudok patrí — aby bolo vidieť, keď sa rozišli."""
    import hashlib

    kusky = [str(report.get("strategy")), ",".join(report.get("pairs") or []),
             str(report.get("trades")), str(report.get("break_even_pct")),
             ",".join(sorted(r.get("id", "") for r in (report.get("runs") or [])))]
    return hashlib.sha1("|".join(kusky).encode("utf-8")).hexdigest()[:8]


def zadanie(report: dict[str, Any]) -> str:
    """Text, ktorý sa dá podať AI: čísla plus otázky, na ktoré má odpovedať."""
    from .. import analytics as an

    hlavicka = (f"Analytika stratégie {report.get('strategy')} nad "
                f"{report.get('trades')} obchodmi z {len(report.get('runs') or [])} behov "
                f"({', '.join(report.get('pairs') or []) or '—'}), break-even "
                f"{report.get('break_even_pct')} %.")
    # Tabuľka je pekná, ale zadanie nesmie padnúť na staršom zázname s iným tvarom —
    # posudok sa píše aj k tomu, čo je v histórii mesiace.
    try:
        tabulka = an.table(report)
    except (KeyError, TypeError, ValueError):
        tabulka = "\n".join(f"- {s_.get('title')}: {s_.get('note') or ''}"
                            for s_ in (report.get("splits") or []))
    casti = [hlavicka, "", report.get("headline") or "", "", tabulka, ""]
    for meno, kluc in (("Konfigurácia", "config"), ("Slabne edge?", "decay"),
                       ("Proti náhode", "nulltest"), ("Syntetický trh", "synthetic"),
                       ("Portfólio", "portfolio")):
        blok = report.get(kluc) or {}
        veta = blok.get("verdict") or blok.get("note")
        if veta:
            casti.append(f"{meno}: {veta}")
    casti += ["", "Odpovedz na tieto otázky, každú vlastným odsekom:"]
    casti += [f"{i}. {o}" for i, o in enumerate(POSUDOK_OTAZKY, 1)]
    return "\n".join(casti)
