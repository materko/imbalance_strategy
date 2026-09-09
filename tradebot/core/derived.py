"""Evidencia sviečok, ktoré nevznikli sťahovaním, ale prepočtom z 1m.

Vyššie timeframy dopĺňajú dve miesta: `tester.timeframes` dopredu (pri štarte webapp)
a Freqtrade adaptér počas behu, keď mu súbor chýba. Oboje zapíše, čo vyrobilo, do
`data/tester/.derived.json` — a `tester.data_archive split` to potom preskočí.

Prečo to musí byť evidované: v gite majú byť len dáta, ktoré naozaj prišli z burzy alebo
z raw exportu. Dopočítaný timeframe sa dá kedykoľvek vyrobiť znova, ale v archíve by sa
už nedal odlíšiť od skutočných sviečok — a celý zmysel archívu je, že je to referencia.

Súbor je v jadre, nie v Testeri, lebo doň píše aj adaptér (produkt), a implementácia má
byť jedna. Cesty v ňom sú relatívne k adresáru, v ktorom leží.
"""

from __future__ import annotations

import json
from pathlib import Path

from .paths import DERIVED_MANIFEST

__all__ = ["MANIFEST", "derived", "forget", "remember"]

MANIFEST = DERIVED_MANIFEST


def derived(manifest: Path | None = None) -> list[Path]:
    """Súbory zapísané ako odvodené. Chýbajúci alebo pokazený zoznam = žiadne."""
    path = Path(manifest or MANIFEST)
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [path.parent / row for row in rows]


def _under(root: Path, paths: list[Path]) -> set[str]:
    """Cesty relatívne ku koreňu manifestu; čo je mimo neho, sa nezapisuje.

    Súbory vyrobené inam (`dukas_import --ft-datadir` do dočasného adresára, testy) nemá
    zmysel evidovať — `split` sa na ne aj tak nikdy nepozrie.
    """
    out: set[str] = set()
    for p in paths:
        try:
            out.add(Path(p).resolve().relative_to(root.resolve()).as_posix())
        except (ValueError, OSError):
            continue
    return out


def remember(made: list[Path] | list[str], manifest: Path | None = None) -> None:
    """Zapíše súbory ako odvodené — `data_archive split` ich potom preskočí."""
    _write(Path(manifest or MANIFEST), add=list(made))


def forget(restored: list[Path] | list[str], manifest: Path | None = None) -> None:
    """Zabudne na súbory, ktoré už odvodené nie sú.

    Volá to `data_archive merge`: čo príde z archívu, je zase originál z burzy, a keby
    ostalo označené za odvodené, `split` by neskoršiu aktualizáciu ticho nezaarchivoval.
    """
    _write(Path(manifest or MANIFEST), drop=list(restored))


def _write(path: Path, add: list | None = None, drop: list | None = None) -> None:
    root = path.parent
    known = _under(root, [p for p in derived(path) if p.exists()])
    known |= _under(root, list(add or []))
    known -= _under(root, list(drop or []))
    if not known:
        if path.exists():
            path.unlink()
        return
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "_comment": "Sviecky dopocitane z 1m (tester.timeframes alebo Freqtrade adapter). "
                        "Do gitu nejdu, `data_archive split` ich preskakuje.",
            "files": sorted(known),
        }, indent=2) + "\n",
        encoding="utf-8",
    )
