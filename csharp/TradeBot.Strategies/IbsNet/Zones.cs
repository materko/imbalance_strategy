// Detekcia SD zon na detekcnom TF + evidencia zon - zrkadlo `tradebot/strategies/ibs/zones.py`
// (Pine riadky 274-279 `snapTime`, 357-392 pattern, 638-660 vytvorenie zony a jej dvoch boxov).
using System;
using System.Collections.Generic;
using TradeBot.Core;

namespace TradeBot.Strategies.IbsNet
{
    /// <summary>Pine `srcIn` v `f_pushZone`.</summary>
    public enum ZoneSource { Sd = 0, Sr = 1, Liquidity = 2 }

    /// <summary>Vysledok hladania patternu na detekcnom TF.</summary>
    public sealed class SdPattern
    {
        public Direction Direction;
        public double Top;
        public double Bot;
        public long BaseMs;      // Pine zT05 - cas najstarsieho baru (bars[3])
        public long ConfirmMs;   // Pine zTConf5 - cas posledneho uzavreteho baru (bars[0])
        public bool VolumeStrong;
        public string Variant;
    }

    /// <summary>Jedna zona v evidencii vratane stavu jej zivotneho cyklu (STATE 0-5).</summary>
    public sealed class Zone
    {
        public int Uid;
        public Direction Direction;
        public double Top;
        public double Bot;
        public long CreatedMs;    // Pine leftT
        public long ConfirmedMs;  // Pine confT
        public long ExpiresMs;    // Pine expT
        public ZoneSource Source = ZoneSource.Sd;
        public bool VolumeStrong;
        public string Variant = "";
        /// <summary>Pine bar_index v momente vzniku - gap sa smie hladat len za nim.</summary>
        public int CreatedBarIndex;
        public long DetectedMs;

        // ---- stav zivotneho cyklu ----
        public int State;
        public bool Used;
        public bool Touched;
        public int? TouchedBarIndex;
        public int? StateBarIndex;
        public long? StateTimeMs;

        // ---- najdeny imbalance / pattern ----
        public double? ImbBodyTop;
        public double? ImbBodyBot;
        public double? ImbOpen;
        public double? ImbHigh;
        public double? ImbLow;
        public int? ImbBarIndex;

        // ---- order ----
        public double? OrderSl;
        public bool Ordered;
        public bool Filled;
        public bool PendingInvalid;
        public bool EntryDone;
        public bool TradeBoxesClosed;

        /// <summary>Pine `"LONG_" + uidStr` / `"SHORT_" + uidStr`.</summary>
        public string OrderId { get { return (Direction == Direction.Long ? "LONG_" : "SHORT_") + Uid; } }

        public bool IsExpired(long tsMs) { return tsMs >= ExpiresMs; }

        public string Color { get { return Palette.ZoneColor((int)Direction, VolumeStrong); } }
        public string PreBoxId { get { return "z" + Uid + ".pre"; } }
        public string PostBoxId { get { return "z" + Uid + ".post"; } }

        /// <summary>Pine `resizeZoneOnInvalidation` - oba boxy koncia TERAZ.</summary>
        public List<DrawCommand> ResizeOnInvalidation(long nowMs)
        {
            List<DrawCommand> list = new List<DrawCommand>(2);
            list.Add(new DrawUpdate(PreBoxId, "x2_ms", nowMs));
            list.Add(new DrawUpdate(PostBoxId, "x2_ms", nowMs));
            return list;
        }

        /// <summary>Dva boxy, ktore Pine kresli pri vzniku zony (riadky 651-657).</summary>
        public List<DrawCommand> Boxes(long stepMs)
        {
            string border = Color;

            long preRight = ConfirmedMs > CreatedMs ? ConfirmedMs : CreatedMs + stepMs;
            preRight = Math.Min(preRight, ExpiresMs);

            long postLeft = ConfirmedMs;
            long postRight = ExpiresMs > postLeft ? ExpiresMs : postLeft + stepMs;

            DrawBox pre = new DrawBox(IbsKinds.SdZonePre, CreatedMs, Top, preRight, Bot, Palette.WithAlpha(border, 15));
            pre.BorderStyle = LineStyles.Dotted;
            pre.ObjId = PreBoxId;
            pre.ZoneUid = Uid;

            DrawBox post = new DrawBox(IbsKinds.SdZonePost, postLeft, Top, postRight, Bot, Palette.WithAlpha(border, 15));
            post.FillColor = Palette.WithAlpha(border, 85);
            post.ObjId = PostBoxId;
            post.ZoneUid = Uid;

            List<DrawCommand> list = new List<DrawCommand>(2);
            list.Add(pre);
            list.Add(post);
            return list;
        }
    }

    public static class ZoneDetection
    {
        /// <summary>Pine `maxSdZonesEff = math.min(maxSdZones, 200)`.</summary>
        public const int MaxZonesHardCap = 200;

        /// <summary>Pine `snapTime` - zarovnanie na grid TF grafu. Musi sediet na milisekundu.</summary>
        public static long SnapTime(long tMs, long stepMs, SnapMode mode)
        {
            if (mode == SnapMode.Off || stepMs <= 0) return tMs;
            double q = (double)tMs / stepMs;
            if (mode == SnapMode.Floor) return (long)Math.Floor(q) * stepMs;
            if (mode == SnapMode.Ceil) return (long)Math.Ceiling(q) * stepMs;
            return (long)Math.Round(q) * stepMs;
        }

        private static bool IsBull(Bar b) { return b.Close > b.Open; }
        private static bool IsBear(Bar b) { return b.Close < b.Open; }

        /// <summary>Pine riadky 357-392. Vrati pattern, alebo null ak ziadny nesedi.</summary>
        public static SdPattern DetectSdPattern(HtfWindow htf, IbsConfig cfg, InstrumentSpec inst, double atr)
        {
            Bar b0 = htf.Bars[0], b1 = htf.Bars[1], b2 = htf.Bars[2], b3 = htf.Bars[3];

            double minImb = cfg.minImbSizePoints.Resolve(inst, b0.Close, atr);

            bool bullImb1 = (b0.Low - b2.High) >= minImb && b0.Low > b2.High;
            bool bearImb1 = (b2.Low - b0.High) >= minImb && b0.High < b2.Low;
            bool bullImb2 = (b1.Low - b3.High) >= minImb && b1.Low > b3.High;
            bool bearImb2 = (b3.Low - b1.High) >= minImb && b1.High < b3.Low;

            bool longV1 = IsBear(b3) && IsBull(b2) && IsBull(b1) && IsBull(b0);
            bool longV2 = IsBear(b3) && IsBull(b2) && bullImb1;
            bool longV3 = IsBear(b3) && IsBull(b2) && bullImb2;
            bool shortV1 = IsBull(b3) && IsBear(b2) && IsBear(b1) && IsBear(b0);
            bool shortV2 = IsBull(b3) && IsBear(b2) && bearImb1;
            bool shortV3 = IsBull(b3) && IsBear(b2) && bearImb2;

            Direction direction;
            string variant;
            if (longV1 || longV2 || longV3)
            {
                direction = Direction.Long;
                variant = longV1 ? "V1" : (longV2 ? "V2" : "V3");
            }
            else if (shortV1 || shortV2 || shortV3)
            {
                direction = Direction.Short;
                variant = shortV1 ? "V1" : (shortV2 ? "V2" : "V3");
            }
            else
            {
                return null;
            }

            double avgImpulseVol = (b0.Volume + b1.Volume + b2.Volume) / 3.0;
            bool volumeStrong = cfg.useVolumeFilter && htf.VolSma > 0 && avgImpulseVol >= cfg.volMultiplier * htf.VolSma;
            if (cfg.useVolumeFilter && cfg.volumeFilterBlockTrading && !volumeStrong) return null;

            SdPattern p = new SdPattern();
            p.Direction = direction;
            p.Top = b3.High;
            p.Bot = b3.Low;
            p.BaseMs = b3.Time;
            p.ConfirmMs = b0.Time;
            p.VolumeStrong = volumeStrong;
            p.Variant = (direction == Direction.Long ? "long" : "short") + variant;
            return p;
        }
    }

    /// <summary>Evidencia zon - poradie vzniku, strop poctu, deduplikacia.</summary>
    public sealed class ZoneBook
    {
        private readonly IbsConfig _cfg;
        public readonly long StepMs;
        public readonly long ZoneValidMs;
        public readonly int MaxZones;
        public readonly List<Zone> Zones = new List<Zone>();
        public int EvictedAlive;
        public int Evicted;
        private int _nextUid;
        private long? _lastBaseMs;

        public ZoneBook(IbsConfig cfg, InstrumentSpec inst, int chartTfMinutes)
        {
            _cfg = cfg;
            StepMs = chartTfMinutes * 60000L;
            ZoneValidMs = (long)(cfg.zoneValidHours * 3600000.0);
            MaxZones = Math.Min(cfg.maxSdZones, ZoneDetection.MaxZonesHardCap);
        }

        public int Count { get { return Zones.Count; } }

        /// <summary>Pine riadky 638-660. Vrati novu zonu, alebo null ak sa nema vytvorit.</summary>
        public Zone CreateFromPattern(SdPattern pattern, long nowMs)
        {
            if (!_cfg.enableZoneDetection) return null;
            if (_lastBaseMs.HasValue && pattern.BaseMs == _lastBaseMs.Value) return null;

            SnapMode mode = _cfg.snapMode;
            long left = ZoneDetection.SnapTime(pattern.BaseMs, StepMs, mode);
            long expires = left + ZoneValidMs;

            long confirm = ZoneDetection.SnapTime(pattern.ConfirmMs != 0 ? pattern.ConfirmMs : nowMs, StepMs, mode);
            confirm = Math.Max(confirm, left);
            confirm = Math.Min(confirm, expires);

            Zone zone = new Zone();
            zone.Uid = _nextUid;
            zone.Direction = pattern.Direction;
            zone.Top = pattern.Top;
            zone.Bot = pattern.Bot;
            zone.CreatedMs = left;
            zone.ConfirmedMs = confirm;
            zone.ExpiresMs = expires;
            zone.Source = ZoneSource.Sd;
            zone.VolumeStrong = pattern.VolumeStrong;
            zone.Variant = pattern.Variant;
            zone.DetectedMs = nowMs;
            _nextUid++;
            _lastBaseMs = pattern.BaseMs;

            Zones.Add(zone);
            EnforceCap(nowMs);
            return zone;
        }

        /// <summary>Pine `array.shift` nad `maxSdZonesEff` - najstarsia zona ide prec.</summary>
        private void EnforceCap(long nowMs)
        {
            while (Zones.Count > MaxZones)
            {
                Zone victim = Zones[0];
                Zones.RemoveAt(0);
                Evicted++;
                if (!victim.IsExpired(nowMs)) EvictedAlive++;
            }
        }

        /// <summary>Pine `f_pushZone` volane z S/R a likvidity - zona zacina na aktualnom bare.</summary>
        public Zone CreateRaw(Direction direction, double top, double bot, long nowMs, ZoneSource source)
        {
            Zone zone = new Zone();
            zone.Uid = _nextUid;
            zone.Direction = direction;
            zone.Top = top;
            zone.Bot = bot;
            zone.CreatedMs = nowMs;
            zone.ConfirmedMs = nowMs;
            zone.ExpiresMs = nowMs + ZoneValidMs;
            zone.Source = source;
            zone.DetectedMs = nowMs;
            _nextUid++;
            Zones.Add(zone);
            EnforceCap(nowMs);
            return zone;
        }
    }
}
