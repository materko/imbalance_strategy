# Stratégie v TradeBote — ako sa píše ďalšia

Tento dokument je návod pre kohokoľvek — človeka aj jazykový model —, kto má do
repozitára pridať stratégiu. Je písaný tak, aby stačil sám o sebe: čo napísať, v akom
poradí, čo si smie stratégia určiť sama a kedy je hotová.

**Tri veci, ktoré tu neplatia ako odporúčanie, ale ako podmienka:**

1. Stratégia sa píše **pre oba enginy naraz** — Freqtrade aj MultiCharts. Nie je to
   práca navyše: logika je jedna a adaptéry sú tenké
   ([nižšie](#oba-enginy-nie-je-odporúčanie-ale-podmienka)).
2. Jadro ani adaptéry sa novou stratégiou **nesmú dotknúť**. Všetko, čo o sebe stratégia
   potrebuje povedať, hovorí cez `StrategySpec` v registry. Keď sa zdá, že to inak nejde,
   je to chyba v návrhu spec-u, nie dôvod siahnuť do `tradebot/core`.
3. Stratégia bez **základnej analytiky a posudku** nie je hotová
   ([nižšie](#analytika-a-posudok-bez-nich-to-nie-je-hotové)). Kód, ktorý beží, ešte nie
   je odpoveď na otázku, či to k niečomu je.

Čo je dnes v registry (`python -m tester.webapp.cli params --strategy <kľúč>` vypíše parametre):

| kľúč | názov | parametrov | na čo |
|---|---|---|---|
| `ibs` | IBS Imbalance Breakout | 115 | ostrá stratégia, golden testy proti TradingView |
| `ibsnet` | IBSNet Imbalance Breakout (C# jadro) | 115 | prepis `ibs` do C# — natívne v NinjaTraderi, pod Freqtrade cez most; signály zhodné s `ibs` bar po bare ([NINJATRADER.md](NINJATRADER.md)) |
| `structure` | Market Structure BOS / CHoCH | 18 | druhý archetyp (štruktúra, protitrendový `sweep`); [ANALYTIKA](../tradebot/strategies/structure/docs/ANALYTIKA.md) |
| `demo_breakout` | Demo Donchian Breakout | 8 | ukážka, ktorá overuje rámec end-to-end; nie je to obchodné odporúčanie |
| `divergence` | Divergence — divergencie indikátorov v smere supertrendu | 65 | port Freqtrade stratégie z r. 2022 (bez Pine); vyššie TF si skladá sama z barov grafu; [PORT](../tradebot/strategies/divergence/docs/PORT.md), [ANALYTIKA](../tradebot/strategies/divergence/docs/ANALYTIKA.md) |
| `orb` | ORB — Opening Range Breakout | 49 | prvých 1–60 min seansy tvorí range, obchoduje sa jeho prerazenie; voliteľná EMA (filter smeru, filter dňa, výstup) |
| `orbnet` | ORBNet Opening Range Breakout (C# jadro) | 49 | prepis `orb` do C# — natívne v NinjaTraderi, pod Freqtrade cez most; signály zhodné s `orb` bar po bare ([NINJATRADER.md](NINJATRADER.md)) |
| `gap` | Gap Fill | 34 | otvárací gap a jeho zatvorenie |
| `range` | Range Breakout | 42 | konsolidácia kdekoľvek na grafe a jej prerazenie; [ANALYTIKA](../tradebot/strategies/range/docs/ANALYTIKA.md) |
| `sdzone` | SD Zones | 44 | dopyt/ponuka zo základne a impulzu (Skorupinski); [ANALYTIKA](../tradebot/strategies/sdzone/docs/ANALYTIKA.md) |
| `breakout` | Breakout — prerazenie prvej sviečky NY openu | 32 | najmenšia z ostrých: dve úrovne z prvej 5m sviečky 9:30 NY, vstup na 1m/2m/3m grafe market alebo limitkou; [ANALYTIKA](../tradebot/strategies/breakout/docs/ANALYTIKA.md) |
| `trendlines` | Trendlines — prerazenie trendovky | 46 | klasické trendovky cez pivoty na vlastnom TF (5m–4h), prerazenie zatvorením, druhým zatvorením alebo retestom; RR a smer nastaviteľné |

`demo_breakout` je zámerne malá a zámerne **úplná**: má všetko, čo tento návod vyžaduje,
takže sa dá kopírovať riadok po riadku. Keď si vyberáš vzor, ber ju — IBS je port
115-vstupového Pine skriptu a väčšina jej zložitosti je vlastnosť tej stratégie, nie rámca.

## Čo je generické a čo je vec stratégie

Toto je celý model. Kto ho má v hlave, nemusí hľadať, kam čo napísať:

| generické (nedotýkaš sa toho) | vec stratégie (píšeš to) |
|---|---|
| prehratie barov, sviečky, timeframy, sklad dát | logika: kedy je setup, kedy vstup, aký SL a TP |
| Freqtrade `IStrategy`, MultiCharts študia, emulátor | čísla a prepínače (config) a ich rozsahy |
| formulár webapp, história behov, graf, hľadanie | popisy parametrov (`params.py`): skupina, titulok, tooltip |
| break-even, charakter, skupiny obchodov, náhoda, Monte Carlo | mená kresieb, ktoré nesú SL/TP, pole s rizikom, vedomosti o ladení |
| sizing z rizika, tick size, zaokrúhľovanie ceny | čo znamená „setup" a koľko histórie na to treba |

Vo všetkých riadkoch vpravo platí to isté: **stratégia to o sebe povie deklaratívne** v
`StrategySpec`, generická časť si to vyzdvihne z registry a menom ju nepozná.

## Čo je kde

```
tradebot/
  core/paths.py         cesty v repozitári (dáta, archívy, tester/) - jediné miesto, kde sú napísané
  core/                 generické jadro: Bar, InstrumentSpec, SizeSpec, BarHistory, SessionClock,
                        StrategyConfig (báza configu + load_profile), Engine protokol + EngineOutput,
                        OrderIntent/StateEvent/MarketContext, TradePlan, DrawCommand + DrawKind registr
  strategies/
    __init__.py         STRATEGIES = {"ibs": …, "structure": …, "demo_breakout": …, "divergence": …}, get_spec(), spec_for_config()
    base.py             StrategySpec (popis stratégie), ChartLayer (vrstva grafu)
    hyperopt.py         StrategyHyperopt — čo o ladení vie stratégia (báza)
    <key>/              jedna stratégia (viď checklist nižšie) — vrátane jej configs/ a docs/
  adapters/freqtrade/   TradebotStrategyBase (generická IStrategy), EngineRunner, export_chart
  adapters/multicharts/ TradebotSignal (generická študia), MCRunner, MCDrawSink, emulátor
  adapters/csharp/      most do C# jadra: CSharpEngine, csharp_engine_factory, preklad csharp/
  adapters/ninjatrader/ TradeBotStrategy.cs (generická NinjaScript stratégia) + inštalácia
  webapp/               tester: výber stratégie, formulár z popisov stratégie, história, graf s vrstvami
deploy/freqtrade/user_data/strategies/<FreqtradeTrieda>.py   shim (Freqtrade resolver)
deploy/multicharts/<Nazov>_Signal.py                          šablóna študie
docs/profily_archiv/<key>/                                    archivované profily
tester/runs/, tester/profiles/                                história behov a profily testerov
```

Balík jednej stratégie:

```
tradebot/strategies/moja/
  __init__.py        SPEC = StrategySpec(...) — jediné, čo o nej vie zvyšok sveta
  config.py          parametre (dataclass), rozsahy, jednotky, vlastné kontroly
  params.py          popisy parametrov pre formulár: skupina, titulok, tooltip
  engine.py          logika: on_bar() -> EngineOutput
  drawing.py         vlastné druhy kresieb
  meta.py            metadáta pre webapp: vrstvy grafu, názvy, závislosti prepínačov
  hyperopt.py        čo o ladení vieme: odporúčania, varovania, väzby, FEATURE_PARAMS
  freqtrade.py       trieda nad TradebotStrategyBase (obvykle 5 riadkov)
  multicharts.py     trieda nad TradebotSignal (obvykle 3 riadky)
  configs/           profily stratégie (JSON)
  docs/sources/      Pine zdroj — LEN keď o neho niekto požiada
  docs/ANALYTIKA.md  generovaná analytika + posudok (viď nižšie)
```

## Postup

### 1. Popisy parametrov

`params.py`: `GROUPS` (poradie skupín vo formulári) a `PARAMS` — `pole -> {group, title,
tooltip, [step], [inline], [options], [type]}`. Je to **jediný** zdroj toho, ako sa
parameter volá po ľudsky a čo robí; formulár webapp aj `cli params` ho čítajú odtiaľ
(`StrategySpec.param_meta`).

Čo sem **nepatrí**: rozsahy, defaulty, typy a hodnoty enumov. Tie sú v `config.py`
(`CONSTRAINTS`, defaulty dataclass, `SIZE_FIELDS`, `ENUM_FIELDS`) a formulár si ich
vyzdvihne odtiaľ, takže sa nemajú ako rozísť s tým, čo config prijme. `type` sa deklaruje
len tam, kde sa z hodnoty odvodiť nedá — farba a voliteľné pole s defaultom `None`.

Že popis má **každé** viditeľné pole, stráži `test_registry.py`.

**Formulár ponúka presne to, čo kód číta.** Každé pole configu musí engine, modul
stratégie alebo adaptér naozaj čítať — pole, ktoré sa dá ladiť a nič nerobí, je horšie
než žiadne. Stráži to `tradebot/tests/test_param_parity.py` (statická kontrola nad
kódom stratégie, `tradebot/core` a adaptérmi). Výnimky sú dve a obe sa deklarujú:

- **Pine vstup, ktorý port vedome nepoužíva** (alerty, tabuľky na graf TradingView) →
  do configu nepatrí: `REMOVED_INPUTS` v `meta.py` s dôvodom (test parity s Pine ho tak
  pozná menovite), a ak už v configu bol, aj `RETIRED_FIELDS`. Len výnimočne, keď ho
  profil musí niesť (IBS `state4MaxBars`, Pine „Rezerva"), → `INERT_INPUTS`: config ho
  drží, formulár ho neukáže. Test stráži aj opak: keď ho kód začne čítať, musí sa vrátiť
  do formulára.
- **Zrušené pole** → zmaž ho z configu aj `params.py` a pridaj do `RETIRED_FIELDS`
  (`meno -> dôvod`). Staré profily a behy ho nesú; `from_dict` ho s varovaním preskočí
  namiesto toho, aby profil odmietol.

### 2. Config — čísla a ich hranice

`config.py`: `@dataclass class MojaConfig(StrategyConfig)` s poľami a s tabuľkami ako
`ClassVar`. Keď stratégia Pine má, názvy polí sú zhodné s Pine identifikátormi — test
parity ich porovná:

| tabuľka | na čo |
|---|---|
| `SIZE_FIELDS` | veľkostné polia so `SizeSpec` a ich jednotkou (`abs`, `ticks`, `atr`, `pct`) |
| `ENUM_FIELDS` | polia s uzavretým zoznamom hodnôt; formulár si z enumu vezme aj ponuku |
| `CONSTRAINTS` | `min`/`max` — webapp aj CLI podľa nich odmietnu nezmysel |
| `PORT_ONLY_FIELDS` | polia, ktoré Pine nemá (`leverage`) — rozšírenia portu s defaultom zhodným s Pine správaním |
| `RETIRED_FIELDS` | zrušené polia (`meno -> dôvod`) — staré profily s nimi sa načítajú, pole sa preskočí |

Vlastné pravidlá (napr. „koniec okna musí byť za začiatkom") idú do `_problems()`.
`CONFIG_DIR = Path(__file__).parent / "configs"`.

Prahy píš v jednotkách, ktoré sa dajú preniesť: `atr` alebo `pct`. Prah v absolútnych
cenových bodoch znamená na BTC niečo iné než na EURUSD, takže stratégia s takými prahmi
sa nedá porovnať na inom trhu ([matica](../tester/AI_TESTING.md)).

### 3. Engine — celá logika

`engine.py`, trieda s `__init__(cfg, inst, chart_tf_minutes)`. Kontrakt je v
[`tradebot/core/engine.py`](../tradebot/core/engine.py) a je zámerne úzky:

```python
class MojaEngine:
    def __init__(self, cfg, inst, chart_tf_minutes):
        self.cfg, self.inst, self.chart_tf_minutes = cfg, inst, chart_tf_minutes
        self.history = BarHistory(maxlen=..., atr_len=...)
        #: predhistória grafu (okná, ATR) + indikátory s vlastnou predhistóriou na svojom TF
        self.warmup = (Warmup(chart_tf_minutes)
                       .add(f"ATR {cfg.atrLen}", self.history.atr_warmup_bars)
                       .add_seeded("Supertrend 10 @60m", supertrend.warmup_bars, 60, self._seed_st))
        #: koľko barov GRAFU treba, kým sú signály platné (Freqtrade startup_candle_count, min. 300)
        self.required_history = self.warmup.chart_bars

    def on_bar(self, bar, htf=None, ctx=None) -> EngineOutput: ...
    def final_drawings(self, bar) -> list[DrawCommand]: ...
```

- **`on_bar` sa volá presne raz na každý uzavretý bar grafu.** Engine je **čistý**: žiadne
  I/O, žiadny globálny stav, všetko v `self`. To je to, čo umožňuje, aby ten istý kód
  bežal vo Freqtrade backteste, v MultiCharts a v emulátore a dával rovnaké signály.
- **`ctx: MarketContext`** je to, čo engine sám nevie a musí mu to povedať adaptér: či je
  v obchodnom okne, aká je pozícia (`position_size`), ktoré ordery reálne bežia. Nikdy si
  pozíciu nedrž sám — adaptér ju pozná lepšie.
- **`EngineOutput`** nesie `orders` (`OrderIntent` s `TradePlan`), `drawings`, `events`
  a `close_session` (zavri všetko za trh, Pine `strategy.close(immediately=true)`).
  Engine sám **nikdy neobchoduje** — len povie, čo chce.
- **`TradePlan`** je plán obchodu: smer, vstup, SL, TP, veľkosť, `sl_distance`. Veľkosť
  počítaj z rizika (`inst.qty_for_risk(riziko, sl_distance)`), nie z pevného počtu kusov —
  inak sa výsledok nedá prepočítať na iný účet. **Trailing** patrí do `TradePlan.trailing`
  (`TrailingPlan`, prípadne potomok s vlastným `stop_price`); oba adaptéry ho berú odtiaľ,
  vo Freqtrade ho netreba písať znova.
- **Predhistória** (`tradebot/core/warmup.py`) má dve časti, ktoré sa nemiešajú:
  - **graf** — `Warmup.add`: okná histórie a indikátory na TF grafu. `chart_bars` je
    `required_history`, z neho Freqtrade `startup_candle_count` (minimum triedy **300**).
    Stavová logika (dni S/R úrovní, predošlá seansa, denný limit, životnosť zón) sa sem
    **nepočíta** — beh začína s prázdnym stavom tak ako vždy.
  - **indikátor na vlastnom vyššom TF** (skladaný z barov grafu, napr. IBS Supertrend/ADX,
    vyššie TF divergencie) — `Warmup.add_seeded(meno, warmup_bars, tf, seed)`. Počet barov
    **jeho** TF povie indikátor (`rma_bars`, `ema_bars`, `sma_bars`: Supertrend(10) = 40,
    ADX 14/14 = 111) a predhistóriu grafu **nezväčšuje**. Adaptér pred prvým barom zavolá
    `seed_engine(engine, dáta, first_ms)`: z riadkov **pred** `first_ms` poskladá bary TF
    indikátora cez `tradebot.core.candles.resample_ohlcv` a `seed(uzavreté, rozpracovaný)`
    ich prehrá výpočtom a rozpracovanú periódu vloží do agregátora (metóda `prime`).
    Stav na prvom bare je tak ten istý ako po tých baroch naživo; dáta od `first_ms` ho
    neovplyvnia. `seed` smie ísť len pred prvým barom (inak `RuntimeError`).
  - kým indikátor nemá `warmup_bars` barov svojho TF (bez dát pred behom), smer nepovolí
    a hlási „SA ROZBIEHA".

  Kde sa seeduje: **Freqtrade** backtest/hyperopt — sviečky TF behu pred prvým riadkom
  DataFrame z disku (dátový handler, bez vypchávky; `_seed_runner`); **dry-run a live** —
  TF indikátorov si stratégia vypýta cez `informative_pairs()`, runner začne na prvom riadku
  DataFrame od burzy zarovnanom na ich periódy (ak za ním ostane `startup_candle_count`
  sviečok) a seeduje sa z uzavretých barov od DataProvidera pred ním; TF mimo burzy, málo
  sviečok pre limit burzy alebo nezarovnaný štart → sviečky TF behu z histórie burzy
  (`Exchange.get_historic_ohlcv`), poskladané cez `tradebot.core.candles`. Signál z baru bez
  celej predhistórie grafu vstup neurobí; reštart aj diera v sviečkach postavia runner nanovo
  ([FREQTRADE.md](FREQTRADE.md#predhistória-v-dry-run-a-live)). `seed_engine` preto berie
  aj funkciu `need -> DataFrame` (každý indikátor iný zdroj).
  **Emulátor MultiCharts** — 1m dáta pred `from_ms` (predhistória grafu sa neemuluje ako
  doteraz). **Živá študia MultiCharts** — neseeduje: `CalcBar` beží na celej histórii
  grafu, indikátor sa rozbehne na nej; `StartCalc` vypíše, koľko hodín dát treba.
  Pevné `+ 40` × pomer TF do `required_history` nepíš — to je presne to, čo seeding nahrádza.
- **Kresli, čo si spočítal.** Kresby nie sú ozdoba: sú jediné miesto, kde ostane **plán**
  obchodu tak, ako ho engine vypočítal (v `trades.json` je len to, čo Freqtrade nakoniec
  urobil). Bez TP/SL boxu nemá analytika vzdialenosť stopu ani plánovaný RR. Box musí mať
  `x1_ms = bar.time` baru signálu — tým sa páruje s obchodom.

### 4. Kresby a metadáta

`drawing.py`: vlastné druhy, `MOJ_DRUH = DrawKind.register("moj_druh", "MOJ_DRUH")`.
Generické druhy (`tp_box`, `sl_box`, `entry`, `exit`, `session`) registruje jadro.

`meta.py`: `REMOVED_INPUTS`, `INTENTIONAL_DEFAULT_DIFFS`, `FEATURES` (prepínač →
podnastavenia, ktoré formulár skryje, keď je vypnutý), `PARAM_NOTES`, `LAYERS` (`ChartLayer(id, titulok, druhy, farba)`),
`KIND_TITLES`. Vrstva smie obsahovať len **registrované** druhy a stratégia má naozaj
kresliť to, čo vo vrstve deklaruje — inak je vo webapp prepínač, ktorý nič nezapína.

### 5. Profily

`configs/<default_profile>.json` s `_title`, `_strategy: "moja"`, `_instrument` (kľúč
z `tradebot.core.types.INSTRUMENTS`) a **len odchýlkami** od Pine defaultov. Profil,
ktorý sa má na dvoch enginoch líšiť, má blok `_engine_overrides`
(`{"multicharts": {…}}`) — nie dva takmer rovnaké súbory.

### 6. Adaptéry (oba)

```python
# freqtrade.py
class MojaStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "moja"
    ENTRY_TAG_PREFIX = "moja:"      # tag = prefix + čas baru signálu v ms
    timeframe = "5m"

# multicharts.py
class MojaSignal(TradebotSignal):
    STRATEGY_KEY = "moja"
```

Plus dva súbory mimo balíka, ktoré sú len ukazovatele:

- `deploy/freqtrade/user_data/strategies/MojaStrategy.py` — prázdna podtrieda (Freqtrade
  resolver berie len triedu, ktorej `__module__` je názov súboru).
- `deploy/multicharts/Moja_Signal.py` — šablóna študie: trieda **bez rodiča**, metódy
  (`Create`, `CalcBar`, …) priamo v nej, delegujú na `MojaSignal`. Kompilátor MultiCharts
  x Python zdedené metódy nevidí; stráži to `test_multicharts_templates.py`.

Háky vo Freqtrade sú voliteľné a väčšina stratégií nepotrebuje ani jeden:
`_after_profile` (napr. `can_short` z parametra), `_feed_informative`, `custom_exit`.
Trailing nie je hák: generický `_trailing_stop` ho berie z plánu obchodu.

### 7. Registry

`tradebot/strategies/__init__.py`: import a riadok do `STRATEGIES`. V `__init__.py`
balíka najprv `from . import drawing` (registrácia druhov musí byť prvá), potom `SPEC`.

### 8. Testy

```bash
PY -m pytest tradebot/tests/test_registry.py tradebot/tests/test_param_parity.py tester/tests/test_pine_parity.py
```

Registry test je [tento checklist ako test](../tradebot/tests/test_registry.py): profil,
popis každého parametra, shim, šablóna, druhy vo vrstvách, FEATURES. Parity test porovná
config s Pine (názvy, defaulty, rozsahy) — a keď stratégia Pine nemá, ticho sa preskočí. K tomu napíš **test enginu na syntetických baroch** (vzor:
[`tradebot/tests/test_demo_engine.py`](../tradebot/tests/test_demo_engine.py)) — bez neho
je jediná kontrola logiky backtest, a ten povie „menej obchodov", nie „tu je chyba".

## Oba enginy: nie je odporúčanie, ale podmienka

Stratégia žije v dvoch svetoch: **Freqtrade** (krypto, futures, backtest a dry/live) a
**MultiCharts** (indexy, akcie, forex cez brokera). Nie sú to dva porty tej istej
myšlienky — je to **jeden engine** a dva tenké adaptéry, ktoré ho volajú. Práve preto sa
oplatí písať oba naraz: keď funguje jeden, druhý je trieda s tromi riadkami a šablóna.

Prečo to má byť podmienka:

- **Kontrola samej seba.** Keď sa tá istá logika prehrá dvoma nezávislými cestami a dá
  iné signály, jedna z nich je zle. Bez druhého enginu sa to nedozvieš.
- **Trhy.** Krypto futures a NAS100 sú iné režimy. Stratégia, ktorá drží len na jednom
  z nich, je vlastnosť toho trhu — a to je dobré vedieť skôr než neskôr.
- **Cena je nulová dopredu a vysoká spätne.** Dopísať MultiCharts vetvu k hotovej
  stratégii znamená znova prejsť všetky rozhodnutia, ktoré sa niekde tichým predpokladom
  opreli o Freqtrade a jeho fill model.

Čo sa v oboch **líši a líšiť má**: fill model. Signály sú rovnaké, ale ako sa order naplní
vnútri baru, je vec platformy. Preto sa každý beh púšťa s `--timeframe-detail 1m` a záver
pre MultiCharts patrí emulátoru, nie Freqtrade behu:

```bash
PY -m tester.webapp.cli run --strategy moja --profile moj_profil \
   --timerange 20250904-20260904 --engine freqtrade   --note "referencia"
PY -m tester.webapp.cli run --strategy moja --profile moj_profil \
   --timerange 20250904-20260904 --engine multicharts --note "ten isty profil emulatorom"
```

Rozdiel v počte obchodov medzi tými dvoma behmi má mať vysvetlenie. Keď ho nemá,
nie je hotová ani jedna vetva. Podrobne: [FREQTRADE.md](FREQTRADE.md) §G,
[MULTICHARTS.md](MULTICHARTS.md).

## Analytika a posudok: bez nich to nie je hotové

Kód, ktorý beží, hovorí len to, že beží. Otázka, ktorá rozhoduje, je iná — **aká je tá
stratégia, na čo sa hodí a či za tým vôbec niečo je**. Odpoveď má každá stratégia
v `tradebot/strategies/<key>/docs/ANALYTIKA.md` a vzniká jedným príkazom:

```bash
PY -m tester.webapp.cli checkup --strategy moja --profile moj_profil --timeframe 5m
```

Päť referenčných okien → charakter → skupiny obchodov → test proti náhode → slabnúci edge
→ Monte Carlo, z toho dva zoznamy („v čom je dobrá", „kde má chyby") a dokument. Čo presne sa meria
a prečo práve to: [ANALYTIKA.md](ANALYTIKA.md).

Aby sa dala zmerať celá, musí `SPEC` deklarovať štyri veci:

| chcem v analytike | v `SPEC` | bez toho |
|---|---|---|
| vzdialenosť stopu a plánovaný RR | `sl_kind`, `tp_kind` | tie dve vlastnosti sa nepočítajú |
| prepočet na iný účet, odporúčanie rizika | `risk_field`, `fixed_size_field` | Monte Carlo obchody len premieša |
| odkaz „preladiť tento parameter" | `hyperopt_cls` → `FEATURE_PARAMS` | analytika povie čo kazí výsledok, ale nie čím to zmeniť |
| odporúčaný priestor pre hyperopt | `hyperopt_cls` → `SUGGESTED`, `WARN` | `--suggested` nemá čo ponúknuť |

Na konci dokumentu je **posudok od AI** a ten k stratégii patrí rovnako ako čísla:
čísla povedia, čo sa stalo, posudok povie, čo si o tom myslieť. Odpovedá na šesť otázok —
kam sa stratégia hodí a kam nie, či má potenciál, čo treba dorobiť, čo otestovať ďalej,
či je vôbec použiteľná, a čo by sa dalo pridať. Píše ho AI (v Claude Code) do dokumentu
medzi značky `POSUDOK`; `cli checkup` ho pri prepočte prenesie a keď sa čísla medzitým
zmenili, označí ho za starý. Dokument bez posudku je tabuľka čísel, nie odpoveď.

## Stratégia s jadrom v C# (NinjaTrader)

NinjaTrader 8 Python engine nespustí — stratégia, ktorá má ísť aj tam, má `engine.py` nahradený
triedou v C# (`csharp/TradeBot.Strategies/<Meno>/`, atribút `[TradeBotEngine("kľúč")]`). V Python
balíku ostáva všetko ostatné (config, `params.py`, meta, profily, adaptérové triedy) a `SPEC` povie:

```python
engine_factory=csharp_engine_factory("kľúč"),          # tradebot.adapters.csharp
csharp_dir=CSHARP_DIR / "TradeBot.Strategies" / "Meno",
```

Zvyšok rámca (Freqtrade, emulátor MultiCharts, webapp, analytika, hyperopt) sa nemení — engine je pre
neho stále `on_bar() -> EngineOutput`. Testy parity parametrov čítajú pri takej stratégii C# zdrojáky
(`cfg.pole`) a `test_csharp_core.py` stráži, že C# config má každé pole s rovnakým defaultom.
Vzory sú `ibsnet` a `orbnet`; celé pravidlá, most a NinjaTrader adaptér: [NINJATRADER.md](NINJATRADER.md).

## Informatívny timeframe

Stratégia, ktorá potrebuje vyšší TF (IBS: detekčný TF zón), deklaruje `informative_tfs(cfg)`
a `htf_feeder(cfg, chart_tf)`. Feeder má `load(bars, extra)` pre Freqtrade (predpočítané
z informative dataframe), `feed(bar)` pre MultiCharts (Data2 po jednom) a `window_for(ts)`,
ktoré vráti to, čo engine dostane ako `htf`. Vzor: `tradebot/strategies/ibs/htf.py`.
Stratégia bez informatívneho TF dá `None` a engine dostáva `htf=None`.

Vyšší TF sa **vždy** skladá z 1m cez `tradebot/core/candles.py` — webapp graf, simulátor,
emulátor aj súbory pre Freqtrade. Keby sa to pravidlo rozišlo, porovnanie platforiem
prestane niečo znamenať.

## Ako to používajú adaptéry a webapp

- **Freqtrade**: `TRADEBOT_PROFILE` (názov z `configs/` stratégie alebo cesta k JSON),
  trieda zo shimu, `--timeframe` z webapp/CLI; stĺpce `tb_*`, `enter_tag` s prefixom
  stratégie.
- **MultiCharts**: šablóna študie, profil cez `PROFILE` v šablóne alebo `TRADEBOT_PROFILE`;
  Data2 len ak stratégia má informatívny TF; ordery `tb_sl`, `tb_tp`, `tb_session_end`.
- **Webapp**: select Stratégia prekreslí formulár a profily, beh nesie `settings.strategy`,
  história má stĺpec Stratégia (hľadanie `strat=moja`), graf berie vrstvy zo `SPEC.layers`.
- **CLI**: `python -m tester.webapp.cli run --strategy moja --profile <nazov|cesta> …`,
  `params --strategy moja`, `checkup --strategy moja`.

## Kedy je hotová

| # | čo | ako to overiť |
|---|---|---|
| 1 | balík, registry, popisy parametrov, shim, šablóna | `pytest tradebot/tests/test_registry.py` |
| 1b | každé pole formulára kód naozaj číta, inertné a zrušené sú deklarované | `pytest tradebot/tests/test_param_parity.py` |
| 2 | config sedí s Pine (ak Pine je) | `pytest tester/tests/test_pine_parity.py` |
| 3 | logika enginu | vlastný test na syntetických baroch |
| 4 | celý balík nič nerozbil | `pytest -q` (vrátane golden testov IBS) |
| 5 | beží vo Freqtrade | `cli run --strategy moja --engine freqtrade …` |
| 6 | beží v MultiCharts | `cli run --strategy moja --engine multicharts …` a rozdiel má vysvetlenie |
| 7 | analytika | `cli checkup --strategy moja …` → `docs/ANALYTIKA.md` |
| 8 | posudok | šesť otázok zodpovedaných v tom istom dokumente |

Až potom je odpoveď na otázku „čo tá stratégia je" v repozitári, a nie v hlave toho,
kto ju písal.

## Rozpracované zadania

Stratégia, ktorá sa ešte len má postaviť, má zadanie v `docs/zadania/` — úplné
natoľko, aby sa dalo otvoriť v samostatnom sedení bez ďalšieho kontextu. Dnes tam
žiadne otvorené nie je; [tržná štruktúra](zadania/STRUKTURA_strategia.md) je hotová
a v registry ako `structure`.

## Časté chyby

- **Zásah do jadra kvôli jednej stratégii.** Keď `tradebot/core` alebo adaptér potrebuje
  vedieť meno stratégie, návrh je zlý. Chýbajúcu informáciu pridaj do `StrategySpec`.
- **Popisy parametrov v Pine.** Pine sa robí len na vyžiadanie a formulár na ňom závisieť
  nesmie — titulky a tooltipy patria do `params.py` pri stratégii.
- **Prahy v absolútnych bodoch.** Fungujú presne na jednom trhu. `atr` alebo `pct`.
- **Pevný počet kontraktov.** Výsledok sa nedá prepočítať na iný účet a Monte Carlo
  nedá odporúčanie k riziku.
- **Vrstva grafu bez kresieb.** Prepínač, ktorý nič nezapína, je horší než žiadny.
- **Stratégia na 1m grafe.** Limity v baroch (`*MaxBars`) znamenajú na 1m inú stratégiu.
- **Záver z jedného okna.** Päť referenčných okien, a pozerá sa **znamienko po rokoch**,
  nie súčet.
- **Ladenie pred analytikou.** Hyperopt na stratégii, o ktorej nevieme, či je odlíšiteľná
  od náhody, nájde presne to, čo v tom okne bolo.

Súvisiace: [ANALYTIKA.md](ANALYTIKA.md) (analytika a posudok),
[TYPY_STRATEGII.md](TYPY_STRATEGII.md) (charakter a čo z neho vyplýva),
[HYPEROPT.md](HYPEROPT.md) (ladenie), [ARCHITEKTURA.md](ARCHITEKTURA.md) (prehľad a cesta
dát), [ARCHITECTURE_port.md](ARCHITECTURE_port.md) (návrh),
[../tester/AI_TESTING.md](../tester/AI_TESTING.md) (testovanie z CLI).
