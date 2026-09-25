//+------------------------------------------------------------------+
//| ORBNet - Opening Range Breakout s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5              |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/OrbNet`,     |
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\ORBNet.mq5 a prelozit (F7); v terminali musi byt      |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| Profil: vstup „InpProfile" = nazov JSON z MQL5\Files\TradeBot\profiles\orbnet alebo cela cesta.   |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "orbnet"
#define TRADEBOT_DEFAULT_PROFILE "nas100_dukascopy_3m"   // CFD NAS100, ako emulátor MultiCharts

#include <TradeBot/TradeBotEA.mqh>
