# Feed: zdieľanie trhov medzi platformami (NinjaTrader 8 ⇄ MetaTrader 5 ⇄ ktokoľvek)

> **Stav: návrh, nič z toho ešte nie je implementované** (16. 10. 2026).
> Dokument opisuje, čo chceme postaviť a prečo takto.

## Čo chceme

Stratégia beží na **MT5** (napr. `NAS100` u CFD brokera), ale indikátor potrebuje **ďalšie
trhy**, ktoré MT5 broker nemá alebo ich má horšie — napríklad CME futures (`NQ`, `ES`, `RTY`,
`6E`, `ZN`…) z dátového feedu **NinjaTradera**. Príklady indikátorov: SMT divergencia
NQ vs. ES, korelácia / relatívna sila voči košu, filter podľa dolára alebo dlhopisov, volume
z futures pri obchodovaní CFD.

1. **Publisher** — adaptér v NinjaTraderi, kde nastavím zoznam trhov; ich bary publikuje.
2. **Odberateľ** — ktokoľvek: MT5 EA, NinjaTrader stratégia, Python (webapp, záznam, analýza).
   Publisher nevie a nezaujíma ho, kto číta.
3. **Opačný smer** — publisher v MT5 (trhy brokera MT5) a odberateľ v NinjaTraderi alebo inde.
   Formát a knižnica sú tie isté, mení sa len to, kto zapisuje.
4. Každý odberateľ si z publikovaných barov **poskladá vlastný TF** pre svoj indikátor
   (5m, 15m, 1h…) — publikuje sa len základ.
5. **Záznam pre budúce testy** — odberateľ, ktorý feed ukladá do feather súborov, a reader,
   ktorý ich v backteste dodá stratégii tak, ako by ich naživo dostala z feedu.

## Rozhodnuté

| | rozhodnutie |
|---|---|
| rozlíšenie | **1m uzavretý bar.** Tiky / bid-ask až keď ich bude potrebovať konkrétny indikátor — formát má na to miesto (`<symbol>\tick\`), dnes sa nerobí. |
| latencia | **do ~0,5 s** po zatvorení minúty stačí. Ako ísť nižšie: sekcia „Latencia". |
| kde dáta žijú | **len na tom istom stroji.** NinjaTrader aj MT5 bežia vždy na tom istom Windowse, feed ani záznam sa nikam neprenášajú — nejdú cez hub, ani do gitu (licencia dátového feedu NT). |
| zatvorený trh | **bar chýba úplne**, tak ako v archíve (sekcia „Keď trh stojí"). |
| rollover futures | **front-month bez úpravy cien** + príznak na bare rolloveru, ako `tester.bento_import` (sekcia „Rollover"). |

## Princípy (zhodné so zvyškom repozitára)

- **Publikuje sa len 1m uzavretý bar.** Vyšší TF si skladá odberateľ, a to rovnakým pravidlom ako
  `tradebot/core/candles.py` (v C# port s testom parity) — inak sa porovnanie backtestu a živého
  behu rozíde. Zhodné s pravidlom „vyšší TF sa z 1m skladá výhradne cez `candles.py`".
- **Čas = ms UTC otvorenia baru**, ako engine, spool aj fasáda MT5. NinjaTrader dáva čas
  zatvorenia v pásme z *Options → General*, MT5 čas servera — prepočet robí publisher, nie
  odberateľ.
- **Platforma píše len na lokálny disk**, nikdy do siete (ako live spool, [LIVE.md](LIVE.md)).
  Chyba feedu nezhodí obchodnú stratégiu, ani publisher, ani odberateľ.
- **Jadro ani adaptéry nepoznajú konkrétny trh ani indikátor menom.** Stratégia v configu
  deklaruje, aké série potrebuje; adaptér ich doručí. Tá istá deklarácia platí pre backtest
  (Freqtrade, emulátor MultiCharts) aj živý beh — stratégia sa píše pre všetky enginy naraz.
- **C# 5 bez NuGet, len BCL** (`tradebot/csharp/TradeBot.Core`), aby to preložil `csc.exe`, NinjaTrader aj
  Mono. MT5 to volá cez `StaticHost` (globálny namespace, len primitívne typy).

## Architektúra

```
 NinjaTrader 8                                   MetaTrader 5
 ┌──────────────────────────┐                    ┌──────────────────────────┐
 │ AddOn TradeBotFeedAddOn  │                    │ EA / skript FeedPublisher│   (F3, opačný smer)
 │  tiky → 1m podľa hodín   │                    │  tiky → 1m podľa hodín   │
 │  feed\publish_nt.json    │                    │  feed\publish_mt5.json   │
 └────────────┬─────────────┘                    └────────────┬─────────────┘
              │ TradeBot.Core FeedWriter                       │ StaticHost::FeedPublish*
              ▼                                                ▼
        %LOCALAPPDATA%\TradeBot\feed\<source>\<symbol>\1m\<yyyyMMdd>.bin   + manifest.json, meta.json
              │
              ├──► MT5 EA (stratégia)     StaticHost::FeedOpen/FeedRead → engine.FeedSeries(...)
              ├──► NT8 stratégia          TradeBot.Core FeedReader
              └──► Python                 tradebot/feed/  (status, dump, záznam do feather)
                                                   │
                                                   ▼
                                    data_feed\<source>\<NAME>-1m.<rok>.feather   (gitignored)
                                                   │
                                                   └──► backtest: ArchiveFeedSource → stratégia
```

### Prečo súbory a nie socket / pipe

| možnosť | + | − |
|---|---|---|
| **súbory (append-only) + signál/polling** | prežije pád ktorejkoľvek strany, odberateľ sa môže pripojiť kedykoľvek a dočítať históriu, ladí sa okom, rovnaký vzor ako spool a control súbor, nič netreba otvárať vo firewalle | bez signálu latencia = interval pollingu |
| memory-mapped file | latencia ~0 | nemá históriu, zložitejší zámok, po reštarte prázdny |
| named pipe / localhost TCP | push, latencia ~0 | publisher musí riešiť odberateľov, reconnect, spätný tlak; MQL5 sockety nefungujú v Testeri |

Voľba: **súbory** ako zdroj pravdy; rýchlosť sa dá pridať bez zmeny formátu (sekcia „Latencia").

Koreň: `%LOCALAPPDATA%\TradeBot\feed\` (neutrálne miesto, ktoré vidí NinjaTrader aj DLL v MT5 —
DLL píše a číta priamo, nie cez MQL sandbox). Prepis: env `TRADEBOT_FEED_DIR` (testy, iný disk).
Cesta sa pridá do `tradebot/core/paths.py`, nikde inde.

### Formát

```
feed\
  nt\                                   <source> = kto publikuje (nt, mt5, …)
    manifest.json                       publisher: host, platforma, verzia, heartbeat (ms UTC), zoznam trhov
    NQ\
      meta.json                         symbol, natívny názov (NQ 12-26), tick, point value, mena,
                                        seansa, posledný rollover, posledný uzavretý bar
      1m\
        20261016.bin                    záznamy pevnej dĺžky, jeden súbor na UTC deň
```

Záznam 1m baru (little-endian, 56 B): `int64 bt` (ms UTC otvorenia), `double o,h,l,c,v`,
`int32 flags` (bit 0 = bar je z histórie, bit 1 = prvý bar po rollovere), `int32 crc`. Pevná dĺžka
= odberateľ si nájde čas binárnym vyhľadávaním a vie, či súbor nie je dopísaný napoly
(dĺžka nie je násobok 56 → posledný kus ignoruje). Zapisuje sa len na koniec; bar sa zapíše
**až keď je uzavretý**. `PY -m tradebot.feed dump` vypíše čitateľne.

`manifest.json` heartbeat sa obnovuje každých ~5 s. Odberateľ podľa neho rozlíši „trh je
zatvorený" (publisher žije, bar nepribudol) od „publisher je dole" (heartbeat starý).

### Keď trh stojí

Overené na archíve (16. 10. 2026): **minúta bez obchodu v dátach nie je vôbec** — žiadny plochý
bar s objemom 0.

| súbor (2025) | 1m barov | medzier > 1 min | typické medzery |
|---|---|---|---|
| `databento/futures/MNQ_USD-1m` | 352 587 | 259 | 61 min (denná prestávka CME, 195×), ~49 h (víkend, 47×), sviatky; objem 0 nikde |
| `dukascopy/futures/NAS100_USD-1m` | 340 555 | 285 | prestávky a víkendy; importér vyhadzuje plochú vypchávku (zvyšné riadky s objemom 0 majú pohyb ceny — Dukascopy objem je tickový) |
| `binance/spot/BTC_USDT-1m` | 525 600 | 0 | krypto beží nonstop |

`resample_ohlcv` prázdne okná zahodí (`dropna(subset=["open"])`), takže chýba aj vyšší TF bar,
v ktorom sa neobchodovalo. **Feed robí to isté**: minútu bez obchodu nezapíše, odberateľ ju
nedopĺňa. Čo má indikátor robiť, keď extra trh stojí a hlavný beží (napr. NQ v dennej prestávke
CME, NAS100 CFD obchoduje ďalej), je vec stratégie: dostane informáciu, kedy bol posledný bar
série (`age`), a sama rozhodne (default: podmienka nad sériou je „neznáma" → nevstupovať).
V backteste to platí rovnako, lebo archív má tie isté diery.

### Rollover

Futures kontrakt má expiráciu (NQ štvrťročne: `NQ 12-26` → `NQ 03-27`). Okolo expirácie sa
obchodovanie presunie do ďalšieho kontraktu a ten má **inú cenu** (rozdiel = úrok a dividendy
do expirácie, pri NQ bežne desiatky až ~200 bodov). Spojená séria „vždy aktuálny kontrakt"
(front-month) má preto v deň prepnutia **umelý skok**, ktorý na trhu nebol:

```
NQ 12-26:  ... 21 010  21 012  21 008 |
NQ 03-27:                             | 21 195  21 199  21 190 ...     ← +187 bodov za jednu minútu
```

Dve možnosti:

- **bez úpravy** (front-month): ceny sú skutočné, ako ich vidí broker, ale skok raz za štvrťrok
  pokazí indikátory, ktoré pozerajú dozadu (ATR, korelácia výnosov, SMT na danom bare);
- **back-adjusted**: celá história pred prepnutím sa posunie o rozdiel, skok zmizne, ale staré
  ceny sú vymyslené (nesedia s tým, čo bolo na trhu).

Rozhodnutie: **bez úpravy**, ako archív z `tester.bento_import` — živý feed, záznam aj backtest
tak dávajú to isté. Prvý bar nového kontraktu nesie príznak `rollover` (flags bit 1), takže
indikátor si môže ten jeden bar vynechať alebo prepočítať. Ktorý kontrakt je aktuálny, rozhoduje
NinjaTrader (*Tools → Options → Market data → Merge policy* / jeho kalendár rolloverov).

## Latencia

Cieľ dnes: **≤ 0,5 s** od konca minúty po bar v engine odberateľa. Odkiaľ sa skladá a čo by sa
dalo zlepšiť, ak by raz treba menej:

| zdroj oneskorenia | dnes | zlepšenie |
|---|---|---|
| **kedy publisher vie, že minúta skončila** | NT/MT5 zatvorí 1m bar až **prvým tikom ďalšej minúty** — v tichom trhu to môžu byť sekundy | publisher skladá 1m bar sám z tikov (`OnMarketData` v NT, `OnTick`/`CopyTicks` v MT5) a uzavrie ho **podľa hodín** v `T + grace` (napr. 150 ms, na neskoré tiky burzy). Toto je najväčší zisk a robí sa hneď v F1. Hodiny publishera sa porovnávajú s časom tikov burzy (posun do `meta.json`) |
| zápis na disk | < 1 ms (append + flush) | — |
| **ako sa odberateľ dozvie, že pribudol bar** | polling súboru každých 250 ms | 1) polling 50 ms (stále lacné, `stat` na pár súborov); 2) **pomenovaná udalosť Windows** (`EventWaitHandle` `Local\TradeBot.feed.<source>.<symbol>`): publisher po zápise `Set()`, odberateľ čaká na signál s timeoutom — oneskorenie ~1 ms, súbory ostávajú zdrojom pravdy a polling poistkou; v MT5 to robí DLL (`StaticHost::FeedWait(h, timeoutMs)`) z `OnTimer`/`EventSetMillisecondTimer` |
| **kedy si odberateľ uzavrie svoj bar** | MT5 graf tiež zatvára bar prvým tikom ďalšej minúty | to isté ako publisher: EA spracuje bar podľa hodín (`OnTimer`) a nečaká na tik |
| čakanie na zarovnanie (`InpFeedMaxWaitMs`) | max 1,5 s, len keď feed mešká | pri lepšom publisherovi stačí 300–500 ms |

Prakticky: **publisher podľa hodín + polling 250 ms ≈ 0,2–0,5 s**; s pomenovanou udalosťou a
EA podľa hodín ≈ **50–200 ms** (dominuje `grace` a oneskorenie tikov od burzy). Ešte nižšie má
zmysel až pri tikoch — memory-mapped „head" s posledným tikom, súbory ostávajú.

## Publisher v NinjaTraderi (F1)

AddOn `TradeBotFeedAddOn` (rovnaký vzor ako `TradeBotLiveAddOn` — beží bez grafu a bez klikania,
po štarte NT aj po rekompilácii). Konfigurácia `Documents\NinjaTrader 8\TradeBot\feed\publish_nt.json`:

```json
{
  "source": "nt",
  "instruments": [
    {"name": "NQ",  "nt": "NQ 12-26",  "history_days": 10},
    {"name": "ES",  "nt": "ES 12-26",  "history_days": 10},
    {"name": "RTY", "nt": "RTY 12-26", "history_days": 10}
  ]
}
```

- Pri štarte `BarsRequest` na 1m za `history_days` → dopíše, čo vo feede chýba (nič neprepisuje).
- Potom tiky (`MarketData`) → 1m bar uzavretý podľa hodín (sekcia „Latencia").
- Zmenu configu číta podľa mtime (ako control súbor) — pridanie trhu netreba reštart NT.
- Zoznam a stav: `PY -m tradebot.feed status` (trhy, posledný bar, oneskorenie, heartbeat);
  neskôr aj na karte **Live** vo webapp (lokálne, webapp beží na tom istom PC).
- Nastavenie z príkazového riadka: `PY -m tradebot.feed publish --source nt --add NQ="NQ 12-26"`
  (atomický zápis configu ako `control`).

## Odberateľ v MT5 (F2)

1. **Deklarácia v stratégii.** Config stratégie dostane pole (v `PORT_ONLY_FIELDS`, default
   prázdne = správanie ako dnes), napr.:
   ```json
   "extraSeries": [
     {"id": "es",  "feed": "nt/ES", "tf": 5},
     {"id": "nq",  "feed": "nt/NQ", "tf": 5}
   ]
   ```
   `StrategySpec` / C# `IEngine` to vystaví ako zoznam potrebných sérií (podobne ako dnes
   `HtfTfMinutes`), engine dostáva bary cez nové `FeedSeries(id, bar)`. Jadro nepozná NQ ani ES —
   len `id` zo configu.
2. **Adaptér EA** (`TradeBotEA.mqh`): v `OnInit` `StaticHost::FeedOpen(h, …)` pre každú sériu,
   predhistória rovnako ako HTF (`2 × RequiredHistory`), potom pred každým `OnBar` dodá všetky
   uzavreté bary sérií. TF skladá C# `CandleAggregator` (port `candles.py`, test parity).
3. **Zarovnanie v čase** — najdôležitejšie pre paritu s backtestom. Bar grafu `[T−tf, T)` smie
   vidieť len bary sérií uzavreté najneskôr v `T`. Keď feed ešte nedosiahol `T`, adaptér počká
   max `InpFeedMaxWaitMs`. Keď nedorazí: engine dostane bar s príznakom `feedStale` a stratégia sa
   rozhodne sama (default: v ten bar nevstupovať), do spoolu ide `note` `warn`. Ako rozlíšiť
   „mešká" od „trh stojí": heartbeat publishera je čerstvý a jeho hodiny už prešli `T + grace`
   → minúta bez obchodu, nečaká sa. V backteste sú dáta vždy zarovnané — bez čakania by naživo
   vznikali obchody, ktoré backtest nepozná.
4. **Strategy Tester MT5**: feed sa v testeri nečíta naživo, ale zo záznamu (`data_feed\…`,
   sekcia nižšie) cez ten istý reader, aby test sedel so živým behom.

NinjaTrader stratégia ako odberateľ (napr. MT5 forex do NT) ide cez ten istý `FeedReader`
z jadra; adaptér `TradeBotStrategy.cs` dostane rovnaké `extraSeries`.

## Záznam do feather a čítanie v testoch (F1–F2)

### Odberateľ-zapisovač (`PY -m tradebot.feed record`)

Najjednoduchší odberateľ, zároveň vzor pre ďalších: číta feed a ukladá ho do feather v **tvare
archívu** (`date` UTC, `open, high, low, close, volume`; 1m; jeden súbor na rok), takže ho prečíta
všetko, čo dnes číta `data/archive/tester/`.

```
data_feed\                                  koreň v tradebot/core/paths.py, v .gitignore (dáta neopúšťajú stroj)
  nt\
    NQ-1m.2026.feather
    NQ-1m.meta.json                         natívne názvy kontraktov, rollovery (čas → kontrakt), tick, point value
    ES-1m.2026.feather
```

```bash
PY -m tradebot.feed record                         # všetky trhy všetkých publisherov, beží a dopisuje
PY -m tradebot.feed record --source nt --name NQ,ES
PY -m tradebot.feed record --once                  # dopíše, čo chýba, a skončí (napr. Plánovač úloh raz denne)
```

- Kurzor = posledný zapísaný `date` v feather (žiadny vlastný stav); po výpadku dopíše od neho.
  Feed si drží históriu po dňoch, takže kým `.bin` súbory existujú, nič sa nestratí.
- Feather sa nedopisuje po riadku — zapisovač drží buffer a súbor roka prepíše atomicky
  (tmp + `os.replace`) raz za N minút a pri ukončení.
- Zapisuje len to, čo prišlo z feedu (žiadne dopĺňanie dier, žiadne vyššie TF) — rovnaké pravidlá
  ako importéry.
- Môže bežať ako služba agenta / webapp na obchodnom PC (neskôr prepínač vo webapp).

### Reader pre backtest (`ArchiveFeedSource`)

Keď má stratégia v configu `extraSeries`, backtest ich potrebuje odniekiaľ dostať. Jedno
rozhranie, dva zdroje:

```python
class FeedSource(Protocol):
    def bars(self, feed: str, since: datetime, until: datetime) -> pd.DataFrame: ...   # 1m, tvar archívu

LiveFeedSource(root=feed_dir)                       # .bin súbory feedu (naživo, Python odberatelia)
ArchiveFeedSource(roots=[data_feed, data_archive])  # feather: najprv záznam z feedu, potom archív
```

- `feed: "nt/NQ"` → `data_feed/nt/NQ-1m.<rok>.feather`; keď tam nie je, mapovanie v
  `tester/feed_sources.json` môže povedať, že `nt/NQ` = `databento/futures/NQ_USD` z archívu
  (dlhá história z importu, posledné mesiace zo záznamu feedu). Nič sa nemieša potichu: beh
  zapíše do `run.json`, z ktorého súboru ktorá séria prišla.
- Vyšší TF série skladá `candles.resample_ohlcv` (v C# `CandleAggregator`) — rovnako v backteste aj
  naživo.
- Adaptéry ho dodajú enginu rovnakou cestou ako naživo (`FeedSeries` pred `OnBar`, s tým istým
  zarovnaním): Freqtrade stratégia (`TradebotStrategyBase`), emulátor MultiCharts, most do C#,
  MT5 Strategy Tester (export zo záznamu do `Common\Files\TradeBot\feed_tester\`).
- Chýbajúce dáta pre zvolené obdobie = beh sa **odmietne** s jasnou chybou (ktorá séria, od–do),
  nie ticho bez série. Webapp to ukáže pri výbere obdobia ako pri chýbajúcom páre.
- Test: ten istý engine raz z `LiveFeedSource` (feed zapísaný z feather replayom) a raz z
  `ArchiveFeedSource` → zhoda bar po bare (`tester/tests/test_feed_parity.py`).

### Replay (bonus k testom)

`PY -m tradebot.feed replay --from data_feed/nt/NQ-1m.2026.feather --source sim --speed 60` —
Python publisher, ktorý zo záznamu zapisuje feed v reálnom (alebo zrýchlenom) čase. Dá sa tak
vyskúšať MT5 EA odberateľ a zarovnanie bez NinjaTradera a mimo obchodných hodín.

## Opačný smer: publisher v MT5 (F3)

EA (alebo skript bez obchodovania) `TradeBotFeed.mq5` s konfiguráciou
`Common\Files\TradeBot\feed\publish_mt5.json` (rovnaký tvar ako NT, `"mt5": "EURUSD"` namiesto
`"nt"`). Tiky (`CopyTicks`) → 1m podľa hodín ako v NT, uzavreté bary posiela do
`StaticHost::FeedPublishBar`. Čas servera → UTC cez ten istý posun ako EA
(`TimeTradeServer() - TimeGMT()`). Výsledok je `feed\mt5\EURUSD\1m\…` — čítať ho môže NT stratégia,
Python, zapisovač aj iný MT5 terminál (napr. iný broker na tom istom PC).

## Python (`tradebot/feed/`)

- `format.py` — záznam, cesty, manifest (zdieľané s testami C#);
- `reader.py` — `LiveFeedSource`, `follow()` generátor nových barov;
- `archive.py` — `ArchiveFeedSource` (feather);
- `writer.py` — publisher z Pythonu (testy, `replay`);
- `__main__.py` — `status`, `dump`, `publish --add/--remove`, `record`, `replay`.

## Fázy

| fáza | obsah | hotové keď |
|---|---|---|
| **F0** | formát, `FeedWriter`/`FeedReader` v C# jadre, Python reader/writer, `CandleAggregator` v C# s paritou na `candles.py` | testy zápis↔čítanie C#/Python, polovičný záznam, rotácia dňa, parita agregácie |
| **F1** | NT AddOn publisher (1m podľa hodín) + `publish_nt.json` + `tradebot.feed status` + **`record` do feather** | NQ/ES 1m z NT sedia s Databento importom za ten istý deň; záznam beží deň bez diery navyše |
| **F2** | `extraSeries` v configu, `FeedSeries` v engine kontrakte, `ArchiveFeedSource` v backteste (Freqtrade, emulátor), MT5 EA odberateľ so zarovnaním, `replay` | ukážková stratégia (napr. SMT NQ/ES) dá v Testeri, v MT5 Strategy Testeri a pri replayi tie isté signály |
| **F3** | MT5 publisher, NT stratégia ako odberateľ | forex z MT5 v NT stratégii |
| **F4** | stav feedu a zapisovača vo webapp (karta Live, lokálne: trhy, oneskorenie, diery) | — |
| **F5** | tiky / bid-ask, memory-mapped head | až keď ich bude chcieť konkrétny indikátor |

Prenos feedu medzi strojmi sa **nerobí** — dáta ostávajú na stroji, kde bežia platformy.

## Otvorené otázky

1. **Ktoré trhy a ktorý indikátor** ako prvý? Od toho závisí ukážková stratégia v F2.
2. **Dlhá história pre backtest**: stačí na začiatok záznam z feedu (rastie odo dňa spustenia),
   alebo sa má `nt/NQ` hneď mapovať na Databento archív (`tester/feed_sources.json`)?
