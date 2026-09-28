# MetaTrader 5 nad C# jadrom

Štvrtý hostiteľ toho istého C# jadra (po Freqtrade moste, NinjaTraderi a stdio hostiteľovi).
IBSNet a ORBNet sa pre MT5 **neprepisujú**: `csharp/TradeBot.Core` a `csharp/TradeBot.Strategies`
nepoznajú žiadnu platformu, MT5 dostane preloženú `TradeBot.dll` a Expert Advisor v MQL5 je len
ďalší adaptér okolo nej — presne ako `TradeBotStrategy.cs` v NinjaTraderi.

```
csharp/TradeBot.Core/StaticHost.cs        statická fasáda (globálny namespace): engine pod handle, vstupy/výstupy ako EngineHost
tradebot/adapters/mt5/TradeBotEA.mqh      generický Expert Advisor (bary → engine → JSON → CTrade), export signálov
tradebot/adapters/mt5/TradeBotJson.mqh    minimálny JSON parser (MQL5 JSON nečíta)
tradebot/adapters/mt5/TradeBotDraw.mqh    DrawCommand → objekty grafu (zóny, čiary, popisky, pozadie, update, delete)
deploy/mt5/<Meno>.mq5                     šablóna EA: TRADEBOT_ENGINE_KEY + default profil + include
tradebot/adapters/mt5/TradeBotImport.mq5  skript: Custom symbol z CSV 1m sviečok skladu (UTC)
tradebot/adapters/mt5/presets/*.set       parametre skriptu a EA (tester, kreslenie, živý beh)
deploy/mt5/ini/*.ini                      štartovacie ini terminálu: import symbolu, beh v Strategy Testeri, živý beh bez človeka
tradebot/adapters/mt5/__main__.py         inštalácia do terminálu (DLL, include, šablóny, skript, profily), csv, run, control
tester/tests/test_mt5_static_host.py      fasáda musí dať bar po bare to isté, čo most do Freqtrade
```

## Prečo fasáda

MT5 nie je .NET aplikácia, ale MQL5 od buildu 2400 vie **importovať .NET assembly priamo**
(`#import "TradeBot.dll"`): MetaEditor si sám vygeneruje obal. Obmedzenie (overené sondou
25. 9. 2026): vidí len **verejné statické metódy tried bez namespace** s `int/long/double/bool/
string`, ich poľami a `ref` — trieda v namespace (`TradeBot.Core.X`) nie je vidieť vôbec, inštancie,
štruktúry ani výnimky neprejdú. `EngineHost` je inštančná trieda v namespace, preto má jadro
`StaticHost` v globálnom namespace (jediná taká trieda v jadre), v MQL5 `StaticHost::Metoda(...)`:

| metóda | čo robí |
|---|---|
| `Version()`, `Strategies()` | verzia kontraktu (EA ju overí), kľúče C# stratégií v DLL |
| `Create(key, configJson, instrumentJson, chartTfMinutes)` | engine → handle > 0; `-1` = chyba v `LastError()` |
| `HtfTfMinutes(h)`, `RequiredHistory(h)`, `Info(h)`, `Stats(h)` | čo adaptér potrebuje vedieť o engine |
| `FeedHtf(h, čas, o, h, l, c, v)` | jeden **uzavretý** bar informatívneho TF; okno si engine skladá sám (ako NinjaTrader) |
| `OnBar(h, čas, o, h, l, c, v, positionSize, dailyWinLimit, openOrderIds)` | uzavretý bar grafu → JSON ako `EngineHost.OnBar` |
| `Seed`, `FinalDrawings`, `Destroy` | ako v `EngineHost` |

Časy sú **ms UTC otvorenia baru**, čísla idú ako natívne `double` a JSON von ako `G17` — parita
s Python predlohou sa robí na rovnosť. Výnimka sa cez hranicu nepúšťa: metóda vráti `-1`/`""`
a text je v `LastError()`.

## Adaptér (Expert Advisor)

`TradeBotEA.mqh` je zrkadlo `TradeBotStrategy.cs`:

- **profil** = úplný config JSON z `Common\Files\TradeBot\profiles\<kľúč>\` (`FILE_COMMON`, lebo agent
  Strategy Testera má vlastné prázdne `MQL5\Files`; rovnaký export ako
  pre NinjaTrader), `InstrumentSpec` zo `SymbolInfo` (tick, hodnota ticku za 1 lot, krok a
  minimum objemu; objem = `real_volume`, keď broker dáva, inak `tick_volume`);
- **predhistória**: v `OnInit` sa prehrá `2 × RequiredHistory` uzavretých barov (chart aj HTF
  cez `CopyRates`) bez obchodovania (`ready = 0`), potom každý nový bar v `OnTick`;
- **HTF**: bary informatívneho TF uzavreté najneskôr s otvorením baru grafu idú do `FeedHtf`
  pred ním — engine si okno vyberie podľa času;
- **ordery** cez `CTrade`: limit/stop/market, komentár = id vstupu, magic number; vyplnenie (aj
  market) eviduje až deal v `OnTradeTransaction`; cancel = `OrderDelete`; trailing z
  `TradePlan.Trailing` sa posúva na zatvorení baru a nikdy späť; koniec seansy = flatten.
  **Hedging účet**: každý vstup je vlastná pozícia so SL/TP na nej (ako NinjaTrader
  `UniqueEntries`), close = `PositionClose`. **Netting účet**: pozícia je jedna na symbol, SL/TP
  by boli spoločné, preto sú výstupy vlastné pending ordery opačného smeru (stop = SL, limit =
  TP) s komentárom = id; vyplnenie jedného zruší druhý, trailing = `OrderModify` stopu, close =
  opačný market order `close:<id>`, vstup proti otvorenej pozícii najprv odpíše otvorené vstupy
  opačného smeru (deal OUT/INOUT) a cudzie zavretie (ručné, stop-out) sa odpíše z otvorených
  vstupov v smere pozície;
- **naživo**: odoslaný, ešte nevyplnený market vstup sa ráta ako pozícia a bar, ktorý prišiel
  neskôr než dva TF po svojom zatvorení, sa neobchoduje (viď docs/NINJATRADER.md, „Naživo“);
- **jedna pozícia naraz** (Pine `pyramiding=0`): vstup, ktorý príde počas pozície, sa odloží a
  nepošle sa brokerovi. Po vyplnení vstupu sa ostatné čakajúce vstupy zmažu (`OrderDelete`) a odložia.
  Po konci pozície sa znova pošlú, ak ich engine nezrušil. Rovnako ako NinjaTrader, viď
  docs/NINJATRADER.md, „Jedna pozícia naraz“;
- **denný limit výhier** (Pine `dailyWinsCount`) presne ako NinjaTrader: výhra = obchod zavretý na
  SL/TP so ziskom > 0 voči plánovanému vstupu (hedging podľa `DEAL_REASON_SL/TP`, netting podľa
  komentára výstupného orderu), zavretie enginom sa nepočíta; engine sa pýta na stav z konca
  predošlého baru;
- **kresby**: každý `DrawCommand` z engine-u je objekt grafu s menom `TB_<id>` (box = `OBJ_RECTANGLE`,
  line = `OBJ_TREND`, label = `OBJ_TEXT`, bgcolor = obdĺžnik cez celú výšku); registrom pre `update`
  a `delete` je sám graf. MT5 nemá priehľadnosť objektov, alfa z `#rrggbbaa` sa zmieša s farbou pozadia
  grafu a výplne idú do pozadia (`OBJPROP_BACK`), aby neprekryli sviečky; box s výplňou aj okrajom sú
  dva objekty (`TB_<id>` a `TB_<id>_b`). `FinalDrawings` (Pine `barstate.islast`) sa kreslia naživo na
  každom bare, v testeri na konci behu. Popisok s pozadím (`bg`) = `OBJ_TEXT` + vyplnený obdĺžnik
  `TB_<id>_bg` za ním, veľkosť z pixelov textu prepočítaná na čas a cenu (sedí presne pri mierke,
  v ktorej vznikol). Vstupy `InpShowDrawings`, `InpShowSessionBg`, `InpReplayBars` (koľko barov
  predhistórie prehrať a nakresliť);
- **live telemetria** (docs/LIVE.md): mimo Strategy Testera píše DLL (`StaticHost::SpoolOpen/SpoolBar/
  SpoolFill/SpoolNote/SpoolClose`, priamo na disk, nie cez MQL sandbox) bary, zámery, prechody, kresby
  a vyplnenia do JSONL spoolu `Common\Files\TradeBot\spool\mt5_<login>-<server>_<symbol>_<TF>m_<kľúč>\`;
  agent hubu ho posiela do webapp (karta **Live**). Vstupy `InpTelemetry` (predvolene zapnuté) a
  `InpTelemetryInTester` (predvolene vypnuté — tester spool nepíše, iba na overenie). Fasáda má od toho
  `Version() == 2`: staršiu `TradeBot.dll` EA odmietne pri štarte, stačí `install`. Chyba spoolu EA
  nezhodí — zaloguje sa a obchoduje sa ďalej;
- **ovládanie na diaľku** cez `Common\Files\TradeBot\control\<inštancia>.json` (pauza, flatten, zmena
  profilu bez človeka pri termináli) — sekcia „Ovládanie na diaľku“ nižšie;
- **export signálov** do `Common\Files\TradeBot\logs\*.csv` v tvare NinjaTrader exportu
  (`kind;bar_open_ms;id;a;b;entry;sl;tp;qty;ready;text`), takže porovnanie s Testerom je to isté
  `python -m tester.ninjatrader compare --csv <súbor>`. Riadky `fill` sú vyplnenia z dealov:
  `in`/`out`, cena, objem a čas dealu v ms UTC; v `b` je pri výstupe `sltp` alebo `close`.

**Čas servera.** MT5 dáva časy barov v čase servera brokera, nie UTC, a v Strategy Testeri sa
posun zistiť nedá (`TimeGMT()` tam kopíruje čas servera). Preto je vstup
`InpServerGmtOffsetMin` (GMT+3 s letným časom = 180) — bez neho by seansy engine-u sedeli o
pár hodín vedľa. Živý účet: `TimeTradeServer() - TimeGMT()`.

**Účet.** Hedging účet = každý vstup vlastná pozícia (ako NinjaTrader `UniqueEntries`). Netting
= jedna pozícia na symbol, SL/TP sú spoločné a čiastočné zatváranie ide cez `PositionClosePartial`
— pre stratégie s viac vstupmi naraz (IBS) treba hedging.

### Čo je v kostre a čo ešte nie

Hotové a overené: fasáda (test parity s mostom), preklad oboch EA MetaEditorom (0 chýb),
profil, instrument, predhistória, HTF, JSON parser, tok orderov, trailing, export signálov,
inštalátor, **beh v Strategy Testeri so signálmi zhodnými s Testerom** (nižšie), **kreslenie na
živom grafe** vrátane pozadia popiskov, **denný limit výhier** (profil s `maxDailyWins=1`: 38 dní
s limitom, 0 vstupov po limite v ten deň). Napísané, ale **neoverené**: netting účet — tester berie
režim z účtu a tvoj demo je hedging; na overenie treba netting demo (pri zakladaní účtu typ
„netting“). Neoverené aj: živý graf s tikmi (custom symbol ich nemá), shorty.

## Inštalácia a beh

```
python -m tradebot.adapters.mt5 where            # ktoré terminály (…\MetaQuotes\Terminal\<hash>\MQL5) našiel
python -m tradebot.adapters.mt5 install          # zostaví TradeBot.dll, nakopíruje všetko a preloží EA MetaEditorom (--mt5-dir keď je terminálov viac)
python -m tradebot.adapters.mt5 check            # len preloží nainštalované EA (metaeditor64.exe /compile)
python -m tradebot.adapters.mt5 profiles         # len znova vyexportuje profily
```

`install` spustí `metaeditor64.exe /compile` sám (MetaEditor číta .NET DLL len z `Libraries`
terminálu, preto sa mimo neho prekladať nedá); v termináli
`Tools > Options > Expert Advisors > Allow DLL imports`. EA sa spúšťa na **minútovom** grafe
(M3 pre `multicharts_mnq_3m`), informatívny TF si berie sám. Po zmene v `csharp/` stačí `install`
— DLL je ale zamknutá, kým EA beží, najprv ho z grafu odstráň.

Strategy Tester: model „Every tick based on real ticks“ je fill model MT5, nie Freqtrade ani
NinjaTrader — parita platí na **signály** (export CSV vs. Tester), nie na PnL. MQL5 Cloud
optimalizácia DLL nepustí.

## Beh v Strategy Testeri bez klikania

Terminál sa dá riadiť štartovacím ini (`terminal64.exe /config:<ini>`): sekcia `[StartUp]` spustí
skript, `[Tester]` beh v Strategy Testeri a `ShutdownTerminal=1` terminál po behu vypne. Bežiaci
terminál ini ignoruje, preto ho `run` najprv slušne zavrie. Celý postup pre MNQ (rovnaké bary ako
Tester a NinjaTrader — tie isté 1m sviečky zo skladu, UTC):

```
python -m tradebot.adapters.mt5 csv --from 2026-02-20 --to 2026-09-10      # Files\TradeBot\import\MNQ_1m.csv
python -m tradebot.adapters.mt5 run deploy/mt5/ini/import_mnq.ini           # skript TradeBotImport: Custom symbol MNQ.TB
python -m tradebot.adapters.mt5 run deploy/mt5/ini/tester_ibsnet_mnq.ini    # IBSNet, M3, 1-minute OHLC, 2026-03-01..09-10
python -m tester.ninjatrader compare --csv "%APPDATA%\MetaQuotes\Terminal\Common\Files\TradeBot\logs\<najnovší>.csv" --from 2026-03-01 --to 2026-09-10
```

Custom symbol má tick 0,25, hodnotu ticku 0,5 $ (bod 2 $), objem 1, spread 0, futures režim výpočtu
s maržou 2 500 $ na kontrakt (CFD režim by pýtal celú nominálnu hodnotu a tester hlásil „No money“)
a čas servera = UTC (`InpServerGmtOffsetMin=0` v `IBSNet_TB.set`). Správa testera je `TradeBot_IBSNet.htm` v dátovom
adresári terminálu, export signálov v `Common\Files\TradeBot\logs`. **Strategy Tester bez účtu nebeží**
(„tester not started because the account is not specified"): demo účet si založ raz v termináli
(File > Open an Account), potom už všetko ide z príkazového riadku.

**Stav 25. 9. 2026 (IBSNet, MNQ.TB, M3, 2026-03-01..09-10, demo účet FTMO hedging):** signály sedia
s Testerom úplne — 81/81 vstupov na rovnakom bare s rovnakým plánom, 1975/1975 prechodov stavov zón
(porovnanie bez uidov zón, lebo MT5 prehrá predhistóriu a uidy sú posunuté). Výsledok MT5 (model
„1 minute OHLC“, vklad 1 000 000 $): 76 obchodov, +6 853,50 $, PF 1,91, max. DD 1 859 $ — NinjaTrader
na tom istom období 78 obchodov, +6 974 $, PF 1,87; emulátor MultiCharts 71, +6 150 $, PF 1,86.
Fill model je iný, PnL sa porovnáva len orientačne, parita platí na signály.
**28. 9. 2026** (po „jedna pozícia naraz“, 694bef711): ten istý beh dáva 71 obchodov, +5 999 $, PF 1,83, max. DD
1 859 $ — počet sedí s emulátorom MultiCharts (71); signály stále 81/81 a 1975/1975. EA s control súborom
(bez súboru = `enabled`) dáva v testeri **presne to isté** ako EA pred ním: správa aj riadky `order`/`fill`
exportu sú identické.

Pasce, na ktoré sa prišlo: `CopyRates` s časovým rozsahom vracia aj práve otvorený bar (EA ho bralo
ako uzavretý — teraz sa berú bary podľa indexu od 1); Strategy Tester beží v agentovi s vlastným
prázdnym `MQL5\Files` (profily a export idú cez `FILE_COMMON`); `TimeGMT()` v testeri = čas servera;
názov exportu nesmie stratiť príponu.

## Kreslenie na grafe bez klikania

```
python -m tradebot.adapters.mt5 run deploy/mt5/ini/chart_ibsnet_mnq.ini
```

Položí IBSNet na graf MNQ.TB M3 (preset `IBSNet_chart.set`: 1 500 barov predhistórie, kresby
zapnuté, bez exportu), EA po vykreslení uloží `MQL5\Files\TradeBot\chart_ibsnet.png` a zoznam
objektov `…png.objects.csv` (meno, typ, časy, ceny, farba) a terminál zavrie — tak sa kreslenie overuje
bez klikania. Overené 25. 9. 2026: 293 objektov engine-u (zóny `imb`/`z`, štruktúra BOS/CHoCH, swingy
HH/HL/LL/LH, S/R zhluky s `2x`…`6x`, likvidita, EXPIRED), rovnaké kresby ako Tester a NinjaTrader.
Predhistória nikdy neobchoduje (`ready` je false), na živom grafe so zavretým trhom by ordery padali.

## Ovládanie na diaľku (control súbor)

Fáza 2 z docs/LIVE.md, tá istá cesta ako telemetria, len naopak: hub → agent → súbor na disku platformy →
EA. Sieť do terminálu nejde nikdy; keď agent alebo hub spadne, platí posledný súbor.

```
Common\Files\TradeBot\control\<inštancia>.json      {"mode": "enabled"|"paused"|"flatten", "profile": "<názov alebo cesta>", "updated": <ms UTC>, "by": "<kto>"}
```

`<inštancia>` = adresár spoolu (`mt5_<login>-<server>_<symbol>_<TF>m_<kľúč>`, napr.
`mt5_1514750898-FTMO-Demo_US100.cash_1m_ibsnet`); EA ho má zo spoolu (`StaticHost::SpoolInstance`), a keď je
telemetria vypnutá, spočíta si ho rovnako (`StaticHost::InstanceId`). Ručne / z agenta:

```
python -m tradebot.adapters.mt5 control list                                   # inštancie v spoole + ich control súbory
python -m tradebot.adapters.mt5 control <inštancia> --mode paused              # len režim (profil ostáva)
python -m tradebot.adapters.mt5 control <inštancia> --profile golden_binance_btcusdt_3m   # len profil (režim ostáva)
python -m tradebot.adapters.mt5 control <inštancia> --mode flatten
python -m tradebot.adapters.mt5 control <inštancia>                            # ukáže, čo tam je
python -m tradebot.live tail --instance <inštancia>                            # potvrdenie: udalosti `control` v spoole
```

Zápis je atomický (tmp + rename), EA číta s `FILE_COMMON | FILE_SHARE_*`. Čo EA robí (`TradeBotEA.mqh`,
`CheckControl`/`ApplyControl`):

- **kedy číta**: `OnTimer` každých 5 s (jeden spoločný timer so screenshotom) a po každom novom bare grafu;
  zmena sa spozná podľa `FILE_MODIFY_DATE` + `FILE_SIZE`, čítanie teda nezávisí od tikov — funguje aj so
  zavretým trhom. Pri štarte sa súbor číta ešte pred stavbou engine-u, takže **profil z control súboru má
  prednosť pred `InpProfile`** a EA sa hneď rozbehne v uloženom režime (po reštarte terminálu ostáva to, čo
  hub naposledy zapísal). Chýbajúci súbor = `enabled` + `InpProfile`; keď súbor zmizne počas behu, EA sa
  vráti na `enabled` + `InpProfile` (udalosť `control` so `source:"default"`).
- `enabled` — obchoduje normálne. `paused` — zámery `entry` z engine-u sa brokerovi neposielajú (engine si ich
  odpíše timeoutom, ako pri `ready = false`), odložené vstupy (jedna pozícia naraz) sa po konci pozície už
  nepošlú; `cancel`/`close`, SL/TP a trailing otvorenej pozície bežia ďalej. `flatten` — raz zruší všetky
  čakajúce vstupy a zavrie pozície (`Flatten("tb_flatten")`, netting cez `close:<id>`), potom sa správa ako
  `paused`; každý nový zápis súboru s `flatten` to zopakuje.
- **zmena profilu** (`profile` iný než beží; prázdny = bez zmeny): aplikuje sa, len keď je stratégia bez
  otvoreného objemu a bez čakajúcich vstupov u brokera (`IsFlat`). Vtedy EA zavrie spool (`bye` s dôvodom
  `profile`), zahodí engine, postaví nový z nového profilu (rovnaké pravidlá cesty ako `InpProfile`, relatívne
  k `Common\Files\TradeBot\profiles\<kľúč>\`), vynuluje stav adaptéra (sledované ordery, denný limit výhier,
  počítadlá), zmaže kresby, prehrá predhistóriu a otvorí spool znova (tá istá inštancia, nová session s
  `hello` s novým profilom). Kým nie je flat, zmena čaká (udalosť `control` so `source:"pending"`) a skúša sa
  po každom deale, bare a tiku timera. Profil, ktorý sa nedá načítať, sa zaloguje a beží ďalej starý.
- každá aplikovaná zmena ide do spoolu ako `{"k":"control","mode","profile","source"}` (`source`:
  `control` zo súboru, `default` bez súboru, `pending` čaká na flat) a do Experts logu (`TradeBot control: …`);
  potlačený vstup sa loguje raz na zmenu režimu. Neplatný JSON alebo neznámy režim = log + ostáva posledný
  režim (skúsi sa znova až po ďalšej zmene súboru).
- v **Strategy Testeri sa control súbor nečíta** (beh musí byť deterministický a rovnaký ako doteraz).

**Overené 28. 9. 2026** (FTMO-Demo hedging, `US100.cash` M1, živé tiky v nedeľu večer, `AllowLiveTrading=0`):
`--mode paused` → do 0,1 s udalosť `control paused (control)` a log „rezim paused (control) - nove vstupy sa
neposielaju“; `--mode enabled` späť; `--profile golden_binance_btcusdt_3m` → `stat`, `bye profile`, nový súbor
session s `hello profil=…golden_binance_btcusdt_3m.json`, `control enabled golden_binance_btcusdt_3m (control)`,
log „profil zmeneny na … engine postaveny nanovo, predhistoria prehrana“; `--mode flatten` → `control flatten`
a log „flatten - zrusenych 0 cakajucich vstupov, zatvara sa 0 pozicii“; zmazanie súboru → `control enabled
multicharts_mnq_3m (default)` a návrat na `InpProfile`. Neoverené s reálnou pozíciou (obchodovanie bolo
vypnuté): `flatten` so skutočným zatváraním a `pending` čakanie na flat — kód ide cez tie isté `Flatten`/
`ClosePosition`/`OnTradeTransaction` ako koniec seansy. Pasca: `FILE_MODIFY_DATE` má sekundové rozlíšenie,
preto sa porovnáva aj veľkosť; dva zápisy s rovnakou veľkosťou v tej istej sekunde by sa mohli zliať (ďalší
zápis to napraví).

## Štart bez človeka (ini)

Terminál spustený so štartovacím ini si sám prihlási uložený účet a pripne EA na graf — nikto nemusí
klikať. `deploy/mt5/ini/live_ibsnet_demo.ini` (overené 28. 9. 2026, build 6230):

```
[Experts]
AllowLiveTrading=0        ; 1 = naozaj obchodovať; tu vypnuté, išlo o mechanizmus
AllowDllImport=1
Enabled=1
[StartUp]
Symbol=US100.cash         ; symbol brokera (FTMO: US100.cash; MNQ.TB je custom symbol bez živých tikov)
Period=M1
Expert=TradeBot\IBSNet
ExpertParameters=IBSNet_live.set    ; MQL5\Presets\ — InpTelemetry=true, InpExportSignals=false, InpLogEvents=true, profil, posun servera
```

```
python -m tradebot.adapters.mt5 run deploy/mt5/ini/live_ibsnet_demo.ini --wait 5    # `run` bežiaci terminál zavrie a spustí nový; po --wait sekundách ho nechá bežať
```

Účet: `[Common] Login/Server` v ini netreba, keď je účet v termináli už prihlásený s uloženým heslom
(`config\common.ini`); pri prvom prihlásení na novom stroji patrí do ini `Login=… Server=FTMO-Demo Password=…`
(a heslo z ini potom zmazať). Jeden dátový adresár terminálu = jeden účet; viac účtov = viac portable
terminálov (`/portable`).

Čo sa overilo a čo nie:

- **EA sa pripne sám** z `[StartUp]`: log „13 inputs read from expert 'TradeBot\IBSNet' set file …“,
  „expert IBSNet (US100.cash,M1) loaded successfully“, v spoole nový súbor session s `hello`; keď existuje
  control súbor, EA ho pri štarte prevezme (profil aj režim, `source:"control"`).
- **`[StartUp]` graf sa po reštarte terminálu neobnoví.** Terminál zavretý slušne (`taskkill /IM
  terminal64.exe`, log „shutdown with 0“) a spustený holo (`terminal64.exe` bez `/config`) obnovil len grafy
  uložené v profile `Default` — vrátane EA, ktoré tam predtým človek pripol ručne (IBSNet na EURUSD M5 nabehol:
  „expert IBSNet (EURUSD,M5) loaded successfully“, nová session v spoole) — ale graf z `[StartUp]` sa do
  profilu neuložil a EA na `US100.cash` nenabehlo. Dôsledok: **pre beh bez človeka sa terminál vždy štartuje
  s ini** (autostart / Task Scheduler / agent hubu), nie holo; reštart s tým istým ini EA pripne znova a control
  súbor ho vráti do posledného režimu a profilu. Ak má EA prežiť aj holý štart, treba ho raz pripnúť ručne (alebo
  po štarte z ini v termináli uložiť profil grafov `File > Profiles > Save As`).
- Beh z ini nechá terminál bežať; `run` vráti -1 („terminál stále beží“), to je v poriadku. Zavretie zvonka
  = `taskkill /IM terminal64.exe` (bez `/F` — terminál sa zavrie slušne, EA dostane `OnDeinit`, spool `bye`).
- Chart z `[StartUp]` s `InpTelemetry` posiela bary, kresby a `control` do spoolu; s `AllowLiveTrading=0`
  by vstupy padli na `TRADE_RETCODE_*` — na živé obchodovanie treba `AllowLiveTrading=1` a demo účet.

## Záloha bez .NET importu

Keby import zlyhal (MT5 pod Wine na macu), `TradeBot.Host.exe` už hovorí JSON riadkami cez stdio
(`csharp/TradeBot.Host`) a MQL5 vie otvoriť named pipe (`FileOpen("\\\\.\\pipe\\…")`); adaptér by
posielal tie isté správy ako most v režime `stdio`. Zatiaľ nie je.
