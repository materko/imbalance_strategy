"""Adaptér MetaTrader 5 nad C# jadrom.

MT5 nie je .NET aplikácia, ale MQL5 vie importovať .NET assembly priamo (`#import "TradeBot.dll"`,
build 2400+): MetaEditor si sám vygeneruje obal pre verejné statické metódy s jednoduchými typmi.
Preto má jadro statickú fasádu `TradeBot.Core.StaticHost` (`csharp/TradeBot.Core/StaticHost.cs`)
a Expert Advisor v MQL5 (`TradeBotEA.mqh` + šablóna `deploy/mt5/<Meno>.mq5`) je len tretí
hostiteľ toho istého engine-u ako NinjaTrader a most do Freqtrade. Inštalácia: `__main__`.
"""
