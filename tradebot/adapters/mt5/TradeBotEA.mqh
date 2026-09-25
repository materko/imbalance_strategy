//+------------------------------------------------------------------+
//| TradeBotEA.mqh - genericky adapter MetaTrader 5 nad C# jadrom TradeBot                              |
//|                                                                                                   |
//| Zrkadlo `tradebot/adapters/ninjatrader/TradeBotStrategy.cs`: kazdy uzavrety bar grafu ide do        |
//| engine-u (`TradeBot.dll`, staticka fasada `TradeBot.Core.StaticHost`), engine vrati JSON s ordermi, |
//| kresbami a udalostami a adapter ich vykona cez CTrade. Strategiu adapter nepozna menom - kluc mu   |
//| da sablona (`deploy/mt5/<Meno>.mq5`) cez TRADEBOT_ENGINE_KEY.                                     |
//|                                                                                                   |
//| Overene: preklad, beh v Strategy Testeri (signaly 1:1 s Testerom), kreslenie na zivom grafe.        |
//| Neoverene: zivy trh s tikmi, shorty, netting ucet (TODO v kode).                                  |
//| Preklada ho MetaEditor (`python -m tradebot.adapters.mt5 install` to spravi sam); v terminali musi  |
//| byt `Tools > Options > Expert Advisors > Allow DLL imports`.                                       |
//+------------------------------------------------------------------+
#property copyright "TradeBot"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include <TradeBot/TradeBotJson.mqh>
#include <TradeBot/TradeBotDraw.mqh>

#ifndef TRADEBOT_ENGINE_KEY
   #error "TRADEBOT_ENGINE_KEY: sablona strategie musi definovat kluc engine-u (napr. \"ibsnet\")"
#endif
#ifndef TRADEBOT_DEFAULT_PROFILE
   #define TRADEBOT_DEFAULT_PROFILE ""
#endif

// .NET assembly: MetaEditor si obal vygeneruje sam (build 2400+). Volania su
// `StaticHost::Metoda(...)` - verejne staticke metody s int/long/double/bool/string.
#import "TradeBot.dll"
#import

//--- vstupy (rovnake ako parametre strategie v NinjaTraderi)
input string InpProfile             = TRADEBOT_DEFAULT_PROFILE; // Profil: nazov JSON v Common\Files\TradeBot\profiles\<kluc>\ alebo cela cesta
input int    InpServerGmtOffsetMin  = 0;      // Posun casu servera brokera voci UTC v minutach (GMT+3 = 180); v testeri sa neda zistit
input int    InpMagic               = 20260925; // Magic number
input bool   InpExportSignals       = true;   // Exportovat signaly (CSV do Common\Files\TradeBot\logs, na porovnanie s Testerom)
input bool   InpLogEvents           = false;  // Logovat prechody stavov do Experts logu
input bool   InpShowDrawings        = true;   // Kreslit objekty engine-u na graf (zony, SL/TP, vstupy...)
input bool   InpShowSessionBg       = false;  // Kreslit aj pozadie seans (Pine bgcolor)
input int    InpReplayBars          = 0;      // Kolko uzavretych barov prehrat pred startom (0 = 2 x predhistoria engine-u)
input string InpScreenshotFile      = "";     // Po prehrati predhistorie ulozit screenshot grafu (MQL5\Files\...png) - diagnostika
input bool   InpCloseAfterShot      = false;  // ...a potom terminal zavriet (davkove overenie kreslenia)
input double InpPointValueOverride  = 0;      // Hodnota bodu (1.0 ceny) za 1 lot v mene uctu; 0 = zo SymbolInfo

//--- stav adaptera
int              g_engine      = -1;          // handle v StaticHost
int              g_chartTfMin  = 0;
long             g_stepMs      = 0;
int              g_htfMin      = 0;
ENUM_TIMEFRAMES  g_htfPeriod   = PERIOD_CURRENT;
long             g_htfStepMs   = 0;
int              g_required    = 0;           // RequiredHistory
int              g_chartBars   = 0;
int              g_htfBars     = 0;
datetime         g_lastChart   = 0;           // cas otvorenia posledneho SPRACOVANEHO baru grafu (server)
datetime         g_lastHtf     = 0;
long             g_firstBarMs  = 0, g_lastBarMs = 0;
int              g_maxDailyWins = 0;
int              g_export      = INVALID_HANDLE;
bool             g_hedging     = false;
CTrade           g_trade;

//--- sledovane ordery (zrkadlo `Tracked` v NinjaTrader adapteri)
struct Tracked
  {
   string   id;
   ulong    orderTicket;      // cakajuci vstup (0 = market alebo uz vyplneny)
   ulong    positionTicket;   // pozicia po vyplneni (hedging: ticket pozicie; netting: POSITION_ID dealu)
   bool     filled;
   double   openQty;
   int      dir;              // 1 long, -1 short
   double   entry, stopLoss, takeProfit;
   bool     hasTrail;
   double   trailActivation, trailOffset;
   double   extreme;          // najlepsia cena od vstupu
   double   lastStop;
  };
Tracked g_orders[];

//--- denny limit vyhier: den (UTC, yyyymmdd) -> pocet; "seen" je stav na zaciatku baru
long   g_winsDay = 0;      int g_winsCount = 0;
long   g_winsSeenDay = 0;  int g_winsSeen = 0;

//+------------------------------------------------------------------+
//| Pomocne                                                          |
//+------------------------------------------------------------------+
string Num(double v) { return StringFormat("%.17g", v); }

long ToMs(datetime serverTime) { return ((long)serverTime - (long)InpServerGmtOffsetMin * 60) * 1000; }
datetime FromMs(long ms) { return (datetime)(ms / 1000 + (long)InpServerGmtOffsetMin * 60); }

long UtcDay(long ms)
  {
   MqlDateTime d; TimeToStruct((datetime)(ms / 1000), d);
   return (long)d.year * 10000 + d.mon * 100 + d.day;
  }

bool HasRealVolume()
  {
   MqlRates r[];
   if(CopyRates(_Symbol, PERIOD_CURRENT, 1, 50, r) <= 0) return false;
   for(int i = 0; i < ArraySize(r); i++) if(r[i].real_volume > 0) return true;
   return false;
  }

double BarVolume(const MqlRates &r, bool real) { return real ? (double)r.real_volume : (double)r.tick_volume; }

ENUM_TIMEFRAMES PeriodOfMinutes(int minutes)
  {
   switch(minutes)
     {
      case 1: return PERIOD_M1;   case 2: return PERIOD_M2;   case 3: return PERIOD_M3;   case 4: return PERIOD_M4;
      case 5: return PERIOD_M5;   case 6: return PERIOD_M6;   case 10: return PERIOD_M10; case 12: return PERIOD_M12;
      case 15: return PERIOD_M15; case 20: return PERIOD_M20; case 30: return PERIOD_M30; case 60: return PERIOD_H1;
      case 120: return PERIOD_H2; case 180: return PERIOD_H3; case 240: return PERIOD_H4; case 360: return PERIOD_H6;
      case 480: return PERIOD_H8; case 720: return PERIOD_H12; case 1440: return PERIOD_D1; case 10080: return PERIOD_W1;
     }
   return PERIOD_CURRENT;
  }

string EngineError(string where)
  {
   string e = StaticHost::LastError();
   return "TradeBot " + TRADEBOT_ENGINE_KEY + ": " + where + ": " + e;
  }

//+------------------------------------------------------------------+
//| Profil a instrument                                              |
//+------------------------------------------------------------------+
// Vsetko cita a pise cez FILE_COMMON (%APPDATA%\MetaQuotes\Terminal\Common\Files): Strategy Tester bezi
// v agentovi s vlastnym prazdnym MQL5\Files, terminalove Files tam nie su - Common je spolocne obom.
string ReadTextFile(string path)
  {
   int h = FileOpen(path, FILE_READ | FILE_BIN | FILE_COMMON);
   if(h == INVALID_HANDLE) return "";
   uchar bytes[];
   int n = (int)FileSize(h);
   ArrayResize(bytes, n);
   FileReadArray(h, bytes, 0, n);
   FileClose(h);
   return CharArrayToString(bytes, 0, n, CP_UTF8);
  }

string ResolveProfilePath()
  {
   // vsetko je relativne k Common\Files (sandbox FileOpen s FILE_COMMON); cela cesta sa berie tak, ako je
   if(StringFind(InpProfile, "\\") >= 0 || StringFind(InpProfile, "/") >= 0) return InpProfile;
   string name = InpProfile;
   if(StringLen(name) < 5 || StringSubstr(name, StringLen(name) - 5) != ".json") name += ".json";
   return "TradeBot\\profiles\\" + TRADEBOT_ENGINE_KEY + "\\" + name;
  }

string InstrumentJson(bool realVolume)
  {
   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);   // za 1 lot, v mene uctu
   double pointValue = InpPointValueOverride > 0 ? InpPointValueOverride : (tick > 0 ? tickValue / tick : 0);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minQty = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   return StringFormat("{\"symbol\":\"%s\",\"venue\":\"mt5\",\"tick_size\":%s,\"point_value\":%s,"
                       "\"qty_step\":%s,\"min_qty\":%s,\"has_real_volume\":%s}",
                       _Symbol, Num(tick), Num(pointValue), Num(step), Num(minQty), realVolume ? "true" : "false");
  }

//+------------------------------------------------------------------+
//| Export signalov - ten isty tvar ako NinjaTrader (`tester.ninjatrader compare`)                     |
//+------------------------------------------------------------------+
void OpenExport()
  {
   string stamp = TimeToString(TimeLocal(), TIME_DATE | TIME_MINUTES);
   StringReplace(stamp, ":", "");
   StringReplace(stamp, ".", "");
   StringReplace(stamp, " ", "-");
   string sym = _Symbol;
   StringReplace(sym, ".", "");
   string name = StringFormat("TradeBot\\logs\\%s_%s_%dm_%s_%d.csv", TRADEBOT_ENGINE_KEY, sym, g_chartTfMin, stamp, (int)GetTickCount());
   g_export = FileOpen(name, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(g_export == INVALID_HANDLE) { Print("TradeBot: export sa neda otvorit: ", name, " (", GetLastError(), ")"); return; }
   FileWriteString(g_export, "kind;bar_open_ms;id;a;b;entry;sl;tp;qty;ready;text\n");
  }

void ExportOrders(long barMs, CJson *out, bool ready)
  {
   if(g_export == INVALID_HANDLE || out == NULL) return;
   CJson *orders = out.Find("o");
   for(int i = 0; orders != NULL && i < orders.Size(); i++)
     {
      CJson *o = orders.At(i);
      string a = o.Str("a");
      string action = a == "entry" ? "Entry" : (a == "cancel" ? "Cancel" : "Close");
      CJson *p = o.Find("p");
      string plan = p == NULL ? ";;;" : Num(p.Dbl("e")) + ";" + Num(p.Dbl("sl")) + ";" + Num(p.Dbl("tp")) + ";" + Num(p.Dbl("q"));
      FileWriteString(g_export, StringFormat("order;%I64d;%s;%s;%s;%s;%s;%s\n", barMs, o.Str("id"), action, o.Str("ot"),
                                             plan, ready ? "1" : "0", o.Str("r")));
     }
   CJson *events = out.Find("e");
   for(int i = 0; events != NULL && i < events.Size(); i++)
     {
      CJson *e = events.At(i);
      string reason = e.Str("r");
      StringReplace(reason, ";", ",");
      StringReplace(reason, "\n", " ");
      FileWriteString(g_export, StringFormat("event;%I64d;%d;%d;%d;;;;;;%s\n", barMs, (int)e.Dbl("z"), (int)e.Dbl("f"),
                                             (int)e.Dbl("to"), reason));
     }
  }

void CloseExport()
  {
   if(g_export == INVALID_HANDLE) return;
   FileWriteString(g_export, StringFormat("stat;0;adapter_chart_bars;%d;;;;;;;\n", g_chartBars));
   FileWriteString(g_export, StringFormat("stat;0;adapter_htf_bars;%d;;;;;;;\n", g_htfBars));
   FileWriteString(g_export, StringFormat("stat;0;adapter_first_bar_ms;%I64d;;;;;;;\n", g_firstBarMs));
   FileWriteString(g_export, StringFormat("stat;0;adapter_last_bar_ms;%I64d;;;;;;;\n", g_lastBarMs));
   if(g_engine > 0)
     {
      CJson *stats = JsonParse(StaticHost::Stats(g_engine));
      for(int i = 0; stats != NULL && i < stats.Size(); i++)
         FileWriteString(g_export, StringFormat("stat;0;%s;%s;;;;;;;\n", stats.At(i).key, Num(stats.At(i).num)));
      delete stats;
     }
   FileClose(g_export);
   g_export = INVALID_HANDLE;
  }

//+------------------------------------------------------------------+
//| Zivotny cyklus                                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(PeriodSeconds() % 60 != 0)
     { Print("TradeBot: strategia bezi len na minutovom grafe (limity su v baroch)"); return INIT_PARAMETERS_INCORRECT; }
   g_chartTfMin = PeriodSeconds() / 60;
   g_stepMs = (long)g_chartTfMin * 60000;
   g_hedging = AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;

   if(StaticHost::Version() != 1)
     { Print("TradeBot: ina verzia fasady TradeBot.dll, preinstaluj (python -m tradebot.adapters.mt5 install)"); return INIT_FAILED; }

   string profilePath = ResolveProfilePath();
   string config = ReadTextFile(profilePath);
   if(config == "") { Print("TradeBot: profil sa nenasiel: Common\\Files\\", profilePath, " (", GetLastError(), ")"); return INIT_PARAMETERS_INCORRECT; }

   bool realVolume = HasRealVolume();
   g_engine = StaticHost::Create(TRADEBOT_ENGINE_KEY, config, InstrumentJson(realVolume), g_chartTfMin);
   if(g_engine <= 0) { Print(EngineError("Create")); return INIT_FAILED; }

   g_required = StaticHost::RequiredHistory(g_engine);
   g_htfMin = StaticHost::HtfTfMinutes(g_engine);
   if(g_htfMin > 0)
     {
      g_htfPeriod = PeriodOfMinutes(g_htfMin);
      if(g_htfPeriod == PERIOD_CURRENT)
        { Print("TradeBot: informativny TF ", g_htfMin, "m MetaTrader nepozna (zvol iny zoneDetectionTF)"); return INIT_PARAMETERS_INCORRECT; }
      g_htfStepMs = (long)g_htfMin * 60000;
     }
   CJson *stats = JsonParse(StaticHost::Stats(g_engine));
   g_maxDailyWins = stats != NULL && stats.Find("max_daily_wins") != NULL ? (int)stats.Dbl("max_daily_wins") : 0;
   delete stats;

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(10);

   if(InpExportSignals) OpenExport();
   Print("TradeBot ", TRADEBOT_ENGINE_KEY, ": TF ", g_chartTfMin, "m, predhistoria ", g_required, " barov, HTF ", g_htfMin,
         "m, tick ", SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), ", ucet ", g_hedging ? "hedging" : "netting",
         ", server UTC", InpServerGmtOffsetMin >= 0 ? "+" : "", InpServerGmtOffsetMin / 60.0, "h, profil ", profilePath);
   if(InpServerGmtOffsetMin == 0)
      Print("TradeBot: POZOR, posun servera voci UTC je 0 - seansy engine-u su v UTC/pasme profilu, skontroluj InpServerGmtOffsetMin");

   if(InpShowDrawings) ObjectsDeleteAll(0, TB_OBJ_PREFIX);   // zvysky z predoslej instancie EA
   ReplayHistory();
   if(InpScreenshotFile != "") EventSetTimer(3);   // graf sa musi najprv vykreslit
   return INIT_SUCCEEDED;
  }

void OnTimer()
  {
   EventKillTimer();
   ChartSetInteger(0, CHART_SCALE, 2);          // viac barov v zabere
   ChartSetInteger(0, CHART_SHOW_GRID, false);
   ChartRedraw(0);
   bool ok = ChartScreenShot(0, InpScreenshotFile, 1800, 900, ALIGN_RIGHT);
   Print("TradeBot: screenshot ", InpScreenshotFile, ok ? " ulozeny" : " zlyhal", " (", GetLastError(), "), objektov ", ObjectsTotalPrefix());
   DumpObjects(InpScreenshotFile + ".objects.csv");
   if(InpCloseAfterShot) TerminalClose(ok ? 0 : 1);
  }

/// Diagnostika kreslenia: zoznam objektov engine-u na grafe (typ, casy, ceny, farba, text).
void DumpObjects(string path)
  {
   int h = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   FileWriteString(h, "name;type;t1;p1;t2;p2;color;fill;back;text\n");
   int total = ObjectsTotal(0, -1, -1);
   for(int i = 0; i < total; i++)
     {
      string name = ObjectName(0, i, -1, -1);
      if(StringFind(name, TB_OBJ_PREFIX) != 0) continue;
      FileWriteString(h, StringFormat("%s;%d;%s;%s;%s;%s;%s;%d;%d;%s\n", name, (int)ObjectGetInteger(0, name, OBJPROP_TYPE),
                      TimeToString((datetime)ObjectGetInteger(0, name, OBJPROP_TIME, 0), TIME_DATE | TIME_MINUTES),
                      DoubleToString(ObjectGetDouble(0, name, OBJPROP_PRICE, 0), 2),
                      TimeToString((datetime)ObjectGetInteger(0, name, OBJPROP_TIME, 1), TIME_DATE | TIME_MINUTES),
                      DoubleToString(ObjectGetDouble(0, name, OBJPROP_PRICE, 1), 2),
                      ColorToString((color)ObjectGetInteger(0, name, OBJPROP_COLOR)),
                      (int)ObjectGetInteger(0, name, OBJPROP_FILL), (int)ObjectGetInteger(0, name, OBJPROP_BACK),
                      ObjectGetString(0, name, OBJPROP_TEXT)));
     }
   FileClose(h);
  }

void OnDeinit(const int reason)
  {
   if(g_engine > 0)
      Print("TradeBot ", TRADEBOT_ENGINE_KEY, ": spracovanych ", g_chartBars, " barov grafu (",
            TimeToString(FromMs(g_firstBarMs), TIME_DATE | TIME_MINUTES), " - ", TimeToString(FromMs(g_lastBarMs), TIME_DATE | TIME_MINUTES),
            " server), ", g_htfBars, " barov informativneho TF",
            g_chartBars < g_required * 2 ? " - PRILIS MALO DAT: skontroluj obdobie a historiu symbolu" : "");
   if(g_engine > 0 && InpShowDrawings && MQLInfoInteger(MQL_TESTER) && g_chartBars > 0) RenderFinal(g_lastRates);
   CloseExport();
   if(g_engine > 0) StaticHost::Destroy(g_engine);
   g_engine = -1;
  }

//+------------------------------------------------------------------+
//| Predhistoria: uzavrete bary spred startu idu do engine-u bez obchodovania (ready = false)          |
//+------------------------------------------------------------------+
bool g_replaying = false;

void ReplayHistory()
  {
   int want = InpReplayBars > 0 ? InpReplayBars : MathMax(g_required * 2, 50);
   g_replaying = true;
   MqlRates chart[];
   int n = CopyRates(_Symbol, PERIOD_CURRENT, 1, want, chart);   // index 1 = posledny uzavrety; pole je od najstarsieho
   if(n <= 0) { Print("TradeBot: CopyRates bez dat (", GetLastError(), ") - engine zacne bez predhistorie"); return; }
   datetime from = chart[0].time;
   if(g_htfMin > 0)
     {
      MqlRates htf[];
      int m = CopyRates(_Symbol, g_htfPeriod, from - (datetime)(g_htfMin * 60 * 8), TimeCurrent(), htf);
      int j = 0;
      for(int i = 0; i < n; i++)
        {
         // HTF bary uzavrete najneskor s otvorenim tohto baru grafu idu pred nim
         while(j < m && (long)htf[j].time + g_htfMin * 60 <= (long)chart[i].time) FeedHtf(htf[j++]);
         ProcessChartBar(chart[i]);
        }
     }
   else
      for(int i = 0; i < n; i++) ProcessChartBar(chart[i]);
   MqlRates last = chart[n - 1];
   g_replaying = false;
   Print("TradeBot: predhistoria ", n, " barov grafu prehrana (", g_htfBars, " HTF); posledny bar ",
         TimeToString(last.time, TIME_DATE | TIME_MINUTES), " tick_volume=", last.tick_volume, " real_volume=", last.real_volume,
         last.real_volume > 0 ? "" : " - POZOR: bez realneho objemu (tester generuje tiky), objemove filtre nesedia s Testerom");
   if(InpShowDrawings && !MQLInfoInteger(MQL_TESTER))
     {
      RenderFinal(last);
      ChartRedraw(0);
      Print("TradeBot: na grafe je ", ObjectsTotalPrefix(), " objektov engine-u");
     }
  }

//+------------------------------------------------------------------+
//| Tik: novy bar grafu = predchadzajuci sa uzavrel                                                   |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(g_engine <= 0) return;
   datetime open0 = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(open0 == 0 || open0 <= g_lastChart) return;
   // Vsetko uzavrete od posledneho spracovaneho baru (bezne jeden bar; po vypadku tikov viac). Berie sa
   // podla INDEXU od 1 (posledny uzavrety): CopyRates s casovym rozsahom vracia aj prave otvoreny bar
   // (v testeri overene 25. 9. 2026 - bar s jednym tikom by isiel do engine-u ako uzavrety).
   MqlRates chart[];
   int k = g_lastChart == 0 ? 1 : (int)MathMin(1000, (open0 - g_lastChart) / PeriodSeconds());
   int n = CopyRates(_Symbol, PERIOD_CURRENT, 1, k, chart);
   for(int i = 0; i < n; i++)
     {
      if(chart[i].time <= g_lastChart || chart[i].time >= open0) continue;
      if(g_htfMin > 0)
        {
         // HTF bary uzavrete najneskor s OTVORENIM tohto baru grafu (rovnake pravidlo ako predhistoria
         // a test parity fasady); ten, co sa uzavrie s jeho zatvorenim, ide pred dalsim barom
         datetime htfOpen0 = iTime(_Symbol, g_htfPeriod, 0);
         MqlRates htf[];
         int m = CopyRates(_Symbol, g_htfPeriod, g_lastHtf + (datetime)(g_htfMin * 60), chart[i].time, htf);
         for(int j = 0; j < m; j++)
            if(htf[j].time > g_lastHtf && htf[j].time < htfOpen0 && (long)htf[j].time + g_htfMin * 60 <= (long)chart[i].time)
               FeedHtf(htf[j]);
        }
      ProcessChartBar(chart[i]);
     }
  }

MqlRates g_lastRates;   // posledny spracovany bar grafu - pre FinalDrawings

void FeedHtf(const MqlRates &r)
  {
   if(r.time <= g_lastHtf) return;
   bool real = r.real_volume > 0;
   if(StaticHost::FeedHtf(g_engine, ToMs(r.time), r.open, r.high, r.low, r.close, BarVolume(r, real)) < 0)
      Print(EngineError("FeedHtf"));
   g_lastHtf = r.time;
   g_htfBars++;
  }

void ProcessChartBar(const MqlRates &r)
  {
   long barMs = ToMs(r.time);
   g_lastRates = r;
   if(g_chartBars++ == 0) g_firstBarMs = barMs;
   g_lastBarMs = barMs;
   g_lastChart = r.time;

   UpdateTrailing(r);

   double positionSize = 0;
   string openIds = "";
   for(int i = 0; i < ArraySize(g_orders); i++)
      if(g_orders[i].filled && g_orders[i].openQty > 0)
        {
         positionSize += g_orders[i].dir * g_orders[i].openQty;
         openIds += (openIds == "" ? "" : ",") + g_orders[i].id;
        }
   long day = UtcDay(barMs);
   bool dailyLimit = g_maxDailyWins > 0 && g_winsSeenDay == day && g_winsSeen >= g_maxDailyWins;

   bool real = r.real_volume > 0;
   string json = StaticHost::OnBar(g_engine, barMs, r.open, r.high, r.low, r.close, BarVolume(r, real),
                                                   positionSize, dailyLimit, openIds);
   if(json == "") { Print(EngineError("OnBar")); return; }
   CJson *out = JsonParse(json);
   if(out == NULL) { Print("TradeBot: nespracovatelny JSON z engine-u: ", StringSubstr(json, 0, 200)); return; }

   // Signal z baru bez celej predhistorie vstup neurobi (engine si ho odpise sam timeoutom).
   bool ready = !g_replaying && g_chartBars >= g_required;
   ExportOrders(barMs, out, ready);

   CJson *orders = out.Find("o");
   for(int i = 0; orders != NULL && i < orders.Size(); i++) Apply(orders.At(i), ready);
   if(out.Bool("cs")) Flatten("tb_session_end");

   if(InpLogEvents)
     {
      CJson *events = out.Find("e");
      for(int i = 0; events != NULL && i < events.Size(); i++)
        {
         CJson *e = events.At(i);
         Print(TimeToString(r.time, TIME_DATE | TIME_MINUTES), " zona ", (int)e.Dbl("z"), ": ", (int)e.Dbl("f"), " -> ", (int)e.Dbl("to"), " ", e.Str("r"));
        }
     }
   if(InpShowDrawings)
     {
      CJson *drawings = out.Find("d");
      for(int i = 0; drawings != NULL && i < drawings.Size(); i++) Render(drawings.At(i));
      // Pine `barstate.islast`: co sa kresli az na poslednom bare (S/R zhluky, Elliott) - nazivo na kazdom
      // bare (objekty maju stale id, prekreslia sa); v testeri az na konci behu (OnDeinit)
      if(!g_replaying && !MQLInfoInteger(MQL_TESTER)) RenderFinal(r);
     }
   delete out;

   // stav denneho limitu na zaciatku dalsieho baru = stav na konci tohto
   if(g_winsDay == day) { g_winsSeenDay = day; g_winsSeen = g_winsCount; }
  }

//+------------------------------------------------------------------+
//| Ordery                                                           |
//+------------------------------------------------------------------+
double Tick(double price)
  {
   double t = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   return t > 0 ? MathRound(price / t) * t : price;
  }

double Lots(double qty)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minQty = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lots = step > 0 ? MathFloor(qty / step + 1e-9) * step : qty;
   return MathMax(minQty, NormalizeDouble(lots, 8));
  }

int FindOrder(string id)
  {
   for(int i = 0; i < ArraySize(g_orders); i++) if(g_orders[i].id == id) return i;
   return -1;
  }

void RemoveOrder(int idx)
  {
   int n = ArraySize(g_orders);
   for(int i = idx; i < n - 1; i++) g_orders[i] = g_orders[i + 1];
   ArrayResize(g_orders, n - 1);
  }

void Apply(CJson *intent, bool ready)
  {
   string action = intent.Str("a");
   string id = intent.Str("id");
   int idx = FindOrder(id);

   if(action == "entry")
     {
      CJson *p = intent.Find("p");
      if(!ready || p == NULL) return;
      // Ten isty vstup este drzi poziciu: Pine by druhy `strategy.entry` s rovnakym id ignoroval.
      if(idx >= 0 && g_orders[idx].filled && g_orders[idx].openQty > 0) return;
      if(idx >= 0) RemoveOrder(idx);

      Tracked t;
      t.id = id; t.orderTicket = 0; t.positionTicket = 0; t.filled = false; t.openQty = 0;
      t.dir = (int)p.Dbl("dir");
      t.entry = p.Dbl("e"); t.stopLoss = p.Dbl("sl"); t.takeProfit = p.Dbl("tp");
      CJson *tr = p.Find("tr");
      t.hasTrail = tr != NULL;
      t.trailActivation = tr != NULL ? tr.Dbl("ap") : 0;
      t.trailOffset = tr != NULL ? tr.Dbl("op") : 0;
      t.extreme = t.entry; t.lastStop = t.stopLoss;

      double lots = Lots(p.Dbl("q"));
      double sl = Tick(t.stopLoss), tp = Tick(t.takeProfit), price = Tick(t.entry);
      string ot = intent.Str("ot");
      bool isLong = t.dir > 0;
      bool ok;
      if(ot == "Market")
         ok = isLong ? g_trade.Buy(lots, _Symbol, 0, sl, tp, id) : g_trade.Sell(lots, _Symbol, 0, sl, tp, id);
      else if(ot == "Stop")
         ok = isLong ? g_trade.BuyStop(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, id)
                     : g_trade.SellStop(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, id);
      else
         ok = isLong ? g_trade.BuyLimit(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, id)
                     : g_trade.SellLimit(lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, id);
      if(!ok || (g_trade.ResultRetcode() != TRADE_RETCODE_DONE && g_trade.ResultRetcode() != TRADE_RETCODE_PLACED))
        { Print("TradeBot: vstup ", id, " odmietnuty: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription()); return; }
      t.orderTicket = g_trade.ResultOrder();
      if(ot == "Market") { t.filled = true; t.openQty = lots; t.positionTicket = g_hedging ? g_trade.ResultDeal() : 0; }
      int n = ArraySize(g_orders);
      ArrayResize(g_orders, n + 1);
      g_orders[n] = t;
      if(InpLogEvents) Print("ENTRY ", id, " ", ot, " @", t.entry, " SL ", t.stopLoss, " TP ", t.takeProfit, " lots ", lots);
      return;
     }

   if(idx < 0) return;
   if(action == "cancel")
     {
      if(!g_orders[idx].filled)
        {
         if(g_orders[idx].orderTicket > 0) g_trade.OrderDelete(g_orders[idx].orderTicket);
         RemoveOrder(idx);
        }
      if(InpLogEvents) Print("CANCEL ", id, " (", intent.Str("r"), ")");
     }
   else if(action == "close")
     {
      if(g_orders[idx].filled && g_orders[idx].openQty > 0) ClosePosition(idx);
      if(InpLogEvents) Print("CLOSE ", id, " (", intent.Str("r"), ")");
     }
  }

void ClosePosition(int idx)
  {
   // hedging: kazdy vstup ma vlastnu poziciu; netting: jedna pozicia na symbol, zatvara sa jej cast
   if(g_hedging && g_orders[idx].positionTicket > 0) g_trade.PositionClose(g_orders[idx].positionTicket);
   else g_trade.PositionClosePartial(_Symbol, g_orders[idx].openQty);   // TODO netting: overit smer a zvysok
  }

/// Koniec poslednej seansy dna: zrus cakajuce vstupy a zavri, co ostalo otvorene.
void Flatten(string signal)
  {
   for(int i = ArraySize(g_orders) - 1; i >= 0; i--)
     {
      if(!g_orders[i].filled)
        {
         if(g_orders[i].orderTicket > 0) g_trade.OrderDelete(g_orders[i].orderTicket);
         RemoveOrder(i);
        }
      else if(g_orders[i].openQty > 0) ClosePosition(i);
     }
  }

/// Trailing z planu obchodu (`TradePlan.Trailing`) - posuva sa na zatvoreni baru grafu, nikdy spat.
void UpdateTrailing(const MqlRates &r)
  {
   for(int i = 0; i < ArraySize(g_orders); i++)
     {
      if(!g_orders[i].filled || g_orders[i].openQty <= 0 || !g_orders[i].hasTrail) continue;
      bool isLong = g_orders[i].dir > 0;
      double best = isLong ? MathMax(g_orders[i].extreme, r.high) : MathMin(g_orders[i].extreme, r.low);
      g_orders[i].extreme = best;
      double stop;
      if(isLong)
         stop = best - g_orders[i].entry < g_orders[i].trailActivation ? g_orders[i].stopLoss
                : MathMax(g_orders[i].stopLoss, best - g_orders[i].trailOffset);
      else
         stop = g_orders[i].entry - best < g_orders[i].trailActivation ? g_orders[i].stopLoss
                : MathMin(g_orders[i].stopLoss, best + g_orders[i].trailOffset);
      bool better = isLong ? stop > g_orders[i].lastStop : stop < g_orders[i].lastStop;
      if(!better) continue;
      g_orders[i].lastStop = stop;
      if(g_hedging && g_orders[i].positionTicket > 0) g_trade.PositionModify(g_orders[i].positionTicket, Tick(stop), Tick(g_orders[i].takeProfit));
      else g_trade.PositionModify(_Symbol, Tick(stop), Tick(g_orders[i].takeProfit));   // TODO netting: SL je spolocny
     }
  }

//+------------------------------------------------------------------+
//| Vyplnenia: co sa stalo s nasimi ordermi (zrkadlo OnExecutionUpdate v NinjaTraderi)                 |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   string comment = HistoryDealGetString(trans.deal, DEAL_COMMENT);
   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   double volume = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
   double profit = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
   ulong positionId = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);

   if(entry == DEAL_ENTRY_IN)
     {
      int idx = FindOrder(comment);
      if(idx < 0) return;
      g_orders[idx].filled = true;
      g_orders[idx].openQty += volume;
      g_orders[idx].positionTicket = positionId;
      return;
     }
   // vystup: SL/TP/close - deal nesie POSITION_ID vstupu (hedging); na nettingu je pozicia spolocna (TODO)
   for(int i = 0; i < ArraySize(g_orders); i++)
     {
      if(!g_orders[i].filled || g_orders[i].openQty <= 0) continue;
      if(g_hedging && g_orders[i].positionTicket != positionId) continue;
      g_orders[i].openQty = MathMax(0.0, g_orders[i].openQty - volume);
      if(g_orders[i].openQty <= 0 && profit > 0)
        {
         long day = UtcDay(ToMs((datetime)HistoryDealGetInteger(trans.deal, DEAL_TIME)));
         if(g_winsDay != day) { g_winsDay = day; g_winsCount = 0; }
         g_winsCount++;
        }
      break;
     }
  }

//+------------------------------------------------------------------+
//| Kresby: DrawCommand -> objekty grafu (TradeBotDraw.mqh)                                            |
//+------------------------------------------------------------------+
datetime TbFromMs(long ms) { return FromMs(ms); }   // X objektu = cas otvorenia baru, ako ho dava engine

void Render(CJson *cmd)
  {
   if(cmd.Str("t") == "bg" && cmd.Str("k") == "session" && !InpShowSessionBg) return;
   TbDraw(cmd);
  }

/// Kresby patriace na posledny bar (Pine `barstate.islast`).
void RenderFinal(const MqlRates &r)
  {
   bool real = r.real_volume > 0;
   string json = StaticHost::FinalDrawings(g_engine, ToMs(r.time), r.open, r.high, r.low, r.close, BarVolume(r, real));
   if(json == "") { Print(EngineError("FinalDrawings")); return; }
   CJson *arr = JsonParse(json);
   for(int i = 0; arr != NULL && i < arr.Size(); i++) Render(arr.At(i));
   delete arr;
  }
