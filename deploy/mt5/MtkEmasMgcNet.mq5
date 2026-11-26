//+------------------------------------------------------------------+
//| MtkEmasMgcNet - MTK EMAS 1.0 s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/mtkemas/ports/csharp`,|
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\MtkEmasMgcNet.mq5 a prelozit (F7); v terminali musi byt   |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| Priemery a ATR z barov grafu; trailing a zamok (break-even) posuva EA na zavreti baru.                                            |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\mtkemasmgcnet alebo cesta.    |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "mtkemasmgcnet"
#define TRADEBOT_DEFAULT_PROFILE "mgc_databento_4h"

#include <TradeBot/TradeBotEA.mqh>
