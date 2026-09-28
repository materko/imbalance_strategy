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
každých 5 s → ≈ 3 + 5 s.

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
| `bar` | `bt,o,h,l,c,v`, `ready` (bool — engine smie obchodovať), `mb` (bias), `cs` (bool, koniec seansy, len keď true) | každý uzavretý bar grafu, aj pri prehrávaní predhistórie (`ready:false`) |
| `order` | `bt`, `ready` + polia `OrderIntent.WriteJson` (`a` entry/cancel/close, `id`, `src`, `dir`, `ot`, `r`, `p{dir,e,sl,tp,q,sd,tr}`) | zámer enginu, jeden riadok na zámer |
| `order` (`a: "modify"`) | `bt`, `ready`, `a: "modify"`, `id` (id vstupu), `p{sl,tp}` (nová hodnota alebo `null` = nemenené), `r` (`trailing` / iný dôvod) | adaptér (nie engine) posunul SL/TP pracujúceho orderu — každý posun trailingu; SL/TP pri vstupe nesie už plán, ten sa nehlási |
| `event` | `bt` + `StateEvent.WriteJson` (`ts,z,f,to,r`) | prechod stavu zóny |
| `draw` | `bt`, `d`: pole `DrawCommand` (box/line/label/bg/update/delete), `final` (bool, len pre kresby posledného baru) | keď engine za bar niečo nakreslil |
| `fill` | `ft` (čas exekúcie ms UTC), `id` (id vstupu), `side` `in`/`out`, `exit` (meno výstupu: NT `Stop loss`/`Profit target`/`tb_close`/`tb_session_end`, MT5 `sltp`/`close`; pri `in` prázdne), `price`, `qty`, `ready` | vyplnenie u brokera (adaptér, nie engine) |
| `stat` | `stats` (objekt: `Engine.Stats()` + `adapter_*` počítadlá) | pri ukončení |
| `note` | `text`, `level` (`info`/`warn`/`error`) | varovania adaptéra (neskorý bar, chyba spoolu…) |
| `bye` | `reason` | ukončenie stratégie (posledný riadok súboru, keď sa stihne) |

Príklad:

```
{"seq":1,"t":1790000000123,"k":"hello","schema":1,"platform":"mt5","account":"5012345-ICMarkets-Demo","symbol":"NAS100","tf":3,"strategy":"ibsnet","profile":"nas100_dukas_3m","session":"a1b2c3d4","host":"VM-TRADE-01","tester":false,"config":{...},"instrument":{...}}
{"seq":2,"t":1790000000456,"k":"bar","bt":1789999820000,"o":20100.5,"h":20110,"l":20099,"c":20105.25,"v":1234,"ready":true,"mb":1}
{"seq":3,"t":1790000000457,"k":"order","bt":1789999820000,"ready":true,"a":"entry","id":"L-4711","src":4711,"dir":1,"ot":"limit","r":"zone touch","p":{"dir":1,"e":20090,"sl":20070,"tp":20150,"q":1,"sd":20}}
{"seq":4,"t":1790000000458,"k":"draw","bt":1789999820000,"d":[{"t":"box","k":"zone","id":"z4711",...}]}
{"seq":5,"t":1790000063000,"k":"fill","ft":1790000062800,"id":"L-4711","side":"in","exit":"","price":20090,"qty":1,"ready":true}
{"seq":6,"t":1790000180002,"k":"order","bt":1790000000000,"ready":true,"a":"modify","id":"L-4711","p":{"sl":20085,"tp":null},"r":"trailing"}
```

## C# (`csharp/TradeBot.Core/Live.cs`)

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
| `store.py` | `LiveStore(path)` nad sqlite — jeden kód pre hub aj zrkadlo webapp (API nižšie) |
| `spool.py` | `default_roots()` (NT + MT5 + env), `SpoolReader(roots, cursor_path)`: `read(max_events)` → `Batch(instance, session, path, events, end_offset)`, `commit(batch)`; neúplný posledný riadok (bez `\n`) sa nečíta |
| `shipper.py` | `LiveShipper(reader, http, agent)`: `pump(max_batches)` → `POST /api/live/events`, kurzor posunie len po 200; `status()` |
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
| GET | `/api/live/export?after=&limit=` | riadky pre zrkadlo |

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
`GET /api/live/{id}/events?…&session=`, a **`GET /api/live/stream?after=`** — SSE
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
`live` = bez `bye` a posledná udalosť do 3 barov TF). V detaile inštancie je výber **Beh**:
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
- Adaptér súbor kontroluje podľa mtime **každých 5 s** (MT5 `OnTimer`, NT `System.Timers.Timer` +
  `TriggerCustomEvent`, nech to beží vo vlákne stratégie; AddOn takisto 5 s) a pri každom bare. Každá
  aplikovaná zmena ide do spoolu ako `control` (`mode`, `profile`, `source`: `control`/`default`/`pending`)
  a do logu. Oneskorenie pokynu z webapp ≈ heartbeat agenta (3 s) + tých 5 s.
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
| **account** | `id` (slug), `agent` (meno agenta = stroj), `platform` (`mt5`/`ninjatrader`), `label`, `login` (MT5 číslo účtu / NT meno účtu, napr. `Sim101`), `server` (MT5 server / NT meno pripojenia), `terminal` (MT5: cesta k `terminal64.exe` alebo k portable inštancii; NT: prázdne), `portable` (bool), `created`, `updated`, `by`, `secret_pending` (heslo čaká na prevzatie agentom — po prevzatí sa z hubu zmaže; hub nikdy heslo neukladá natrvalo) |
| **deployment** | `id`, `account` (id), `strategy` (kľúč enginu), `symbol`, `tf` (min), `profile` (názov), `config` (celý config enginu = snímka profilu), `config_hash` (sha256 configu), `mode` (`enabled`/`paused`/`flatten`; **nové nasadenie je predvolene `paused`** — `DEFAULT_MODE`, control súbor s pauzou je na disku skôr, než platforma inštanciu spustí, a obchodovať začne, až keď ho človek zapne; výslovný `mode: enabled` v POST sa rešpektuje), `active` (bool — má inštancia vôbec existovať; `false` = odstrániť z platformy), `created`, `updated`, `by`; odvodené `instance` = `instance_id(platform, <MT5 login>-<server> / NT meno účtu, symbol, tf, strategy)` |
| **audit** | `ts`, `by`, `action`, `account`/`deployment`, `old`, `new` (JSON) — každá zmena |
| **applied** | čo agent naposledy hlásil k deploymentu: `deployment`, `agent`, `config_hash`, `mode`, `status` (`ok`/`pending`/`error`), `error`, `ts` |

### Hub API (mutácie len s hlavným tokenom; čítanie ktokoľvek s tokenom)

`GET/POST /api/live/accounts`, `GET/PATCH/DELETE /api/live/accounts/{id}` (POST/PATCH smie niesť
`password` — uloží sa len ako `secret_pending`), `GET/POST /api/live/deployments`,
`GET/PATCH/DELETE /api/live/deployments/{id}` (PATCH: `mode`, `profile`+`config`, `active`),
`GET /api/live/audit?limit=`. Odpoveď deploymentu nesie aj `applied` a `instance` (a či inštancia
v spoole žije).

### Heartbeat (rozšírenie, `tester/hub`)

- Agent posiela navyše `live: {"instances": [ {instance, session, last_t, last_bar_ms, mode, profile} ], "applied": [ {deployment, config_hash, mode, status, error} ], "drivers": ["mt5", "ninjatrader"] }`.
- Hub odpovedá navyše `live: {"accounts": [ … len tohto agenta, so `secret` ak čaká … ], "deployments": [ … len tohto agenta, s `config` … ]}` — vždy celý zoznam (malý), agent si drží posledný a zosúlaďuje pri každom heartbeate; keď agent v `applied` potvrdí prevzatie hesla (`secret_ack: [account_id]`), hub `secret_pending` zmaže.

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
```

`Reconciler.run(desired)` volá driver pre každý účet: heslo → `store_secret`, profily → `ensure_profile`,
control → `write_control`, inštancie → `ensure_instance`/`remove_instance`; výsledok ide do `applied`
v ďalšom heartbeate. Nič nesmie vyhodiť výnimku von (chyba = `status: error` k danému deploymentu).

Poradie okolo control súboru je vec bezpečnosti, lebo adaptéry berú **chýbajúci súbor ako `enabled`**:

- control sa píše **pred** `ensure_instance` (nové nasadenie = `paused` na disku skôr, než platforma
  inštanciu spustí; MT5 driver to pred štartom terminálu ešte skontroluje a chýbajúci dopíše);
- `remove_instance` control **nemaže**, ale prepne na `paused` (`flatten` neprebíja) a odloží; zmaže ho až
  `ensure_instance` — MT5 po zavretí terminálu s tým grafom, NT až v kole, keď inštancia už nebola
  v `deploy.json` (AddOn ju medzitým zastavil);
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
  podľa obsahu, nie textu). Zmena množiny grafov (aj zmenený config pri rovnakom názve profilu — EA číta
  profil len pri štarte) = slušný reštart terminálu; režim a názov profilu idú bez reštartu cez control.
  Driver terminál spúšťa a pri páde reštartuje; `install` DLL/EA nerobí (to je nasadenie kódu, fáza 2c).
  Podrobne [MT5.md](MT5.md), „Nasadenie z hubu (driver)“.
- **NinjaTrader driver:** zapíše `Documents\NinjaTrader 8\TradeBot\deploy.json`
  `{"instances":[{deployment, connection, account, instrument, tf, strategy, profile}]}` a control
  súbory; beh robí **AddOn** (`TradeBotLiveAddOn`), ktorý pri štarte NT a pri zmene mtime
  `deploy.json` inštancie spustí/zastaví: `Connection.Connect`, `BarsRequest` (história =
  predhistória enginu + živé bary), `Engine.OnBar`, ordery cez `Account.CreateOrder/Submit`,
  SL/TP ako samostatné ordery (OCO), jedna pozícia naraz, trailing, fills z `ExecutionUpdate`,
  spool cez `LiveSpool`, control súbor. NT proces spúšťa driver len ak nebeží (login NT konta musí
  byť zapamätaný — jediný ručný krok).

### Webapp (karta Live)

Sekcie **Účty** (zoznam + „Pridať účet“: agent, platforma, názov, login, server/pripojenie,
terminál, heslo — heslo ide raz na hub, nikdy sa neukladá do zrkadla) a **Nasadenia** (tabuľka:
účet, stratégia, symbol, TF, profil, režim, stav inštancie zo spoolu, drift `config_hash` vs.
`applied`, posledný bar; tlačidlá pauza/zapnúť/flatten, zmena profilu (výber z profilov stratégie
alebo úprava parametrov formulárom z `params.py`), odstrániť; „Nasadiť“: účet, stratégia, symbol,
TF, profil, režim — predvolene **pauza**, nová stratégia sa zapína až v tabuľke). „Pridať účet“ má
nepovinné **Id účtu** (placeholder ukazuje slug názvu, ktorý by hub spravil sám). Mutácie idú cez
webapp na hub s **admin tokenom** (`admin_token` v `tester/agent.json`
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
   súbory inštancie (`position_from_spool`). Inštancia bez spoolu = pozícia neznáma = blokované.
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

## Testy

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
  +`order/modify` sú platné podľa `schema.validate`, `Version() == 2`.
- `python -m tradebot.adapters.ninjatrader check` a `python -m tradebot.adapters.mt5 check` prekladajú.
