"""Freqtrade nacitava strategie z tohto adresara podla nazvu triedy.

Implementacia zije v `ibs/adapters/freqtrade/strategy.py`, aby bola verzionovana
spolu s jadrom a testovatelna aj bez Freqtrade. Tento subor je len ukazovatel.

POZOR - nestaci trieda naimportovat. Freqtrade resolver berie do uvahy len triedy,
ktorych `__module__` sa zhoduje s nazvom TOHTO suboru (viz IResolver._get_valid_object),
takze naimportovanu triedu treba este podedit. Preto ten prazdny subclass nizsie.

Profil sa prepina premennou prostredia IBS_PROFILE (default: golden_binance_btcusdt_3m; nazov z ibs/configs alebo cesta k JSON).
"""

from ibs.adapters.freqtrade.strategy import IBSImbalanceStrategy as _IBSImbalanceStrategy


class IBSImbalanceStrategy(_IBSImbalanceStrategy):
    pass
