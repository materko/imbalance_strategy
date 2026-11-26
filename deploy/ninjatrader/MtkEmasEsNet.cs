// MtkEmasEsNet - MTK EMAS 1.0 (klzave priemery, sledovanie trendu) s jadrom v C# ako strategia NinjaTrader 8.
//
// Tento subor je len ukazovatel: cela logika je v C# jadre (`tradebot/strategies/mtkemas/ports/csharp`)
// a vsetko okolo NinjaTradera v generickom adapteri (`tradebot/adapters/ninjatrader/TradeBotStrategy.cs`).
// Instalacia (skopiruje jadro, adapter, tuto sablonu a profily do Documents\NinjaTrader 8):
//
//     python -m tradebot.adapters.ninjatrader install
//
// Potom v NinjaTraderi: New > NinjaScript Editor > F5 (preklad), strategia „MtkEmasEsNet" na MINUTOVOM grafe.
// Informativny TF strategia nema; priemery a ATR pocita z barov grafu (TF podla profilu: 30m - 1D).
// Filter trendu a volatility, potvrdenie sviecou a limitku robi C# jadro samo (`EntryLayers`), ako v testoch.
// Profil: parameter „Profil" = nazov JSON z Documents\NinjaTrader 8\TradeBot\profiles alebo cela cesta.
#region Using declarations
using System;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MtkEmasEsNet : TradeBotStrategy
    {
        protected override string EngineKey { get { return "mtkemasesnet"; } }

        // Klzavy priemer (cena x priemer alebo krizenie) + EMA 200, len longy, stop a trailing v ATR
        protected override string DefaultProfile { get { return "es_databento_1h"; } }

        protected override void OnStateChange()
        {
            base.OnStateChange();
            if (State == State.SetDefaults)
            {
                Name = "MtkEmasEsNet";
                // Kym vetva NinjaTrader nie je overena proti Testeru, kazdy beh necha stopu na porovnanie
                // (`python -m tester.ninjatrader compare --strategy mtkemasesnet`). Pred optimalizaciou vypni.
                ExportSignals = true;
            }
        }
    }
}
