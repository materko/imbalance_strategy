// Zivotny cyklus zony STATE 0 -> 5 - zrkadlo `tradebot/strategies/ibs/statemachine.py` (Pine 1534-2270)
// a vypoctu SL/TP/velkosti z `tradebot/core/risk.py` (Pine 1944-2016).
//
//   0 cena sa dotkne zony a hlada sa v nej gap
//   1 gap najdeny, caka sa na vystup zo zony        (max state1MaxBars)
//   2 cena vysla, caka sa na potvrdenie zavretim    (max state2MaxBars)
//   3 potvrdene, caka sa na retest vstupnej ceny    (max state3MaxBars)
//   4 polozi sa order
//   5 caka sa na vyplnenie                          (max state5MaxBars)
//
// Pin Bar a Engulfing model preskakuju rovno z 0 do 4. Engine dostava len uzavrete bary.
using System;
using System.Collections.Generic;
using TradeBot.Core;
using TradeBot.Strategies.IbsNet.Ta;

namespace TradeBot.Strategies.IbsNet
{
    public static class ZoneState
    {
        public const int Invalid = -1;
        public const int Waiting = 0;
        public const int GapFound = 1;
        public const int LeftZone = 2;
        public const int Confirmed = 3;
        public const int Ready = 4;
        public const int OrderPending = 5;
    }

    /// <summary>Stop loss, take profit, velkost pozicie a trailing.</summary>
    public static class Risk
    {
        /// <summary>Pine 1952-1966 - SL z najextremnejsieho swingu za `slLookback` barov.</summary>
        public static double SwingStopLoss(BarHistory history, Direction direction, IbsConfig cfg, InstrumentSpec inst,
                                           double zoneTop, double zoneBot, double atr)
        {
            double? swing = null;
            for (int lb = 0; lb < cfg.slLookback; lb++)
            {
                if (!history.Has(lb)) break;
                Bar bar = history[lb];
                if (direction == Direction.Long)
                {
                    if (!swing.HasValue || bar.Low < swing.Value) swing = bar.Low;
                }
                else
                {
                    if (!swing.HasValue || bar.High > swing.Value) swing = bar.High;
                }
            }

            double buffer = cfg.slBufferTicks.Resolve(inst, history.Current.Close, atr);
            if (direction == Direction.Long) return (swing.HasValue ? swing.Value : zoneBot) - buffer;
            return (swing.HasValue ? swing.Value : zoneTop) + buffer;
        }

        public static TrailingPlan BuildTrailing(IbsConfig cfg, InstrumentSpec inst, double slDistance)
        {
            if (!cfg.enableTrailing || slDistance <= 0 || inst.TickSize <= 0) return null;
            double activation = cfg.trailActivationR * slDistance;
            double offset = cfg.trailOffsetR * slDistance;
            return new TrailingPlan(activation, offset, activation / inst.TickSize, offset / inst.TickSize);
        }

        /// <summary>Dopocita TP z `rrRatio`, velkost pozicie a trailing.</summary>
        public static TradePlan BuildTradePlan(Direction direction, double entry, double stopLoss, IbsConfig cfg, InstrumentSpec inst)
        {
            double slDistance = direction == Direction.Long ? (entry - stopLoss) : (stopLoss - entry);
            double takeProfit = direction == Direction.Long
                ? entry + slDistance * cfg.rrRatio
                : entry - slDistance * cfg.rrRatio;
            double qty = cfg.maxLossDollar > 0 ? cfg.PositionQty(inst, cfg.maxLossDollar, slDistance) : 1.0;
            return new TradePlan(direction, entry, stopLoss, takeProfit, qty, slDistance, BuildTrailing(cfg, inst, slDistance));
        }
    }

    /// <summary>Posuva vsetky zony o jeden bar. Stav drzi v samotnych `Zone` objektoch.</summary>
    public sealed class StateMachine
    {
        private readonly IbsConfig _cfg;
        private readonly InstrumentSpec _inst;
        private readonly ZoneBook _book;
        public List<StateEvent> Events = new List<StateEvent>();
        /// <summary>Pine `box.set_*` volania z tohto baru - engine ich pripoji k vystupu.</summary>
        public List<DrawCommand> Drawings = new List<DrawCommand>();
        /// <summary>`tradeDirection = Indicator`; bez neho sa smer indikatorom neobmedzuje.</summary>
        public DirectionGate DirectionGate;

        /// <summary>Pine `stateLabelMax` - graf drzi len poslednych tolko cisel stavov, starsie sa zmazu.</summary>
        public const int StateLabelMax = 350;
        /// <summary>Pine `stateLabelPool` pre cisla stavov (obj_id v poradi vzniku).</summary>
        private readonly Queue<string> _stateLabels = new Queue<string>();
        /// <summary>Pine `lblCountUp` / `lblCountDown` - cisla viacerych zon na jednom bare idu pod seba.</summary>
        private int _lblUp, _lblDown;
        /// <summary>Pine lokalne `st` ostane po timeoute STATE 1-3 na starej hodnote (zona je uz -1).</summary>
        private int? _timeoutSt;

        public StateMachine(IbsConfig cfg, InstrumentSpec inst, ZoneBook book)
        {
            _cfg = cfg; _inst = inst; _book = book;
        }

        /// <summary>Pine `str.tostring(float)` - bez nadbytocnych nul, `na` ako "NaN".</summary>
        public static string PineToString(double? v)
        {
            if (!v.HasValue) return "NaN";
            return v.Value.ToString("0.##########", System.Globalization.CultureInfo.InvariantCulture);
        }

        public List<OrderIntent> OnBar(Bar bar, BarHistory history, MarketContext ctx, double atr)
        {
            List<OrderIntent> intents = new List<OrderIntent>();
            Events = new List<StateEvent>();
            Drawings = new List<DrawCommand>();
            _lblUp = 0;
            _lblDown = 0;

            Expire(bar);

            foreach (Zone zone in new List<Zone>(_book.Zones))
            {
                if (!IsActive(zone)) continue;
                intents.AddRange(Advance(zone, bar, history, ctx, atr));
            }
            return intents;
        }

        /// <summary>Pine 2271-2288 - koniec KAZDEJ seansy utne zony v STATE 0-3.</summary>
        public void CutFormingZones(Bar bar)
        {
            foreach (Zone z in new List<Zone>(_book.Zones))
                if (z.State >= 0 && z.State <= 3) Invalidate(z, bar, "koniec seansy");
        }

        /// <summary>Pine 2291-2318 - koniec poslednej seansy dna zmete vsetko zo stola. Volat az po `OnBar`.</summary>
        public List<OrderIntent> CloseSession(Bar bar, MarketContext ctx)
        {
            List<OrderIntent> intents = new List<OrderIntent>();
            foreach (Zone z in new List<Zone>(_book.Zones))
            {
                if (!(z.State >= 0 && z.State <= 5)) continue;
                if (z.State >= 1)
                {
                    intents.Add(new OrderIntent(OrderAction.Cancel, z.OrderId, z.Uid, "koniec seansy"));
                    if (z.State == 5 && ctx.OpenOrderIds.Contains(z.OrderId))
                        intents.Add(new OrderIntent(OrderAction.Close, z.OrderId, z.Uid, "SESSION_END"));
                }
                Invalidate(z, bar, "koniec seansy");
            }
            return intents;
        }

        // ------------------------------------------------------------------ //

        /// <summary>Pine 665-681 - zona, ktorej vyprsala platnost a este nebola pouzita, sa oznaci ako `used`.</summary>
        private void Expire(Bar bar)
        {
            foreach (Zone z in _book.Zones)
            {
                if (!z.Used && bar.Time >= z.ExpiresMs)
                {
                    z.Used = true;
                    Events.Add(new StateEvent(bar.Time, z.Uid, z.State, z.State, "zona expirovala"));
                    Drawings.AddRange(z.ResizeOnInvalidation(bar.Time));
                }
            }
        }

        /// <summary>Pine: `(not used and st >= 0) or (used and 2 <= st <= 5)`.</summary>
        private static bool IsActive(Zone z)
        {
            if (!z.Used) return z.State >= ZoneState.Waiting;
            return z.State >= ZoneState.LeftZone && z.State <= ZoneState.OrderPending;
        }

        private void Transition(Zone z, int to, Bar bar, string reason)
        {
            Events.Add(new StateEvent(bar.Time, z.Uid, z.State, to, reason));
            z.State = to;
        }

        private void Invalidate(Zone z, Bar bar, string reason)
        {
            Transition(z, ZoneState.Invalid, bar, reason);
            z.Used = true;
            Drawings.AddRange(z.ResizeOnInvalidation(bar.Time));
        }

        // ------------------------------------------------------------------ //

        private List<OrderIntent> Advance(Zone z, Bar bar, BarHistory history, MarketContext ctx, double atr)
        {
            List<OrderIntent> intents = new List<OrderIntent>();
            _timeoutSt = null;

            if (z.State == ZoneState.Waiting) State0(z, bar, history, atr);

            if (_cfg.enableImbEntry && z.State >= ZoneState.GapFound && z.State <= ZoneState.Ready)
                intents.AddRange(ReEntry(z, bar, history, atr));

            if (z.State >= ZoneState.GapFound && z.State <= ZoneState.OrderPending) MarkPassedThrough(z, bar);

            if (z.State == ZoneState.GapFound) State1(z, bar, history);
            if (z.State == ZoneState.LeftZone) State2(z, bar, history, atr);
            if (z.State == ZoneState.Confirmed) State3(z, bar, history, ctx);
            if (z.State == ZoneState.Ready) intents.AddRange(State4(z, bar, history, ctx, atr));
            if (z.State == ZoneState.OrderPending) intents.AddRange(State5(z, bar, history, ctx));

            DrawStateLabel(z, bar, history);
            return intents;
        }

        // ---- STATE 0 ------------------------------------------------------- //

        private void State0(Zone z, Bar bar, BarHistory history, double atr)
        {
            bool isLong = z.Direction == Direction.Long;

            if (!z.Touched)
            {
                // Pine `correctApproach` - dotyk musi prist zo spravnej strany.
                bool approach = isLong
                    ? (bar.Low <= z.Top && bar.High >= z.Top)
                    : (bar.High >= z.Bot && bar.Low <= z.Bot);
                if (approach)
                {
                    z.Touched = true;
                    z.TouchedBarIndex = history.BarIndex;
                }
            }

            if (!z.Touched) return;

            bool inZone = bar.High >= z.Bot && bar.Low <= z.Top;
            bool invalidated = isLong ? (bar.Low < z.Bot) : (bar.High > z.Top);

            if (_cfg.enablePinBarEntry)
            {
                if (inZone && Patterns.IsPinBar(bar, z.Direction, _cfg, _inst, atr))
                {
                    ArmFromCandle(z, bar, history, atr);
                    return;
                }
                if (invalidated)
                {
                    Invalidate(z, bar, "PIN BAR: cena presla zonou");
                    return;
                }
            }

            if (_cfg.enableEngulfingEntry && z.State == ZoneState.Waiting)
            {
                // „Okno trpezlivosti": prvych engTouchWindowBars barov po dotyku sa zona neinvaliduje.
                bool withinWindow = !z.TouchedBarIndex.HasValue
                    || (history.BarIndex - z.TouchedBarIndex.Value) <= _cfg.engTouchWindowBars;
                if (inZone && Patterns.IsEngulfing(history, z.Direction, _cfg, _inst, atr))
                {
                    ArmFromCandle(z, bar, history, atr);
                    return;
                }
                if (!withinWindow && invalidated)
                {
                    Invalidate(z, bar, "ENGULFING: cena presla zonou");
                    return;
                }
            }

            if (_cfg.enableImbEntry && _cfg.enableGapDetection && z.State == ZoneState.Waiting)
            {
                ImbalanceHit hit = Patterns.FindImbalance(history, z.Top, z.Bot, z.Direction, _cfg, _inst, z.CreatedBarIndex, atr);
                if (hit != null)
                {
                    TakeHit(z, hit);
                    z.StateBarIndex = history.BarIndex;
                    Transition(z, ZoneState.GapFound, bar, "gap @ " + hit.BarIndex);
                }
                else if (invalidated)
                {
                    Invalidate(z, bar, "IMB: cena presla zonou");
                }
            }
        }

        private static void TakeHit(Zone z, ImbalanceHit hit)
        {
            z.ImbBodyTop = hit.BodyTop;
            z.ImbBodyBot = hit.BodyBot;
            z.ImbOpen = hit.Open;
            z.ImbHigh = hit.High;
            z.ImbLow = hit.Low;
            z.ImbBarIndex = hit.BarIndex;
        }

        /// <summary>Pin Bar / Engulfing: zona ide rovno do STATE 4 a SL je z tejto sviecky.</summary>
        private void ArmFromCandle(Zone z, Bar bar, BarHistory history, double atr)
        {
            double buffer = _cfg.slBufferTicks.Resolve(_inst, bar.Close, atr);
            z.ImbBodyTop = bar.BodyTop;
            z.ImbBodyBot = bar.BodyBottom;
            z.ImbOpen = bar.Close; // vstup je na zavreti, nie na otvoreni
            z.ImbHigh = bar.High;
            z.ImbLow = bar.Low;
            z.ImbBarIndex = history.BarIndex;
            z.OrderSl = z.Direction == Direction.Long ? (bar.Low - buffer) : (bar.High + buffer);
            z.StateBarIndex = history.BarIndex;
            z.StateTimeMs = bar.Time;
            Transition(z, ZoneState.Ready, bar, "pattern entry");
        }

        // ---- RE-ENTRY ------------------------------------------------------ //

        /// <summary>Pine 1710-1770 - cena sa vratila a nasiel sa INY gap nez ten, na ktorom uz bezi order.</summary>
        private List<OrderIntent> ReEntry(Zone z, Bar bar, BarHistory history, double atr)
        {
            List<OrderIntent> none = new List<OrderIntent>();
            bool isLong = z.Direction == Direction.Long;

            bool reTouch = isLong
                ? (bar.Low <= z.Top && bar.High >= z.Top)
                : (bar.High >= z.Bot && bar.Low <= z.Bot);
            if (!(reTouch && _cfg.enableGapDetection)) return none;

            ImbalanceHit hit = Patterns.FindImbalance(history, z.Top, z.Bot, z.Direction, _cfg, _inst, z.CreatedBarIndex, atr);
            if (hit == null || (z.ImbBarIndex.HasValue && hit.BarIndex == z.ImbBarIndex.Value)) return none;

            TakeHit(z, hit);
            z.Imb0Drawn = false;
            z.Filled = false;
            z.PendingInvalid = false;
            z.Ordered = false;
            z.OrderSl = null;
            z.EntryDone = false;
            z.Used = false;
            z.StateBarIndex = history.BarIndex;
            Transition(z, ZoneState.GapFound, bar, "re-entry: iny gap");

            none.Add(new OrderIntent(OrderAction.Cancel, z.OrderId, z.Uid, "re-entry"));
            return none;
        }

        /// <summary>Pine: cena presla zonou naskrz - zona sa oznaci, ale hned nezanika.</summary>
        private static void MarkPassedThrough(Zone z, Bar bar)
        {
            bool passed = z.Direction == Direction.Long
                ? (bar.High >= z.Top && bar.Low < z.Bot)
                : (bar.Low <= z.Bot && bar.High > z.Top);
            if (passed && !z.PendingInvalid) z.PendingInvalid = true;
        }

        // ---- STATE 1-3 ------------------------------------------------------ //

        private static int BarsInState(Zone z, BarHistory history)
        {
            if (!z.StateBarIndex.HasValue) z.StateBarIndex = history.BarIndex;
            return history.BarIndex - z.StateBarIndex.Value;
        }

        private void State1(Zone z, Bar bar, BarHistory history)
        {
            if (BarsInState(z, history) > _cfg.state1MaxBars)
            {
                _timeoutSt = ZoneState.GapFound;
                Invalidate(z, bar, "STATE1 timeout");
                return;
            }
            bool left = z.Direction == Direction.Long
                ? (bar.High > z.Top && bar.Low <= z.Top)
                : (bar.Low < z.Bot && bar.High >= z.Bot);
            if (left)
            {
                z.StateBarIndex = history.BarIndex;
                z.StateTimeMs = bar.Time;
                z.Used = true;
                Transition(z, ZoneState.LeftZone, bar, "vystup zo zony");
            }
        }

        private void State2(Zone z, Bar bar, BarHistory history, double atr)
        {
            if (BarsInState(z, history) > _cfg.state2MaxBars)
            {
                _timeoutSt = ZoneState.LeftZone;
                Invalidate(z, bar, "STATE2 timeout");
                return;
            }
            double confirm = _cfg.state2ConfirmTicks.Resolve(_inst, bar.Close, atr);
            bool ok = z.Direction == Direction.Long
                ? (z.ImbBodyTop.HasValue && bar.Close > z.ImbBodyTop.Value + confirm)
                : (z.ImbBodyBot.HasValue && bar.Close < z.ImbBodyBot.Value - confirm);
            if (ok)
            {
                z.StateBarIndex = history.BarIndex;
                Transition(z, ZoneState.Confirmed, bar, "potvrdene zavretim");
            }
        }

        private void State3(Zone z, Bar bar, BarHistory history, MarketContext ctx)
        {
            if (BarsInState(z, history) > _cfg.state3MaxBars)
            {
                _timeoutSt = ZoneState.Confirmed;
                Invalidate(z, bar, "STATE3 timeout");
                return;
            }
            if (!z.ImbOpen.HasValue || !ctx.InTradeWindow) return;

            bool retest = z.Direction == Direction.Long ? bar.Low <= z.ImbOpen.Value : bar.High >= z.ImbOpen.Value;
            if (retest)
            {
                z.StateBarIndex = history.BarIndex;
                z.StateTimeMs = bar.Time;
                Transition(z, ZoneState.Ready, bar, "retest vstupnej ceny");
            }
        }

        // ---- STATE 4 -------------------------------------------------------- //

        private List<OrderIntent> State4(Zone z, Bar bar, BarHistory history, MarketContext ctx, double atr)
        {
            List<OrderIntent> intents = new List<OrderIntent>();

            if (ctx.DailyWinLimitReached)
            {
                Invalidate(z, bar, "MAX DAILY");
                return intents;
            }

            if (!ctx.InTradeWindow)
            {
                Invalidate(z, bar, "mimo trade okna");
                intents.Add(new OrderIntent(OrderAction.Cancel, z.OrderId, z.Uid, "mimo trade okna"));
                return intents;
            }

            // Pine: ina zona uz obchoduje ten isty gap -> tato sa zahodi.
            if (!z.Ordered)
            {
                foreach (Zone other in _book.Zones)
                {
                    if (ReferenceEquals(other, z) || !other.Ordered) continue;
                    if (other.State != ZoneState.Ready && other.State != ZoneState.OrderPending) continue;
                    bool sameBar = other.ImbBarIndex == z.ImbBarIndex;
                    bool sameOpen = z.ImbOpen.HasValue && other.ImbOpen == z.ImbOpen;
                    if (sameBar || sameOpen)
                    {
                        Invalidate(z, bar, "duplicitny gap");
                        return intents;
                    }
                }
            }

            if (z.Ordered)
            {
                if (z.State != ZoneState.OrderPending)
                {
                    z.StateBarIndex = history.BarIndex;
                    z.StateTimeMs = bar.Time;
                    Transition(z, ZoneState.OrderPending, bar, "order uz zadany");
                }
                return intents;
            }

            if (!z.ImbOpen.HasValue)
            {
                Invalidate(z, bar, "chyba vstupna cena");
                return intents;
            }
            double entry = z.ImbOpen.Value;

            // Pin Bar / Engulfing si SL priniesli zo STATE 0
            double stop = z.OrderSl.HasValue
                ? z.OrderSl.Value
                : Risk.SwingStopLoss(history, z.Direction, _cfg, _inst, z.Top, z.Bot, atr);

            TradePlan plan = Risk.BuildTradePlan(z.Direction, entry, stop, _cfg, _inst);

            string skip = SkipReason(z, bar, history, ctx, plan, atr);
            if (skip != null)
            {
                Invalidate(z, bar, "SKIP: " + skip);
                DrawLabelFor(z, bar, IbsKinds.Skip,
                             "SKIP (" + (z.Direction == Direction.Long ? "LONG" : "SHORT") + ")\n" + skip,
                             Palette.WithAlpha(Palette.Gray, 20), true);
                return intents;
            }

            bool useMarket = z.OrderSl.HasValue && _cfg.pbEngOrderType == OrderType.Market;

            z.Ordered = true;
            z.OrderSl = stop;
            z.StateBarIndex = history.BarIndex;
            Transition(z, ZoneState.OrderPending, bar, "order zadany");
            DrawTradeBoxes(z, bar, plan);

            OrderIntent intent = new OrderIntent(OrderAction.Entry, z.OrderId, z.Uid);
            intent.Direction = z.Direction;
            intent.Plan = plan;
            intent.OrderType = useMarket ? OrderType.Market : OrderType.Limit;
            intents.Add(intent);
            return intents;
        }

        // -- kreslenie ------------------------------------------------------- //

        /// <summary>Pine 2085-2099 - dva vyplnene bloky rozdelene na urovni entry (zeleny k TP, cerveny k SL).</summary>
        private void DrawTradeBoxes(Zone z, Bar bar, TradePlan plan)
        {
            long right = bar.Time + _cfg.state5MaxBars * 3 * _book.StepMs;
            AddTradeBox(z, bar, plan, DrawKinds.TpBox, plan.TakeProfit, Palette.Strong, right);
            AddTradeBox(z, bar, plan, DrawKinds.SlBox, plan.StopLoss, Palette.Long, right);
        }

        private void AddTradeBox(Zone z, Bar bar, TradePlan plan, string kind, double price, string col, long right)
        {
            DrawBox box = new DrawBox(kind, bar.Time, Math.Max(plan.Entry, price), right, Math.Min(plan.Entry, price),
                                      Palette.WithAlpha(col, 100));
            box.FillColor = Palette.WithAlpha(col, 70);
            box.BorderWidth = 0;
            box.ObjId = "z" + z.Uid + "." + kind;
            box.ZoneUid = z.Uid;
            Drawings.Add(box);
        }

        /// <summary>Pine 2231-2233 - po zavreti obchodu box konci na aktualnom bare.</summary>
        private void CloseTradeBoxes(Zone z, Bar bar)
        {
            Drawings.Add(new DrawUpdate("z" + z.Uid + "." + DrawKinds.TpBox, "x2_ms", bar.Time));
            Drawings.Add(new DrawUpdate("z" + z.Uid + "." + DrawKinds.SlBox, "x2_ms", bar.Time));
        }

        /// <summary>Pine `deleteTradeBoxes` - order zruseny, boxy zmiznu.</summary>
        private void DeleteTradeBoxes(Zone z)
        {
            Drawings.Add(new DrawDelete("z" + z.Uid + "." + DrawKinds.TpBox));
            Drawings.Add(new DrawDelete("z" + z.Uid + "." + DrawKinds.SlBox));
        }

        /// <summary>Stitok nad/pod svieckou. Pine ho pri LONG dava pod low, pri SHORT nad high.</summary>
        private void DrawLabelFor(Zone z, Bar bar, string kind, string text, string color, bool bubble)
        {
            bool isLong = z.Direction == Direction.Long;
            double off = _inst.TickSize * 10;
            DrawLabel label = new DrawLabel(kind, bar.Time, isLong ? bar.Low - off : bar.High + off, text,
                                            bubble ? "#ffffff" : color);
            label.Style = bubble ? (isLong ? LabelStyles.Up : LabelStyles.Down) : LabelStyles.None;
            label.Above = !isLong;
            label.BgColor = bubble ? color : null;
            label.ObjId = "z" + z.Uid + "." + kind + "." + bar.Time;
            label.ZoneUid = z.Uid;
            Drawings.Add(label);
        }

        /// <summary>Pine 2237-2269 - cislo stavu pod/nad svieckou, kym je zona v STATE 1-4;
        /// pri prvom cisle zony este "0" pri imbalance sviecke.</summary>
        private void DrawStateLabel(Zone z, Bar bar, BarHistory history)
        {
            int st = _timeoutSt.HasValue ? _timeoutSt.Value : z.State;
            if (st < 1 || st > 4) return;
            bool isLong = z.Direction == Direction.Long;
            string color = isLong ? Palette.Long : Palette.Short;
            double tick = _inst.TickSize;

            if (!z.Imb0Drawn && z.ImbBarIndex.HasValue)
            {
                int offset = history.BarIndex - z.ImbBarIndex.Value;
                long x = history.Has(offset) ? history[offset].Time : bar.Time - offset * _book.StepMs;
                double y0 = isLong
                    ? (z.ImbLow.HasValue ? z.ImbLow.Value : bar.Low) - tick * 5
                    : (z.ImbHigh.HasValue ? z.ImbHigh.Value : bar.High) + tick * 5;
                DrawLabel zero = new DrawLabel(IbsKinds.ImbZero, x, y0, "0", color);
                zero.Above = !isLong;
                zero.ObjId = "z" + z.Uid + "." + IbsKinds.ImbZero + "." + x;
                zero.ZoneUid = z.Uid;
                PushStateLabel(zero);
                z.Imb0Drawn = true;
            }

            double off = tick * 10;
            double y;
            if (isLong) { y = bar.Low - off * (1 + _lblUp); _lblUp++; }
            else { y = bar.High + off * (1 + _lblDown); _lblDown++; }
            string text = st == 4 ? "4\n" + PineToString(z.ImbOpen) : st.ToString(System.Globalization.CultureInfo.InvariantCulture);
            DrawLabel label = new DrawLabel(IbsKinds.Counter, bar.Time, y, text, color);
            label.Above = !isLong;
            label.ObjId = "z" + z.Uid + "." + IbsKinds.Counter + "." + bar.Time;
            label.ZoneUid = z.Uid;
            PushStateLabel(label);
        }

        private void PushStateLabel(DrawLabel label)
        {
            Drawings.Add(label);
            _stateLabels.Enqueue(label.ObjId);
            if (_stateLabels.Count > StateLabelMax) Drawings.Add(new DrawDelete(_stateLabels.Dequeue()));
        }

        /// <summary>Pine `canTrade` - poradie dovodov je zachovane, lebo sa zobrazuje v SKIP labeli.</summary>
        private string SkipReason(Zone z, Bar bar, BarHistory history, MarketContext ctx, TradePlan plan, double atr)
        {
            bool isLong = z.Direction == Direction.Long;

            if (!_cfg.enableTrading) return "OBCHODOVANIE VYPNUTE";

            bool oppositeOpen = (isLong && ctx.PositionSize < 0) || (!isLong && ctx.PositionSize > 0);
            if (oppositeOpen) return "OPACNA POZICIA";

            foreach (Zone other in _book.Zones)
            {
                if (!ReferenceEquals(other, z) && other.State == ZoneState.OrderPending
                    && other.Direction != z.Direction && !other.Filled)
                    return "OPACNY ORDER UZ CAKA";
            }

            if (_cfg.useStructureFilter)
            {
                int wanted = isLong ? 1 : -1;
                if (ctx.MarketBias != wanted) return "STRUKTURA NESEDI";
            }

            if (_cfg.useVolumeFilter && _cfg.volumeFilterBlockTrading && z.Source == ZoneSource.Sd)
            {
                double volSma = history.SmaVolume(_cfg.volSmaLen, 0);
                if (!(bar.Volume >= _cfg.volMultiplier * volSma)) return "VOLUME NEDOSTATOCNY";
            }

            if (!_cfg.Allows(z.Direction)) return "SMER VYPNUTY";

            if (DirectionGate != null)
            {
                string blocked = DirectionGate.BlockReason(z.Direction);
                if (blocked != null) return blocked;
            }

            if (plan != null)
            {
                double minSl = _cfg.minSlDistance.Resolve(_inst, plan.Entry, atr);
                if (minSl > 0 && plan.SlDistance < minSl) return "SL PRILIS TESNY";
            }

            return null;
        }

        // ---- STATE 5 -------------------------------------------------------- //

        private List<OrderIntent> State5(Zone z, Bar bar, BarHistory history, MarketContext ctx)
        {
            List<OrderIntent> intents = new List<OrderIntent>();
            int barsWaiting = BarsInState(z, history);

            bool runningNow = ctx.OpenOrderIds.Contains(z.OrderId);

            if (!z.Filled && !runningNow)
            {
                bool timedOut = barsWaiting >= _cfg.state5MaxBars;
                if (timedOut || !ctx.InTradeWindow)
                {
                    Invalidate(z, bar, timedOut ? "EXPIRED" : "koniec seansy");
                    if (timedOut)
                        DrawLabelFor(z, bar, IbsKinds.Expired, "EXPIRED\nb=" + barsWaiting, Palette.Amber, true);
                    z.EntryDone = false;
                    intents.Add(new OrderIntent(OrderAction.Cancel, z.OrderId, z.Uid, timedOut ? "EXPIRED" : "koniec seansy"));
                    return intents;
                }
                return intents;
            }

            if (z.Filled && !runningNow && !z.TradeBoxesClosed)
            {
                // Pine 2231-2233: obchod sa zavrel (TP/SL) - boxom sa utne pravy okraj.
                z.TradeBoxesClosed = true;
                CloseTradeBoxes(z, bar);
            }

            if (!z.Filled && runningNow)
            {
                z.Filled = true;
                Events.Add(new StateEvent(bar.Time, z.Uid, z.State, z.State, "FILLED"));

                // Pine 2185 - vyplnenim orderu sa zona vizualne uzavrie. Stav sa NEmeni.
                if (_cfg.invalidateOnFill || z.PendingInvalid)
                    Drawings.AddRange(z.ResizeOnInvalidation(bar.Time));

                // OCO: kto vyplnil prvy, ten vypina opacne cakajuce ordery.
                foreach (Zone other in _book.Zones)
                {
                    if (!ReferenceEquals(other, z) && other.State == ZoneState.OrderPending
                        && other.Direction != z.Direction && !other.Filled)
                    {
                        Invalidate(other, bar, "ZRUSENY (OCO)");
                        DeleteTradeBoxes(other);
                        other.EntryDone = false;
                        intents.Add(new OrderIntent(OrderAction.Cancel, other.OrderId, other.Uid, "OCO"));
                    }
                }
            }

            return intents;
        }
    }
}
