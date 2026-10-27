# Live: telemetria zo spustených stratégií (NinjaTrader 8, MetaTrader 5) do webapp

Fáza 1 — **len čítanie**: bežiaca stratégia s C# jadrom hlási bary, zámery enginu (ordery),
prechody stavov, kresby a vyplnenia u brokera; webapp ich ukazuje na karte **Live**. Ovládanie
(zmena profilu, pauza, nasadenie, účty) je fáza 2 a stavia na tých istých entitách.

## Cesta dát a kde sa čo cache-uje

```
NT8 strategia / MT5 EA ──► TradeBot.Core LiveSpool ──► spool/<instance>/<súbor>.jsonl   (1) disk platformy, flush hneď
                                                              │
      tester.hub agent (na tom istom PC) ── SpoolReader + kurzor ──► Transport.push_events    (2) strážca spoolu 1 s → hneď;
                                                              │       (HTTP POST /api/live/events)  heartbeat 3 s = poistka
                                                     HUB  live.sqlite                        (3) hub
                                                              │
      webapp ── LiveMirror (Transport.pull_export, 2 s) ──► tester/live/mirror.sqlite        (4) webapp, 2 s
                                                              │
      prehliadač ◄── GET /api/live/stream (SSE, push po každom zápise do zrkadla)              (5) stránka, hneď
```

**Oneskorenie bar → stránka ≈ 2–4 s** (súčet: zápis hneď + strážca do 1 s + HTTP + zrkadlo do 2 s
+ push hneď). Predtým to bol heartbeat 10 s + zrkadlo 5 s + polling stránky 5 s, teda do 20 s.
Pokyny opačným smerom (control súbor, fáza 2) idú heartbeatom (3 s) a adaptér súbor číta
každé 2 s → ≈ 3 + 2 s.

Každý uzol smie byť dole a nič sa nestratí:

1. **Platforma** píše len na lokálny disk (append-only JSONL, flush po riadku v realtime). Sieť
   z NT/MT5 nejde nikdy — MQL5 `WebRequest` chce allow-list a v Testeri nefunguje; keď spadne
   agent alebo hub, stratégia obchoduje ďalej a súbory čakajú.
2. **Agent** číta spool od uloženého kurzora (`tester/live/cursor.json`: súbor → offset) a posúva
   ho **až po 200 od hubu**. Hub dole = kurzor stojí, súbory rastú, po návrate sa dopošle všetko.
   Ľahké vlákno agenta každú sekundu pozrie veľkosti súborov spoolu (len `stat`) a keď narástli,
   zobudí odosielanie hneď — bar nečaká na heartbeat (ten ostáva ako poistka).
3. **Hub** ukladá do `tester/hub_data/live.sqlite` idempotentne (`UNIQUE(instance, session, seq)`),
   takže opakované poslanie tej istej dávky nič nezdvojí.
4. **Webapp** si z hubu zrkadlí udalosti do vlastného sqlite (kurzor = rowid hubu) každé 2 s
   (plná stránka = hneď ďalšia). Hub dole = webapp ukazuje, čo má. Keď webapp beží na
   obchodnom PC, číta aj lokálny spool priamo (vlastný kurzor `tester/live/cursor_webapp.json`)
   — funguje aj bez hubu.
   **Diery:** platforma čísluje udalosti behu `seq` od 1 bez medzier, takže chýbajúci kus je
   vidieť (`LiveStore.gaps`; koniec behu sa z čísiel poznať nedá). Zrkadlo raz za minútu
   (`GAP_CHECK_SECONDS`) hľadá diery; tú, ktorá trvá aspoň minútu (`GAP_GRACE_SECONDS` — dávky
   z dvoch súborov spoolu jedného behu môžu prísť v opačnom poradí), dopýta z hubu
   (`Transport.pull_range` → `GET /api/live/range`). Čo ani tak nemá, je v stave zrkadla
   (`gaps`: instance, session, first, last, missing, since, `on_hub` — `true` = hub na dopyt
   nevrátil nič, stratilo sa cestou z platformy; `null` = bez hubu) a karta Live to ukáže
   (varovanie pod stavom, chip „chýbajú dáta“ pri inštancii); doplnené počíta `gaps_refilled`.
5. **Stránka** drží otvorený `EventSource` na `/api/live/stream`; webapp jej po každom zápise do
   zrkadla pošle nové riadky. Bez SSE (starý server, proxy) sa stránka vráti k pollingu 5 s.

Platformy sú za NAT, verejný je len hub → všetko je **pull/push od agenta**, hub nikdy nevolá von.

### Transport

Shipper agenta ani zrkadlo webapp nepoznajú HTTP cesty hubu — hovoria s rozhraním
`tradebot.live.transport.Transport`: `push_events(agent, batches) -> {"accepted": n}` (agent →
hub, idempotentné podľa `(instance, session, seq)`) a `pull_export(after, limit) -> rows` (hub →
zrkadlo). Dnes ho plní `HttpTransport(HubHttp)` nad `/api/live/events` a `/api/live/export`;
`as_transport()` zabalí aj holý HTTP klient (staré volania, falošné HTTP v testoch). Heartbeat
agenta a celý protokol výpočtov (`tester/hub/protocol.py`) sú **mimo** transportu — cez
`Transport` ide len telemetria. Ako by tie isté tri operácie vyzerali cez NATS/JetStream
(subjecty `live.events.<agent>`, durable consumer pre export, dedup podľa `Nats-Msg-Id`), je
v docstringu modulu — len náčrt, žiadna implementácia.

## Identita

- **instance** = adresár spoolu: `<platform>_<account>_<symbol>_<tf>m_<strategy>`, znaky mimo
  `[A-Za-z0-9._-]` nahradené `-` (`ninjatrader_Sim101_MNQ_3m_ibsnet`,
  `mt5_5012345-ICMarkets-Demo_NAS100_3m_orbnet`). Stabilná cez reštarty — jedna inštancia v webapp.
  - NT: `Account.Name`; MT5: `<ACCOUNT_LOGIN>-<ACCOUNT_SERVER>`.
  - Symbol na NT je `Instrument.MasterInstrument.Name` (`MNQ`), nie celý názov `MNQ 12-26` —
    nasadenie nesie celý názov (AddOn ho potrebuje pre `BarsRequest`), do id ide časť pred prvou
    medzerou (`schema.instance_symbol`; hub aj driver). Overené 28. 9. 2026: kým to tak nebolo,
    hub počítal `…_MNQ-12-26_…`, agent písal control súbor pod tým menom, hlásil `ok`, a AddOn
    (spool `…_MNQ_…`) pauzu z webapp nikdy nevidel.
- **session** = 8 hex znakov na jeden štart stratégie (nový engine = nová session). `seq` je
  poradové číslo riadku v rámci session, od 1. Kľúč idempotencie: `(instance, session, seq)`.
- Súbor: `<yyyyMMdd-HHmmss UTC štartu>_<session>.jsonl`; nový súbor aj pri zmene UTC dňa
  (tá istá session, `seq` pokračuje). Agent nikdy nemaže; retencia je vec fázy 2.

## Kde spool leží

| platforma | koreň | ako sa zistí |
|---|---|---|
| NinjaTrader 8 | `Documents\NinjaTrader 8\TradeBot\spool\` | `Globals.UserDataDir` (ako `profiles`, `logs`) |
| MetaTrader 5 | `%APPDATA%\MetaQuotes\Terminal\Common\Files\TradeBot\spool\` | `TERMINAL_COMMONDATA_PATH` (DLL píše priamo, nie cez MQL sandbox) |
| test / iné | čokoľvek | env `TRADEBOT_LIVE_SPOOL` = korene oddelené `os.pathsep` (pridajú sa k predvoleným) |

Telemetria je **zapnutá predvolene** (NT vlastnosť `LiveTelemetry`, MT5 `InpTelemetry`) a
**vypnutá v Strategy Analyzeri / Strategy Testeri** (NT `IsInStrategyAnalyzer`, MT5
`MQL_TESTER`), aby backtesty nezaplavili spool; MT5 má na overenie `InpTelemetryInTester`.
CSV export signálov (`ExportSignals`) ostáva nezmenený — `tester.ninjatrader compare` naň závisí.

## Schéma udalostí (JSONL, `schema: 1`)

Každý riadok: `{"seq": <int>, "t": <ms UTC hodín stroja>, "k": "<druh>", …}`. Časy barov sú
`bt` = čas **otvorenia** baru v ms UTC (ako engine). Čísla dvojitej presnosti idú ako v
`EngineHost` (`G17`), farby a kresby v tvare `DrawCommand.WriteJson` (ten istý ako most do
Freqtrade a graf webapp).

| `k` | polia | kedy |
|---|---|---|
| `hello` | `schema`, `platform` (`ninjatrader`/`mt5`), `account`, `symbol`, `tf` (min), `strategy` (kľúč enginu), `profile` (názov/cesta), `session`, `host` (meno stroja), `tester` (bool), `config` (celý config enginu), `instrument` (InstrumentSpec ako JSON mostu) | prvý riadok každého súboru session (pri rotácii dňa sa zopakuje) |
| `bar` | `bt,o,h,l,c,v`, `ready` (bool — engine smie obchodovať), `mb` (bias), `cs` (bool, koniec seansy, len keď true) | každý uzavretý bar grafu, aj pri prehrávaní predhistórie (`ready:false`) — okrem historických barov, ktoré už zapísal predošlý beh inštancie s tým istým profilom a configom (`LiveSpool.ReadPrevious`: chvost posledných `PreviousFiles` súborov); graf jedného behu potom ukáže bary od reštartu, pohľad naprieč behmi ich má z predošlého |
| `m1` | `bt,o,h,l,c,v` | uzavretý **1m bar symbolu** nezávisle od TF grafu (`LiveSpool.Minute`); po štarte aj predhistória `MinuteBackfill` = 3 dni, ale len minúty za posledným `m1`, ktorý už zapísal predošlý beh inštancie (diera po výpadku sa doplní, duplicity nie — po reštarte 14 inštancií boli `m1` a historické bary ~70 % všetkých udalostí). NT8 stratégia z jemnej série na plnenie (`FillDetailMinutes = 1`), AddOn z vlastného 1m `BarsRequest`, MT5 EA z `CopyRates(PERIOD_M1)` (`StaticHost.SpoolMinute`, fasáda verzie 4). Z nich je sklad živých sviečok `data_live` ([DATA.md §D](DATA.md)) |
| `order` | `bt`, `ready` + polia `OrderIntent.WriteJson` (`a` entry/cancel/close, `id`, `src`, `dir`, `ot`, `r`, `p{dir,e,sl,tp,q,sd,tr}`, pri vstupe voliteľne `life{cancel_at,close_at,hold_ms}` — [ROUTING.md](ROUTING.md)) | zámer enginu, jeden riadok na zámer |
| `order` (`a: "modify"`) | `bt`, `ready`, `a: "modify"`, `id` (id vstupu), `p{sl,tp}` (nová hodnota alebo `null` = nemenené), `r` (`trailing` / iný dôvod) | adaptér (nie engine) posunul SL/TP pracujúceho orderu — každý posun trailingu; SL/TP pri vstupe nesie už plán, ten sa nehlási |
| `event` | `bt` + `StateEvent.WriteJson` (`ts,z,f,to,r`) | prechod stavu zóny |
| `draw` | `bt`, `d`: pole `DrawCommand` (box/line/label/bg/update/delete), `final` (bool, len pre kresby posledného baru) | keď engine za bar niečo nakreslil |
| `fill` | `ft` (čas exekúcie ms UTC), `id` (id vstupu), `side` `in`/`out`, `exit` (meno výstupu: NT `Stop loss`/`Profit target`/`tb_close`/`tb_session_end`, MT5 `sltp`/`close`; pri `in` prázdne), `price`, `qty`, `ready` | vyplnenie u brokera (adaptér, nie engine) |
| `stat` | `stats` (objekt: `Engine.Stats()` + `adapter_*` počítadlá) | pri ukončení |
| `note` | `text`, `level` (`info`/`warn`/`error`) | varovania adaptéra (neskorý bar, chyba spoolu…) |
| `hb` | `bars` (barov v session), `lb` (čas posledného baru, 0 = žiadny), `mode` (posledný `control`, keď bol), `pos` / `pos_px` / `pos_of` (pozícia u brokera — nižšie, keď ju adaptér hlási), `route` (stav MT5 exekútora pri smerovaní orderov — `ok`, `no_executor`, `stale` … [ROUTING.md](ROUTING.md)) | **ping** každých 60 s z časovača `LiveSpool` (mimo Strategy Testera/Analyzera), aj keď bary nechodia; **nečísluje `seq`** (nesie posledné pridelené) |
| `bye` | `reason` | ukončenie stratégie (posledný riadok súboru, keď sa stihne) |

Príklad:

```
{"seq":1,"t":1790000000123,"k":"hello","schema":1,"platform":"mt5","account":"5012345-ICMarkets-Demo","symbol":"NAS100","tf":3,"strategy":"ibsnet","profile":"nas100_dukas_3m","session":"a1b2c3d4","host":"VM-TRADE-01","tester":false,"config":{...},"instrument":{...}}
{"seq":2,"t":1790000000456,"k":"bar","bt":1789999820000,"o":20100.5,"h":20110,"l":20099,"c":20105.25,"v":1234,"ready":true,"mb":1}
{"seq":3,"t":1790000000457,"k":"order","bt":1789999820000,"ready":true,"a":"entry","id":"L-4711","src":4711,"dir":1,"ot":"limit","r":"zone touch","p":{"dir":1,"e":20090,"sl":20070,"tp":20150,"q":1,"sd":20}}
{"seq":4,"t":1790000000458,"k":"draw","bt":1789999820000,"d":[{"t":"box","k":"zone","id":"z4711",...}]}
{"seq":5,"t":1790000063000,"k":"fill","ft":1790000062800,"id":"L-4711","side":"in","exit":"","price":20090,"qty":1,"ready":true}
{"seq":6,"t":1790000180002,"k":"order","bt":1790000000000,"ready":true,"a":"modify","id":"L-4711","p":{"sl":20085,"tp":null},"r":"trailing"}
{"seq":6,"t":1790000240000,"k":"hb","bars":1,"lb":1789999820000,"mode":"enabled"}
```

### Ping (`hb`)

Bez pingu dostáva spool udalosti len pri bare alebo obchode, takže v noci a cez víkend vyzerá každá
inštancia ako „ticho“ a spadnutá či zamrznutá platforma sa od zatvoreného trhu nedá rozlíšiť.
`LiveSpool` preto mimo Testera spustí vlastný `System.Threading.Timer` (`HeartbeatMs`, predvolene
60 000; vlákno z poolu, zápis pod tým istým zámkom ako obchodné vlákno) a píše `hb` — dostanú ho NT8
aj MT5 bez zmeny adaptérov ani MQL5. `hb` sa flushuje hneď (agent ho vidí aj mimo realtime);
`StaticHost.SpoolHeartbeat(h)` ho napíše na požiadanie (MT5 `OnTimer`, testy).

**Prečo `hb` nečísluje `seq`:** 1440 pingov denne na inštanciu by v `events` hubu aj zrkadla len
zavadzalo, a keby mali vlastné čísla, sklad by ich buď musel držať všetky, alebo by v `seq` vznikali
diery, ktoré `LiveStore.gaps` (a dopytovanie z hubu) hlási ako stratené dáta. Ping preto nesie
posledné pridelené `seq` a `LiveStore` z pingov behu drží **jeden riadok** (`seq = 0`, takže `UNIQUE`
aj `gaps` ho nevidia): novší ping ho zmaže a vloží znova s novým `rowid` — zrkadlo ho tak dostane cez
`export` ako každú inú udalosť, starší alebo opakovaný ping nezmení nič. Stav inštancie nesie
`last_hb` a `hb` (telo posledného pingu) a `last_t` sa posúva aj pingom.

**Pozícia u brokera** (`pos`, `pos_px`, `pos_of`): odhad pozície z fillov nevie, čo sa stalo mimo telemetrie (reštart
platformy, ručné zatvorenie, výstup, ktorý nikto nenahlásil — 16. 10. 2026 NT VWAP ORB ukazoval −1 ešte dni po tom,
čo stop u brokera zavrel pozíciu). Adaptér preto volá `LiveSpool.Broker(qty, avgPrice, scope)` (MT5
`StaticHost.SpoolBroker`) so skutočnou pozíciou z platformy: podpísané množstvo (+ long, − short, 0 flat), priemerná
cena a `pos_of` = `account` (NinjaTrader AddOn aj NinjaScript `TradeBotStrategy` — tá každé 2 s z časovača control:
celý účet na inštrumente, aj iné inštancie) alebo `magic` (MT5 EA: len pozície s jeho magic). Ide do každého `hb`, pri zmene sa `hb` napíše hneď (v Testeri nie). Webapp ju na karte Live
ukáže ako „u brokera“ a pri nezhode s odhadom (pri `account` so súčtom odhadov inštancií toho účtu a symbolu) dá ≠.

**Živá / trh zatvorený / ticho** (`tradebot.live.store.liveness`, to isté v `live.js` `liveState`,
v Telegrame `/status`, v nasadeniach `live.state`): inštancia, ktorá pinguje (posledný `hb` nie je
o viac než 3 min starší než posledná udalosť), je živá, kým posledná udalosť nie je staršia než
3 min (`HB_ALIVE_MS`), nezávisle od TF; keď k tomu bar neprišiel dlhšie než 4 bary TF, je to
**trh zatvorený** (platforma beží, trh stojí). Bez pingu, ani udalosti 3 min = **ticho** — platforma
spadla alebo zamrzla. Inštancia bez pingov (starý kód, Tester) sa posudzuje ako predtým: živá, kým
posledná udalosť nie je staršia než 3 bary TF. Nasadenie (`live.state` na hube) berie čerstvejší z dvoch
zdrojov: udalosti, ktoré už do hubu došli, a stav spoolu, ktorý agent hlási v heartbeate (`live.instances`,
koniec posledného súboru na stroji). Po reštarte platformy totiž prehratá história (desiatky tisíc barov,
kresieb a 1m predhistórie na 14 inštancií, ~135 000 udalostí) dobieha do hubu aj 10 min a dovtedy by
nasadenie ukazovalo „ok“, hoci stratégia beží; karta inštancií (zrkadlo webapp) ukáže živú až po dobehnutí.

## C# (`tradebot/core/csharp/TradeBot.Core/Live.cs`)

`TradeBot.Core.LiveSpool` — C# 5, len BCL, **nikdy nevyhodí výnimku do obchodného vlákna**:
každá metóda chytá `Exception`, pri chybe zapíše `LastError`, vypne sa (`Broken = true`) a ďalšie
volania sú no-op. Zápis synchrónny (`StreamWriter`, `AutoFlush` v realtime, inak flush každých
N riadkov a pri zatvorení) — riadok JSON na uzavretý bar je lacný, fronta netreba.

```csharp
public sealed class LiveSpool : IDisposable {
    public const int Schema = 1;
    public static string InstanceId(string platform, string account, string symbol, int tfMinutes, string strategy);
    // hello: platform, account, symbol, tf, strategy, profile, host, tester, config (Dictionary), instrument (InstrumentSpec)
    public LiveSpool(string root, string platform, string account, string symbol, int tfMinutes, string strategy,
                     string profile, bool tester, Dictionary<string, object> config, InstrumentSpec instrument);
    public string Instance { get; }  public string Session { get; }  public string Path { get; }
    public bool Realtime { get; set; }   // flush po každom riadku
    public bool Broken { get; }          public string LastError { get; }
    public void Bar(Bar bar, EngineOutput output, bool ready, int marketBias);   // bar + order* + event* + draw
    public void FinalDrawings(Bar bar, IList<DrawCommand> drawings);            // draw s final:true
    public void Fill(long execMs, string id, bool entry, string exitName, double price, double qty, bool ready);
    public void Modify(long barMs, string id, double? sl, double? tp, string reason, bool ready);  // order a:"modify" (null = nemenené)
    public void Note(string level, string text);
    public void Stats(Dictionary<string, double> stats);
    public void Close(string reason);    // stat sa píše zvlášť pred Close; Close = bye + Dispose
}
```

- `EngineHost` si pamätá `LastBar`, `LastOutput`, `LastBias` z `OnBar` (fasáda pre MT5 ich
  potrebuje na zápis bez opätovného parsovania JSON).
- `StaticHost` (MQL5) dostane: `SpoolOpen(handle, root, platform, account, symbol, profile, tester)`
  → 1/-1 (symbol/tf/strategy/config/instrument pozná zo slotu), `SpoolRealtime(handle, bool)`,
  `SpoolBar(handle, ready)` (posledný bar z `OnBar`), `SpoolFill(handle, execMs, id, entry, exitName,
  price, qty, ready)`, `SpoolModify(handle, barMs, id, sl, tp, reason, ready)` (MQL nemá nullable:
  `sl`/`tp` ≤ 0 = nemenené → `null`), `SpoolNote(handle, level, text)`, `SpoolClose(handle, reason)` (napíše aj
  `stat`), `SpoolPath(handle)`; `Destroy` zavrie spool, ak ostal otvorený. `Version()` → **2**
  (EA kontroluje 2; starú DLL treba preinštalovať).
- NinjaTrader volá `LiveSpool` priamo (`TradeBotStrategy.cs`): otvorí v `DataLoaded` (ak
  `LiveTelemetry && !IsInStrategyAnalyzer`), `Realtime = true` v `State.Realtime`, `Bar` hneď po
  `Export(...)`, `Fill` vedľa `ExportFill`, `Modify(..., "trailing", ...)` v `UpdateTrailing` pri každom
  `SetStopLoss` po vstupe, `Stats` + `Close("terminated")` v `Terminated`.
- MT5 EA (`TradeBotEA.mqh`) zrkadlo: `SpoolOpen` v `OnInit` po `Create` (koreň
  `TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\TradeBot\\spool"`), `SpoolRealtime(true)`
  po `ReplayHistory`, `SpoolBar` hneď po `StaticHost::OnBar`, `SpoolFill` vedľa `ExportFill`,
  `SpoolModify` v `UpdateTrailing` po úspešnom `PositionModify`/`OrderModify`, `SpoolClose` v `OnDeinit`.

## Python (`tradebot/live/`)

| modul | čo |
|---|---|
| `schema.py` | konštanty (`SCHEMA`, druhy), `instance_id(...)` (to isté ako C#), `parse_line`, `validate(event)` |
| `store.py` | `LiveStore(path)` nad sqlite — jeden kód pre hub aj zrkadlo webapp (API nižšie). Zápis (`ingest`) ide jedným spojením pod zámkom, čítanie (`export`, `instances`, `snapshot`, …) vlastným spojením každého vlákna v čítacej transakcii bez zámku (WAL); cache 128 MB, `synchronous=NORMAL` — na NAS-e inak dávka agenta držala zámok sekundy a zrkadlá webapp aj zoznamy na ňu čakali |
| `spool.py` | `default_roots()` (NT + MT5 + env), `SpoolReader(roots, cursor_path)`: `read(max_events)` → `Batch(instance, session, path, events, end_offset)`, `commit(batch)`; neúplný posledný riadok (bez `\n`) sa nečíta |
| `shipper.py` | `LiveShipper(reader, http, agent)`: `pump(max_batches)` → `POST /api/live/events` po 500–2000 udalostí (`BATCH_START` → `BATCH_EVENTS`, podľa odozvy hubu), telo zbalené gzipom (~14× menšie; hub ho rozbalí middlewarom `GzipRequests`, starší hub dostane holé), kurzor posunie len po 200; `status()` (aj `batch`). Agent ho volá vo vlastnom vlákne (`hub-agent-ship`), nie medzi nasadeniami a novým kódom |
| `__main__.py` | `python -m tradebot.live status|tail|ship` na ručné overenie |

`LiveStore`:

```python
LiveStore(path: Path)
.ingest(agent: str, instance: str, session: str, events: list[dict]) -> int   # počet nových (idempotentné)
.instances() -> list[dict]        # id, agent, platform, account, symbol, tf, strategy, profile, host, first_seen, last_seen, last_t, last_bar_ms, last_session, hello
.instance(id) -> dict | None
.sessions(instance) -> list[dict]  # behy, najnovší prvý: session, agent, started, ended, last_t, bars, fills, orders, first_bar_ms, last_bar_ms, profile, reason, live
.events(instance, *, after: int = 0, kinds: list[str] | None = None, limit: int = 1000, session: str | None = None) -> list[dict]   # riadky {"id": rowid, "session", "seq", "event": {...}}
.snapshot(instance, *, bars: int | None = None, session: str | None = None) -> dict    # {"instance", "session", "bars", "orders", "events", "draw", "fills", "stats", "notes"} za posledných N barov (500; so session celý beh do 5000)
.export(after: int = 0, limit: int = 5000) -> list[dict]   # {"id", "agent", "instance", "session", "event"} — pre zrkadlo
.gaps(instance: str | None = None) -> list[dict]          # diery v seq: {"instance", "session", "first", "last", "missing"}
.events_range(instance, session, first, last, limit=5000) -> list[dict]   # seq first..last jedného behu, tvar ako export
.cursor() -> int                   # max rowid
```

Hub (`tester/hub/live.py`, pripája `create_hub_app`), auth ako ostatné (token agenta = jeho meno):

| metóda | cesta | telo / odpoveď |
|---|---|---|
| POST | `/api/live/events` | `{"agent", "batches": [{"instance", "session", "events": [...]}]}` → `{"accepted": n}`; `own(who, agent)` |
| GET | `/api/live/instances` | zoznam |
| GET | `/api/live/instances/{id}` | jedna |
| GET | `/api/live/instances/{id}/sessions` | behy inštancie (`LiveStore.sessions`) |
| GET | `/api/live/instances/{id}/events?after=&kinds=&limit=&session=` | riadky |
| GET | `/api/live/instances/{id}/snapshot?bars=&session=` | snapshot (so `session=` len ten beh) |
| GET | `/api/live/export?after=&limit=` | riadky pre zrkadlo (rovno `json.dumps`; s `Accept-Encoding: gzip` zbalené ~14×) |
| GET | `/api/live/range?instance=&session=&first=&last=&limit=` | seq `first..last` jedného behu — doplnenie diery v zrkadle |
| GET | `/api/live/gaps?instance=` | diery v seq na hube (diagnostika) |

Agent (`tester/hub/agent.py`): v pomalom vlákne (`work()`) je krok `_ship_live` — shipper
vznikne, keď existuje aspoň jeden koreň spoolu. Tretie, ľahké vlákno (`watch_spool`, 1 s) pozerá
veľkosti súborov spoolu a pri raste zobudí pomalé vlákno hneď; heartbeat (predvolene 3 s,
`DEFAULT_HEARTBEAT`; hub pošle svoj interval v odpovedi a agent ho prevezme) ostáva poistkou.
Headless `python -m tester.hub agent` posiela rovnako.

Webapp (`tester/webapp/api/live.py`, `static/js/live.js`, karta **Live**): `LiveMirror` vlákno
(každé 2 s `Transport.pull_export` z hubu + lokálny spool, ak je) → `tester/live/mirror.sqlite`;
každý tik, ktorý niečo uložil, zdvihne `version` zrkadla a zobudí čakajúcich (`wait_for_change`).
`GET /api/live` (inštancie + stav zrkadla + `cursor`), `GET /api/live/{id}/sessions`,
`GET /api/live/{id}/snapshot?bars=&session=` (nesie `cursor` zrkadla pred čítaním),
`GET /api/live/{id}/events?…&session=`, `GET /api/live/{id}/lost` (vstupy bez zatvorenia, ktoré už nebežia), a **`GET /api/live/stream?after=`** — SSE
(`text/event-stream`): hneď `{"type":"instances", instances, mirror, now, deploy, cursor}` a po
každej zmene zrkadla `{"type":"events", instance, rows:[{id, session, seq, event}]}` po inštanciách
+ znova `instances`; bez zmeny každých 15 s komentár (keepalive). Stránka pri otvorení karty
načíta zoznam a snapshot ako doteraz, potom drží `EventSource`: zoznam sa prekreslí z `instances`,
otvorený detail sa **dopĺňa** z `events` (bary podľa `bt`, ordery, kresby, fills, poznámky, stat;
riadky s `id ≤ cursor` snapshotu sa preskočia) a snapshot sa sťahuje znova len pri zmene behu
(nový `hello` v „aktuálnom“ pohľade). Ukončený beh sa nemení. Bez `EventSource` alebo po chybe
streamu ide polling každých 5 s (stream sa skúsi znova o minútu); účty a nasadenia (hub, nie
zrkadlo) sa pri streame obnovujú každých 15 s. `TRADEBOT_LIVE_DIR` presunie `tester/live/`
(zrkadlo, kurzory) inam — druhá webapp na stroji, skúšky proti dočasnému zrkadlu.
Graf: Plotly sviečky z `bar`, kresby cez `objectTraces` z `chart.js`, fills ako značky, posuny SL/TP
(`order` `a:"modify"`) ako malé stupienky a riadky „posun SL/TP“ v tabuľke orderov.

**Behy (sessions).** Každý štart stratégie je nový beh — `session` v `hello` a v každom riadku
spoolu; dáta sa ukladajú po behoch a `LiveStore.sessions(instance)` z nich urobí prehľad (štart =
`t` prvého `hello`, koniec = `t` `bye`, počty barov/fillov/orderov, profil, dôvod ukončenia,
`live` = bez `bye` a `liveness` behu nie je ticho — ping do 3 min, bez pingov udalosť do 3 barov TF). V detaile inštancie je výber **Beh**:
„aktuálny / živý“ = posledných 500 barov naprieč behmi ako doteraz (po reštarte teda vidno
prehratú predhistóriu aj nový beh v jednom okne), pod ním behy od najnovšieho ako
`štart UTC → koniec UTC (bary, fills, profil)`. Vybraný beh načíta `snapshot?session=` — celý beh
(do 5000 barov), tabuľky orderov a fillov aj graf idú len z neho, pod hlavičkou je jeho agent, profil,
stroj a dôvod konca. Ukončený beh sa už neobnovuje; živý beh a „aktuálny“ sa dopĺňajú zo streamu
(pri pollingu každých 5 s). Zrkadlo nič navyše nerobí — nesie všetky behy tak, ako prišli z hubu.

## Fáza 2: ovládanie cez control súbor

Tá istá cesta naopak: hub nesie **požadovaný stav** (deployment), agent ho zapíše ako súbor na disk
platformy a adaptér ho číta. Sieť do NT/MT5 stále nejde; keď agent alebo hub spadne, platí posledný
súbor. Chýbajúci súbor = `enabled` + profil z parametrov stratégie (dnešné správanie).

| platforma | control súbor |
|---|---|
| NinjaTrader 8 | `Documents\NinjaTrader 8\TradeBot\control\<instance>.json` |
| MetaTrader 5 | `Common\Files\TradeBot\control\<instance>.json` (MQL číta cez `FILE_COMMON`) |

```json
{"mode": "enabled" | "paused" | "flatten", "profile": "<názov alebo cesta>", "updated": <ms UTC>, "by": "<kto>"}
```

- `enabled` — obchoduje normálne. `paused` — **nové vstupy sa neposielajú** (zámery `entry` sa zahodia
  a engine to vidí ako zrušené), `cancel`/`close` a SL/TP otvorenej pozície bežia ďalej. `flatten` —
  raz zruší všetky čakajúce vstupy a zavrie pozíciu (`tb_flatten`), potom sa správa ako `paused`.
- **Zmena profilu** (iný `profile` než beží): aplikuje sa, **až keď je stratégia bez pozície a bez
  čakajúcich vstupov** — adaptér zahodí engine, postaví nový z nového profilu a prehrá predhistóriu
  (engine je deterministický, výsledok je ako čerstvý štart; MT5 to v `OnInit` robí aj dnes). Kým nie
  je flat, zmena čaká (`control` udalosť so `source:"pending"`). Vynútenie = najprv `flatten`.
- Adaptér súbor kontroluje podľa mtime **každé 2 s** (MT5 `OnTimer`, NT `System.Timers.Timer` +
  `TriggerCustomEvent`, nech to beží vo vlákne stratégie; AddOn takisto 2 s) a pri každom bare. Každá
  aplikovaná zmena ide do spoolu ako `control` (`mode`, `profile`, `source`: `control`/`default`/`pending`)
  a do logu. Oneskorenie pokynu z webapp ≈ heartbeat agenta (3 s) + tie 2 s.
  TODO: znížiť poll adaptérov na 1–2 s (NT `Timer`, MT5 `EventSetTimer`, AddOn) — C#/MQL, mení sa zvlášť.
- Id inštancie adaptér pozná zo spoolu (`LiveSpool.Instance`, MT5 `StaticHost::SpoolInstance`);
  keď je telemetria vypnutá, spočíta ho `LiveSpool.InstanceId` / `StaticHost::InstanceId`.
- NT8: súbor ručne píše `python -m tradebot.adapters.ninjatrader control <inštancia|list> [--mode] [--profile]`
  (atomicky); čo adaptér `Strategy` pri zmene profilu vie a nevie (bez predhistórie, pevný informatívny TF)
  je v [NINJATRADER.md](NINJATRADER.md), „Ovládanie na diaľku“.

Nasadenie a účty (čo z toho vie platforma bez človeka): MT5 — terminál spustený s ini
(`[StartUp] Expert/Symbol/Period/ExpertParameters`, `[Common] Login/Server[/Password]`) pripne EA
sám, jeden portable terminál = jeden účet, po reštarte sa grafy s EA obnovia. NT8 — `Strategy` sa
programovo zapnúť nedá (ani po reštarte), preto ide živý beh cez **AddOn** (štartuje s NT,
`Connection.Connect` na nakonfigurované pripojenie, `BarsRequest`, `Account.CreateOrder/Submit`);
nové pripojenie z mena a hesla NT API nemá.

## Fáza 2b: účty a nasadenia z webapp (hub = požadovaný stav, agent = zosúladenie)

Hub drží **požadovaný stav** (čo má kde bežať), agent na obchodnom stroji ho **zosúlaďuje** so
skutočnosťou (súbory, terminály) a hlási, čo sa mu podarilo; webapp ukazuje oboje vedľa seba
(deployment vs. inštancia zo spoolu) a rozdiel je drift. Hub ani webapp nepoznajú platformu menom —
o platforme vie len **driver** na strane agenta (`tradebot/live/drivers/<platforma>.py`).

### Entity (hub, `live.sqlite`, modul `tradebot/live/deploy.py` — `DeployStore`)

| entita | polia |
|---|---|
| **account** | prihlásenie do platformy, **bez stroja**: `id` (slug), `platform` (`mt5`/`ninjatrader` — iná sa neprijme), `label`, `login` (MT5 číslo účtu / NT meno účtu, napr. `Sim101`), `server` (MT5 server / NT meno pripojenia), `rev` (verzia prihlásenia — nová pri zmene loginu, servera alebo hesla; driver podľa nej inštanciu reštartuje), `created`, `updated`, `by`; heslo (len MT5) hub drží **šifrované** (`tradebot/live/vault.py`, kľúč `secret.key` vedľa `live.sqlite` alebo `TRADEBOT_HUB_SECRET_KEY`) — v zozname len `secret` (uložené?) a `secret_waiting` (stroje, ktoré aktuálnu verziu ešte neprevzali). Zmazať sa dá len účet bez aktívneho nasadenia; platforma sa nemení, kým má účet nasadenia |
| **deployment** | `id`, `account` (id), `agent` (stroj, na ktorom beží — povinný; starý klient bez neho dostane stroj, na ktorý bol účet kedysi viazaný), `terminal` + `portable` (len MT5: terminál na tom stroji; jeden účet má na stroji jeden spoločný terminál — ďalšie nasadenie musí ísť do toho istého), `own_terminal` (len MT5: nasadenie beží vo vlastnej portable kópii terminálu, `terminal`/`portable` sa mu neukladá a pravidlo spoločného terminálu sa ho netýka — [MT5.md](MT5.md), „Viac stratégií na jednom serveri“), `slot` (len MT5: rozlišovač v id inštancie — tá istá stratégia na účte, symbole a TF s iným profilom; `[A-Za-z0-9-]{1,16}`, prázdny = bez neho), `strategy` (kľúč enginu), `symbol`, `tf` (min), `profile` (názov), `config` (celý config enginu = snímka profilu), `config_hash` (sha256 configu), `mode` (`enabled`/`paused`/`flatten`; **nové nasadenie je predvolene `paused`** — `DEFAULT_MODE`, control súbor s pauzou je na disku skôr, než platforma inštanciu spustí, a obchodovať začne, až keď ho človek zapne; výslovný `mode: enabled` v POST sa rešpektuje), `active` (bool — má inštancia vôbec existovať; `false` = odstrániť z platformy), `created`, `updated`, `by`; odvodené `instance` = `instance_id(platform, <MT5 login>-<server> / NT meno účtu, symbol, tf, strategy, slot)`; `slot` a `own_terminal` sú ako stratégia, symbol a TF identita — `PATCH` ich nemení |
| **route** (v nasadení) | len NinjaTrader: ordery do MT5 exekútora `{via, account, symbol, price, scale, qty}` — [ROUTING.md](ROUTING.md); účet MT5 nesie aliasy symbolov `symbols`, hub agentovi pridá virtuálne nasadenie exekútora (`kind: executor`) |
| **audit** | `ts`, `by`, `action`, `account`/`deployment`, `old`, `new` (JSON) — každá zmena |
| **applied** | čo agent naposledy hlásil k deploymentu: `deployment`, `agent`, `config_hash`, `mode`, `status` (`ok`/`pending`/`error`), `error`, `ts`; `status: ok` s `error` „nenabehla: <dôvod>“ = aplikované, ale inštancia na platforme nenabehla (nižšie) |

### Hub API (mutácie len s hlavným tokenom; čítanie ktokoľvek s tokenom)

`GET/POST /api/live/accounts`, `GET/PATCH/DELETE /api/live/accounts/{id}` (POST/PATCH smie niesť
`password` — uloží sa šifrované; DELETE účtu s aktívnym nasadením je 409 aj s `force`), `GET/POST /api/live/deployments`,
`GET/PATCH/DELETE /api/live/deployments/{id}` (PATCH: `mode`, `profile`+`config`, `active`),
`GET /api/live/audit?limit=`. Odpoveď deploymentu nesie aj `applied` a `instance` (a či inštancia
v spoole žije).

### Heartbeat (rozšírenie, `tester/hub`)

- Agent posiela navyše `live: {"instances": [ {instance, session, last_t, last_bar_ms, mode, profile} ], "applied": [ {deployment, config_hash, mode, status, error} ], "drivers": ["mt5", "ninjatrader"] }`.
- Hub odpovedá navyše `live: {"accounts": [ … účty, ktoré používajú nasadenia tohto agenta, s `terminal`/`portable` z jeho nasadení, `rev` a `secret`, kým aktuálnu verziu hesla nepotvrdil … ], "deployments": [ … len tohto agenta, s `config` … ]}` — vždy celý zoznam (malý), agent si drží posledný a zosúlaďuje pri každom heartbeate; keď agent potvrdí prevzatie hesla (`secret_ack: [account_id]`), hub si zapíše, že tento stroj má verziu, ktorá mu odišla (`secret_sent`). Nové heslo odíde znova každému stroju s nasadením na účte.

### Agent: reconciler a drivery (`tradebot/live/apply.py`, `tradebot/live/drivers/`)

```python
class Driver:                      # jedna trieda na platformu; agent ich načíta podľa toho, čo je na stroji
    platform: str
    def available(self) -> bool                      # je platforma na tomto stroji?
    def store_secret(self, account, password) -> None   # DPAPI (CryptProtectData), tester/live/secrets/<account>.bin
    def ensure_profile(self, deployment) -> Path     # config snímka -> profil na disku platformy (názov = deployment.profile)
    def write_control(self, deployment) -> Path      # control/<instance>.json {mode, profile}
    def ensure_instance(self, account, deployments) -> None   # platforma beží a má všetky aktívne inštancie účtu
    def remove_instance(self, account, deployment) -> None
    def status(self, account) -> dict                # beží proces? ktoré inštancie má?
    def instance_issue(self, account, deployment) -> str | None   # prečo inštancia nenabehla (log platformy); predvolene None
```

`Reconciler.run(desired)` volá driver pre každý účet: heslo → `store_secret`, profily → `ensure_profile`,
control → `write_control`, inštancie → `ensure_instance`/`remove_instance`; výsledok ide do `applied`
v ďalšom heartbeate. Nič nesmie vyhodiť výnimku von (chyba = `status: error` k danému deploymentu).

**Inštancia nenabehla.** Driver súbory zapíše bez chyby, ale platforma inštanciu nespustí (NT: účet nie
je Connected, pripojenie nie je v `ConnectOptions`, inštrument, profil, engine, `BarsRequest`) — to vie
len log platformy na stroji. Po `ensure_instance` sa reconciler ku každému aplikovanému aktívnemu
nasadeniu opýta `Driver.instance_issue` a dôvod pošle v `applied` ako **`status: ok` + `error:
"nenabehla: <dôvod>"`** — stav ostáva `ok` (idempotencia, brána mazania, žiadny drift), takže to prejde
aj cez hub, ktorý o tom nič nevie (ukladá `status` a `error` tak, ako prišli). Reálna chyba nasadenia
(`status: error`) sa dôvodom neprepíše. Zisťuje sa v každom kole a bez nového stavu z hubu aj cez
`Reconciler.refresh()` (krok `_apply_live` agenta, najviac raz za 15 s). NinjaTrader driver číta koniec
(256 kB) najnovšieho `TradeBot\logs\addon_*.txt`: posledný pokus `[<nasadenie>] start …` (AddOn skúša
znova každých 60 s) skončený riadkom zlyhania `LiveInstance.Setup` → jeho text s časom (UTC), pri
pripojení aj s riadkom AddOnu o pripojení; `predhistoria prehrata` → nabehla; pokus, ktorý ešte beží
(čakanie na pripojenie/účet až 2 × 60 s), drží výsledok predošlého. Log staršieho štartu NT sa nečíta.

Poradie okolo control súboru je vec bezpečnosti, lebo adaptéry berú **chýbajúci súbor ako `enabled`**:

- control sa píše **pred** `ensure_instance` (nové nasadenie = `paused` na disku skôr, než platforma
  inštanciu spustí; MT5 driver to pred štartom terminálu ešte skontroluje a chýbajúci dopíše);
- `remove_instance` control **nemaže**, ale prepne na `paused` (`flatten` neprebíja) a odloží; zmaže ho až
  `ensure_instance` — MT5 po zavretí terminálu s tým grafom, NT až v kole, keď inštancia už nebola
  v `deploy.json` (AddOn ju medzitým zastavil);
- rušené nasadenie (deaktivované alebo zmazané), ktorého inštancia má podľa spoolu **otvorenú pozíciu**,
  sa neodoberie: graf ostane v `paused` (alebo `flatten`, keď ho tak človek nastavil), EA pozíciu dovedie
  a odoberie sa až v cykle po jej zatvorení — `apply_state.json` ho drží v `held`, aj keď ho hub zmaže;
- stav agenta (`apply_state.json`) si ku každému nasadeniu pamätá `instance` a cestu control súboru;
  keď sa id inštancie zmení (iný login/server účtu), starý control ide tou istou cestou
  (`remove_instance`), nie ostane ako sirota. MT5 driver má identitu účtu aj v manifeste grafov
  (`charts.json: account`) — iný login = reštart terminálu s novým ini.

- **MT5 driver:** jeden účet = jedna inštancia terminálu (nainštalovaný terminál stroja, daný
  `terminal`, alebo portable kópia v `tester/live/mt5/<account>/terminal/` pri `portable` bez `terminal`);
  ini `[Common] Login/Server[/Password z DPAPI, po prihlásení sa z ini zmaže]`, `[Charts] ProfileLast=tradebot`,
  `[Experts] AllowLiveTrading=1 AllowDllImport=1 Enabled=1`; viac grafov na účte = vygenerovaný
  **profil grafov** terminálu (`MQL5\Profiles\Charts\tradebot\chartNN.chr` + `order.wnd`, UTF-16 s BOM,
  so symbolom, periódou a EA s inputmi; šablóna EA z `deploy/mt5/*.mq5`, magic z id nasadenia). Overené
  28. 9. 2026: terminál profil otvorí cez `ProfileLast` v `/config:` ini (žiadny `/profile:` prepínač ani
  Supervisor EA netreba), profil reštart prežije (terminál si ho pri vypnutí prepíše, driver ho porovnáva
  podľa obsahu, nie textu). Zmena množiny grafov = slušný reštart terminálu; režim, názov profilu aj nové
  parametre pri rovnakom názve idú bez reštartu (control súbor, EA sleduje mtime súboru profilu — driver
  sa na to spolieha len pri `features: ["profile_reload"]` v `installed.json`, staršie EA reštartuje).
  Driver terminál spúšťa a pri páde reštartuje; `install` DLL/EA nerobí (to je nasadenie kódu, fáza 2c).
  Podrobne [MT5.md](MT5.md), „Nasadenie z hubu (driver)“; viac stratégií a účtov na jednom stroji (vlastný
  terminál nasadenia `units/<nasadenie>/`, slot, netting) v „Viac stratégií na jednom serveri“ a prevzatie
  otvorených obchodov EA po reštarte terminálu v „Reštart terminálu s otvorenými obchodmi“.
- **NinjaTrader driver:** zapíše `Documents\NinjaTrader 8\TradeBot\deploy.json`
  `{"instances":[{deployment, connection, account, instrument, tf, strategy, profile}]}` a control
  súbory; beh robí **AddOn** (`TradeBotLiveAddOn`), ktorý pri štarte NT a pri zmene mtime
  `deploy.json` inštancie spustí/zastaví: `Connection.Connect`, `BarsRequest` (história =
  predhistória enginu + živé bary), `Engine.OnBar`, ordery cez `Account.CreateOrder/Submit`,
  SL/TP ako samostatné ordery (OCO), jedna pozícia naraz, trailing, fills z `ExecutionUpdate`,
  spool cez `LiveSpool`, control súbor. NT proces spúšťa driver len ak nebeží (login NT konta musí
  byť zapamätaný — jediný ručný krok).

### Webapp (karta Live)

Sekcie **Účty** (zoznam s prehľadom „kde beží“ — každé nasadenie účtu so strojom, stavom a režimom;
„Pridať účet“ / „upraviť“: platforma a len jej polia — MT5 číslo účtu, server, heslo; NinjaTrader meno
účtu a pripojenie; heslo ide na hub, do zrkadla webapp sa nedostane; úprava prihlásenia účtu, na ktorom
niečo beží, sa pýta, lebo stroje inštancie zastavia a spustia s novým prihlásením; „zmazať“ len keď na
účte nič nebeží) a **Nasadenia** (tabuľka:
účet, stratégia, symbol, TF, profil, režim, stav inštancie zo spoolu, drift `config_hash` vs.
`applied`, posledný bar — pri stave `ok` bez živého spoolu chip upozornenia **„nenabehla: <dôvod>“**
(plný text v title); tlačidlá pauza/zapnúť/flatten, zmena profilu (výber z profilov stratégie
alebo úprava parametrov formulárom z `params.py`), odstrániť; „Nasadiť“: účet, stroj (agenti s driverom
platformy účtu), pri MT5 terminál a portable, stratégia, profil, symbol, TF, režim — predvolene **pauza**, nová stratégia sa zapína až v tabuľke). „Pridať účet“ má
nepovinné **Id účtu** (placeholder ukazuje slug názvu, ktorý by hub spravil sám).

„Nasadiť“ ponúka **len stratégie s C# jadrom** (`StrategySpec.csharp_dir`, v `/api/meta` príznak `csharp`) —
NinjaTrader aj MT5 spúšťajú C# engine; pythonová stratégia sa na live dostane až portom do
`tradebot/strategies/<kľúč>/csharp/`. **Symbol a TF sú nepovinné**: prázdne doplní webapp z profilu
(`tradebot.live.symbols`, `GET /api/live/deploy-defaults` = placeholder formulára) — TF z `_timeframe`,
symbol z `_instrument` pre platformu účtu: najprv symbol, ktorý už na tom účte beží s rovnakým základom,
inak NinjaTrader front-month kvartálneho CME kontraktu (`MNQ 12-26`, roll 8 dní pred tretím piatkom) a
MT5 meno Dukascopy CFD (`NAS100`, `EURUSD`, `XAUUSD`); keď sa nedá (MT5 + futures z Databento, NT MGC), 422
s radou zadať ho ručne. Keď stroj po nasadení nemá na platforme účtu jeho kód (`code_state` ≠ `ok`),
webapp hubu **sama pošle `code_target`** (fáza 2c nižšie) — bez iných aktívnych nasadení na stroji s
`force` (nové je pauznuté a nebežalo), inak cez bránu agenta; odpoveď nesie `code_update`. Commit, ktorý
nie je na GitHube (`gitcode.on_remote`), sa ako cieľ neposiela vôbec (agent by ho ani po `git pull`
nemal) — nasadenie aj „Aktualizovať kód“ to povedia hneď, sekcia Stroje ukáže „nie je na GitHube“.
Mutácie idú cez webapp na hub s **admin tokenom** (`admin_token` v `tester/agent.json`
/ `TRADEBOT_HUB_ADMIN_TOKEN`); bez neho je karta len na čítanie.

## Fáza 2c: nový kód na stroji (hub = cieľový commit, agent = inštalácia a preklad)

Zmena jadra alebo C# enginu sa na obchodný stroj dostane z webapp, nie ručne cez `install` + F5.
Tá istá cesta ako pri nasadeniach: hub nesie **cieľ**, agent ho **vykoná** a hlási, čo urobil; hub
ani webapp nepoznajú platformu — čo znamená „nainštalovať a preložiť“, vie len driver.

### Kto akú verziu má

| kde | čo | odkiaľ |
|---|---|---|
| nasadenie | `version` = commit, na ktorom zadávateľ (webapp) nasadenie vytvoril alebo mu zmenil profil/config; bez neho commit hubu | `POST/PATCH /api/live/deployments` (`version`), `DeployStore.version()` |
| agent | `version` = HEAD klonu agenta (už v heartbeate) | `gitcode.version()` |
| platforma | `installed` = commit, z ktorého bol kód TradeBotu na platformu **nainštalovaný** — marker vedľa kódu, píše ho `install` a číta `Driver.installed_version()` | MT5 `Common\Files\TradeBot\installed.json`, NT `Documents\NinjaTrader 8\TradeBot\installed.json` (`compiled: false` = zdrojáky sú na disku, NT ich ešte nepreložil → nepočíta sa) |

Heartbeat agenta nesie navyše `live.installed = {"mt5": "<sha>", "ninjatrader": "<sha>"|null}` a
`live.code_update` (výsledok poslednej aktualizácie, nižšie). Hub z toho odvodí **`code_state`**
(`tradebot.live.deploy.code_state`): `ok` = platforma má chcený commit (rovnaký sha, alebo chcený je
v histórii nainštalovaného — hub to overí `git merge-base --is-ancestor` vo vlastnom klone, takže
novší kód na stroji je `ok`), `outdated` = iný commit, `unknown` = stroj marker nehlási (kód
nainštalovaný ručne pred fázou 2c). Ukazuje sa **pri nasadení** (`code_state` = jeho `version` proti
platforme účtu) aj **pri agentovi** (`GET /api/agents` → `live.code_state` po platformách proti commitu
hubu, `live.installed`, `live.code_update`, `code_target`).

### Požiadavka a doručenie

`POST /api/live/agents/{name}/update {version?, force?}` (len hlavný token; `?by=` do auditu, riadok
`code_update_request` v audite aj v logu udalostí hubu) uloží agentovi **`code_target`**
`{version, force, requested_by, ts}` — bez `version` je cieľom commit hubu; webapp posiela svoj.
Hub ho posiela v každom heartbeate ako `live.code_target`, **kým agent nehlási `code_update` so
`status: ok` pre tú istú verziu** (potom ho zmaže, udalosť `code_update_done`); `DELETE …/update` ho
stiahne ručne. Cieľ prežije reštart hubu (`state.json`).

### Agent: `tradebot/live/update.py` (`CodeUpdater`), krok `_update_code` pomalého vlákna

1. **Už hotové?** Každý driver hlási `installed_version() == version` a nie je `force` → `ok` bez zásahu
   (`noop`). Preto sa po reštarte agenta uprostred aktualizácie nič nerobí dvakrát a headless agent,
   ktorý sa po pulle reštartoval skôr, než odišiel heartbeat, cieľ potvrdí hneď.
2. **Kód**: `gitcode.has_version` → keď commit chýba, `gitcode.pull()` (to isté, čo pri výpočtoch); keď
   nie je ani potom → `error` („zadávateľ ho musí pushnúť do main“). Kým sa mení kód, agent hlási
   `updating` (hub mu nič nepridelí); keď beží výpočet hubu, aktualizácia čaká (`blocked`, dôvod
   „agent počíta…“). Zmena HEAD = `needs_restart`: headless agent sa reštartuje **až po**
   inštalácii platforiem (`__main__`), webapp to ukáže (chip „reštart“, `/api/hub`).
3. **Brána** (`gate_reasons`), preskočí ju len `force`: každé aktívne nasadenie tohto agenta musí byť
   v režime `paused`/`flatten` (posledný `control` v spoole; keď ho spool nemá, to, čo reconciler
   zapísal do control súboru) **a bez pozície** — fills v spoole, `in` − `out` po id cez všetky
   súbory inštancie (`position_from_spool`). Inštancia bez spoolu = pozícia neznáma = blokované —
   okrem pauznutej, keď koreň spoolu na stroji existuje (inštancia tam nikdy nič nezapísala, teda
   nebežala: nové nasadenie, ktoré na svoju stratégiu v novom kóde len čaká).
   Výsledok `blocked` s `reasons` (webapp: „blokované: <dôvod>“); agent to skúša znova každú minútu
   (chybu každých 5 minút), nový cieľ hneď.
4. **Platformy**: `Driver.install_code(version, účty platformy)` pre každý driver stroja, chyba jedného
   je `error` len preň (`platforms`), druhý ide ďalej. Potom marker `installed.json`.
   - **MT5**: slušne zavrie terminály účtov (aj cudzí z toho istého `exe`) — DLL je zamknutá, kým EA
     beží —, `tradebot.adapters.mt5.install()` v procese agenta (DLL, includy, šablóny, presety,
     profily, preklad MetaEditorom) do dátového adresára každého terminálu účtov (portable kópia, len
     keď už existuje) aj nainštalovaného terminálu stroja; terminály **spustí ďalšie kolo reconcilera**
     (`ensure_instance`: pid nie je → štart s ini, EA prehrá predhistóriu).
   - **NinjaTrader**: `tradebot.adapters.ninjatrader.install()` (zdrojáky do `bin\Custom`) a **preklad bez
     človeka** (`nt_compile`): MSBuild z .NET Frameworku na `NinjaTrader.Custom.csproj` **neprejde** —
     je to SDK-style projekt (`Sdk=Microsoft.NET.Sdk`, C# 13, NuGet; MSB4041) a .NET SDK ani VS na
     stroji nie sú; funguje **F5 do okna NinjaScript Editora** bežiaceho NT cez pywinauto (UIA; overené
     28. 9. 2026: DLL nová a AddOn v novej generácii do 2 s, bežiaca inštancia nabehla znova v novej
     session). NT musí bežať (login je ručný); keď nebeží, zdrojáky sú na disku, marker má
     `compiled: false` a platforma hlási chybu, kým to niekto nepreloží (ďalší pokus pri bežiacom NT).
     Podrobne [NINJATRADER.md](NINJATRADER.md).
5. **Hlásenie**: `live.code_update = {version, status: ok|blocked|error, error, reasons, pulled,
   code_changed, needs_restart, platforms: {<platforma>: {status, error, installed, …}}, ts, noop}` v
   každom ďalšom heartbeate; `live.installed` z markerov.

### Webapp (karta Live)

Sekcia **Stroje**: agent, online/„mení kód“/„reštart“, commit agenta, kód platforiem („kód: aktuálny /
zastaraný <sha7> / neznámy“ proti commitu webapp), posledná aktualizácia („čaká: <sha7>“, „ok“,
„blokované: <dôvod>“, „chyba: …“), tlačidlo **Aktualizovať kód** (len s admin tokenom; potvrdenie
popíše výpadok: MT5 terminály sa zavrú a reštartujú, NT sa prekompiluje a AddOn nabehne v novej
generácii) s voľbou **aj s otvorenými pozíciami** (`force`) a „zrušiť“, keď cieľ ešte visí. Tabuľka
nasadení má stĺpec **kód** (`code_state` nasadenia). Formulár **Nasadiť** upozorní, keď má stroj
vybraného účtu starší (alebo neznámy) kód než webapp — neblokuje.

**Čo potrebuje človeka**: NinjaTrader beží len prihlásený (login s „Remember“ + klik na Log In) — bez
bežiaceho NT sa preklad neurobí; MT5 nič (terminál štartuje driver s ini). Beh agenta bez človeka na
VM (autoštart, služba) je popísaný zvlášť, neskôr.

## Telegram: správy z obchodného stroja a príkazy späť

Cieľ: správa o obchode príde, aj keď je hub alebo webapp dole, a o výpadku sa dozvieš aj vtedy,
keď spadne práve to, čo by ho malo hlásiť. Preto **dve miesta, žiadne v adaptéri NT8/MT5**:

| čo | kde | prečo tam |
|---|---|---|
| obchody, signály, režim, štart/koniec, `note`, chyby nasadení | **agent** (`tradebot.live.telegram`, vlákno `hub-agent-telegram`) | je na tom istom stroji ako platformy a číta ich spool; hub ani webapp nepotrebuje |
| príkazy `/status`, `/pause`, `/resume`, `/flatten`; 🧾 Obchody a 📈 Výkon z denníka obchodov | **agent** | zapíše control súbor — ten istý mechanizmus ako webapp, EA aj NT8 ho čítajú do 2 s; v MQL5 ani C# nič nové |
| „stroj sa neozval“ / „znova sa hlási“ | **hub** (plugin `watchdog`, `tester/hub/plugins`) | spadnutý agent, vypnutý stroj ani výpadok internetu doma zvnútra ohlásiť nejde |

Adaptér by nepridal nič, čo tieto dve miesta nepokryjú, a porušil by pravidlo „platforma nechodí na
sieť“ (MT5 `WebRequest` je blokujúci, chce allow-list v každom termináli, v Testeri nejde; v NT8 by
HTTP bežalo vo vlákne stratégie) — a `getUpdates` smie na jednom bote volať **len jeden proces**
(inak 409), takže príkazy v šiestich inštanciách by nešli vôbec.

| výpadok | agent | hub |
|---|---|---|
| hub / VPS | ✅ správy aj príkazy idú ďalej | — |
| webapp | ✅ | ✅ |
| agent | ⏸ správy sa dopošlú po reštarte (kurzor) | ✅ „stroj sa neozval“ |
| terminál MT5 / NT8 | ✅ `bye`, chyba nasadenia („nenabehla…“) z reconcilera | ✅ |
| celý stroj, internet doma | ❌ | ✅ |

Nepokryté: NT8/MT5 zamrznuté bez pádu (proces žije, bary nechodia) — tiché inštancie sa zatiaľ
nehlásia, lebo zatvorený trh vyzerá rovnako; hlásilo by to každý deň pri dennej prestávke.

### Nastavenie

1. Bot u [@BotFather](https://t.me/BotFather) (`/newbot`) → token. Napíš botovi čokoľvek a id chatu
   nájdeš v `https://api.telegram.org/bot<token>/getUpdates` (`message.chat.id`; skupina má záporné id).
2. Na obchodnom stroji `tester/live/telegram.json` (gitignored, `TELEGRAM_CONFIG`):

   ```json
   {"token": "123456:ABC…", "chats": [123456789], "admins": [123456789],
    "commands": true, "signals": false, "notes": "warn", "capital": {"FTMO": 100000, "*": 50000}}
   ```

   `chats` — kam idú správy a odkiaľ sa berú príkazy; `admins` — id používateľov (`message.from.id`),
   ktorí smú ovládať — pauza, spustenie, flatten (prázdne = ovládať sa dá len v súkromnom chate s botom, v skupine
   nikto; čítať stav smie každý z `chats`). `/pause N` berie číslo z posledného zobrazeného /status; `signals` — aj zámery vstupu, nielen vyplnenia;
   `notes` — najnižšia úroveň `note` (`info`/`warn`/`error`/`off`); `capital` — kapitál účtu pre percentá
   v 📈 Výkon (číslo = každý účet, alebo účet či časť jeho mena → číslo, `*` predvolené; viac účtov sa sčíta,
   bez neho sa % neukážu); `label` — predpona správ
   (predvolene meno agenta). Env `TRADEBOT_TELEGRAM_TOKEN` a `TRADEBOT_TELEGRAM_CHATS` súbor prebijú.
   Agent config preverí raz za minútu — reštart netreba.
3. Na hube `tester/hub_data/telegram.json` (`HUB_TELEGRAM_CONFIG`, vedľa stavu hubu) v tom istom tvare;
   `commands` sa ignoruje (hub len posiela). Ten istý bot je v poriadku — posielať smie viac procesov,
   prijímať len jeden. Posielajú cez neho pluginy hubu (docs/HUB.md, „Pluginy“: strážca, kalendár
   ForexFactory); config sa načíta znova pri zmene súboru.

Príkazy prijíma **jediný agent na bot**: keď ich zapneš na dvoch strojoch s tým istým tokenom, druhý
dostane 409, príkazy si vypne (`commands_error` v stave) a správy posiela ďalej. Pre viac obchodných
strojov buď `commands: false` všade okrem jedného, alebo bot na stroj.

### Správy (agent)

`LiveNotifier` číta spool **vlastným kurzorom** (`TELEGRAM_CURSOR`, nezávisle od shippera na hub) a
posúva ho až po odoslaní; čo už odišlo, si pamätá podľa `(instance, session, seq)` (`TELEGRAM_STATE`),
takže výpadok Telegramu uprostred dávky nič nezdvojí. **Prvý štart** (bez stavu) prehrá históriu bez
odosielania — pozná zámery vstupov a otvorené pozície, ale nespamuje starými obchodmi.

Správy sú HTML, meno inštancie je krátke (**US100** vwaporbnet · MT5 · 1514925336-FTMO-Demo — symbol po prvú bodku či medzeru, inak by
Telegram z `US100.cash` urobil odkaz; za platformou účet z `hello`, lebo tá istá stratégia beží na viacerých
účtoch; TF je v 📊 Stav).

| udalosť | správa |
|---|---|
| `fill` `in` | `🟢 VSTUP SHORT × 0.14 @ 29152.03` / `US100 vwaporbnet · MT5 · 1514925336-FTMO-Demo · SL … · TP …` — SL/TP zo zámeru vstupu |
| `fill` `out` | `✅/❌ VÝSTUP SHORT × 0.14 @ 28802.33 · +48.96 $ (+349.70 b)` / `US100 vwaporbnet · MT5 · 1514925336-FTMO-Demo (sltp)` — P&L z priemernej ceny vstupu a `instrument.point_value` z `hello` |
| `order` `entry` (`ready`, len so `signals`) | `📍 Signál SHORT Market @ … × …` / `… · SL … · TP …` |
| `note` od úrovne `notes` | `⚠️ US100 vwaporbnet · MT5 · 1514925336-FTMO-Demo` / text (escapovaný) |
| `hello`, `bye`, `control` (zmena režimu) | **súhrn**: `🔄 Reštart · MT5 · US100: ibsentrynet, vwapadxnet, vwaporbnet`, `▶️ Spustené …`, `⏹ Zastavené … (dôvod)`, `⏸ Pauza …`, `▶️ Obchoduje …`, `⛔ Flatten …` |
| chyba nasadenia z reconcilera (`applied.error`, raz za 30 s) | `⚠️ Nenabehli: ibsentrynet MNQ NT8, vwapadxnet MNQ NT8, …` / *príčina* — zoskupené podľa príčiny; po náprave `✅ Znova v poriadku: …` |

Obchody a varovania jedného kola idú v jednej správe (odsek na udalosť). Kolo číta spool po 2000 udalostí
znova a znova, kým je čo, najviac 2 s (`PUMP_EVENTS`, `PUMP_SECONDS`) — po reštarte platforiem prehratá
história (~135 000 udalostí na 14 inštancií) inak dobiehala po 500 každé 3 s štvrť hodiny a štarty
jednotlivých inštancií prišli v niekoľkých súhrnoch. Štart, koniec a režim sa zbierajú
v stave (`life`) a odídu súhrnom, keď 30 s nič nepribudlo (`LIFE_QUIET`, najneskôr po 3 min) — reštart
terminálu s tromi EA je tak jeden riadok, nie deväť správ. Reštart = koniec a znova štart v jednej
zbierke; režim sa hlási len pri zmene (EA ho potvrdzuje pri každom štarte). Kto to spôsobil, stojí pri
stratégii (`vwaporbnet (👤 rasto)`): agent si z požadovaného stavu pamätá `by` zmeneného nasadenia
(nové `updated`) a `requested_by` nového kódu na stroj (všetky aktívne inštancie stroja) a štart či stop
do 15 min potom (`ACTOR_TTL`) mu pripíše; pád bez zmeny z hubu meno nemá. Chyba nasadenia sa porovnáva
a ukazuje bez `nenabehla:`, detailu za „ — “, „skúsim znova“ a času pokusu. Beh v Strategy Testeri /
Analyzeri (`hello.tester`) a udalosti predhistórie (`ready: false`) sa nehlásia.

### Príkazy (agent)

Ovláda sa **gombíkmi**, nič netreba písať: `/start` (raz) pridá stálu klávesnicu — 📊 Stav, 📋 Ordery,
🧾 Obchody, 📈 Výkon, pohľady pluginov hubu (📅 Udalosti …) a ❓ Pomoc — a agent pri štarte nastaví menu „/“
(`setMyCommands`). Správy so stavom sú HTML a ťuknutie ich prepíše na mieste
(`editMessageText`), takže chat nezahltia.

- **📊 Stav** (`/status`) — stratégie po platformách a účtoch: režim (▶/⏸/⛔), 🟢 živá (ping alebo udalosť nedávno) /
  🌙 trh zatvorený (pinguje, bary nechodia) / ⚪ ticho N (platforma spadla či zamrzla) / ⏹ skončila, vek baru, pozícia a počet čakajúcich vstupov; gombík na každú stratégiu, **Pauza
  všetkým**, **Spustiť všetky**, Obnoviť, Ordery. Inštancia bez udalosti 7 dní (`STALE_DAYS`) sa neukazuje.
- **ponuka stratégie** — profil, režim, posledný bar, pozície (cena, SL/TP aj po posune trailingu, nerealizovaný
  zisk z close posledného baru) a čakajúce vstupy; **Pauza**, **Spustiť**, **Flatten…** (otázka s **Áno, zavrieť**,
  platí 2 minúty).
- **⏱ Auto-obnova** (gombík v stave) — tá istá správa sa prepisuje každú minútu (`AUTO_SECONDS`) a je pripnutá
  hore v chate; **⏹ Vypnúť auto** ju zastaví a odopne. V chate je najviac jedna (nová vypne starú), ťuknutie
  na stratégiu či Ordery v tej správe ju vypne (inak by obnova prepísala ponuku späť), zmazaná správa vypadne sama.
  Zoznam je v `TELEGRAM_STATE.auto`, prežije reštart agenta.
- **📋 Ordery** (`/orders`) — otvorené pozície a čakajúce vstupy všetkých stratégií. Je to odhad zo spoolu
  (`entry` → kým nepríde `fill`/`cancel`, `fill in − out`); pozícia prežije nový beh tej istej inštancie
  (reštart terminálu, prekompilovanie NT), zámery nie.
- **🧾 Obchody** (`/trades`) — posledných 15 orderov z denníka: `✅/❌` uzavretý s P&L ($ a cena vstup → výstup,
  dôvod výstupu), `🟢` otvorený, `⏳` čakajúci vstup, `🚫` zrušený (s dôvodom, napr. `expired`); gombík na
  každú stratégiu a Všetky.
- **📈 Výkon** (`/perf`) — tie isté čísla ako súhrn behu v Testeri: obchody, ✅ výhry / ❌ prehry / ⚪ remízy,
  winrate, P&L $ a % (s `capital`), profit factor, max drawdown $ a %, najdlhšia séria výhier a prehier,
  priemerná výhra / prehra, najlepší / najhorší, kapitál začiatok → koniec, výstupy; pri všetkých stratégiách
  aj riadok na každú. Gombíky Dnes / 7 dní / 30 dní / Všetko, stratégie, **🖼 Graf** (equity krivka po obchodoch
  ako obrázok, `sendPhoto`; Pillow) a 🧾 Obchody. P&L je **hrubý** — spool poplatky nenesie.
- **📅 Udalosti** a ďalšie pohľady **pluginov hubu** (docs/HUB.md, „Pluginy“) — agent si ich zoznam pýta
  z `GET /api/plugins/views` (raz za 5 min, hub dole = posledný známy), text z `GET /api/plugins/<p>/views/<v>`;
  gombík pod ním obnoví. `/hub` ukáže všetky. Bez hubu povie „hub nedostupný“ — zvyšok Telegramu ide ďalej.
- Textom ostáva `/pause <č|časť mena|all>`, `/resume <…>`, `/flatten <…>` — zapíše control súbor
  (`by: telegram:<user id>`).

Gombíky nesú v `callback_data` krátky kľúč inštancie (`ikey` = crc32 id, Telegram drží do 64 bajtov):
`s` stav, `o` ordery, `m:<k>` ponuka, `P:`/`R:<k|*>` pauza / spustenie, `F:<k|*>` otázka, `X:<čas>:<k|*>` flatten,
`tr:<k|*>` obchody, `pf:<obdobie>:<k|*>` výkon, `gr:<obdobie>:<k|*>` graf (obdobie `d`/`7`/`30`/`a`), `h` pohľady
hubu, `v:<plugin>:<pohľad>` jeden pohľad.

### Denník obchodov (agent)

`tradebot.live.journal`: vlastný kurzor do spoolu (`LIVE_JOURNAL_CURSOR`, nezávislý od shippera aj od správ),
raz za 10 s v tom istom vlákne ako Telegram. Udalosti prejdú tým istým `format_event` ako správy (kontext
inštancie, priemerná cena vstupu, P&L výstupu), len namiesto správy vznikne záznam do `LIVE_JOURNAL`
(`tester/live/journal.jsonl`, len pribúda): `entry` (zámer, len `ready` — predhistória nie), `cancel` (zrušený
čakajúci vstup), `in`, `out` (`pts`, `usd`, `exit`, `left` = zvyšok pozície). **Prvý štart prejde celý spool**,
takže v denníku sú aj staré obchody. Čo už je zapísané, drží `LIVE_JOURNAL_STATE` (`instance|session → seq`);
pád medzi zápisom a stavom zdvojí riadok v súbore, čítanie ho dá raz. Beh v Testeri sa nezapisuje.
Obchod pre výkon = jedno id vstupu (čiastočné výstupy sa sčítajú), uzavretý posledným výstupom
(`tradebot.live.perf`); prehľady pre Telegram skladá `tradebot.live.reports`.

Proti záplave: všetky riadky jedného kola (reštart troch stratégií = 3× `bye` + 3× `hello`) idú v jednej
správe a chyba nasadenia sa porovnáva bez času pokusu na konci (`(23:09:44 UTC)` — AddOn ho mení pri
každom pokuse, inak by každých 30 s odišla nová správa za každú stratégiu).

Prepnutie je **prekrytie** požadovaného stavu, kým ho hub neprevezme: agent ho drží v
`TELEGRAM_STATE.overrides`, posiela v heartbeate (`live.overrides: [{instance, mode, by, ts}]`)
a reconcilerovi podstrčí nasadenie s prepnutým `mode` (`HubAgent._with_overrides`) — bez toho by
najbližšia zmena nasadenia na hube vrátila starý režim. Hub (`DeployStore.apply_overrides`) zapíše
`mode` do aktívneho nasadenia toho agenta s tou inštanciou (audit `by` = `telegram:<id>@<agent>`),
**ak ho od `ts` sám nezmenil** — novšia zmena z webapp vyhráva. Prekrytie padá, keď hub má ten istý
režim alebo nasadenie zmenil neskôr (`updated ≥ ts`). Bez hubu ostáva a control súbor platí.

### Strážca (hub)

Plugin hubu `watchdog` (docs/HUB.md, „Pluginy“). Raz za 20 s pozrie stroje s aktívnym nasadením (`DeployStore.active_agents`): ticho dlhšie než
`agent_timeout` + 2 min (`OFFLINE_GRACE`) = `🔴 stroj nas-win11 sa neozval N min — nasadenia na ňom bežia
ďalej, ale bez dohľadu a bez príkazov z webapp`, návrat = `🟢 stroj … sa znova hlási`. Prvé 2–3 minúty
po štarte hubu mlčí (agenti sa ešte neohlásili). Stráží aj ostatné pluginy: `⚠️ plugin … : nenačítal
sa / padá N min / visí N min / <problém, ktorý plugin sám hlási>` a `🟢 plugin … je znova v poriadku`.
Čo naposledy hlásil, si pamätá v `hub_data/plugins/watchdog/state.json` (prvý štart prevezme starý
`HUB_TELEGRAM_STATE`).

## Testy

- `tester/tests/test_live_telegram.py` — formát (vstup, výstup s P&L, filtre `note`/`control`), notifier
  (prvý štart prehrá históriu bez správ, výpadok Telegramu = kurzor stojí a nič sa nezdvojí, rotácia dňa,
  Tester sa nehlási), chyby nasadení, príkazy (cudzí chat/používateľ, `/pause` + prekrytie, `/flatten`
  len s potvrdením a do 2 min, 409), 429 a odstup správ, config/env, prekrytie v agentovi, prevzatie
  na hube; strážca je v `tester/tests/test_hub_plugins.py`.
- `tester/tests/test_live_journal.py` — záznamy z `format_event` (aj čiastočné výstupy), denník prejde históriu
  raz a Tester vynechá, nič nezdvojí, výkon ako v Testeri a kapitál po účtoch, 🧾/📈/🖼 (PNG), klávesnica
  s pohľadmi hubu a hub dole, `sendPhoto` multipart, `capital` v configu, `GET /api/plugins/views`.

- `tester/tests/test_live_update.py` — `CodeUpdater`: brána (obchoduje / pozícia / bez spoolu), `force`,
  pull len keď commit chýba a chyba, keď nepríde, chyby po platformách oddelene, markery, `noop`;
  agent: cieľ z heartbeatu → `live.installed` + `live.code_update`, hotový cieľ sa neopakuje, blokovaný
  o minútu, počas výpočtu hubu čaká, po zmene HEAD `needs_restart`.
- `tester/tests/test_hub.py` — `code_target` len správca, doručuje sa do `ok`, `code_state` nasadenia
  aj agenta (aj cez `is_ancestor`), audit a log, prežije reštart, zrušenie.
- `tester/tests/test_webapp_live.py` — proxy „Aktualizovať kód“ len s admin tokenom, cieľ = commit
  webapp, nasadenie nesie `version`.
- `tester/tests/test_ninjatrader_tools.py` — marker (`compiled: false` sa nepočíta), MSBuild na SDK
  projekte hlási neúspech (skip bez MSBuild), poradie MSBuild → editor, driver bez bežiaceho NT.
- `tester/tests/test_live_drivers_ninjatrader.py` — `instance_issue` z addon logu: dôvody `Setup`, detail
  pripojenia, pokus v behu drží predošlý dôvod, `predhistoria prehrata` = nabehla, len najnovší log a jeho koniec.
- `tester/tests/test_live_apply.py` — „nenabehla“: `ok` + `error`, idempotencia drží, `refresh()` s intervalom
  a uložením, `status: error` sa neprepíše; cez hub (`DeployStore`) end-to-end.
- `tester/tests/test_webapp_live.py` — `applied.error` „nenabehla: …“ prejde proxy, `ldIssueChip` v stave.
- `tester/tests/test_live_drivers_mt5.py` — `install_code` zavrie terminály, inštaluje raz na dátový
  adresár, marker, ďalšie kolo terminál spustí.
- `tester/tests/test_live_store.py` — store: idempotencia, snapshot, export/kurzor.
- `tester/tests/test_live_spool.py` — reader: kurzor, neúplný riadok, rotácia, viac inštancií;
  shipper proti falošnému `Transport` aj starému falošnému HTTP (výpadok = kurzor stojí, po
  návrate nič dvakrát).
- `tester/tests/test_webapp_live.py` — zrkadlo cez `Transport` a poslucháč verzie; SSE
  (`sse_event`, `stream_messages`, `/api/live/stream` volaný priamo ako ASGI — `TestClient`
  odpoveď vždy dočíta celú, stream by nikdy neskončil).
- `tester/tests/test_hub.py` — `/api/live/*` cez TestClient, práva tokenov; agent preberá
  `heartbeat_seconds` hubu a strážca spoolu zobudí odosielanie.
- `tester/tests/test_mt5_static_host.py` — `Spool*` cez reflexiu: súbor vznikne, `hello`+`bar`+`fill`
  +`order/modify` sú platné podľa `schema.validate`, `Version() == 5`, slot v id inštancie (`InstanceIdSlot`, `SpoolOpenSlot`),
  1m bary `SpoolMinute` (`m1`), EOD podľa hodín (`EodDue`), obnova rozbitého spoolu po `ReopenSeconds`.
- `tester/tests/test_livedata.py` — export skladu do `data/live` (1m aj bary grafu, behy z Testera von, nič sa
  neprepíše), čítanie git + hub, `sync_hub`, plugin hubu `livedata` (ponuka mimo gitu, mesačný push do
  lokálneho bare repa), súbory pluginu cez API, poradie zdrojov sviečok okolo hranice, párovanie, API webapp.
- `python -m tradebot.adapters.ninjatrader check` a `python -m tradebot.adapters.mt5 check` prekladajú.
