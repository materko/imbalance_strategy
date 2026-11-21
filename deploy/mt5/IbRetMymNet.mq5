//+------------------------------------------------------------------+
//| IbRetMymNet - IB RETRACE 1.0 MYM (C# jadro) ako Expert Advisor MetaTrader 5
//|
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibret/ports/csharp`,
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:
//|
//|     python -m tradebot.adapters.mt5 install
//|
//| Potom v MetaEditore otvorit Experts\TradeBot\IbRetMymNet.mq5 a prelozit (F7); v terminali musi byt
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\ibretmymnet alebo cesta.
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "ibretmymnet"
#define TRADEBOT_DEFAULT_PROFILE "mym_databento_5m"

#include <TradeBot/TradeBotEA.mqh>
