// Koniec obchodneho dna (EOD) pre prop ucty - o 15:59 New York (21:59 nasho casu) je vsetko zavrete.
//
// Obal nad enginom strategie (aj s jej obalmi vstupov): na poslednom bare grafu, ktory sa zatvara najneskor o 15:59 NY
// (3m: bar zatvarajuci sa 15:57, 5m: 15:55, 1m: 15:59), zavrie kazdu otvorenu poziciu, zrusi cakajuce vstupne ordery
// a az do 18:00 NY (novy obchodny den CME) nepusti ziadny novy vstup. Mimo toho okna je engine bit po bite ten isty
// ako bez obalu. Cas je vzdy New York, takze aj v tyzdnoch, ked sa letny cas v USA a v Europe meni inak, je to
// 15:59 NY (u nas vtedy 20:59) - nikdy nie neskor.
//
// Strategia s EOD je vlastny kluc (`<kluc>eod`, napr. `noaneteod`): trieda v jej priecinku len postavi engine
// predlohy a da ho sem. Obaly vstupov nasadi tento obal POD seba, aby ani limitka ci potvrdenie nevyslali vstup
// v okne EOD; `EngineRegistry.Create` ich preto druhy raz nebali (`IWrapsEntryLayers`).
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    /// <summary>Engine, ktory si obaly vstupov nasadil sam - `EngineRegistry.Create` ho uz nebali.</summary>
    public interface IWrapsEntryLayers
    {
    }

    /// <summary>
    /// Zivy adapter: zatvorenie podla hodin, ked posledny bar pred 15:59 NY neprisiel (zamrznuty feed, reconnect) -
    /// audit N-LIVE-7. Backtest to nepouziva: tam bar pride vzdy a zatvori engine.
    /// </summary>
    public interface IClockFlatten
    {
        /// <summary>`nowMs` (UTC) je v okne, v ktorom uz nesmie byt nic otvorene.</summary>
        bool FlattenDue(long nowMs);
    }

    public static class ClockFlatten
    {
        /// <summary>Prva vrstva enginu (zvonka dnu), ktora zatvara podla hodin; null = engine taku nema.</summary>
        public static IClockFlatten Find(IEngine engine)
        {
            for (IEngine e = engine; e != null; )
            {
                IClockFlatten c = e as IClockFlatten;
                if (c != null) return c;
                EngineLayer layer = e as EngineLayer;
                e = layer != null ? layer.Inner : null;
            }
            return null;
        }
    }

    public abstract class EodCloseEngine : EngineLayer, IWrapsEntryLayers, IClockFlatten
    {
        /// <summary>Zatvorenie podla hodin od 15:58:30 NY - bar zatvarajuci sa 15:57 (3m) to bezne spravi skor.</summary>
        public const int ClockCloseSec = CloseMin * 60 - 30;
        public const string Zone = "America/New_York";
        /// <summary>15:59 New York - najneskorsie zavretie baru, na ktorom sa este obchoduje</summary>
        public const int CloseMin = 15 * 60 + 59;
        /// <summary>18:00 New York - novy obchodny den CME, odkedy su vstupy znova povolene</summary>
        public const int ReopenMin = 18 * 60;
        public const string Reason = "EOD 15:59 NY";

        private readonly TimeZoneInfo _tz;
        private readonly int _tf;
        /// <summary>vstupy poslane brokerovi, ktore este nie su vyplnene ani zrusene</summary>
        private readonly HashSet<string> _pending = new HashSet<string>();
        private HashSet<string> _dropped = new HashSet<string>();
        private int _idx = -1;

        protected EodCloseEngine(IEngine strategy, Dictionary<string, object> config, int chartTfMinutes)
            : base(EntryLayers.Wrap(strategy, config, chartTfMinutes))
        {
            _tz = TimeZones.Get(Zone);
            _tf = Math.Max(1, chartTfMinutes);
        }

        /// <summary>Bar (cas otvorenia v ms UTC) je v okne EOD: dalsi bar by sa zatvoril po 15:59 NY a je pred 18:00 NY.</summary>
        public static bool InWindow(long barOpenMs, int tfMinutes, TimeZoneInfo tz)
        {
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddMilliseconds(barOpenMs), tz);
            int openMin = t.Hour * 60 + t.Minute;
            return openMin + 2 * tfMinutes > CloseMin && openMin < ReopenMin;
        }

        /// <summary>Najblizsie zatvorenie podla hodin (15:58:30 NY, `ClockCloseSec`) po `afterMs` v ms UTC, mimo
        /// soboty a nedele - `OrderLife.CloseAtMs` vstupu, aby ho vzdialeny vykonavac zavrel aj bez enginu.</summary>
        public static long NextClockCloseMs(long afterMs, TimeZoneInfo tz)
        {
            DateTime epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(epoch.AddMilliseconds(afterMs), tz);
            DateTime day = local.Date;
            for (int i = 0; i < 8; i++, day = day.AddDays(1))
            {
                if (day.DayOfWeek == DayOfWeek.Saturday || day.DayOfWeek == DayOfWeek.Sunday) continue;
                DateTime close = DateTime.SpecifyKind(day.AddSeconds(ClockCloseSec), DateTimeKind.Unspecified);
                if (close <= local) continue;
                return (long)(TimeZoneInfo.ConvertTimeToUtc(close, tz) - epoch).TotalMilliseconds;
            }
            return 0;
        }

        public bool FlattenDue(long nowMs)
        {
            DateTime t = TimeZoneInfo.ConvertTimeFromUtc(new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddMilliseconds(nowMs), _tz);
            int sec = t.Hour * 3600 + t.Minute * 60 + t.Second;
            return sec >= ClockCloseSec && sec < ReopenMin * 60;
        }

        private static List<string> Sorted(IEnumerable<string> ids)
        {
            List<string> list = new List<string>(ids);
            list.Sort(StringComparer.Ordinal);
            return list;
        }

        public override EngineOutput OnBar(Bar bar, HtfWindow htf, MarketContext ctx)
        {
            _idx += 1;
            if (ctx == null)
            {
                ctx = new MarketContext();
                ctx.InTradeWindow = true;
            }
            EngineOutput o = Inner.OnBar(bar, htf, EntryDraw.WithIds(ctx, new string[0], _dropped));
            _dropped = new HashSet<string>();
            foreach (string id in ctx.OpenOrderIds) _pending.Remove(id);
            bool eod = InWindow(bar.Time, _tf, _tz);

            List<OrderIntent> kept = new List<OrderIntent>();
            HashSet<string> closing = new HashSet<string>();
            foreach (OrderIntent i in o.Orders)
            {
                if (i.Action == OrderAction.Entry)
                {
                    if (eod)
                    {
                        // vstup v okne EOD - zahodit aj s kresbou obchodu, strategia sa to dozvie ako pri filtri
                        o.Drawings = EntryDraw.Without(o.Drawings, EntryDraw.TradeDrawings(o.Drawings, bar.Time));
                        _dropped.Add(i.OrderId);
                        continue;
                    }
                    _pending.Add(i.OrderId);
                    // vstup ide brokerovi na zatvoreni baru; vzdialeny vykonavac ho zavrie o 15:58:30 NY aj sam
                    if (i.Life == null) i.Life = new OrderLife();
                    i.Life.CloseAtMs = OrderLife.Earlier(i.Life.CloseAtMs, NextClockCloseMs(bar.Time + _tf * 60000L, _tz));
                }
                else
                {
                    _pending.Remove(i.OrderId);
                    if (i.Action == OrderAction.Close) closing.Add(i.OrderId);
                }
                kept.Add(i);
            }

            if (eod)
            {
                bool any = false;
                foreach (string id in Sorted(_pending))
                {
                    kept.Add(new OrderIntent(OrderAction.Cancel, id, _idx, Reason));
                    _dropped.Add(id);
                    any = true;
                }
                _pending.Clear();
                foreach (string id in Sorted(ctx.OpenOrderIds))
                {
                    if (closing.Contains(id)) continue;
                    kept.Add(new OrderIntent(OrderAction.Close, id, _idx, Reason));
                    any = true;
                }
                if (any) o.CloseSession = true;
            }
            o.Orders = kept;
            return o;
        }
    }
}
