# Šablóna MultiCharts študie pre IBS — skopíruj obsah do PowerLanguage .NET Editora.
#
#   File → New → Signal, jazyk Python, názov študie IBS (= trieda nižšie), potom sem
#   vlož tento súbor a skompiluj (F7). Po setup.ps1 treba MultiCharts reštartovať.
#
# Celá logika je v balíku `tradebot` (nainštaluje ho platforms/multicharts/scripts/setup.ps1),
# takže sa dá testovať bez MultiCharts a je zdieľaná s Freqtrade vetvou. Trieda nižšie
# je v tvare, aký MultiCharts x Python vyžaduje (ako jeho vlastná šablóna Strategy.PY):
# bez rodiča, metódy Create/CalcBar priamo v triede, len delegujú na balík.
#
# NA GRAFE MUSIA BYŤ DVE DÁTOVÉ SÉRIE:
#   Data1 = graf (napr. MNQ 3m)
#   Data2 = detekčný TF (`zoneDetectionTF` z profilu, štandardne 5m)
# Bez Data2 nevznikne ani jedna SD zóna — študia to napíše do Output okna.
# Graf: Time Zone Exchange, burza symbolu v pásme GMT (adaptér berie čas baru ako UTC).
#
# Profil sa prepína premennou prostredia TRADEBOT_PROFILE (predvolene "multicharts_mnq_3m"
# z tradebot/configs/ibs), alebo natvrdo nižšie cez PROFILE (názov alebo cesta k JSON).
# Ordery študie: vstupy tb_long_<n>/tb_short_<n> (meno konkrétneho orderu LONG_<uid> sa
# dosadí pri Send), výstupy tb_sl, tb_tp a tb_session_end.

import clr
clr.AddReference("System")
clr.AddReference("System.Drawing")
clr.AddReference("PLTypes")
clr.AddReference("PLStudiesProxy")
clr.AddReference("PLStudiesProxyPython")
clr.AddReference("PLBuiltInFunctions")
clr.AddReference("PLTradeManager")
clr.AddReference("ATCenterProxy.interop")
clr.AddReference("PLDataLoader")

from System import *
from System.Drawing import *
from PowerLanguage import *


class IBS:
    # None = profil z prostredia (TRADEBOT_PROFILE) alebo default stratégie
    PROFILE = None
    # PROFILE = "multicharts_mnq_3m"          # futures MNQ, 1:1 s TradingView nastaveniami
    # PROFILE = "golden_binance_btcusdt_3m"
    # PROFILE = r"C:/cesta/k/repu/docs/profily_archiv/ibs/nas100_dukas_3m.json"   # NAS100 CFD z Dukascopy
    # Záloha za Data2 (beta odmieta BarsOfData(2)): 1m Dukascopy CSV, z ktorého sa 5m poskladá.
    HTF_CSV = None
    # HTF_CSV = r"C:/dukas/NAS100_M1_10Y.csv"
    # Diagnostika: True vypne kreslenie (oddelí pády MultiCharts v kreslení od orderov).
    NO_DRAW = False

    # Balík tradebot sa importuje až tu, nie na úrovni modulu: MultiCharts zdroják
    # overuje aj v procesoch, kde balík nemusí byť viditeľný. Študia je obyčajná
    # trieda bez rodiča ako v šablóne bety; všetko deleguje na IBSSignal.
    def _sig(self):
        s = getattr(self, "_tb", None)
        if s is None:
            from tradebot.strategies.ibs.multicharts import IBSSignal

            s = IBSSignal()
            s.PROFILE = self.PROFILE
            s.HTF_CSV = self.HTF_CSV
            s.NO_DRAW = self.NO_DRAW
            self._tb = s
        return s

    def GetInputs(self):
        return self._sig().GetInputs()

    def GetInputValue(self, name):
        return self._sig().GetInputValue(name)

    def SetInputValue(self, name, value):
        self._sig().SetInputValue(name, value)

    def Create(self, ctx):
        self._sig().Create(ctx)

    def StartCalc(self):
        self._sig().StartCalc()

    def CalcBar(self):
        self._sig().CalcBar()

    def StopCalc(self):
        self._sig().StopCalc()

    def Destroy(self):
        self._sig().Destroy()

    def OnOrderRejected(self, action, category, lots, price, price2):
        self._sig().OnOrderRejected(action, category, lots, price, price2)
