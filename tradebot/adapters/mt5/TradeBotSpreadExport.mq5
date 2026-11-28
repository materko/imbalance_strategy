//+------------------------------------------------------------------+
//| TradeBotSpreadExport - spread z historie tikov brokera (SMERNICA V2 U3)                            |
//|                                                                                                   |
//| Pre kazdy symbol z InpSymbols prejde historiu tikov po dnoch (CopyTicksRange, bid/ask) a zapise     |
//| do Common\Files\TradeBot\spread\:                                                                  |
//|   <symbol>_ticks.csv  minuta UTC;pocet tikov;spread v bodoch:pocet|spread:pocet|...  (histogram)   |
//|   <symbol>_m1.csv     cas otvorenia M1 UTC;spread sviecky v bodoch (MqlRates.spread)               |
//| Prvy riadok oboch: #symbol=<s>;point=<_Point>;digits=<d>;offset_min=<posun servera teraz>.         |
//| Cas servera sa prevadza na UTC posunom servera (ako EA: zisteny teraz, letny cas podla New Yorku). |
//| Spracuje to `python -m tester.spread history --dir <adresar>` (p50/p75/p95 po oknach New Yorku).  |
//|                                                                                                   |
//| Spusta ho pouzivatel na demo terminali (Navigator > Scripts > TradeBot). Na zivom stroji len so   |
//| suhlasom - skript nic neobchoduje, ale stahovanie tikov terminal na minuty vytazi.                 |
//+------------------------------------------------------------------+
#property copyright "TradeBot"
#property version   "1.00"
#property script_show_inputs

input string   InpSymbols            = "US100.cash,US500.cash,XAUUSD"; // Symboly oddelene ciarkou
input datetime InpFrom               = D'2015.01.01';  // Od (cas servera); co broker nema, preskoci
input datetime InpTo                 = 0;              // Do (cas servera); 0 = teraz
input int      InpServerGmtOffsetMin = 0;              // Posun servera voci UTC v minutach; 0 = zisti sam (TimeTradeServer - TimeGMT)
input bool     InpServerDstNy        = true;           // Server meni letny cas s New Yorkom (FTMO GMT+2/+3)
input bool     InpM1                 = true;           // Zapisat aj spread M1 sviecok

int g_offNow = 0;   // posun servera teraz (s)
int g_nyNow  = 0;   // posun New Yorku teraz (s)

long NthSundayUtc(int year, int mon, int nth, int hourUtc)
  {
   MqlDateTime d; ZeroMemory(d);
   d.year = year; d.mon = mon; d.day = 1;
   datetime first = StructToTime(d);
   MqlDateTime f; TimeToStruct(first, f);
   int day = 1 + (7 - f.day_of_week) % 7 + (nth - 1) * 7;
   return (long)first + (long)(day - 1) * 86400 + (long)hourUtc * 3600;
  }

int NyOffsetSec(long utcSec)
  {
   MqlDateTime d; TimeToStruct((datetime)utcSec, d);
   bool dst = utcSec >= NthSundayUtc(d.year, 3, 2, 7) && utcSec < NthSundayUtc(d.year, 11, 1, 6);
   return dst ? -4 * 3600 : -5 * 3600;
  }

/// Server -> UTC (s): posun teraz, pri InpServerDstNy posunuty o zmenu letneho casu New Yorku od teraz.
long ToUtc(long serverSec)
  {
   long approx = serverSec - g_offNow;
   int off = InpServerDstNy ? g_offNow + NyOffsetSec(approx) - g_nyNow : g_offNow;
   return serverSec - off;
  }

string Minute(long utcSec) { return TimeToString((datetime)utcSec, TIME_DATE | TIME_MINUTES); }

/// Histogram jednej minuty: spread v bodoch -> pocet tikov.
int    g_val[];
int    g_cnt[];
void HistAdd(int v)
  {
   for(int i = 0; i < ArraySize(g_val); i++) if(g_val[i] == v) { g_cnt[i]++; return; }
   int n = ArraySize(g_val);
   ArrayResize(g_val, n + 1); ArrayResize(g_cnt, n + 1);
   g_val[n] = v; g_cnt[n] = 1;
  }

void HistFlush(int h, long minuteUtc)
  {
   int n = ArraySize(g_val);
   if(n == 0) return;
   int total = 0;
   string parts = "";
   for(int i = 0; i < n; i++)
     {
      total += g_cnt[i];
      parts += (i > 0 ? "|" : "") + IntegerToString(g_val[i]) + ":" + IntegerToString(g_cnt[i]);
     }
   FileWriteString(h, Minute(minuteUtc) + ";" + IntegerToString(total) + ";" + parts + "\r\n");
   ArrayResize(g_val, 0); ArrayResize(g_cnt, 0);
  }

string Header(string sym)
  {
   return "#symbol=" + sym + ";point=" + DoubleToString(SymbolInfoDouble(sym, SYMBOL_POINT), 10) + ";digits="
          + IntegerToString((int)SymbolInfoInteger(sym, SYMBOL_DIGITS)) + ";offset_min=" + IntegerToString(g_offNow / 60)
          + ";dst_ny=" + (InpServerDstNy ? "1" : "0") + "\r\n";
  }

int CopyDay(string sym, long fromMs, long toMs, MqlTick &ticks[])
  {
   for(int attempt = 0; attempt < 5; attempt++)
     {
      ResetLastError();
      int n = CopyTicksRange(sym, ticks, COPY_TICKS_INFO, (ulong)fromMs, (ulong)toMs);
      if(n >= 0) return n;
      Sleep(500);   // historia sa este synchronizuje
     }
   return -1;
  }

bool ExportTicks(string sym, long from, long to)
  {
   string path = "TradeBot\\spread\\" + sym + "_ticks.csv";
   int h = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE) { Print("TradeBotSpreadExport: ", path, " sa neda zapisat: ", GetLastError()); return false; }
   FileWriteString(h, Header(sym));
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   long days = 0, total = 0;
   MqlTick ticks[];
   for(long day = from - from % 86400; day < to; day += 86400)
     {
      if(IsStopped()) break;
      int n = CopyDay(sym, day * 1000, (day + 86400) * 1000 - 1, ticks);
      if(n <= 0) continue;
      days++;
      total += n;
      long cur = -1;
      for(int i = 0; i < n; i++)
        {
         if(ticks[i].bid <= 0 || ticks[i].ask <= 0 || ticks[i].ask < ticks[i].bid) continue;
         long utc = ToUtc((long)(ticks[i].time_msc / 1000));
         long minute = utc - utc % 60;
         if(minute != cur) { HistFlush(h, cur); cur = minute; }
         HistAdd((int)MathRound((ticks[i].ask - ticks[i].bid) / point));
        }
      HistFlush(h, cur);
      if(days % 20 == 0) Comment("TradeBotSpreadExport ", sym, ": ", TimeToString((datetime)day, TIME_DATE), ", tikov ", total);
     }
   FileClose(h);
   Print("TradeBotSpreadExport: ", sym, " - ", days, " dni s tikmi, ", total, " tikov -> Common\\Files\\", path);
   return true;
  }

bool ExportM1(string sym, datetime from, datetime to)
  {
   string path = "TradeBot\\spread\\" + sym + "_m1.csv";
   int h = FileOpen(path, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE) { Print("TradeBotSpreadExport: ", path, " sa neda zapisat: ", GetLastError()); return false; }
   FileWriteString(h, Header(sym));
   long bars = 0;
   MqlRates r[];
   for(datetime a = from; a < to; a += 30 * 86400)
     {
      if(IsStopped()) break;
      datetime b = (datetime)MathMin((long)to, (long)a + 30 * 86400) - 1;
      int n = CopyRates(sym, PERIOD_M1, a, b, r);
      for(int i = 0; i < n; i++)
         FileWriteString(h, Minute(ToUtc((long)r[i].time)) + ";" + IntegerToString(r[i].spread) + "\r\n");
      if(n > 0) bars += n;
     }
   FileClose(h);
   Print("TradeBotSpreadExport: ", sym, " - ", bars, " M1 sviecok -> Common\\Files\\", path);
   return true;
  }

void OnStart()
  {
   g_offNow = InpServerGmtOffsetMin != 0 ? InpServerGmtOffsetMin * 60
              : (int)MathRound((double)(TimeTradeServer() - TimeGMT()) / 1800.0) * 1800;
   g_nyNow = NyOffsetSec((long)TimeGMT());
   datetime to = InpTo > 0 ? InpTo : TimeTradeServer();
   string syms[];
   int n = StringSplit(InpSymbols, ',', syms);
   for(int i = 0; i < n && !IsStopped(); i++)
     {
      string s = syms[i];
      StringTrimLeft(s); StringTrimRight(s);
      if(s == "") continue;
      if(!SymbolSelect(s, true)) { Print("TradeBotSpreadExport: symbol ", s, " broker nepozna"); continue; }
      Print("TradeBotSpreadExport: ", s, " od ", TimeToString(InpFrom), " do ", TimeToString(to), ", posun servera ",
            g_offNow / 60, " min", InpServerDstNy ? " (letny cas podla New Yorku)" : "");
      ExportTicks(s, (long)InpFrom, (long)to);
      if(InpM1) ExportM1(s, InpFrom, to);
     }
   Comment("");
  }
