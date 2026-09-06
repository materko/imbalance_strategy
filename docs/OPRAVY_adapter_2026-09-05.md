# Štyri opravy Freqtrade adaptéra (2026-09-05)

Revízia adaptéra po systematickom prechode Pine skriptu. Jadro (`tradebot/core`) sa
nemenilo — všetky nálezy sú v tom, ako adaptér prekladá engine na Freqtrade.
Prvé dve môžu meniť obchody, ďalšie dve sú správnosť a hygiena.

## 1. Freqtrade rušil limitky skôr než engine *(mení obchody)*

Engine drží nevyplnený order `state5MaxBars` barov (10 × 3m = **30 minút**) a Pine
tiež. Freqtrade config mal `unfilledtimeout.entry` **10 minút** a Coinbase config
nemal nič, teda Freqtrade default — tiež 10 minút. Vstupy vyplnené na 4. až 10. bare
po zadaní tak vo Freqtrade nevznikli, kým engine s nimi počítal (blokoval opačné
ordery, čakal na vyplnenie, na konci seansy posielal CLOSE).

Golden okno to neodhalilo, lebo všetkých šesť obchodov sa vyplnilo do troch barov.

Oprava má dve časti, lebo Freqtrade ruší podľa `unfilledtimeout` **nezávisle** od
callbacku — čo príde skôr, platí:

* `unfilledtimeout.entry = 30` v oboch configoch (test to stráži).
* Nový `check_entry_timeout` v stratégii replikuje STATE 5 presne: zruší po
  `state5MaxBars` sviečkach od otvorenia obchodu, alebo keď predchádzajúci bar už
  nebol v obchodnom okne. Stratégia pri štarte varuje, ak je config kratší.

## 2. Obchod mohol dostať SL/TP cudzieho signálu *(mení obchody)*

Freqtrade otvára obchod na sviečke **po** signáli a `custom_*` callbacky dostávajú
jej čas. Adaptér hľadal „posledný signál s časom ≤ otvorenie". Keď engine vygeneroval
signál aj na tej sviečke (iná zóna o bar neskôr — pri SD + S/R + likviditných zónach
bežné), obchod dostal SL, TP, veľkosť aj `in_trade_window` z toho novšieho.

Oprava: `enter_tag` už nie je konštanta `"ibs"`, ale `ibs:<čas baru signálu v ms>`.
Každý callback si signál vyhľadá podľa tagu (`EngineRunner.signal_at`); hľadanie
podľa času ostáva len ako záloha pre obchody bez tagu (force entry).

Pri analýze exportov si na to treba dať pozor: `enter_tag` je teraz pre každý obchod
iný, takže zoskupovanie podľa tagu treba robiť cez prefix.

## 3. Fill model runnera oživoval zavreté obchody *(správnosť, long only nemení)*

Runner si drží zjednodušený model vyplnenia, aby engine videl konzistentný svet.
Po zásahu SL/TP order označil ako „nevyplnený", ale nechal ho v evidencii — ďalší
bar, ktorý pretol vstupnú cenu, ho **vyplnil znova**. Engine potom videl fantómovú
pozíciu: pri `tradeDirection = Both` blokovala opačné vstupy („OPACNA POZICIA")
a na konci seansy vyrobila CLOSE bez reálneho obchodu. Pozícia bola navyše jedno
číslo, takže zavretie jedného z dvoch orderov vynulovalo aj druhý.

Na long-only profiloch to výsledok nemení (opačný smer sa neobchoduje). Order teraz
po zavretí z modelu vypadne a pozícia sa odvádza zo skutočne vyplnených orderov.

## 4. `maxDailyWins` sa vo Freqtrade nikdy neuplatnil

`MarketContext.daily_win_limit_reached` plnil len `tradebot.tools.scan_trades`; runner ho
nechával `False`. Doplnené podľa Pine: UTC deň, výhra = zavretie na TP, limit platí
od nasledujúceho baru (Pine počíta `dailyWinLimitReached` pred pripočítaním výhry
z aktuálneho baru). Bar so SL aj TP sa berie ako strata, rovnako ako v `scan_trades`.

S piatimi výhrami za deň a jednou pozíciou naraz sa limit prakticky nespustí —
je to oprava parity, nie výsledku.

## Čo sa vedome NEmenilo

Pin Bar a Engulfing majú v Pine market order; adaptér ich posiela ako limitku na
zatváracej cene sviečky patternu. Na Binance perp sa otváracia cena ďalšej sviečky
rovná zatváracej predchádzajúcej, takže rozdiel je nulový a golden test s Pin Barom
sedí. Ostáva to tak, kým sa neobjaví dôvod.

`_extremes` (vstup do trailingu) sa po výstupe obchodu uprace v `confirm_trade_exit`,
aby v dlhom live behu nerástol.

## Testy

* `tradebot/tests/test_freqtrade_runner.py` — fill model, denný limit, `signal_at`.
* `tradebot/tests/test_freqtrade_entries.py` — tag → signál, `check_entry_timeout`,
  config timeout, upratanie trailingu. Beží len s nainštalovaným Freqtrade.

Po týchto zmenách treba **znova prebehnúť backtesty** z `docs/*_2026-09-04.md`
a `SEANSY_2026-09-05.md`: oprava 1 pridá vstupy vyplnené medzi 4. a 10. barom,
oprava 2 môže zmeniť SL/TP obchodov, ktoré mali susedný signál.

---

# Výsledok po opravách

Prebehnuté s Freqtrade 2026.8, `--timeframe-detail 1m`, na tých istých piatich
oknách ako v [SEANSY_2026-09-05.md](SEANSY_2026-09-05.md) a
[FILTRE_vstupu_2026-09-04.md](FILTRE_vstupu_2026-09-04.md).

## Golden okno: parita drží

`btcusdt_3m_binance_tv` + S/R + likvidita, Aug 24 – Sep 4 2026, bez poplatkov:
**6 obchodov, 4W/2L**, PnL +187,8 / −480,8 / −57,1 / +504,97 / +62,8 / +201,3 —
presne to, čo je v [GOLDEN_binance_2026-08-24.md](GOLDEN_binance_2026-08-24.md).
Všetkých 300 testov prechádza, vrátane golden testov nad `scan_trades`.

## Profil `btcusdt_3m_binance_ny` (najlepšia konfigurácia)

Break-even poplatok (% na stranu), bez poplatkov, 1 BTC na obchod:

| okno | obchodov po | break-even pred | **po** |
|---|---|---|---|
| 2021-10 → 2022-10 | 39 | 0,207 | **0,2072** |
| 2022-10 → 2023-10 | 56 | 0,062 | **0,0568** |
| 2023-10 → 2024-10 | 46 | 0,014 | **−0,0023** |
| 2024-09 → 2025-09 | 40 | 0,082 | **0,0820** |
| 2025-09 → 2026-09 | 34 | 0,142 | **0,1332** |
| **spolu** | **215** (pred ~42/rok, teda ~208) | 0,0944 | **0,0879** |

SEANSY uvádza počty obchodov len ako priemer na rok, preto tu nie je porovnanie
po rokoch; sedem nových obchodov je rozobraných nižšie.

Hrubý profit factor cez päť rokov 1,838 (pred 1,945).

S reálnymi poplatkami (0,05 %/strana, peňaženka 10 000 USDT):

| okno | čistý pred | **čistý po** | max DD pred | **max DD po** |
|---|---|---|---|---|
| 2021-10 → 2022-10 | +11,09 % | **+11,09 %** | 4,93 % | **4,93 %** |
| 2022-10 → 2023-10 | +2,44 % | **+1,83 %** | 3,16 % | **3,85 %** |
| 2023-10 → 2024-10 | −1,69 % | **−3,37 %** | 5,66 % | **7,13 %** |
| 2024-09 → 2025-09 | +1,48 % | **+1,48 %** | 4,45 % | **4,45 %** |
| 2025-09 → 2026-09 | +5,86 % | **+5,92 %** | 2,38 % | **2,38 %** |
| **spolu** | +19,2 % | **+17,0 %** | max 5,7 % | **max 7,1 %** |

Štyri z piatich rokov ostávajú ziskové. Záver zo SEANSY platí, len s menšou rezervou:
break-even 0,088 % proti taker poplatku 0,05 %.

### Odkiaľ je rozdiel

Presne tam, kde ho oprava 1 predpovedala. Rozloženie oneskorenia vyplnenia vstupu
od zadania limitky ukazuje, že **pred opravou neexistoval ani jeden obchod vyplnený
neskôr než 9 minút** — Freqtrade ich rušil. Teraz ich je sedem:

| okno | vstupov > 9 min | ich PnL (1 BTC) |
|---|---|---|
| 2022-10 → 2023-10 | 3 | −105 |
| 2023-10 → 2024-10 | 2 | −810 |
| 2025-09 → 2026-09 | 2 | +652 |

Sedem obchodov za päť rokov, spolu −263 USDT — obchody, ktoré TradingView mal
a Freqtrade doteraz nie. Roky 2021-22 a 2024-25 sú identické, lebo v nich sa
žiadny order nevyplnil po štvrtom bare.

Oprava 2 (tag signálu) sa vo výsledkoch neprejavila samostatne: na týchto profiloch
sa susedné signály netrafili tak, aby obchod dostal cudzí SL. Je to poistka.

## Profil `btcusdt_3m_binance_struct` (obe seansy)

| okno | obchodov pred → po | break-even pred | **po** |
|---|---|---|---|
| 2021-10 → 2022-10 | 87 → 91 | 0,1398 | **0,1200** |
| 2022-10 → 2023-10 | 107 → 114 | −0,0032 | **−0,0056** |
| 2023-10 → 2024-10 | 106 → 111 | 0,0156 | **0,0105** |
| 2024-09 → 2025-09 | 96 → 95 | 0,0397 | **0,0404** |
| 2025-09 → 2026-09 | 82 → 85 | 0,0568 | **0,0600** |
| **spolu** | 478 → **496** | 0,0423 | **0,0396** |

Rovnaký obraz: o pár obchodov viac, edge o kúsok menší, poradie záverov sa nemení
(Londýn edge nemá, NY áno).

### Drobnosť, ktorá nie je chyba

Dva obchody v roku 2023-24 majú dôvod výstupu `trailing_stop_loss`, hoci trailing
je vypnutý. Limitka na 41 319,4 sa vyplnila na otváracej cene 41 299,6 (trh medzitým
klesol pod ňu), takže plánovaný SL 41 302,4 skončil **nad** vstupom a Freqtrade ho
spustil hneď — a keďže sa stop od otvorenia obchodu zmenil (pôvodne −99 %), označí
to ako trailing. Pine limitku plní rovnako „na limite alebo lepšie" a stop nad cenou
by tiež spustil okamžite. Výsledok je +11 a +36 USDT, teda šum.

## Ako to zopakovať

```bash
TRADEBOT_PROFILE=btcusdt_3m_binance_ny .venv/Scripts/python.exe -m freqtrade backtesting \
  --config platforms/freqtrade/config.binance.json \
  --userdir platforms/freqtrade/user_data --strategy IBSImbalanceStrategy \
  --timeframe-detail 1m --timerange 20250904-20260904 --cache none
```

Pre break-even pridaj `--fee 0 --dry-run-wallet 400000` a výsledok prežeň cez
`python -m tradebot.tools.fees`. Jeden rok trvá zhruba 30 sekúnd.
