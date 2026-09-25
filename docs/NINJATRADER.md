# NinjaTrader vetva a C# jadro

Tretí adaptér TradeBota. Od Freqtrade a MultiCharts sa líši v jednom podstatnom: **NinjaTrader 8
je .NET aplikácia a stratégie si prekladá sám**, takže Python engine v ňom bežať nemôže. Stratégia,
ktorá má ísť do NinjaTradera, má preto **jadro v C#** — a to isté jadro potom beží aj pod Freqtrade,
aby sa dalo testovať, merať a porovnávať tým istým náradím ako všetko ostatné.

```
csharp/TradeBot.Core/                 generické C# jadro (zrkadlo tradebot/core): Bar, InstrumentSpec, SizeSpec,
                                      BarHistory, SessionClock, kresby, ordery, TradePlan, Warmup, IEngine, register
csharp/TradeBot.Strategies/<Meno>/    stratégia v C# — trieda s [TradeBotEngine("kľúč")] nad IEngine
csharp/TradeBot.Host/                 TradeBot.Host.exe — engine ako proces (stdio most, Mono)
        │
        ├── tradebot/adapters/ninjatrader/TradeBotStrategy.cs   adaptér NinjaTrader (NinjaScript, managed ordery)
        │       └── deploy/ninjatrader/<Meno>.cs                šablóna stratégie pre graf (3 riadky)
        │
        ├── tradebot/adapters/mt5/TradeBotEA.mqh                adaptér MetaTrader 5 (MQL5 nad TradeBot.dll) — docs/MT5.md
        │       └── deploy/mt5/<Meno>.mq5                       šablóna Expert Advisora (2 define + include)
        │
        └── tradebot/adapters/csharp/                           adaptér Freqtrade nad C# jadrom = most
                └── tradebot/strategies/<kľúč>/                 Python balík stratégie: config, popisy, SPEC
```

Dnes majú C# jadro dve stratégie, obe prepisy Python predlohy s parametrami, profilmi, kresbami aj
signálmi zhodnými s ňou; vo webapp sú to obyčajné stratégie pod Freqtrade:

| kľúč | predloha | C# | NinjaTrader šablóna |
|---|---|---|---|
| **`ibsnet`** | `ibs` (IBS Imbalance Breakout) | `csharp/TradeBot.Strategies/IbsNet` | `deploy/ninjatrader/IBSNet.cs` |
| **`orbnet`** | `orb` (Opening Range Breakout) | `csharp/TradeBot.Strategies/OrbNet` | `deploy/ninjatrader/ORBNet.cs` |

## Pravidlá (tie isté ako inde, len v C#)

- **Jadro ani adaptér nepoznajú stratégiu menom.** C# engine sa hlási atribútom
  `[TradeBotEngine("ibsnet", "…")]`; `EngineRegistry` si triedy nájde v načítaných assembly.
  Python strana má `StrategySpec.csharp_dir` a `engine_factory=csharp_engine_factory("ibsnet")`.
- **Adaptér NinjaTrader spustí len stratégiu s C# jadrom.** Python stratégie (`ibs`, `structure`, …)
  v ňom nejdú — a naopak C# stratégia ide pod Freqtrade aj do emulátora MultiCharts cez most.
- **Engine je čistý**: žiadne I/O, žiadny globálny stav, jedno volanie `OnBar` na uzavretý bar grafu.
- **Jazyk je C# 5 bez NuGet závislostí.** Nie je to nostalgia: takto jadro preloží `csc.exe`, ktorý je
  súčasťou .NET Frameworku na každom Windows (netreba .NET SDK ani Visual Studio), na macOS/Linuxe
  Mono, a NinjaTrader ho preloží tiež. Čiže: žiadne `$"…"`, `?.`, `nameof`, `=>` členy, `out var`, tuple.
- Config číta C# z **toho istého JSON** ako Python (`to_dict()` / profil). Rozsahy, popisy a validácia
  ostávajú v Pythone; že C# config pozná každé pole s rovnakým defaultom, stráži
  `tradebot/tests/test_csharp_core.py`.

## Most do Freqtrade (`tradebot/adapters/csharp`)

`CSharpEngine` spĺňa kontrakt `Engine` (`on_bar`, `final_drawings`, `required_history`, `warmup`
vrátane seedingu indikátorov na vyššom TF), takže generický `TradebotStrategyBase`, emulátor
MultiCharts, webapp, hyperopt aj analytika s ním pracujú bez zmeny. Dva transporty, jeden protokol
(`EngineHost`: jednoduché typy dnu, jeden JSON na bar von):

| transport | kedy | čo treba |
|---|---|---|
| `inproc` — pythonnet, v procese | predvolene, keď je pythonnet nainštalovaný | Windows: nič (.NET Framework); macOS/Linux: Mono |
| `stdio` — `TradeBot.Host.exe` ako proces | bez pythonnet, alebo `TRADEBOT_CSHARP_BRIDGE=stdio` | Windows: nič; macOS/Linux: Mono |

**Windows** (.NET Framework 4.8) aj **Mono** sú overené. Mono 6.14 na Linuxe (WSL Ubuntu, 2026-09-20):
jadro preložené `mcs`, 44 164 volaní enginu nahraných na Windows (BTC 3m, 2025-09-04 – 12-04, všetko
zapnuté, cez jesenné prechody času v troch pásmach) dalo **tie isté odpovede na rovnosť** — cez `stdio`
aj cez pythonnet nad Mono. macOS používa ten istý runtime (`brew install mono`), na Macu samotnom to ešte
nikto nespustil; kontrola je jeden príkaz a stačí na ňu holý Python 3:

```bash
PY -m tester.compare.csharp_replay record --from 2026-08-24 --to 2026-09-04 --out replay.jsonl   # na Windows
python3 -m tester.compare.csharp_replay verify replay.jsonl                                       # na Macu / Linuxe
```

Na stroji s celým prostredím to isté (a viac) robí `pytest tester/tests/test_csharp_parity.py` — tam sa
C# pod Mono porovnáva priamo s Python enginom. Dve pasce, ktoré test pod Mono našiel a sú opravené:
preklad sa robil v systémovom `/tmp` a `os.replace` cez hranicu zväzku padá (teraz vedľa cieľa), a DLL
z `mcs` nenabehne na .NET Frameworku (viaže sa na metódy, ktoré tam nie sú) — preto `csharp/bin/.built-by`
a preklad z iného systému v zdieľanom adresári sa berie ako zastaraný.

Čísla idú dnu ako natívne `double` (pythonnet) alebo ako bitový vzor (stdio) a von ako `G17` — cestou
sa nezmení ani posledný bit, preto sa dá C# engine porovnávať s Python enginom **na rovnosť**.

Dve veci, na ktoré most narazil a ktoré v ňom preto sú:

- **Hyperopt** posiela stratégiu aj s enginmi do paralelných procesov cez pickle; C# objekt sa preniesť
  nedá, takže `CSharpEngine` si v novom procese otvorí čerstvý engine s tým istým configom
  (`__getstate__`/`__setstate__`) — generický adaptér si pri hyperopte aj tak stavia runner pre každú
  epochu nanovo.
- **Koniec procesu**: pythonnet pri `unload` opakovane prejde celú haldu Pythonu. Po Freqtrade backteste
  to bolo ~20 s, po celej sade testov (90 miliónov objektov, jeden zber 10 s) **~15 minút** „visiaceho"
  procesu po vypísaní výsledku. Vynechať `unload` nejde (CLR potom spadne, návratový kód 127), preto
  `tradebot.core.clr.tame_shutdown()` tesne pred ním zavolá `gc.freeze()`. Volá sa po každom načítaní
  CLR — v moste aj pri `import clr` v MultiCharts adaptéri, lebo v testoch ho ako prvý načíta ten.

Preklad rieši most sám: `csharp/bin/TradeBot.dll` sa zostaví pri prvom použití a vždy, keď je niektorý
`.cs` novší (`python -m tradebot.adapters.csharp.build [--force]`). `csharp/bin/` je v `.gitignore`.
DLL sa do procesu načíta z bajtov, takže ju bežiaci beh nezamkne. `setup.ps1`/`setup.sh` inštalujú
pythonnet (`pip install -e .[csharp]`), `install-macos.sh` aj Mono.


### Naživo: asynchrónne fily a oneskorené bary

Engine ORB berie vstup, ktorý po jednom bare stále nemá pozíciu, ako nevyplnený: zruší ho a na
ďalšom bare pošle nový. V backteste market order vyplní hneď, naživo je fill asynchrónny — a keď
dátový feed dodá dávku oneskorených barov naraz (25. 9. 2026: 20 minútových barov v jednej sekunde),
engine vidí na každom z nich pozíciu 0 a pošle 20 market orderov. Oba živé adaptéry (NinjaTrader,
MT5) preto rátajú **odoslaný, ešte nevyplnený market vstup ako pozíciu** a **bar, ktorý prišiel
neskôr než dva TF po svojom zatvorení, neobchodujú** (do logu ide „prisiel neskoro“). Ani jedno
nemení backtest ani paritu signálov.

## Parita s Python predlohou

C# jadro je prepis, nie nová stratégia — kontroluje sa bar po bare, nie počtom obchodov:

```bash
PY -m tester.compare.csharp_parity --from 2026-08-24 --to 2026-09-04
PY -m tester.compare.csharp_parity --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl.json \
   --from 2025-09-04 --to 2026-09-04 --set tradeDirection=Indicator --set indAdx=true --set showElliott=true
```

Oba enginy bežia v tom istom `EngineRunner` (rovnaký model vyplnenia, HTF feeder, seeding) a na každom
bare sa porovnajú ordery, kresby, udalosti stavu, koniec seansy aj hodiny. Výsledok a čísla behov:
[merania/PARITA_ibsnet_2026-09-20.md](merania/PARITA_ibsnet_2026-09-20.md). V `pytest` to stráži
`tester/tests/test_csharp_parity.py` (syntetické bary so všetkým zapnutým, oba transporty, golden okno).

ORBNet proti ORB (burza `nas100` = Dukascopy NAS100 zo skladu, `mnq` = Databento MNQ):

```bash
PY -m tester.compare.csharp_parity --python orb --csharp orbnet --profile nas100_dukascopy_3m --exchange nas100 --from 2021-01-04
```

V Strategy Analyzeri (MNQ 12-26, 2026-03-01 – 09-10) sedí 207 z 207 vstupov s Testerom
(`tester.ninjatrader compare --strategy orbnet --profile nas100_dukascopy_3m`).
Výsledok: [merania/PARITA_orbnet_2026-09-24.md](merania/PARITA_orbnet_2026-09-24.md), v `pytest`
`tester/tests/test_csharp_parity_orb.py`. Pri ORB sa ukázala ďalšia pasca: Python 3.12 `sum()` nad
floatmi nie je cyklus, ale kompenzovaná (Neumaierova) suma — kde predloha píše `sum(...)`, C# volá
`PyMath.Sum`, kde píše cyklus, C# píše cyklus.

Na čo si dať pri prepise pozor (všetko sa už raz stalo alebo skoro stalo):

- **poradie operácií** — plávajúca čiarka nie je asociatívna; `sum()` je cyklus zľava doprava;
- `round()` v Pythone je bankárske = `Math.Round` (default `ToEven`); `int(x)` orezáva k nule;
- `sorted()` je stabilný, `List.Sort` nie; `dict` drží poradie vloženia;
- **časové pásma**: .NET Framework nepozná IANA mená (`America/New_York`) → `TimeZones` ich mapuje na
  Windows ID; neexistujúci a dvojznačný lokálny čas (prechod na letný/zimný) sa rieši ako Python `fold=0`;
- formát čísel v textoch: `PyFormat.Fixed` zaokrúhľuje ako Python `{x:.1f}`, vždy `InvariantCulture`;
- zdrojáky sú UTF-8 bez BOM → kompilátor dostáva `-codepage:65001` (šípky v štítkoch likvidity).

## NinjaTrader 8

```bash
PY -m tradebot.adapters.ninjatrader check      # preloží adaptér proti DLL nainštalovaného NinjaTradera
PY -m tradebot.adapters.ninjatrader install    # skopíruje jadro, adaptér, šablóny a profily
```

`install` kopíruje **zdrojáky** do `Documents\NinjaTrader 8\bin\Custom` (`AddOns\TradeBot\…` jadro,
`Strategies\TradeBotStrategy.cs` adaptér, `Strategies\IBSNet.cs` a `ORBNet.cs` šablóny) a profily ako úplné configy
do `Documents\NinjaTrader 8\TradeBot\profiles\`. Potom v NinjaTraderi *New → NinjaScript Editor → F5*
a stratégia **IBSNet** alebo **ORBNet** na **minútový** graf. Netreba pridávať referenciu na DLL; po zmene jadra stačí
`install` zopakovať. `check` beží aj samostatne — chybu NinjaTrader API ukáže pri preklade, nie v grafe.

Čo adaptér robí:

| | |
|---|---|
| bar | `Calculate.OnBarClose`; čas baru = čas **zatvorenia** v pásme z *Options → General* → prepočet na čas otvorenia v ms UTC |
| detekčný TF zón | druhú sériu (`zoneDetectionTF` z profilu) si pridá sám (`AddDataSeries`), kŕmi ňou `HtfFeeder` |
| inštrument | `TickSize` a `PointValue` z `MasterInstrument`, krok množstva 1 kontrakt |
| ENTRY | managed: `EnterLong/ShortLimit` (live until cancelled), pri Pin Bar/Engulfing podľa `pbEngOrderType` market; SL/TP cez `SetStopLoss`/`SetProfitTarget` na meno vstupu (`LONG_<uid>`) |
| CANCEL / CLOSE | `CancelOrder`; `ExitLong/Short` na meno vstupu; koniec poslednej seansy dňa zavrie všetko (`tb_session_end`) |
| kontext pre engine | pozícia, mená **vyplnených** vstupov, denný limit výhier (platí od ďalšieho baru, ako v Pine) |
| plnenie orderov | na vlastnej 1m sérii (`FillDetailMinutes`, 0 = bary grafu) — náhrada za *Order fill resolution = High*, ktorú NinjaTrader pri viac sériách nepovolí |
| trailing | z `TradePlan.Trailing`, posúva sa na zatvorení baru grafu |
| kresby | `Draw.Rectangle/Line/Text/RegionHighlightX`, zmeny cez `DrawRegistry`; pozadie seáns je vypnuté (parameter) |
| predhistória | signál z baru pred `RequiredHistory` order nepošle; indikátory smeru sa rozbehnú na histórii grafu (bez seedingu, ako živá študia MultiCharts) |

**Signály sú rovnaké, fill model nie** — to platí pre každú platformu. Strategy Analyzer plní limitku
podľa svojho *Order fill resolution*; pre porovnateľné čísla nastav *High* s 1-minútovou sériou (to je
to isté, čo `--timeframe-detail 1m` vo Freqtrade). Závery pre NinjaTrader patria behom v NinjaTraderi.

### Test v Strategy Analyzeri proti Testeru

NinjaTrader nemá históriu, kým nie je pripojený poskytovateľ dát — a aj potom by to boli iné sviečky
než v sklade Testera. Preto sa dáta do neho **importujú z nášho skladu** a signály sa z neho
**exportujú späť**:

```bash
PY -m tester.ninjatrader export --instrument mnq_databento --contract "MNQ 12-26" --from 2026-03-01 --to 2026-09-10
#   -> data/ninjatrader/MNQ 12-26.Last.txt   (1m, čas zatvorenia baru, UTC)
```

1. *Tools → Import → Historical Data*: súbor vyššie, **Format** „NinjaTrader (end of bar)",
   **Data type** Last, **Time zone UTC**.
   Pred behom nastav *Tools → Options → Market data → Merge policy* na **Do not merge**: s predvoleným
   „Merge back adjusted" NinjaTrader pre staršie dátumy číta vtedajšie kontrakty (`MNQ 03-26`, `06-26`…),
   ktoré import nemá — beh potom skončí za sekundu, bez jedinej zóny a orderu (adaptér to vypíše do
   Output okna: „PRILIS MALO DAT").
2. *New → Strategy Analyzer*: Backtest, stratégia **IBSNet**, inštrument `MNQ 12-26`, **Minute 3**,
   obdobie importu, *Order fill resolution* **Standard** — „High" NinjaTrader pre stratégiu s viac sériami
   nepovolí; jemné plnenie si adaptér robí sám (parameter „Detail plnenia (min)" = 1 pridá 1m sériu
   a ordery idú na ňu, obdoba `--timeframe-detail 1m`); v parametroch stratégie zapni
   **„Exportovat signaly"** (profil nechaj prázdny = `multicharts_mnq_3m`). *Run*.
3. Porovnaj, čo engine chcel v NinjaTraderi a čo v Testeri nad tými istými barmi:

```bash
PY -m tester.ninjatrader compare --instrument mnq_databento --profile multicharts_mnq_3m --from 2026-03-01 --to 2026-09-10
```

`compare` číta najnovší export z `Documents\NinjaTrader 8\TradeBot\logs\` a porovná **vstupy** (bar,
cena, SL, TP, veľkosť) a **prechody stavov zón 0–3** — to, čo na fill modeli nezávisí a sedieť má.
Stavy 4–5 (vyplnenie, OCO, timeout) sa rozísť smú: NinjaTrader plní po svojom. Referencia na tomto
okne: 83 vstupov, 2 438 udalostí stavu.

Stav k 2026-09-20: prvý beh v Strategy Analyzeri prebehol a **signály sedia s Testerom úplne** —
83 z 83 vstupov (bar, cena, SL, TP, veľkosť) a 1 988 z 1 988 prechodov stavov zón; výsledok sa líši len
fill modelom (78 obchodov, +6 974 $, PF 1,87 proti 71, +6 150 $, PF 1,861 v emulátore). Čísla:
[merania/PARITA_ibsnet_2026-09-20.md](merania/PARITA_ibsnet_2026-09-20.md). Neoverené ostáva: živý
graf (realtime prechod, kreslenie) a shorty v NinjaTraderi (profil MNQ je long-only; trailing v ňom zapnutý je).
Ovládanie okna NinjaTradera je pre AI asistenta len na čítanie — import a Run musí naklikať človek.

## Ako pridať ďalšiu stratégiu s C# jadrom

1. `csharp/TradeBot.Strategies/<Meno>/` — config (`*Config.cs`, polia menom zhodné s Python configom),
   engine s `[TradeBotEngine("kľúč", "titulok")]` a konštruktorom
   `(Dictionary<string, object> config, InstrumentSpec inst, int chartTfMinutes)`.
2. `tradebot/strategies/<kľúč>/` ako každá iná stratégia ([STRATEGIE.md](STRATEGIE.md)), len
   `engine_factory=csharp_engine_factory("kľúč")` a `csharp_dir=…`; `engine.py` v Pythone nie je.
3. `deploy/ninjatrader/<Meno>.cs` — potomok `TradeBotStrategy` s `EngineKey`.
4. Keď má stratégia Python predlohu, porovnaj ju cez `tester.compare.csharp_parity --python … --csharp …`.
