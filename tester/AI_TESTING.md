# Testovanie z príkazového riadku (aj pre AI)

Tento súbor je návod pre kohokoľvek — človeka aj jazykový model —, kto má na tomto
repozitári **spúšťať behy a vyhodnocovať ich**, nie meniť kód. Je písaný tak, aby stačil
sám o sebe: čo spustiť, čo to znamená a čomu neveriť.

`PY` = Python z `.venv` (`.venv\Scripts\python.exe` na Windows, `.venv/bin/python` inde).
Všetko sa spúšťa **z koreňa repozitára**.

---

## 1. Čo je čo

| | |
|---|---|
| **stratégia** | logika (`--strategy ibs`, `demo_breakout`). Zoznam: `PY -m tester.webapp.cli params --help` |
| **engine** | čím sa beh prehrá: `freqtrade` (backtest Freqtradu) alebo `multicharts` (emulátor MultiCharts — ten istý runner, čo beží v štúdii) |
| **pár** | čo sa obchoduje: `BTC/USDT:USDT`, `ETH/USDT:USDT`, `NAS100/USD`… |
| **profil** | parametre stratégie (JSON). Bez neho sa berú Pine defaulty. |
| **timerange** | `YYYYMMDD-YYYYMMDD` |

Tie štyri veci sú nezávislé: tá istá stratégia s tým istým profilom sa dá prehnať oboma
enginmi na ktoromkoľvek páre, pre ktorý sú dáta. Práve to je podstata porovnávacích behov.

## 2. Jeden beh

```bash
PY -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --note "co tento beh testuje"
```

- **Vždy `--note`.** Bez poznámky je história na nič.
- `--set kluc=hodnota` mení jeden parameter (opakovateľné). Veľkostné polia sú
  `hodnota@jednotka` (`abs`, `ticks`, `atr`, `pct`), napr. `--set minSlDistance=0.25@pct`.
- `--engine freqtrade|multicharts` vyberie engine; bez neho sa vezme ten, pre ktorý sú dáta
  (pri Dukascopy symboloch emulátor, inak Freqtrade).
- `--pair`, `--timeframe`, `--fee`, `--wallet`, `--no-detail` podľa potreby.
- Ak beží webapp, beh ide do jej fronty a je vidno naživo; ak nebeží, CLI ho spustí priamo.
  Do histórie sa uloží tak či tak. **Beh spustený holým `freqtrade backtesting` sa do
  histórie nedostane.**

Zoznam parametrov stratégie s rozsahmi: `PY -m tester.webapp.cli params [filter]`.

## 3. Čítanie výsledkov

```bash
PY -m tester.webapp.cli list                       # posledné behy
PY -m tester.webapp.cli list "rrRatio>=4 pnl>0"    # rovnaká syntax ako hľadanie vo webapp
PY -m tester.webapp.cli show <run_id> [--json]
```

Kľúčové číslo je **break-even poplatok** (% na stranu): koľko smie burza brať, aby beh
vyšiel na nulu. Binance taker berie 0,05 %. PnL v % závisí od sizingu a peňaženky,
break-even nie.

## 4. Čomu neveriť

- **Jeden rok o stratégii nič nepovie.** Každý záver over na piatich referenčných oknách:
  `20211001-20221001`, `20221001-20231001`, `20231001-20241001`, `20240904-20250904`,
  `20250904-20260904`. Pozeraj **znamienko po rokoch**, nie súčet.
- **Beh s 0 obchodmi nie je výsledok.** Ak engine dal signály a nevznikol obchod, súhrn to
  napíše (`POZOR: …`) — typicky je malá peňaženka na profil s `legacyPineSizing`.
  Riešenie: `--wallet 1000000`, alebo profil s risk-based sizingom.
- **Profil musí sedieť s párom.** Prahy v bodoch (`abs`) platia pre podklad ako MNQ/NAS100;
  na ETH a forexe treba jednotku `atr`. BTC profil na ETH dá stovky nezmyselných obchodov —
  CLI aj webapp na to varujú, varovanie neignoruj.
- **Výsledky z rôznych enginov nie sú zameniteľné.** Signály sú rovnaké, fill model nie
  (Freqtrade vs. MultiCharts). Ladiť sa dá cez Freqtrade, ale záver pre MultiCharts over
  emulátorom — [docs/FREQTRADE.md §G](../docs/FREQTRADE.md).
- **Freqtrade beží na fiktívnej burze Tester** (`tester/ftexchange.py`), ktorá pozná naše
  páry aj všetky timeframy. Nie je to skutočný trh: poplatok zadávaš cez `--fee`, funding je
  nula a likvidácia sa nepočíta. Na porovnanie s reálnou burzou sú configy `config.binance*.json`.
- **Bez `--timeframe-detail 1m`** (CLI ho má zapnutý) sú fill ceny hrubé. `--no-detail` je
  len na rýchly odhad, nie do záverov.
- **Stratégiu nikdy nespúšťaj na 1m grafe** — limity `*MaxBars` sú v baroch, na 1m by to
  bola iná stratégia.

## 5. Monte Carlo: interval okolo výsledku a veľkosť účtu

Backtest dá jedno číslo. Koľko z neho je edge a koľko vzorka — a aký veľký musí byť účet,
aby ho séria strát neodpísala — povie bootstrap nad obchodmi hotového behu. Bez ďalšieho
backtestu, číta sa `runs/<id>/trades.json`:

```bash
PY -m tester.montecarlo                          # posledný beh v histórii
PY -m tester.montecarlo <run_id> --fee 0.05      # poplatok na stranu (default: ten z behu)
PY -m tester.montecarlo <run_id> --risk 250      # 250 USD rizika na obchod
PY -m tester.montecarlo <run_id> --account 25000 --limits 10,20,30
PY -m tester.montecarlo <run_id> --risk-pct 1    # riziko ako % z equity (zložené úročenie)
PY -m tester.montecarlo <run_id> --block 1       # nezávislé obchody namiesto blokov
```

Losuje sa **po blokoch** desiatich po sebe idúcich obchodov (`--block`). Straty totiž
nechodia rovnomerne: jeden režim trhu vyrobí päť SL za sebou a losovanie obchod po obchode
by takú sériu skoro nikdy nevyrobilo — a práve tá zabíja účet. Na tom istom behu je
rozdiel vidno: 95. percentil drawdownu 28,9 % pri `--block 1` a 32,9 % pri blokoch.

**Edge:** break-even poplatok — nameraný, medián, 90 % interval a `P(edge > poplatok)`.
Pri 161 obchodoch za päť rokov: 0,0995 %, interval 0,037–0,163 %, edge nad taker 0,05 %
s pravdepodobnosťou 90 %.

**Účet:** max drawdown (% z vrcholu), ako často účet klesne pod hranice −10/−20/−30/−50 %
počiatočného zostatku, pravdepodobnosť ruiny, najdlhšia séria strát, najdlhšie čakanie na
nové maximum a konečný zostatok. Veľkosť pozície sa preškáluje z rizika behu
(`maxLossDollar`) na `--risk`, takže rovnaká stratégia sa dá prepočítať na iný účet.
Na záver vypíše, **koľko sa smie riskovať**, aby 95 % ciest zostalo nad hranicou −20 %
(na spomínanom behu 71 USDT na obchod pri účte 10 000 a riziku 100).

Profil s `legacyPineSizing` (pevný počet kontraktov) sa preškálovať nedá — vtedy sa
počíta veľkosť z behu tak, ako je, a odporúčanie k riziku sa nevypíše.

Čo z toho **nevyplýva**:

- **Pretrénovanie to nemeria.** Obchody preladenej konfigurácie naozaj ziskové boli, chyba
  bola vo výbere najlepšej z dvesto epoch — proti tomu chránia len dáta, ktoré optimalizátor
  nevidel (§4, päť okien).
- **Počíta len uzavreté obchody.** Pozícia, ktorá išla hlboko proti a nakoniec vyšla na TP,
  je neviditeľná — pre margin a likvidáciu pri páke je pritom rozhodujúca.
- Nie sú tu denné limity strát (séria nemá dátumy), zmena režimu trhu ani korelácia medzi
  viacerými účtami na tej istej stratégii.

Pod 30 obchodov výpis sám napíše, že interval je príliš široký na akýkoľvek záver.

To isté je vo webapp v detaile behu — rozbaľovacia sekcia **Monte Carlo** s oboma
histogramami a poľami na účet a riziko ([docs/WEBAPP.md](../docs/WEBAPP.md)).

## 6. Porovnávacie behy

```bash
# engine offline nad burzovými dátami alebo surovým Dukascopy CSV (bez Freqtrade aj bez MultiCharts)
PY -m tester.compare.scan_trades --exchange binance --profile golden_binance_btcusdt_3m
PY -m tester.compare.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-01 --to 2025-01-31

# obchody zo skutočnej MultiCharts štúdie a ich spárovanie so simulátorom
PY -m tester.compare.mc_log_trades --from 2025-01-01 --to 2025-01-31
PY -m tester.compare.mc_compare --csv … --profile … --from … --to …

# parita s TradingView (golden testy) a s Pine zdrojom
PY -m pytest tester/tests/test_golden_tv_binance.py tester/tests/test_pine_parity.py
```

Ak padnú golden testy, kód alebo dáta nesedia s referenciou — **nahlás to, neopravuj
referenciu**.

## 7. Sweep: hľadanie parametra bez písania kódu

Mriežka behov cez hodnoty jedného či viacerých parametrov. Každý bod je **obyčajný
backtest** — uloží sa do histórie, dá sa otvoriť, porovnať aj prehnať Monte Carlom.

```bash
PY -m tester.webapp.cli sweep --param rrRatio=2:6:1    --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json    --timerange 20250904-20260904 --goal break_even --min-trades 20

PY -m tester.webapp.cli sweep --param rrRatio=3,5 --param slLookback=10,20,30    --goal winrate --max-dd 15 --timerange 20250904-20260904
```

Hodnoty sú buď rozsah `od:do:krok` (vrátane hornej hranice), alebo zoznam `a,b,c`
(aj `true,false`, `Long only,Both`, `0.25@pct`). `--param` sa dá opakovať — vznikne
kartézsky súčin. Strop nie je žiadny (`--max-runs 0`) — mriežka smie bežať cez noc alebo
na serveri. Cena je čas: každý bod je celý backtest, rok je asi 30 sekúnd, takže 40 bodov
na piatich referenčných oknách je hodina a pol. Vo webapp sa celá mriežka dá zrušiť jedným
tlačidlom, z CLI Ctrl+C.

K hotovej mriežke sa dá kedykoľvek vrátiť — je v histórii ako každý beh:

```bash
PY -m tester.webapp.cli sweeps                    # zoznam mriežok, od najnovšej
PY -m tester.webapp.cli sweeps --strategy ibs     # len mriežky jednej stratégie
PY -m tester.webapp.cli sweeps 20260909-185815    # tá istá tabuľka aj s poradím
```

Je jedno, či mriežka vznikla tu alebo vo webapp — v ponuke **Predošlá mriežka** aj v tomto
výpise je to isté.

**Kritérium hovorí, čo je lepšie** — bez neho sa „optimálne" nedá určiť:

| `--goal` | vyberá | kedy |
|---|---|---|
| `break_even` | najvyšší break-even poplatok | prednastavené; nezávisí od sizingu ani peňaženky |
| `profit` | najvyšší zisk v % | keď ide o výnos a drawdown stráži limit |
| `winrate` | najvyšší podiel ziskových | keď má byť séria strát krátka |
| `drawdown` | najnižší max drawdown | keď je hranicou účet, nie výnos |

K tomu mantinely `--max-dd` (strop na drawdown v %) a `--min-trades`. Body, ktoré ich
porušia, sa nezahodia — ukážu sa pod čiarou s dôvodom, nech je vidno, že optimum tam je,
len je mimo dohodnutých hraníc.

Výsledok je tabuľka zoradená podľa kritéria a id najlepšieho behu. **Než z neho spravíš
profil, prežeň ho ostatnými referenčnými oknami** (§4) — mriežka vie len to okno, na ktorom
bežala.

Parametre, ktoré rozbijú paritu s TradingView (sizing, STATE timeouty), sú označené
a sweep na ne upozorní; zakázané nie sú — ak ich chceš ladiť vedome, ladia sa.

## 8. Hyperopt (len engine Freqtrade)

Tie isté `--param` ako sweep, len sa v rozsahu **hľadá** namiesto prechádzania. Zadanie sa
nepíše dvakrát: `2:8:0.5` je pre sweep 13 hodnôt, pre hyperopt rozsah, v ktorom hľadá.

```bash
PY -m tester.webapp.cli hyperopt --param rrRatio=2:8:0.5 --param slLookback=5:40:1 \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --goal break_even --min-trades 15 --epochs 200

PY -m tester.webapp.cli hyperopt --suggested --timerange 20250904-20260904 --epochs 200
```

`--suggested` vezme priestor, ktorý **odporúča stratégia** — to, čo na nej prežilo
out-of-sample. To isté robí `./deploy/freqtrade/scripts/hyperopt.sh <okno> [epochy]`.

Po dobehnutí sa víťaz **sám** pustí na piatich referenčných oknách a výsledky sa ukážu
vedľa seba (ladené okno označené) s jednou vetou na záver: `VITAZ PREZIL` / `NEJASNE` /
`PRETRENOVANE`. Nie je to doplnok — hyperopt nájde optimum práve toho okna, ktoré videl,
a už sa raz stalo, že víťaz mal na ladenom roku +34,8 % a stratu vo všetkých štyroch
ostatných ([docs/merania/HYPEROPT_btcusdt_2026-09-04.md](../docs/merania/HYPEROPT_btcusdt_2026-09-04.md)).
Overovacie behy sú obyčajné behy v histórii, dajú sa otvoriť aj prehnať Monte Carlom.

Na jeden–dva parametre je čitateľnejší **sweep** (§7). Hyperopt sa oplatí od troch.

Poradie, v ktorom to dáva zmysel: hyperopt nájde parametre → out-of-sample okná rozhodnú,
či to prežije → `tester.montecarlo` (§5) dá k prežitému číslu interval. Monte Carlo
hyperopt **nenahrádza** ani neodhalí jeho pretrénovanie; sú to dve rôzne otázky.

Ako sa nastavujú hranice, ako pridať hyperopt k novej stratégii a čo sa deje vnútri:
[docs/HYPEROPT.md](../docs/HYPEROPT.md).

## 8a. Okolie víťaza hyperoptu

```bash
PY -m tester.webapp.cli plateau <hyperopt_id>
```

Hyperopt vráti jedno číslo. Okolie povie, či je to stred niečoho (**plató** — presná hodnota
nie je kritická), alebo náhodná diera v šume (**špička** — optimum je tvar toho okna).
Susedia sa berú o krok a o dva kroky, vždy len na jednom parametri; „drží" znamená, že
sused padol do intervalu spoľahlivosti víťaza z Monte Carla. Vo webapp je to v detaile
hyperoptu tlačidlom **Preveriť okolie víťaza**.
[docs/HYPEROPT.md](../docs/HYPEROPT.md#okolie-víťaza-plató-alebo-osamelá-špička).

## 8b. Analytika: ktorá skupina obchodov kazí výsledok

Karta **Analytika** vo webapp. Backtest povie jedno číslo za celý beh; tu sa obchody
rozrežú na skupiny (hodina, deň, smer, vzdialenosť stopu, plánovaný RR) a pri každej sa
spočíta break-even poplatok **a čo by sa stalo, keby tá skupina nebola**. To je odpoveď na
otázku, či sa oplatí filter — a keď je najhoršia skupina väčšina obchodov, tak to nie je
filter, ale nastavenie parametra (appka to povie a ponúkne ho preladiť).

Vlastnosti známe **až po obchode** (dôvod výstupu, dĺžka, kam cena zašla) sú zvlášť
a označené. „Obchody, ktoré skončili na stope, majú zlý break-even" je pravda a zároveň
bezcenná — pri vstupe to nikto nevie.

Tá istá karta zaradí stratégiu do typu (prerazenie / trendová / protitrendová / scalping /
formácia / swingová) a povie, čo je pri tom type normálne, na čo pozor a čo ladiť. Meria sa
to z obchodov, hlavne z **pohybu pred vstupom**: [docs/TYPY_STRATEGII.md](../docs/TYPY_STRATEGII.md).
Na IBS vyšlo prerazenie (vstup po pohybe +1,01 ATR, winrate 29,7 %, payoff 2,30) — z toho
vyplýva, že ladiť winrate nemá zmysel a 42 % výstupov na stope nie je chyba.

## 8d. Portfólio: koľko sa dá zarobiť a za aký drawdown

„Koľko sa na tom dá zarobiť?" je otázka, na ktorú jeden beh odpovedať nevie — odpoveď
závisí od toho, **koľko riskuješ na obchod** a **čo všetko obchoduješ naraz**.

```bash
PY -m tester.webapp.cli portfolio --runs <id1>,<id2>,...
PY -m tester.webapp.cli portfolio "note~matica" --limit 12
```

To isté je na karte **Analytika** (počíta sa z tých istých vybraných behov). Výstup má tri
časti:

| | čo hovorí |
|---|---|
| **cena rizika** | riziko na obchod → zhodnotenie → ročne (CAGR) → max drawdown |
| **rok po roku** | nesie to jeden dobrý rok, alebo je to rozložené? |
| **korelácie** | koľko z toho, čo robí jeden člen, robia aj ostatní |

**Korelácie sú to najdôležitejšie číslo.** Portfólio má zmysel len vtedy, keď sa členovia
nechovajú rovnako: keď jeden prehráva a druhý zarába, krivka je hladšia než ktorýkoľvek
z nich. Keď sú korelovaní, je to len jeden beh s väčšou pozíciou a **drawdown sa nezmenší,
len sa znásobí**. U nás je to zvyčajne jedna stratégia na viacerých trhoch, takže korelácia
bude vyššia než pri naozaj rôznych stratégiách — výpis to meria a nehovorí „portfólio je
hladšie", kým to čísla nepotvrdia.

Dve veci, ktoré treba pri čítaní vedieť:

- **Člen je jeden beh.** Dva behy toho istého trhu v tom istom období nie sú dvaja
  členovia, ale dve **alternatívy** jednej veci; keby sa ich obchody sčítali, to isté
  obdobie by sa započítalo dvakrát. Modul takú dvojicu nájde a povie `TO NIE JE PORTFOLIO`.
  Dobrým zdrojom členov je **matica trhov** (§8e) — rôzne trhy, to isté okno.
- **Veľkosť pozície sa prepočíta**, nepreberá sa z behu: `riziko = zostatok × risk %`,
  `množstvo = riziko / vzdialenosť stopu`. Bez toho by sa sčítavali veľkosti z rôznych
  behov a výsledok by hovoril o peňaženkách, nie o stratégii. Obchod bez známej vzdialenosti
  stopu do prepočtu nevstúpi a výpis povie, koľko ich bolo.

Súbežné pozície sa nekrátia — keď majú dvaja členovia otvorené naraz, obaja sú sizovaní
z vtedajšieho zostatku a margin sa nekontroluje. Je to teda horná hranica toho, čo by šlo.

## 8c. Je ten edge odlíšiteľný od náhody?

Break-even 0,064 % je veľa alebo málo? Bez referencie to nie je odpoveď, ale číslo. Test
proti náhode postaví „hlúpu" verziu tej istej stratégie — obchoduje rovnako často, rovnakým
smerom, s rovnakým stopom aj take profitom a drží rovnako dlho, **len si nevyberá, kedy
vstúpiť** — spraví tisíc takých behov a povie, kde skutočný výsledok medzi nimi leží.

```bash
PY -m tester.webapp.cli nulltest "pair=BTC/USDT:USDT" --limit 12
```

To isté je na karte **Analytika** hneď pod hlavičkou (počíta sa z tej istej vzorky obchodov).

Merajú sa **dve rôzne náhody** a rozdiel medzi nimi je to zaujímavé:

| náhoda | vstupy | čo z toho vieme |
|---|---|---|
| `anytime` | kedykoľvek v okne | o celej stratégii vrátane toho, **kedy** obchoduje |
| `session` | v tých istých hodinách ako stratégia | o tom, čo robí **vnútri** svojho okna |

Keď je stratégia výrazne lepšia než `anytime`, ale nie než `session`, celý jej edge je
v tom, že obchoduje v NY seanse — a to sa dá mať aj bez nej.

Dve veci, ktoré test robí zámerne a treba o nich vedieť:

- **Náhoda dedí drift trhu.** Keď trh rástol, náhodné longy na ňom zarobia a stratégia to
  musí prekonať. Bez toho by „nakúp a drž" vyzeralo ako edge; latka je teda edge **nad
  driftom**, nie nad nulou.
- **Simuluje sa na 1m sviečkach**, aj keď stratégia beží na 3m. Vnútri baru nevieme, či
  prišiel skôr stop alebo take profit, a pri hrubších sviečkach tá nevedomosť vychýli
  referenčný bod — čím by edge stratégie vyzeral lepší, než je. Je to ten istý dôvod, pre
  ktorý sa každý backtest púšťa s `--timeframe-detail 1m`.

Výsledok na IBS (1014 obchodov z piatich referenčných okien, BTC/USDT:USDT 3m): break-even
0,064 % oproti náhode −0,001 % ± 0,015, teda **4,4 sigma** — a obe náhody dávajú to isté,
takže edge nie je len o výbere času.

Pod 15 obchodov je rozdelenie náhody také široké, že jediný poctivý záver je „málo dát" —
výpis to povie sám.

## 9. FreqAI

Dá sa pripojiť, ale odpovedá na inú otázku: hyperopt vyberie statické parametre, FreqAI
trénuje model, ktorý sa v čase mení. Stratégia je deterministický stavový automat a jeho
parita s Pine je zmyslom celého portu, takže model ju **nenahrádza** — dáva sa nad ňu ako
filter (engine nájde setup, model predpovie, či ho brať), a to paritu poruší, takže by to
bolo rozšírenie mimo Pine s defaultom „vypnuté".

Chýbajú závislosti (`pip install "freqtrade[freqai]"`) a hlavne obchody: máme 20–170
obchodov za rok, teda ~100–800 nálepiek za päť rokov. Čo presne by sa muselo dorobiť, čo
to stojí a prečo sa najprv oplatí ručne zmerať, či má filter vôbec priestor:
[docs/HYPEROPT.md — FreqAI](../docs/HYPEROPT.md).

## 10. Čo nerobiť

- Needituj `tradebot/core`, adaptéry ani referenčné profily kvôli tomu, aby beh „vyšiel".
- Nesťahuj dáta z burzy pri bežnom testovaní — páry a obdobia sú tie, čo sú v archíve
  ([docs/DATA.md](../docs/DATA.md)).
- Nezapisuj závery z jedného okna. Ak nemáš päť okien, napíš, že ich nemáš.
