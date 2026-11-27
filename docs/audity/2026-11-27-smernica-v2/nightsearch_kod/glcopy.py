"""Kópia výsledkov na plochu a do iCloudu. V Pythone, nie v sh: launchd úlohe macOS nedovolí sh/cp
zapisovať na plochu a do iCloudu, Python z .venv áno (ranná tabuľka do PRIEBEH sa tak zapisuje odjakživa)."""
from pathlib import Path
SRC = Path("/Users/martin/IBS/.nightsearch")
HOME = Path.home()
HEAD = ('<!doctype html>\n<html lang="sk"><head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width, initial-scale=1">\n')
WEBLOC = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
          '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict><key>URL</key>'
          '<string>https://mmkrissak-cmyk.github.io/tradebot-vysledky/</string></dict></plist>\n')
README = """TradeBot výsledky — testovanie podľa smernice (VWAP ORB, IBS Entry Zone, SPX sila, JSS, CRT + TBS)

• TradeBot výsledky.html — dashboard, otvor dvojklikom (kapitálová krivka, kalendár ziskov, štatistiky, obchody).
• TradeBot výsledky online — ten istý dashboard na webe, prihlásenie menom a heslom.
• Tabuľka – posledná.md — ranná tabuľka. Všetky dni sú v iCloude: SMERNICA-TESTOVANIA/PRIEBEH.

Aktualizuje sa každé ráno o 6:00. Profily, ktoré prešli smernicou, sú vo webapp (PREŠIEL SMERNICAMI).
"""
html = HEAD + (SRC / "dash" / "tradebot_vysledky.html").read_text() + "\n</html>\n"
for d in (HOME / "Desktop" / "TradeBot výsledky", HOME / "Library/Mobile Documents/com~apple~CloudDocs/TRADEBOT-VYSLEDKY"):
    d.mkdir(parents=True, exist_ok=True)
    (d / "TradeBot výsledky.html").write_text(html)
    (d / "TradeBot výsledky online.webloc").write_text(WEBLOC)
    (d / "Tabuľka – posledná.md").write_text((SRC / "GL_report.md").read_text())
    (d / "PRECITAJ_MA.txt").write_text(README)
(HOME / "Desktop" / "TradeBot výsledky – online.webloc").write_text(WEBLOC)
# dáta pre úpravy stránky z MacBooku (TRADEBOT-VYSLEDKY/UPRAVY-STRANKY, 16. 10. 2026)
_u = HOME / "Library/Mobile Documents/com~apple~CloudDocs/TRADEBOT-VYSLEDKY/UPRAVY-STRANKY"
_u.mkdir(parents=True, exist_ok=True)
(_u / "dashboard_data.json").write_text((SRC / "dash" / "dashboard_data.json").read_text())
print("ok")
