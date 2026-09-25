//+------------------------------------------------------------------+
//| TradeBotImport - vlastny symbol MT5 z 1m sviecok skladu TradeBot                                    |
//|                                                                                                   |
//| Protipol `tester.ninjatrader export`: CSV `cas;o;h;l;c;v` (cas otvorenia baru, UTC, format         |
//| yyyy.mm.dd hh:mm) z MQL5\Files\TradeBot\import\<Meno>_1m.csv sa nahra ako Custom symbol, aby       |
//| Strategy Tester bezal nad tymi istymi barmi ako Tester a NinjaTrader. Cas servera = UTC, takze     |
//| v EA je InpServerGmtOffsetMin = 0.                                                                 |
//|                                                                                                   |
//| Spusta ho instalator cez startovaci ini terminalu ([StartUp] Script=TradeBot\TradeBotImport),     |
//| alebo rucne z Navigatora (Scripts > TradeBot). Po importe terminal zavrie, ked InpCloseTerminal.  |
//+------------------------------------------------------------------+
#property copyright "TradeBot"
#property version   "1.00"
#property script_show_inputs

input string InpSymbol        = "MNQ.TB";                       // Nazov vlastneho symbolu
input string InpCsv           = "TradeBot\\import\\MNQ_1m.csv"; // CSV v MQL5\Files (cas;o;h;l;c;v)
input int    InpDigits        = 2;                              // Desatinne miesta
input double InpTickSize      = 0.25;                           // Velkost ticku
input double InpTickValue     = 0.5;                            // Hodnota ticku za 1 lot v USD (MNQ: 2 $/bod * 0.25)
input double InpContractSize  = 2.0;                            // Velkost kontraktu (hodnota bodu)
input double InpVolumeMin     = 1.0;                            // Min. objem
input double InpVolumeStep    = 1.0;                            // Krok objemu
input double InpMarginInitial = 2500.0;                         // Pociatocna marza za 1 lot v USD (futures rezim; CFD rezim by chcel celu nominalnu hodnotu)
input double InpMarginMaint   = 2300.0;                         // Udrziavacia marza za 1 lot v USD
input bool   InpCloseTerminal = false;                          // Po importe zavriet terminal (davkovy rezim)

bool Prepare()
  {
   if(!SymbolInfoInteger(InpSymbol, SYMBOL_CUSTOM))
     {
      if(!CustomSymbolCreate(InpSymbol, "TradeBot"))
        { Print("TradeBotImport: CustomSymbolCreate ", InpSymbol, " zlyhal: ", GetLastError()); return false; }
     }
   CustomSymbolSetInteger(InpSymbol, SYMBOL_DIGITS, InpDigits);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE, InpTickSize);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE, InpTickValue);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_TRADE_CONTRACT_SIZE, InpContractSize);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_MIN, InpVolumeMin);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_STEP, InpVolumeStep);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_VOLUME_MAX, 1000.0);
   // Futures rezim: zisk = (close - open) / tick * hodnota ticku * loty, marza = loty * InpMarginInitial.
   // CFD rezim by pytal marzu = cela nominalna hodnota (loty * kontrakt * cena) bez paky - "No money" pri 3 lotoch.
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_CALC_MODE, SYMBOL_CALC_MODE_EXCH_FUTURES);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_MARGIN_INITIAL, InpMarginInitial);
   CustomSymbolSetDouble(InpSymbol, SYMBOL_MARGIN_MAINTENANCE, InpMarginMaint);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_MODE, SYMBOL_TRADE_MODE_FULL);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_EXEMODE, SYMBOL_TRADE_EXECUTION_EXCHANGE);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_ORDER_MODE, SYMBOL_ORDER_MARKET | SYMBOL_ORDER_LIMIT | SYMBOL_ORDER_STOP
                          | SYMBOL_ORDER_STOP_LIMIT | SYMBOL_ORDER_SL | SYMBOL_ORDER_TP);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_FILLING_MODE, SYMBOL_FILLING_FOK | SYMBOL_FILLING_IOC);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_STOPS_LEVEL, 0);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_TRADE_FREEZE_LEVEL, 0);
   CustomSymbolSetInteger(InpSymbol, SYMBOL_SPREAD, 0);
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_BASE, "USD");
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_PROFIT, "USD");
   CustomSymbolSetString(InpSymbol, SYMBOL_CURRENCY_MARGIN, "USD");
   CustomSymbolSetString(InpSymbol, SYMBOL_DESCRIPTION, "TradeBot: 1m sviecky zo skladu (UTC)");
   return SymbolSelect(InpSymbol, true);
  }

int ReadCsv(MqlRates &rates[])
  {
   int h = FileOpen(InpCsv, FILE_READ | FILE_CSV | FILE_ANSI, ';');
   if(h == INVALID_HANDLE) { Print("TradeBotImport: CSV sa neda otvorit: MQL5\\Files\\", InpCsv, " (", GetLastError(), ")"); return -1; }
   int n = 0, cap = 0;
   while(!FileIsEnding(h))
     {
      string t = FileReadString(h);
      if(t == "") break;
      MqlRates r;
      r.time = StringToTime(t);
      r.open = StringToDouble(FileReadString(h));
      r.high = StringToDouble(FileReadString(h));
      r.low = StringToDouble(FileReadString(h));
      r.close = StringToDouble(FileReadString(h));
      r.tick_volume = (long)StringToInteger(FileReadString(h));
      r.real_volume = r.tick_volume;
      r.spread = 0;
      if(n >= cap) { cap += 65536; ArrayResize(rates, cap); }
      rates[n++] = r;
     }
   FileClose(h);
   ArrayResize(rates, n);
   return n;
  }

void OnStart()
  {
   if(!Prepare()) return;
   MqlRates rates[];
   int n = ReadCsv(rates);
   if(n <= 0) return;
   int done = CustomRatesReplace(InpSymbol, rates[0].time, rates[n - 1].time, rates);
   Print("TradeBotImport: ", InpSymbol, ": ", n, " barov z CSV, ", done, " zapisanych (",
         TimeToString(rates[0].time, TIME_DATE | TIME_MINUTES), " - ", TimeToString(rates[n - 1].time, TIME_DATE | TIME_MINUTES), " UTC)");
   if(done < 0) Print("TradeBotImport: CustomRatesReplace zlyhal: ", GetLastError());
   if(InpCloseTerminal) TerminalClose(done < 0 ? 1 : 0);
  }
