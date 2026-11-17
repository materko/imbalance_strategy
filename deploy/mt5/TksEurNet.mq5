//+------------------------------------------------------------------+
//| TksEurNet - TKS 1.0 6E (C# jadro) ako Expert Advisor MetaTrader 5
//|
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/tks/ports/csharp`,
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:
//|
//|     python -m tradebot.adapters.mt5 install
//|
//| Potom v MetaEditore otvorit Experts\TradeBot\TksEurNet.mq5 a prelozit (F7); v terminali musi byt
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\tkseurnet alebo cesta.
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "tkseurnet"
#define TRADEBOT_DEFAULT_PROFILE "6e_databento_3m"

#include <TradeBot/TradeBotEA.mqh>
