# Parita IBSNinja (C# jadro) s IBS (Python) — 2026-09-20

`ibsninja` je prepis stratégie `ibs` do C# (`csharp/TradeBot.Strategies/IbsNinja` nad
`csharp/TradeBot.Core`), aby tá istá logika bežala natívne v NinjaTraderi 8 a zároveň pod Freqtrade
cez most `tradebot/adapters/csharp` ([NINJATRADER.md](../NINJATRADER.md)). Otázka merania: **dáva C#
jadro to isté čo Python engine?** Nie „podobné výsledky" — to isté, na každom bare.

Odpoveď: **áno, bez jediného rozdielu** — na úrovni enginu (bar po bare) aj na úrovni Freqtrade
backtestov (obchod po obchode).

## 1. Engine proti enginu, bar po bare

`python -m tester.compare.csharp_parity` prehrá oba enginy v tom istom `EngineRunner` (rovnaký model
vyplnenia, HTF feeder detekčného TF, seeding Supertrendu a ADX) a na každom bare porovná **na rovnosť**
ordery (vrátane plánu: vstup, SL, TP, veľkosť, trailing), kresby (druh, súradnice, farby, texty, id),
udalosti stavového automatu, koniec seansy, hodiny seáns a riadok signálu; na konci aj `final_drawings`
(S/R zhluky, Elliott). Čísla sa porovnávajú ako `double`, nie zaokrúhlené.

BINANCE BTCUSDT.P 3m, profil `docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl.json` a k nemu
**zapnuté všetko**, čo profil vypína: `showElliott`, `enableTrailing`, `tradeDirection=Indicator` so
Supertrendom aj ADX (60m, seedované), všetky tri seansy (Praha, New York, Londýn — teda aj prechody
letného času v troch pásmach).

| okno | barov | vstupov | orderov | udalostí stavu | kresieb | rozdielov |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 175 680 | 102 | 967 | 13 289 | 231 962 | **0** |
| 20221001-20231001 | 175 680 | 68 | 1 223 | 15 307 | 233 479 | **0** |
| 20231001-20241001 | 176 160 | 78 | 942 | 13 838 | 239 819 | **0** |
| 20240904-20250904 | 175 680 | 89 | 927 | 13 356 | 244 577 | **0** |
| 20250904-20260904 | 175 322 | 82 | 910 | 13 524 | 242 267 | **0** |

(Posledné okno malo navyše zapnutý `useVolumeFilter`.) K tomu referenčný profil
`golden_binance_btcusdt_3m` na celých piatich rokoch naraz (2021-10-01 – 2026-09-04): 863 642 barov,
945 vstupov, 2 841 orderov, 22 914 udalostí, 731 035 kresieb — **0 rozdielov**. Golden okno proti
TradingView (2026-08-24 – 09-04) sedí aj cez druhý transport (`TRADEBOT_CSHARP_BRIDGE=stdio`,
`TradeBot.Host.exe` ako samostatný proces).

## 2. Freqtrade backtesty v histórii Testera

Tie isté behy, aké robí tester: `cli run`, `--timeframe-detail 1m`, poplatok 0,05 % na stranu,
peňaženka 10 000, profil `btcusdt_3m_binance_ny_sl` bez zmien. Každé okno dvakrát — `--strategy ibs`
a `--strategy ibsninja`.

| okno | obchodov | PnL | PF | WR | max DD | break-even | beh `ibs` | beh `ibsninja` |
|---|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 28 | +12,54 % | 2,285 | 39,29 % | 3,591 % | 0,2615 % | `20260919-220857-e958be` | `20260919-220924-f33e95` |
| 20221001-20231001 | 34 | +1,37 % | 1,146 | 32,35 % | 4,074 % | 0,0707 % | `20260919-220744-7c2cb2` | `20260919-220813-c8cff4` |
| 20231001-20241001 | 37 | −3,10 % | 0,770 | 27,03 % | 6,652 % | 0,0078 % | `20260919-220643-e75cf8` | `20260919-220708-6d1506` |
| 20240904-20250904 | 28 | +4,49 % | 1,462 | 46,43 % | 3,718 % | 0,1341 % | `20260919-220532-d4685b` | `20260919-220559-90029a` |
| 20250904-20260904 | 22 | +7,88 % | 2,438 | 54,55 % | 2,376 % | 0,2227 % | `20260919-220413-134bdd` | `20260919-220445-9886a0` |

V každom riadku sú čísla oboch behov **totožné**, preto je stĺpec len jeden. Nie je to zhoda súhrnov:
`csharp_parity --runs <ibs> <ibsninja>` porovnáva `trades.json` obchod po obchode (časy otvorenia
a zatvorenia, ceny, veľkosť, zisk, dôvod výstupu, stop, extrémy) — všetkých 149 obchodov sedí presne;
líši sa len prefix v `enter_tag` (`ibs:` / `ibsninja:`).

### Druhý engine: emulátor MultiCharts, NAS100

Most nie je len pre Freqtrade — C# engine beží aj v emulátore MultiCharts (iný trh, iný tick, dáta
z Dukascopy, iný fill model). `cli run --engine multicharts --pair NAS100/USD`, profil
`docs/profily_archiv/ibs/nas100_dukas_3m.json`, okno 20240904-20250904: `ibs` (`20260919-221817-03e8f3`)
aj `ibsninja` (`20260919-221830-26e65a`) dali 157 obchodov, +69,93 %, PF 1,321, max DD 27,764 % —
opäť **zhodné obchod po obchode**.

### Iný runtime: Mono na Linuxe (cesta pre macOS)

`tester.compare.csharp_replay`: na Windows nahraných 44 164 volaní C# enginu aj s odpoveďami (BTC 3m,
2025-09-04 – 12-04, všetko zapnuté, tri seansy cez jesenný prechod času), na Linuxe (WSL Ubuntu 26.04,
Mono 6.14.1, jadro preložené `mcs`) prehraté a porovnané na rovnosť: **0 rozdielov**, cez `stdio`
(`mono TradeBot.Host.exe`, 4,8 s) aj cez pythonnet nad Mono (3,6 s). Časové pásma tam idú priamo cez
IANA mená, na Windows cez mapu na Windows ID — výsledok je rovnaký.

### NinjaTrader 8 — Strategy Analyzer proti Testeru

Prvý beh adaptéra v NinjaTraderi. MNQ 3m, 2026-03-01 – 09-10, profil `multicharts_mnq_3m`, dáta
**importované z nášho skladu** (`tester.ninjatrader export` → *Import Historical Data*, UTC), takže
NinjaTrader aj Tester videli tie isté 1m sviečky. Adaptér exportoval, čo engine chcel
(`TradeBot\logs\*.csv`), a `python -m tester.ninjatrader compare` to porovnal s tým istým C# enginom
prehratým v `EngineRunner` Testera:

| | NinjaTrader | Tester | zhodných |
|---|---|---|---|
| bary grafu / detekčného TF | 63 464 / 38 078 | — | — |
| vstupy (bar, cena, SL, TP, veľkosť) | 83 | 83 | **83** |
| prechody stavov zón 0–3 | 1 988 | 1 988 | **1 988** |
| všetky zámery (ENTRY/CANCEL/CLOSE) | 315 | 315 | — |

Signály teda sedia úplne — vrátane času barov (NinjaTrader značí bar zatvorením a v lokálnom pásme),
skladania 3m a 5m z 1m a hodín seáns. Výsledok obchodovania sa líši len fill modelom, ako má:

| | NinjaTrader Strategy Analyzer | emulátor MultiCharts (`20260919-231820-081b12`) |
|---|---|---|
| obchodov | 78 | 71 |
| čistý zisk (bez poplatkov) | +6 974 $ | +6 150 $ |
| profit factor | 1,87 | 1,861 |
| winrate | 65,38 % | 64,79 % |

Rozbor po jednom (export adaptéra proti referencii, každý order a každá udalosť):

- **Ordery 315 = 315**, z toho 314 zhodných do poslednej cifry (83 ENTRY, 227 CANCEL — 122 re-entry,
  79 koniec seansy, 22 mimo okna, 4 EXPIRED — a 5 CLOSE). Jediný rozdiel je *kedy* prišiel CANCEL
  `LONG_944` (3. 9.: Tester 10:00, NinjaTrader 19:45) — dôsledok toho, že sa v NinjaTraderi vyplnil.
- **Vyplnené vstupy: NinjaTrader 78** (= 78 obchodov v Strategy Analyzeri), referenčný model Testera 77,
  rovnaká zóna aj bar 76. Dva rozdiely, oba fill model, nie signál:
  - `LONG_482` (5. 6., limit 30 175,75): o 09:29 sa cena limitky presne **dotkla** (low = 30 175,75).
    Tester dotyk berie ako vyplnenie; NinjaTrader bez voľby *Fill limit orders on touch* chce, aby cena
    limitkou prešla — vyplnil až o 09:36 (low 30 173,25).
  - `LONG_944` (3. 9., vstup **Market** z pin baru/engulfingu, 29 177,25): NinjaTrader ho vyplnil na otvorení
    ďalšieho baru (29 177,00). Zjednodušený model v `EngineRunner` berie každý vstup ako limitku na
    dotyk a bar 09:45 mal high 29 177,00 < 29 177,25, takže ho nevyplnil vôbec. Tu má pravdu
    NinjaTrader — je to slabina referenčného modelu Testera (market vstup sa má vyplniť vždy), nie adaptéra.

**Oprava modelu (ten istý deň).** Pravidlo vyplnenia čakajúceho vstupu je teraz jedno a na jednom
mieste — `tradebot.core.orders.entry_fills`: market vždy, limitka za svoju cenu **alebo lepšiu** (aj keď
ju bar celý preskočí), stop zrkadlovo. Používa ho `EngineRunner` (model pre stavový automat vo
Freqtrade adaptéri) aj `FillSimulator` v `tester.compare.scan_trades` (golden testy). Po oprave sedí
referencia s NinjaTraderom na **315 z 315 orderov a 78 : 78 vyplnení**; ostáva len `LONG_482`, teda
dotyk proti prechodu limitky — nastavenie NinjaTradera, nie chyba. Čo sa tým zmenilo inde: **nič** —
golden testy proti TradingView prechádzajú a päť referenčných Freqtrade behov IBS
(`btcusdt_3m_binance_ny_sl`) vyšlo obchod po obchode rovnako ako pred opravou
(`20260919-2333…2335`, 149 obchodov). Prípad, ktorý oprava rieši, je vzácny: market vstup, ktorému
cena hneď po signáli ujde.

Na čo sa cestou prišlo (všetko je v `docs/NINJATRADER.md`): *Order fill resolution = High* NinjaTrader
pri stratégii s viac sériami nepovolí → adaptér si pridáva 1m sériu a ordery posiela na ňu; s
*Merge policy = Merge back adjusted* číta NinjaTrader pre staršie dátumy iné kontrakty, než sú
naimportované → beh bez dát, 0 orderov (treba *Do not merge*).

## 3. Rýchlosť

Ročný backtest (175 tisíc barov 3m, 1m detail), holý Freqtrade proces na tom istom stroji:

| | čas |
|---|---|
| `ibs` (Python engine) | 22,8 s |
| `ibsninja` (C# cez pythonnet) — prvá verzia | 38,4 s |
| `ibsninja` po oprave ukončenia procesu | **15,4 s** |

Samotný most stojí ~19 µs na bar (volanie do CLR + `json.loads` + stavba objektov), engine v C# je
rýchlejší než v Pythone. Tých 38 s nebol výpočet: pythonnet pri konci procesu až 20× prejde celú haldu
Pythonu a vo Freqtrade procese s 1m dátami to trvalo ~20 s. Vynechať jeho `unload` nejde (CLR potom pri
konci spadne na GIL, návratový kód 127 a webapp by beh označila za zlyhaný) — pomohlo schovať mu haldu:
`atexit.register(gc.freeze)` tesne pred `unload` (`tradebot/adapters/csharp/bridge.py`).

## Čo z toho plynie

- Všetko, čo je zmerané o `ibs` (analytika, merania po rokoch, hyperopt), platí pre `ibsninja` bez
  výhrady — pod Freqtrade je to ten istý stroj na signály.
- **Neplatí to automaticky pre NinjaTrader.** Signály budú rovnaké (to isté jadro), fill model nie:
  Strategy Analyzer plní limitky po svojom, trailing sa v adaptéri posúva na zatvorení baru a čas baru
  sa prepočítava zo zatvorenia na otvorenie. Adaptér sa prekladá proti DLL NinjaTradera
  (`python -m tradebot.adapters.ninjatrader check`), ale beh v NinjaTraderi zatiaľ nikto neurobil.
  Prvé porovnanie má byť počet zón a vstupov proti Freqtrade behu na tých istých dátach.
- Parita je vlastnosť, ktorá sa stráca potichu: každá zmena logiky v `ibs` sa musí urobiť aj
  v `csharp/…/IbsNinja`. Stráži to `tester/tests/test_csharp_parity.py` (syntetické bary so všetkým
  zapnutým, oba transporty, golden okno) a `tradebot/tests/test_csharp_core.py` (C# config má každé
  pole Python configu s rovnakým defaultom).

## Ako to zopakovať

```bash
PY -m tester.compare.csharp_parity --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl.json \
   --from 2025-09-04 --to 2026-09-04 --set showElliott=true --set enableTrailing=true \
   --set tradeDirection=Indicator --set indAdx=true --set sess1On=true --set sess3On=true
PY -m tester.webapp.cli run --strategy ibsninja --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl.json \
   --timerange 20250904-20260904 --note "parita s ibs"
PY -m tester.compare.csharp_parity --runs <id behu ibs> <id behu ibsninja>
```
