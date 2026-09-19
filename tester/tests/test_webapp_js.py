"""Stránka sa nesmie rozbiť tichým odstránením funkcie.

Karta Analytika volá pri vykresľovaní pol tucta `*Html()` funkcií. Keď jedna z nich
zmizne (napríklad pri presúvaní blokov v súbore), stránka spočíta všetko správne a potom
nevykreslí **nič** — chyba je len v konzole prehliadača a v Pythone ju nič nechytí.
Tento test je preto lacná náhrada za lintera: každé volané meno musí byť aj definované.
"""

from __future__ import annotations

import re

from tradebot.core.paths import TESTER_DIR

JS_DIR = TESTER_DIR / "webapp" / "static" / "js"
INDEX_HTML = TESTER_DIR / "webapp" / "static" / "index.html"

#: Mená, ktoré poskytuje prehliadač alebo sú metódami — tie sa v súbore nedefinujú.
BUILTIN = {
    "Array", "Boolean", "Date", "Error", "JSON", "Math", "Number", "Object", "Promise",
    "RegExp", "Set", "String", "URLSearchParams", "AbortController", "Event", "Option",
    "fetch", "alert", "confirm", "prompt", "setTimeout", "clearTimeout", "setInterval",
    "clearInterval", "parseInt", "parseFloat", "isNaN", "encodeURIComponent",
    "decodeURIComponent", "requestAnimationFrame", "structuredClone", "queueMicrotask",
    "if", "for", "while", "switch", "catch", "return", "function", "typeof", "await",
    "new", "of", "in", "do", "else", "try", "throw", "delete", "void", "yield", "case",
}


def _scripts() -> list[str]:
    """Skripty stránky v poradí, v akom ich načíta `index.html`."""
    return re.findall(r'<script src="/static/js/([^"]+\.js)"', INDEX_HTML.read_text(encoding="utf-8"))


def _source() -> str:
    return "\n".join((JS_DIR / name).read_text(encoding="utf-8") for name in _scripts())


def test_index_nacita_kazdy_skript_prave_raz():
    """Skript, ktorý v `index.html` chýba, sa nenačíta — a jeho funkcie ticho chýbajú."""
    nacitane = _scripts()
    assert sorted(nacitane) == sorted(p.name for p in JS_DIR.glob("*.js"))
    assert len(nacitane) == len(set(nacitane))
    assert nacitane[0] == "core.js" and nacitane[-1] == "main.js"


def test_ziadne_globalne_meno_nie_je_v_dvoch_skriptoch():
    """Klasické skripty zdieľajú globálny priestor: `const x` v dvoch súboroch zhodí načítanie
    druhého (SyntaxError) a `function x` v dvoch potichu prepíše prvú verziu."""
    kde: dict[str, list[str]] = {}
    for name in _scripts():
        text = (JS_DIR / name).read_text(encoding="utf-8")
        for meno in re.findall(r"^(?:(?:async\s+)?function\s+|(?:const|let|var|class)\s+)([A-Za-z0-9_$]+)",
                               text, re.M):
            kde.setdefault(meno, []).append(name)
    dvojite = {m: s for m, s in kde.items() if len(s) > 1}
    assert not dvojite, f"definované vo viacerých skriptoch: {dvojite}"


def _defined(text: str) -> set[str]:
    """Mená definované v súbore — deklarácie funkcií aj funkcie priradené do premennej."""
    out = set(re.findall(r"^(?:async\s+)?function\s+([A-Za-z0-9_$]+)", text, re.M))
    out |= set(re.findall(r"^\s*(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(",
                          text, re.M))
    out |= set(re.findall(r"^\s*(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*[A-Za-z0-9_$]+\s*=>",
                          text, re.M))
    out |= set(re.findall(r"^\s*(?:const|let|var)\s+([A-Za-z0-9_$]+)", text, re.M))
    return out


def test_kazda_volana_html_funkcia_je_aj_definovana():
    """Presne toto padlo naživo: `portfolioHtml is not defined` po presune blokov."""
    text = _source()
    volane = set(re.findall(r"\b([A-Za-z0-9_$]*Html)\s*\(", text))
    chyba = sorted(volane - _defined(text) - BUILTIN)

    assert not chyba, f"volané, ale nedefinované: {', '.join(chyba)}"


def test_ziadna_funkcia_nie_je_definovana_dvakrat():
    """Dve definície toho istého mena znamenajú, že jedna verzia ticho nefunguje."""
    text = _source()
    mena = re.findall(r"^(?:async\s+)?function\s+([A-Za-z0-9_$]+)", text, re.M)
    dvojite = sorted({m for m in mena if mena.count(m) > 1})

    assert not dvojite, f"definované viackrát: {', '.join(dvojite)}"


def test_prvky_stranky_pouzite_v_kode_v_html_existuju():
    """`$("#nieco")` na prvok, ktorý v stránke nie je, je tichá chyba."""
    text, html = _source(), INDEX_HTML.read_text(encoding="utf-8")
    v_html = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
    # Časť prvkov vzniká až v JS (tlačidlá v tabuľkách, formulár prop výzvy), takže id
    # treba pozbierať aj zo šablón v kóde.
    v_html |= set(re.findall(r'id="([A-Za-z0-9_-]+)"', text))
    generovane = set(re.findall(r'id="\$\{p\}-([A-Za-z0-9_-]+)"', text))
    v_html |= {f"prop-{x}" for x in generovane} | {f"nprop-{x}" for x in generovane}

    hladane = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"\)', text))
    chyba = sorted(hladane - v_html)

    assert not chyba, f"kód hľadá prvky, ktoré v index.html nie sú: {', '.join(chyba)}"
