"""Webová aplikácia pre testerov stratégie.

    python -m tradebot.webapp            # http://127.0.0.1:8765

Tester si vo formulári nastaví parametre stratégie (všetkých ~110 Pine vstupov
zoskupených ako v TradingView plus rozšírenia portu), vyberie pár a obdobie, spustí
backtest a po dobehnutí vidí kartu s kľúčovými číslami, graf výnosnosti ako
v Strategy Testeri a zoznam obchodov. Každý beh sa uloží ako adresár JSON súborov
do `platforms/freqtrade/user_data/runs/`, ktorý sa commituje — história sa dá
pushovať a pullovať a nestratí sa. Behy sa dajú vyhľadávať podľa parametrov.

Moduly:
  pine_meta  — metadáta vstupov (titulky, skupiny, tooltipy, rozsahy) z Pine skriptu
  store      — ukladanie a vyhľadávanie behov
  runner     — fronta a spúšťanie Freqtrade backtestu v podprocese
  app        — FastAPI aplikácia a statická stránka
"""
