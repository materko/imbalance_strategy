# Šablóna MultiCharts študie — skopíruj obsah do PowerLanguage .NET Editora.
#
#   File → New → Signal, jazyk Python.NET, potom sem vlož tento súbor.
#
# Zámerne je tu len toľko kódu, koľko MultiCharts naozaj potrebuje. Celá logika
# je v balíku `ibs` (nainštaluje ho platforms/multicharts/scripts/setup.ps1), takže
# sa dá testovať bez MultiCharts a je zdieľaná s Freqtrade vetvou.
#
# NA GRAFE MUSIA BYŤ DVE DÁTOVÉ SÉRIE:
#   Data1 = graf (napr. MNQ 3m)
#   Data2 = detekčný TF (`zoneDetectionTF` z profilu, štandardne 5m)
# Bez Data2 nevznikne ani jedna SD zóna — študia to napíše do Output okna.
#
# Profil sa prepína premennou prostredia IBS_PROFILE (predvolene "mnq_3m"),
# alebo natvrdo nižšie cez PROFILE.

from ibs.adapters.multicharts.signal import IBSSignal


class IBS(IBSSignal):
    # PROFILE = "mnq_3m"          # futures MNQ, 1:1 s TradingView nastaveniami
    # PROFILE = "btcusdt_3m_binance"
    pass
