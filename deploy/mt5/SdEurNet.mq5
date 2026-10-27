//+------------------------------------------------------------------+
//| SdEurNet - SD ZONY EURUSD s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/sdeur/csharp`,|
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\SdEurNet.mq5 a prelozit (F7); v terminali musi byt  |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| Futures 6E / M6E; na CFD EURUSD prahy v ATR sedia aj bez prepoctu.                            |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\sdeurnet alebo cesta.  |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "sdeurnet"
#define TRADEBOT_DEFAULT_PROFILE "eurusd_6e_5m"

#include <TradeBot/TradeBotEA.mqh>
