# Šablóna MultiCharts študie pre Range Breakout (konsolidacia kdekolvek na grafe) — skopíruj obsah do
# PowerLanguage .NET Editora (File → New → Signal, jazyk Python, názov ORB = trieda nižšie).
#
# Celá logika je v balíku `tradebot` (nainštaluje ho deploy/multicharts/scripts/setup.ps1).
# Trieda je v tvare, aký MultiCharts x Python vyžaduje: bez rodiča, metódy priamo v triede,
# len delegujú na balík. Stratégia nemá informatívny TF, na grafe stačí Data1.
#
# Profil sa prepína premennou prostredia TRADEBOT_PROFILE (predvolene "nas100_dukascopy_3m"
# z tradebot/strategies/range/configs), alebo natvrdo nižšie cez PROFILE.
# Ordery študie sa volajú tb_sl, tb_tp a tb_session_end.

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


class Range:
    PROFILE = None
    # PROFILE = "nas100_dukascopy_3m"
    HTF_CSV = None   # demo nemá informatívny TF; pole je tu len pre jednotný tvar šablóny
    NO_DRAW = False

    # Balík tradebot sa importuje až tu, nie na úrovni modulu: MultiCharts zdroják
    # overuje aj v procesoch, kde balík nemusí byť viditeľný. Študia je obyčajná
    # trieda bez rodiča ako v šablóne bety; všetko deleguje na RangeSignal.
    def _sig(self):
        s = getattr(self, "_tb", None)
        if s is None:
            from tradebot.strategies.range.multicharts import RangeSignal

            s = RangeSignal()
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
