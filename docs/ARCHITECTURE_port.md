# Architektúra portu: Pine → spoločné jadro → Freqtrade + MultiCharts

Cieľ: **jedna implementácia logiky**, dva tenké adaptéry. Rovnaké obchody aj rovnaké vykreslovanie
na oboch platformách aj v TradingView.

Referenčný zdroj pravdy: [`pine/imbalance_strategy_FULL.pine`](../pine/imbalance_strategy_FULL.pine) +
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
│   ├── trailing.py              # trailActivationR / trailOffsetR
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

## 3b. Inštrument nie je konštanta — `InstrumentSpec`

MultiCharts pobeží na MNQ, akciách a možno forexe; Freqtrade na crypte. Tie sa líšia
v troch veciach, ktoré má Pine zadrátované do inputov:

```python
@dataclass(frozen=True)
class InstrumentSpec:
    tick_size: float          # syminfo.mintick  (MNQ 0.25 | BTCUSD 0.01 | EURUSD 0.00001 | akcie 0.01)
    point_value: float        # $ za pohyb o 1.0 ceny, na 1 kontrakt/jednotku
    qty_step: float           # MNQ 1 | BTC 0.001 | forex 0.01 lotu | akcie 1
    min_qty: float
    has_real_volume: bool     # forex = False (len tick volume) -> useVolumeFilter je nezmyselný
```

Získa sa z platformy, nezadáva sa ručne:
- **MultiCharts**: `tick_size = MinMove/PriceScale`, `point_value = BigPointValue`
- **Freqtrade**: z `exchange.get_pair_quote_currency()` + market info (`precision`, `contractSize`)
- **Pine (referencia)**: `syminfo.mintick`, `syminfo.pointvalue`

### Parametre v „points" musia dostať jednotku
Tieto inputy sú v absolútnych cenových bodoch a **nedajú sa preniesť medzi inštrumentmi**:

| Input | Hodnota | MNQ | BTCUSD @ 80 000 | EURUSD |
|---|---|---|---|---|
| `minImbSizePoints` | 2.5 | 2.5 bodu ≈ $5 | $2.5 = 0.003 % | nezmysel (2.5 = 250 000 pipov) |
| `srClusterPoints` | 15 | rozumné | $15 | nezmysel |
| `liqSweepMinWick` | 5 | rozumné | $5 | nezmysel |
| `ewMinWavePoints` | 20 | rozumné | $20 | nezmysel |
| `pbMinRangePoints` / `engMinRangePoints` | 2 | rozumné | $2 | nezmysel |

Riešenie — každý takýto parameter je `SizeSpec`, nie `float`:

```python
@dataclass(frozen=True)
class SizeSpec:
    value: float
    unit: Literal['abs', 'ticks', 'atr', 'pct']    # 'abs' = presné Pine správanie

    def resolve(self, inst: InstrumentSpec, price: float, atr: float) -> float: ...
```

Config profily potom vyzerajú takto a **`abs` zaručuje bit-identitu s TradingView**:
```
configs/mnq_3m.json       → {"minImbSizePoints": {"value": 2.5,  "unit": "abs"}}   # 1:1 s TV, ZÁKLAD
configs/btcusdt_3m.json   → {"minImbSizePoints": {"value": 0.25, "unit": "atr"}}   # prenositeľné
configs/<stock>_3m.json   → odvodené z mnq_3m.json
```

Odporúčanie: **na MNQ používaj `abs`** (aby sedelo s TV backtestom), na ostatné inštrumenty `atr`.
Tick-based inputy (`imbMaxDistTicks`, `state2ConfirmTicks`, `slBufferTicks`) sú už násobené
`syminfo.mintick`, takže tie sa prenášajú samy — problém sú len tie „points".

### Cieľové inštrumenty (rozhodnuté 2026-09-04)

| Profil | Freqtrade | MultiCharts | Rola |
|---|---|---|---|
| `btcusdt_3m_binance` | ✅ futures | ✅ | spoločný inštrument → **priama parita medzi platformami** |
| `btcusd_3m_coinbase` | ❌ (viď nižšie) | ✅ | **referenčný** — presne to, čo je na TV screenshotoch |
| `mnq_3m` | — | ✅ | **základ pre futures/akcie**, `unit: abs`, 1:1 s TV |
| akcie | — | ✅ | odvodené z `mnq_3m` |
| forex | — | (možno neskôr) | |

To, že **BTCUSDT beží na oboch platformách, je testovacia výhoda**: rovnaké dáta, rovnaký config,
dva adaptéry → ak sa výsledky rozídu, chyba je v adaptéri, nie v jadre. Toto bude náš
cross-platform smoke test (`tests/test_adapter_parity.py`).

### Burzy: Coinbase + Binance

`InstrumentSpec` dostane `venue` — jadro zostáva venue-agnostické, líši sa len spec a profil:

```
configs/btcusd_3m_coinbase.json    # tick 0.01 — zhodné s TV screenshotmi
configs/btcusdt_3m_binance.json    # tick 0.1  — perp
```

> ⚠️ **Freqtrade Coinbase nepodporuje.** V oficiálnom zozname búrz Coinbase **vôbec nefiguruje**
> (Binance, Bingx, Kraken, Kraken Futures, Kucoin, HTX, OKX, Gate.io, Bybit, Bitget, Hyperliquid,
> Bitvavo). Futures vedia len Binance, Bitget, Bybit, Gate.io, Hyperliquid, Kraken Futures, OKX.
> Cez ccxt by Coinbase možno bežal, ale **spot-only, netestovaný a bez `stoploss_on_exchange`** —
> čo je v rozpore s rozhodnutím #1 (futures).

Preto navrhujem takéto rozdelenie rolí — obe burzy zostávajú, každá robí to, čo vie:

| Burza | Rola | Freqtrade | MultiCharts |
|---|---|---|---|
| **Coinbase** `BTCUSD` | **referenčná / dátová** — presne to, čo je na TV screenshotoch, takže tu porovnávame paritu s TradingView | ❌ nepodporovaná | ✅ (cez data feed) |
| **Binance** `BTCUSDT` perp | **exekučná** — reálne obchodovanie, futures, shorty | ✅ futures isolated | ✅ |

Vo Freqtrade je aj tak **jedna inštancia = jedna burza**, takže by to boli dva configy;
takto máme namiesto duplicity zmysluplnú deľbu: Coinbase overuje *logiku* proti TV,
Binance obchoduje.

### ⚠️ Tick-based inputy nie sú venue-neutrálne

| | Coinbase BTCUSD | Binance BTCUSDT perp |
|---|---|---|
| `tick_size` | **0.01** | **0.1** (10× väčší) |
| `imbMaxDistTicks = 100` | $1 | **$10** |
| `slBufferTicks = 2` | $0.02 | **$0.20** |
| `state2ConfirmTicks = 1` | $0.01 | **$0.10** |

Tvária sa prenositeľne, ale nie sú. Ak sa má stratégia na Binance správať ako na Coinbase,
tieto tri hodnoty treba na Binance profile **vydeliť 10** (`imbMaxDistTicks: 10`,
`slBufferTicks: 1` — pozor, `state2ConfirmTicks` už nižšie ako 1 nejde, tam nastane
nevyhnutná odchýlka). Alternatíva: prepnúť ich tiež na `SizeSpec` s `unit: 'abs'`
a zadať rovno v dolároch — čistejšie a odporúčam to.

`tick_size` / `qty_step` sa **nezadávajú do configu ručne** — adaptér ich číta z burzy
(Freqtrade: `exchange.markets[pair]['precision']` / `['limits']`; MultiCharts: `MinMove/PriceScale`),
lebo burzy ich občas menia.

---

## 3c. Position sizing: `tickDollarValue = 0.5` je nastavené pre MNQ, na BTC nefunguje

Presný Pine kód (riadky **2010–2016**):

```pine
float rawSlDist          = typ == 1 ? (entryPrice - slPrice) : (slPrice - entryPrice)
float slDistTicks        = rawSlDist / syminfo.mintick
float slDollarPerContract = slDistTicks * tickDollarValue
orderQty := int(math.max(1, math.floor(maxLossDollar / slDollarPerContract)))
```

### Čo `tickDollarValue` je
**Koľko dolárov zarobíš/stratíš, keď sa cena pohne o jeden tick, na 1 kontrakt.**
Tick = najmenší možný pohyb ceny daného inštrumentu (`syminfo.mintick`).

Pre **MNQ** (Micro E-mini Nasdaq-100): tick = 0.25 indexového bodu, hodnota tiku = **$0.50**.
Tvoja hodnota `0.5` je presne toto — **config je vyladený na MNQ**, nie na BTC.

### Prečo to na BTCUSD tíško nefunguje
BTCUSD na Coinbase má `mintick = 0.01`. Ak tam necháš `tickDollarValue = 0.5`, vyjde
implicitná hodnota bodu $50/bod (namiesto $1/bod). Pri SL vzdialenosti ~$150:

```
slDistTicks = 150 / 0.01              = 15 000
slDollarPerContract = 15 000 × 0.5    = $7 500
orderQty = max(1, floor(350 / 7500))  = max(1, 0) = 1
```

→ `floor()` dá 0, `max(1, …)` to vytiahne na 1, takže **strategia vždy obchoduje qty=1
a limit $350 sa ticho ignoruje.** Preto je „RISK / OBCHOD: $350" na tvojom BTC grafe len kozmetika.

Na **BTCUSDT perp** (tick 0.1) to vyjde rovnako zle: `150/0.1 × 0.5 = $750`,
`floor(350/750) = 0 → 1`. Problém teda nezmizne prechodom na iný pár — treba opraviť vzorec.

### Návrh: nahradiť `tickDollarValue` za `point_value`
Matematika je totožná, ale prenositeľná — `point_value = tickDollarValue / tick_size`:

```python
qty_raw = max_loss_dollar / (sl_dist_price * inst.point_value)
qty     = max(inst.min_qty, floor(qty_raw / inst.qty_step) * inst.qty_step)
```

| Inštrument | `tick_size` | `point_value` | `qty_step` | pozn. |
|---|---|---|---|---|
| MNQ (Micro Nasdaq) | 0.25 | **2.0** | 1 | = dnešné `tickDollarValue 0.5` |
| ES / MES | 0.25 | 50 / 5 | 1 | |
| **BTCUSDT perp** | **0.1** | **1.0** | **0.001** | frakčné qty!; overiť na burze |
| EURUSD (1 štandardný lot) | 0.00001 | 100 000 | 0.01 | |
| Akcie US | 0.01 | 1.0 | 1 | |

Kľúčová zmena oproti Pine: **`qty_step` namiesto `int()`**. Pine zaokrúhľuje na celé kontrakty,
čo je správne pre futures a akcie, ale na crypte to zabíja risk management.
Pri BTC so `sl_dist = 150` a `point_value = 1` vyjde `qty = 350/150 = 2.333 → 2.333 BTC`
(zaokrúhlené na `qty_step 0.001`) — teda reálne riskovaných $350, ako má byť.

> ⚠️ Na Freqtrade futures navyše platí, že `custom_stake_amount()` vracia **stake v quote mene**,
> nie počet kontraktov — adaptér to musí prepočítať cez `leverage` a `contractSize`.

---

## 4. Adaptér: Freqtrade

Problém: `populate_indicators()` sa v dry/live volá opakovane nad rastúcim DataFrame.
Prehnať engine od nuly pri každom volaní je pomalé a v backteste zbytočné.

```python
class IBSImbalanceStrategy(IStrategy):
    timeframe = '3m'                       # NIE 1m - viď §7 bod 1
    timeframe_detail = '1m'                # rozlíšenie fillov v backteste
    informative_timeframe = '5m'           # = cfg.zone_detection_tf
    process_only_new_candles = True
    can_short = True                       # futures
    trading_mode = 'futures'
    margin_mode = 'isolated'
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
- **Position sizing**: `custom_stake_amount()` — viď §3c, `qty = maxLossDollar / (sl_dist × point_value)`.
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

**Bod 1 a 2 sú najväčšie riziko odchýlky.** Engine bude mať prepínač
`fill_model: 'close' | 'next_open' | 'intrabar'`, aby sme vedeli porovnať, ktorý model
najlepšie reprodukuje TradingView čísla, a ten použiť v oboch adaptéroch.

### Rozhodnuté: 1m detail, ale stratégia zostáva na 3m

Freqtrade na to má priamo `timeframe_detail`:

```
freqtrade backtesting --strategy IBSImbalanceStrategy --timeframe 3m --timeframe-detail 1m
```

Signály sa naďalej generujú na uzavretých **3m** sviečkach (presne ako v TV), ale vyplnenie
SL/TP/limitiek sa vnútri každej 3m sviečky prehráva po **1m** krokoch. To rieši aj bod 1 aj bod 5
a zároveň odstráni najhoršiu chybu backtestu — nejednoznačnosť „trafil SL alebo TP skôr?".

> ⚠️ **Nesmieme celú stratégiu prepnúť na `timeframe = '1m'`.** Všetky čakacie limity
> (`state1MaxBars=10`, `state2MaxBars=15`, `state3MaxBars=1`, `state5MaxBars=10`, `imbLookback=20`,
> `slLookback=10`) sú v **baroch, nie v minútach**. Na 3m grafe je `state2MaxBars=15` = 45 minút;
> na 1m by to bolo 15 minút — úplne iná stratégia. Preto `timeframe='3m'` + `timeframe_detail='1m'`.

MultiCharts ekvivalent: `IntrabarOrderGeneration = True` + druhá 1-min dátová séria.

---

## 8. Poradie prác

1. ✅ **hotové** — `core/config.py` + `core/types.py` + `InstrumentSpec`/`SizeSpec`: všetkých 115
   inputov ako dataclass, načítané z JSON profilov.
2. ✅ **hotové** — `core/clock.py` + `core/zones.py` + `core/drawing.py`: session okná, detekcia SD
   zón na detekčnom TF, `snapMode`, evidencia zón a ich boxy ako `DrawCommand`.
   Overené na reálnych dátach cez `python -m ibs.tools.scan_zones`.
3. ✅ **hotové** — `core/history.py`, `core/ta/{imbalance,patterns}.py`, `core/risk.py`,
   `core/statemachine.py`: celý STATE 0-5 vrátane re-entry, OCO, SKIP dôvodov, Pin Bar
   a Engulfing modelu. Overené cez `python -m ibs.tools.scan_trades`.
4. ✅ **hotové** — `core/engine.py` (`IBSEngine` ako jediný vstupný bod) +
   `adapters/freqtrade/`. Backtest dáva 5 obchodov zhodných s TradingView na minútu
   vyplnenia, vstupnú cenu, veľkosť aj výstup (`test_golden_tv_binance.py`).
5. ✅ **hotové** — `adapters/multicharts/`: `MCRunner` (bez PowerLanguage,
   testovateľný), `MCDrawSink` (`DrawCommand` → `Drw*`) a `signal.py` (jediný súbor,
   ktorý sa dotýka PowerLanguage API). Šablóna štúdie je v `platforms/multicharts/IBS_Signal.py`.
6. ✅ **hotové** — `core/ta/{structure,sr,liquidity,elliott}.py` + kreslenie životného
   cyklu objektov (`obj_id`, `DrawUpdate`, `DrawRegistry`) + plotly renderer
   `ibs/tools/plot.py`. Market Structure a likvidita sú overené proti TradingView
   (`test_golden_tv_draw.py`, 76 z 76 objektov).

Zostáva: preladiť ATR prahy exekučného profilu hyperoptom a rozhodnúť wallet/páku
(dnes sa stake oreže na ~1 % žiadanej veľkosti, takže `maxLossDollar` sa neuplatní).

---

## 9. Rozhodnutia (2026-09-04)

| # | Vec | Rozhodnutie |
|---|---|---|
| 1 | Freqtrade spot/futures | **futures** — `trading_mode='futures'`, `margin_mode='isolated'`, `can_short=True` |
| 2 | `tickDollarValue` | nahradiť za `point_value` v `InstrumentSpec` (§3c); `qty_step` namiesto `int()` |
| 3 | Fill model | `timeframe='3m'` + `timeframe_detail='1m'` (§7) — **nie** stratégia na 1m |
| 4 | Inštrumenty | **BTCUSDT na oboch platformách**; MultiCharts navyše **MNQ ako základ** pre futures/akcie → `InstrumentSpec` + `SizeSpec` (§3b) |
| 5 | Burzy | **Coinbase + Binance.** Coinbase = referenčná (parita s TV), Binance = exekučná (futures). Freqtrade Coinbase nepodporuje (§3b) |
| 6 | PickMyTrade | **neportuje sa** — Freqtrade aj MultiCharts posielajú ordre priamo. Vypadlo 5 vstupov: `pmtToken`, `pmtAccountId`, `pmtStratName`, `pmtMarketOrderType`, `trailFreqPct` |
| 7 | Golden fixture | export z TradingView pre **oba** grafy: `COINBASE:BTCUSD` (parita jadra) aj `BINANCE:BTCUSDT.P` (parita exekúcie) |
| 8 | Rozšírenia configu mimo Pine | `atrLen`, `legacyPineSizing`, `leverage`, `minSlDistance` — všetky s defaultom, pri ktorom je správanie zhodné s Pine; zoznam stráži `PORT_ONLY_FIELDS` a `test_pine_parity.py`. `minSlDistance` (2026-09-05) preskočí obchod s SL tesnejším než zadané % ceny / ATR — filter na pomer edge k poplatku, viď `docs/OPTIMALIZACIA_2026-09-05.md` |

### Čo z toho vyplýva pre multi-inštrument

- **Forex nemá reálny volume**, len tick volume → `useVolumeFilter` a `volMultiplier` sú tam
  nespoľahlivé. `InstrumentSpec.has_real_volume=False` → engine volume filter potichu preskočí
  a zaloguje to (namiesto toho, aby ticho pustil/zablokoval zlé zóny).
- **Akcie a MNQ majú RTH vs ETH.** Session okná (`sess1/2/3`) sú dnes definované ručne v TZ —
  to funguje, ale pre akcie treba pridať respektovanie sviatkov a skrátených dní (polovičné
  seansy okolo Thanksgivingu, Vianoc). `core/clock.py` dostane voliteľný `exchange_calendar`.
- **Forex nemá dennú medzeru rovnako** ako futures → `closeAtSessionEnd` a `weekdaysOnly`
  sa správajú inak; nedeľné otvorenie o 22:00 UTC patrí už do pondelka.
- **Konfig sa rozpadne na profily:** `configs/mnq_3m.json` (1:1 s TV, `unit: abs`),
  `configs/btcusd_3m.json`, `configs/eurusd_5m.json`, … Spoločná je len logika, nie čísla.

### Ešte otvorené

- Či na Binance profile **prepočítame tick-based inputy na `abs` v dolároch** (odporúčam),
  alebo ich necháme v tickoch a zmierime sa s 10× posunom oproti Coinbase.
- Ak by sa naozaj malo obchodovať aj na Coinbase cez Freqtrade, treba zvoliť inú podporovanú
  burzu so spotom (Kraken, Kucoin) alebo akceptovať netestovaný ccxt režim bez futures.
- Či pre MNQ chceme MultiCharts brať ako referenciu namiesto TradingView (obe sú futures dáta,
  takže by mali sedieť tesnejšie než BTC).
- **Funding rate** na perpetuáli — Pine ho nepozná vôbec. Pri `zoneValidHours=6` a intradenných
  obchodoch je vplyv malý, ale vo Freqtrade backteste sa započíta a v TV nie → malá systematická
  odchýlka, ktorú treba vedieť, aby sme ju nehľadali ako chybu v logike.

---

**Zdroje k MultiCharts Python API:**
[MultiCharts × Python](https://www.multicharts.com/trading-software/index.php?title=Category:MultiCharts_x_Python) ·
[How to Integrate Python with MultiCharts](https://www.multicharts.com/trading-software/index.php?title=How_to_Integrate_Python_with_MultiCharts) ·
[How Python Studies are Calculated and Optimized](https://www.multicharts.com/trading-software/index.php?title=How_Python_Studies_are_Calculated_and_Optimized_in_MultiCharts)
