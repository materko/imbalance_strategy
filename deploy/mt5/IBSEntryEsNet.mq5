//+------------------------------------------------------------------+
//| IBSEntryEsNet - IBS EZ ES (S&P 500 futures) s jadrom v C# (.NET) ako Expert Advisor MetaTrader 5                 |
//|                                                                                                   |
//| Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/csharp/TradeBot.Strategies/IbsEntryNet`,|
//| prelozene `TradeBot.dll` v MQL5\Libraries) a vsetko okolo MetaTradera v generickom adapteri        |
//| (`tradebot/adapters/mt5/TradeBotEA.mqh`, v MQL5\Include\TradeBot). Instalacia:                    |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| Potom v MetaEditore otvorit Experts\TradeBot\IBSEntryEsNet.mq5 a prelozit (F7); v terminali musi byt |
//| povolene Tools > Options > Expert Advisors > Allow DLL imports. EA sa spusta na MINUTOVOM grafe   |
//| (napr. M3); informativny TF zon (`zoneDetectionTF` z profilu) si cita sam cez CopyRates.          |
//| Profil: vstup „InpProfile" = nazov JSON z Common\Files\TradeBot\profiles\ibsentryesnet alebo cesta. |
//+------------------------------------------------------------------+
#define TRADEBOT_ENGINE_KEY      "ibsentryesnet"
#define TRADEBOT_DEFAULT_PROFILE "PRESIEL_SMERNICAMI_IBS_EZ_ES_1"   // futures ES / MES 3m

#include <TradeBot/TradeBotEA.mqh>
