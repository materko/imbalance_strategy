// Denny stop uctu - poistka nad vsetkymi strategiami na jednom ucte (docs/DAILY_STOP.md).
//
// Ked equity uctu (vratane otvorenych obchodov) klesne o `Pct` % pod equity zo zaciatku obchodneho dna, ucet
// je do konca dna "zastaveny": adapter zavrie vsetky svoje pozicie, zrusi cakajuce vstupy a nove neposle.
// Den zacina v `ResetTime` casu `Zone` (predvolene 00:00 Europe/Prague = FTMO, SMERNICA V2 U1; CME/Apex/Topstep
// 18:00 America/New_York). Zakladom je max(balance, equity) z prveho pozorovania dna (V2: v okamihu resetu).
//
// Je to vec NASADENIA, nie strategie: zapina a nastavuje sa v adapteri (MT5 EA inputy `InpDailyStop*`,
// NinjaTrader vlastnosti strategie a nasadenie AddOnu), profil strategie ho nepozna a backtest ho nepocita.
// Jadro ani adaptery preto nemusia o strategii nic vediet - stop dostane kazda strategia bez zmeny kodu.
//
// Stav je za ucet SPOLOCNY: jeden objekt na subor stavu v procese (vsetky EA v jednom terminali MT5, vsetky
// instancie v NinjaTraderi) a subor `<adresar>/dailystop_<ucet>_<pasmo>_<HHmm>.json` pre restart a ine procesy
// (druhy terminal na tom istom ucte). Zastavenie jednou instanciou plati pre vsetky - na ucte s viacerymi
// nastaveniami teda vyhra to najprisnejsie. Subor sa znova cita najviac raz za `RefreshMs`, zapisuje len pri
// zmene (novy den, zastavenie).
//
// Jazyk je zamerne C# 5 a len BCL (csc.exe z .NET Frameworku, NinjaTrader, Mono).
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace TradeBot.Core
{
    /// <summary>Nastavenie denneho stopu z adaptera; neplatne hodnoty su chyba, nie ticho default.</summary>
    public sealed class DailyStopRule
    {
        public const double DefaultPct = 4.0;
        public const string DefaultZone = "Europe/Prague";
        public const string DefaultTime = "00:00";

        public readonly double Pct;
        public readonly string Zone;
        /// <summary>minuty od polnoci v pasme `Zone`, kedy zacina novy den</summary>
        public readonly int ResetMin;
        public readonly TimeZoneInfo Tz;

        public DailyStopRule(double pct, string zone, string resetTime)
        {
            if (double.IsNaN(pct) || pct <= 0 || pct >= 100)
                throw new ArgumentException("denny stop: percento musi byt medzi 0 a 100, nie " + pct.ToString(CultureInfo.InvariantCulture));
            Pct = pct;
            Zone = string.IsNullOrEmpty(zone) ? DefaultZone : zone;
            Tz = TimeZones.Get(Zone);
            ResetMin = ParseTime(string.IsNullOrEmpty(resetTime) ? DefaultTime : resetTime);
        }

        /// <summary>"HH:MM" (00:00-23:59) na minuty od polnoci.</summary>
        public static int ParseTime(string text)
        {
            string[] parts = text.Trim().Split(new char[] { ':' });
            int h, m;
            if (parts.Length != 2
                || !int.TryParse(parts[0], NumberStyles.None, CultureInfo.InvariantCulture, out h)
                || !int.TryParse(parts[1], NumberStyles.None, CultureInfo.InvariantCulture, out m)
                || h < 0 || h > 23 || m < 0 || m > 59)
                throw new ArgumentException("denny stop: cas zaciatku dna ma byt HH:MM, nie '" + text + "'");
            return h * 60 + m;
        }

        public string ResetText()
        {
            return (ResetMin / 60).ToString("00", CultureInfo.InvariantCulture) + ":" + (ResetMin % 60).ToString("00", CultureInfo.InvariantCulture);
        }

        /// <summary>Obchodny den, do ktoreho patri `nowMs` (UTC): datum (yyyyMMdd) jeho zaciatku v pasme `Zone`.</summary>
        public string DayKey(long nowMs)
        {
            DateTime local = TimeZoneInfo.ConvertTimeFromUtc(DailyStop.Epoch.AddMilliseconds(nowMs), Tz);
            DateTime start = local.Date.AddMinutes(ResetMin);
            if (local < start) start = start.AddDays(-1);
            return start.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
        }

        public string Describe()
        {
            return "-" + Pct.ToString("0.##", CultureInfo.InvariantCulture) + " % od " + ResetText() + " " + Zone;
        }
    }

    public sealed class DailyStop
    {
        internal static readonly DateTime Epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        /// <summary>Najviac tak casto sa znova cita subor stavu (zastavenie z ineho procesu).</summary>
        public static int RefreshMs = 5000;

        private static readonly object Gate = new object();
        private static readonly Dictionary<string, DailyStop> Shared = new Dictionary<string, DailyStop>(StringComparer.OrdinalIgnoreCase);

        public readonly string Path;
        public readonly string Account;
        private readonly string _zone;
        private readonly int _resetMin;

        // stav dna - pod `Gate`
        private string _day = "";
        private double _base = double.NaN;
        private bool _stopped;
        private long _stoppedMs;
        private double _stoppedEquity = double.NaN;
        private double _stoppedPct = double.NaN;
        private double _lastEquity = double.NaN;
        private long _readMs = long.MinValue;
        private long _sweepMs = long.MinValue;

        /// <summary>Zatvaranie celeho uctu pri zastaveni (V2 U1): najviac raz za tolko ms v procese platformy.</summary>
        public static int SweepMs = 5000;
        /// <summary>...a az tolko ms po zastaveni: vlastne pozicie zatvaraju instancie samy (do 2 s), zametanie
        /// berie len to, co ostalo (rucne, cudzie) - inak by v nettingu dve zatvorenia tej istej pozicie ju otocili.</summary>
        public static int SweepDelayMs = 10000;

        private DailyStop(string path, string account, DailyStopRule rule)
        {
            Path = path;
            Account = account;
            _zone = rule.Zone;
            _resetMin = rule.ResetMin;
        }

        /// <summary>Subor stavu uctu pre hranicu dna pravidla (ine pasmo / cas = iny den = iny stav). Prazdny
        /// `stateDir` = stav len v pamati procesu (Strategy Tester / Analyzer: opakovany beh toho isteho obdobia
        /// by inak nasiel zastavenie z predosleho behu).</summary>
        public static string StatePath(string stateDir, string account, DailyStopRule rule)
        {
            if (string.IsNullOrEmpty(account)) throw new ArgumentException("denny stop: chyba ucet");
            string name = "dailystop_" + Safe(account) + "_" + Safe(rule.Zone) + "_" + rule.ResetText().Replace(":", "") + ".json";
            return string.IsNullOrEmpty(stateDir) ? MemoryPrefix + name : System.IO.Path.Combine(stateDir, name);
        }

        private const string MemoryPrefix = "mem:";

        private bool OnDisk { get { return !Path.StartsWith(MemoryPrefix, StringComparison.Ordinal); } }

        private static string Safe(string text)
        {
            StringBuilder sb = new StringBuilder(text.Length);
            foreach (char c in text) sb.Append(char.IsLetterOrDigit(c) || c == '-' || c == '.' ? c : '-');
            return sb.ToString();
        }

        /// <summary>Spolocny stav uctu v tomto procese (vytvori ho pri prvom volani).</summary>
        public static DailyStop For(string stateDir, string account, DailyStopRule rule)
        {
            string path = StatePath(stateDir, account, rule);
            lock (Gate)
            {
                DailyStop s;
                if (!Shared.TryGetValue(path, out s))
                {
                    s = new DailyStop(path, account, rule);
                    Shared[path] = s;
                }
                return s;
            }
        }

        /// <summary>Testy: zabudnut stavy v pamati (subory ostanu).</summary>
        public static void ResetShared()
        {
            lock (Gate) Shared.Clear();
        }

        /// <summary>
        /// Nova equity uctu v `nowMs` (UTC). Vrati true, ked je ucet v tento obchodny den zastaveny - adapter
        /// zavrie a zrusi vsetko svoje a nove vstupy neposiela. Equity &lt;= 0 alebo NaN (ucet este nie je
        /// pripojeny) stav nemeni.
        /// </summary>
        public bool Check(DailyStopRule rule, long nowMs, double equity)
        {
            return Check(rule, nowMs, equity, double.NaN);
        }

        /// <summary>Ako `Check`, zaklad dna je max(balance, equity) (SMERNICA V2 U1) - pri otvorenej strate zaciatkom
        /// dna je teda zakladom balance, nie nizsia equity. `balance` NaN / &lt;= 0 = len equity.</summary>
        public bool Check(DailyStopRule rule, long nowMs, double equity, double balance)
        {
            lock (Gate)
            {
                string day = rule.DayKey(nowMs);
                bool changed = false;
                if (day != _day)
                {
                    _day = day;
                    _base = double.NaN;
                    _stopped = false;
                    _stoppedMs = 0;
                    _stoppedEquity = double.NaN;
                    _stoppedPct = double.NaN;
                    _readMs = long.MinValue;
                }
                if (nowMs - _readMs >= RefreshMs || _readMs > nowMs)
                {
                    _readMs = nowMs;
                    Merge();
                }
                bool valid = !double.IsNaN(equity) && !double.IsInfinity(equity) && equity > 0;
                if (valid)
                {
                    _lastEquity = equity;
                    if (double.IsNaN(_base))
                    {
                        bool bal = !double.IsNaN(balance) && !double.IsInfinity(balance) && balance > 0;
                        _base = bal ? Math.Max(balance, equity) : equity;
                        changed = true;
                    }
                    if (!_stopped && equity <= Limit(rule))
                    {
                        _stopped = true;
                        _stoppedMs = nowMs;
                        _stoppedEquity = equity;
                        _stoppedPct = rule.Pct;
                        changed = true;
                    }
                }
                if (changed) Save();
                return _stopped;
            }
        }

        /// <summary>Equity, pri ktorej sa ucet zastavi (NaN, kym nie je zaklad dna).</summary>
        public double Limit(DailyStopRule rule)
        {
            lock (Gate) return double.IsNaN(_base) ? double.NaN : _base * (1.0 - rule.Pct / 100.0);
        }

        /// <summary>Zastaveny ucet: smie teraz niektora instancia procesu zatvarat vsetky pozicie a prikazy uctu?
        /// true najviac raz za `SweepMs` na ucet - inak by viac EA / instancii na tom istom ucte poslalo zatvaracie
        /// prikazy naraz a druhy by poziciu otocil. Nezastaveny ucet = false.</summary>
        public bool SweepDue(long nowMs)
        {
            lock (Gate)
            {
                if (!_stopped) return false;
                if (_stoppedMs > 0 && nowMs - _stoppedMs < SweepDelayMs) return false;
                if (_sweepMs != long.MinValue && nowMs - _sweepMs < SweepMs && nowMs >= _sweepMs) return false;
                _sweepMs = nowMs;
                return true;
            }
        }

        public bool Stopped { get { lock (Gate) return _stopped; } }
        public string Day { get { lock (Gate) return _day; } }
        public double Base { get { lock (Gate) return _base; } }

        /// <summary>Veta do logu / telemetrie: zaklad, hranica, posledna equity, pripadne kedy sa zastavilo.</summary>
        public string Text(DailyStopRule rule)
        {
            lock (Gate)
            {
                CultureInfo ci = CultureInfo.InvariantCulture;
                StringBuilder sb = new StringBuilder();
                sb.Append("denny stop ").Append(rule.Describe()).Append(", ucet ").Append(Account).Append(", den ").Append(_day);
                if (double.IsNaN(_base)) { sb.Append(": este bez equity"); return sb.ToString(); }
                sb.Append(": zaklad ").Append(_base.ToString("0.00", ci)).Append(", hranica ").Append(Limit(rule).ToString("0.00", ci));
                if (!double.IsNaN(_lastEquity)) sb.Append(", equity ").Append(_lastEquity.ToString("0.00", ci));
                if (_stopped)
                {
                    sb.Append(" - ZASTAVENE");
                    if (_stoppedMs > 0)
                        sb.Append(" o ").Append(Epoch.AddMilliseconds(_stoppedMs).ToString("yyyy-MM-dd HH:mm:ss", ci)).Append(" UTC");
                    if (!double.IsNaN(_stoppedEquity)) sb.Append(" pri equity ").Append(_stoppedEquity.ToString("0.00", ci));
                    if (!double.IsNaN(_stoppedPct) && _stoppedPct != rule.Pct)
                        sb.Append(" (prisnejsie nastavenie -").Append(_stoppedPct.ToString("0.##", ci)).Append(" % inej instancie)");
                    sb.Append(", nove vstupy az od ").Append(rule.ResetText()).Append(" ").Append(rule.Zone);
                }
                return sb.ToString();
            }
        }

        // -- subor stavu (pod `Gate`) -------------------------------------- //

        /// <summary>Zlucit so suborom: ten isty den - zaklad z prveho zapisu, zastavenie plati, ked ho ma ktokolvek.</summary>
        private void Merge()
        {
            if (!OnDisk) return;
            Dictionary<string, object> d;
            try
            {
                if (!File.Exists(Path)) return;
                d = Json.ParseObject(File.ReadAllText(Path, Encoding.UTF8));
            }
            catch (Exception) { return; }   // rozpisany / poskodeny subor - plati stav v pamati, dalsi zapis ho opravi
            if (Json.GetString(d, "day", "") != _day) return;
            double fileBase = Json.GetDouble(d, "base", double.NaN);
            if (!double.IsNaN(fileBase) && fileBase > 0) _base = fileBase;
            if (Json.GetBool(d, "stopped", false) && !_stopped)
            {
                _stopped = true;
                _stoppedMs = (long)Json.GetDouble(d, "stopped_ms", 0);
                _stoppedEquity = Json.GetDouble(d, "stopped_equity", double.NaN);
                _stoppedPct = Json.GetDouble(d, "stopped_pct", double.NaN);
            }
        }

        private void Save()
        {
            if (!OnDisk) return;
            Merge();   // iny proces mohol medzitym zapisat zaklad alebo zastavenie
            JsonWriter w = new JsonWriter();
            w.BeginObject();
            w.Key("account").Value(Account).Key("zone").Value(_zone);
            w.Key("reset_min").Value(_resetMin);
            w.Key("day").Value(_day);
            w.Key("base").Value(double.IsNaN(_base) ? (double?)null : _base);
            w.Key("stopped").Value(_stopped);
            w.Key("stopped_ms").Value(_stoppedMs);
            w.Key("stopped_equity").Value(double.IsNaN(_stoppedEquity) ? (double?)null : _stoppedEquity);
            w.Key("stopped_pct").Value(double.IsNaN(_stoppedPct) ? (double?)null : _stoppedPct);
            w.EndObject();
            try { Bridge.AtomicWrite(Path, w.ToString()); }
            catch (Exception) { }   // zapis stavu nesmie zastavit kontrolu; stav v pamati plati dalej
        }
    }
}
