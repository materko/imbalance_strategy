// TradeBot Live - co instancia AddOnu ukazuje na grafe (indikator TradeBotLiveView, docs/NINJATRADER.md, "Graf nazivo").
//
// AddOn nema graf, takze kresby enginu, ordery a fily drzi kazda instancia v `LiveViewFeed` a zverejni ho
// v `LiveViews` (staticky zoznam v tom istom procese NinjaTradera). Indikator `TradeBotLiveView` si na grafe
// najde feed svojho instrumentu a TF a kresli z neho - nic neposiela, na obchodovanie nema vplyv.
//
// Vlakna: feed plni vlakno instancie, cita ho vlakno grafu; vsetko je pod zamkom feedu a von idu len kopie
// (`LiveViewItem`, `LiveViewOrder`, `LiveViewFill`). Kresby sa nepredavaju cele pri kazdej zmene: feed drzi
// aktualny stav objektov (`TB.DrawRegistry`) a log id zmenenych objektov; indikator si pamata, kam v logu
// dosiel, a dostane len zmeny. Nove prehratie historie (novy engine, iny profil) zvysi epochu - indikator
// vtedy zmaze svoje kresby a nakresli vsetko znova. Ked log narastie, feed ho zhusti na aktualne objekty
// (tiez nova epocha).
#region Using declarations
using System;
using System.Collections.Generic;
using TB = TradeBot.Core;
#endregion

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>Kopia jednej kresby enginu na kreslenie mimo vlakna instancie (`Deleted` = objekt zmizol).</summary>
    public sealed class LiveViewItem
    {
        public string Id = "";
        public bool Deleted;
        /// <summary>box / line / label / bg</summary>
        public string Type = "";
        public string Kind = "";
        public long X1Ms, X2Ms;
        public double Y1, Y2;
        public string Color, FillColor, Style, Text, BgColor;
        public int Width = 1;
        public bool Above = true;

        /// <summary>Posledny cas objektu (na orezanie starych kresieb indikatorom).</summary>
        public long LastMs { get { return Math.Max(X1Ms, X2Ms); } }

        internal static LiveViewItem Of(TB.DrawCommand o)
        {
            LiveViewItem v = new LiveViewItem();
            v.Id = o.ObjId;
            TB.DrawBox box = o as TB.DrawBox;
            if (box != null)
            {
                v.Type = "box"; v.Kind = box.Kind; v.X1Ms = box.X1Ms; v.X2Ms = box.X2Ms; v.Y1 = box.Y1; v.Y2 = box.Y2;
                v.Color = box.BorderColor; v.FillColor = box.FillColor; v.Style = box.BorderStyle; v.Width = box.BorderWidth;
                v.Text = box.Text;
                return v;
            }
            TB.DrawLine line = o as TB.DrawLine;
            if (line != null)
            {
                v.Type = "line"; v.Kind = line.Kind; v.X1Ms = line.X1Ms; v.X2Ms = line.X2Ms; v.Y1 = line.Y1; v.Y2 = line.Y2;
                v.Color = line.Color; v.Style = line.Style; v.Width = line.Width; v.Text = line.Text;
                return v;
            }
            TB.DrawLabel label = o as TB.DrawLabel;
            if (label != null)
            {
                v.Type = "label"; v.Kind = label.Kind; v.X1Ms = v.X2Ms = label.XMs; v.Y1 = v.Y2 = label.Y;
                v.Color = label.Color; v.Text = label.Text; v.Above = label.Above; v.BgColor = label.BgColor; v.Style = label.Style;
                return v;
            }
            TB.DrawBg bg = o as TB.DrawBg;
            if (bg != null)
            {
                v.Type = "bg"; v.Kind = bg.Kind; v.X1Ms = bg.X1Ms; v.X2Ms = bg.X2Ms; v.Color = bg.Color;
                return v;
            }
            return null;
        }
    }

    /// <summary>Order instancie, ako ho indikator kresli: cakajuci vstup, alebo pozicia so SL a TP.</summary>
    public sealed class LiveViewOrder
    {
        public string Id = "";
        public bool Long;
        public bool Filled;
        public bool Parked;
        public double Entry, Stop, Target;
        public int Qty;
        /// <summary>Od kedy (ms UTC): vyplnenie vstupu, inak odoslanie.</summary>
        public long SinceMs;

        internal string Signature()
        {
            return Id + "|" + Long + "|" + Filled + "|" + Parked + "|" + Entry + "|" + Stop + "|" + Target + "|" + Qty + "|" + SinceMs;
        }
    }

    /// <summary>Vyplnenie (vstup alebo vystup) s poradovym cislom feedu.</summary>
    public sealed class LiveViewFill
    {
        public int Seq;
        public long Ms;
        public string Id = "";
        public bool Entry;
        /// <summary>Smer obchodu, ked ho instancia pozna.</summary>
        public bool? Long;
        public double Price;
        public double Qty;
        public string Exit = "";
    }

    public sealed class LiveViewFeed
    {
        /// <summary>Log zmien sa zhusti, ked je dlhsi nez toto a zaroven stvornasobok zivych objektov.</summary>
        private const int CompactAt = 50000;
        private const int MaxFills = 500;

        public readonly string Instance, Strategy, Instrument, Account;
        public readonly int Tf;

        private readonly object _gate = new object();
        private TB.DrawRegistry _registry = new TB.DrawRegistry();
        private readonly HashSet<string> _alive = new HashSet<string>();
        private List<string> _log = new List<string>();
        private int _epoch = 1;
        private List<LiveViewOrder> _orders = new List<LiveViewOrder>();
        private string _ordersSig = "";
        private int _ordersRev;
        private readonly List<LiveViewFill> _fills = new List<LiveViewFill>();
        private int _fillSeq;

        public LiveViewFeed(string instance, string strategy, string instrument, int tf, string account)
        {
            Instance = instance; Strategy = strategy; Instrument = instrument; Tf = tf; Account = account;
        }

        // -- strana instancie --------------------------------------------- //

        /// <summary>Nove prehratie historie: engine kresli od zaciatku, stare objekty neplatia.</summary>
        public void Reset()
        {
            lock (_gate)
            {
                _registry = new TB.DrawRegistry();
                _alive.Clear();
                _log = new List<string>();
                _epoch++;
            }
        }

        public void Draw(IList<TB.DrawCommand> commands)
        {
            if (commands == null || commands.Count == 0) return;
            lock (_gate)
            {
                foreach (TB.DrawCommand cmd in commands)
                {
                    TB.DrawCommand target;
                    try { target = _registry.Apply(cmd); }
                    catch (ArgumentException) { continue; }   // objekt bez id - na grafe ho nie je ako menit
                    if (target == null) continue;
                    if (cmd is TB.DrawDelete) _alive.Remove(target.ObjId);
                    else _alive.Add(target.ObjId);
                    _log.Add(target.ObjId);
                }
                if (_log.Count > CompactAt && _log.Count > 4 * _alive.Count)
                {
                    _log = new List<string>(_alive);
                    _epoch++;
                }
            }
        }

        public void SetOrders(List<LiveViewOrder> orders)
        {
            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            foreach (LiveViewOrder o in orders) sb.Append(o.Signature()).Append(';');
            string sig = sb.ToString();
            lock (_gate)
            {
                if (sig == _ordersSig) return;
                _ordersSig = sig;
                _orders = orders;
                _ordersRev++;
            }
        }

        public void AddFill(long ms, string id, bool entry, bool? isLong, double price, double qty, string exit)
        {
            lock (_gate)
            {
                LiveViewFill f = new LiveViewFill();
                f.Seq = ++_fillSeq; f.Ms = ms; f.Id = id ?? ""; f.Entry = entry; f.Long = isLong; f.Price = price; f.Qty = qty;
                f.Exit = exit ?? "";
                _fills.Add(f);
                if (_fills.Count > MaxFills) _fills.RemoveRange(0, _fills.Count - MaxFills);
            }
        }

        // -- strana indikatora -------------------------------------------- //

        /// <summary>Zmeny kresieb od `pos`. Iny `epoch` ako feed = indikator ma zmazat vsetko a dostane vsetko
        /// (vrati true). Kazdy objekt raz, v poslednom stave.</summary>
        public bool ReadDrawings(ref int epoch, ref int pos, List<LiveViewItem> into)
        {
            lock (_gate)
            {
                bool reset = epoch != _epoch || pos > _log.Count;
                if (reset) { epoch = _epoch; pos = 0; }
                HashSet<string> seen = new HashSet<string>();
                for (int i = _log.Count - 1; i >= pos; i--)
                {
                    string id = _log[i];
                    if (!seen.Add(id)) continue;
                    TB.DrawCommand o = _alive.Contains(id) ? _registry.Find(id) : null;
                    LiveViewItem v = o != null ? LiveViewItem.Of(o) : null;
                    if (v == null) { v = new LiveViewItem(); v.Id = id; v.Deleted = true; }
                    into.Add(v);
                }
                into.Reverse();
                pos = _log.Count;
                return reset;
            }
        }

        /// <summary>Ordery, ked sa od `rev` zmenili (inak null).</summary>
        public List<LiveViewOrder> ReadOrders(ref int rev)
        {
            lock (_gate)
            {
                if (rev == _ordersRev) return null;
                rev = _ordersRev;
                return new List<LiveViewOrder>(_orders);
            }
        }

        /// <summary>Fily s poradovym cislom vacsim nez `seq`.</summary>
        public List<LiveViewFill> ReadFills(ref int seq)
        {
            lock (_gate)
            {
                List<LiveViewFill> out_ = new List<LiveViewFill>();
                foreach (LiveViewFill f in _fills)
                    if (f.Seq > seq) out_.Add(f);
                seq = _fillSeq;
                return out_;
            }
        }
    }

    /// <summary>Feedy beziacich instancii v tomto procese NinjaTradera (po rekompilacii nova assembly = novy zoznam,
    /// stara generacia AddOnu svoje instancie zastavi a nova ich zverejni znova).</summary>
    public static class LiveViews
    {
        private static readonly object Gate = new object();
        private static readonly Dictionary<string, LiveViewFeed> Feeds = new Dictionary<string, LiveViewFeed>();

        public static void Publish(LiveViewFeed feed)
        {
            lock (Gate) Feeds[feed.Instance] = feed;
        }

        /// <summary>Odhlasi feed - len ten isty objekt (nova instancia toho isteho id uz moze byt zverejnena).</summary>
        public static void Remove(LiveViewFeed feed)
        {
            lock (Gate)
            {
                LiveViewFeed cur;
                if (Feeds.TryGetValue(feed.Instance, out cur) && ReferenceEquals(cur, feed)) Feeds.Remove(feed.Instance);
            }
        }

        /// <summary>Feedy na instrumente (MasterInstrument.Name) a TF; `strategy` a `account` prazdne = vsetky.</summary>
        public static List<LiveViewFeed> Matching(string instrument, int tf, string strategy, string account)
        {
            List<LiveViewFeed> out_ = new List<LiveViewFeed>();
            lock (Gate)
                foreach (LiveViewFeed f in Feeds.Values)
                {
                    if (!string.Equals(f.Instrument, instrument, StringComparison.OrdinalIgnoreCase) || f.Tf != tf) continue;
                    if (!string.IsNullOrEmpty(strategy) && !string.Equals(f.Strategy, strategy.Trim(), StringComparison.OrdinalIgnoreCase)) continue;
                    if (!string.IsNullOrEmpty(account) && !string.Equals(f.Account, account.Trim(), StringComparison.OrdinalIgnoreCase)) continue;
                    out_.Add(f);
                }
            out_.Sort(delegate(LiveViewFeed a, LiveViewFeed b) { return string.CompareOrdinal(a.Instance, b.Instance); });
            return out_;
        }
    }
}
