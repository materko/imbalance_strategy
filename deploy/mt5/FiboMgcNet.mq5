//+------------------------------------------------------------------+
//| FiboMgcNet - Fibo 1.0 MGC s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                    |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/fibo/ports/csharp`, |
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\FiboMgcNet.mq5 a prelozit (F7); v terminali musi byt  |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe.   |
//| Futures MGC / GC; na CFD XAU (krok 8 smernice presiel) prahy v ATR sedia aj bez prepoctu.         |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\fibomgcnet alebo cesta.  |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "fibomgcnet"
#define TRADEBOT_DEFAULT_PROFILE "PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1"

#include <TradeBot/TradeBotEA.mqh>
