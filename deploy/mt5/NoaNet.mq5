//+------------------------------------------------------------------+
//| NoaNet - NOA 1.0 (Noise Area) s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/csharp/TradeBot.Strategies/NoaNet`, |
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\NoaNet.mq5 a prelozit (F7); v terminali musi byt  |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| VWAP potrebuje skutocny objem burzy; na CFD je objem len aktivita tickov (VWAP je odhad).         |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\noanet alebo cesta.  |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "noanet"
#define TRADEBOT_DEFAULT_PROFILE "mnq_databento_5m"

#include <TradeBot/TradeBotEA.mqh>
