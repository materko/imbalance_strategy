# Smerovanie príkazov: stratégia v NinjaTraderi, obchody v MetaTraderi 5 (návrh)

Stav (26. 10. 2026): **fáza 1 hotová** — protokol v jadre (`csharp/TradeBot.Core/Bridge.cs`), fasáda
`StaticHost.Bridge*` pre MT5, `OrderIntent.Life` s EOD obalom, testy `tester/tests/test_bridge.py`.
Exekútor v MT5, strana NinjaTradera, hub a webapp ešte nie sú (fázy 2–5 nižšie). Cieľ: pri každom živom nasadení si zvoliť, kde idú
ordery — **na ten istý účet, na ktorom stratégia beží** (dnešné správanie), alebo **remote** na iný
terminál na tom istom stroji, dnes MT5. Stratégia (engine, bary, zóny, kresby, telemetria) ostáva
v NinjaTraderi na dátach, na ktorých bola testovaná; MT5 je len vykonávač.

```
NinjaTrader 8 (AddOn LiveInstance)                         MetaTrader 5 (jeden terminál = jeden účet)
  BarsRequest MNQ 12-26 → C# engine → OrderIntent
        │                                                    TradeBotExecutor (EA na jednom grafe)
        ├─ route = local → Account.CreateOrder (dnes)          │  ┌ obchoduje ľubovoľný symbol účtu
        └─ route = mt5   → Bridge (TradeBot.Core)              │  │ (NAS100, XAUUSD, US500 …)
                              │                                 │  │
             Common\Files\TradeBot\bridge\<inštancia>\         │  │
                 route.json  (kam, symbol, mapovanie)  ───────►│  │
                 cmd.jsonl   (príkazy, NT píše)        ───────►│  │ CTrade → broker
                 evt.jsonl   (fily, stavy, MT5 píše)   ◄───────│  ┘
                 nt.hb / Common\Files\TradeBot\exec\<účet>.hb.json (živosť oboch strán)
```

## Jeden exekútor na účet, nie na inštrument

Zistené (MQL5, vlastnosti terminálu):

- EA pripnutý na **jeden** graf smie obchodovať **akýkoľvek symbol** účtu: `CTrade` /
  `OrderSend` berie symbol ako parameter, symbol stačí pridať do Market Watch (`SymbolSelect`).
  Ceny iných symbolov dá `SymbolInfoTick`, špecifikácie `SymbolInfoDouble/Integer`.
- `OnTradeTransaction` dostáva **všetky** transakcie účtu, nielen symbolu grafu. Vlastné ordery
  sa rozlíšia magic číslom a ticketom (ako dnes v `TradeBotEA.mqh`).
- `OnTick` chodí len za symbol grafu. Exekútor preto nebeží na tikoch, ale na `EventSetMillisecondTimer(50)`.
- Jeden terminál je naraz prihlásený do **jedného** účtu. Dva MT5 účty sú dva terminály, a teda
  dva exekútory. To už MT5 driver robí („jeden účet = jedna inštancia terminálu“, [LIVE.md](LIVE.md)).

**Záver: jeden `TradeBotExecutor` na MT5 účet** obslúži všetky NT inštancie a všetky symboly, ktoré
na ten účet smerujú. Graf, na ktorom sedí, je jedno (driver dá prvý mapovaný symbol, M1).

## Názvy

| čo | meno | prečo |
|---|---|---|
| tenký EA v MT5 | **`TradeBotExecutor`** (po slovensky *exekútor*), šablóna `deploy/mt5/TradeBotExecutor.mq5` | nič nepočíta, len vykoná; nezamení sa s EA stratégií (`IBSNet.mq5` …) |
| voľba v nasadení | **`route`** (smerovanie): `local` / `mt5` | rovnaké slovo v hube, webapp aj v NT |
| kanál medzi nimi | **bridge** (`TradeBot.Core/Bridge.cs`), adresár `bridge\<inštancia>\` | jeden C# kód pre obe strany |
| identita exekútora | `mt5exec_<login>-<server>` (ako id inštancie, [LIVE.md](LIVE.md), „Identita“) | NT podľa nej overí, že hovorí so správnym účtom |

Alternatíva k menu: `TradeBotRelay`. Navrhujem *Executor*, lebo relay naznačuje, že správy len
preposiela. Tento EA však drží aj ochranu pozície (SL u brokera, strážca SL).

## Kde sa smerovanie volí: v nasadení, nie v profile stratégie

Profil (`tradebot/strategies/<kľúč>/configs`, `config_hash`) je config enginu. Ten istý profil
beží v backteste, v parite aj naživo. Kam idú ordery, je vec **nasadenia** (deployment v hube, [LIVE.md](LIVE.md), fáza 2b).
Tak sa ten istý profil dá nasadiť raz lokálne a raz cez MT5 bez kópie. Vo formulári „Nasadiť“ to
vyzerá ako voľba v profile:

```
Obchodovať:  ( ) tu — na účte nasadenia (Sim101 / Apex …)
             (•) cez MT5 exekútor   účet: [ftmo-100k ▾]   symbol: [US100.cash ▾]   objem: [podľa hodnoty bodu ▾]
```

Nové pole deploymentu (hub `live.sqlite`, `tradebot/live/deploy.py`):

```json
"route": null                                   // = local, dnešné správanie
"route": {
  "via": "mt5",
  "account": "ftmo-100k",                       // id MT5 účtu v hube; musí byť na tom istom stroji (agent)
  "symbol": "US100.cash",                       // symbol u brokera; prázdne = z mapovania nižšie
  "price": "basis",                             // ako prepočítať ceny (nižšie)
  "scale": 1.0,                                 // pomer cien MT5 / NT (1 pre NQ↔NAS100, MGC↔XAUUSD)
  "qty": {"mode": "value"}                      // alebo {"mode": "fixed", "lots": 0.5} na kontrakt
}
```

`route` je ako stratégia, symbol a TF súčasť identity nasadenia (`PATCH` ho nemení; iné smerovanie =
nové nasadenie), lebo prepnutie s otvorenou pozíciou by ju nechalo na jednom účte a ďalší vstup poslalo na druhý.

## Mapovanie inštrumentov

Tri vrstvy, každá prepíše predošlú:

1. **Predvolená tabuľka v repe** (`tradebot/live/routes.py`, vedľa `symbols.py`): koreň CME kontraktu →
   meno CFD a mierka.

   | NT (koreň) | MT5 (meno CFD) | scale |
   |---|---|---|
   | `MNQ`, `NQ` | `NAS100` | 1 |
   | `MES`, `ES` | `US500` | 1 |
   | `MYM`, `YM` | `US30` | 1 |
   | `M2K`, `RTY` | `US2000` | 1 |
   | `MGC`, `GC` | `XAUUSD` | 1 |
   | `M6E`, `6E` | `EURUSD` | 1 |

2. **Aliasy brokera pri MT5 účte v hube** (nové pole účtu `symbols`, napr. `{"NAS100": "US100.cash",
   "XAUUSD": "XAUUSD.r"}`). Každý broker volá CFD inak (FTMO `US100.cash`, IC Markets `USTEC`).
   Nastaví sa raz pre účet a potom platí pre všetky nasadenia.
3. **`route.symbol` v nasadení**, keď treba niečo výnimočné.

Exekútor v heartbeate hlási **zoznam symbolov účtu so špecifikáciou** (tick, hodnota ticku za lot,
minimum a krok objemu, `trade_mode`). Webapp z neho robí rozbaľovací zoznam a hub odmietne nasadenie
na symbol, ktorý účet nemá (422).

### Ceny: futures ≠ CFD

NQ a NAS100 sa líšia o **basis** (úroky, dividendy do expirácie, bid/ask CFD), a ten sa mení. Absolútne
ceny z enginu (`e`, `sl`, `tp`) preto nejdú do MT5 priamo:

- Každý príkaz nesie `ref` = poslednú cenu NT inštrumentu v čase príkazu.
- Exekútor pri vykonaní: `mt5 = mid_MT5_teraz + (cena − ref) × scale`, zaokrúhlené na tick symbolu.
  **Vzdialenosti od aktuálnej ceny ostávajú zachované**, teda aj limitka „5 bodov pod trhom“ a
  SL „20 bodov pod vstupom“.
- **SL/TP po vyplnení** (`price: "basis"`, predvolené): exekútor ich po fille prekotví na **skutočnú
  cenu fillu** (`fill ± pôvodná vzdialenosť`). Sklz na CFD tak nezmení riziko obchodu v bodoch.
- Trailing (`a: modify`) sa prepočíta tým istým spôsobom s `ref` v čase posunu.
- `price: "same"` = bez prepočtu, pre prípad, že NT aj MT5 obchodujú ten istý inštrument (napr. MT5
  broker s CME futures).

Fill sa vracia do NT s **oboma cenami**: `price` (MT5) a `price_nt` (spätne cez basis). Engine a
telemetria NT pracujú v cenách NT. Webapp ukáže obe a sklz.

### Objem

- `qty.mode = "value"` (predvolené): `loty = kontrakty × PointValue_NT / (hodnota bodu za 1 lot v MT5)`,
  zaokrúhlené **nadol** na krok objemu. MNQ (2 $/bod) na NAS100 s 1 $/bod/lot = 2 loty na kontrakt.
  Riziko v dolároch je potom rovnaké ako v backteste.
- `qty.mode = "fixed"`: `lots` lotov na kontrakt.
- Vyjde pod minimum objemu → príkaz sa **odmietne** (`evt reject`, `note error`), nezaokrúhli sa nahor.

## Protokol (JSONL v `Common\Files\TradeBot\bridge\<inštancia>\`)

Súbory, nie sieť: rovnaký princíp ako spool a control ([LIVE.md](LIVE.md)). Prečo:

- obe platformy sú na jednom stroji;
- súbory prežijú pád ktorejkoľvek strany (nič sa nestratí, po návrate sa dočíta od kurzora);
- dajú sa čítať a prehrať pri ladení;
- MQL5 sieť (`WebRequest`) nechceme.

Zápis aj čítanie robí **C# `Bridge` v `TradeBot.Core`**. NinjaTrader ho má zo zdrojákov (`install`
kopíruje jadro) a MT5 ho volá cez `StaticHost` (`BridgeOpen/Poll/Emit/Heartbeat`, fasáda verzie 6).
Protokol je teda napísaný raz a otestovaný v Pythone cez fasádu ako `test_mt5_static_host.py`.

| súbor | píše | obsah |
|---|---|---|
| `route.json` | NT pri štarte inštancie | `to` (id exekútora), `symbol`, `price`, `scale`, `qty`, `magic` (z id nasadenia), `nt_symbol`, `nt_point_value`, `nt_tick` |
| `cmd.jsonl` | NT, append | `{"seq", "t", "cid", "a": "entry"/"cancel"/"close"/"modify"/"flatten"/"sync", "id", "dir", "ot", "p": {e, sl, tp, q, tr}, "life": {…}, "ref", "exp"}` |
| `evt.jsonl` | exekútor, append | `{"seq", "t", "cid", "k": "ack"/"reject"/"placed"/"fill"/"modified"/"cancelled"/"closed"/"snapshot", "id", "price", "price_nt", "qty", "lots", "exit", "err"}` |
| `nt.hb` | NT, každú 1 s | `{t, session, mode}` (živosť stratégie pre `on_master_lost`) |
| `exec\mt5exec_<login>-<server>.hb.json` | exekútor, každú 1 s | `{t, v, login, server, margin_mode, connected, trade_allowed, symbols:[…], routes:[…]}` |
| `exec\…state.json` | exekútor | spracované `seq` za každú route, `cid → ticket`, otvorené pozície route (pre reštart) |

Pravidlá:

- **Idempotencia:** `cid` (id príkazu) sa vykoná najviac raz, aj po reštarte terminálu (stav na disku).
- **Doručenie vstupu:** `entry` má `exp`, termín, do ktorého sa príkaz smie **odoslať brokerovi**
  (market: 10 s, limit/stop: koniec baru + 1 TF). Neskorší príkaz exekútor odmietne (`reject
  expired`), napríklad keď MT5 hodinu nebežal a market vstup by išiel za úplne inú cenu. Toto nie je
  životnosť orderu (tú má `life`, nižšie). `cancel`, `close`, `modify` a `flatten` termín nemajú.
- **Ochrana u brokera:** vstup ide so SL/TP priamo v orderi (MT5 pending order nesie `sl/tp`, ktoré
  platia po vyplnení). Pozícia teda nie je ani chvíľu bez stopu, aj keď NT medzitým spadne.
  Strážca SL (dnes v `TradeBotEA.mqh`) beží v exekútore na každej route.
- **Zdroj pravdy o pozícii** je MT5. NT pri štarte pošle `sync` a exekútor vráti `snapshot`
  (pozície a ordery route podľa magic). Tým sa nahradí `RestoreState` voči NT účtu.
- **Len hedging účet.** Každý vstup je vlastná pozícia so SL/TP na nej. Netting exekútor nepodporuje:
  hlási ho v hb (`margin_mode`) a NT dá stav `netting_unsupported`.
- **Po návrate spojenia NT nič nepredpokladá.** Prvý príkaz po obnovení `nt.hb` (aj po reštarte NT) je
  `sync`. Exekútor vráti `snapshot`: čo je na účte teraz, a **všetko, čo sa medzitým stalo** (fily,
  zrušenia a zatvorenia podľa `life`, každé s dôvodom a časom). NT to zapíše do spoolu ako fily a
  engine dostane skutočný stav. Netvári sa, že všetko beží, ak to tak nie je.

### Order, ktorý vie fungovať sám

Exekútor **nič neruší preto, že NT zmizol.** Čakajúce vstupy aj pozície bežia ďalej a čakajú na návrat
NT. Aby sa order nestal sirotou, nesie od začiatku **celý svoj život**: kedy prestane platiť a kedy
sa má pozícia zavrieť. Exekútor to vykoná sám, či NT beží, alebo nie.

| čo order nesie | odkiaľ to NT vie | čo exekútor robí sám |
|---|---|---|
| SL, TP | `TradePlan` (dnes) | sú priamo v orderi u brokera |
| trailing (aktivácia, odstup) | `TradePlan.Trailing` (dnes) | kým NT žije, posúva stop NT (na zatvorení svojho baru, ako v backteste). Keď je `nt.hb` starý, exekútor posúva sám na zatvorení 1m baru symbolu MT5, nikdy nie späť |
| `life.cancel_at`: dokedy platí čakajúci vstup | timeout stratégie (`limitka nevyplnená`, `EXPIRED`, `retest nevyplnený` …) | o tomto čase zruší nevyplnený vstup |
| `life.close_at`: absolútny čas zatvorenia | koniec seansy (`tb_session_end`), EOD 15:59 NY (`EodCloseEngine`, `IClockFlatten`) | o tomto čase zatvorí pozíciu a zruší čakajúci vstup |
| `life.hold_ms`: najdlhšie držanie od fillu | `maxHoldHours`, „časový exit“, „zavretie v čase“ | `fill + hold_ms` zatvorí trhom |

Každý order má aspoň `close_at` = koniec seansy inštrumentu. Ten pozná adaptér vždy, takže žiadny order
nebeží donekonečna. Termíny z `life` sa vykonajú s oneskorením **5 s**. Keď NT žije, jeho vlastný
`cancel`/`close` príde skôr (na zatvorení baru, presne ako v backteste) a termín exekútora sa už
nemá čoho chytiť. Exekútor je teda len poistka, ktorá nezmení obchody oproti backtestu.

**Čo sám nevie:** výstupy závislé od ceny alebo indikátorov na dátach NT. Napríklad „návrat cez EMA“,
„prerazenie VWAP proti obchodu“, OCO dvoch vstupov alebo re-entry. Tie počíta len engine na baroch NT.
Počas výpadku pozíciu chránia SL/TP (a trailing) a `close_at`/`hold_ms`. Pri `sync` po návrate engine
zistí, že výstup mal nastať, a pošle `close` hneď.

**Zmena kontraktu enginu (hotové):** `OrderIntent` má voliteľné `Life` (`OrderLife`: `CancelAtMs`,
`CloseAtMs`, `HoldMs`). Na backtest nemá vplyv. Do JSON zámeru (`OnBar`, spool `order`) ide ako
`"life": {"cancel_at", "close_at", "hold_ms"}`, a to len s nastavenými poľami. Python predloha ho nemá,
lebo naživo bežia len C# enginy. Most do Freqtrade ho pri čítaní zahodí, takže parita sa nemení.
EOD obal (`EodCloseEngine`, kópie `<kľúč>eod`) dáva každému vstupu `close_at` = najbližších
15:58:30 New York po zatvorení baru (`NextClockCloseMs`, bez sobôt a nedieľ). Je to ten istý čas,
v ktorom zatvára živý adaptér podľa hodín (`IClockFlatten`). Ostatné stratégie budú `Life` plniť
postupne. Kým ho nemajú, order nesie SL/TP, trailing a koniec seansy, ktorý doplní adaptér (fáza 3).

### Živosť: NT musí hlásiť, či exekútor vidí

NT inštancia každú sekundu vyhodnotí stav route (z hb exekútora a z `route` v ňom):

| stav | čo znamená | čo NT robí |
|---|---|---|
| `ok` | hb < 3 s, správny login/server, terminál pripojený, AutoTrading povolený, symbol obchodovateľný, route prijatá | obchoduje |
| `no_executor` | hb súbor neexistuje | vstupy neposiela (ako `paused`), `cancel`/`close` čakajú v `cmd.jsonl` |
| `stale` | hb starší než 3 s (MT5 spadol, EA odstránený) | to isté |
| `disconnected` / `trade_disabled` | terminál nemá spojenie alebo vypnutý AutoTrading | to isté |
| `symbol_missing` / `account_mismatch` | mapovanie nesedí | to isté + `note error` hneď po štarte |

Každá zmena stavu ide do spoolu ako `note` (`warn`/`error` → Telegram ako dnes) a do `hb` ako pole
`route`. Webapp to ukáže čipom pri nasadení („MT5 exekútor: ok“ / „nevidím exekútor“). Druhá strana
je rovnaká: exekútor pri `nt.hb` staršom než 30 s zapíše `note` a prepne route do režimu
„NT preč“. Nič nezruší, len prevezme trailing a ďalej stráži `life` (vyššie). Pri návrate NT čaká na `sync`.

## Čo sa kde zmení

| miesto | zmena |
|---|---|
| `csharp/TradeBot.Core/Bridge.cs` (nový) | zápis/čítanie JSONL s kurzormi, hb, `route.json`, prepočet cien a objemu (čisté funkcie, testovateľné) |
| `csharp/TradeBot.Core/StaticHost.cs` | `Bridge*` metódy pre MQL5, `Version() = 6` |
| `tradebot/adapters/ninjatrader/TradeBotLiveInstance.cs` | vrstva vykonávania za rozhraním: `NtAccountExecution` (dnešný kód: `CreateOrder`, OCO SL/TP, `ExecutionUpdate`, `RestoreState`) a `Mt5RouteExecution` (bridge). Engine, bary, control, spool a „jedna pozícia naraz“ ostávajú spoločné |
| `tradebot/adapters/ninjatrader/TradeBotLiveAddOn.cs` | `route` z `deploy.json` do inštancie |
| `tradebot/adapters/mt5/TradeBotOrders.mqh` (nový) | z `TradeBotEA.mqh` sa vyberie vrstva orderov (Tracked, SendEntry, strážca SL, netting, párovanie dealov) parametrizovaná **symbolom a magic** namiesto `_Symbol`. EA stratégií ju používa ďalej bez zmeny správania (beh v Strategy Testeri proti Testeru musí dať to isté) |
| `csharp/TradeBot.Core/Orders.cs`, `EodClose.cs` | voliteľné `OrderIntent.Life`; obal `EodCloseEngine` ho plní 15:58:30 NY |
| `tradebot/adapters/mt5/TradeBotExecutor.mqh` + `deploy/mt5/TradeBotExecutor.mq5` (nové) | timer 50 ms, `Bridge` poll, `TradeBotOrders` na každú route, hb, termíny `life`, záložný trailing, `snapshot` |
| `tradebot/live/deploy.py`, hub API | pole `route` v nasadení, `symbols` (aliasy) v účte; validácia: MT5 účet na tom istom agentovi, symbol v hb exekútora |
| `tradebot/live/apply.py`, `drivers/mt5.py` | MT5 účet, na ktorý smeruje aspoň jedno NT nasadenie, dostane **automaticky** graf s `TradeBotExecutor` (jeden na účet); posledné odstránené = exekútor preč (až keď route nemá pozície) |
| `tradebot/live/drivers/ninjatrader.py` | `route` do `deploy.json` |
| `tradebot/live/routes.py` (nový) | predvolené mapovanie + aliasy + výber symbolu (ako `symbols.py`) |
| webapp karta Live | voľba „Obchodovať“ vo formulári Nasadiť, čip stavu route, obe ceny fillu |
| testy | `test_bridge.py` (protokol cez fasádu: idempotencia, expirácia, kurzory po reštarte, prepočet cien/objemu), `test_routes.py` (mapovanie), rozšírenie testov deploy/apply/driverov |

Chart Strategy `TradeBotStrategy.cs` smerovanie **nedostane**: nie je na živý účet (NINJATRADER.md).
Opačný smer (stratégia v MT5, ordery v NT) protokol zvládne, lebo je symetrický, ale nie je v rozsahu.

## Fázy

1. **Bridge v jadre + testy** (hotové 26. 10. 2026). `Bridge.cs` (`RouteSpec`, `RouteMath`, `RouteStatus`,
   `BridgeMaster`, `BridgeExecutor`), fasáda `StaticHost.Bridge*`, `OrderIntent.Life` s EOD obalom a
   `test_bridge.py`. Bez platforiem. Koniec seansy do `life.close_at` doplní adaptér až vo fáze 3.
2. **Exekútor v MT5.** Vybrať `TradeBotOrders.mqh` z EA (s overením, že EA dáva v Strategy Testeri to
   isté), napísať `TradeBotExecutor`, ručný test na demo účte: príkazy píše skript
   `python -m tradebot.adapters.mt5 bridge send …` namiesto NT (vstup, zrušenie, close, modify, reštart
   terminálu s otvorenou pozíciou, expirovaný príkaz).
3. **NT strana.** `Mt5RouteExecution` v AddOne, stav route, `sync` po štarte. Test: Sim101 dáta MNQ →
   MT5 demo NAS100.
4. **Hub, driver, webapp.** `route` v nasadení, aliasy v účte, automatický exekútor, formulár a čipy, Telegram.
5. **Overenie naživo a dokumentácia.** Týždeň na demo/prop skúške, porovnanie fillov NT (virtuálne)
   a MT5 (skutočné), sklz a basis. Doplniť [NINJATRADER.md](NINJATRADER.md), [MT5.md](MT5.md) a [LIVE.md](LIVE.md).

## Rozhodnuté (26. 10. 2026)

- **Účet MT5:** len hedging.
- **Objem:** podľa hodnoty bodu (`qty.mode = "value"`), aby bolo riziko v $ rovnaké ako v backteste.
- **Výpadok NT:** nič sa neruší, ani čakajúce vstupy. Order nesie svoj život (`life`), exekútor ho
  dodrží sám a po návrate NT najprv `sync`.
- **Časové výstupy** (koniec seansy, EOD 15:59 NY, max. držanie, timeout vstupu) idú s orderom a
  exekútor ich vie vykonať sám. Nemusí ísť o „poistku len pre EOD“.
- **NinjaTrader** pri route `mt5` slúži len na dáta. `Sim101` je len meno v id inštancie a ordery na
  ňom nebudú.
