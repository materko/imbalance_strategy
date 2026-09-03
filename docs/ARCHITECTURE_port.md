# Architektúra portu: Pine → spoločné jadro → Freqtrade + MultiCharts

Cieľ: **jedna implementácia logiky**, dva tenké adaptéry. Rovnaké obchody aj rovnaké vykreslovanie
na oboch platformách aj v TradingView.

Referenčný zdroj pravdy: [`imbalance_strategy_FULL.pine`](../imbalance_strategy_FULL.pine) +
[`tv_settings_2026-09-03.md`](tv_settings_2026-09-03.md).

---

## 1. Kľúčové zistenie, ktoré určuje celý dizajn

Stratégia **nie je vektorizovateľná**. Je to *stavový automat na každú zónu zvlášť*
(`STATE 0 → 1 → 2 → 3 → 4 → 5`, Pine riadky **1548–2270**): zóna vznikne, hľadá sa v nej gap,
čaká sa na výstup z nej (max `state1MaxBars`), na potvrdenie (max `state2MaxBars`), na retest
(max `state3MaxBars`), potom sa položí order a čaká sa na vyplnenie (max `state5MaxBars`).
Každý krok závisí od výsledku predchádzajúceho a od toho, čo sa medzitým stalo s inými zónami
(`oppositeOpen`, `oppositePending`, `maxDailyWins`, `invalidateOnFill`).

Preto:

> **Jadro je bar-by-bar event engine, nie pandas pipeline.**
> `engine.on_bar(bar) -> EngineOutput`

To sedí priamo na MultiCharts (`CalcBar()` sa volá raz za bar) a do Freqtrade sa dostane tak,
že adaptér prebehne engine v cykle nad DataFrame a výsledok zapíše do stĺpcov.
Vektorizovať sa dajú len čisté indikátory (pivoty, ATR, SMA volume) — tie sú v `core/ta/`.

---

## 2. Rozdelenie balíka

```
ibs/
├── core/                        # ŽIADNY import z freqtrade ani MultiCharts
│   ├── types.py                 # Bar, Zone, PendingOrder, TradeRecord, Direction, ZoneState
│   ├── config.py                # IBSConfig — 1:1 všetkých 115 Pine inputov + from_dict/from_json
│   ├── clock.py                 # sessions 1–3 (TZ, zone window, trade window), weekdaysOnly
│   ├── ta/
│   │   ├── swings.py            # pivot high/low — spoločné pre structureSwingLen/srSwingLen/liqSweepLen/ewSwingLen
│   │   ├── structure.py         # BOS / CHoCH  → marketBias
│   │   ├── sr.py                # S/R zhlukovanie (srClusterPoints, srMinTouches, srMaxLevels)
│   │   ├── liquidity.py         # sweep / stop hunt
│   │   ├── elliott.py           # zigzag, číslovanie vĺn, projekcia
│   │   ├── patterns.py          # f_isPinBar, f_isEngulfing
│   │   └── imbalance.py         # detekcia gapu + minImbSizePoints + imbMaxDistTicks
│   ├── zones.py                 # SD zóny na detekčnom TF + f_push_zone() = spoločný vstup pre SD/SR/LQ
│   ├── statemachine.py          # lifecycle zóny STATE 0..5 → OrderIntent
│   ├── risk.py                  # SL (slLookback + slBufferTicks), TP (rrRatio), qty (maxLossDollar/tickDollarValue)
│   ├── trailing.py              # trailActivationR / trailOffsetR / trailFreqPct
│   ├── drawing.py               # DrawBox / DrawLine / DrawLabel / DashboardCell — platformovo neutrálne
│   └── engine.py                # IBSEngine.on_bar(bar, htf_bar=None) -> EngineOutput
│
├── adapters/
│   ├── freqtrade/
│   │   ├── IBSImbalanceStrategy.py   # IStrategy — populate_indicators/entry/exit
│   │   └── plotting.py               # DrawCommand → plot_config / plotly shapes
│   └── multicharts/
│       ├── IBS_Signal.py             # Create / StartCalc / CalcBar / Destroy — obchoduje
│       └── IBS_Indicator.py          # to isté, ale len kreslí (bez orderov)
│
└── tests/
    ├── golden/                  # export trade listu z TV + zoznam zón → fixtures
    └── test_parity.py           # engine musí reprodukovať TV bar po bare
```

### Pravidlo závislostí
```
adapters/freqtrade  ──┐
                      ├──►  core   (core neimportuje NIČ z adapters)
adapters/multicharts ─┘
```
`core` smie závisieť len od stdlib + `numpy` (a `pandas` maximálne v `ta/`, nie v `engine.py`).
MultiCharts beží cez Python.NET a inštalovať tam ťažké závislosti je bolesť.

---

## 3. Rozhranie jadra

```python
@dataclass(frozen=True)
class Bar:
    time: int          # ms epoch, čas OTVORENIA baru (Pine `time`)
    open: float; high: float; low: float; close: float
    volume: float

@dataclass
class EngineOutput:
    orders:   list[OrderIntent]    # ENTRY / CANCEL / MODIFY_SL / EXIT
    drawings: list[DrawCommand]    # boxy zón, labely BOS/CHoCH/SKIP/EXPIRED, čiary S/R…
    dashboard: DashboardState      # winrate, séria, pozícia, risk/obchod
    events:   list[EngineEvent]    # pre logovanie a golden testy

class IBSEngine:
    def __init__(self, cfg: IBSConfig, tick_size: float, chart_tf_minutes: int): ...
    def on_bar(self, bar: Bar, htf_bar: Bar | None = None) -> EngineOutput: ...
    def on_fill(self, order_id: str, price: float, qty: float) -> None: ...
    def on_exit(self, order_id: str, price: float, reason: str) -> None: ...
```

Engine je **čistý**: žiadne I/O, žiadny `print`, žiadne globálne stavy. Všetko, čo si pamätá,
je v `self`. To ho robí testovateľným aj deterministickým.

### Prečo HTF okno, nie jeden HTF bar
`zoneDetectionTF = "5"`, ale graf beží na 3m. Pine to rieši jedným `request.security()`
(riadok **338**) — a je dôležité, **čo presne** si ťahá:

```pine
[o5_0, c5_0, h5_0, l5_0, t5_0,  o5_1, ...,  o5_2, ...,  o5_3, ..., t5_3,  v5_0, v5_1, v5_2, v5Sma]
    = request.security(syminfo.tickerid, zoneDetectionTF,
        [open[1], close[1], high[1], low[1], time[1],   // posledný UZAVRETÝ 5m bar
         open[2], ...,  open[3], ...,  open[4], ..., time[4],
         volume[1], volume[2], volume[3], ta.sma(volume, volSmaLen)[1]],
        barmerge.gaps_off, barmerge.lookahead_off)
```

Čiže engine potrebuje **rolling okno posledných 4 uzavretých HTF barov** (`[1]`..`[4]`) plus
`SMA(volume, volSmaLen)` — nie jeden bar. Všetko je offsetnuté o `[1]` a `lookahead_off`,
takže **žiadny repaint**: pattern sa vyhodnocuje výlučne z uzavretých 5m barov.

```python
def on_bar(self, bar: Bar, htf: HTFWindow | None = None) -> EngineOutput: ...

@dataclass
class HTFWindow:
    bars: list[Bar]      # [1]..[4], index 0 = posledný uzavretý
    vol_sma: float       # ta.sma(volume, volSmaLen)[1]
```

- **Freqtrade**: `informative_pairs()` + `merge_informative_pair()` na 5m, potom `.shift(1..4)`
- **MultiCharts**: druhá dátová séria (Data2) na 5 min, `self.Bars.Open[1..4]` na Data2

`htf` je `None`, kým nie sú k dispozícii aspoň 4 uzavreté HTF bary.

**`snapMode`** (Pine riadok **276**) zarovnáva začiatok zóny na grid aktuálneho TF:
```python
out = t if snap == 'Off' or step_ms <= 0 else int(floor|ceil|round(t / step_ms) * step_ms)
```
Musí byť bit-identické (vrátane celočíselnej aritmetiky v ms), inak sa zóny nakreslia inde.

---

## 4. Adaptér: Freqtrade

Problém: `populate_indicators()` sa v dry/live volá opakovane nad rastúcim DataFrame.
Prehnať engine od nuly pri každom volaní je pomalé a v backteste zbytočné.

```python
class IBSImbalanceStrategy(IStrategy):
    timeframe = '3m'
    informative_timeframe = '5m'          # = cfg.zone_detection_tf
    process_only_new_candles = True
    can_short = True                       # potrebné pre tradeDirection != "Long only"
    startup_candle_count = 300

    def informative_pairs(self):
        return [(p, self.informative_timeframe) for p in self.dp.current_whitelist()]

    def populate_indicators(self, df, metadata):
        pair = metadata['pair']
        eng, done = self._engines.setdefault(pair, (IBSEngine(CFG, ...), 0))
        # spracuj LEN nové bary → inkrementálne, engine si drží stav
        for i in range(done, len(df)):
            out = eng.on_bar(Bar.from_row(df.iloc[i]), htf_bar=self._htf_for(df, i))
            self._record(df, i, out)          # zapíš do stĺpcov ibs_entry_long / ibs_sl / ibs_tp / ...
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df['ibs_entry_long'] == 1,  ['enter_long',  'enter_tag']] = (1, 'ibs_imb')
        df.loc[df['ibs_entry_short'] == 1, ['enter_short', 'enter_tag']] = (1, 'ibs_imb')
        return df

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kw):
        return self._engines[pair][0].stoploss_for(trade)   # trailActivationR/trailOffsetR
```

- **SL/TP**: `use_custom_stoploss = True` + `custom_exit()` na TP. Nie statický `minimal_roi` —
  TP je `rrRatio × SL distance`, teda per-trade.
- **Position sizing**: `custom_stake_amount()` z `maxLossDollar / (sl_distance_ticks × tickDollarValue)`.
- **Kreslenie**: `DrawCommand` → `plot_config` nezvládne boxy, takže na verifikáciu použijeme
  vlastný plotly export (`adapters/freqtrade/plotting.py`) — vygeneruje HTML graf s rovnakými
  boxmi/labelmi ako TradingView.

---

## 5. Adaptér: MultiCharts

MultiCharts Python študia je trieda so životným cyklom `Create → StartCalc → CalcBar → Destroy`,
postavená nad PowerLanguage .NET API.

```python
class IBS_Signal(SignalObject):
    def __init__(self, ctx): super().__init__(ctx)

    def StartCalc(self):
        self.eng = IBSEngine(load_config(), tick_size=self.Bars.Info.MinMove/self.Bars.Info.PriceScale,
                             chart_tf_minutes=self.Bars.Info.Resolution.Size)
        self.buy  = self.MarketPosition_at_broker  # ...
        self.draw = MCDrawSink(self)

    def CalcBar(self):
        bar = Bar(self.Bars.Time[0], self.Bars.Open[0], self.Bars.High[0],
                  self.Bars.Low[0],  self.Bars.Close[0], self.Bars.Volume[0])
        out = self.eng.on_bar(bar, htf_bar=self._data2_bar())
        self.draw.render(out.drawings)          # DrawBox → self.DrwRectangle.Create(...)
        for o in out.orders:
            self._place(o)                       # → self.BuyOrder / SellShortOrder .Send()
```

- `CalcBar()` beží aj na historických aj na live baroch — presne ako Pine.
- `IntrabarOrderGeneration` = zapnúť, ak chceme replikovať `calc_on_every_tick=true` (viď §7).
- Kreslenie: `DrwRectangle` / `DrwTrendLine` / `DrwText` — mapovanie je 1:1 s `DrawCommand`.
- **Pozor na GIL**: MultiCharts optimalizácia v Pythone je výrazne pomalšia než PowerLanguage/C#.
  Na optimalizáciu parametrov použijeme radšej Freqtrade `hyperopt` a do MultiCharts dáme výsledok.

---

## 6. Ako zabezpečíme, že to naozaj kreslí rovnako

`core/drawing.py` je celý zmysel spoločnej vrstvy. Engine nikdy nekreslí — len vráti príkazy:

```python
DrawBox(kind='sd_zone', x1=t1, y1=p1, x2=t2, y2=p2, dir=+1, state=ZoneState.WAITING)
DrawLabel(kind='skip', x=t, y=p, text='SKIP (SHORT)', reason='SMER VYPNUTY')
DrawLabel(kind='counter', x=t, y=p, text='3x')
```

Každý adaptér má `DrawSink`, ktorý to premení na natívne objekty. Farby/štýly sú v jednom
`core/drawing.py` slovníku, prevzatom z Pine sekcie *"DESIGN SYSTEM – zjednotena farebna paleta"*
(riadok 251 vo FULL súbore).

**Verifikácia = golden testy.** Z TradingView vyexportujeme List of Trades pre BTCUSD 3m
(referenčný beh: 17 obchodov, 8W/9L, 47 %) a uložíme do `tests/golden/`. Test prebehne engine
nad tými istými dátami a porovná: čas vstupu, smer, entry, SL, TP, qty, výsledok — a navyše
počet a súradnice nakreslených zón. Scény na ručnú kontrolu sú v
[`chart_reference_BTCUSD_3m.md`](chart_reference_BTCUSD_3m.md).

---

## 7. Rozdiely, ktoré treba vedome rozhodnúť

| # | Vec | Pine (TradingView) | Freqtrade | MultiCharts |
|---|---|---|---|---|
| 1 | `calc_on_every_tick=true` | prepočet na každom ticku | len uzavreté sviečky | `IntrabarOrderGeneration` |
| 2 | Limitné ordre + čakanie `state5MaxBars` | `strategy.entry` limit + GTD | Freqtrade nemá natívne pending limit ordre v backteste | natívne, `Send()` + `GTD` |
| 3 | OCO (SL a TP naraz) | natívne | `custom_exit` + `custom_stoploss` | natívne |
| 4 | `pyramiding=0` | max 1 pozícia | `max_open_trades=1` na pár | `MaxEntries` |
| 5 | Fill za `close` vs za skutočnú cenu | `process_orders_on_close=false` | fill na open ďalšej sviečky | konfigurovateľné |

**Bod 1 a 2 sú najväčšie riziko odchýlky.** Návrh: engine bude mať prepínač
`fill_model: 'close' | 'next_open' | 'intrabar'`, aby sme vedeli porovnať, ktorý model
najlepšie reprodukuje TradingView čísla, a ten použiť v oboch adaptéroch.

---

## 8. Poradie prác

1. `core/config.py` + `core/types.py` — všetkých 115 inputov ako dataclass, načítané z JSON
   (nastavenia z `tv_settings_2026-09-03.md` ako `configs/btcusd_3m.json`).
2. `core/clock.py` + `core/zones.py` — SD zóny na 5m, vrátane `snapMode`. **Prvý vizuálny milník:
   zóny sa kreslia na rovnakých miestach ako v TV.**
3. `core/ta/imbalance.py` + `core/statemachine.py` + `core/risk.py` — IMB entry model.
   Druhý milník: rovnaké entry/SL/TP.
4. Adaptér Freqtrade + golden test proti TV trade listu.
5. Adaptér MultiCharts.
6. Zvyšné moduly: Pin Bar entry (`enablePinBarEntry=true` v tvojom nastavení!), potom
   display-only moduly — Market Structure, S/R, Likvidita, Elliott.

Kroky 1–4 pokrývajú **všetko, čo v tvojom aktuálnom nastavení reálne ovplyvňuje obchody**,
okrem Pin Baru. `enableSrTrading=false`, `enableLqTrading=false`, `useStructureFilter=false`,
`showElliott=false` → tie moduly sú zatiaľ čisto vizuálne a môžu ísť naposledy.

---

## 9. Otvorené otázky

1. **Freqtrade: spot alebo futures?** `tradeDirection` má „Short only" aj „Both" — shorty
   vyžadujú futures (`can_short`, `trading_mode: futures`). Aktuálne máš „Long only",
   takže spot by stačil, ale jadro to musí vedieť oboje.
2. **`tickDollarValue = 0.5`** — vyzerá to na hodnotu z futures kontraktu (MNQ?). Pre BTCUSD
   na Coinbase to dá zlé `qty`. Treba potvrdiť, čím sa má na krypte nahradiť.
3. **Ktorý fill model** (§7) berieme ako referenčný pri porovnávaní s TradingView.

---

**Zdroje k MultiCharts Python API:**
[MultiCharts × Python](https://www.multicharts.com/trading-software/index.php?title=Category:MultiCharts_x_Python) ·
[How to Integrate Python with MultiCharts](https://www.multicharts.com/trading-software/index.php?title=How_to_Integrate_Python_with_MultiCharts) ·
[How Python Studies are Calculated and Optimized](https://www.multicharts.com/trading-software/index.php?title=How_Python_Studies_are_Calculated_and_Optimized_in_MultiCharts)
