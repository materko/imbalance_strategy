// Nahradne typy NinjaTradera pre simulator poruch (tester/faultsim) - len to, co pouziva
// tradebot/adapters/ninjatrader/TradeBotLiveInstance.cs. Do NinjaTradera sa NEINSTALUJE.
//
// `Account` je falosny broker: ordery prijima, udalosti (OrderUpdate, ExecutionUpdate) drzi vo fronte a dorucuje ich
// az na pokyn scenara, takze poradie "zrusenie vs. fill" a stratene ci odmietnute spravy sa daju predpisat presne.
// Model brokera (co je predpoklad, nie overene spravanie NT) je popisany v docs/SIMULATOR_PORUCH.md.
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using NinjaTrader.Cbi;
using NinjaTrader.Data;

namespace NinjaTrader.Sim
{
    /// <summary>Pravidlo poruchy: co broker urobi s poziadavkou (`submit` / `cancel` / `change`) na order daneho mena.</summary>
    public sealed class Rule
    {
        public string On = "";
        /// <summary>meno orderu; `*` na konci = predpona, prazdne = kazdy</summary>
        public string Match = "";
        /// <summary>reject | ignore | hold | throw</summary>
        public string Then = "";
        public int Times = 1;

        public bool Fits(string on, string name)
        {
            if (Times <= 0 || On != on) return false;
            if (Match.Length == 0) return true;
            if (Match.EndsWith("*", StringComparison.Ordinal)) return name.StartsWith(Match.Substring(0, Match.Length - 1), StringComparison.Ordinal);
            return Match == name;
        }
    }

    /// <summary>Udalost brokera cakajuca na dorucenie.</summary>
    public sealed class Pending
    {
        public Order Order;
        /// <summary>state | fill</summary>
        public string Kind = "state";
        public OrderState State;
        /// <summary>false = sprava o odmietnutej poziadavke, order ostava v stave, v akom bol</summary>
        public bool SetState = true;
        public ErrorCode Error = ErrorCode.NoError;
        public string Comment = "";
        public int Qty;
        public double Price;
        public bool LoseExecution;
        /// <summary>drzana udalost sa nedoruci, kym ju scenar neuvolni (`release`)</summary>
        public bool Held;
    }

    /// <summary>Svet simulacie: hodiny, bary, pravidla poruch, log.</summary>
    public static class World
    {
        public static DateTime Now = new DateTime(2026, 3, 2, 15, 0, 0, DateTimeKind.Utc);
        public static readonly List<Rule> Rules = new List<Rule>();
        public static readonly List<string> Log = new List<string>();
        public static readonly List<BarsRequest> Requests = new List<BarsRequest>();
        public static readonly List<double[]> Bars = new List<double[]>();
        public static readonly List<DateTime> BarTimes = new List<DateTime>();
        public static double LastPrice = 100.0;
        public static string Dir = "";
        public static bool InSession = true;

        public static string Peek(string on, string name)
        {
            foreach (Rule r in Rules)
                if (r.Fits(on, name)) return r.Then;
            return "";
        }

        public static string Take(string on, string name)
        {
            foreach (Rule r in Rules)
                if (r.Fits(on, name)) { r.Times--; return r.Then; }
            return "";
        }

        public static void AddBar(DateTime close, double o, double h, double l, double c)
        {
            Bars.Add(new double[] { o, h, l, c, 100.0 });
            BarTimes.Add(close);
            LastPrice = c;
        }

        public static void RaiseBars(int index)
        {
            foreach (BarsRequest r in Requests.ToArray()) r.Raise(index);
        }
    }
}

namespace NinjaTrader.Core
{
    public sealed class GeneralOptions
    {
        public TimeZoneInfo TimeZoneInfo { get { return TimeZoneInfo.Utc; } }
    }

    public static class Globals
    {
        private static readonly GeneralOptions Options = new GeneralOptions();
        public static DateTime Now { get { return DateTime.SpecifyKind(NinjaTrader.Sim.World.Now, DateTimeKind.Unspecified); } }
        public static DateTime MaxDate { get { return new DateTime(2099, 12, 1); } }
        public static GeneralOptions GeneralOptions { get { return Options; } }
        public static string UserDataDir { get { return NinjaTrader.Sim.World.Dir; } }
    }
}

namespace NinjaTrader.Cbi
{
    public enum OrderState { Initialized, Submitted, Accepted, Working, PartFilled, Filled, CancelPending, CancelSubmitted, Cancelled, ChangePending, ChangeSubmitted, Rejected, TriggerPending, Unknown }
    public enum OrderAction { Buy, BuyToCover, Sell, SellShort }
    public enum OrderType { Limit, Market, MIT, StopLimit, StopMarket }
    public enum OrderEntry { Automated, Manual }
    public enum TimeInForce { Day, Gtc }
    public enum MarketPosition { Flat, Long, Short }
    public enum ConnectionStatus { Connected, Connecting, ConnectionLost, Disconnected, Disconnecting }
    public enum ErrorCode { NoError, OrderRejected, UnableToCancelOrder, UnableToChangeOrder, Panic }
    public enum Currency { UsDollar, Euro }

    public sealed class MasterInstrument
    {
        public string Name = "SIM";
        public double TickSize = 0.25;
        public double PointValue = 2.0;
        public Currency Currency = Currency.UsDollar;
        public TradingHours TradingHours = new TradingHours();

        public double RoundToTickSize(double price)
        {
            return Math.Round(price / TickSize, MidpointRounding.AwayFromZero) * TickSize;
        }
    }

    public sealed class Instrument
    {
        public static readonly Dictionary<string, Instrument> Known = new Dictionary<string, Instrument>();
        public string FullName = "";
        public MasterInstrument MasterInstrument = new MasterInstrument();

        public static Instrument GetInstrument(string name)
        {
            Instrument i;
            return Known.TryGetValue(name, out i) ? i : null;
        }
    }

    public sealed class ConnectionOptions { public string Name = "Sim"; }

    public sealed class Connection { public ConnectionOptions Options = new ConnectionOptions(); }

    public sealed class Order
    {
        public string Name = "";
        public Instrument Instrument;
        public Account Account;
        public OrderState OrderState = OrderState.Initialized;
        public OrderAction OrderAction;
        public OrderType OrderType;
        public int Quantity, QuantityChanged;
        public double LimitPrice, LimitPriceChanged, StopPrice, StopPriceChanged;
        public int Filled;
        public double AverageFillPrice;
        public string Oco = "";
        public DateTime Time;
        public int Seq;

        public bool IsLong { get { return OrderAction == OrderAction.Buy || OrderAction == OrderAction.BuyToCover; } }

        public bool IsTerminal
        {
            get { return OrderState == OrderState.Filled || OrderState == OrderState.Cancelled || OrderState == OrderState.Rejected; }
        }
    }

    public sealed class Execution
    {
        public Order Order;
        public string Name = "";
        public Instrument Instrument;
        public DateTime Time;
        public double Price;
        public int Quantity;
        public MarketPosition MarketPosition;
    }

    public sealed class Position
    {
        public Instrument Instrument;
        public MarketPosition MarketPosition;
        public int Quantity;
        public double AveragePrice;
    }

    public sealed class OrderEventArgs : EventArgs
    {
        public Order Order;
        public OrderState OrderState;
        public ErrorCode Error;
        public string Comment = "";
    }

    public sealed class ExecutionEventArgs : EventArgs
    {
        public Execution Execution;
        public double Price;
        public int Quantity;
        public DateTime Time;
    }

    /// <summary>Falosny ucet = falosny broker.</summary>
    public sealed class Account
    {
        public static readonly Collection<Account> All = new Collection<Account>();

        public string Name = "";
        public ConnectionStatus ConnectionStatus = ConnectionStatus.Connected;
        public Connection Connection = new Connection();
        public readonly Collection<Order> Orders = new Collection<Order>();
        public readonly Collection<Execution> Executions = new Collection<Execution>();
        private readonly Collection<Position> _positions = new Collection<Position>();
        private readonly Collection<Position> _none = new Collection<Position>();
        /// <summary>Po vypadku spojenia ucet chvilu ziadne pozicie neukazuje.</summary>
        public bool HidePositions;
        public Collection<Position> Positions { get { return HidePositions ? _none : _positions; } }

        public event EventHandler<OrderEventArgs> OrderUpdate;
        public event EventHandler<ExecutionEventArgs> ExecutionUpdate;

        public readonly List<NinjaTrader.Sim.Pending> Queue = new List<NinjaTrader.Sim.Pending>();
        /// <summary>Vsetko, co adapter od brokera chcel (pre vypis scenara).</summary>
        public readonly List<string> Requests = new List<string>();
        private int _seq;

        public int Net;
        public double AvgPrice;

        public void DropSubscribers() { OrderUpdate = null; ExecutionUpdate = null; }

        public Order CreateOrder(Instrument instrument, OrderAction action, OrderType type, OrderEntry entry, TimeInForce tif,
                                 int quantity, double limitPrice, double stopPrice, string oco, string name, DateTime gtd, object custom)
        {
            Order o = new Order();
            o.Instrument = instrument; o.Account = this; o.OrderAction = action; o.OrderType = type;
            o.Quantity = quantity; o.LimitPrice = limitPrice; o.StopPrice = stopPrice; o.Oco = oco ?? ""; o.Name = name ?? "";
            o.Seq = ++_seq;
            return o;
        }

        private static string Describe(Order o)
        {
            string px = o.OrderType == OrderType.Limit ? " @" + o.LimitPrice : (o.OrderType == OrderType.StopMarket ? " stop " + o.StopPrice : "");
            return o.Name + " " + (o.IsLong ? "buy" : "sell") + " " + o.OrderType + " x" + o.Quantity + px;
        }

        private void Enqueue(Order o, OrderState state)
        {
            NinjaTrader.Sim.Pending p = new NinjaTrader.Sim.Pending();
            p.Order = o; p.State = state;
            Queue.Add(p);
        }

        private void Refuse(Order o, ErrorCode code, string comment, bool terminal)
        {
            NinjaTrader.Sim.Pending p = new NinjaTrader.Sim.Pending();
            p.Order = o; p.State = OrderState.Rejected; p.SetState = terminal; p.Error = code; p.Comment = comment;
            Queue.Add(p);
        }

        public void QueueFill(Order o, int qty, double price, bool loseExecution)
        {
            NinjaTrader.Sim.Pending p = new NinjaTrader.Sim.Pending();
            p.Order = o; p.Kind = "fill"; p.Qty = qty; p.Price = price; p.LoseExecution = loseExecution;
            Queue.Add(p);
        }

        public void Submit(IEnumerable<Order> orders)
        {
            List<Order> list = new List<Order>(orders);
            foreach (Order o in list)
                if (NinjaTrader.Sim.World.Peek("submit", o.Name) == "throw")
                {
                    NinjaTrader.Sim.World.Take("submit", o.Name);
                    Requests.Add("submit " + Describe(o) + " -> vynimka");
                    throw new InvalidOperationException("sim: Submit zlyhal");
                }
            foreach (Order o in list)
            {
                o.Time = NinjaTrader.Sim.World.Now;
                o.OrderState = OrderState.Submitted;
                lock (Orders) Orders.Add(o);
                string then = NinjaTrader.Sim.World.Take("submit", o.Name);
                Requests.Add("submit " + Describe(o) + (then.Length > 0 ? " -> " + then : ""));
                if (then == "ignore") continue;
                if (then == "reject") { Refuse(o, ErrorCode.OrderRejected, "sim: order odmietnuty", true); continue; }
                Enqueue(o, OrderState.Accepted);
                Enqueue(o, OrderState.Working);
                if (o.OrderType == OrderType.Market && then != "hold") QueueFill(o, o.Quantity, NinjaTrader.Sim.World.LastPrice, false);
            }
        }

        public void Cancel(IEnumerable<Order> orders)
        {
            foreach (Order o in new List<Order>(orders))
            {
                string then = o.IsTerminal ? "uz prec" : NinjaTrader.Sim.World.Take("cancel", o.Name);
                Requests.Add("cancel " + o.Name + (then.Length > 0 ? " -> " + then : ""));
                if (then == "throw") throw new InvalidOperationException("sim: Cancel zlyhal");
                if (then == "ignore" || then == "uz prec") continue;
                if (then == "reject") { Refuse(o, ErrorCode.UnableToCancelOrder, "sim: zrusenie odmietnute", false); continue; }
                NinjaTrader.Sim.Pending p = new NinjaTrader.Sim.Pending();
                p.Order = o; p.State = OrderState.Cancelled; p.Held = then == "hold";
                Queue.Add(p);
            }
        }

        public void Change(IEnumerable<Order> orders)
        {
            foreach (Order o in new List<Order>(orders))
            {
                string then = o.IsTerminal ? "uz prec" : NinjaTrader.Sim.World.Take("change", o.Name);
                Requests.Add("change " + o.Name + " qty " + o.QuantityChanged + " stop " + o.StopPriceChanged + (then.Length > 0 ? " -> " + then : ""));
                if (then == "throw") throw new InvalidOperationException("sim: Change zlyhal");
                if (then == "ignore" || then == "uz prec") continue;
                if (then == "reject") { Refuse(o, ErrorCode.UnableToChangeOrder, "sim: zmena odmietnuta", false); continue; }
                if (o.QuantityChanged > 0) o.Quantity = o.QuantityChanged;
                if (o.StopPriceChanged > 0) o.StopPrice = o.StopPriceChanged;
                if (o.LimitPriceChanged > 0) o.LimitPrice = o.LimitPriceChanged;
                Enqueue(o, OrderState.Working);
            }
        }

        /// <summary>Doruci jednu udalost adapteru. Vracia false, ked uz neplati (order medzitym skoncil).</summary>
        public bool Deliver(NinjaTrader.Sim.Pending p)
        {
            Order o = p.Order;
            if (p.Kind == "fill")
            {
                if (o.OrderState == OrderState.Cancelled || o.OrderState == OrderState.Rejected || o.Filled >= o.Quantity) return false;
                int qty = Math.Min(p.Qty, o.Quantity - o.Filled);
                o.AverageFillPrice = (o.AverageFillPrice * o.Filled + p.Price * qty) / (o.Filled + qty);
                o.Filled += qty;
                o.OrderState = o.Filled >= o.Quantity ? OrderState.Filled : OrderState.PartFilled;
                Raise(o, o.OrderState, ErrorCode.NoError, "");
                Execution x = new Execution();
                x.Order = o; x.Name = o.Name; x.Instrument = o.Instrument; x.Time = NinjaTrader.Core.Globals.Now; x.Price = p.Price; x.Quantity = qty;
                x.MarketPosition = o.IsLong ? MarketPosition.Long : MarketPosition.Short;
                lock (Executions) Executions.Add(x);
                Book(o, qty, p.Price);
                if (!p.LoseExecution)
                {
                    EventHandler<ExecutionEventArgs> h = ExecutionUpdate;
                    if (h != null)
                    {
                        ExecutionEventArgs e = new ExecutionEventArgs();
                        e.Execution = x; e.Price = p.Price; e.Quantity = qty; e.Time = x.Time;
                        h(this, e);
                    }
                }
                if (o.OrderState == OrderState.Filled) CancelSiblings(o);
                return true;
            }
            if (p.SetState)
            {
                if (o.IsTerminal) return false;
                if (p.State != OrderState.Cancelled && p.State != OrderState.Rejected && o.OrderState == OrderState.PartFilled) return false;
                o.OrderState = p.State;
            }
            Raise(o, p.State, p.Error, p.Comment);
            if (p.SetState && p.State == OrderState.Cancelled) CancelSiblings(o);
            return true;
        }

        /// <summary>OCO: vyplneny alebo zruseny order stiahne ostatne zo svojej skupiny.</summary>
        private void CancelSiblings(Order o)
        {
            if (o.Oco.Length == 0) return;
            List<Order> all;
            lock (Orders) all = new List<Order>(Orders);
            foreach (Order s in all)
                if (!ReferenceEquals(s, o) && s.Oco == o.Oco && !s.IsTerminal && !Queue.Exists(delegate(NinjaTrader.Sim.Pending q) { return ReferenceEquals(q.Order, s) && q.Kind == "state" && q.State == OrderState.Cancelled; }))
                    Enqueue(s, OrderState.Cancelled);
        }

        private void Raise(Order o, OrderState state, ErrorCode error, string comment)
        {
            EventHandler<OrderEventArgs> h = OrderUpdate;
            if (h == null) return;
            OrderEventArgs e = new OrderEventArgs();
            e.Order = o; e.OrderState = state; e.Error = error; e.Comment = comment;
            h(this, e);
        }

        private void Book(Order o, int qty, double price)
        {
            int signed = o.IsLong ? qty : -qty;
            int after = Net + signed;
            if (Net == 0 || Math.Sign(Net) == Math.Sign(signed)) AvgPrice = (AvgPrice * Math.Abs(Net) + price * qty) / Math.Max(1, Math.Abs(after));
            else if (Math.Sign(after) != Math.Sign(Net)) AvgPrice = after == 0 ? 0.0 : price;
            Net = after;
            lock (_positions)
            {
                _positions.Clear();
                if (Net != 0)
                {
                    Position pos = new Position();
                    pos.Instrument = o.Instrument;
                    pos.MarketPosition = Net > 0 ? MarketPosition.Long : MarketPosition.Short;
                    pos.Quantity = Math.Abs(Net);
                    pos.AveragePrice = AvgPrice;
                    _positions.Add(pos);
                }
            }
        }
    }
}

namespace NinjaTrader.Data
{
    public enum BarsPeriodType { Tick, Minute, Day }
    public enum MergePolicy { DoNotMerge, MergeBackAdjusted }

    public sealed class TradingHours { }

    public sealed class BarsPeriod
    {
        public BarsPeriodType BarsPeriodType;
        public int Value;
    }

    public class BarsSeries
    {
        public int Count { get { return NinjaTrader.Sim.World.Bars.Count; } }
        public DateTime GetTime(int i) { return DateTime.SpecifyKind(NinjaTrader.Sim.World.BarTimes[i], DateTimeKind.Unspecified); }
        public double GetOpen(int i) { return NinjaTrader.Sim.World.Bars[i][0]; }
        public double GetHigh(int i) { return NinjaTrader.Sim.World.Bars[i][1]; }
        public double GetLow(int i) { return NinjaTrader.Sim.World.Bars[i][2]; }
        public double GetClose(int i) { return NinjaTrader.Sim.World.Bars[i][3]; }
        public double GetVolume(int i) { return NinjaTrader.Sim.World.Bars[i][4]; }
    }

    public sealed class Bars : BarsSeries { }

    public sealed class BarsUpdateEventArgs : EventArgs
    {
        public BarsSeries BarsSeries;
        public int MinIndex, MaxIndex;
    }

    /// <summary>Simulator pozna len 1m graf: kazda seria dostane tie iste bary sveta.</summary>
    public sealed class BarsRequest : IDisposable
    {
        public BarsPeriod BarsPeriod;
        public TradingHours TradingHours;
        public MergePolicy MergePolicy;
        public Bars Bars;
        public event EventHandler<BarsUpdateEventArgs> Update;

        public BarsRequest(NinjaTrader.Cbi.Instrument instrument, int barsBack) { }

        public void Request(Action<BarsRequest, ErrorCode, string> callback)
        {
            if (BarsPeriod == null || BarsPeriod.Value != 1) { callback(this, ErrorCode.Panic, "simulator pozna len 1m graf"); return; }
            Bars = new Bars();
            NinjaTrader.Sim.World.Requests.Add(this);
            callback(this, ErrorCode.NoError, "");
        }

        public void Raise(int index)
        {
            EventHandler<BarsUpdateEventArgs> h = Update;
            if (h == null) return;
            BarsUpdateEventArgs e = new BarsUpdateEventArgs();
            e.BarsSeries = Bars; e.MinIndex = index; e.MaxIndex = index;
            h(this, e);
        }

        public void Dispose() { NinjaTrader.Sim.World.Requests.Remove(this); }
    }

    public sealed class SessionIterator
    {
        public SessionIterator(TradingHours hours) { }
        public DateTime ActualSessionEnd { get { return NinjaTrader.Core.Globals.Now.Date.AddDays(1); } }
        public bool IsInSession(DateTime time, bool includesEndTimeStamp, bool isIntraDay) { return NinjaTrader.Sim.World.InSession; }
        public bool GetNextSession(DateTime time, bool includesEndTimeStamp) { return true; }
    }
}

namespace NinjaTrader.NinjaScript.AddOns
{
    /// <summary>Z AddOnu instancia potrebuje len adresare, log a pripojenie.</summary>
    public static class TradeBotLiveAddOn
    {
        public static string TradeBotDir { get { return System.IO.Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "TradeBot"); } }
        public static string ProfilesDir { get { return System.IO.Path.Combine(TradeBotDir, "profiles"); } }
        public static string SpoolDir { get { return System.IO.Path.Combine(TradeBotDir, "spool"); } }
        public static string ControlDir { get { return System.IO.Path.Combine(TradeBotDir, "control"); } }
        public static string StateDir { get { return System.IO.Path.Combine(TradeBotDir, "state"); } }

        public static void Say(string text)
        {
            NinjaTrader.Sim.World.Log.Add(NinjaTrader.Sim.World.Now.ToString("HH:mm:ss", System.Globalization.CultureInfo.InvariantCulture) + " " + text);
        }

        public static bool EnsureConnected(string name, int seconds) { return true; }
    }
}
