//+------------------------------------------------------------------+
//| MtkZoneNet - MTK ZONE s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/mtkzone/ports/csharp`, |
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\MtkZoneNet.mq5 a prelozit (F7); v terminali musi byt  |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na 3m (2m) grafe.      |
//| Zony z objemu potrebuju skutocny objem burzy; na CFD je objem len aktivita tickov (odhad).        |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\mtkzonenet alebo cesta.  |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "mtkzonenet"
#define TRADEBOT_DEFAULT_PROFILE "mnq_databento_3m"

#include <TradeBot/TradeBotEA.mqh>
