// TradeBot Live View - indikator, ktory na grafe NinjaTradera ukaze, co robi instancia AddOnu
// (docs/NINJATRADER.md, "Graf nazivo"): kresby enginu (zony, TP/SL boxy, stitky, ciary), cakajuce vstupy,
// pozicie so SL a TP a vyplnenia. AddOn nema graf - instancie zverejnuju `LiveViewFeed` v `LiveViews`
// a indikator si najde feed podla instrumentu (MasterInstrument) a TF grafu.
//
// Len zobrazuje: nic neposiela, instanciu neovplyvni; odobratie z grafu ani zatvorenie grafu ju nezastavi.
// Synchronizacia bezi vo vlakne indikatora - pri kazdom ticku a kazdu sekundu cez System.Timers.Timer ->
// TriggerCustomEvent (trh stoji, ticky nechodia). Feed dava len zmeny od posledneho citania; restart instancie
// (novy feed) alebo nove prehratie historie (nova epocha) = zmazat a nakreslit vsetko znova.
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Windows;
using System.Windows.Media;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Tools;
using NinjaTrader.NinjaScript.AddOns;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Indicators
{
    public class TradeBotLiveView : Indicator
    {
        /// <summary>Co si indikator pamata o jednom feede (jednej instancii).</summary>
        private sealed class Seen
        {
            public LiveViewFeed Feed;
            public string Prefix = "";
            public int Epoch = -1, Pos, FillSeq, OrdersRev = -1;
            public List<LiveViewOrder> Orders = new List<LiveViewOrder>();
            public readonly HashSet<string> DrawTags = new HashSet<string>();
            public readonly HashSet<string> OrderTags = new HashSet<string>();
            public readonly HashSet<string> FillTags = new HashSet<string>();
        }

        private static readonly DateTime Epoch0 = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        private readonly Dictionary<string, Seen> _seen = new Dictionary<string, Seen>();
        private readonly Dictionary<string, Brush> _brushes = new Dictionary<string, Brush>();
        private System.Timers.Timer _timer;
        private volatile bool _tickQueued;
        private int _ordersBar = -1;
        private string _status = "";

        [Display(Name = "Strategia", Description = "Kluc strategie (napr. ibsentrynet). Prazdne = vsetky instancie AddOnu na tomto instrumente a TF.", GroupName = "TradeBot", Order = 1)]
        public string StrategyKey { get; set; }

        [Display(Name = "Ucet", Description = "Ucet instancie (napr. Sim101). Prazdne = hocijaky.", GroupName = "TradeBot", Order = 2)]
        public string AccountName { get; set; }

        [Range(0, int.MaxValue)]
        [Display(Name = "TF instancie (min)", Description = "TF, na ktorom bezi instancia. 0 = TF grafu (graf musi byt minutovy).", GroupName = "TradeBot", Order = 3)]
        public int InstanceTf { get; set; }

        [Range(1, 365)]
        [Display(Name = "Dni dozadu", Description = "Kresby starsie nez toto sa nekreslia - na dlhej historii by spomalili graf.", GroupName = "TradeBot", Order = 4)]
        public int DaysBack { get; set; }

        [Display(Name = "Kreslit objekty", Description = "Zony, TP/SL boxy, stitky a ciary z enginu.", GroupName = "TradeBot", Order = 5)]
        public bool ShowDrawings { get; set; }

        [Display(Name = "Kreslit ordery", Description = "Cakajuce vstupy a otvorene pozicie so SL a TP.", GroupName = "TradeBot", Order = 6)]
        public bool ShowOrders { get; set; }

        [Display(Name = "Kreslit vyplnenia", Description = "Sipky vstupov a kosostvorce vystupov.", GroupName = "TradeBot", Order = 7)]
        public bool ShowFills { get; set; }

        [Display(Name = "Kreslit pozadie seans", Description = "Pas pozadia na kazdom bare seansy - na dlhej historii spomaluje graf.", GroupName = "TradeBot", Order = 8)]
        public bool ShowSessionBackground { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "TradeBotLiveView";
                Description = "Kresby, ordery a vyplnenia instancie TradeBot AddOnu (strategia bezi bez grafu) na tomto grafe.";
                IsOverlay = true;
                Calculate = Calculate.OnPriceChange;
                DisplayInDataBox = false;
                PaintPriceMarkers = false;
                DrawOnPricePanel = true;
                IsSuspendedWhileInactive = false;
                StrategyKey = "";
                AccountName = "";
                InstanceTf = 0;
                DaysBack = 5;
                ShowDrawings = true;
                ShowOrders = true;
                ShowFills = true;
                ShowSessionBackground = false;
            }
            else if (State == State.Realtime)
            {
                StartTimer();
            }
            else if (State == State.Terminated)
            {
                StopTimer();
            }
        }

        protected override void OnBarUpdate()
        {
            if (State != State.Realtime) return;
            Sync(null);
        }

        // ------------------------------------------------------------------ //
        // Synchronizacia s feedmi
        // ------------------------------------------------------------------ //

        private void StartTimer()
        {
            if (_timer != null) return;
            try
            {
                _timer = new System.Timers.Timer(1000);
                _timer.AutoReset = true;
                _timer.Elapsed += OnTimer;
                _timer.Start();
            }
            catch (Exception e) { Print("TradeBotLiveView: timer zlyhal - " + e.Message); }
        }

        private void StopTimer()
        {
            if (_timer == null) return;
            try
            {
                _timer.Stop();
                _timer.Elapsed -= OnTimer;
                _timer.Dispose();
            }
            catch (Exception) { }
            _timer = null;
        }

        private void OnTimer(object sender, System.Timers.ElapsedEventArgs e)
        {
            try
            {
                if (State != State.Realtime || _tickQueued) return;
                _tickQueued = true;
                TriggerCustomEvent(Sync, null);
            }
            catch (Exception) { _tickQueued = false; }
        }

        /// <summary>TF instancie: z vlastnosti, inak minutovy TF grafu; 0 = graf nie je minutovy.</summary>
        private int Tf()
        {
            if (InstanceTf > 0) return InstanceTf;
            return BarsPeriod.BarsPeriodType == BarsPeriodType.Minute ? BarsPeriod.Value : 0;
        }

        private void Sync(object state)
        {
            _tickQueued = false;
            try
            {
                int tf = Tf();
                List<LiveViewFeed> feeds = tf > 0
                    ? LiveViews.Matching(Instrument.MasterInstrument.Name, tf, StrategyKey, AccountName)
                    : new List<LiveViewFeed>();
                ShowStatus(tf == 0 ? "TradeBotLiveView: graf nie je minutovy - nastav TF instancie"
                       : feeds.Count == 0 ? "TradeBotLiveView: ziadna instancia AddOnu na " + Instrument.MasterInstrument.Name + " " + tf + "m"
                       + (string.IsNullOrEmpty(StrategyKey) ? "" : " (" + StrategyKey + ")") : "");

                HashSet<string> live = new HashSet<string>();
                foreach (LiveViewFeed f in feeds) live.Add(f.Instance);
                foreach (string gone in new List<string>(_seen.Keys))
                    if (!live.Contains(gone)) { Clear(_seen[gone]); _seen.Remove(gone); }

                bool newBar = CurrentBar != _ordersBar;
                _ordersBar = CurrentBar;
                foreach (LiveViewFeed f in feeds)
                {
                    Seen s;
                    if (!_seen.TryGetValue(f.Instance, out s) || !ReferenceEquals(s.Feed, f))
                    {
                        if (s != null) Clear(s);   // restart instancie - novy feed, kresli sa odznova
                        s = new Seen();
                        s.Feed = f;
                        s.Prefix = "tb." + f.Strategy + "." + f.Account + ".";
                        _seen[f.Instance] = s;
                    }
                    SyncDrawings(s);
                    SyncOrders(s, newBar);
                    SyncFills(s);
                }
            }
            catch (Exception e) { ShowStatus("TradeBotLiveView: " + e.Message); }
        }

        private void ShowStatus(string text)
        {
            if (text == _status) return;
            _status = text;
            if (text.Length == 0) RemoveDrawObject("tb.status");
            else Draw.TextFixed(this, "tb.status", text, TextPosition.BottomLeft);
        }

        private void Clear(Seen s)
        {
            foreach (string tag in s.DrawTags) RemoveDrawObject(tag);
            foreach (string tag in s.OrderTags) RemoveDrawObject(tag);
            foreach (string tag in s.FillTags) RemoveDrawObject(tag);
            s.DrawTags.Clear(); s.OrderTags.Clear(); s.FillTags.Clear();
        }

        private long CutoffMs()
        {
            return (long)(DateTime.UtcNow.AddDays(-DaysBack) - Epoch0).TotalMilliseconds;
        }

        private void SyncDrawings(Seen s)
        {
            List<LiveViewItem> items = new List<LiveViewItem>();
            int epoch = s.Epoch, pos = s.Pos;
            bool reset = s.Feed.ReadDrawings(ref epoch, ref pos, items);
            if (reset)
            {
                foreach (string tag in s.DrawTags) RemoveDrawObject(tag);
                s.DrawTags.Clear();
            }
            s.Epoch = epoch;
            s.Pos = pos;
            if (!ShowDrawings) return;
            long cutoff = CutoffMs();
            long stepMs = s.Feed.Tf * 60000L;
            foreach (LiveViewItem v in items)
            {
                string tag = s.Prefix + v.Id;
                bool skip = v.Deleted || v.LastMs < cutoff || (v.Type == "bg" && v.Kind == "session" && !ShowSessionBackground);
                if (skip)
                {
                    if (s.DrawTags.Remove(tag)) RemoveDrawObject(tag);
                    continue;
                }
                if (Paint(tag, v, stepMs)) s.DrawTags.Add(tag);
            }
        }

        private void SyncOrders(Seen s, bool newBar)
        {
            int rev = s.OrdersRev;
            List<LiveViewOrder> orders = s.Feed.ReadOrders(ref rev);
            if (orders != null) { s.Orders = orders; s.OrdersRev = rev; }
            else if (!newBar) return;   // ciary siahaju po posledny bar - na novom bare sa predlzia
            HashSet<string> keep = new HashSet<string>();
            if (ShowOrders && CurrentBar >= 0)
            {
                DateTime end = Time[0];
                foreach (LiveViewOrder o in s.Orders)
                {
                    DateTime start = o.SinceMs > 0 ? FromMs(o.SinceMs) : end;
                    if (start > end) start = end;
                    string name = s.Feed.Strategy + " " + (o.Long ? "L" : "S") + o.Qty;
                    Brush entry = o.Filled ? Brushes.DodgerBlue : Brushes.Gray;
                    DashStyleHelper dash = o.Filled ? DashStyleHelper.Solid : DashStyleHelper.Dash;
                    OrderLine(s, keep, o.Id + ".e", start, end, o.Entry, entry, dash,
                              name + (o.Filled ? " vstup" : (o.Parked ? " odlozeny" : " cakajuci")));
                    if (o.Stop > 0) OrderLine(s, keep, o.Id + ".sl", start, end, o.Stop, Brushes.Crimson, dash, name + " SL");
                    if (o.Target > 0) OrderLine(s, keep, o.Id + ".tp", start, end, o.Target, Brushes.SeaGreen, dash, name + " TP");
                }
            }
            foreach (string tag in new List<string>(s.OrderTags))
                if (!keep.Contains(tag)) { RemoveDrawObject(tag); s.OrderTags.Remove(tag); }
        }

        private void OrderLine(Seen s, HashSet<string> keep, string id, DateTime start, DateTime end, double price,
                               Brush brush, DashStyleHelper dash, string text)
        {
            string tag = s.Prefix + "o." + id;
            Draw.Line(this, tag, false, start, price, end, price, brush, dash, 2);
            Draw.Text(this, tag + ".t", false, text, end, price, 8, brush, new SimpleFont("Arial", 9),
                      TextAlignment.Left, Brushes.Transparent, Brushes.Transparent, 0);
            keep.Add(tag); keep.Add(tag + ".t");
            s.OrderTags.Add(tag); s.OrderTags.Add(tag + ".t");
        }

        private void SyncFills(Seen s)
        {
            int seq = s.FillSeq;
            List<LiveViewFill> fills = s.Feed.ReadFills(ref seq);
            s.FillSeq = seq;
            if (!ShowFills) return;
            long cutoff = CutoffMs();
            foreach (LiveViewFill f in fills)
            {
                if (f.Ms < cutoff) continue;
                string tag = s.Prefix + "f." + f.Seq;
                DateTime t = FromMs(f.Ms);
                if (f.Entry && f.Long == true) Draw.ArrowUp(this, tag, false, t, f.Price, Brushes.DodgerBlue);
                else if (f.Entry && f.Long == false) Draw.ArrowDown(this, tag, false, t, f.Price, Brushes.Crimson);
                else Draw.Diamond(this, tag, false, t, f.Price, f.Entry ? Brushes.Gray : Brushes.Gold);
                s.FillTags.Add(tag);
            }
        }

        // ------------------------------------------------------------------ //
        // Kreslenie (ako TradeBotStrategy.Paint)
        // ------------------------------------------------------------------ //

        private static TimeZoneInfo PlatformZone { get { return NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo; } }

        private static DateTime FromMs(long ms)
        {
            return TimeZoneInfo.ConvertTimeFromUtc(Epoch0.AddMilliseconds(ms), PlatformZone);
        }

        private Brush BrushOf(string hex, out int opacity)
        {
            // "#rrggbb" alebo "#rrggbbaa" (Pine `color.new` -> alfa)
            opacity = 100;
            if (string.IsNullOrEmpty(hex) || hex.Length < 7) return Brushes.Transparent;
            string rgb = hex.Substring(0, 7);
            if (hex.Length == 9)
                opacity = (int)Math.Round(int.Parse(hex.Substring(7, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture) / 255.0 * 100);
            Brush brush;
            if (_brushes.TryGetValue(rgb, out brush)) return brush;
            Color c = Color.FromRgb(byte.Parse(rgb.Substring(1, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture),
                                    byte.Parse(rgb.Substring(3, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture),
                                    byte.Parse(rgb.Substring(5, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
            brush = new SolidColorBrush(c);
            brush.Freeze();
            _brushes[rgb] = brush;
            return brush;
        }

        /// <summary>Jedna kresba enginu; X = cas otvorenia baru instancie, NinjaTrader kresli bar na case zatvorenia.</summary>
        private bool Paint(string tag, LiveViewItem v, long stepMs)
        {
            int opacity, fillOpacity;
            switch (v.Type)
            {
                case "box":
                {
                    Brush border = BrushOf(v.Color, out opacity);
                    Brush fill = BrushOf(v.FillColor, out fillOpacity);
                    if (opacity == 0 || v.Width == 0) border = Brushes.Transparent;
                    Draw.Rectangle(this, tag, false, FromMs(v.X1Ms + stepMs), v.Y1, FromMs(v.X2Ms + stepMs), v.Y2, border, fill,
                                   v.FillColor == null ? 0 : fillOpacity);
                    return true;
                }
                case "line":
                {
                    DashStyleHelper dash = v.Style == "dotted" ? DashStyleHelper.Dot
                                         : (v.Style == "dashed" ? DashStyleHelper.Dash : DashStyleHelper.Solid);
                    Draw.Line(this, tag, false, FromMs(v.X1Ms + stepMs), v.Y1, FromMs(v.X2Ms + stepMs), v.Y2,
                              BrushOf(v.Color, out opacity), dash, v.Width);
                    return true;
                }
                case "label":
                {
                    Brush text = BrushOf(v.Color, out opacity);
                    Brush bg = BrushOf(v.BgColor, out fillOpacity);
                    Draw.Text(this, tag, false, v.Text ?? "", FromMs(v.X1Ms + stepMs), v.Y1, v.Above ? 12 : -12, text,
                              new SimpleFont("Arial", 10), TextAlignment.Center, Brushes.Transparent, bg, v.BgColor == null ? 0 : fillOpacity);
                    return true;
                }
                case "bg":
                {
                    Brush brush = BrushOf(v.Color, out opacity);
                    Draw.RegionHighlightX(this, tag, FromMs(v.X1Ms + stepMs), FromMs(v.X2Ms + stepMs), Brushes.Transparent, brush, opacity);
                    return true;
                }
            }
            return false;
        }
    }
}
