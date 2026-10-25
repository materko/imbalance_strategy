//+------------------------------------------------------------------+
//| NyVaEsNet - NY VA BREAKOUT ES s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`csharp/TradeBot.Strategies/NyVaNet`, |
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\NyVaEsNet.mq5 a prelozit (F7); v terminali musi byt  |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| Volume profile prvej hodiny NY potrebuje skutocny objem burzy (ES / MES); na CFD nie.            |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\nyvaesnet alebo cesta.  |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "nyvaesnet"
#define TRADEBOT_DEFAULT_PROFILE "PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1"

#include <TradeBot/TradeBotEA.mqh>
