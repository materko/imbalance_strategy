"""Adaptér NinjaTrader 8 — generická NinjaScript stratégia nad C# jadrom TradeBota.

Na rozdiel od Freqtrade a MultiCharts adaptéra je tento celý v C# (`TradeBotStrategy.cs`):
NinjaTrader je .NET aplikácia a stratégie si prekladá sám. Spustiť vie **len stratégie, ktoré
majú jadro v C#** (`StrategySpec.csharp_dir`, v C# trieda s `[TradeBotEngine("kľúč")]`); menom
nepozná žiadnu — stratégia pre graf je tenký potomok v `deploy/ninjatrader/`.

Python tu robí len inštaláciu a kontrolu prekladu: `python -m tradebot.adapters.ninjatrader`.
"""
