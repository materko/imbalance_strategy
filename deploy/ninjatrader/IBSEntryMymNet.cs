// IBSEntryMymNet - IBS EZ MYM (S&P 500) s jadrom v C# ako strategia NinjaTrader 8.
// MYM / YM: IBS EZ MYM - prahy v násobkoch ATR, filter trendu / volatility (profil mym_databento_3m).
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibsentry/ports/csharp` nad
// `IbsNet`) a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „IBSEntryMymNet" na MINUTOVOM grafe.
// Druhu datovu seriu (detekcny TF zon, `zoneDetectionTF` z profilu) si strategia prida sama; zony z FVG
// (5m/15m/30m/1h) si sklada z barov grafu.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class IBSEntryMymNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "ibsentrymymnet"; } }

        // futures MYM / YM 3m, východiskový profil (ladenie na MYM od 12. 11. 2026)
        protected override string DefaultProfile { get { return "mym_databento_3m"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "IBSEntryMymNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy ibsentrymymnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
