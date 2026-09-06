# Šablóna MultiCharts študie pre IBS — skopíruj obsah do PowerLanguage .NET Editora.
#
#   File → New → Signal, jazyk Python.NET, potom sem vlož tento súbor.
#
# Zámerne je tu len toľko kódu, koľko MultiCharts naozaj potrebuje. Celá logika
# je v balíku `tradebot` (nainštaluje ho platforms/multicharts/scripts/setup.ps1),
# takže sa dá testovať bez MultiCharts a je zdieľaná s Freqtrade vetvou.
#
# NA GRAFE MUSIA BYŤ DVE DÁTOVÉ SÉRIE:
#   Data1 = graf (napr. MNQ 3m)
#   Data2 = detekčný TF (`zoneDetectionTF` z profilu, štandardne 5m)
# Bez Data2 nevznikne ani jedna SD zóna — študia to napíše do Output okna.
#
# Profil sa prepína premennou prostredia TRADEBOT_PROFILE (predvolene "multicharts_mnq_3m"
# z tradebot/configs/ibs), alebo natvrdo nižšie cez PROFILE (názov alebo cesta k JSON).
# Ordery študie sa volajú tb_sl, tb_tp a tb_session_end.

from tradebot.strategies.ibs.multicharts import IBSSignal


class IBS(IBSSignal):
    # PROFILE = "multicharts_mnq_3m"          # futures MNQ, 1:1 s TradingView nastaveniami
    # PROFILE = "golden_binance_btcusdt_3m"
    pass
