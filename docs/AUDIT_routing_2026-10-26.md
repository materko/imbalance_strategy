# Audit smerovania príkazov: dáta v NinjaTraderi, ordery v MT5

Dátum: 26. 10. 2026. Auditovaný commit: `20e2d1de4` (`main`). Audit kódu fáz 1–4 z
[ROUTING.md](ROUTING.md) (jadro mosta, NT AddOn, MT5 exekútor, hub, drivery, webapp) z pohľadu
logiky, rýchlosti, spracovania chýb a programátorskej kvality. Nič z toho ešte nebežalo naživo
(fáza 5), takže nálezy sú z čítania kódu; čo sa dalo, je overené testom alebo odvodením s konkrétnym
scenárom. „Neisté“ znamená, že správanie platformy nie je z kódu jednoznačné.

## 1. Záver

Kostra je správna: protokol je napísaný raz v C# (`Bridge.cs`) a obe strany ho len volajú, príkazy
nesú `cid` a vybavené `cid` sú s potvrdeným offsetom na disku, JSONL sa číta len po celých
riadkoch, malé súbory sa píšu atomicky, SL/TP idú k brokerovi v orderi od prvej chvíle, order
nesie svoj `life` a exekútor pri výpadku NT nič neruší. Prekotvenie SL/TP na skutočný fill
drží riziko v bodoch. Kód je čistý C# 5, testy pokrývajú prepočty, idempotenciu a stavy route.

Pred nasadením naživo treba opraviť **sedem vecí, ktoré nechajú pozíciu bez dozoru alebo
zdvoja vstup** (§2, K1–K5 exekútora a V2–V3 NT strany) a **štyri v hube/driveri**, z ktorých jedna
(graf exekútora reštartuje MT5 terminál v každom kole, §4 H3) sa prejaví hneď pri prvom
nasadení na stroji so staršou inštaláciou EA. Zvyšok sú stredné a nízke veci: presnosť, spam
notifikácií, rozpory s dokumentom.

Poradie opráv, ktoré navrhujem: exekútor K1 + K3 + K4 + K5 (jedna zmena v `HandleEntry`,
`CancelEntry`, `Reconcile`), potom V1 exekútora (kotva `modify`), NT V2 + V3 + S1, hub H1 + H2,
driver H3. Až potom demo test podľa ROUTING.md.

## 2. MT5 exekútor (`tradebot/adapters/mt5/TradeBotExecutor.mqh`)

### Kritické — sirota alebo zlý stav pozície

| # | kde | čo | scenár |
|---|---|---|---|
| **K1** | `CancelEntry` 612 | `t == 0 \|\| OrderDelete(t) \|\| !OrderSelect(t)` berie *zmiznutý* pending order ako zrušený | limitka sa u brokera vyplní, `DEAL_ADD` ešte čaká za `OnTimer`, príde `cancel` (od NT, z `life`, z `flatten`); `OrderDelete` zlyhá, `OrderSelect` je false → `cancelled` + `RemoveOrder`. `OnTradeTransaction` už nenájde `XOrder` (651–661): **pozícia ostane otvorená bez trailingu, `life` a strážcu, NT ju má za zrušenú**. Treba `PositionSelectByTicket(t)` / `HistoryOrderGetInteger(ORDER_STATE) == FILLED` a prevziať ju ako fill |
| **K2** | `HandleEntry` 566, `Sent` 125 | len `DONE`/`PLACED` je úspech | market vstup s `DONE_PARTIAL` (10010) alebo timeout 10012, keď request prešiel: `reject` do NT, `AddOrder` sa nezavolá, deal sa nespáruje → sirota so SL/TP, NT bez pozície |
| **K3** | `Existing` 496–509, 545–553 | vracia aj ticket **pozície**, ale `o.filled` ostane false, `fill` sa neemituje | market vstup sa vyplní, terminál spadne pred `BridgeDone`, po reštarte do 10 s sa cid zopakuje: `placed "prevzaty po restarte"`, `Guards` 722 ho nechá (pozícia existuje), nikdy nie je `filled`; prvý `cancel` ho cez K1 zmaže a pozícia osirie |
| **K4** | `HandleEntry` 515–518 | `exp` a `state` sa kontrolujú pred `Existing`/`FindOrder` | limitka je u brokera, pád pred `Done`, reštart po `exp`: `reject expired`, GTC order beží ďalej; ak nebol v `orders.json`, je sirota bez `cancel_at` |
| **K5** | `OnTimer` 429–434 | `BridgeDone` (atomický `exec.state`) ide po každom príkaze, `SaveState` až po dávke | pád medzi nimi: cid hotový, order u brokera, v `orders.json` nie je; replay nepríde a `Reconcile` (240–301) ani `Snapshot` (477) neprehľadávajú brokera podľa magic → nikto ho neprevezme. `SaveState` pred `Done`; `Reconcile` adoptovať ordery/pozície s magic route |

### Vysoké

- **V1 `HandleModify` 590–598 — kotva je cena orderu, nie fill.** `ntFill = ntEntry + (fill − entry)/scale` a potom `Reanchor(fill, ntFill, …)` sa zjednoduší na `entry + (sl − ntEntry)·scale`. Prvotný SL je však prekotvený od fillu (`OnEntryFill` 679). Long so sklzom 3 b.: SL po fille 183, NT pošle trailing 81 → exekútor položí 182, **stop sa uvoľní**. `HandleModify` nemá „nikdy späť“ (má ho len `TrailOnMinute` 782); to isté po návrate NT, ktorý nevie o trailingu exekútora.
- **V2 `modified` 787 bez `price_nt`**, `Snapshot` dáva SL len v texte (488) — NT po návrate nepozná skutočný stop (vstup do V1).
- **V3 (neisté) `OnInit` 808–809** robí `LoadState → Reconcile` hneď. Ak pri štarte terminálu ešte nie sú pozície/história synchronizované, `Reconcile` vyhlási všetko za `cancelled "u brokera po restarte nie je"` (293–295) → hromadné siroty. `TimeTradeServer` pred pripojením môže dať zlý `fillMs`; `ACCOUNT_LOGIN == 0` by dalo id `mt5exec_0-` na celú reláciu. Driver terminál reštartuje pri každej zmene grafov, cesta je častá. Odložiť do `OnTimer` po `TERMINAL_CONNECTED`.
- **V4 `StaticHost.BridgeExecOpen` 441–455 bez zámku** — EA na dvoch grafoch = dva kurzory nad tým istým `cmd.jsonl`, každý príkaz dvakrát, dvaja píšu `orders.json`. **Duplicitné vstupy.** Odmietnuť druhú inštanciu s rovnakým id.
- **V5 čiastočný fill pending orderu 654** len pripočíta `openLots`, nič neemituje (NT nevie o objeme), zvyšok orderu ostane GTC: `cancel` sa ignoruje (447), `life` cancel platí len pre `!filled` → zvyšok sa vyplní kedykoľvek neskôr.

### Stredné

- 560–565: limit/stop, ktoré by sa v NT vyplnili hneď (limit nad trhom), broker odmietne (10015) → `reject`, obchod oproti backtestu chýba; chýba prepnutie na market.
- `Mid(sym) = 0` (bez kotácie po čerstvom `SymbolSelect`) dá v 529–533 nezmyselné ceny; `CheckRoute` overuje len hedging a trade mode. `SYMBOL_TRADE_STOPS_LEVEL`/freeze level sa nikde neposúvajú; `TrailOnMinute` 784 pri odmietnutí mlčí.
- `ClosePosition` 631–635 pri 10018 (trh zatvorený) píše `note error` každý pokus (max. raz za 60 s) donekonečna → cez NT Telegram spam. Requote/off quotes pri vstupe sa v rámci `exp` neopakujú.
- `WatchMasters` 402: `BridgeMasterAge` vráti pri chybe −2 a berie sa ako `lost` → falošný `warn` a na sekundu trailing exekútora.
- `Reconcile` pri fille počas výpadku neprekotví SL/TP, neberie `POSITION_SL` od brokera (EA to robí, `TradeBotEA.mqh:1760`), nedobehne `extreme`; výstupy z ešte otvorenej pozície sa neemitujú.
- Návrh: `cancel_at` dať aj brokerovi (`ORDER_TIME_SPECIFIED`) ako druhú poistku, dnes `life` platí len pri bežiacom termináli.

### Rýchlosť

- 50 ms `BridgePoll` na route = `File.Exists` + `FileStream` + `Length` v C# — v poriadku. Pri chybe však `Print` **každých 50 ms** (421).
- `RefreshRoutes` každé 2 s prechádza všetky adresáre `bridge\` a číta každý `route.json` (Bridge.cs 611–627), aj staré a cudzie; adresáre sa nikdy nemažú. Mŕtve route s `to` = tento exekútor sa pollujú ďalej a po každom štarte dostanú `warn`.
- Heartbeat: na každý symbol Market Watch 1 volanie DLL + 9× `SymbolInfo` (380–388); pri 100+ symboloch ~1000 volaní/s a veľký JSON, ktorý NT parsuje každú sekundu. Posielať len symboly route (+ pár na výber vo webapp) alebo celý zoznam raz za minútu.
- `nt.hb` sa číta 2× na route (400–401). `evt.jsonl`/`cmd.jsonl` rastú bez rotácie.

### Nízke

- `NowMs() = TimeGMT()*1000` (115) má sekundovú presnosť; `t` v hb, `exp`, `life` sú orezané — pri hraniciach 3 s (stale) a 10 s (`exp`) tesné. Použiť `Bridge.NowMs()`.
- Tickety v `orders.json` ako číslo cez `double` (185, 228); EA ich zámerne drží ako reťazce (`TradeBotEA.mqh:1577`).
- `TradeBotJson` prijme objekt/pole končiace čiarkou (141, 158). Dnes neškodné (celé riadky, atomické súbory). Úniky `CJson` som nenašiel.
- Prechodná chyba čítania `route.json` route vyradí (337–344) a vráti cez `ZeroMemory` (318–325) → reset `masterSeen`, `masterLost`, `lastM1`.
- Plán bez TP/SL (`null` → 0) dá `MapPrice(0, …)` zápornú cenu → broker odmietne (neisté, či to niektorý engine posiela).
- `XRoute.masterSession` sa píše, nečíta. Udalosť `closed` sa nikdy neemituje. ROUTING.md opisuje `exec\…state.json` s `cid → ticket`; skutočnosť je `bridge\<inst>\exec.state` + `exec\<id>.orders.json`.
- `StaticHost._lastError` je statický pre celý terminál — EA stratégií a exekútor si ho prepisujú.

## 3. NinjaTrader AddOn a jadro mosta (`TradeBotLiveInstance.cs`, `Bridge.cs`)

Nič nenecháva pozíciu bez stopu (SL/TP sú v orderi). Vysoké:

- **V1 `SubmitRemote` 2156 — `ref` je zatvorenie posledného baru.** Volá sa aj z `ReleaseParked` (1195–1204) na `fill out` uprostred baru, kým exekútor počíta od `mid` *teraz*. Long limit 100, posledný close 104, SL inej pozície padne pri 98: MT5 dostane `mid + (100 − 104)`, limitka je o 6 b. nižšie a nevyplní sa; pri opačnom pohybe BuyLimit nad trhom → `reject`, vstup preč. Lokálna vetva posiela absolútnu cenu, chyba je len pri route. `ref` = posledný tick NT.
- **V2 `BridgeMaster.Poll` (Bridge.cs 557–566) — kurzor sa uloží pred spracovaním a offset sa posúva v pamäti.** Výnimka z `AtomicWrite` kurzora (po 20 pokusoch, antivírus) zahodí prečítané riadky; pád NT medzi `Poll` a `SaveState` (416) ich stratí tiež. Stratený `fill in`: NT drží vstup ako `RemoteLive`, engine ho neskôr zruší (963–966), exekútor odpovie `ack "uz je vyplneny"`, ktorý NT ignoruje → pozícia v MT5 bez trailingu a výstupov enginu, `OwnNet = 0`, engine smie otvoriť ďalšiu (**dvojitá expozícia**). Kurzor ukladať až po spracovaní a `SaveState`.
- **V3 snapshot 2292–2299 zahodí platný vstup poslaný po `sync`.** `RouteTick` pošle `sync` (2108) a v tej istej iterácii `ProcessBars` pošle `entry`; snapshot ho neobsahuje, NT ho zahodí, potom príde `fill in` neznámeho vstupu → `Close "neznamy vstup"` (2215): **platný obchod sa hneď zavrie**. Nezahadzovať vstupy so `SentMs ≥ čas sync`.
- **V4 `Apply` 938–942 zahodí vstup pri každom stave ≠ `ok`**, aj pri jednom zlom meraní. Hb exekútora má sekundové `t` a 1 s periódu, rezerva do `StaleMs = 3000` je ~1 s; zaváhanie timera MT5 pri zatvorení baru = vstup sa nepošle a nezopakuje (odchýlka od backtestu). `exp` a kontrola stavu v exekútore (mqh 516–517) ho aj tak chránia; zahadzovať len pri trvalých stavoch (`account_mismatch`, `netting_unsupported`, `symbol_missing`), inak poslať.

Stredné:

- **S1 2222 `t.OpenQty += qty` na `fill in` bez kontroly `t.Filled`** — exekútor pošle `fill in` znova, ak spadne medzi `Emit` (675) a `SaveState` (662) → `OpenQty = 2`, `fill out` zníži na 1, pozícia „visí“: `HasOpenPosition` parkuje vstupy, close dostane „nič na zatvorenie“. Opraví až `pos` zo `sync`. Na `fill in` `=`, nie `+=`.
- **S2 1414–1430 `LastStop` sa nastaví hneď po zápise `modify`**, `reject` len zapíše note (2199–2203) → ďalší `modify` príde, až keď bude stop lepší než už „posunutý“; SL u brokera ostane na starej úrovni. Lokálna vetva to rieši (N-LIVE-10).
- **S3 `RouteMath.Lots` 139 — mena účtu.** `SYMBOL_TRADE_TICK_VALUE` je v mene účtu, `nt_point_value` v USD. EUR účet: riziko o kurz mimo; CZK účet (FTMO ho ponúka): ~23× menej lotov → pod minimom → každý vstup `reject`.
- **S4 jeden `try` 401–402 obaľuje heartbeat, status aj `Poll`**; chyba v `Heartbeat` preskočí aj čítanie udalostí; `Note("error", … + e)` posiela celý stack 4×/s bez obmedzenia → Telegram.
- **S5 strata `exec.state` (Bridge.cs 636–648)** prehrá celý `cmd.jsonl`: vstupy chráni `exp` a `Existing`, ale `flatten`/`close`/`modify` termín nemajú — staré `flatten` z control zavrie súčasné pozície.
- **S6 (neisté) rollover s pozíciou**: id inštancie aj bridge adresár sú bez expirácie, `RestoreRoute` vráti plán v cenách starého kontraktu, `CatchUpExtreme` a trailing (1408–1416) počítajú z nového → SL posunutý o roll spread. `OldContractCheck` je pri route vypnutý (414).

Nízke: `ReadShared` nechytá `UnauthorizedAccessException` (Bridge.cs 307–325; `AtomicWrite` áno); `ReleaseParked → SubmitRemote` obíde bránu stavu route (N2); výstupné qty `Math.Max(1, (int)Math.Round(qty))` (2207) pri čiastočnom fille 0,5 → banková 0 → 1; `JsonlLog.Append` 389–394 pri výnimke z `Flush` nezvýši `_seq` → ďalší príkaz dostane ten istý `cid` a exekútor ho preskočí; `SpoolBroker` pri route hlási `OwnNet()`, teda vieru NT, nie MT5 (stĺpec „u brokera“ je tautológia); `nt.hb` sa zapíše v `OpenRoute` (2083), ale `RequestSeries`/`Replay` môžu trvať >30 s → falošné „master lost“ pri štarte; `BridgeMaster.Flatten` NT nepoužíva; `ref` v `modify` exekútor ignoruje (ROUTING.md tvrdí opak); `exp` limitky je `now + TF`, nie „koniec baru + TF“; logy skladajú double cez aktuálnu kultúru; `MapPrice` nemá ochranu `scale ≤ 0` (`ToNtPrice` má); opakované `Entry` s tým istým id (949–956) exekútor odpovie `ack "vstup uz bezi"` a nový plán zahodí (neisté, či engine posiela).

`test_bridge.py` pokrýva prepočty, `LifeAction`, idempotenciu a kurzory cez reštart, `cid` po reštarte mastera, všetky stavy `Evaluate`, tvar hb, EOD `life`, CLI. Nepokrýva neukončený riadok JSONL, zlyhanie zápisu kurzora (V2), stratu `exec.state` (S5), poškodený koniec v `LastSeq`, `HandleRouteEvent` (nemá harness), menu účtu, súbežný prístup.

## 4. Hub, drivery, webapp (`tradebot/live/*`, `tester/webapp`)

Vysoké:

- **H1 route bez `to` potichu obchoduje na účte NinjaTradera.** `Deployment.route` vráti `None` bez `to` (`drivers/base.py:96–99`), NT driver zapíše záznam bez `route` (`drivers/ninjatrader.py:220–225`) a `test_live_routes.py:137` to výslovne vyžaduje. `to` zmizne, keď: `delete_account` blokuje len aktívne route (`deploy.py:510–512`), `update_deployment` pri `active: true` route neoverí (690–691), `_executors` pri chýbajúcom účte len `continue` (780–782). Scenár: NT nasadenie s route na `ftmo` deaktivujem, účet zmažem, nasadenie cez PATCH aktivujem → ordery idú na NT účet (napr. živý Apex) bez chyby. Route bez `to` = `error` nasadenia, nikdy lokálne.
- **H2 deaktivácia NT nasadenia s otvorenou pozíciou odoberie graf exekútora.** Exekútor je aktívny, kým je aktívne niektoré NT nasadenie (`deploy.py:785`); reconciler podrží NT inštanciu (`apply.py:315`, `_hold_open`), exekútora nie — `position_from_spool("mt5exec_…")` je `None`, lebo exekútor nemá spool (`update.py:62–63`). Podržaná NT inštancia posiela `close`/trailing do `cmd.jsonl` a nikto ich nevykoná, `life.close_at`/`hold_ms` (EOD 15:58:30) tiež nie; u brokera ostane len SL/TP. Rozpor s N-LIVE-15 a s „Order, ktorý vie fungovať sám“.
- **H3 graf exekútora reštartuje MT5 terminál v každom kole** (overené testom: 3 kolá `ensure_instance` = 3 štarty, 2 zavretia). Graf má `profile: "executor"`, ale `inputs: {}` (`mt5.py:625–628`), v `.chr` nie je `InpProfile`, na disku je `""`; `_profile_matches(reload=False)` porovnáva profil → `same` je vždy False. Nastane na stroji, kde `installed.json` nemá `profile_reload` (marker spred `20e2d1de4`); s `reload=True` sa to zakryje. Test exekútora `ensure_instance` vôbec nevolá. Oprava: grafu exekútora dať `profile: ""` alebo ho z porovnania profilu vynechať.

Stredné:

- **H4 platforma MT5 účtu s aktívnou route sa dá zmeniť** (`_account_agents` pozerá len vlastné nasadenia, `deploy.py:327–330, 441`; `live.js:1182` to pustí): `_executors` ďalej vyrába `exec-ftmo`, NT driver zapíše „inštanciu“ so stratégiou `executor` do `deploy.json`, AddOn ju neúspešne štartuje; `route.to` sa skladá z NT loginu.
- **H5 symbol grafu exekútora = `min(symbols)` zo všetkých route** (`deploy.py:786–794`), nikde neoverený. Preklep v jednej route pravdepodobne zhodí graf pre všetky route účtu (neisté, či MT5 graf s neznámym symbolom otvorí); route s abecedne menším symbolom zmení graf → reštart spoločného terminálu aj s EA stratégií. Kontrola 422 „symbol, ktorý účet nemá“ (ROUTING.md 105–107) **nie je implementovaná** — hub hb exekútora nevidí.
- **H6 chyby exekútora sa nikam nedostanú**: `report_applied` zahodí hlásenie k `exec-*` (nemá riadok v `deployments`, `deploy.py:812–814`); bez MT5 drivera/terminálu na stroji NT vidno len čip „exekútor nebeží“ bez dôvodu. Formulár ponúka stroje len podľa NT drivera (`live.js:1030`), nekontroluje `mt5` v `live.drivers`.

Nízke: alias na koreň futures (`{"MNQ": "USTEC"}`) sa pre známe korene ignoruje (`routes.py:72–78`, docstring tvrdí opak); aliasy v route zamrznú (`normalize_route` uloží výsledný symbol, PATCH ho nemení; ROUTING.md 102 sľubuje „platí pre všetky nasadenia“); `scale`/`lots` = `nan`/`inf` prejdú validáciou (`routes.py:111–130`, chýba `isfinite`; `inf` → `Infinity` v `deploy.json`, C# `Json` pozná len `NaN`); `upsert_account` existujúceho účtu volá `normalize_aliases` mimo `try` (`deploy.py:452`, `RouteError` → 500, dnes cez Pydantic nedosiahnuteľné); poškodený JSON v stĺpci `route` zhodí celý `desired_for_agent` (344); `executor_id` sedí s `Bridge.ExecutorId` pre číselný login, rozíde sa pri logine s nulou na začiatku a pri inej veľkosti písmen servera (`account_mismatch`) — žiadny test neporovnáva Python s C#; čip stavu berie `hb.route` aj zo starého pingu (`live.js:907–913`), mŕtva inštancia ukazuje zelené „ok“; `bridge.py` `execs`/`tail` volajú `_core()` aj keď len čítajú (bez pythonnet traceback), `send modify` bez `--sl`/`--tp` pošle prázdny modify.

Rýchlosť: `_executors` jeden SELECT účtu na routované nasadenie a `desired_for_agent` jeden na účet v každom heartbeate, `deployments()` N+1 na `applied` — pri desiatkach nasadení zanedbateľné. `position_from_spool` číta v každom kole celý spool každého neaktívneho nasadenia (`update.py:57–82`) — staršia vec.

### Rozpory kódu s ROUTING.md

- „Ten istý profil raz lokálne a raz cez MT5“ (r. 59): na tom istom NT účte, symbole a TF nejde — `instance_id` route neobsahuje, duplicita končí `Conflict`, NT nemá slot.
- Magic (r. 150) „z id nasadenia“: NT driver píše `magic: 0`, AddOn berie FNV-1a z id **inštancie** (`TradeBotLiveInstance.cs:2079`); MT5 EA berú `magic_for(deployment.id)`. Dve konvencie.
- Rozbaľovací zoznam symbolov z hb exekútora (r. 106): vo webapp voľný text (`index.html:527`), 422 chýba.
- „MT5 účet musí byť na tom istom stroji“ (r. 73) sa nevynucuje; exekútor ide na stroj NT (r. 240 to hovorí inak).
- `price` a `scale` sa vo formulári nedajú zadať (vždy `basis` a tabuľka).
- Duplicity: doplnenie defaultov route v `normalize_route` aj v `_entries` NT drivera; `"executor"` na troch miestach; `{login}-{server}` v `ACCOUNT_IDENTITY`, `executor_id`, `Mt5Driver.spool_account`; `PRICE_MODES`/`QTY_MODES` zvlášť v Pythone, C# a HTML.

### Chýbajúce testy

Reaktivácia po zmazaní MT5 účtu (H1); reconciler s exekútorom a podržanou NT inštanciou (H2); `Mt5Driver.ensure_instance` s exekútorom, `reload=False` (H3); zmena platformy účtu (H4); `executor_id` proti `StaticHost.BridgeExecutorId`; migrácia DB bez `route`/`symbols`; API s route (422, aliasy cez PATCH); NaN/inf; alias na známy koreň.

## 5. Čo je v poriadku

`cid` = session + seq, `Done` s potvrdeným offsetom a `Inflight`, atomický hb, čítanie po celých riadkoch, `FileShare.ReadWrite|Delete` — protokol napísaný raz, idempotentný cez reštart oboch strán. SL/TP v orderi, fill párovaný podľa ticketu orderu/pozície (nie komentára), funguje pre všetky symboly účtu, cudzie dealy ignoruje. `life` ako čistá funkcia s odkladom 5 s. Strážca SL zavrie po 3 neúspechoch, zatváranie má backoff 2–60 s, záložný trailing nikdy späť. `normalize_route` kontroluje platformu, účet, `via`, `price`, `qty.mode`, kladné `lots`/`scale` (422); route sa cez PATCH nemení; migrácia stĺpcov je správna; zmena aliasov nemení `rev`; `route.to` sa dopočíta pri každom heartbeate. Dve NT nasadenia na ten istý MT5 účet a symbol majú rôzny magic (hedging). MT5 driver exekútorovi správne nepíše profil ani control. Výnimky pri udalostiach z MT5 sú izolované (2124–2125).
