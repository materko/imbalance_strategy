// IBSEntryEsNet - IBS EZ ES (S&P 500) s jadrom v C# ako strategia NinjaTrader 8.
// ES / MES: IBS EZ ES - prahy v násobkoch ATR, filter trendu / volatility (profil PRESIEL_SMERNICAMI_IBS_EZ_ES_1).
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/ibsentry/ports/csharp` nad
// `IbsNet`) a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „IBSEntryEsNet" na MINUTOVOM grafe.
// Druhu datovu seriu (detekcny TF zon, `zoneDetectionTF` z profilu) si strategia prida sama; zony z FVG
// (5m/15m/30m/1h) si sklada z barov grafu.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class IBSEntryEsNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "ibsentryesnet"; } }

        // futures ES / MES 3m, profil, ktorý prešiel smernicou (25. 10. 2026)
        protected override string DefaultProfile { get { return "PRESIEL_SMERNICAMI_IBS_EZ_ES_1"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "IBSEntryEsNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy ibsentryesnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
