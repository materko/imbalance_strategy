# Šablóna MultiCharts študie pre Demo Donchian Breakout — skopíruj obsah do
# PowerLanguage .NET Editora (File → New → Signal, jazyk Python.NET).
#
# Celá logika je v balíku `tradebot` (nainštaluje ho platforms/multicharts/scripts/setup.ps1).
# Stratégia nemá informatívny TF, na grafe stačí Data1.
#
# Profil sa prepína premennou prostredia TRADEBOT_PROFILE (predvolene "binance_btcusdt_5m"
# z tradebot/configs/demo_breakout), alebo natvrdo nižšie cez PROFILE.
# Ordery študie sa volajú tb_sl, tb_tp a tb_session_end.

from tradebot.strategies.demo_breakout.multicharts import DemoBreakoutSignal


class DemoBreakout(DemoBreakoutSignal):
    # PROFILE = "binance_btcusdt_5m"
    pass
