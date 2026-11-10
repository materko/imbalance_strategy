# Audit kódu a architektúry: stav po 25. 10., nové nálezy, vylepšenia

Dátum: 9. 11. 2026. Auditovaný commit: `fb2b31590` (`main`). Nadväzuje na
[AUDIT_architektura_2026-10-25.md](AUDIT_architektura_2026-10-25.md) (commit `fbb1de025`) a
[AUDIT_routing_2026-10-26.md](AUDIT_routing_2026-10-26.md); medzi nimi je 197 commitov a ~120 000
pridaných riadkov (38 nových stratégií, prepísaný `tradebot/live`, +3 000 riadkov v hube, +1 700
v každom z adaptérov NinjaTrader a MT5). Rozsah: architektúra, rýchlosť, obnova spojenia, error handling.

Označenie nálezov: `N-…` sú z 25. 10. (stav v §3), `M-…` sú nové (§4). Popis architektúry, API a
protokolov z §3–4 októbrového auditu platí ďalej a neopakuje sa tu.

## 1. Záver

Od októbra sa opravila väčšina toho, čo bolo vtedy P1: obaly vstupov v C# sa zapínajú podľa hodnôt
configu (N-CS-1), emulátor má predhistóriu a neadoptuje cudzí SL/TP (N-CORE-2, 3), pozícia bez stopu
po odmietnutom SL/TP sa v NT aj MT5 rieši (N-LIVE-1 až 6), import dát zlučuje a píše atomicky
(N-DATA-1), reštart agenta a duplicitné meno agenta hub zvláda (N-HUB-1, 2, 4), všetkých päť kritických
nálezov routingu (K1–K5) je opravených. Otvorené ostali prevažne nálezy P3; stav po jednom je v §3.

Nové riziká sú tam, kde pribudlo najviac kódu:

1. **Životný cyklus orderu v živých adaptéroch.** NinjaTrader aj MT5 EA prestanú order sledovať
   v okamihu, keď pošlú jeho zrušenie, nie keď broker zrušenie potvrdí. Výplň, ktorá príde medzitým,
   skončí ako pozícia bez SL/TP, trailingu a EOD (M-LIVE-1, 2, 3). Exekútor MT5 to isté už vyriešený má
   (routing K1) — oprava sa len nepreniesla.
2. **Oprava N-CORE-1 je neúplná.** Market vstup vo Freqtrade sa už plní na open ďalšej sviečky, ale
   veľkosť sa stále počíta z close signálnej. Keď je open vyššie, Freqtrade množstvo oreže pod zadaný
   počet kontraktov — pri 1 kontrakte MNQ obchod vypadne (M-CORE-1). Dotýka sa každej stratégie
   s market vstupom na inštrumente s celým krokom.
3. **Požadovaný stav nasadení nemá identitu.** Hub s prázdnou alebo staršou databázou nasadení
   pošle agentovi prázdny zoznam a agent zloží grafy zo všetkých obchodných strojov (M-HUB-2).
4. **Rýchlosť.** Lenivý zápis `state.json` hubu z októbra sa nikdy neuplatní — zapisuje sa ďalej pri
   každom heartbeate (M-HUB-1). Úvodná karta webapp skladá katalóg 96 stratégií a 637 profilov nanovo
   pri každom volaní (M-WEB-3).

Obnova spojenia: kostra (agent ťahá, kurzor až po potvrdení, idempotentný sklad) drží. Chýba stále
backoff s jitterom (N-HUB-13), idempotencia zadania výpočtu (M-HUB-5), rozlíšenie trvalej a dočasnej
chyby pri posielaní spoolu (M-HUB-6) a v NT samooprava mŕtveho dátového radu (N-LIVE-7).

**Čo je a čo nie je overené.** Audit je z čítania kódu; nič sa nebuildovalo, nespúšťalo u brokera
ani proti živému hubu a sada testov sa nepúšťala. Nálezy označené ✔ som po sub-audite potvrdil
v zdrojáku sám; ostatné stoja na jednom čítaní. Jediný nález s meraním je M-HUB-1 (10 heartbeatov =
10 plných zápisov). Správanie NT8 a MT5 pri pretekoch cancel/fill a pri štarte bez spojenia je úsudok
z kódu a znalosti platforiem, nie reprodukcia.

## 2. Odporúčané poradie

| # | Čo | Nálezy | Odhad |
|---|---|---|---|
| 1 | Jedno pravidlo životného cyklu orderu v NT, EA aj exekútore: sledovaný order sa zahodí až po potvrdenom koncovom stave; vlastná výplň bez záznamu sa adoptuje alebo zavrie s `error` | M-LIVE-1, 2, 3, 6 | 2–3 dni + demo |
| 2 | EA: obnova stavu až po spojení a periodické zosúladenie s brokerom (prevziať z exekútora) | M-LIVE-4, 7 | 1 deň |
| 3 | Veľkosť market vstupu vo Freqtrade z ceny výplne + integračný test s gapom; potom prepočítať merania market stratégií | M-CORE-1 | 0,5 dňa + prepočet |
| 4 | `store_id` + rastúca revízia požadovaného stavu; neznáma pozícia = podržať | M-HUB-2, 3 | 1 deň |
| 5 | Jedna `write_atomic` / `load_or_quarantine` v jadre pre manifest odvodených TF, `state.json`, `agent.json`, kurzory, rolls, plán behu | M-CORE-4, N-HUB-8, 9, N-WEB-4, M-HUB-10 | 1 deň |
| 6 | Spoľahlivé vypnutie webapp (`timeout_graceful_shutdown`, `atexit`, stav „closing") | M-WEB-1, 2, 6 | 0,5 dňa |
| 7 | Rýchlosť: fingerprint hubu bez `live`, cache katalógu, throttle `index.sync` | M-HUB-1, M-WEB-3, 4, 5 | 1–2 dni |
| 8 | Viditeľnosť straty telemetrie a zadaní: `rejected` z hubu, karanténa otrávenej dávky, `request_id`, backoff + jitter | M-HUB-4, 5, 6, N-HUB-13 | 2 dni |
| 9 | Kalendár SPRÁVY: doplniť 2027 pre JOLTS, RETAIL, PCE, GDP a pridať kontrolu konca pokrytia | M-CORE-3 | pred 1. 1. 2027 |
| 10 | Simulátor porúch pre stavové automaty adaptérov (rejekty, neskoré výplne, výpadky) | — | týždeň |

Demo test exekútora z auditu routingu stále nie je urobený; kroky 1 a 2 ho nenahrádzajú.

> **Stav 10. 11. 2026: krok 10 je hotový pre NinjaTrader.** `tester/faultsim` púšťa skutočný `LiveInstance` nad
> náhradnými typmi NT s falošným brokerom a skriptovaným enginom, čas je simulovaný (`LiveClock`, `Step`);
> 31 scenárov v `tester/tests/test_ninjatrader_faults.py` drží M-LIVE-1, 2, 6 a N-LIVE-1, 11, 12
> ([docs/SIMULATOR_PORUCH.md](../SIMULATOR_PORUCH.md)). Simulátor hneď našiel dve nové chyby, obe opravené:
> SL/TP ostávali u brokera po trhovom výstupe, keď sa ich zrušenie nepotvrdilo (stop bez pozície), a odmietnuté
> zrušenie vstupu sa bralo ako koniec orderu. **MT5 (EA, exekútor) simulátor nepokrýva** — MQL5 mimo terminálu
> nebeží; M-LIVE-3 a routing ostávajú na Strategy Testeri a deme. Model brokera je predpoklad, nie NT:
> skúšku na Sim101 nenahrádza.

### 2.1 Stav 10. 11. 2026 večer: druhé kolo — všetky otvorené nálezy naraz

Po krokoch 1–10 sa prešli všetky nálezy, ktoré ostali otvorené alebo čiastočné (§3, §4) a vylepšenia z §5.
Tento blok je platný stav; tabuľky v §3 a texty v §4 opisujú stav pri audite. **Overené:** `ruff`, preklad C# jadra,
preklad adaptéra proti NinjaTraderu 8, preklad EA a exekútora MetaEditorom z repa (dočasný strom), sada testov
a simulátor porúch (33 scenárov). **Neoverené:** nič z toho nebežalo u brokera (Sim101, MT5 demo) ani proti živému
hubu; ESLint sa lokálne pustiť nedá (bez Node) — skripty webapp prešli len načítaním v prehliadači.

**Živé adaptéry**

| Nález | Stav | Čo sa zmenilo |
|---|---|---|
| M-LIVE-5 | opravené | EA `PlaceExits` starú dvojicu SL/TP najprv zruší; čo sa zrušiť nedá, ostáva sledované (`exitsStale`) a timer to skúša znova |
| M-LIVE-7 (exekútor) | opravené | `PositionGone`: vyplnená pozícia, ktorá u brokera 10 s chýba bez dealu, sa dohľadá v histórii; nenájdená ostáva s `error` |
| M-LIVE-8 | opravené | EA `EngineFail`: zlyhanie `OnBar`, `FeedHtf`, `EodDue` ide do hubu ako `note error` s tlmením |
| M-LIVE-9 | opravené | most: `BridgeError` aj pri zavretej rúre, stderr hosta v chybe; build: DLL a Host.exe sa menia spolu alebo vôbec, timeout kompilátora; NT: udalosť route, ktorá hodí výnimku, sa skúša 5× a až potom zahodí s `error`; stav nesie `closing` (zatváranie sa po reštarte dokončí, aj v EA) a vlastný trailing enginu sa pri prevzatí ohlási |
| N-LIVE-7 | opravené | NT: mŕtvy rad barov pri pripojenom účte (10 min) = reštart inštancie `feed_dead`, AddOn ju spustí znova |
| N-LIVE-8 | opravené | grafová `Strategy`: `OnBarUpdate`, `OnOrderUpdate`, `OnExecutionUpdate` naživo výnimku zachytia a nahlásia; v histórii ju neprehltnú |
| N-LIVE-23 | čiastočne | prehrávanie predhistórie už nedostáva živú pozíciu účtu; sklz market orderov EA je vstup `InpDeviationPts` (50). Ostatné drobnosti riadku (hodiny hubu vs. agenta, F5 cez `SendInput`, denný limit podľa UTC dňa) ostávajú |
| N-LIVE-13, 20, 22 | prijaté obmedzenie | dve inštancie na jednom účte a inštrumente, podlaha 1 kontrakt nad rizikom a rollover kontraktu majú alarm, nie automatiku — zmena je rozhodnutie o správaní, nie oprava |
| Routing H1–H6 | opravené podľa auditu routingu | každý má v [AUDIT_routing_2026-10-26.md](AUDIT_routing_2026-10-26.md) poznámku *(opravené)* a test; znova sa nečítali |
| §5 bod 1 | hotové | [docs/STAV_ORDERU.md](../STAV_ORDERU.md): jedna tabuľka stavov a pravidiel pre NT, EA a exekútor |
| §5 bod 6 | hotové pre kalendár | `IPreflight` v C# jadre, `StaticHost.Preflight` pre MT5; SPRÁVY pri živom štarte hlási koniec pokrytia kalendára 45 dní vopred. Vek profilu a verziu DLL voči commitu hub už ukazuje (`live.installed`), do preflightu nešli |

**Jadro, dáta, C# most**

| Nález | Stav | Čo sa zmenilo |
|---|---|---|
| M-CORE-2 | opravené | súčty cez okná berú obchod z prekrytia raz — reže sa podľa času (skoršie okno vyhráva); kľúč `(open_date, enter_tag)` z nálezu nefunguje, `enter_tag` nesie číslo baru od začiatku behu |
| M-CORE-5 | opravené | `timeframes --force` prepíše len súbory z manifestu odvodených |
| M-CORE-6 | opravené | `rolls.json` sa zlučuje podľa dátumu |
| M-CORE-7, N-CORE-7 | opravené | `canonical_key` v configu; jedno pravidlo PF (`core.money.profit_factor`); TF cez `timeframe_minutes`; Sharpe zo všetkých obchodných dní okien (deň bez obchodu = 0). **Sharpe a DSR nových posudkov vyjdú nižšie než v už napísaných dokumentoch**, tie sa neprepisovali |
| M-CORE-8, §5 bod 3 | otvorené (rozhodnutie) | spoločný čas New Yorku a seansa naprieč enginmi sa nerobili |
| M-CORE-9 | opravené | dvojitý kľúč v registry je chyba; pokazený `calendar.json` nezhodí import, chyba príde až pri použití SPRÁV. Trhové varianty ostali balíkmi (rozhodnutie) |
| N-CORE-9 | opravené, jedna časť čiastočne | chýbajúci `engine_factory` je `ValueError`, zlyhané záverečné kresby a chýbajúci detail sú v logu; chýbajúci TF vo Freqtrade je `error` s tracebackom, ale beh pokračuje |
| N-CORE-10, §5 bod 4 | čiastočne | emulátor reže m1 raz (`searchsorted`, `BarCache`; výsledky 8 stratégií bit po bite rovnaké, behy ~20 % rýchlejšie). `BarHistory._sma` a `StateMachine` IBS bez zmeny — bit po bite rovnaký výsledok by nedali |
| N-CORE-12 | opravené | sedem testov DST v `tradebot/tests/test_clock.py`, C# strana kontrolovaná tiež |
| N-DATA-5 | opravené | zápis ASCII po stĺpcoch (bajt po bajte rovnaký), cache pohľadu `livesim` sleduje len súbory svojej inštancie |
| N-CS-2 | opravené pre most | neznáme kľúče profilu sú v `Info()` ako `unknown_config` a most ich loguje; NT a MT5 ich ešte neukazujú |
| N-CS-6, 7, 9 | opravené | stdio vs. inproc pre každú C# stratégiu; `SessionClock.LocalToUtcMs`; EMA z orezaného N; TF grafu pod 1 minútu je chyba; zmenená DLL po načítaní sa ohlási |
| N-CS-8 | čiastočne | cache `SessionClock.Local`, buffer v `OrbEngine.VolumeOk`; ostatné alokácie ostali |

**Hub, agent, telemetria**

| Nález | Stav | Čo sa zmenilo |
|---|---|---|
| M-HUB-7 | opravené | Telegram 409 príkazy len pozastaví, skúša znova (30 s – 10 min), trvalý konflikt ohlási raz |
| M-HUB-8 | opravené | heartbeat má vlastný timeout 10 s, verzia kódu sa číta zo súborov `.git`, spool sa nevypisuje pri každom tiku |
| M-HUB-9 | opravené | zrkadlo webapp si drží kotvu riadku pod kurzorom; iná DB na hube = odznova |
| M-HUB-10, N-HUB-10 | opravené | agent stráži svoje vlákna, pokazený stav a kurzor je vidno, `computing` sa mení len pod zámkom |
| M-HUB-11 | opravené pre hub | strážca ide cez `PluginContext.agents()`; zlyhaný reload nechá bežať starý plugin. Hostiteľ pluginov **agenta** návrat nemá — znamenal by zmenu kontraktu a reštart obchodných strojov |
| N-HUB-3, 7, 8, 11, 12, 13, 15 | opravené | `/api/health` s chybami zápisu, zápis `state.json` mimo zámku, zip pred zmenou výpočtu, platnosť nevyzdvihnutých výsledkov (30 dní), chyba živej DB nezhodí heartbeat, SIGTERM = `bye`, strop veľkosti výsledku. Popis: [docs/HUB.md](../HUB.md) |
| zvyšok M-HUB-6 | opravené | strážca hlási stroj, ktorý 10 minút nevie poslať telemetriu |

**Webapp**

| Nález | Stav | Čo sa zmenilo |
|---|---|---|
| M-WEB-7, N-FE-4, §5 bod 5 | opravené | jeden `makePoller` (backoff, koniec pri 404, viditeľná chyba) pre frontu, sweep, hyperopt a maticu; fronta polluje aj prázdna |
| M-WEB-8, 9 | opravené | CLI berie HTTP chybu ako chybu (výpadok je len 502–504); zrušenie čakajúceho behu je pod zámkom fronty |
| M-WEB-10 | opravené | `StrategySpec.base_key` namiesto hádania z mena; jedna konštanta `DEFAULT_STRATEGY`; `demo_breakout` má trh a typ |
| N-WEB-4, 8, 12–18 | opravené | atomický `log.txt` a obnova z archívu; stĺpce `batch_kind`/`batch_id` v indexe a odhad času z indexu; GET histórie analytík nič nezapisuje; overenie id behu, strop dobehnutých úloh, `workers` platí hneď, zámky cache, timeout gitu, limit čakania na pracovný proces |
| N-WEB-19 | opravené skôr | `docs/API.md` a `docs/WEBAPP.md` už sedeli |
| N-FE-5 | opravené pre kreslenie | graf Live sa pri prúde udalostí prekresľuje najviac raz za 500 ms |

**Ostáva otvorené — menia obchody alebo dáta, treba rozhodnúť**

- **N-CORE-8** (SL/TP na bare výplne vo Freqtrade): zmení, čo engine vidí ako pozíciu, a tým obchody existujúcich stratégií.
- **N-CORE-11** (zaokrúhlenie `entry` pred `sl_distance` v ORB, RETEST limitka v počte obchodov): zmení množstvá a stopy
  ORB / ORBNet / VWAP ORB až o tick; rovnaká zmena patrí do `OrbEngine.cs`.
- **N-DATA-6**: front-month podľa dňa seansy mení commitnuté dáta archívu, zahodenie neúplnej poslednej odvodenej
  sviečky mení bary.
- **M-CORE-8** a §5 bod 3: nechané otvorené rozhodnutím z 10. 11.

## 3. Stav nálezov z 25. 10. a 26. 10.

### 3.1 Jadro, backtest adaptéry, dáta

| Nález | Stav | Dôkaz |
|---|---|---|
| N-CORE-1 market vstup ako limitka | čiastočne | `adapters/freqtrade/callbacks.py:140` vracia `proposed_rate`; veľkosť nie — M-CORE-1 |
| N-CORE-2 cudzí SL/TP v emulátore | opravené | `multicharts/emulator.py:310–322, 354` |
| N-CORE-3 emulátor bez predhistórie | opravené | `emulator.py:119–126, 246–272` |
| N-CORE-4, 5, 6 | opravené | `core/types.py:305`, `core/entry_order.py:123`, `tester/webapp/store.py:67–75` |
| N-CORE-7 PF bez strát | otvorené | `core/money.py:250`; druhé pravidlo v `tester/robust.py:74–77` (M-CORE-7) |
| N-CORE-8 interný model Freqtrade | otvorené | `freqtrade/runner.py:209–215` |
| N-CORE-9 tiché degradácie | otvorené | `freqtrade/timeframes.py:76`, `callbacks.py:125`, `emulator.py:484` |
| N-CORE-10 výkon | čiastočne | len `clock.py:43, 48` (`lru_cache`); `history.py:104`, IBS `statemachine.py` bez zmeny |
| N-CORE-11, 12 | otvorené | `orb/engine.py:188, 411`; DST bez testov |
| N-DATA-1, 2, 3, 4 | opravené | `tester/dukas_import.py:192–201`, `tester/timeframes.py:138–139`, `tester/livesim.py:119`, `tester/data_archive.py:108` |
| N-DATA-5, 6 | otvorené | `livesim.py:255`, `quotemanager.py:86`, `bento_import.py` |

### 3.2 C# jadro a most

| Nález | Stav | Dôkaz |
|---|---|---|
| N-CS-1 obaly podľa prítomnosti kľúčov | opravené | `TradeBot.Core/EntryLayers.cs:716–753`, `tester/tests/test_csharp_partial_profile.py` |
| N-CS-2 neznáme hodnoty | čiastočne | enumy hádžu (`EntryLayers.cs:721–724, 758–764`); neznáme kľúče sa ticho ignorujú |
| N-CS-3, 4, 5 | opravené | `Engine.cs:84–89`, `adapters/csharp/bridge.py:164–217`, `NativeBacktest.cs:34–46` |
| N-CS-6, 7 | čiastočne | pribudol test čiastočného profilu; `Ma.cs:19`, `Feather.cs:111–119` |
| N-CS-8, 9 | otvorené (P3) | `OrbEngine.cs:248`, `SessionClock.cs:130`, `bridge.py:84–109` |

### 3.3 Živé obchodovanie a routing

| Nález | Stav | Dôkaz (`LI` = `TradeBotLiveInstance.cs`, `EA` = `TradeBotEA.mqh`, `EX` = `TradeBotExecutor.mqh`) |
|---|---|---|
| N-LIVE-1, 2 | opravené | `LI:1104–1110, 1129–1163, 1200–1240` |
| N-LIVE-3, 4, 6 | opravené | `EA:1267–1306, 1340–1403, 1030–1040` |
| N-LIVE-5 pending pri `OnDeinit` | opravené, zvyšok v M-LIVE-3 | `EA:784–800` |
| N-LIVE-7 EOD a mŕtvy feed | čiastočne | alarm a hodinový EOD sú (`LI:1403–1448`, `EA:703–750`); mŕtvy `BarsRequest` sa znova nevyžiada |
| N-LIVE-8 | čiastočne | len zdokumentované; `TradeBotStrategy.cs:698` bez `try/catch` |
| N-LIVE-9, 10, 11, 12, 19, 21 | opravené | `LI:609, 1503–1512, 1366–1373`, `EA:393, 1423–1434, 1505–1508`, `Live.cs:341–354` |
| N-LIVE-13, 20, 22 | čiastočne | `LI:1521–1524` (`Ours()`), podlahy `LI:1066`, `EA:1020`, alarm `LI:1303–1325` |
| N-LIVE-14, 17, 18 | opravené | `tradebot/live/update.py:268`, `agent_plugins/telegram/service.py:535–541, 1006–1010` |
| N-LIVE-15 | čiastočne | M-HUB-3 |
| N-LIVE-23 | otvorené | `LI:863`, `EA:374` |
| Routing K1–K5 | opravené | `EX:1046–1056, 917, 829–841, 648–649, 939–983` |
| Routing V1, V3, V5; NT V2–V4, S2 | opravené | `EX:1005–1013, 1305–1316, 1150–1167`; `LI:2257–2265, 2467, 2213, 2357` |
| Routing H1–H6 | neoverené | overená len prítomnosť `_hold_open` (`live/apply.py:409`) |

### 3.4 Hub, agent, telemetria

| Nález | Stav | Dôkaz |
|---|---|---|
| N-HUB-1, 2, 4 | opravené | `hub/agent.py:1143–1177`, `hub/state.py:221–226, 281–283` |
| N-HUB-3 `persist_error` | čiastočne | je v stave a v UI; `hub/events.py:52–53` stále `except OSError: pass`, `/api/health` ho nevracia |
| N-HUB-5, 6, 14 | opravené | `live/spool.py:211–221`, `hub/update.py:76–82`, `tests/test_hub.py:29–38` |
| N-HUB-7 zápis pri heartbeate | čiastočne | `_dispatch` opravený; lenivý zápis nefunguje — M-HUB-1 |
| N-HUB-8, 9, 11, 12, 15 | otvorené | `state.py:869–881` (zip bez tmp), `:129–132` (pokazený `state.json` = prázdny hub), `:925`, `:319, 343`, `server.py:377` |
| N-HUB-10 | čiastočne | zamknutý len `_save` (`agent.py:823–826`); `computing` sa mení z dvoch vlákien bez zámku |
| N-HUB-13 backoff, `bye` | otvorené | pevné čakania `agent.py:310`, `client.py:403, 410`; `hub/__main__.py:241–243` |

### 3.5 Webapp

| Nález | Stav | Dôkaz (cesty v `tester/webapp/`) |
|---|---|---|
| N-WEB-1 sirota po vypnutí | čiastočne | `runner.py:214–232` + `app.py:66`; hook sa nie vždy spustí — M-WEB-1, 2 |
| N-WEB-2, 3, 5, 6, 7, 9, 10, 11 | opravené | `runner.py:251–288`, `archive.py`, `index.py:160–177`, `api/live.py:530–569`, `tester/native.py:107` |
| N-WEB-4 atomické zápisy | čiastočne | atomicky `store.py:100`, `profiles.py:262`, `anstore.py`; nie `store.py:155–160, 230`, `archive.py:210–215` |
| N-WEB-8 celá história na dopyt | čiastočne | `store.all()` ostáva pre odhad času: `api/hub.py:223`, `cli/remote.py:74`, `hub/agent.py:850, 882, 895` |
| N-WEB-12, 19 | čiastočne | GET stále zapisuje (`api/analytics_history.py:51–54`), už pod zámkom |
| N-WEB-13, 14, 15, 16, 17 | otvorené | `store.py:277–298` bez `_ID_RE`; `runner.jobs` nikdy nezmenšené; `gitsync.py:69–73` bez timeoutu |
| N-WEB-18 | neoverené | |
| N-FE-1, 2, 3 | opravené | `queue_hub.js:10–19`, `live.js:347–376` |
| N-FE-4, 5 | čiastočne | pollery bežia navždy aj pri 404 (`sweep.js:223`, `hyperopt.js:140–143`, `matrix.js:109–112`); `renderLiveChart` pri každej udalosti (`live.js:182`) |

## 4. Nové nálezy

### 4.1 Živé obchodovanie (NinjaTrader 8, MetaTrader 5)

> **Stav 9. 11. 2026 večer: M-LIVE-1, 2, 3 a 6 sú opravené v kóde.** NT (`TradeBotLiveInstance.cs`): zrušený
> vstup ostáva v `_dying`, kým broker zrušenie nepotvrdí; neskorý fill sa prevezme a zavrie trhom
> (`AdoptLate`), nový vstup s tým istým id čaká na potvrdenie, pri zatváraní sa ruší aj zvyšok čiastočne
> vyplneného vstupu. EA (`TradeBotEA.mqh`): `EntryCancelState` rozlišuje vyplnený vstup od zrušeného
> (stav orderu v histórii), vyplnený ostáva sledovaný s `cancelWanted` a `RetryGuards` ho po príchode dealu
> zavrie. Overené prekladom (`ninjatrader check`, MetaEditor na dočasnom strome) a existujúcimi testmi;
> **správanie pri skutočných pretekoch cancel/fill nie je overené** — testy na stavový automat adaptérov
> neexistujú (§5 bod 2) a treba to prejsť na Sim101 / deme. Route (NT → exekútor) sa nemenil.
>
> **M-LIVE-4 a 7 sú opravené v EA** (tiež len preklad, bez dema): `RestoreState` beží až po pripojení k brokerovi
> (dovtedy sa stav neprepisuje a vstupy stoja) a `ReconcileBroker` na timeri zosúlaďuje sledované pozície a
> čakajúce vstupy s brokerom — pozícia bez dealu o zatvorení sa prestane sledovať, vstup vyplnený bez dealu sa
> prevezme z histórie. Exekútor (druhá polovica M-LIVE-7) sa nemenil. M-LIVE-5 a 8 ostávajú otvorené.

**M-LIVE-1 (P1) ✔ NT: preteky cancel/fill nechajú pozíciu bez ochrany.** `LI:1041–1045` (cancel
z enginu), `1471–1475` (Flatten/EOD), `2049` (obnova) zrušia vstup a `Tracked` hneď vyhodia z `_orders`.
Výplň, ktorá príde skôr, než broker zrušenie potvrdí, padne v `LI:1632–1637` do vetvy „cudzí order":
bez SL/TP, trailingu, EOD aj alarmu, a `HasOpenPosition` potom odkladá všetky ďalšie vstupy.
*Oprava:* `Tracked` označiť `Cancelling` a vyhodiť až pri `OrderState.Cancelled` (`HandleOrder` to
na `LI:1556` už robí); výplň vlastného orderu bez záznamu adoptovať alebo zavrieť s `note error`.

**M-LIVE-2 (P1) ✔ NT: nový vstup s rovnakým id nechá starý order pracovať.** `LI:1021–1034`:
`previous` sa ruší len vo vetve „odložený", inak ho nový `Tracked` v slovníku prepíše a `SubmitEntry`
ho neruší. Výplň starého orderu zahodí `ReferenceEquals` na `LI:1620` — nechránená alebo dvojitá
pozícia. EA (`EA:1068–1073`) aj grafová stratégia (`TradeBotStrategy.cs:820–821`) to ošetrené majú.
*Oprava:* najprv zrušiť `previous`, nový poslať po potvrdení.

**M-LIVE-3 (P1 netting, P2 hedging) ✔ EA: `DeleteOrGone` berie vyplnený vstup ako zmiznutý.**
`EA:1236–1241`: keď `OrderDelete` zlyhá a order už nie je medzi čakajúcimi, vráti `true` — „vyplnený
alebo zrušený inde" sa nerozlišuje. `CancelEntry` (`EA:1254–1257`) a `OnDeinit` (`EA:796`) ho potom
prestanú sledovať a neskorší deal sa zahodí (`EA:1526`). Je to chyba K1 z routingu, opravená len
v exekútore. *Oprava:* `HistoryOrderGetInteger(ORDER_STATE)` / `PositionSelectByTicket` ako `EX:1046–1056`.

**M-LIVE-4 (P1, správanie platformy neoverené) EA: `RestoreState` v `OnInit` bez čakania na spojenie.**
`EA:391` nekontroluje `TERMINAL_CONNECTED` (exekútor áno, `EX:1305–1316`). Ak pozície ešte nie sú
zosynchronizované, vetva hedgingu (`EA:1766–1767`) označí uložené obchody za zatvorené a `SaveState`
(`EA:395`) stav prepíše — pozície bežia bez trailingu a EOD a nové vstupy pyramídujú. Driver terminál
reštartuje často. *Oprava:* odložiť do `OnTimer` po pripojení.

**M-LIVE-5 (P2) EA netting: druhá čiastočná výplň vstupu stratí prvý pár SL/TP.** `EA:1534` volá
`PlaceExits` znova a `EA:1227–1231` prepíše `slTicket`/`tpTicket`; osirelý stop ostane GTC a neskôr
môže otvoriť opačnú pozíciu. *Oprava:* existujúci pár najprv zrušiť alebo mu zmeniť objem.

**M-LIVE-6 (P2) NT: zvyšok čiastočne vyplneného vstupu sa nezruší.** `RequestClose` (`LI:1173–1175`)
a spracovanie výstupu (`LI:1644–1649`) siahajú len na SL/TP; neskoršia výplň zvyšku je nesledovaná.

**M-LIVE-7 (P2) EA a exekútor: sledovaná pozícia sa s brokerom pravidelne nezosúlaďuje.**
`EX:1065, 1226`, `EA:1276, 1376` ticho vrátia, keď pozícia chýba; `Reconcile` beží raz (`EX:1315`).
Zmeškaný `DEAL_ADD` nechá fantómovú pozíciu, ktorá natrvalo blokuje vstupy. *Oprava:* pri spojení a
chýbajúcej pozícii dlhšie než N sekúnd zavolať `ReconcileOrder` / `ReportClosedAway`.

**M-LIVE-8 (P2) EA: chyby enginu hub nevidí.** `EA:956–958` pri zlyhaní `OnBar` len `Print` a
`g_lastChart` je už posunutý, takže `FeedWatch` mlčí; `EodDue == -1` sa ignoruje (`EA:706`).
*Oprava:* `Report("error")` s tlmením.

**M-LIVE-9 (P3) Most, build, obnova.** `bridge.py:210–211`: `BrokenPipeError` zo `stdin.write` nie je
zabalená do `BridgeError` a stderr hosta sa k chybe nepripája. `LI:2261–2265`: kurzor route udalosti sa
potvrdí, aj keď `HandleRouteEvent` hodil výnimku. `build.py:139–146`: pri `PermissionError` môže ostať
nová DLL so starým Host.exe a `.built-by` sa aj tak zapíše; `build.py:113` bez timeoutu.
`LI:1908–1913`: stav neukladá `Closing` a vlastné trailingy (VWAP stop) sa po reštarte ticho stratia.

### 4.2 Jadro, backtest adaptéry, dáta

**M-CORE-1 (P1) ✔ Freqtrade: veľkosť market vstupu sa počíta z inej ceny, než na akej sa plní.**
`adapters/freqtrade/callbacks.py:161`: `rate = row.entry` (close signálnej sviečky) aj pri `row.market`,
ale výplň je po oprave N-CORE-1 na `proposed_rate` (open ďalšej). Freqtrade si množstvo dopočíta
`stake / cena` a oreže na krok. Pri open > close vyjde menej než `qty`: MNQ s krokom 1 a `qty = 1`
dá 0,9999… → 0, obchod vypadne; `_STAKE_EPS` to nekryje. *Oprava:* `rate = current_rate if row.market
else row.entry` a integračný test Freqtrade vs. emulátor s gapom. Kým to nie je, merania market
stratégií na futures cez Freqtrade majú menej obchodov než emulátor a platforma.

> **Stav 10. 11. 2026: opravené.** Market vstup počíta stake z `current_rate` (cena po `custom_entry_price`),
> limitka ďalej z ceny plánu. Test `test_market_vstup_po_gape_drzi_pocet_kontraktov`
> (`tradebot/tests/test_freqtrade_entries.py`) prechádza a bez opravy pri gape nahor padá; golden testy proti
> TradingView prešli. Je to test na vzorci, ktorým Freqtrade množstvo dopočíta, nie celý backtest Freqtrade
> vs. emulátor. **Behy market stratégií cez Freqtrade spred opravy majú o obchod či kontrakt menej** tam, kde
> je krok kontraktu hrubý (futures a CFD na burze Tester); merania z nich treba prepočítať. Na krypte s krokom
> 0,001 je rozdiel najviac jeden krok.

**M-CORE-2 (P2) ✔ `tester/robust.py`: prekryv okien sa počíta dvakrát.** Komentár na `:128` tvrdí,
že prekrytie sa započíta raz, `_daily` (`:80–85`) ale sčíta. Okná `20231001-20241001` a
`20240904-20250904` sa prekrývajú 4.–30. 9. 2024, takže tie obchody sú v `all_base` dvakrát a skresľujú
celkový PF, verdikty `fee2`/`delay` aj DSR. *Oprava:* deduplikovať podľa `(open_date, enter_tag)`.

**M-CORE-3 (P2) ✔ Kalendár SPRÁVY končí pre štyri typy udalostí v decembri 2026.**
`strategies/spravy/calendar.json`, `coverage.to`: JOLTS 2026-12-01, RETAIL 2026-12-16, PCE a GDP
2026-12-23; ostatné do decembra 2027. Engine koniec pokrytia nekontroluje (`spravy/engine.py:90–93`),
takže živá stratégia od januára tieto udalosti ticho prestane obchodovať. *Oprava:* doplniť dátumy a
pridať varovanie + test, keď posledný dátum typu je bližšie než N dní.

> **Stav 10. 11. 2026: čiastočne.** PCE a GDP sú doplnené na celý rok 2027 z BEA
> (`apps.bea.gov/API/signup/release_dates.json`, prečítané priamo; koniec roka 2026 v ňom sedí s kalendárom)
> a `SpravyCalendar.cs` je vygenerovaný znova. Pribudla kontrola `python -m tradebot.strategies.spravy.calendar
> --check [dni]` a `tester/tests/test_spravy_calendar.py`: varuje 45 dní pred koncom pokrytia a padne, keď
> niektorému typu kalendár už skončil. **Chýba JOLTS** (posledný 1. 12. 2026 — v rozvrhu BLS na 2027 nie je)
> **a RETAIL** (posledný 16. 12. 2026 — stránku Census sa nepodarilo prečítať, blokuje automatický prístup;
> termíny z vyhľadávača som do kalendára nedal, lebo nesprávny dátum znamená obchod bez správy). Engine sa
> nemenil: koniec pokrytia naživo stále nehlási, stráži ho len kontrola a test.
>
> **Automatické dopĺňanie z ForexFactory** (plugin hubu `ff_calendar`, `sync.py`): týždenný export sa po každom
> stiahnutí porovná s kalendárom a rozdiel ide do nasadení ako `newsAdd` / `newsSkip` (hneď) a raz za mesiac do
> `calendar.json` v repozitári. Chýbajúce JOLTS a RETAIL sa tak doplnia samy v týždni, keď vyjdú. Na exporte
> z 9.–13. 11. 2026 je rozdiel nulový (CPI, CLAIMS, PPI sedia). Názvy udalostí pre ostatné typy
> (`calendar.FF_TITLES`) sú podľa zaužívaných názvov ForexFactory a overia sa až na živom feede — nesprávny názov
> sa prejaví ako oznámenie „v kalendári je, vo feede nie", nie ako vynechaná správa. Postup: [docs/HUB.md](../HUB.md).

**M-CORE-4 (P2) Manifest odvodených TF sa píše bez zámku a neatomicky.** `core/derived.py:71–83`
z webapp (`ensure`) aj z podprocesu Freqtrade (`freqtrade/timeframes.py:69`); pokazený manifest sa číta
ako prázdny (`:29–32`). Po stratenom zápise sa dopočítané súbory tvária ako stiahnuté — `split` ich
dá do archívu a gitu, čo je presne to, čo pravidlo o TF zakazuje.

> **Stav 10. 11. 2026: jednotný zápis je v `tradebot/core/atomic.py`** (`tester/atomic.py` ho len reexportuje):
> atomický zápis s opakovaním pri zamknutom cieli na Windows, zámok medzi procesmi (`file_lock`) a `read_json`,
> ktorý pokazený súbor odloží ako `.corrupt-<čas>` a zaloguje. Použité: manifest odvodených TF pod zámkom
> (M-CORE-4), `state.json` hubu pri načítaní (N-HUB-9), zip výsledku (N-HUB-8, len zápis), `agent.json` a stav
> agenta (N-HUB-13 časť, M-HUB-10 časť), kurzor spoolu, feather v `data_archive`, `rolls.json`, `plan.json`
> (N-WEB-4 časť). Testy v `tradebot/tests/test_atomic.py`. **Ostáva:** zlúčenie `rolls.json` podľa dátumu
> (M-CORE-6 — zápis je atomický, obsah stále len z posledného exportu), poradie „najprv zip, potom zmena
> výpočtu" a blokujúci `async` handler v hube (zvyšok N-HUB-8), `log.txt` behu a obnova z archívu (zvyšok
> N-WEB-4), dohľad nad vláknami agenta (zvyšok M-HUB-10).

**M-CORE-5 (P2) `timeframes --force` prepíše aj stiahnuté TF.** `tester/timeframes.py:138–139, 154`
a `remember(made)` ich označí ako odvodené; nápoveda (`:189`) sľubuje len odvodené.

**M-CORE-6 (P3) `rolls.json` po čiastočnom importe nesedí s archívom.** `tester/bento_import.py:294–296`
ho prepíše len z aktuálneho exportu, hoci rok sa už zlučuje.

**M-CORE-7 (P3) Drobnosti.** `core/config.py:203–208` číta `STRATEGIES[...]` bez `canonical_key`
(profil s `_strategy: "ibsninja"` padne); dve pravidlá PF bez strát (`robust.py:74–77` vs.
`money.py:250`); ručné parsovanie TF v `tester/lookahead.py:122–126` a `robust.py:105` (padne na „1h")
namiesto `core.candles.timeframe_minutes`; `robust.py:69` anualizuje Sharpe cez √252 z dní, kde bol
obchod, čo riedke stratégie nadhodnocuje.

**M-CORE-8 (P3) Opakované vzory v nových stratégiách** (vzorka spravy, sigma, nb, m2, sdeur).
37 enginov má vlastný `ZoneInfo("America/New_York")` a necachovaný `datetime.fromtimestamp` raz až
dvakrát na bar, s natvrdo zapísaným RTH 9:30/16:00 bez skrátených dní (`sigma/engine.py:78, 96`,
`nb/engine.py:198, 238`, `m2/engine.py:169, 232`). Predĺženie TP/SL boxu je skopírované v štyroch
enginoch, hoci existuje `rqport.TradeDraw`. Opakuje sa vzor N-CORE-11 (zaokrúhlený `entry`,
nezaokrúhlený `sl_distance`, `spravy/engine.py:122–123`) a `qty <= 0` sa ticho dvíha na `min_qty`.

**M-CORE-9 (P3) Registry.** `strategies/__init__.py`: 96 ručných importov a literál slovníka bez
kontroly jedinečnosti kľúčov; `spravy/calendar.py:31` číta súbor pri importe, takže pokazený
`calendar.json` zhodí celý registry. Trhové varianty (`sigmaes`, `m2mnq`, …) sú celé balíky kvôli
jednému `replace(BASE_SPEC, …)`.

**Vrstvy.** Jadro ani adaptéry sa podľa mena stratégie nevetvia. Zvyšky: `DEFAULT_STRATEGY = "ibs"`
(`core/config.py:41`, `freqtrade/hyperplan.py:165, 181`) a legacy re-exporty IBS
(`core/__init__.py:52–63`, `multicharts/signal.py:807`). Jedna asymetria Python/C#: Python vyžaduje
`hasattr(cfg, "trendTF")` (`core/entry_filter.py:218`), C# nie.

### 4.3 Hub, agent, telemetria

**M-HUB-1 (P2, rýchlosť) ✔ Lenivý zápis `state.json` sa nikdy neuplatní.** `hub/state.py:334`
zapíše pri každom heartbeate `agent["live"]["reported"] = clock()` a `_jobs_fingerprint` (`:148–152`)
`live` zahŕňa, takže porovnanie na `:313` vždy vyjde „zmena" a zápis je plný, pod globálnym zámkom.
Merané sondou: 10 heartbeatov = 10 zápisov, bez `live` 0. *Oprava:* `live`/`plugins` z odtlačku von
a serializovať mimo zámku zo snímky.

**M-HUB-2 (P1/P2, obnova) ✔ Prázdna alebo staršia databáza nasadení zloží živé stroje.**
`create_hub_app` založí prázdne tabuľky (`hub/server.py:200–203`), `desired_for_agent` vráti
`deployments: []` a zosúlaďovač berie všetko doterajšie ako zmiznuté (`live/apply.py:272–273`) a volá
`remove_instance`. Stratený volume alebo obnovená záloha tak zloží grafy na všetkých obchodných
strojoch; stará záloha navyše vráti pozastavené nasadenie do staršieho režimu. Otvorenú pozíciu drží
`_hold_open`, ale len keď ju pozná (M-HUB-3). *Oprava:* `store_id` + rastúca `rev`; agent odmietne
cudzie id, nižšiu revíziu aj „zmizlo všetko naraz" bez výslovného potvrdenia.

**M-HUB-3 (P2) ✔ `_hold_open` pri neznámej pozícii graf zloží.** `live/apply.py:426–432`: komentár
hovorí „radšej podržať", ale výnimka aj `None` (inštancia nie je v spoole) padnú do `if not pos:
return False`. *Oprava:* `None` = podržať, odstrániť len pri známej nule.

> **Stav 10. 11. 2026: M-HUB-2 a M-HUB-3 sú opravené.** Požadovaný stav nesie `store: {id, rev}` (meta tabuľka
> a triggery v `DeployStore`); reconciler stav z iného skladu alebo zo staršej revízie neaplikuje a hlási to hubu
> (`live_store_refused`), správca ho potvrdí cez `python -m tradebot.live store --adopt / --raise-rev`
> ([docs/LIVE.md](../LIVE.md)). M-HUB-3 bol užší, než hovorí nález: `None` z `position_from_spool` znamená
> „inštancia v spoole nie je" a tam sa odstraňuje správne (inak by sa nikdy nebežiace nasadenie neodstránilo);
> chybou bola len vetva s výnimkou, ktorá teraz nasadenie podrží. Pokryté testami v `test_live_apply.py` a
> `test_live_deploy.py`. Zostáva: stroj so zmazaným spoolom bežiacej inštancie pozíciu nepozná.

**M-HUB-4 (P2) Hub ticho zahadzuje udalosti, ktoré nevie validovať, a agent aj tak posunie kurzor.**
`live/store.py:263–266` bez logu a počítadla; `live/shipper.py:94–99` potvrdí vždy. Hub starší než
schéma platformy (nový druh udalosti) ich stratí natrvalo. *Oprava:* vracať `rejected` s dôvodmi,
agent kurzor podrží alebo riadok odloží do karantény.

**M-HUB-5 (P2) `POST /api/jobs` nie je idempotentný.** `hub/client.py:210–219` opakuje každú metódu
raz a `webapp/cli/remote.py:179–181` zadáva sweep holým cyklom. Timeout po prijatí hubom = duplicitný
výpočet; chyba pri k-tom bode nechá predošlé zadania osirelé (a podľa N-HUB-11 navždy). *Oprava:*
`request_id` od klienta, ktorý hub deduplikuje.

**M-HUB-6 (P2) ✔ Trvalá 4xx pri dávke spoolu sa opakuje donekonečna.** `live/shipper.py:84–87`
berie každú výnimku ako dočasnú; dávka sa síce zmenšuje, ale kurzor sa nepohne a alarm nie je.
*Oprava:* pri 4xx (okrem 401/408/429) dávku rozpoliť až po otrávený riadok a ten dať do karantény;
strážca nech hlási vek `ship.last_error`.

> **Stav 10. 11. 2026: M-HUB-4, 5, 6 a časť N-HUB-13 sú opravené.** Hub odmietnuté udalosti počíta a hlási
> (`rejected` v odpovedi, `live_events_rejected` v logu, `rejected_total` v štatistikách aj u agenta); kurzor
> sa nedrží, lebo spool na disku ostáva a dá sa poslať znova. Trvalo odmietanú dávku (400/413/422) shipper
> delí až po jednu udalosť a tú odloží do `poison.jsonl`. Zadanie výpočtu nesie `request_id`, hub podľa neho
> vráti už založený výpočet a klient prechodnú chybu skúsi trikrát s tým istým id. Heartbeat agenta a čakanie
> na výsledok majú pri výpadku rastúcu pauzu s rozptylom ±20 % (agent najviac 15 s, pod `agent_timeout` hubu);
> headless agent sa pri Ctrl+C odhlási. **Ostáva:** SIGTERM headless agenta, upozornenie strážcu na vek
> `ship.last_error`, čas platnosti nevyzdvihnutých výsledkov (N-HUB-11), M-HUB-7 až 11.

**M-HUB-7 (P2, predpoklad) Telegram 409 vypne príkazy do reštartu.** `agent_plugins/telegram/service.py:1019–1022`
nastaví `disabled` natrvalo; ak je 409 prechodná (po výpadku siete — neoverené), `/pause` a `/flatten`
zmiznú len s riadkom v logu.

**M-HUB-8 (P3) Heartbeat môže sám presiahnuť 45 s limit agenta.** 30 s timeout + 3×5 s connect
(`hub/client.py:89–90, 112`); `tick()` navyše každé 3 s spúšťa `git rev-parse` (`agent.py:689`) a
`_live_body` robí scandir celého spoolu (`agent.py:575`). *Oprava:* timeout ~10 s, verziu cachovať.

**M-HUB-9 (P3) Zrkadlo webapp po resete živej DB hubu ticho stojí.** `webapp/api/live.py:182–193`
kľúčuje kurzor len adresou hubu.

**M-HUB-10 (P3) Vlákna agenta nikto nestráži.** `agent.py:272–285` ich spustí raz; pokazený
`agent_state.json` alebo `cursor.json` sa ticho stane prázdnym (`config.py:184–185`, `spool.py:110–111`),
čo zabudne `computing` alebo pošle celý spool znova.

**M-HUB-11 (P3, architektúra) Plugin strážcu obchádza kontrakt.** `hub/plugins/watchdog/plugin.py:54–55`
siaha na `hub._lock` a `hub.agents` namiesto `PluginContext`. Reload pluginu nemá návrat: po zlyhanom
importe ostane plugin vypnutý, lebo starý je už zrušený (`hub/plugins/__init__.py:186–197`). Mená
stratégií sa v kóde hubu nenašli.

### 4.4 Webapp

**M-WEB-1 (P1) ✔ Otvorená karta Live zablokuje shutdown hook.** `__main__.py:162` volá `uvicorn.run`
bez `timeout_graceful_shutdown`; uvicorn čaká na zatvorenie spojení a až potom volá lifespan shutdown,
pri vynútenom konci ho preskočí. SSE stream z `api/live.py:534–547` sa sám neukončí. Ctrl+C s otvorenou
kartou Live visí, druhé Ctrl+C preskočí `runner.shutdown` aj `_hub_bye` — Freqtrade sirota a beh bez
`run.json`, teda pôvodný N-WEB-1. Poradie v uvicorne je z čítania jeho zdroja, nespúšťané.
*Oprava:* `timeout_graceful_shutdown=5`, príznak „closing" v SSE generátore, `atexit` ako záloha.

> **Stav 10. 11. 2026: M-WEB-1, 2 a 6 sú opravené.** Spúšťač drží `uvicorn.Server` s
> `timeout_graceful_shutdown=5`, SSE karty Live končí pri `server.should_exit` a `runner.shutdown` je aj v
> `atexit`. Overené na skutočnom uvicorne s otvoreným streamom: s príznakom server skončil za 0,3 s, len
> s časovým limitom za 5,3 s, shutdown hook zbehol v oboch prípadoch. Priamy beh z CLI pri Ctrl+C volá
> `runner.shutdown`. Pred auto-reštartom sa fronta zavrie (`RunnerClosed`, API 422) a skontroluje znova.
> Neoverené ručne: skutočné Ctrl+C v konzole a druhé Ctrl+C (vynútený koniec → `atexit`).

**M-WEB-2 (P2) Priamy beh z CLI nemá shutdown.** `cli/run.py:176–186`: Ctrl+C ukončí CLI, Freqtrade
beží ďalej.

**M-WEB-3 (P2) ✔ `/api/catalog` skladá všetko nanovo pri každom volaní.** `api/catalog.py:171–227`:
`store.all()`, `profile_info` pre 96 stratégií (637 JSON profilov) a pre každú vysvetlivka,
`ANALYTIKA.md`, `run.json` a `trades.json` najlepšieho behu. Len profily a dokumenty: 4,3 s na studenom
disku, 0,3 s na teplom. *Oprava:* cache s kľúčom (počet a max id v indexe, verzia meta, verzia výberu),
krivku najlepšieho behu lenivo.

**M-WEB-4 (P2) ✔ Okno hodnotenia načíta celú históriu na každý klik.** `api/catalog.py:234` →
`catalog_report.py:325, 330`; `store.of_strategy(key)` už existuje (`store.py:385`).

**M-WEB-5 (P2) ✔ `index.sync()` robí plnú prácu pri každom dopyte.** `index.py:253–291`: scandir
celého `runs/` a `SELECT` všetkých riadkov pod zámkom; `_synced` sa nastaví (`:290`), ale nikde nečíta.
Detail hyperoptu ho volá trikrát. *Oprava:* preskočiť sync mladší než 1–2 s; stĺpce `batch_kind`,
`batch_id` s indexom.

> **Stav 10. 11. 2026: M-WEB-3, 4, 5 a M-HUB-1 sú opravené.** Katalóg sa skladá len pri zmene vstupov (odtlačok
> z indexu histórie, výberu a `stat` profilov a dokumentov): na skutočnej histórii (3 889 behov) skladanie
> 2,8 s, odpoveď z cache 32 ms. Okno hodnotenia číta `store.of_strategy` (52 ms namiesto 223 ms). `index.sync`
> má rýchlu cestu, keď sa nezmenil zoznam adresárov ani `PRAGMA data_version` (9 ms, bez čítania všetkých
> riadkov) — časový limit som zavrhol, lebo by porušil pravidlo „index odpovedá to isté čo súbory". Odtlačok
> stavu hubu už neobsahuje premenlivú časť `live` (čas hlásenia, inštancie, odosielanie), takže heartbeat
> zapisuje `state.json` najviac raz za 5 s; drivery a stav kódu z `live` idú na disk ďalej hneď. **Ostáva:**
> stĺpce `batch_kind`/`batch_id` v indexe (N-WEB-8), zápis stavu hubu mimo zámku (zvyšok N-HUB-7), dokumenty
> meraní čítané pri každom hodnotení.

**M-WEB-6 (P3) Auto-reštart má okno bez ochrany.** `__main__.py:78–85`: medzi kontrolou fronty a
`os.execv` beží `_hub_bye` až 15 s; beh zadaný v tom čase zanikne.

**M-WEB-7 (P3) Frontend.** Fronta pri prázdnom stave prestane pollovať, takže beh z CLI alebo z hubu
sa neukáže (`queue_hub.js:33–37`); zrušenie a mazanie behu bez ošetrenia chyby (`queue_hub.js:59`,
`main.js:126–129`).

**M-WEB-8 (P3) CLI berie HTTP chybu ako výpadok.** `cli/run.py:159`: `HTTPError` je podtrieda
`URLError`, takže 404/500 znamená 5 minút čakania namiesto chyby.

**M-WEB-9 (P3) ✔ Zrušenie čakajúceho behu nie je pod zámkom.** `runner.py:190–200` vs. `:273–278`.

**M-WEB-10 (P3, architektúra) ✔ Predloha C# portu sa háda z mena.** `api/catalog.py:158–159`
(`endswith("eod")` / `"net"`), zrkadlovo `settings.js:576–580`; patrí do `StrategySpec` ako `base_key`.
`"ibs"` ako default je na ~25 miestach namiesto jednej konštanty a `demo_breakout` chýba
v `STRATEGIA_TRH_TYP` (jediná z 96).

## 5. Vylepšenia nad rámec opráv

1. **Jedna pravda o stave orderu.** NT, EA a exekútor majú tri implementácie toho istého automatu
   (čakajúci → vyplnený → chránený → zatvorený) a každá má inú podmnožinu opráv. Tabuľka prechodov
   v jednom dokumente a rovnaké názvy stavov by zabránili tomu, aby sa K1 opravil na jednom mieste
   z troch.
2. **Simulátor porúch adaptérov.** Falošný Account/broker s rejektmi, neskorými výplňami a výpadkami.
   Žiadny z nálezov M-LIVE nie je dnes pokrytý testom a parita bar po bare ich nenájde, lebo sa týka
   signálov, nie exekúcie.
3. **Spoločný čas a seansa v jadre.** Cachovaný prevod na čas New Yorku a RTH so skrátenými dňami
   namiesto 37 kópií; súčasne zrýchli enginy a zavrie M-CORE-8.
4. **Emulátor: m1 rozrezať raz.** `bars_from_frame` filtruje celý m1 4–5× na beh
   (`emulator.py:238, 239, 248, 257`); `lookahead.cut_test` púšťa emuláciu 11× a `robust` 10× na profil.
   Jeden `searchsorted` a zdieľané bary.
5. **Jeden poller na frontende** s backoffom, zastavením pri 404 a viditeľnou chybou pre frontu, sweep,
   hyperopt a maticu.
6. **Dátumová kontrola pri štarte živej stratégie**: koniec pokrytia kalendára, vek profilu, verzia
   DLL vs. commit — jedna `preflight` správa do hubu namiesto tichých degradácií.

## 6. Čo tento audit nepokrýva

Sada testov a build C# sa nepúšťali. Hlbšie nečítané: `tester/livesim.py`, vnútro `tester/livedata.py`,
`tradebot/live/bridge.py`, `routes.py`, `drivers/*`, väčšina tela Telegram služby, `hyperopt_job.py`,
`api/hub.py`, `diversify.js`, `livediv.js`, `strategy_report.js`. Zo stratégií len vzorka piatich nových.
Nálezy routingu H1–H6 a N-WEB-18 ostali neoverené. Správnosť pravidiel stratégií a ich ziskovosť
riešia [AUDIT_strategie_2026-11-07.md](AUDIT_strategie_2026-11-07.md) a
[AUDIT_lookahead_2026-11-09.md](AUDIT_lookahead_2026-11-09.md).
