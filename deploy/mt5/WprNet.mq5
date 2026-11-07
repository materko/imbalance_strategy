//+------------------------------------------------------------------+
//| WprNet - WILLIAMS %R LONG 1.0 (C# jadro) ako Expert Advisor MetaTrader 5
//|
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/wpr/ports/csharp`,
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:
//|
//|     python -m tradebot.adapters.mt5 install
//|
//| Potom v MetaEditore otvorit Experts\TradeBot\WprNet.mq5 a prelozit (F7); v terminali musi byt
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\wprnet alebo cesta.
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "wprnet"
#define TRADEBOT_DEFAULT_PROFILE "PRESIEL_SMERNICAMI_WILLIAMS_R_MNQ_1"

#include <TradeBot/TradeBotEA.mqh>
