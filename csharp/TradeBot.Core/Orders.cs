// Co engine povie adapteru: order intenty, udalosti stavu, kontext trhu a plan obchodu.
// Zrkadlo `tradebot/core/orders.py` a datovej casti `tradebot/core/risk.py`.
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    public enum OrderAction
    {
        Entry,
        Cancel,
        /// <summary>Zavri otvorenu poziciu za trhovu cenu - Pine `strategy.close(immediately=true)`.</summary>
        Close
    }

    /// <summary>Trailing parametre v cenovych bodoch aj v tickoch.</summary>
    public class TrailingPlan
    {
        public readonly double ActivationPriceDistance;
        public readonly double OffsetPriceDistance;
        public readonly double ActivationTicks;
        public readonly double OffsetTicks;

        public TrailingPlan(double activationPriceDistance, double offsetPriceDistance,
                            double activationTicks, double offsetTicks)
        {
            ActivationPriceDistance = activationPriceDistance;
            OffsetPriceDistance = offsetPriceDistance;
            ActivationTicks = activationTicks;
            OffsetTicks = offsetTicks;
        }

        /// <summary>Efektivny stop po zohladneni trailingu - Pine `strategy.exit(trail_points=, trail_offset=)`.
        /// `extreme` je najlepsia cena od vstupu. Stop sa nikdy nevracia spat.</summary>
        public virtual double StopPrice(Direction direction, double entry, double baseStop, double extreme)
        {
            if (direction == Direction.Long)
            {
                if (extreme - entry < ActivationPriceDistance) return baseStop;
                return Math.Max(baseStop, extreme - OffsetPriceDistance);
            }
            if (entry - extreme < ActivationPriceDistance) return baseStop;
            return Math.Min(baseStop, extreme + OffsetPriceDistance);
        }

        /// <summary>Dosiahne sviecka priaznivy extrem skor nez stranu, kde je stop?
        /// Pravidlo broker emulatora TradingView: blizsi extrem k otvaracej cene sa dosiahne skor.</summary>
        public static bool ExtremeBeforeStop(double barOpen, double high, double low, bool isLong)
        {
            return isLong
                ? Math.Abs(barOpen - low) > Math.Abs(high - barOpen)
                : Math.Abs(high - barOpen) > Math.Abs(barOpen - low);
        }
    }

    /// <summary>Hotovy plan obchodu - presne to, co ide do `strategy.entry` + `strategy.exit`.</summary>
    public sealed class TradePlan
    {
        public readonly Direction Direction;
        public readonly double Entry;
        public readonly double StopLoss;
        public readonly double TakeProfit;
        public readonly double Qty;
        public readonly double SlDistance;
        public readonly TrailingPlan Trailing;

        public TradePlan(Direction direction, double entry, double stopLoss, double takeProfit,
                         double qty, double slDistance, TrailingPlan trailing)
        {
            Direction = direction; Entry = entry; StopLoss = stopLoss; TakeProfit = takeProfit;
            Qty = qty; SlDistance = slDistance; Trailing = trailing;
        }

        public double RiskReward
        {
            get { return SlDistance > 0 ? Math.Abs(TakeProfit - Entry) / SlDistance : 0.0; }
        }
    }

    /// <summary>Co ma adapter spravit. Engine sam nikdy neobchoduje.</summary>
    public sealed class OrderIntent
    {
        public readonly OrderAction Action;
        public readonly string OrderId;
        /// <summary>identita zdroja signalu (IBS: uid zony)</summary>
        public readonly int SourceId;
        public Direction? Direction;
        public TradePlan Plan;
        public OrderType OrderType = OrderType.Limit;
        public string Reason = "";

        public OrderIntent(OrderAction action, string orderId, int sourceId)
        {
            Action = action; OrderId = orderId; SourceId = sourceId;
        }

        public OrderIntent(OrderAction action, string orderId, int sourceId, string reason)
            : this(action, orderId, sourceId)
        {
            Reason = reason;
        }

        public void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("a").Value(Action == OrderAction.Entry ? "entry" : (Action == OrderAction.Cancel ? "cancel" : "close"));
            w.Key("id").Value(OrderId).Key("src").Value(SourceId);
            if (Direction.HasValue) w.Key("dir").Value((int)Direction.Value);
            w.Key("ot").Value(EnumText.Text(OrderType));
            if (!string.IsNullOrEmpty(Reason)) w.Key("r").Value(Reason);
            if (Plan != null)
            {
                w.Key("p").BeginObject();
                w.Key("dir").Value((int)Plan.Direction).Key("e").Value(Plan.Entry).Key("sl").Value(Plan.StopLoss);
                w.Key("tp").Value(Plan.TakeProfit).Key("q").Value(Plan.Qty).Key("sd").Value(Plan.SlDistance);
                if (Plan.Trailing != null)
                {
                    w.Key("tr").BeginObject();
                    w.Key("ap").Value(Plan.Trailing.ActivationPriceDistance).Key("op").Value(Plan.Trailing.OffsetPriceDistance);
                    w.Key("at").Value(Plan.Trailing.ActivationTicks).Key("ot").Value(Plan.Trailing.OffsetTicks);
                    w.EndObject();
                }
                w.EndObject();
            }
            w.EndObject();
        }
    }

    /// <summary>Zaznam prechodu - pre logy, diagnostiku a porovnavacie testy.</summary>
    public sealed class StateEvent
    {
        public readonly long TsMs;
        public readonly int ZoneUid;
        public readonly int FromState;
        public readonly int ToState;
        public readonly string Reason;

        public StateEvent(long tsMs, int zoneUid, int fromState, int toState, string reason)
        {
            TsMs = tsMs; ZoneUid = zoneUid; FromState = fromState; ToState = toState; Reason = reason ?? "";
        }

        public void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("ts").Value(TsMs).Key("z").Value(ZoneUid).Key("f").Value(FromState).Key("to").Value(ToState);
            w.Key("r").Value(Reason);
            w.EndObject();
        }
    }

    /// <summary>Co o svete engine sam nevie a musi mu to povedat adapter.</summary>
    public sealed class MarketContext
    {
        public bool InTradeWindow;
        /// <summary>&gt; 0 long, &lt; 0 short, 0 flat - Pine `strategy.position_size`</summary>
        public double PositionSize;
        public bool DailyWinLimitReached;
        /// <summary>+1 bullish, -1 bearish, 0 neurcene</summary>
        public int MarketBias;
        /// <summary>id orderov, ktore u brokera prave realne bezia (vyplnene vstupy)</summary>
        public HashSet<string> OpenOrderIds = new HashSet<string>();
    }
}
