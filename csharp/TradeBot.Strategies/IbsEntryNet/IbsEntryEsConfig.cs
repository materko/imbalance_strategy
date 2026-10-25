// Polia IBS EZ ES navyse oproti IBS Entry Zone - filter trendu a volatility. Cita ich `EntryLayers` v C# jadre priamo
// z configu (`EntryFilterEngine`); tu su len kvoli zhode configu s Pythonom (`IBSEntryEsNetConfig`, defaulty
// z `tradebot/core/entry_filter.py`).
namespace TradeBot.Strategies.IbsEntryNet
{
    public sealed class IbsEntryEsConfig
    {
        public string trendFilter = "off";
        public int trendEmaLen = 200;
        public int trendTF = 0;
        public string volFilter = "off";
        public int volLookback = 100;
    }
}
