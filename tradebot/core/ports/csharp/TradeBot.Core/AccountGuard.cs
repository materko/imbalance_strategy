// Ochrana uctu pred vstupom (SMERNICA V2 U1, docs/DAILY_STOP.md): sucet rizik do SL vsetkych otvorenych pozicii
// uctu a noveho obchodu najviac `MaxOpenRiskPct` % equity (predvolene 1,5) a pozicia bez SL u brokera dlhsie nez
// `NoStopGraceMs` od fillu sa zavrie. Pocitanie je tu, aby MT5 EA, exekutor aj NinjaTrader dali to iste (fasada
// `StaticHost.OpenRisk*`). Adapter dodava cisla z uctu - pozicie aj ine nez vlastne.
//
// Jazyk je zamerne C# 5 a len BCL.
using System;
using System.Globalization;
using System.IO;
using System.Text;

namespace TradeBot.Core
{
    public static class AccountGuard
    {
        public const double DefaultMaxOpenRiskPct = 1.5;
        /// <summary>Pozicia bez SL u brokera sa po tomto case od fillu zavrie trhom (V2 U1.3).</summary>
        public const long NoStopGraceMs = 5000;

        /// <summary>Riziko jednej pozicie do SL v mene uctu: |vstup - SL| x objem x hodnota bodu (za 1,0 ceny a 1 lot).
        /// SL &lt;= 0 (pozicia bez SL) = NaN - riziko nie je zname.</summary>
        public static double PositionRisk(double entry, double stop, double volume, double valuePerPoint)
        {
            if (!(stop > 0) || !(entry > 0) || double.IsNaN(volume) || double.IsNaN(valuePerPoint)) return double.NaN;
            return Math.Abs(entry - stop) * Math.Abs(volume) * Math.Abs(valuePerPoint);
        }

        /// <summary>"" = vstup smie ist; inak dovod odmietnutia. `openRisk` = sucet rizik otvorenych pozicii uctu
        /// (NaN = niektora nema SL), `newRisk` = riziko noveho obchodu. `maxPct` &lt;= 0 kontrolu vypina.</summary>
        public static string RiskVerdict(double openRisk, double newRisk, double equity, double maxPct)
        {
            if (!(maxPct > 0)) return "";
            CultureInfo ci = CultureInfo.InvariantCulture;
            if (!(equity > 0)) return "equity uctu nie je znama";
            if (double.IsNaN(openRisk)) return "otvorena pozicia bez SL u brokera - riziko uctu nie je zname";
            if (double.IsNaN(newRisk)) return "novy obchod nema SL";
            double limit = equity * maxPct / 100.0;
            double total = openRisk + newRisk;
            if (total > limit + 1e-9)
                return "sucasne riziko " + total.ToString("0.00", ci) + " (otvorene " + openRisk.ToString("0.00", ci)
                       + " + nove " + newRisk.ToString("0.00", ci) + ") > " + maxPct.ToString("0.##", ci) + " % equity = "
                       + limit.ToString("0.00", ci);
            return "";
        }

        /// <summary>Pozicia bez SL u brokera od `fillMs` je v `nowMs` po lehote - treba ju zavriet trhom.</summary>
        public static bool StopOverdue(long fillMs, long nowMs, bool hasStop)
        {
            return !hasStop && fillMs > 0 && nowMs - fillMs >= NoStopGraceMs;
        }

        /// <summary>Skupina uctov, ktore sa scitavaju (V2 U1.4): `groups` = skupiny loginov oddelene ';', loginy ','
        /// (napr. "111,222;333,444"). Login v niektorej skupine -> "grp-" + ta skupina bez medzier, inak `account`.</summary>
        public static string GroupOf(string login, string account, string groups)
        {
            if (!string.IsNullOrEmpty(groups) && !string.IsNullOrEmpty(login))
                foreach (string g in groups.Split(';'))
                    foreach (string id in g.Split(','))
                        if (id.Trim() == login.Trim()) return "grp-" + g.Replace(" ", "");
            return account ?? "";
        }
    }

    /// <summary>
    /// Zamok duplicity (SMERNICA V2 U1.4): ten isty kluc strategie s tym istym profilom smie bezat len na jednom
    /// ucte skupiny uctov, ktore sa scitavaju. Subor `dup_&lt;skupina&gt;_&lt;kluc&gt;_&lt;profil&gt;.txt` v adresari
    /// stavu nesie vlastnika (ucet + proces/terminal) a cas poslednej obnovy; zamok starsi ako `FreshMs` (pad bez
    /// uvolnenia) neplati. Ten isty vlastnik (iny slot, restart) duplicitou nie je.
    /// </summary>
    public static class DupLock
    {
        public static long FreshMs = 120000;

        public static string PathOf(string stateDir, string group, string key, string profile)
        {
            return System.IO.Path.Combine(stateDir, "dup_" + Safe(group) + "_" + Safe(key) + "_" + Safe(profile) + ".txt");
        }

        private static string Safe(string text)
        {
            StringBuilder sb = new StringBuilder();
            foreach (char c in text ?? "") sb.Append(char.IsLetterOrDigit(c) || c == '-' || c == '.' || c == ',' ? c : '-');
            return sb.ToString();
        }

        /// <summary>true = zamok je nas (zapisany); false = drzi ho iny vlastnik, `other` = kto.</summary>
        public static bool Claim(string path, string owner, long nowMs, out string other)
        {
            other = "";
            try
            {
                if (File.Exists(path))
                {
                    string[] lines = File.ReadAllText(path, Encoding.UTF8).Split('\n');
                    string who = lines.Length > 0 ? lines[0].Trim() : "";
                    long ms;
                    if (who.Length > 0 && who != owner && lines.Length > 1
                        && long.TryParse(lines[1].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out ms)
                        && nowMs - ms < FreshMs)
                    {
                        other = who;
                        return false;
                    }
                }
            }
            catch (Exception) { }   // necitatelny zamok neblokuje - prepise sa
            Refresh(path, owner, nowMs);
            return true;
        }

        public static void Refresh(string path, string owner, long nowMs)
        {
            try
            {
                string dir = System.IO.Path.GetDirectoryName(path);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                Bridge.AtomicWrite(path, owner + "\n" + nowMs.ToString(CultureInfo.InvariantCulture) + "\n");
            }
            catch (Exception) { }
        }

        /// <summary>Uvolnit, ak je zamok nas.</summary>
        public static void Release(string path, string owner)
        {
            try
            {
                if (!File.Exists(path)) return;
                string[] lines = File.ReadAllText(path, Encoding.UTF8).Split('\n');
                if (lines.Length > 0 && lines[0].Trim() == owner) File.Delete(path);
            }
            catch (Exception) { }
        }
    }
}
