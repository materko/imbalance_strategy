//+------------------------------------------------------------------+
//| SpravyNet - SPRAVY (zlato po spravach USA) s jadrom v C# ako Expert Advisor MetaTrader 5   |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/spravy/ports/csharp`,|
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\SpravyNet.mq5 a prelozit (F7); v terminali musi byt  |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| XAUUSD (CFD) alebo MGC; cas sprav je v kalendari jadra (New York, prevod pre kazdy den).      |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\spravynet alebo cesta.  |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "spravynet"
#define TRADEBOT_DEFAULT_PROFILE "mgc_databento_5m"

#include <TradeBot/TradeBotEA.mqh>
