// Konfiguracia IBS Entry Zone (C#) - zrkadlo `tradebot/strategies/ibsentry/config.py`.
// Vsetky polia IBS (`IbsConfig`) plus stvrty zdroj zon: velke imbalance (FVG) z vyssich TF.
using System;
using System.Collections.Generic;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet;

namespace TradeBot.Strategies.IbsEntryNet
{
    public sealed class IbsEntryConfig : IbsConfig
    {
        // ---- Zony z imbalance (FVG) -------------------------------------------
        public bool enableFvgTrading = true;
        /// <summary>Inverzne FVG - medzera prerazena zatvorenim sa stane zonou opacneho smeru.</summary>
        public bool enableIfvgTrading = false;
        public bool fvgUse5m = true;
        public bool fvgUse15m = true;
        public bool fvgUse30m = true;
        public bool fvgUse60m = true;
        public SizeSpec fvgMinSize = new SizeSpec(5.0, "abs");

        /// <summary>Minuty TF, z ktorych sa velke imbalance naozaj citaju (Python `active_fvg_timeframes`).</summary>
        public int[] ActiveFvgTimeframes()
        {
            List<int> tfs = new List<int>();
            if (fvgUse5m) tfs.Add(5);
            if (fvgUse15m) tfs.Add(15);
            if (fvgUse30m) tfs.Add(30);
            if (fvgUse60m) tfs.Add(60);
            return tfs.ToArray();
        }

        public static new IbsEntryConfig FromDict(Dictionary<string, object> data)
        {
            return Fill(new IbsEntryConfig(), data);
        }

        protected override string SizeUnit(string name)
        {
            return name == "fvgMinSize" ? "abs" : base.SizeUnit(name);
        }
    }
}
