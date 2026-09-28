# Live: telemetria zo spustených stratégií (NinjaTrader 8, MetaTrader 5) do webapp

Fáza 1 — **len čítanie**: bežiaca stratégia s C# jadrom hlási bary, zámery enginu (ordery),
prechody stavov, kresby a vyplnenia u brokera; webapp ich ukazuje na karte **Live**. Ovládanie
(zmena profilu, pauza, nasadenie, účty) je fáza 2 a stavia na tých istých entitách.

## Cesta dát a kde sa čo cache-uje

```
NT8 strategia / MT5 EA ──► TradeBot.Core LiveSpool ──► spool/<instance>/<súbor>.jsonl   (1) disk platformy
                                                              │
      tester.hub agent (na tom istom PC) ── SpoolReader + kurzor ──► POST /api/live/events   (2) kurzor za potvrdením
                                                              │
                                                     HUB  live.sqlite                        (3) hub
                                                              │
      webapp ── LiveMirror (GET /api/live/export?after=) ──► tester/live/mirror.sqlite       (4) webapp
```

Každý uzol smie byť dole a nič sa nestratí:

1. **Platforma** píše len na lokálny disk (append-only JSONL, flush po riadku v realtime). Sieť
   z NT/MT5 nejde nikdy — MQL5 `WebRequest` chce allow-list a v Testeri nefunguje; keď spadne
   agent alebo hub, stratégia obchoduje ďalej a súbory čakajú.
2. **Agent** číta spool od uloženého kurzora (`tester/live/cursor.json`: súbor → offset) a posúva
   ho **až po 200 od hubu**. Hub dole = kurzor stojí, súbory rastú, po návrate sa dopošle všetko.
3. **Hub** ukladá do `tester/hub_data/live.sqlite` idempotentne (`UNIQUE(instance, session, seq)`),
   takže opakované poslanie tej istej dávky nič nezdvojí.
4. **Webapp** si z hubu zrkadlí udalosti do vlastného sqlite (kurzor = rowid hubu). Hub dole =
   webapp ukazuje, čo má. Keď webapp beží na obchodnom PC, číta aj lokálny spool priamo
   (vlastný kurzor `tester/live/cursor_webapp.json`) — funguje aj bez hubu.

Platformy sú za NAT, verejný je len hub → všetko je **pull/push od agenta**, hub nikdy nevolá von.

## Identita

- **instance** = adresár spoolu: `<platform>_<account>_<symbol>_<tf>m_<strategy>`, znaky mimo
  `[A-Za-z0-9._-]` nahradené `-` (`ninjatrader_Sim101_MNQ-12-26_3m_ibsnet`,
  `mt5_5012345-ICMarkets-Demo_NAS100_3m_orbnet`). Stabilná cez reštarty — jedna inštancia v webapp.
  - NT: `Account.Name`; MT5: `<ACCOUNT_LOGIN>-<ACCOUNT_SERVER>`.
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
  price, qty, ready)`, `SpoolNote(handle, level, text)`, `SpoolClose(handle, reason)` (napíše aj
  `stat`), `SpoolPath(handle)`; `Destroy` zavrie spool, ak ostal otvorený. `Version()` → **2**
  (EA kontroluje 2; starú DLL treba preinštalovať).
- NinjaTrader volá `LiveSpool` priamo (`TradeBotStrategy.cs`): otvorí v `DataLoaded` (ak
  `LiveTelemetry && !IsInStrategyAnalyzer`), `Realtime = true` v `State.Realtime`, `Bar` hneď po
  `Export(...)`, `Fill` vedľa `ExportFill`, `Stats` + `Close("terminated")` v `Terminated`.
- MT5 EA (`TradeBotEA.mqh`) zrkadlo: `SpoolOpen` v `OnInit` po `Create` (koreň
  `TerminalInfoString(TERMINAL_COMMONDATA_PATH) + "\\Files\\TradeBot\\spool"`), `SpoolRealtime(true)`
  po `ReplayHistory`, `SpoolBar` hneď po `StaticHost::OnBar`, `SpoolFill` vedľa `ExportFill`,
  `SpoolClose` v `OnDeinit`.

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
.events(instance, *, after: int = 0, kinds: list[str] | None = None, limit: int = 1000) -> list[dict]   # riadky {"id": rowid, "session", "seq", "event": {...}}
.snapshot(instance, *, bars: int = 500) -> dict    # {"instance", "bars", "orders", "events", "draw", "fills", "stats", "notes"} za posledných N barov
.export(after: int = 0, limit: int = 5000) -> list[dict]   # {"id", "agent", "instance", "session", "event"} — pre zrkadlo
.cursor() -> int                   # max rowid
```

Hub (`tester/hub/live.py`, pripája `create_hub_app`), auth ako ostatné (token agenta = jeho meno):

| metóda | cesta | telo / odpoveď |
|---|---|---|
| POST | `/api/live/events` | `{"agent", "batches": [{"instance", "session", "events": [...]}]}` → `{"accepted": n}`; `own(who, agent)` |
| GET | `/api/live/instances` | zoznam |
| GET | `/api/live/instances/{id}` | jedna |
| GET | `/api/live/instances/{id}/events?after=&kinds=&limit=` | riadky |
| GET | `/api/live/instances/{id}/snapshot?bars=` | snapshot |
| GET | `/api/live/export?after=&limit=` | riadky pre zrkadlo |

Agent (`tester/hub/agent.py`): v pomalom vlákne (`work()`) pribudne krok `_ship_live` — shipper
vznikne, keď existuje aspoň jeden koreň spoolu; heartbeat sa nemení. Headless
`python -m tester.hub agent` posiela rovnako.

Webapp (`tester/webapp/api/live.py`, `static/js/live.js`, karta **Live**): `LiveMirror` vlákno
(každých 5 s `export` z hubu + lokálny spool, ak je) → `tester/live/mirror.sqlite`;
`GET /api/live` (inštancie + stav zrkadla), `GET /api/live/{id}/snapshot`, `GET /api/live/{id}/events`.
Graf: Plotly sviečky z `bar`, kresby cez `objectTraces` z `chart.js`, fills ako značky, tabuľky
orderov a fillov; obnova každých 5 s.

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
  `TriggerCustomEvent`, nech to beží vo vlákne stratégie) a pri každom bare. Každá aplikovaná zmena
  ide do spoolu ako `control` (`mode`, `profile`, `source`: `control`/`default`/`pending`) a do logu.
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

## Testy

- `tester/tests/test_live_store.py` — store: idempotencia, snapshot, export/kurzor.
- `tester/tests/test_live_spool.py` — reader: kurzor, neúplný riadok, rotácia, viac inštancií;
  shipper proti falošnému HTTP (výpadok = kurzor stojí, po návrate nič dvakrát).
- `tester/tests/test_hub.py` — `/api/live/*` cez TestClient, práva tokenov.
- `tester/tests/test_mt5_static_host.py` — `Spool*` cez reflexiu: súbor vznikne, `hello`+`bar`+`fill`
  sú platné podľa `schema.validate`, `Version() == 2`.
- `python -m tradebot.adapters.ninjatrader check` a `python -m tradebot.adapters.mt5 check` prekladajú.
