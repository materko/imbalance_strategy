//+------------------------------------------------------------------+
//| TradeBotExecutor.mqh - tenky vykonavac orderov pre strategiu, ktora bezi v inej platforme          |
//|                                                                                                   |
//| docs/ROUTING.md: strategia (engine, bary, telemetria) bezi v NinjaTraderi na jeho datach, ordery    |
//| idu sem. Jeden exekutor na MT5 ucet obsluzi vsetky route (NT instancie) a vsetky symboly uctu -    |
//| graf, na ktorom sedi, je jedno. Kanal su subory v Common\Files\TradeBot\bridge\<instancia>\ a      |
//| cely protokol je v C# jadre (`TradeBot.Core.Bridge`, fasada `StaticHost::Bridge*`): MQL tu len      |
//| cita prikazy, vola CTrade a hlasi, co sa stalo.                                                    |
//|                                                                                                   |
//| Co exekutor robi sam (aj ked NinjaTrader nebezi - nic sa preto nerusi):                            |
//|   - SL/TP su v orderi u brokera; po vyplneni sa prekotvia na skutocny fill (riziko v bodoch ostava) |
//|   - terminy z `life` (cancel_at / close_at / hold_ms) s odkladom 5 s                               |
//|   - strazca SL: pozicia bez stopu ho dostane znova, po 3 neuspechoch sa zavrie trhom              |
//|   - zalozny trailing na zatvoreni 1m baru symbolu, ked heartbeat NT je starsi nez 30 s            |
//| Len hedging ucet (kazdy vstup vlastna pozicia). Netting route odmietne (`netting_unsupported`).    |
//|                                                                                                   |
//| Pamat cez restart terminalu: Common\Files\TradeBot\exec\<id>.orders.json - po starte sa zladi s    |
//| brokerom (pozicia ticket = ticket orderu, ktory ju otvoril). Co sa zavrelo pocas vypadku, ide do   |
//| evt.jsonl ako fill z historie dealov.                                                             |
//+------------------------------------------------------------------+
#property copyright "TradeBot"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include <TradeBot/TradeBotJson.mqh>

#import "TradeBot.dll"
#import

input int    InpTimerMs        = 50;      // Ako casto citat prikazy (ms)
input int    InpDeviationPts   = 50;      // Povoleny sklz market orderov v bodoch symbolu
input bool   InpLog            = true;    // Logovat kazdy prikaz do Experts logu

const string ExecVersion   = "1";
const int    NoStopGraceSec  = 2;
const int    MaxExitAttempts = 3;
const long   MasterLostMs    = 30000;     // Bridge.MasterLostMs

struct XRoute
  {
   string id;
   string symbol;
   string price;        // basis / same
   double scale;
   string qtyMode;      // value / fixed
   double lots;
   long   magic;
   double ntPointValue;
   string state;        // co hlasi heartbeat (ok / symbol_missing / netting_unsupported ...)
   string detail;
   bool   masterLost;
   bool   masterSeen;
   string masterSession;
   datetime lastM1;     // posledny spracovany 1m bar (server)
   bool   seen;         // pri obnove zoznamu: route este existuje
  };

struct XOrder
  {
   string route;
   string id;           // id vstupu z enginu (komentar orderu)
   string cid;          // prikaz, ktory ho zalozil
   int    dir;
   string ot;           // Limit / Market / Stop
   double q;            // kontrakty mastera
   double ntEntry, ntSl, ntTp;   // plan v cenach mastera
   double entry, sl0, tp0;       // v cenach exekutora pri odoslani (sl0/tp0 po prekotveni)
   double lots;
   ulong  ticket;       // order; v hedgingu aj ticket pozicie po vyplneni
   bool   filled;
   double fill;         // cena vstupu u brokera
   long   fillMs;
   double openLots;
   long   cancelAt, closeAt, holdMs;
   bool   hasTrail;
   double trailAct, trailOff;    // v cenach exekutora (x scale)
   double extreme;
   double lastStop, lastTp;
   bool   closing;
   int    closeFails;
   datetime closeRetryAt;
   string closeWhy;     // close / life_close / flatten
   int    slFails;
   datetime noStopSince;
   bool   cancelWanted;
   string cancelWhy;
  };

int      g_x = -1;              // handle exekutora v StaticHost
string   g_root = "";
string   g_id = "";
string   g_statePath = "";      // relativne k Common\Files
string   g_stateText = "";
XRoute   g_routes[];
XOrder   g_xo[];
CTrade   g_trade;
int      g_gmtOffsetSec = 0;
datetime g_lastSlow = 0;
datetime g_lastRoutes = 0;
bool     g_hedging = false;

//+------------------------------------------------------------------+
//| Pomocne                                                          |
//+------------------------------------------------------------------+
string Num(double v) { return StringFormat("%.17g", v); }

string JStr(string s)
  {
   StringReplace(s, "\\", "\\\\");
   StringReplace(s, "\"", "\\\"");
   return "\"" + s + "\"";
  }

long NowMs() { return (long)TimeGMT() * 1000; }

void RefreshGmtOffset()
  {
   long diff = (long)TimeTradeServer() - (long)TimeGMT();
   g_gmtOffsetSec = (int)(MathRound(diff / 900.0) * 900);
  }

long ServerMsToUtc(long serverMs) { return serverMs - (long)g_gmtOffsetSec * 1000; }

bool Sent() { return g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED; }

string TradeErr() { return IntegerToString(g_trade.ResultRetcode()) + " " + g_trade.ResultRetcodeDescription(); }

int FindRoute(string id)
  {
   for(int i = 0; i < ArraySize(g_routes); i++) if(g_routes[i].id == id) return i;
   return -1;
  }

int FindOrder(string route, string id)
  {
   for(int i = 0; i < ArraySize(g_xo); i++) if(g_xo[i].route == route && g_xo[i].id == id) return i;
   return -1;
  }

void RemoveOrder(int i)
  {
   int n = ArraySize(g_xo);
   for(int k = i; k < n - 1; k++) g_xo[k] = g_xo[k + 1];
   ArrayResize(g_xo, n - 1);
  }

double Tick(string sym) { return SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE); }
double Mid(string sym) { return (SymbolInfoDouble(sym, SYMBOL_BID) + SymbolInfoDouble(sym, SYMBOL_ASK)) / 2.0; }
double RoundTick(string sym, double p) { return StaticHost::BridgeMapPrice(p, 0, 0, 1.0, Tick(sym)); }

/// Udalost do evt.jsonl route (StaticHost::BridgeEmit). Ceny a objemy 0 = nepisu sa.
void Emit(string route, string kind, string cid, string id, string side, double price, double priceNt, double qty,
          double lots, long execMs, string exitName, string text)
  {
   if(StaticHost::BridgeEmit(g_x, route, NowMs(), kind, cid, id, side, price, priceNt, qty, lots, execMs, exitName, text) < 0)
      Print("TradeBot exekutor: zapis udalosti ", kind, " do ", route, " zlyhal: ", StaticHost::LastError());
  }

void Note(string route, string level, string text)
  {
   Print("TradeBot exekutor [", route, "] ", level, ": ", text);
   if(route != "") Emit(route, "note", "", "", level, 0, 0, 0, 0, 0, "", text);
  }

/// Cena exekutora -> cena mastera pre vyplnenie: planovany vstup mastera + sklz prepocitany mierkou.
double NtPrice(const XOrder &o, double execPrice, double anchorExec, double anchorNt)
  {
   int r = FindRoute(o.route);
   double scale = r >= 0 ? g_routes[r].scale : 1.0;
   return StaticHost::BridgeToNtPrice(execPrice, anchorNt, anchorExec, scale);
  }

double QtyNt(const XOrder &o, double lots) { return o.lots > 0 ? o.q * lots / o.lots : 0; }

//+------------------------------------------------------------------+
//| Pamat cez restart                                                |
//+------------------------------------------------------------------+
string OrderJson(const XOrder &o)
  {
   return "{" + "\"route\":" + JStr(o.route) + ",\"id\":" + JStr(o.id) + ",\"cid\":" + JStr(o.cid)
          + ",\"dir\":" + IntegerToString(o.dir) + ",\"ot\":" + JStr(o.ot) + ",\"q\":" + Num(o.q)
          + ",\"nte\":" + Num(o.ntEntry) + ",\"ntsl\":" + Num(o.ntSl) + ",\"nttp\":" + Num(o.ntTp)
          + ",\"e\":" + Num(o.entry) + ",\"sl0\":" + Num(o.sl0) + ",\"tp0\":" + Num(o.tp0) + ",\"lots\":" + Num(o.lots)
          + ",\"ticket\":" + IntegerToString((long)o.ticket) + ",\"filled\":" + (o.filled ? "true" : "false")
          + ",\"fill\":" + Num(o.fill) + ",\"fill_ms\":" + IntegerToString(o.fillMs) + ",\"open\":" + Num(o.openLots)
          + ",\"cancel_at\":" + IntegerToString(o.cancelAt) + ",\"close_at\":" + IntegerToString(o.closeAt)
          + ",\"hold_ms\":" + IntegerToString(o.holdMs) + ",\"trail\":" + (o.hasTrail ? "true" : "false")
          + ",\"ta\":" + Num(o.trailAct) + ",\"to\":" + Num(o.trailOff) + ",\"ext\":" + Num(o.extreme)
          + ",\"stop\":" + Num(o.lastStop) + ",\"tp\":" + Num(o.lastTp) + "}";
  }

void SaveState()
  {
   string text = "[";
   for(int i = 0; i < ArraySize(g_xo); i++) text += (i > 0 ? "," : "") + OrderJson(g_xo[i]);
   text += "]";
   if(text == g_stateText) return;
   string tmp = g_statePath + ".tmp";
   int h = FileOpen(tmp, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE) { Print("TradeBot exekutor: stav sa neda zapisat: ", GetLastError()); return; }
   FileWriteString(h, text);
   FileClose(h);
   if(!FileMove(tmp, FILE_COMMON, g_statePath, FILE_REWRITE | FILE_COMMON))
     { Print("TradeBot exekutor: presun stavu zlyhal: ", GetLastError()); return; }
   g_stateText = text;
  }

void LoadState()
  {
   ArrayResize(g_xo, 0);
   if(!FileIsExist(g_statePath, FILE_COMMON)) return;
   int h = FileOpen(g_statePath, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE) return;
   string text = "";
   while(!FileIsEnding(h)) text += FileReadString(h);
   FileClose(h);
   CJson *root = JsonParse(text);
   if(root == NULL || root.type != JSON_ARRAY) { Print("TradeBot exekutor: stav je poskodeny, zacinam bez neho"); if(root != NULL) delete root; return; }
   for(int i = 0; i < root.Size(); i++)
     {
      CJson *j = root.At(i);
      XOrder o;
      ZeroMemory(o);
      o.route = j.Str("route"); o.id = j.Str("id"); o.cid = j.Str("cid"); o.dir = (int)j.Dbl("dir"); o.ot = j.Str("ot");
      o.q = j.Dbl("q"); o.ntEntry = j.Dbl("nte"); o.ntSl = j.Dbl("ntsl"); o.ntTp = j.Dbl("nttp");
      o.entry = j.Dbl("e"); o.sl0 = j.Dbl("sl0"); o.tp0 = j.Dbl("tp0"); o.lots = j.Dbl("lots");
      o.ticket = (ulong)j.Dbl("ticket"); o.filled = j.Bool("filled"); o.fill = j.Dbl("fill"); o.fillMs = (long)j.Dbl("fill_ms");
      o.openLots = j.Dbl("open"); o.cancelAt = (long)j.Dbl("cancel_at"); o.closeAt = (long)j.Dbl("close_at");
      o.holdMs = (long)j.Dbl("hold_ms"); o.hasTrail = j.Bool("trail"); o.trailAct = j.Dbl("ta"); o.trailOff = j.Dbl("to");
      o.extreme = j.Dbl("ext"); o.lastStop = j.Dbl("stop"); o.lastTp = j.Dbl("tp");
      int n = ArraySize(g_xo);
      ArrayResize(g_xo, n + 1);
      g_xo[n] = o;
     }
   delete root;
  }

/// Po starte: co zo stavu este zije u brokera. Pozicia v hedgingu ma ticket orderu, ktory ju otvoril.
void Reconcile()
  {
   int kept = 0, closed = 0, gone = 0;
   for(int i = ArraySize(g_xo) - 1; i >= 0; i--)
     {
      ulong t = g_xo[i].ticket;
      if(PositionSelectByTicket(t))
        {
         if(!g_xo[i].filled)
           {
            // vyplnil sa pocas vypadku
            g_xo[i].filled = true;
            g_xo[i].fill = PositionGetDouble(POSITION_PRICE_OPEN);
            g_xo[i].fillMs = ServerMsToUtc(PositionGetInteger(POSITION_TIME_MSC));
            g_xo[i].extreme = g_xo[i].fill;
            Emit(g_xo[i].route, "fill", g_xo[i].cid, g_xo[i].id, "in", g_xo[i].fill,
                 NtPrice(g_xo[i], g_xo[i].fill, g_xo[i].entry, g_xo[i].ntEntry), g_xo[i].q, PositionGetDouble(POSITION_VOLUME),
                 g_xo[i].fillMs, "", "vyplnene pocas vypadku exekutora");
           }
         g_xo[i].openLots = PositionGetDouble(POSITION_VOLUME);
         kept++;
         continue;
        }
      if(!g_xo[i].filled && OrderSelect(t)) { kept++; continue; }
      // ani pozicia, ani cakajuci order: dohladat v historii
      if(HistorySelectByPosition(t))
        {
         double inLots = 0;
         for(int k = 0; k < HistoryDealsTotal(); k++)
           {
            ulong d = HistoryDealGetTicket(k);
            ENUM_DEAL_ENTRY e = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(d, DEAL_ENTRY);
            double vol = HistoryDealGetDouble(d, DEAL_VOLUME), px = HistoryDealGetDouble(d, DEAL_PRICE);
            long ms = ServerMsToUtc(HistoryDealGetInteger(d, DEAL_TIME_MSC));
            if(e == DEAL_ENTRY_IN)
              {
               inLots += vol;
               if(!g_xo[i].filled)
                 {
                  g_xo[i].filled = true; g_xo[i].fill = px; g_xo[i].fillMs = ms;
                  Emit(g_xo[i].route, "fill", g_xo[i].cid, g_xo[i].id, "in", px, NtPrice(g_xo[i], px, g_xo[i].entry, g_xo[i].ntEntry),
                       g_xo[i].q, vol, ms, "", "vyplnene pocas vypadku exekutora");
                 }
               continue;
              }
            ENUM_DEAL_REASON why = (ENUM_DEAL_REASON)HistoryDealGetInteger(d, DEAL_REASON);
            string exitName = why == DEAL_REASON_SL ? "sl" : (why == DEAL_REASON_TP ? "tp" : "external");
            double ntFill = NtPrice(g_xo[i], g_xo[i].fill, g_xo[i].entry, g_xo[i].ntEntry);
            Emit(g_xo[i].route, "fill", g_xo[i].cid, g_xo[i].id, "out", px, NtPrice(g_xo[i], px, g_xo[i].fill, ntFill),
                 QtyNt(g_xo[i], vol), vol, ms, exitName, "zatvorene pocas vypadku exekutora");
           }
         if(inLots > 0) { closed++; RemoveOrder(i); continue; }
        }
      Emit(g_xo[i].route, "cancelled", g_xo[i].cid, g_xo[i].id, "", 0, 0, 0, 0, 0, "", "order u brokera po restarte nie je");
      gone++;
      RemoveOrder(i);
     }
   if(kept + closed + gone > 0)
      Print(StringFormat("TradeBot exekutor: po restarte %d orderov/pozicii bezi dalej, %d sa medzitym zavrelo, %d u brokera nie je",
                         kept, closed, gone));
   SaveState();
  }

//+------------------------------------------------------------------+
//| Route a heartbeat                                                |
//+------------------------------------------------------------------+
void RefreshRoutes()
  {
   string raw = StaticHost::BridgeRoutes(g_x);
   if(raw == "") { Print("TradeBot exekutor: zoznam route: ", StaticHost::LastError()); return; }
   CJson *arr = JsonParse(raw);
   if(arr == NULL) return;
   for(int i = 0; i < ArraySize(g_routes); i++) g_routes[i].seen = false;
   for(int k = 0; k < arr.Size(); k++)
     {
      CJson *j = arr.At(k);
      string id = j.Str("id");
      int r = FindRoute(id);
      if(r < 0)
        {
         r = ArraySize(g_routes);
         ArrayResize(g_routes, r + 1);
         ZeroMemory(g_routes[r]);
         g_routes[r].id = id;
         Print("TradeBot exekutor: nova route ", id, " -> ", j.Str("symbol"));
        }
      g_routes[r].symbol = j.Str("symbol");
      g_routes[r].price = j.Str("price");
      g_routes[r].scale = j.Dbl("scale") > 0 ? j.Dbl("scale") : 1.0;
      g_routes[r].qtyMode = j.Str("qty_mode");
      g_routes[r].lots = j.Dbl("lots");
      g_routes[r].magic = (long)j.Dbl("magic");
      g_routes[r].ntPointValue = j.Dbl("nt_point_value");
      g_routes[r].seen = true;
      CheckRoute(r);
     }
   delete arr;
   for(int i = ArraySize(g_routes) - 1; i >= 0; i--)
     {
      if(g_routes[i].seen) continue;
      Print("TradeBot exekutor: route ", g_routes[i].id, " zmizla (otvorene ordery sa stazia dalej)");
      int n = ArraySize(g_routes);
      for(int k = i; k < n - 1; k++) g_routes[k] = g_routes[k + 1];
      ArrayResize(g_routes, n - 1);
     }
  }

/// Stav route, ktory ide do heartbeatu: symbol na ucte, obchodovatelny oboma smermi, hedging.
void CheckRoute(int r)
  {
   string state = "ok", detail = "";
   bool custom = false;
   string sym = g_routes[r].symbol;
   if(!g_hedging) { state = "netting_unsupported"; detail = "ucet nie je hedging"; }
   else if(sym == "" || !SymbolExist(sym, custom)) { state = "symbol_missing"; detail = "ucet nema symbol " + sym; }
   else
     {
      SymbolSelect(sym, true);
      if(SymbolInfoInteger(sym, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL)
        { state = "symbol_missing"; detail = "symbol " + sym + " sa neda obchodovat oboma smermi"; }
     }
   if(state != g_routes[r].state && g_routes[r].state != "")
      Print("TradeBot exekutor: route ", g_routes[r].id, " ", g_routes[r].state, " -> ", state, " ", detail);
   g_routes[r].state = state;
   g_routes[r].detail = detail;
  }

bool TradeAllowed()
  {
   return TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED)
          && AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) && AccountInfoInteger(ACCOUNT_TRADE_EXPERT);
  }

void WriteHeartbeat()
  {
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   if(StaticHost::BridgeHbBegin(g_x, NowMs(), login, AccountInfoString(ACCOUNT_SERVER), g_hedging ? "hedging" : "netting",
                                TerminalInfoInteger(TERMINAL_CONNECTED) != 0, TradeAllowed(), ExecVersion) < 0)
     { Print("TradeBot exekutor: heartbeat: ", StaticHost::LastError()); return; }
   // symboly: vsetky z Market Watch (webapp z nich ponuka vyber pri nasadeni) - route ich tam pridava sama
   int n = SymbolsTotal(true);
   for(int i = 0; i < n; i++)
     {
      string s = SymbolName(i, true);
      StaticHost::BridgeHbSymbol(g_x, s, Tick(s), SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE),
                                 SymbolInfoDouble(s, SYMBOL_VOLUME_MIN), SymbolInfoDouble(s, SYMBOL_VOLUME_STEP),
                                 SymbolInfoDouble(s, SYMBOL_VOLUME_MAX), (int)SymbolInfoInteger(s, SYMBOL_TRADE_MODE),
                                 SymbolInfoDouble(s, SYMBOL_BID), SymbolInfoDouble(s, SYMBOL_ASK));
     }
   for(int r = 0; r < ArraySize(g_routes); r++)
      StaticHost::BridgeHbRoute(g_x, g_routes[r].id, g_routes[r].state, g_routes[r].detail);
   if(StaticHost::BridgeHbWrite(g_x) < 0) Print("TradeBot exekutor: heartbeat: ", StaticHost::LastError());
  }

/// Zije master route? Nikoho nic neruší - len sa to zapise a exekutor prevezme trailing.
void WatchMasters()
  {
   long now = NowMs();
   for(int r = 0; r < ArraySize(g_routes); r++)
     {
      long age = StaticHost::BridgeMasterAge(g_x, g_routes[r].id, now);
      string session = StaticHost::BridgeMasterSession(g_x, g_routes[r].id);
      bool lost = age < 0 || age > MasterLostMs;
      if(age >= 0) g_routes[r].masterSeen = true;
      if(lost && !g_routes[r].masterLost && g_routes[r].masterSeen)
         Note(g_routes[r].id, "warn", StringFormat("master neodpoveda %d s - ordery bezia dalej podla svojho life, trailing preberam", (int)(age / 1000)));
      if(!lost && g_routes[r].masterLost)
         Note(g_routes[r].id, "info", "master je spat (session " + session + ")");
      g_routes[r].masterLost = lost && g_routes[r].masterSeen;
      g_routes[r].masterSession = session;
     }
  }

//+------------------------------------------------------------------+
//| Prikazy                                                          |
//+------------------------------------------------------------------+
void PollCommands()
  {
   for(int r = 0; r < ArraySize(g_routes); r++)
     {
      string raw = StaticHost::BridgePoll(g_x, g_routes[r].id);
      if(raw == "") { Print("TradeBot exekutor: prikazy ", g_routes[r].id, ": ", StaticHost::LastError()); continue; }
      if(raw == "[]") continue;
      CJson *arr = JsonParse(raw);
      if(arr == NULL) { Print("TradeBot exekutor: prikazy ", g_routes[r].id, " sa nedaju precitat"); continue; }
      for(int k = 0; k < arr.Size(); k++)
        {
         CJson *c = arr.At(k);
         string cid = c.Str("cid");
         Handle(r, c);
         if(StaticHost::BridgeDone(g_x, g_routes[r].id, cid) < 0)
            Print("TradeBot exekutor: Done ", cid, ": ", StaticHost::LastError());
        }
      delete arr;
      SaveState();
     }
  }

void Handle(int r, CJson *c)
  {
   string a = c.Str("a"), cid = c.Str("cid"), id = c.Str("id"), route = g_routes[r].id;
   if(InpLog) Print("TradeBot exekutor [", route, "] ", a, " ", id, " (", cid, ")");
   if(a == "entry") { HandleEntry(r, c); return; }
   if(a == "cancel")
     {
      int i = FindOrder(route, id);
      if(i < 0) { Emit(route, "ack", cid, id, "", 0, 0, 0, 0, 0, "", "nic na zrusenie"); return; }
      if(g_xo[i].filled) { Emit(route, "ack", cid, id, "", 0, 0, 0, 0, 0, "", "uz je vyplneny - cancel sa ignoruje"); return; }
      CancelEntry(i, cid, c.Str("r"));
      return;
     }
   if(a == "close")
     {
      int i = FindOrder(route, id);
      if(i < 0) { Emit(route, "ack", cid, id, "", 0, 0, 0, 0, 0, "", "nic na zatvorenie"); return; }
      if(!g_xo[i].filled) { CancelEntry(i, cid, c.Str("r")); return; }
      g_xo[i].closeWhy = "close";
      ClosePosition(i);
      Emit(route, "ack", cid, id, "", 0, 0, 0, 0, 0, "", "zatvaram");
      return;
     }
   if(a == "modify") { HandleModify(r, c); return; }
   if(a == "flatten")
     {
      for(int i = ArraySize(g_xo) - 1; i >= 0; i--)
        {
         if(g_xo[i].route != route) continue;
         if(!g_xo[i].filled) CancelEntry(i, cid, "flatten");
         else { g_xo[i].closeWhy = "flatten"; ClosePosition(i); }
        }
      Emit(route, "ack", cid, "", "", 0, 0, 0, 0, 0, "", "flatten");
      return;
     }
   if(a == "sync") { Snapshot(r, cid); return; }
   Emit(route, "reject", cid, id, "", 0, 0, 0, 0, 0, "", "neznamy prikaz " + a);
  }

void Snapshot(int r, string cid)
  {
   string route = g_routes[r].id;
   int n = 0;
   for(int i = 0; i < ArraySize(g_xo); i++)
     {
      if(g_xo[i].route != route) continue;
      n++;
      string side = g_xo[i].dir > 0 ? "long" : "short";
      if(g_xo[i].filled)
         Emit(route, "pos", cid, g_xo[i].id, side, g_xo[i].fill, NtPrice(g_xo[i], g_xo[i].fill, g_xo[i].entry, g_xo[i].ntEntry),
              QtyNt(g_xo[i], g_xo[i].openLots), g_xo[i].openLots, g_xo[i].fillMs, "", "SL " + Num(g_xo[i].lastStop) + " TP " + Num(g_xo[i].lastTp));
      else
         Emit(route, "order", cid, g_xo[i].id, side, g_xo[i].entry, g_xo[i].ntEntry, g_xo[i].q, g_xo[i].lots, 0, "", g_xo[i].ot);
     }
   Emit(route, "snapshot", cid, "", "", 0, 0, n, 0, 0, "", g_routes[r].state);
  }

/// Order s tym istym magic a komentarom uz u brokera je (prikaz sa po pade zopakoval) - ticket, inak 0.
ulong Existing(string sym, long magic, string id)
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetInteger(ORDER_MAGIC) == magic && OrderGetString(ORDER_SYMBOL) == sym && OrderGetString(ORDER_COMMENT) == id) return t;
     }
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == magic && PositionGetString(POSITION_SYMBOL) == sym && PositionGetString(POSITION_COMMENT) == id) return t;
     }
   return 0;
  }

void HandleEntry(int r, CJson *c)
  {
   string route = g_routes[r].id, cid = c.Str("cid"), id = c.Str("id"), sym = g_routes[r].symbol;
   long now = NowMs();
   long exp = (long)c.Dbl("exp");
   if(exp > 0 && now > exp) { Emit(route, "reject", cid, id, "", 0, 0, 0, 0, 0, "", "expired: prikaz prisiel neskoro (" + IntegerToString((now - exp) / 1000) + " s po termine)"); return; }
   if(g_routes[r].state != "ok") { Emit(route, "reject", cid, id, "", 0, 0, 0, 0, 0, "", g_routes[r].state + ": " + g_routes[r].detail); return; }
   if(FindOrder(route, id) >= 0) { Emit(route, "ack", cid, id, "", 0, 0, 0, 0, 0, "", "vstup uz bezi"); return; }
   CJson *p = c.Find("p");
   if(p == NULL) { Emit(route, "reject", cid, id, "", 0, 0, 0, 0, 0, "", "vstup bez planu"); return; }

   XOrder o;
   ZeroMemory(o);
   o.route = route; o.id = id; o.cid = cid;
   o.dir = (int)p.Dbl("dir"); o.ot = c.Str("ot"); o.q = p.Dbl("q");
   o.ntEntry = p.Dbl("e"); o.ntSl = p.Dbl("sl"); o.ntTp = p.Dbl("tp");
   double scale = g_routes[r].scale, tick = Tick(sym);
   bool same = g_routes[r].price == "same";
   double refNt = c.Dbl("ref"), refExec = Mid(sym);
   if(refNt <= 0) refNt = o.ntEntry;
   o.entry = same ? RoundTick(sym, o.ntEntry) : StaticHost::BridgeMapPrice(o.ntEntry, refNt, refExec, scale, tick);
   o.sl0 = same ? RoundTick(sym, o.ntSl) : StaticHost::BridgeMapPrice(o.ntSl, refNt, refExec, scale, tick);
   o.tp0 = same ? RoundTick(sym, o.ntTp) : StaticHost::BridgeMapPrice(o.ntTp, refNt, refExec, scale, tick);
   o.lastStop = o.sl0; o.lastTp = o.tp0;
   o.lots = StaticHost::BridgeLots(o.q, g_routes[r].ntPointValue, scale, SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE), tick,
                                   SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP),
                                   SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX), g_routes[r].qtyMode, g_routes[r].lots);
   if(o.lots <= 0)
     { Emit(route, "reject", cid, id, "", 0, 0, o.q, 0, 0, "", StringFormat("objem %.2f kontraktov je na %s pod minimom lotov", o.q, sym)); return; }
   CJson *life = c.Find("life");
   if(life != NULL) { o.cancelAt = (long)life.Dbl("cancel_at"); o.closeAt = (long)life.Dbl("close_at"); o.holdMs = (long)life.Dbl("hold_ms"); }
   CJson *tr = p.Find("tr");
   if(tr != NULL && tr.type == JSON_OBJECT) { o.hasTrail = true; o.trailAct = tr.Dbl("ap") * scale; o.trailOff = tr.Dbl("op") * scale; }

   ulong prior = Existing(sym, g_routes[r].magic, id);
   if(prior > 0)
     {
      // prikaz sa zopakoval po pade pred `Done`: order uz je u brokera - prevziat, neposlat druhy
      o.ticket = prior;
      AddOrder(o);
      Emit(route, "placed", cid, id, "", o.entry, o.ntEntry, o.q, o.lots, 0, "", "prevzaty po restarte");
      return;
     }
   g_trade.SetExpertMagicNumber((ulong)g_routes[r].magic);
   g_trade.SetTypeFillingBySymbol(sym);
   g_trade.SetDeviationInPoints(InpDeviationPts);
   bool isLong = o.dir > 0, ok;
   if(o.ot == "Market")
      ok = isLong ? g_trade.Buy(o.lots, sym, 0, o.sl0, o.tp0, id) : g_trade.Sell(o.lots, sym, 0, o.sl0, o.tp0, id);
   else if(o.ot == "Stop")
      ok = isLong ? g_trade.BuyStop(o.lots, o.entry, sym, o.sl0, o.tp0, ORDER_TIME_GTC, 0, id)
                  : g_trade.SellStop(o.lots, o.entry, sym, o.sl0, o.tp0, ORDER_TIME_GTC, 0, id);
   else
      ok = isLong ? g_trade.BuyLimit(o.lots, o.entry, sym, o.sl0, o.tp0, ORDER_TIME_GTC, 0, id)
                  : g_trade.SellLimit(o.lots, o.entry, sym, o.sl0, o.tp0, ORDER_TIME_GTC, 0, id);
   if(!ok || !Sent())
     { Emit(route, "reject", cid, id, "", o.entry, o.ntEntry, o.q, o.lots, 0, "", "broker: " + TradeErr()); return; }
   o.ticket = g_trade.ResultOrder();
   o.extreme = o.entry;
   AddOrder(o);
   Emit(route, "placed", cid, id, "", o.entry, o.ntEntry, o.q, o.lots, 0, "",
        StringFormat("%s %s SL %s TP %s", o.ot, sym, DoubleToString(o.sl0, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS)),
                     DoubleToString(o.tp0, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS))));
  }

void AddOrder(const XOrder &o)
  {
   int n = ArraySize(g_xo);
   ArrayResize(g_xo, n + 1);
   g_xo[n] = o;
  }

void HandleModify(int r, CJson *c)
  {
   string route = g_routes[r].id, cid = c.Str("cid"), id = c.Str("id");
   int i = FindOrder(route, id);
   if(i < 0 || !g_xo[i].filled) { Emit(route, "ack", cid, id, "", 0, 0, 0, 0, 0, "", "nic na posun"); return; }
   string sym = g_routes[r].symbol;
   bool same = g_routes[r].price == "same";
   double ntFill = NtPrice(g_xo[i], g_xo[i].fill, g_xo[i].entry, g_xo[i].ntEntry);
   CJson *jsl = c.Find("sl");
   CJson *jtp = c.Find("tp");
   double sl = g_xo[i].lastStop, tp = g_xo[i].lastTp;
   // posun od skutocneho fillu: vzdialenost SL od vstupu v cenach mastera ostava
   if(jsl != NULL && jsl.type == JSON_NUMBER)
      sl = same ? RoundTick(sym, jsl.num) : StaticHost::BridgeReanchor(g_xo[i].fill, ntFill, jsl.num, g_routes[r].scale, Tick(sym));
   if(jtp != NULL && jtp.type == JSON_NUMBER)
      tp = same ? RoundTick(sym, jtp.num) : StaticHost::BridgeReanchor(g_xo[i].fill, ntFill, jtp.num, g_routes[r].scale, Tick(sym));
   if(!g_trade.PositionModify(g_xo[i].ticket, sl, tp) || !Sent())
     { Emit(route, "reject", cid, id, "", sl, 0, 0, 0, 0, "", "posun SL/TP: " + TradeErr()); return; }
   g_xo[i].lastStop = sl; g_xo[i].lastTp = tp;
   Emit(route, "modified", cid, id, "", sl, jsl != NULL && jsl.type == JSON_NUMBER ? jsl.num : 0, 0, 0, 0, "", "TP " + Num(tp));
  }

//+------------------------------------------------------------------+
//| Rusenie a zatvaranie                                             |
//+------------------------------------------------------------------+
void CancelEntry(int i, string cid, string why)
  {
   string route = g_xo[i].route, id = g_xo[i].id;
   ulong t = g_xo[i].ticket;
   if(t == 0 || g_trade.OrderDelete(t) || !OrderSelect(t))
     {
      Emit(route, "cancelled", cid, id, "", 0, 0, 0, 0, 0, why, "");
      RemoveOrder(i);
      return;
     }
   if(!g_xo[i].cancelWanted) Note(route, "error", "vstup " + id + " sa neda zrusit: " + TradeErr() + " - skusam znova");
   g_xo[i].cancelWanted = true;
   g_xo[i].cancelWhy = why;
  }

void ClosePosition(int i)
  {
   g_xo[i].closing = true;
   if(!PositionSelectByTicket(g_xo[i].ticket)) return;   // uz zavreta - deal pride v OnTradeTransaction
   int r = FindRoute(g_xo[i].route);
   if(r >= 0) g_trade.SetExpertMagicNumber((ulong)g_routes[r].magic);
   g_trade.SetDeviationInPoints(InpDeviationPts);
   if(g_trade.PositionClose(g_xo[i].ticket) && Sent()) { g_xo[i].closeRetryAt = TimeLocal() + 10; return; }
   g_xo[i].closeFails++;
   int wait = (int)MathMin(60, 1 << (int)MathMin(6, g_xo[i].closeFails));
   g_xo[i].closeRetryAt = TimeLocal() + wait;
   Note(g_xo[i].route, "error", StringFormat("zatvorenie %s odmietnute: %s (%d. neuspech, dalsi pokus o %d s; SL/TP ostavaju)",
                                             g_xo[i].id, TradeErr(), g_xo[i].closeFails, wait));
  }

//+------------------------------------------------------------------+
//| Vyplnenia                                                        |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   ulong order = (ulong)HistoryDealGetInteger(trans.deal, DEAL_ORDER);
   ulong position = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   long magic = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   double vol = HistoryDealGetDouble(trans.deal, DEAL_VOLUME), px = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   long ms = ServerMsToUtc(HistoryDealGetInteger(trans.deal, DEAL_TIME_MSC));
   for(int i = 0; i < ArraySize(g_xo); i++)
     {
      if(entry == DEAL_ENTRY_IN && g_xo[i].ticket == order && !g_xo[i].filled) { OnEntryFill(i, vol, px, ms, position); break; }
      if(entry == DEAL_ENTRY_IN && g_xo[i].ticket == order && g_xo[i].filled) { g_xo[i].openLots += vol; break; }   // ciastocny fill dalsej casti
      if(entry != DEAL_ENTRY_IN && g_xo[i].filled && g_xo[i].ticket == position)
        {
         ENUM_DEAL_REASON why = (ENUM_DEAL_REASON)HistoryDealGetInteger(trans.deal, DEAL_REASON);
         OnExitFill(i, vol, px, ms, why == DEAL_REASON_SL ? "sl" : (why == DEAL_REASON_TP ? "tp" : (g_xo[i].closing ? g_xo[i].closeWhy : "external")));
         break;
        }
     }
   SaveState();
  }

void OnEntryFill(int i, double vol, double px, long ms, ulong position)
  {
   g_xo[i].filled = true;
   g_xo[i].fill = px;
   g_xo[i].fillMs = ms;
   g_xo[i].openLots = vol;
   g_xo[i].extreme = px;
   if(position > 0) g_xo[i].ticket = position;   // hedging: pozicia ma ticket orderu, ktory ju otvoril
   int r = FindRoute(g_xo[i].route);
   string sym = r >= 0 ? g_routes[r].symbol : PositionGetString(POSITION_SYMBOL);
   Emit(g_xo[i].route, "fill", g_xo[i].cid, g_xo[i].id, "in", px, NtPrice(g_xo[i], px, g_xo[i].entry, g_xo[i].ntEntry),
        QtyNt(g_xo[i], vol), vol, ms, "", "");
   // SL/TP od skutocneho fillu (sklz na CFD nezmeni riziko v bodoch)
   if(r < 0 || g_routes[r].price == "same") return;
   double sl = StaticHost::BridgeReanchor(px, g_xo[i].ntEntry, g_xo[i].ntSl, g_routes[r].scale, Tick(sym));
   double tp = StaticHost::BridgeReanchor(px, g_xo[i].ntEntry, g_xo[i].ntTp, g_routes[r].scale, Tick(sym));
   if(MathAbs(sl - g_xo[i].sl0) < Tick(sym) / 2 && MathAbs(tp - g_xo[i].tp0) < Tick(sym) / 2) return;
   g_trade.SetExpertMagicNumber((ulong)g_routes[r].magic);
   if(g_trade.PositionModify(g_xo[i].ticket, sl, tp) && Sent())
     {
      g_xo[i].sl0 = sl; g_xo[i].tp0 = tp; g_xo[i].lastStop = sl; g_xo[i].lastTp = tp;
      Emit(g_xo[i].route, "modified", "", g_xo[i].id, "", sl, g_xo[i].ntSl, 0, 0, 0, "", "SL/TP od fillu, TP " + Num(tp));
     }
   else
      Note(g_xo[i].route, "warn", "prekotvenie SL/TP " + g_xo[i].id + " na fill odmietnute: " + TradeErr() + " - ostavaju z orderu");
  }

void OnExitFill(int i, double vol, double px, long ms, string exitName)
  {
   double ntFill = NtPrice(g_xo[i], g_xo[i].fill, g_xo[i].entry, g_xo[i].ntEntry);
   Emit(g_xo[i].route, "fill", g_xo[i].cid, g_xo[i].id, "out", px, NtPrice(g_xo[i], px, g_xo[i].fill, ntFill),
        QtyNt(g_xo[i], vol), vol, ms, exitName, "");
   g_xo[i].openLots = MathMax(0.0, g_xo[i].openLots - vol);
   if(g_xo[i].openLots <= 1e-9) RemoveOrder(i);
  }

//+------------------------------------------------------------------+
//| Strazcovia (kazdu sekundu)                                        |
//+------------------------------------------------------------------+
void Guards()
  {
   datetime now = TimeLocal();
   long nowMs = NowMs();
   for(int i = ArraySize(g_xo) - 1; i >= 0; i--)
     {
      if(i >= ArraySize(g_xo)) continue;
      // terminy z life (aj ked master bezi - jeho vlastny prikaz pride skor, toto je poistka)
      if(!g_xo[i].closing)
        {
         string act = StaticHost::BridgeLifeAction(g_xo[i].cancelAt, g_xo[i].closeAt, g_xo[i].holdMs, g_xo[i].filled, g_xo[i].fillMs, nowMs);
         if(act == "cancel" && !g_xo[i].filled) { Note(g_xo[i].route, "info", "vstup " + g_xo[i].id + " vyprsal (life)"); CancelEntry(i, "", "life"); continue; }
         if(act == "close" && g_xo[i].filled) { Note(g_xo[i].route, "info", "pozicia " + g_xo[i].id + " - cas zatvorenia (life)"); g_xo[i].closeWhy = "life_close"; ClosePosition(i); continue; }
        }
      if(!g_xo[i].filled)
        {
         if(g_xo[i].cancelWanted) { CancelEntry(i, "", g_xo[i].cancelWhy); continue; }
         // order u brokera zmizol bez dealu (zruseny rucne, expiroval, odmietnuty)
         if(g_xo[i].ticket > 0 && !OrderSelect(g_xo[i].ticket) && !PositionSelectByTicket(g_xo[i].ticket)
            && HistoryOrderSelect(g_xo[i].ticket))
           {
            ENUM_ORDER_STATE st = (ENUM_ORDER_STATE)HistoryOrderGetInteger(g_xo[i].ticket, ORDER_STATE);
            if(st == ORDER_STATE_CANCELED || st == ORDER_STATE_REJECTED || st == ORDER_STATE_EXPIRED)
              {
               Emit(g_xo[i].route, "cancelled", "", g_xo[i].id, "", 0, 0, 0, 0, 0, "broker", "order zruseny mimo exekutora");
               RemoveOrder(i);
              }
           }
         continue;
        }
      if(g_xo[i].closing)
        {
         if(now >= g_xo[i].closeRetryAt) ClosePosition(i);
         continue;
        }
      GuardStop(i, now);
     }
  }

void GuardStop(int i, datetime now)
  {
   if(!PositionSelectByTicket(g_xo[i].ticket)) return;
   bool missing = PositionGetDouble(POSITION_SL) <= 0 && g_xo[i].lastStop > 0;
   if(!missing) { g_xo[i].noStopSince = 0; g_xo[i].slFails = 0; return; }
   if(g_xo[i].noStopSince == 0) { g_xo[i].noStopSince = now; return; }
   if(now - g_xo[i].noStopSince < NoStopGraceSec) return;
   if(g_xo[i].slFails >= MaxExitAttempts)
     {
      Note(g_xo[i].route, "error", "pozicia " + g_xo[i].id + " je bez SL a polozit ho zlyhalo " + IntegerToString(g_xo[i].slFails) + "x - zatvaram trhom");
      g_xo[i].closeWhy = "no_stop";
      ClosePosition(i);
      return;
     }
   g_xo[i].slFails++;
   g_xo[i].noStopSince = now;
   Note(g_xo[i].route, "warn", "pozicia " + g_xo[i].id + " nema SL - pokladam ho znova (pokus " + IntegerToString(g_xo[i].slFails) + ")");
   if(!g_trade.PositionModify(g_xo[i].ticket, g_xo[i].lastStop, g_xo[i].lastTp) || !Sent())
      Note(g_xo[i].route, "error", "SL na pozicii " + g_xo[i].id + " odmietnuty: " + TradeErr());
  }

/// Extrem od vstupu sa sleduje vzdy (na zatvoreni 1m baru symbolu); stop podla neho posuva exekutor len vtedy,
/// ked master neodpoveda - inak trailing robi master na svojich baroch, presne ako v backteste.
void TrailOnMinute()
  {
   for(int r = 0; r < ArraySize(g_routes); r++)
     {
      MqlRates bar[];
      if(CopyRates(g_routes[r].symbol, PERIOD_M1, 1, 1, bar) != 1) continue;
      if(bar[0].time == g_routes[r].lastM1) continue;
      g_routes[r].lastM1 = bar[0].time;
      for(int i = 0; i < ArraySize(g_xo); i++)
        {
         if(g_xo[i].route != g_routes[r].id || !g_xo[i].filled || !g_xo[i].hasTrail || g_xo[i].closing) continue;
         bool isLong = g_xo[i].dir > 0;
         g_xo[i].extreme = isLong ? MathMax(g_xo[i].extreme, bar[0].high) : MathMin(g_xo[i].extreme, bar[0].low);
         if(!g_routes[r].masterLost) continue;
         double stop = StaticHost::BridgeTrailStop(g_xo[i].dir, g_xo[i].fill, g_xo[i].sl0, g_xo[i].extreme, g_xo[i].trailAct, g_xo[i].trailOff);
         stop = RoundTick(g_routes[r].symbol, stop);
         bool better = isLong ? stop > g_xo[i].lastStop : stop < g_xo[i].lastStop;
         if(!better) continue;
         if(g_trade.PositionModify(g_xo[i].ticket, stop, g_xo[i].lastTp) && Sent())
           {
            g_xo[i].lastStop = stop;
            Emit(g_routes[r].id, "modified", "", g_xo[i].id, "", stop, 0, 0, 0, 0, "", "trailing exekutora (master neodpoveda)");
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Zivotny cyklus                                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   if(MQLInfoInteger(MQL_TESTER)) { Print("TradeBot exekutor nebezi v Strategy Testeri"); return INIT_FAILED; }
   g_hedging = AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   RefreshGmtOffset();
   g_id = StaticHost::BridgeExecutorId(AccountInfoInteger(ACCOUNT_LOGIN), AccountInfoString(ACCOUNT_SERVER));
   if(g_id == "") { Print("TradeBot exekutor: TradeBot.dll bez Bridge* - preinstaluj: python -m tradebot.adapters.mt5 install"); return INIT_FAILED; }
   g_root = TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\TradeBot";
   g_x = StaticHost::BridgeExecOpen(g_root, g_id);
   if(g_x < 0) { Print("TradeBot exekutor: ", StaticHost::LastError()); return INIT_FAILED; }
   g_statePath = "TradeBot\\exec\\" + g_id + ".orders.json";
   if(!g_hedging) Print("TradeBot exekutor: ucet je NETTING - route budu odmietnute (podporovany je len hedging)");
   LoadState();
   Reconcile();
   RefreshRoutes();
   WatchMasters();
   WriteHeartbeat();
   EventSetMillisecondTimer(MathMax(10, InpTimerMs));
   Print("TradeBot exekutor ", g_id, ": ", ArraySize(g_routes), " route, ", ArraySize(g_xo), " sledovanych orderov, koren ", g_root);
   return INIT_SUCCEEDED;
  }

void OnTimer()
  {
   PollCommands();
   datetime now = TimeLocal();
   if(now == g_lastSlow) return;
   g_lastSlow = now;
   // raz za sekundu
   RefreshGmtOffset();
   if(now - g_lastRoutes >= 2) { RefreshRoutes(); g_lastRoutes = now; }
   WatchMasters();
   Guards();
   TrailOnMinute();
   WriteHeartbeat();
   SaveState();
  }

void OnTick() {}

void OnDeinit(const int reason)
  {
   EventKillTimer();
   // nic sa nerusi ani nezatvara: ordery a pozicie maju SL/TP u brokera a po starte sa prevezmu (Reconcile)
   SaveState();
   if(g_x > 0) StaticHost::BridgeExecClose(g_x);
   g_x = -1;
  }
