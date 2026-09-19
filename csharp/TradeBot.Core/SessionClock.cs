// Sessions a casove okna - zrkadlo `tradebot/core/clock.py` (Pine riadky 283-322).
// Kazda seansa ma dve nezavisle okna (zone / trade) a vlastne casove pasmo. Hranice okna sa
// pocitaju z DATUMU aktualneho baru v pasme seansy, takze okno sedi aj cez letny/zimny cas.
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    /// <summary>IANA mena pasiem (ako ich pisu profily) -> `TimeZoneInfo`.
    /// .NET Framework na Windows pozna len Windows ID, mono/.NET na Linuxe a macOS pozna IANA priamo.</summary>
    public static class TimeZones
    {
        private static readonly Dictionary<string, TimeZoneInfo> Cache = new Dictionary<string, TimeZoneInfo>();
        private static readonly Dictionary<string, string> IanaToWindows = new Dictionary<string, string>
        {
            { "UTC", "UTC" }, { "Etc/UTC", "UTC" }, { "GMT", "UTC" },
            { "Europe/Prague", "Central Europe Standard Time" },
            { "Europe/Bratislava", "Central Europe Standard Time" },
            { "Europe/Budapest", "Central Europe Standard Time" },
            { "Europe/Vienna", "W. Europe Standard Time" },
            { "Europe/Berlin", "W. Europe Standard Time" },
            { "Europe/Zurich", "W. Europe Standard Time" },
            { "Europe/Amsterdam", "W. Europe Standard Time" },
            { "Europe/Rome", "W. Europe Standard Time" },
            { "Europe/Paris", "Romance Standard Time" },
            { "Europe/Madrid", "Romance Standard Time" },
            { "Europe/Brussels", "Romance Standard Time" },
            { "Europe/Warsaw", "Central European Standard Time" },
            { "Europe/London", "GMT Standard Time" },
            { "Europe/Dublin", "GMT Standard Time" },
            { "Europe/Lisbon", "GMT Standard Time" },
            { "Europe/Athens", "GTB Standard Time" },
            { "Europe/Helsinki", "FLE Standard Time" },
            { "Europe/Kiev", "FLE Standard Time" },
            { "Europe/Istanbul", "Turkey Standard Time" },
            { "Europe/Moscow", "Russian Standard Time" },
            { "America/New_York", "Eastern Standard Time" },
            { "America/Toronto", "Eastern Standard Time" },
            { "America/Chicago", "Central Standard Time" },
            { "America/Denver", "Mountain Standard Time" },
            { "America/Los_Angeles", "Pacific Standard Time" },
            { "America/Sao_Paulo", "E. South America Standard Time" },
            { "Asia/Tokyo", "Tokyo Standard Time" },
            { "Asia/Seoul", "Korea Standard Time" },
            { "Asia/Shanghai", "China Standard Time" },
            { "Asia/Hong_Kong", "China Standard Time" },
            { "Asia/Singapore", "Singapore Standard Time" },
            { "Asia/Kolkata", "India Standard Time" },
            { "Asia/Dubai", "Arabian Standard Time" },
            { "Australia/Sydney", "AUS Eastern Standard Time" },
            { "Pacific/Auckland", "New Zealand Standard Time" },
        };

        public static TimeZoneInfo Get(string name)
        {
            lock (Cache)
            {
                TimeZoneInfo tz;
                if (Cache.TryGetValue(name, out tz)) return tz;
                tz = Resolve(name);
                Cache[name] = tz;
                return tz;
            }
        }

        private static TimeZoneInfo Resolve(string name)
        {
            if (name == "UTC" || name == "Etc/UTC" || name == "GMT") return TimeZoneInfo.Utc;
            try { return TimeZoneInfo.FindSystemTimeZoneById(name); }
            catch (Exception) { }
            string win;
            if (IanaToWindows.TryGetValue(name, out win))
            {
                try { return TimeZoneInfo.FindSystemTimeZoneById(win); }
                catch (Exception) { }
            }
            throw new ArgumentException("nezname casove pasmo '" + name + "' - dopln ho do TimeZones.IanaToWindows");
        }
    }

    public struct SessionWindow
    {
        public readonly int StartH, StartM, EndH, EndM;

        public SessionWindow(int startH, int startM, int endH, int endM)
        {
            StartH = startH; StartM = startM; EndH = endH; EndM = endM;
        }
    }

    public sealed class SessionSpec
    {
        public readonly string Name;
        public readonly bool Enabled;
        public readonly string Tz;
        public readonly SessionWindow Zone;
        public readonly SessionWindow Trade;

        public SessionSpec(string name, bool enabled, string tz, SessionWindow zone, SessionWindow trade)
        {
            Name = name; Enabled = enabled; Tz = tz; Zone = zone; Trade = trade;
        }
    }

    /// <summary>Stav casu pre jeden bar.</summary>
    public sealed class ClockState
    {
        public readonly bool[] ZoneFlags;
        public readonly bool[] TradeFlags;
        public readonly bool NoMoreSessionsToday;

        private static readonly string[] SessionColors = { Palette.Session1, Palette.Session2, Palette.Session3 };

        public ClockState(bool[] zoneFlags, bool[] tradeFlags, bool noMoreSessionsToday)
        {
            ZoneFlags = zoneFlags; TradeFlags = tradeFlags; NoMoreSessionsToday = noMoreSessionsToday;
        }

        public bool InZoneWindow { get { foreach (bool f in ZoneFlags) if (f) return true; return false; } }
        public bool InTradeWindow { get { foreach (bool f in TradeFlags) if (f) return true; return false; } }

        /// <summary>Pine `bgcolor()` - pas pozadia pre tento bar; trade okno ma prednost (priehladnost 92 vs 96).</summary>
        public List<DrawCommand> Backgrounds(long tsMs, long stepMs)
        {
            List<DrawCommand> list = new List<DrawCommand>();
            for (int i = 0; i < ZoneFlags.Length; i++)
            {
                if (!(ZoneFlags[i] || TradeFlags[i])) continue;
                string baseColor = SessionColors[i % SessionColors.Length];
                DrawBg bg = new DrawBg(DrawKinds.Session, tsMs, tsMs + stepMs, Palette.WithAlpha(baseColor, TradeFlags[i] ? 92 : 96));
                bg.ObjId = "bg" + (i + 1) + "." + tsMs;
                bg.Text = "Session " + (i + 1);
                list.Add(bg);
            }
            return list;
        }

        public void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("z").BeginArray();
            foreach (bool f in ZoneFlags) w.Value(f);
            w.EndArray();
            w.Key("t").BeginArray();
            foreach (bool f in TradeFlags) w.Value(f);
            w.EndArray();
            w.Key("n").Value(NoMoreSessionsToday);
            w.EndObject();
        }
    }

    /// <summary>Vyhodnocuje session okna pre dany cas baru. Bezstavove.</summary>
    public sealed class SessionClock
    {
        public const long DayMs = 86400000L;
        private static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        public readonly bool WeekdaysOnly;
        public readonly SessionSpec[] Sessions;

        public SessionClock(bool weekdaysOnly, SessionSpec[] sessions)
        {
            WeekdaysOnly = weekdaysOnly;
            Sessions = sessions;
        }

        private static DateTime Local(long tsMs, TimeZoneInfo tz)
        {
            return TimeZoneInfo.ConvertTimeFromUtc(Epoch.AddMilliseconds(tsMs), tz);
        }

        /// <summary>Pine `timestamp(tz, y, mo, d, h, m)` - lokalny cas v pasme -> ms epoch.
        /// Neexistujuci cas (jarny posun) a dvojznacny cas (jesenny) sa riesia ako Python `fold=0`:
        /// posun platny PRED prechodom, resp. prvy (letny) vyskyt.</summary>
        private static long TimestampMs(TimeZoneInfo tz, DateTime localDate, int hour, int minute)
        {
            DateTime local = new DateTime(localDate.Year, localDate.Month, localDate.Day, hour, minute, 0, DateTimeKind.Unspecified);
            TimeSpan offset;
            if (tz.IsInvalidTime(local))
            {
                offset = tz.GetUtcOffset(local.AddHours(-3));
            }
            else if (tz.IsAmbiguousTime(local))
            {
                TimeSpan[] offsets = tz.GetAmbiguousTimeOffsets(local);
                offset = offsets[0];
                foreach (TimeSpan o in offsets) if (o > offset) offset = o;
            }
            else
            {
                offset = tz.GetUtcOffset(local);
            }
            DateTime utc = DateTime.SpecifyKind(local - offset, DateTimeKind.Utc);
            return (long)(utc - Epoch).TotalMilliseconds;
        }

        /// <summary>Pine `isWeekdayTZ` - den v tyzdni sa berie v pasme danej seansy, nie v UTC.</summary>
        public bool IsWeekday(long tsMs, TimeZoneInfo tz)
        {
            if (!WeekdaysOnly) return true;
            DayOfWeek d = Local(tsMs, tz).DayOfWeek;
            return d != DayOfWeek.Saturday && d != DayOfWeek.Sunday;
        }

        /// <summary>Pine `inWindowTZ` - vratane posunu o den, ktory riesi okna cez polnoc.</summary>
        public bool InWindow(long tsMs, SessionWindow w, TimeZoneInfo tz)
        {
            DateTime local = Local(tsMs, tz);
            long start = TimestampMs(tz, local, w.StartH, w.StartM);
            long end = TimestampMs(tz, local, w.EndH, w.EndM);
            long end2 = end <= start ? end + DayMs : end;
            long t2 = tsMs < start ? tsMs + DayMs : tsMs;
            return start <= t2 && t2 < end2;
        }

        /// <summary>Pine `sessionHasTimeLeft` - ma este dnes trade okno tejto seansy dobehnut?</summary>
        public bool SessionHasTimeLeft(long tsMs, SessionSpec s)
        {
            if (!s.Enabled) return false;
            TimeZoneInfo tz = TimeZones.Get(s.Tz);
            if (!IsWeekday(tsMs, tz)) return false;
            DateTime local = Local(tsMs, tz);
            long start = TimestampMs(tz, local, s.Trade.StartH, s.Trade.StartM);
            long end = TimestampMs(tz, local, s.Trade.EndH, s.Trade.EndM);
            if (end <= start) end += DayMs;
            return tsMs < end;
        }

        public ClockState State(long tsMs)
        {
            bool[] zone = new bool[Sessions.Length];
            bool[] trade = new bool[Sessions.Length];
            bool anyTime = false;
            for (int i = 0; i < Sessions.Length; i++)
            {
                SessionSpec s = Sessions[i];
                if (!s.Enabled) continue;
                TimeZoneInfo tz = TimeZones.Get(s.Tz);
                bool weekdayOk = IsWeekday(tsMs, tz);
                zone[i] = weekdayOk && InWindow(tsMs, s.Zone, tz);
                trade[i] = weekdayOk && InWindow(tsMs, s.Trade, tz);
                if (SessionHasTimeLeft(tsMs, s)) anyTime = true;
            }
            return new ClockState(zone, trade, !anyTime);
        }
    }
}
