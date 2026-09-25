//+------------------------------------------------------------------+
//| IBSNet - IBS Imbalance Breakout s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5              |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/IbsNet`,     |
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\IBSNet.mq5 a prelozit (F7); v terminali musi byt      |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe   |
//| (napr. M3); informativny TF zon (`zoneDetectionTF` z profilu) si cita sam cez CopyRates.          |
//| Profil: vstup „InpProfile" = nazov JSON z MQL5\Files\TradeBot\profiles\ibsnet alebo cela cesta.   |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "ibsnet"
#define TRADEBOT_DEFAULT_PROFILE "multicharts_mnq_3m"   // futures MNQ, 1:1 s nastaveniami z TradingView

#include <TradeBot/TradeBotEA.mqh>
