//+------------------------------------------------------------------+
//| IbRetNet - IB RETRACE 1.0 s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibret/ports/csharp`,|
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\IbRetNet.mq5 a prelozit (F7); v terminali musi byt   |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| IB 9:30-10:30 New York, cas servera prepocita adapter.                                            |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\ibretnet alebo cesta.    |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "ibretnet"
#define TRADEBOT_DEFAULT_PROFILE "mnq_databento_5m"

#include <TradeBot/TradeBotEA.mqh>
