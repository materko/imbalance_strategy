//+------------------------------------------------------------------+
//| IBSEntryNetEod - (EOD 15:59 NY) IBS Entry Zone s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                 |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibsentry/csharp`,|
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\IBSEntryNetEod.mq5 a prelozit (F7); v terminali musi byt |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe   |
//| (napr. M3); informativny TF zon (`zoneDetectionTF` z profilu) si cita sam cez CopyRates.          |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\ibsentryneteod alebo cesta. |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "ibsentryneteod"
#define TRADEBOT_DEFAULT_PROFILE "multicharts_mnq_3m"   // futures MNQ 3m

#include <TradeBot/TradeBotEA.mqh>
