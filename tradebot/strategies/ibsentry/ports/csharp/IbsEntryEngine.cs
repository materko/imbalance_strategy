// `IbsEntryEngine` - IBS Entry Zone s jadrom v C#. Zrkadlo `tradebot/strategies/ibsentry/engine.py`; s Python
// enginom sa porovnava bar po bare, na rovnost.
//
// IBS obchoduje zony z troch zdrojov (SD pattern, S/R urovne, likvidita); tento engine pridava stvrty: fair value
// gap z 5m, 15m, 30m a 1h. Zona z FVG sa znaci rovnako ako SD zona a obchoduje sa rovnakym modelom (STATE 0-5,
// imbalance / pin bar / engulfing) - nie je to filter. Bullish FVG = dopyt -> LONG zona, bearish = ponuka -> SHORT.
// Detekcia SD zon je synchronizovana s datami ako v `ibszones` (`HtfFeeder` so `ZoneSync`).
using System;
using System.Collections.Generic;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet;

namespace TradeBot.Strategies.IbsEntryNet
{
    [TradeBotEngine("ibsentrynet", "IBS Entry Zone (C#)")]
    public sealed class IbsEntryEngine : IbsEngine
    {
        private readonly IbsEntryConfig _cfg;
        private readonly int[] _tfs;
        public readonly FvgDetector Fvg;
        /// <summary>kolko zon z FVG (a z IFVG) vrstva doteraz vyrobila</summary>
        public int FvgZonesCreated;
        public int IfvgZonesCreated;

        public IbsEntryEngine(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)
            : this(IbsEntryConfig.FromDict(config), inst, chartTfMinutes)
        {
        }

        public IbsEntryEngine(IbsEntryConfig cfg, InstrumentSpec inst, int chartTfMinutes)
            : base(cfg, inst, chartTfMinutes)
        {
            _cfg = cfg;
            _tfs = cfg.ActiveFvgTimeframes();
            Fvg = new FvgDetector(_tfs);
            // aby bolo z coho zlozit tri sviecky najvyssieho zapnuteho TF
            if ((cfg.enableFvgTrading || cfg.enableIfvgTrading) && _tfs.Length > 0)
            {
                int maxTf = 0;
                foreach (int m in _tfs) maxTf = Math.Max(maxTf, m);
                int need = 3 * (int)Math.Ceiling((double)maxTf / _chartTfMinutes) + 1;
                _requiredHistory = Math.Max(_requiredHistory, need);
            }
        }

        public override IHtfFeeder CreateHtfFeeder() { return new HtfFeeder(Cfg, _chartTfMinutes, true); }

        /// <summary>Hacik z `IbsEngine` - vola sa na tom istom mieste ako S/R a likvidita.</summary>
        protected override void SpawnExtraZones(Bar bar, EngineOutput o)
        {
            bool fvgOn = _cfg.enableFvgTrading, ifvgOn = _cfg.enableIfvgTrading;
            if (!(fvgOn || ifvgOn) || _tfs.Length == 0) return;
            double minSize = _cfg.fvgMinSize.Resolve(_inst, bar.Close, History.Atr);
            // Medzera sa sleduje kvoli inverzii tak dlho, ako by zila jej zona.
            List<FvgHit> hits = Fvg.OnBar(bar, minSize, (long)(_cfg.zoneValidHours * 3600000L));
            if (fvgOn)
            {
                foreach (FvgHit hit in hits)
                {
                    PushGapZone(hit, "FVG", bar, o);
                    FvgZonesCreated += 1;
                }
            }
            if (ifvgOn)
            {
                foreach (FvgHit hit in Fvg.Inverted)
                {
                    PushGapZone(hit, "IFVG", bar, o);
                    IfvgZonesCreated += 1;
                }
            }
        }

        /// <summary>Medzera -> obycajna zona v knihe (smer podla `hit.Direction`).</summary>
        private void PushGapZone(FvgHit hit, string label, Bar bar, EngineOutput o)
        {
            Direction direction = hit.Direction == 1 ? Direction.Long : Direction.Short;
            Zone zone = Book.CreateRaw(direction, hit.Top, hit.Bot, bar.Time, ZoneSource.Fvg);
            zone.CreatedBarIndex = History.BarIndex;
            zone.Variant = label + hit.TfMinutes + "m";
            o.Drawings.AddRange(zone.Boxes(_stepMs));
        }
    }
}
