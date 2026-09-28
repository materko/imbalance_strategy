//+------------------------------------------------------------------+
//| TradeBotEA.mqh - genericky adapter MetaTrader 5 nad C# jadrom TradeBot                              |
//|                                                                                                   |
//| Zrkadlo `tradebot/adapters/ninjatrader/TradeBotStrategy.cs`: kazdy uzavrety bar grafu ide do        |
//| engine-u (`TradeBot.dll`, staticka fasada `TradeBot.Core.StaticHost`), engine vrati JSON s ordermi, |
//| kresbami a udalostami a adapter ich vykona cez CTrade. Strategiu adapter nepozna menom - kluc mu   |
//| da sablona (`deploy/mt5/<Meno>.mq5`) cez TRADEBOT_ENGINE_KEY.                                     |
//|                                                                                                   |
//| Overene: preklad, beh v Strategy Testeri (signaly 1:1 s Testerom), kreslenie na zivom grafe.        |
//| Neoverene: zivy trh s tikmi, shorty, netting ucet (napisany; tester bezi v rezime uctu = hedging). |
//| Live telemetria (docs/LIVE.md): mimo Strategy Testera pise DLL bary, zamery, kresby, vyplnenia    |
//| a posuny SL trailingom (`order` s a:"modify")                                                       |
//| do JSONL spoolu Common\Files\TradeBot\spool\<instancia>\ (StaticHost::Spool*); agent hubu ich    |
//| posiela do webapp. Chyba spoolu EA nezhodi - zaloguje sa a obchoduje sa dalej.                    |
//| Ovladanie na dialku (docs/LIVE.md, faza 2): Common\Files\TradeBot\control\<instancia>.json         |
//| {"mode": enabled|paused|flatten, "profile": ...} - EA ho cita podla mtime kazdych 5 s (OnTimer)   |
//| a pri kazdom novom bare; paused = vstupy sa neposielaju, flatten = raz zrusi vstupy a zavrie       |
//| pozicie, iny profil = novy engine, ked je strategia bez pozicie (inak caka). Chybajuci subor =     |
//| enabled + InpProfile. V Strategy Testeri sa control subor necita (beh musi byt deterministicky).    |
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
input bool   InpTelemetry           = true;   // Live telemetria: JSONL spool do Common\Files\TradeBot\spool (docs/LIVE.md)
input bool   InpTelemetryInTester   = false;  // ...aj v Strategy Testeri (len na overenie; inak tester spool nepise)

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
bool             g_spool       = false;       // live telemetria otvorena (StaticHost::SpoolOpen)
bool             g_hedging     = false;
bool             g_replaying   = false;       // prehravanie predhistorie pri starte (bez obchodov)
CTrade           g_trade;

//--- sledovane ordery (zrkadlo `Tracked` v NinjaTrader adapteri)
struct Tracked
  {
   string   id;
   ulong    orderTicket;      // cakajuci vstup (0 = market alebo uz vyplneny)
   ulong    positionTicket;   // pozicia po vyplneni (hedging: ticket pozicie; netting: POSITION_ID dealu)
   ulong    slTicket, tpTicket;   // netting: vlastne vystupne ordery (stop + limit) s komentarom = id
   bool     filled;
   bool     isMarket;         // market vstup: medzi odoslanim a dealom sa pocita ako pozicia
   double   lots;             // objem vstupu
   double   openQty;
   int      dir;              // 1 long, -1 short
   double   entry, stopLoss, takeProfit;
   bool     hasTrail;
   double   trailActivation, trailOffset;
   double   extreme;          // najlepsia cena od vstupu
   double   lastStop;
   string   ot;               // Limit / Stop / Market
   bool     parked;           // odlozeny vstup: bezi pozicia, u brokera nie je (Pine `pyramiding=0`)
  };
Tracked g_orders[];

//--- ovladanie na dialku (docs/LIVE.md, faza 2): Common\Files\TradeBot\control\<instancia>.json
string g_instance       = "";          // id instancie = adresar spoolu (StaticHost::SpoolInstance / InstanceId)
string g_controlPath    = "";          // relativne k Common\Files (FILE_COMMON)
string g_mode           = "enabled";   // enabled / paused / flatten
string g_profile        = "";          // profil, z ktoreho bezi engine (nazov alebo cesta ako v InpProfile / control)
string g_pendingProfile = "";          // zmena profilu, ktora caka, kym bude strategia flat
long   g_controlMtime   = -2;          // posledne videne FILE_MODIFY_DATE (-1 = subor nie je)
long   g_controlSize    = -2;
bool   g_controlOn      = false;       // len mimo Strategy Testera
bool   g_shotDone       = false;       // screenshot (InpScreenshotFile) uz bol - timer je od toho spolocny
bool   g_suppressLogged = false;       // "vstup potlaceny" sa loguje raz na zmenu rezimu

//--- denny limit vyhier (Pine `dailyWinsCount`): vyhra = obchod zavrety na SL/TP so ziskom > 0 voci planovanemu
//--- vstupu; zavretie enginom (close, koniec seansy) sa nepocita. `seen` = stav na konci predosleho baru,
//--- presne ako v NinjaTrader adapteri (engine sa pyta na zaciatku baru).
long   g_winsDay = 0;      int g_winsCount = 0;
long   g_winsSeenDay = 0;  int g_winsSeen = 0;
long   g_limitLoggedDay = 0;
int    g_staleLogged = 0;

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
   // zdielane citanie: control subor prepisuje agent (tmp + rename) aj pocas behu EA
   int h = FileOpen(path, FILE_READ | FILE_BIN | FILE_COMMON | FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE) return "";
   uchar bytes[];
   int n = (int)FileSize(h);
   ArrayResize(bytes, n);
   FileReadArray(h, bytes, 0, n);
   FileClose(h);
   return CharArrayToString(bytes, 0, n, CP_UTF8);
  }

/// Profil ako nazov (`multicharts_mnq_3m`) alebo cesta - z InpProfile aj z control suboru (rovnake pravidla).
string ResolveProfilePath(string spec)
  {
   // vsetko je relativne k Common\Files (sandbox FileOpen s FILE_COMMON); cela cesta sa berie tak, ako je
   if(StringFind(spec, "\\") >= 0 || StringFind(spec, "/") >= 0) return spec;
   string name = spec;
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

/// Vyplnenie u brokera (zrkadlo `ExportFill` v NinjaTrader adapteri): `in` = vstup, `out` = vystup; cas dealu v ms UTC.
void ExportFill(datetime dealTime, string id, bool entry, string exitName, double price, double volume)
  {
   if(g_export == INVALID_HANDLE) return;
   FileWriteString(g_export, StringFormat("fill;%I64d;%s;%s;%s;%s;;;%s;%s;\n", ToMs(dealTime), id, entry ? "in" : "out", exitName,
                                          Num(price), Num(volume), g_replaying || MQLInfoInteger(MQL_TESTER) ? "0" : "1"));
   if(!MQLInfoInteger(MQL_TESTER)) FileFlush(g_export);
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

   if(StaticHost::Version() != 2)
     { Print("TradeBot: ina verzia fasady TradeBot.dll (cakam 2, docs/LIVE.md), preinstaluj: python -m tradebot.adapters.mt5 install"); return INIT_FAILED; }

   // Ovladanie na dialku: id instancie je zname este pred engine-om (rovnake polia ako spool), control subor
   // moze uz pri starte urcit rezim a profil - chybajuci subor = enabled + InpProfile (docs/LIVE.md, faza 2).
   g_controlOn = MQLInfoInteger(MQL_TESTER) == 0;
   g_instance = StaticHost::InstanceId("mt5", AccountId(), _Symbol, g_chartTfMin, TRADEBOT_ENGINE_KEY);
   g_controlPath = "TradeBot\\control\\" + g_instance + ".json";
   g_profile = InpProfile;
   string source = "default";
   if(g_controlOn)
     {
      g_controlMtime = FileGetInteger(g_controlPath, FILE_MODIFY_DATE, true);
      g_controlSize = g_controlMtime < 0 ? -1 : FileGetInteger(g_controlPath, FILE_SIZE, true);
      string mode, profile;
      if(g_controlMtime >= 0 && ReadControl(mode, profile) > 0)
        {
         g_mode = mode;
         if(profile != "") g_profile = profile;
         source = "control";
        }
     }

   string profilePath = ResolveProfilePath(g_profile);
   int h = CreateEngine(profilePath);
   if(h <= 0) return INIT_FAILED;
   AdoptEngine(h);

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(10);

   if(InpExportSignals) OpenExport();
   OpenSpool(profilePath);
   PrintEngineInfo(profilePath);
   if(InpServerGmtOffsetMin == 0)
      Print("TradeBot: POZOR, posun servera voci UTC je 0 - seansy engine-u su v UTC/pasme profilu, skontroluj InpServerGmtOffsetMin");

   if(InpShowDrawings) ObjectsDeleteAll(0, TB_OBJ_PREFIX);   // zvysky z predoslej instancie EA
   if(InpScreenshotFile != "") { ChartSetInteger(0, CHART_SCALE, 2); ChartSetInteger(0, CHART_SHOW_GRID, false); }   // pred kreslenim: pozadia popiskov sa pocitaju z mierky
   ReplayHistory();
   // od teraz kazdy riadok spoolu hned na disk (nazivo); tester si flushuje po davkach
   if(g_spool && !MQLInfoInteger(MQL_TESTER) && StaticHost::SpoolRealtime(g_engine, true) < 0) Print(EngineError("SpoolRealtime"));
   SpoolControl(g_mode, g_profile, source);
   if(g_controlOn)
      Print("TradeBot control: instancia ", g_instance, ", subor Common\\Files\\", g_controlPath, g_controlMtime >= 0 ? " (existuje)" : " (nie je)",
            ", rezim ", g_mode, " (", source, ")", g_mode == "enabled" ? "" : " - nove vstupy sa neposielaju");
   // jeden spolocny timer: screenshot raz (graf sa musi najprv vykreslit), control subor kazdych 5 s
   if(g_controlOn || InpScreenshotFile != "") EventSetTimer(5);
   return INIT_SUCCEEDED;
  }

string AccountId() { return IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "-" + AccountInfoString(ACCOUNT_SERVER); }

/// Engine z profilu (config JSON z Common\Files, instrument zo SymbolInfo): handle > 0, alebo -1 (dovod v logu).
int CreateEngine(string profilePath)
  {
   string config = ReadTextFile(profilePath);
   if(config == "") { Print("TradeBot: profil sa nenasiel: Common\\Files\\", profilePath, " (", GetLastError(), ")"); return -1; }
   int h = StaticHost::Create(TRADEBOT_ENGINE_KEY, config, InstrumentJson(HasRealVolume()), g_chartTfMin);
   if(h <= 0) { Print(EngineError("Create")); return -1; }
   int htfMin = StaticHost::HtfTfMinutes(h);
   if(htfMin > 0 && PeriodOfMinutes(htfMin) == PERIOD_CURRENT)
     { Print("TradeBot: informativny TF ", htfMin, "m MetaTrader nepozna (zvol iny zoneDetectionTF)"); StaticHost::Destroy(h); return -1; }
   return h;
  }

/// Prevezme engine: co adapter potrebuje vediet na kazdom bare (predhistoria, HTF, denny limit).
void AdoptEngine(int h)
  {
   g_engine = h;
   g_required = StaticHost::RequiredHistory(h);
   g_htfMin = StaticHost::HtfTfMinutes(h);
   g_htfPeriod = g_htfMin > 0 ? PeriodOfMinutes(g_htfMin) : PERIOD_CURRENT;
   g_htfStepMs = (long)g_htfMin * 60000;
   CJson *stats = JsonParse(StaticHost::Stats(h));
   g_maxDailyWins = stats != NULL && stats.Find("max_daily_wins") != NULL ? (int)stats.Dbl("max_daily_wins") : 0;
   delete stats;
  }

void PrintEngineInfo(string profilePath)
  {
   Print("TradeBot ", TRADEBOT_ENGINE_KEY, ": TF ", g_chartTfMin, "m, predhistoria ", g_required, " barov, HTF ", g_htfMin,
         "m, tick ", SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE), ", ucet ", g_hedging ? "hedging" : "netting",
         ", server UTC", InpServerGmtOffsetMin >= 0 ? "+" : "", InpServerGmtOffsetMin / 60.0, "h, profil ", profilePath);
  }

//+------------------------------------------------------------------+
//| Ovladanie na dialku (docs/LIVE.md, faza 2): control subor podla mtime                              |
//+------------------------------------------------------------------+
/// Precita control subor: 1 = platny (`mode`, `profile`), 0 = neda sa otvorit, -1 = neplatny (zalogovane).
int ReadControl(string &mode, string &profile)
  {
   string text = ReadTextFile(g_controlPath);
   if(text == "") return 0;
   CJson *root = JsonParse(text);
   if(root == NULL || root.type != JSON_OBJECT)
     { if(root != NULL) delete root; Print("TradeBot control: neplatny JSON v Common\\Files\\", g_controlPath, " - ostava rezim ", g_mode); return -1; }
   mode = root.Str("mode");
   profile = root.Str("profile");
   delete root;
   if(mode == "") mode = "enabled";
   if(mode != "enabled" && mode != "paused" && mode != "flatten")
     { Print("TradeBot control: neznamy rezim '", mode, "' v Common\\Files\\", g_controlPath, " - ostava rezim ", g_mode); return -1; }
   return 1;
  }

/// Kazdych 5 s (OnTimer) a pri kazdom novom bare: zmena mtime/velkosti = precitat a aplikovat; inak len skusit
/// cakajucu zmenu profilu. Nezavisi od barov - funguje aj so zavretym trhom.
void CheckControl()
  {
   if(!g_controlOn || g_engine <= 0) return;
   long mtime = FileGetInteger(g_controlPath, FILE_MODIFY_DATE, true);   // -1 = subor nie je
   long size = mtime < 0 ? -1 : FileGetInteger(g_controlPath, FILE_SIZE, true);
   if(mtime == g_controlMtime && size == g_controlSize) { RetryPendingProfile(); return; }
   if(mtime < 0)
     {
      // subor zmizol = enabled + profil zo vstupu EA (docs/LIVE.md)
      g_controlMtime = mtime; g_controlSize = size;
      Print("TradeBot control: subor Common\\Files\\", g_controlPath, " zmizol - enabled + InpProfile");
      ApplyControl("enabled", InpProfile, "default");
      return;
     }
   string mode, profile;
   int r = ReadControl(mode, profile);
   if(r == 0) return;   // prave sa prepisuje (tmp + rename) - skusi sa o 5 s
   g_controlMtime = mtime; g_controlSize = size;
   if(r < 0) return;    // neplatny obsah: ostava posledny rezim, zalogovane raz (mtime si pamatame)
   ApplyControl(mode, profile, "control");
  }

/// Aplikuje rezim a profil; kazda aplikovana zmena ide do spoolu ako `control` (mode, profile, source).
void ApplyControl(string mode, string profile, string source)
  {
   bool modeChanged = mode != g_mode;
   g_mode = mode;
   if(modeChanged)
     {
      g_suppressLogged = false;
      Print("TradeBot control: rezim ", mode, " (", source, ")", mode == "enabled" ? " - obchoduje sa normalne" : " - nove vstupy sa neposielaju");
     }
   if(mode == "flatten")
     {
      // raz: zrusit cakajuce vstupy a zavriet pozicie (dealy pridu cez OnTradeTransaction), dalej ako paused
      int pending = 0, open = 0;
      for(int i = 0; i < ArraySize(g_orders); i++) { if(g_orders[i].filled && g_orders[i].openQty > 0) open++; else pending++; }
      Flatten("tb_flatten");
      Print("TradeBot control: flatten - zrusenych ", pending, " cakajucich vstupov, zatvara sa ", open, " pozicii");
     }
   string want = profile == "" ? g_profile : profile;
   if(ResolveProfilePath(want) != ResolveProfilePath(g_profile))
     {
      if(!IsFlat())
        {
         g_pendingProfile = want;
         Print("TradeBot control: profil ", want, " caka, kym bude strategia bez pozicie a cakajucich vstupov (bezi ", g_profile, ")");
         SpoolControl(g_mode, want, "pending");
         return;
        }
      g_pendingProfile = "";
      RebuildEngine(want);   // pri chybe bezi dalej stary profil (zalogovane)
     }
   else g_pendingProfile = "";
   SpoolControl(g_mode, g_profile, source);
  }

/// Cakajuca zmena profilu (po deale, po bare, z timera): aplikuje sa, len co je strategia flat.
void RetryPendingProfile()
  {
   if(g_pendingProfile == "" || !IsFlat()) return;
   string want = g_pendingProfile;
   g_pendingProfile = "";
   if(RebuildEngine(want)) SpoolControl(g_mode, g_profile, "control");
  }

/// Bez pozicie a bez cakajucich vstupov u brokera (odlozene vstupy u brokera nie su - novy engine ich nepozna).
bool IsFlat()
  {
   for(int i = 0; i < ArraySize(g_orders); i++)
     {
      if(g_orders[i].filled && g_orders[i].openQty > 0) return false;
      if(!g_orders[i].filled && !g_orders[i].parked && (g_orders[i].orderTicket > 0 || g_orders[i].isMarket)) return false;
     }
   return true;
  }

/// Zmena profilu: novy engine z noveho profilu, stary zahodit (spool zavriet s dovodom "profile"), stav adaptera
/// od nuly a predhistoriu prehrat znova - engine je deterministicky, vysledok je ako cerstvy start (docs/LIVE.md).
bool RebuildEngine(string spec)
  {
   string path = ResolveProfilePath(spec);
   int h = CreateEngine(path);
   if(h <= 0) { Print("TradeBot control: profil ", spec, " sa neda nacitat - bezi dalej ", g_profile); return false; }
   if(g_spool && StaticHost::SpoolClose(g_engine, "profile") < 0) Print(EngineError("SpoolClose"));
   g_spool = false;
   CloseExport();
   StaticHost::Destroy(g_engine);
   ArrayResize(g_orders, 0);
   g_winsDay = 0; g_winsCount = 0; g_winsSeenDay = 0; g_winsSeen = 0; g_limitLoggedDay = 0; g_staleLogged = 0;
   g_chartBars = 0; g_htfBars = 0; g_lastChart = 0; g_lastHtf = 0; g_firstBarMs = 0; g_lastBarMs = 0;
   g_profile = spec;
   AdoptEngine(h);
   if(InpExportSignals) OpenExport();
   OpenSpool(path);
   PrintEngineInfo(path);
   if(InpShowDrawings) ObjectsDeleteAll(0, TB_OBJ_PREFIX);
   ReplayHistory();
   if(g_spool && !MQLInfoInteger(MQL_TESTER) && StaticHost::SpoolRealtime(g_engine, true) < 0) Print(EngineError("SpoolRealtime"));
   Print("TradeBot control: profil zmeneny na ", spec, " (Common\\Files\\", path, "), engine postaveny nanovo, predhistoria prehrana");
   return true;
  }

void SpoolControl(string mode, string profile, string source)
  {
   if(!g_spool) return;
   if(StaticHost::SpoolControl(g_engine, mode, profile, source) < 0) { Print(EngineError("SpoolControl (telemetria vypnuta)")); g_spool = false; }
  }

//+------------------------------------------------------------------+
//| Live telemetria (docs/LIVE.md): DLL pise priamo na disk, nie cez MQL sandbox                        |
//+------------------------------------------------------------------+
void OpenSpool(string profilePath)
  {
   bool tester = MQLInfoInteger(MQL_TESTER) != 0;
   if(!InpTelemetry || (tester && !InpTelemetryInTester)) return;
   string root = TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\TradeBot\\spool";
   if(StaticHost::SpoolOpen(g_engine, root, "mt5", AccountId(), _Symbol, profilePath, tester) < 0)
     { Print(EngineError("SpoolOpen (telemetria vypnuta)")); return; }
   g_spool = true;
   // id instancie zo spoolu je smerodajne (to iste, co InstanceId - control subor sa hlada podla neho)
   string instance = StaticHost::SpoolInstance(g_engine);
   if(instance != "" && instance != g_instance)
     { g_instance = instance; g_controlPath = "TradeBot\\control\\" + g_instance + ".json"; }
   Print("TradeBot: live telemetria -> ", StaticHost::SpoolPath(g_engine));
  }

void SpoolFill(datetime dealTime, string id, bool entry, string exitName, double price, double volume, bool ready)
  {
   if(!g_spool) return;
   if(StaticHost::SpoolFill(g_engine, ToMs(dealTime), id, entry, exitName, price, volume, ready) < 0)
     { Print(EngineError("SpoolFill (telemetria vypnuta)")); g_spool = false; }
  }

/// Posun SL/TP pracujuceho orderu adapterom (trailing): riadok `order` s `a:"modify"`; 0 = nemenene (null).
void SpoolModify(long barMs, string id, double sl, double tp, string reason, bool ready)
  {
   if(!g_spool) return;
   if(StaticHost::SpoolModify(g_engine, barMs, id, sl, tp, reason, ready) < 0)
     { Print(EngineError("SpoolModify (telemetria vypnuta)")); g_spool = false; }
  }

/// Spolocny timer (5 s): screenshot raz po vykresleni grafu, control subor pri kazdom tiku timera.
void OnTimer()
  {
   if(InpScreenshotFile != "" && !g_shotDone)
     {
      g_shotDone = true;
      TakeScreenshot();
      if(InpCloseAfterShot) return;
     }
   if(g_controlOn) CheckControl();
   else EventKillTimer();
  }

void TakeScreenshot()
  {
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
   EventKillTimer();
   if(g_engine > 0)
      Print("TradeBot ", TRADEBOT_ENGINE_KEY, ": spracovanych ", g_chartBars, " barov grafu (",
            TimeToString(FromMs(g_firstBarMs), TIME_DATE | TIME_MINUTES), " - ", TimeToString(FromMs(g_lastBarMs), TIME_DATE | TIME_MINUTES),
            " server), ", g_htfBars, " barov informativneho TF",
            g_chartBars < g_required * 2 ? " - PRILIS MALO DAT: skontroluj obdobie a historiu symbolu" : "");
   if(g_engine > 0 && InpShowDrawings && MQLInfoInteger(MQL_TESTER) && g_chartBars > 0) RenderFinal(g_lastRates);
   CloseExport();
   if(g_engine > 0 && g_spool && StaticHost::SpoolClose(g_engine, "deinit") < 0) Print(EngineError("SpoolClose"));
   g_spool = false;
   if(g_engine > 0) StaticHost::Destroy(g_engine);
   g_engine = -1;
  }

//+------------------------------------------------------------------+
//| Predhistoria: uzavrete bary spred startu idu do engine-u bez obchodovania (ready = false)          |
//+------------------------------------------------------------------+

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
   // novy bar = aj kontrola control suboru (a cakajucej zmeny profilu); timer to robi kazdych 5 s bez ohladu na bary
   if(n > 0) CheckControl();
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
     {
      if(g_orders[i].filled && g_orders[i].openQty > 0)
        {
         positionSize += g_orders[i].dir * g_orders[i].openQty;
         openIds += (openIds == "" ? "" : ",") + g_orders[i].id;
        }
      // market vstup, ktory uz odisiel, ale deal este neprisiel, sa pocita ako pozicia (inak by engine
      // po bare vstup zrusil a poslal dalsi - viď NinjaTrader adapter, 25. 9. 2026: 20 orderov naraz)
      else if(!g_orders[i].filled && !g_orders[i].parked && g_orders[i].isMarket) positionSize += g_orders[i].dir * g_orders[i].lots;
     }
   long day = UtcDay(barMs);
   bool dailyLimit = g_maxDailyWins > 0 && g_winsSeenDay == day && g_winsSeen >= g_maxDailyWins;
   if(dailyLimit && InpLogEvents && g_limitLoggedDay != day)
     { g_limitLoggedDay = day; Print("DENNY LIMIT ", g_winsSeen, "/", g_maxDailyWins, " vyhier - dnes uz bez vstupov (", TimeToString(r.time, TIME_DATE | TIME_MINUTES), ")"); }

   bool real = r.real_volume > 0;
   string json = StaticHost::OnBar(g_engine, barMs, r.open, r.high, r.low, r.close, BarVolume(r, real),
                                                   positionSize, dailyLimit, openIds);
   if(json == "") { Print(EngineError("OnBar")); return; }
   CJson *out = JsonParse(json);
   if(out == NULL) { Print("TradeBot: nespracovatelny JSON z engine-u: ", StringSubstr(json, 0, 200)); return; }

   // Signal z baru bez celej predhistorie vstup neurobi (engine si ho odpise sam timeoutom).
   bool ready = !g_replaying && g_chartBars >= g_required;
   // Nazivo: bar, ktory prisiel s velkym oneskorenim (vypadok spojenia, davka barov naraz), sa neobchoduje.
   if(ready && !MQLInfoInteger(MQL_TESTER) && TimeCurrent() - (r.time + PeriodSeconds()) > 2 * PeriodSeconds())
     {
      ready = false;
      if(g_staleLogged++ < 5)
        {
         string stale = "TradeBot: bar " + TimeToString(r.time, TIME_MINUTES) + " prisiel neskoro ("
                      + IntegerToString((long)(TimeCurrent() - r.time - PeriodSeconds())) + " s) - bez vstupu";
         Print(stale);
         if(g_spool) StaticHost::SpoolNote(g_engine, "warn", stale);
        }
     }
   ExportOrders(barMs, out, ready);
   if(g_spool && StaticHost::SpoolBar(g_engine, ready) < 0)
     { Print(EngineError("SpoolBar (telemetria vypnuta)")); g_spool = false; }

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
      // paused / flatten (control subor): vstup sa brokerovi neposle, engine si ho odpise timeoutom ako pri !ready
      if(g_mode != "enabled")
        {
         if(!g_suppressLogged)
           { g_suppressLogged = true; Print("TradeBot control: ENTRY ", id, " potlaceny - rezim ", g_mode, " (dalsie potlacene vstupy sa do zmeny rezimu neloguju)"); }
         return;
        }
      // Ten isty vstup este drzi poziciu: Pine by druhy `strategy.entry` s rovnakym id ignoroval.
      if(idx >= 0 && g_orders[idx].filled && g_orders[idx].openQty > 0) return;
      if(idx >= 0)
        {
         // rovnake meno este caka u brokera (re-entry bez CANCEL) - stiahni ho, novy plan ho nahradi
         if(g_orders[idx].orderTicket > 0) g_trade.OrderDelete(g_orders[idx].orderTicket);
         RemoveOrder(idx);
        }

      Tracked t;
      t.id = id; t.orderTicket = 0; t.positionTicket = 0; t.slTicket = 0; t.tpTicket = 0; t.filled = false; t.openQty = 0;
      t.ot = intent.Str("ot"); t.isMarket = t.ot == "Market"; t.lots = 0; t.parked = false;
      t.dir = (int)p.Dbl("dir");
      t.entry = p.Dbl("e"); t.stopLoss = p.Dbl("sl"); t.takeProfit = p.Dbl("tp");
      CJson *tr = p.Find("tr");
      t.hasTrail = tr != NULL;
      t.trailActivation = tr != NULL ? tr.Dbl("ap") : 0;
      t.trailOffset = tr != NULL ? tr.Dbl("op") : 0;
      t.extreme = t.entry; t.lastStop = t.stopLoss;

      t.lots = Lots(p.Dbl("q"));
      // Jedna pozicia naraz (Pine `pyramiding=0`, MultiCharts, Freqtrade `max_open_trades=1`, simulator
      // `scan_trades`): kym pozicia bezi, vstup caka mimo brokera a posle sa, az ked skonci - ak ho engine
      // medzitym nezrusi. Rovnako NinjaTrader adapter (25. 9. 2026 otvoril druhy long popri prvom).
      if(HasOpenPosition())
        {
         t.parked = true;
         if(InpLogEvents) Print("ENTRY ", id, " odlozeny - bezi pozicia");
        }
      else if(!SendEntry(t)) return;
      // vyplnenie (aj market) zaeviduje az deal v OnTradeTransaction - inak by sa objem pocital dvakrat
      int n = ArraySize(g_orders);
      ArrayResize(g_orders, n + 1);
      g_orders[n] = t;
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

bool Sent()
  {
   return g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED;
  }

/// Posle vstup brokerovi; `orderTicket` = cakajuci order (market: ticket orderu, deal pride v OnTradeTransaction).
bool SendEntry(Tracked &t)
  {
   double price = Tick(t.entry);
   // hedging: SL/TP na pozicii (kazdy vstup ma vlastnu); netting: pozicia je jedna na symbol, SL/TP by boli
   // spolocne - vystupy su preto vlastne pending ordery s komentarom = id (PlaceExits po vyplneni)
   double sl = g_hedging ? Tick(t.lastStop) : 0, tp = g_hedging ? Tick(t.takeProfit) : 0;
   bool isLong = t.dir > 0;
   bool ok;
   if(t.ot == "Market")
      ok = isLong ? g_trade.Buy(t.lots, _Symbol, 0, sl, tp, t.id) : g_trade.Sell(t.lots, _Symbol, 0, sl, tp, t.id);
   else if(t.ot == "Stop")
      ok = isLong ? g_trade.BuyStop(t.lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, t.id)
                  : g_trade.SellStop(t.lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, t.id);
   else
      ok = isLong ? g_trade.BuyLimit(t.lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, t.id)
                  : g_trade.SellLimit(t.lots, price, _Symbol, sl, tp, ORDER_TIME_GTC, 0, t.id);
   if(!ok || !Sent())
     { Print("TradeBot: vstup ", t.id, " odmietnuty: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription()); return false; }
   t.orderTicket = g_trade.ResultOrder();
   if(InpLogEvents) Print("ENTRY ", t.id, " ", t.ot, " @", t.entry, " SL ", t.stopLoss, " TP ", t.takeProfit, " lots ", t.lots);
   return true;
  }

/// Bezi pozicia: vyplneny vstup s otvorenym objemom, alebo odoslany market vstup bez dealu.
bool HasOpenPosition()
  {
   for(int i = 0; i < ArraySize(g_orders); i++)
     {
      if(g_orders[i].filled && g_orders[i].openQty > 0) return true;
      if(!g_orders[i].filled && !g_orders[i].parked && g_orders[i].isMarket) return true;
     }
   return false;
  }

/// Vstup sa vyplnil: ostatne cakajuce vstupy stiahni od brokera a odloz (engine o nich stale vie).
void ParkOthers(int filled)
  {
   for(int i = 0; i < ArraySize(g_orders); i++)
     {
      if(i == filled || g_orders[i].filled || g_orders[i].parked || g_orders[i].isMarket) continue;
      if(g_orders[i].orderTicket > 0 && !g_trade.OrderDelete(g_orders[i].orderTicket))
        { Print("TradeBot: odlozenie ", g_orders[i].id, " zlyhalo: ", g_trade.ResultRetcode()); continue; }
      g_orders[i].orderTicket = 0;
      g_orders[i].parked = true;
      if(InpLogEvents) Print("ENTRY ", g_orders[i].id, " odlozeny - vyplnil sa ", g_orders[filled].id);
     }
  }

/// Pozicia skoncila: odlozene vstupy znova k brokerovi.
void ReleaseParked()
  {
   if(HasOpenPosition()) return;
   for(int i = ArraySize(g_orders) - 1; i >= 0; i--)
     {
      if(!g_orders[i].parked) continue;
      g_orders[i].parked = false;
      // paused / flatten: odlozeny vstup sa uz neposle (engine si ho odpise timeoutom)
      if(g_mode != "enabled") { if(InpLogEvents) Print("ENTRY ", g_orders[i].id, " odlozeny sa neposle - rezim ", g_mode); RemoveOrder(i); continue; }
      if(!SendEntry(g_orders[i])) RemoveOrder(i);
     }
  }

/// Netting: vystupy vstupu ako vlastne pending ordery (SL = stop, TP = limit) opacneho smeru s komentarom = id.
/// Vyplnenie jedneho zrusi druhy (OCO robi adapter v OnTradeTransaction).
void PlaceExits(int i)
  {
   if(g_hedging || g_orders[i].openQty <= 0) return;
   bool isLong = g_orders[i].dir > 0;
   double vol = g_orders[i].openQty, sl = Tick(g_orders[i].lastStop), tp = Tick(g_orders[i].takeProfit);
   string id = g_orders[i].id;
   if(isLong ? g_trade.SellStop(vol, sl, _Symbol, 0, 0, ORDER_TIME_GTC, 0, id) : g_trade.BuyStop(vol, sl, _Symbol, 0, 0, ORDER_TIME_GTC, 0, id))
      if(Sent()) g_orders[i].slTicket = g_trade.ResultOrder();
   if(g_orders[i].slTicket == 0) Print("TradeBot: SL order ", id, " odmietnuty: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
   if(isLong ? g_trade.SellLimit(vol, tp, _Symbol, 0, 0, ORDER_TIME_GTC, 0, id) : g_trade.BuyLimit(vol, tp, _Symbol, 0, 0, ORDER_TIME_GTC, 0, id))
      if(Sent()) g_orders[i].tpTicket = g_trade.ResultOrder();
   if(g_orders[i].tpTicket == 0) Print("TradeBot: TP order ", id, " odmietnuty: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
  }

void CancelExits(int i)
  {
   if(g_orders[i].slTicket > 0) { g_trade.OrderDelete(g_orders[i].slTicket); g_orders[i].slTicket = 0; }
   if(g_orders[i].tpTicket > 0) { g_trade.OrderDelete(g_orders[i].tpTicket); g_orders[i].tpTicket = 0; }
  }

/// Zavretie vstupu enginom (close, koniec seansy) - nepocita sa ako vyhra.
void ClosePosition(int idx)
  {
   if(g_hedging)
     {
      if(g_orders[idx].positionTicket > 0) g_trade.PositionClose(g_orders[idx].positionTicket);
      return;
     }
   // netting: opacny market order s komentarom "close:<id>" zavrie prave tolko z netto pozicie
   CancelExits(idx);
   double vol = MathMin(g_orders[idx].openQty, PositionSelect(_Symbol) ? PositionGetDouble(POSITION_VOLUME) : 0);
   if(vol <= 0) { g_orders[idx].openQty = 0; return; }
   string comment = "close:" + g_orders[idx].id;
   if(g_orders[idx].dir > 0) g_trade.Sell(vol, _Symbol, 0, 0, 0, comment); else g_trade.Buy(vol, _Symbol, 0, 0, 0, comment);
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
      bool moved = false;
      if(g_hedging) { if(g_orders[i].positionTicket > 0) moved = g_trade.PositionModify(g_orders[i].positionTicket, Tick(stop), Tick(g_orders[i].takeProfit)); }
      else if(g_orders[i].slTicket > 0) moved = g_trade.OrderModify(g_orders[i].slTicket, Tick(stop), 0, 0, ORDER_TIME_GTC, 0, 0);
      // kazdy uspesny posun stopu ide do spoolu ako order/modify, aby webapp videla trailing (docs/LIVE.md)
      if(moved) SpoolModify(ToMs(r.time), g_orders[i].id, Tick(stop), 0, "trailing", !g_replaying && !MQLInfoInteger(MQL_TESTER));
     }
  }

//+------------------------------------------------------------------+
//| Vyplnenia: co sa stalo s nasimi ordermi (zrkadlo OnExecutionUpdate v NinjaTraderi)                 |
//+------------------------------------------------------------------+
void CountWin(int i, double exitPrice, datetime dealTime)
  {
   // Pine `dailyWinsCount`: vyhra = zisk voci PLANOVANEMU vstupu > 0 (ako NinjaTrader adapter)
   double move = g_orders[i].dir > 0 ? exitPrice - g_orders[i].entry : g_orders[i].entry - exitPrice;
   if(move <= 0) return;
   long day = UtcDay(ToMs(dealTime));
   if(g_winsDay != day) { g_winsDay = day; g_winsCount = 0; }
   g_winsCount++;
   if(InpLogEvents) Print("VYHRA ", g_orders[i].id, " @", exitPrice, " (", g_winsCount, ". dnes)");
}

/// Uzavretie casti/celeho vstupu; `win` = vystup na SL/TP (pocita sa do denneho limitu).
void Reduce(int i, double volume, double price, datetime dealTime, bool win)
  {
   ExportFill(dealTime, g_orders[i].id, false, win ? "sltp" : "close", price, volume);
   SpoolFill(dealTime, g_orders[i].id, false, win ? "sltp" : "close", price, volume, !g_replaying && !MQLInfoInteger(MQL_TESTER));
   g_orders[i].openQty = MathMax(0.0, g_orders[i].openQty - volume);
   if(g_orders[i].openQty > 0) return;
   CancelExits(i);
   if(win) CountWin(i, price, dealTime);
   RemoveOrder(i);
  }

/// Netting: vstup opacneho smeru najprv zavrie vsetko otvorene v opacnom smere (deal OUT/INOUT).
/// Vrati objem, ktory sa tym zavrel.
double CloseOpposite(int dir, double volume, double price, datetime dealTime)
  {
   double closed = 0;
   for(int i = ArraySize(g_orders) - 1; i >= 0 && volume - closed > 1e-9; i--)
     {
      if(!g_orders[i].filled || g_orders[i].openQty <= 0 || g_orders[i].dir == dir) continue;
      double part = MathMin(g_orders[i].openQty, volume - closed);
      closed += part;
      Reduce(i, part, price, dealTime, false);   // zavretie opacnym vstupom nie je SL/TP
     }
   return closed;
  }

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   HandleDeal(trans);
   // az po celom deale: pri netting obrate CloseOpposite na chvilu nechava poziciu nulovu
   ReleaseParked();
   // zmena profilu, ktora cakala na flat (control subor)
   RetryPendingProfile();
  }

void HandleDeal(const MqlTradeTransaction &trans)
  {
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   string comment = HistoryDealGetString(trans.deal, DEAL_COMMENT);
   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   ENUM_DEAL_REASON reason = (ENUM_DEAL_REASON)HistoryDealGetInteger(trans.deal, DEAL_REASON);
   ENUM_DEAL_TYPE type = (ENUM_DEAL_TYPE)HistoryDealGetInteger(trans.deal, DEAL_TYPE);
   double volume = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
   double price = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   datetime dealTime = (datetime)HistoryDealGetInteger(trans.deal, DEAL_TIME);
   ulong positionId = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   int dealDir = type == DEAL_TYPE_BUY ? 1 : (type == DEAL_TYPE_SELL ? -1 : 0);
   if(dealDir == 0) return;

   int idx = FindOrder(comment);
   bool isEntryDeal = idx >= 0 && !g_orders[idx].filled;

   if(isEntryDeal || entry == DEAL_ENTRY_IN || entry == DEAL_ENTRY_INOUT)
     {
      // netting: vstup proti otvorenej pozicii ju najprv zavrie (OUT = cely, INOUT = cast a zvysok otvori)
      double closed = g_hedging ? 0 : CloseOpposite(dealDir, volume, price, dealTime);
      idx = FindOrder(comment);   // CloseOpposite mohol pole preusporiadat
      if(idx < 0) return;
      g_orders[idx].filled = true;
      g_orders[idx].parked = false;
      g_orders[idx].openQty += volume - closed;
      g_orders[idx].positionTicket = positionId;
      ExportFill(dealTime, comment, true, "", price, volume - closed);
      SpoolFill(dealTime, comment, true, "", price, volume - closed, !g_replaying && !MQLInfoInteger(MQL_TESTER));
      if(g_orders[idx].openQty > 0) { PlaceExits(idx); ParkOthers(idx); } else RemoveOrder(idx);
      return;
     }

   // vystup
   if(g_hedging)
     {
      for(int i = 0; i < ArraySize(g_orders); i++)
         if(g_orders[i].filled && g_orders[i].openQty > 0 && g_orders[i].positionTicket == positionId)
           { Reduce(i, volume, price, dealTime, reason == DEAL_REASON_SL || reason == DEAL_REASON_TP); return; }
      return;
     }
   if(idx >= 0) { Reduce(idx, volume, price, dealTime, true); return; }          // nas SL/TP order (komentar = id)
   if(StringFind(comment, "close:") == 0)
     {
      idx = FindOrder(StringSubstr(comment, 6));
      if(idx >= 0) Reduce(idx, volume, price, dealTime, false);
      return;
     }
   // cudzie zavretie netto pozicie (rucne, stop-out): odpise sa z otvorenych vstupov v smere pozicie
   double left = volume;
   for(int i = ArraySize(g_orders) - 1; i >= 0 && left > 1e-9; i--)
     {
      if(!g_orders[i].filled || g_orders[i].openQty <= 0 || g_orders[i].dir == dealDir) continue;
      double part = MathMin(g_orders[i].openQty, left);
      left -= part;
      Reduce(i, part, price, dealTime, false);
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
