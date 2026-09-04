# Hyperopt na BINANCE:BTCUSDT.P (3m) — 2026-09-04

Východiskom bol manuálny prieskum v TradingView na BTCUSD: RR 2,5, Long only,
všetky tri entry modely, S/R aj likviditné zóny zapnuté.

## Čo sa ladilo

Len tie parametre, ktoré **nie sú prevzaté z TradingView** — prahy v jednotke `atr`
(štartovacie odhady, viď ARCHITECTURE_port.md §3b), `rrRatio` a prepínače entry
modelov. Session okná, STATE timeouty ani sizing sa neladili; ich zmena by rozbila
paritu, ktorú stráži `test_golden_tv_binance.py`.

## Tri veci, ktoré museli byť opravené predtým

**Bez páky sa risk-based sizing nezmestí do peňaženky.** Backtest to hlásil ako
`stake orezany z 880751 na 9828 (1.1% z chceneho)` — `maxLossDollar` sa ticho
neuplatňoval. Pridané `IBSConfig.leverage`.

**`EngineRunner` je inkrementálny a drží stav.** Pri hyperopte by epochy ticho
počítali so starými parametrami. Teraz je cachovaný podľa odtlačku configu.

**`--analyze-per-epoch` je povinné.** Freqtrade počíta `populate_indicators` len raz
pre celý beh a per-epochu prepočítava iba `populate_entry_trend`. Celý náš engine
beží v `populate_indicators`, takže bez toho prepínača dalo prvých 200 epoch
**identický výsledok**.

**Vlastná loss funkcia.** Štandardný `CalmarHyperOptLoss` vyhlásil za víťaza epochu
so **7 obchodmi** za 90 dní a +17 %, len preto, že mala malý drawdown.
`IBSHyperOptLoss` pridáva spodný limit na počet obchodov.

## Sizing rozhoduje o tom, čo vlastne meriaš

TradingView bežal s Pine sizingom, ktorý na BTC vždy vráti `qty = 1 BTC`
(`floor(350 / (SLdist/0.1 × 0.5)) = 0 → max(1,0) = 1`), takže `maxLossDollar`
sa neuplatní. Risk-based sizing ($350 na obchod) je na obchodovanie správnejší,
ale robí z toho iný experiment — inak váži jednotlivé obchody, a teda aj PF.

Tie isté obchody na 365 dňoch (143 obchodov, WR 34,3 %):

| sizing | PnL | max DD |
|---|---|---|
| risk-based ($350/obchod) | −48,9 % | 66,7 % |
| legacy Pine (1 BTC) | −26,4 % | 57,0 % |

Preto sa ladilo s `legacyPineSizing`, aby bol výsledok porovnateľný s TradingView.

## Výsledok hyperoptu

300 epoch, okno 2025-09-05 → 2026-09-04, loss `IBSHyperOptLoss`.

| | risk-based sizing | legacy Pine sizing |
|---|---|---|
| ziskových epoch | 9 z 300 | **90 z 300** |
| epoch so ≥100 obchodmi | 204 | 215 |
| z toho ziskových | **0** | **63** |
| najlepší PF | 1,08 | **1,24** |

Najlepšia epocha (288): RR 1,7, `minImbSize` 0,43 ATR, `pbMinRange` 0,72,
`engMinRange` 0,93, `liqSweepMinWick` 0,59, `srCluster` 0,21, všetky štyri
prepínače zapnuté → **103 obchodov, +34,8 %, WR 44,7 %, DD 24,7 %, PF 1,24**.

### Čo je na parametroch stabilné

Medzi 63 ziskovými epochami so ≥100 obchodmi:

| parameter | rozloženie |
|---|---|
| `enablePinBarEntry` | **True v 63 z 63** |
| `enableEngulfingEntry` | **True v 63 z 63** |
| `enableLqTrading` | True v 53 z 63 |
| `enableSrTrading` | 36 / 27 — nerozhoduje |
| `rrRatio` | 2,6 (24×), 1,5 a 1,7 (po 16×) |

Bez Pin Baru a Engulfingu neexistuje ani jedna zisková konfigurácia s rozumným
počtom obchodov. To nezávisle potvrdzuje zistenie z TradingView, že Engulfing
pridáva výraznú hodnotu. Aj `rrRatio` sedí (TradingView 2,5, tu najčastejšie 2,6).

## Out-of-sample: profil neobstál

Parametre z epochy 288 pustené na roky, na ktorých sa **neladilo**:

| okno | obchodov | PnL | WR | max DD | PF |
|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 127 | −11,3 % | 35,4 % | 26,8 % | 0,91 |
| 2022-10 → 2023-10 | 161 | −50,1 % | 42,9 % | 50,5 % | 0,52 |
| 2023-10 → 2024-10 | 129 | −64,8 % | 35,7 % | 71,9 % | 0,60 |
| 2024-10 → 2025-09 | 90 | −56,4 % | 33,3 % | 59,8 % | 0,70 |
| **2025-09 → 2026-09** (ladené) | 103 | **+34,8 %** | 44,7 % | 24,7 % | **1,24** |

**Zisk existuje len na okne, na ktorom sa ladilo.** Všetky štyri predchádzajúce roky
sú stratové, tri z nich výrazne. Je to učebnicové pretrénovanie: 10 parametrov
a ~150 obchodov za rok je príliš málo dát na toľko stupňov voľnosti.

Profil `btcusdt_3m_binance_opt` preto **nie je odporúčaním na obchodovanie**.

## Čo z toho plynie

1. **Nastavenia entry modelov sa potvrdili** (Pin Bar + Engulfing povinné, RR ~2,5)
   — to je zistenie, ktoré prežilo aj naprieč rokmi, lebo nejde o jemné doladenie
   prahu, ale o zapnutie/vypnutie celého modelu.
2. **Konkrétne hodnoty ATR prahov sa nepotvrdili.** Sú vyladené na jeden rok.
3. Ďalší rozumný krok nie je viac epoch, ale **menej parametrov**: nechať ladiť
   len `rrRatio` a `minImbSizePoints`, zvyšok zafixovať. Menej stupňov voľnosti
   znamená menší priestor na pretrénovanie.
4. Alternatíva je **walk-forward**: ladiť na roku N, testovať na roku N+1, a pozerať
   sa na priemer týchto out-of-sample výsledkov namiesto jedného čísla.

## Ako to zopakovať

```bash
./platforms/freqtrade/scripts/hyperopt.sh 20250905-20260904 300
```

Podrobnosti v [RUNNING.md](RUNNING.md) §D2.
