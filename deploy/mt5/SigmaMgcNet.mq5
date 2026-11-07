//+------------------------------------------------------------------+
//| SigmaMgcNet - SIGMA BREAKOUT 1.0 MGC (C# jadro) ako Expert Advisor MetaTrader 5
//|
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/sigma/ports/csharp`,
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:
//|
//|     python -m tradebot.adapters.mt5 install
//|
//| Potom v MetaEditore otvorit Experts\TradeBot\SigmaMgcNet.mq5 a prelozit (F7); v terminali musi byt
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\sigmamgcnet alebo cesta.
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "sigmamgcnet"
#define TRADEBOT_DEFAULT_PROFILE "PRESIEL_SMERNICAMI_SIGMA_MGC_1"

#include <TradeBot/TradeBotEA.mqh>
