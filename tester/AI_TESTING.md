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
| **stratégia** | logika (`--strategy ibs`, `structure`, `demo_breakout`). Zoznam: `PY -m tester.webapp.cli params --help` |
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
vyšiel na nulu. PnL v % závisí od sizingu a peňaženky,
break-even nie.

**Poplatok nie je jedno číslo pre všetky trhy.** Na krypte je to provízia z nominálu
(Binance taker 0,05 %), na CFD je provízia drobná až nulová a skutočný náklad je **spread**
— teda pevný posun ceny. Krypto sadzba na CFD urobí zo ziskového trhu stratový: break-even
0,0287 % na NAS100 je proti 0,05 % „strata“ a proti spreadu pohodlný zisk. Preto `--fee`
bez hodnoty berie náklad **toho inštrumentu** (`InstrumentSpec.cost` / `cost_unit`) a do
behu sa uloží aj to, odkiaľ číslo je.

Pri Dukascopy CFD je to zatiaľ **odhad, nie meranie**: polovica spreadu = 1 tick. Spread sa
z našich dát zistiť nedá, lebo export má len jednu stranu trhu (bid). Keď sa zistí skutočná
hodnota od brokera, je to jeden riadok v `tradebot/core/instruments_dukascopy.json`
(`half_spread_ticks` a `cost_note`). Pozor na symboly s umelo jemným tickom — NAS100 má tick
0,01, teda sto tickov na jeden bod indexu, takže jeden tick je tam hlboko pod skutočným
spreadom.

**Filtre v histórii.** Nad tabuľkou behov sú tri ponuky — **stratégia** (predvolene tá,
ktorá je práve nastavená vo formulári), **pár** a **timeframe**. Skladajú sa s tým, čo je
vo vyhľadávaní, ale do textu sa nezapisujú, aby sa testerovi neprepisovalo, čo si sám
napísal. To isté z príkazového riadku: `list "strategy=ibs pair=NAS100/USD tf=3m"`.

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

Delí sa aj podľa **stavu trhu pri vstupe** (`tester.regime`): či bol v trende alebo
v rozsahu, aká bola volatilita voči normálu, kde v rozsahu sa vstupovalo a či išiel obchod
s trendom alebo proti nemu. Počíta sa to z barov **pred** vstupom, takže sa podľa toho
filtrovať dá — a práve tam býva zvyšný edge, keď ho v samotnom patterne už niet.

Na IBS z toho vyšli dve zistenia a dopadli opačne
([docs/merania/REZIM_filtre_btcusdt_2026-09-10.md](../docs/merania/REZIM_filtre_btcusdt_2026-09-10.md)):

- **S trendom vs. proti trendu — potvrdené.** Na desiatich trhoch × piatich oknách je
  break-even obchodov s trendom vyšší v **23 z 26 buniek** (medián +0,105 p. b.,
  znamienkový test p = 0,00004), kladné na ôsmich trhoch z deviatich.
- **Vrch vs. spodok rozsahu — nepotvrdené.** 14 z 25 buniek, teda hod mincou. Na
  `BTC/USDT:USDT` pritom vyšlo 5 z 5 — ale na `BTC/USD`, čo je ten istý podklad z iného
  zdroja, 1 zo 4. Efekt je vlastnosťou tej jednej série, nie trhu.

Obe zliate čísla (3× a 5×) pôvodne vyzerali rovnako presvedčivo. Rozdiel medzi nimi
ukázalo až rozloženie na bunky — a to je dôvod, prečo sa zliate číslo overuje po oknách
a trhoch, a prečo sa do jednej vzorky nemiešajú rôzne konfigurácie.

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

### Kalendár: deň v mesiaci, sviatky a makro
Delí sa aj podľa kalendára — **deň v mesiaci**, **kalendárny mesiac** (marec vôbec, nie
marec 2023), **makro udalosť** v ten deň (Fed, CPI, NFP), **pred vyhlásením či po ňom** a
**sviatok na burze v USA**. Všetko sa vie dopredu, takže sú to legitímne filtre.

Zdroje sú dva a líšia sa zámerne:

- **Sviatky sa počítajú pravidlom** („tretí pondelok januára", Veľký piatok z Veľkej noci),
  takže platia pre ktorýkoľvek rok a nič sa nesťahuje.
- **Makro dátumy sú odpísané** z `federalreserve.gov` a `bls.gov` do
  [tester/calendar_us.json](calendar_us.json) aj so zdrojom — pravidlo nemajú, NFP nie je
  vždy prvý piatok a CPI nie je vždy trinásteho.

Súbor nesie `coverage`, dokedy je zoznam úplný. Obchod mimo toho rozsahu **nedostane nič**,
nie „žiadna udalosť" — inak by sa mlčanie kalendára čítalo ako pokojný deň. Ďalší rok sa
doplní z tých istých stránok.

> **Pozor, toto je pasca na preoptimalizovanie.** Rozdiel medzi začiatkom a koncom mesiaca
> vyzerá na zliatej vzorke presvedčivo a po rozklade na bunky zmizne — u nás 22 z 36
> buniek, p = 0,12, viď
> [KALENDAR_dni_a_makro_2026-09-10.md](../docs/merania/KALENDAR_dni_a_makro_2026-09-10.md).
> Kalendár čítaj ako otázku na overenie, nie ako hotový filter.

### Syntetický trh priamo v analytike
Karta ukáže aj to, ako tá istá konfigurácia dopadla na **premiešanom trhu** (§8j) — okno po
okne, vrátane toho, koľko signálov sa vyplnilo. Nič sa nespúšťa; hľadajú sa behy, ktoré
v histórii sú, a keď chýbajú, je pri tom rovno príkaz, ktorým vzniknú.

| verdikt | čo znamená |
|---|---|
| `ENGINE OK` | na premiešanom trhu edge nie je — namerané čísla nevyrába backtest |
| `POZOR NA ENGINE` | edge vyšiel aj tam, kde ho trh nemá z čoho dať — hľadaj pohľad dopredu, fill model, sizing |
| `NEJASNE` | málo okien alebo málo obchodov na rozhodnutie |

### Posudok (AI)
Čísla povedia, čo sa stalo. Nepovedia, **čo z toho plynie** — či je najhoršia skupina
príležitosť alebo vlastnosť vzorky, čo tomu v tom istom výpise protirečí a čo pustiť ďalej.
Preto má uložená analytika miesto na posudok:

1. **Uložiť do histórie** (posudok sa píše k záznamu, nie k výpisu na obrazovke),
2. **Skopírovať zadanie pre AI** — čísla plus päť otázok,
3. odpoveď vložiť a **Uložiť posudok**.

To isté z príkazového riadku: `cli analytics <id>` vypíše zadanie, keď posudok chýba, a
`cli analytics <id> --posudok @subor.md` ho uloží.

Posudok patrí ku **konkrétnym číslam**, takže sa k nemu ukladá ich odtlačok. Keď sa
analytika prepočíta na inej vzorke, text ostane (písať ho znova je práca), ale je označený
za **starý** — inak by o mesiac nikto nevedel, o čom hovorí.

### Z akej konfigurácie tie obchody sú
Analytika, prop výzva aj meranie počítajú nad **zliatymi** obchodmi z viacerých behov.
Kým je to tá istá konfigurácia na rôznych oknách alebo trhoch, je to presne to, na čo sa
zlievajú. Keď nie je, mieša sa dokopy niekoľko rôznych stratégií a výsledok nehovorí
o žiadnej z nich — tak vznikli neplatné čísla v
[REZIM_filtre_btcusdt_2026-09-10.md](../docs/merania/REZIM_filtre_btcusdt_2026-09-10.md).

Hlavička preto hovorí, z čoho sa počítalo, v troch stupňoch:

| | čo to znamená |
|---|---|
| jedna konfigurácia | behy sa líšia len oknom alebo trhom — v poriadku |
| jeden profil, iné čísla | `--set`, alebo prepočet prahov na ATR v matici; over, či to tak má byť |
| **rôzne profily** | zliate rôzne stratégie — vyber si jednu, inak čísla nehovoria o ničom |

### História analytiky
Analytika sa počíta nad výberom behov a inak by zmizla s obnovením stránky. Tlačidlo
**Uložiť do histórie** zapíše **záver, nie obchody** (tie ostávajú v behoch, na ktoré sa
záznam odkazuje) do `tester/analytics/` a ponuka **Predošlé analytiky tejto stratégie** sa
k nemu vráti. Rovnako ako mriežky a matice je to **per stratégia**: vlastnosti aj parametre
sú pri každej iné, takže zliate v jednom zozname by sa neporovnávali.

```bash
PY -m tester.webapp.cli analytics                 # zoznam
PY -m tester.webapp.cli analytics --strategy ibs
PY -m tester.webapp.cli analytics <id>            # detail aj s tabuľkou
```

Push ich commituje spolu s behmi, takže sa dajú zdieľať cez GitHub.

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

## 8e. Matica trhov: drží tá myšlienka aj inde?

Že stratégia funguje na BTC, hovorí o BTC. Že tá istá myšlienka funguje na indexe, na
komodite **aj** na krypte, hovorí o myšlienke. Matica je sweep, v ktorom sa nemení
parameter, ale **trh a timeframe**; každá bunka je obyčajný beh a ostane v histórii.

```bash
PY -m tester.webapp.cli matrix --profile <profil> --pairs all --timeframes 3m \
   --timerange 20250904-20260904 --wallet 40000000
PY -m tester.webapp.cli matrices              # matice z histórie
```

Dve veci, bez ktorých je tabuľka na nič, a modul ich robí sám:

- **Prahy sa prepočítajú na ATR.** `minImbSizePoints = 2,5` znamená 2,5 dolára na BTC,
  ale 2,5 **celej ceny** na EURUSD — teda podmienku, ktorá nikdy nenastane. Prepočítava sa
  `abs` aj `ticks` (`imbMaxDistTicks = 100` je na BTC 0,115 ATR, na EURUSD 3,86 ATR).
  Bez toho by v tabuľke nebolo „na forexe to nefunguje", ale „profil je tam nezmysel" —
  a to dvoje sa v nej nedá rozlíšiť. Vypnúť sa to dá (`--no-relative`), závery z toho
  nikam nepatria.
- **Peňaženka musí stačiť na jeden kontrakt.** Jeden lot EURUSD je ~108 000 USD; s
  peňaženkou 10 000 sa veľkosť oreže na nulu a bunka vyzerá ako „tu to nefunguje".
  Príkaz to skontroluje vopred a navrhne peňaženku. Break-even od peňaženky nezávisí,
  takže ju zvýšiť sa smie.

Výsledok na IBS (21 trhov, okno 2025-26): break-even je kladný na **8 z 10** trhov s dosť
obchodmi — indexy, krypto, energie. Edge teda nie je vlastnosťou BTC.

## 8f. Slabne edge?

Backtest za päť rokov dá jedno číslo. Nepovie, či stratégia zarábala rovnomerne, alebo
zarobila v rokoch 2021-2023 a odvtedy stojí — a pre rozhodnutie „ideme s tým naostro" je
to rozdiel zásadný. Edge sa opotrebúva.

```bash
PY -m tester.webapp.cli decay "pair=BTC/USDT:USDT" --limit 12
PY -m tester.webapp.cli decay --runs <id1>,<id2>,... --parts 4
```

To isté je na karte **Analytika** (z tých istých vybraných behov).

**Prečo sa posledná štvrtina neporovnáva s celkom.** Má štyrikrát menej obchodov, teda je
aj prirodzene rozkolísanejšia; oproti celkovému číslu by vyšla horšie asi v polovici
prípadov a test by hlásil úpadok stále. Referenciou je preto niečo iné: **ako by vyzeral
úsek tej istej dĺžky, keby sa edge nemenil.** Z celej histórie sa blokovým bootstrapom
natiahnu vzorky presne takej veľkosti, akú má posledné obdobie, a namerané číslo sa
porovná s ich rozdelením. Blok (10 obchodov) drží série strát pokope — bez neho by bolo
rozdelenie príliš úzke.

| verdikt | čo znamená |
|---|---|
| `DRZI` | posledné obdobie je v medziach, ktoré stratégia vyrobí sama od seba |
| `SLABNE` | je pod dolnou hranicou — úsek taký zlý by náhodou vyšiel v menej než 5 % prípadov |
| `POZOR NA TREND` | posledné je ešte v medziach, ale **každé** obdobie je horšie než predošlé |
| `ZLEPSUJE SA` | nad hornou hranicou; nie je to dôvod zvyšovať riziko |
| `MALO DAT` | menej než 60 obchodov celkom alebo 12 v poslednom období |

Sleduje sa aj **počet obchodov na mesiac**: keď stratégia prestane nachádzať signály, je to
úpadok rovnako, len sa v break-evene neprejaví.

Tri veci, ktoré test nevie:

- **Nerozlíši dohorený edge od nepriaznivého režimu.** Slabá posledná štvrtina môže byť
  oboje a z tých istých dát sa to oddeliť nedá — na to je stav trhu (`tester.regime`) a čas.
- **Percentil je test len pre posledné obdobie**, lebo to bolo vybraté vopred. Percentily
  ostatných období sú opis: pri štyroch obdobiach vyjde jedno pod piatym percentilom
  náhodou zhruba raz z piatich prípadov.
- **O budúcnosti nehovorí nič.** `DRZI` znamená, že úpadok v dátach vidieť nie je — nie
  že nepríde.

## 8g. Celá batéria naraz: základná analytika stratégie

Kroky 5 a 8a–8f majú spoločné poradie a spoločný výstup — a ten patrí k stratégii, nie do
jedného terminálu:

```bash
PY -m tester.webapp.cli checkup --strategy ibs    --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timeframe 3m
```

Päť referenčných okien → charakter → skupiny obchodov → test proti náhode → slabnúci edge
→ Monte Carlo, z toho dva zoznamy („v čom je dobrá", „kde má chyby") a dokument
`tradebot/strategies/<key>/docs/ANALYTIKA.md`. Behy sú obyčajné behy v histórii, takže sa
dajú otvoriť aj použiť znova (`--runs id,id,…` poskladá dokument bez nových backtestov).

Dokument sa **generuje celý znova**; jediná časť, ktorá prežije, je **posudok od AI** na
konci — šesť otázok (kam sa stratégia hodí, či má potenciál, čo dorobiť, čo otestovať
ďalej, či je vôbec použiteľná, čo pridať). Keď sa čísla medzitým zmenili, posudok sa
označí za starý a treba ho prepísať. Podrobne: [docs/ANALYTIKA.md](../docs/ANALYTIKA.md).

## 8h. Meranie, ktoré sa napíše samo

Rozdiel oproti batérii vyššie je v **živote dokumentu**, nie v meraní: `checkup` udržiava
jeden dokument pri stratégii, ktorý sa celý prepisuje a hovorí, aká tá stratégia je dnes.
`paper` zapíše **datovaný snímok** do `docs/merania/` z tých behov, ktoré mu dáš — čo sa
meralo v ten deň a čo z toho vyšlo. Prvý sa mení, druhý ostáva.

Merá sa **tou istou batériou** (`checkup.measure`), inak by sa dva dokumenty o tej istej
stratégii nedali porovnať. Meranie navyše pridáva dve veci, ktoré k jednej stratégii
nepatria, ale k otázke áno: **maticu trhov** a **cenu rizika**.

```bash
PY -m tester.webapp.cli paper --runs <id1>,<id2>,... --title "IBS na BTC 3m"
PY -m tester.webapp.cli paper "pair=BTC/USDT:USDT" --limit 12 --stdout
```

To isté je tlačidlo **Zapísať meranie** na karte Analytika (z tých istých behov, aké sú
práve na stránke).

Tri veci, kvôli ktorým to má zmysel:

- **Prázdny `## Záver`.** Vygenerovaná záverečná veta by vyzerala ako zistenie, a nie je;
  patrí tam veta človeka. Zhrnutie hore je tabuľka verdiktov a pod ňou tie isté vety
  („v čom je dobrá", „kde má chyby"), aké má stratégia vo svojej `ANALYTIKA.md`.
- **Sekcia „Na čo behy nestačili".** Čo sa nespočítalo, sa nezamlčí — dokument to povie
  aj s príkazom, ktorým sa to doplní. Prázdna tabuľka plná pomlčiek vyzerá ako zmerané
  nič, hoci sa nemeralo.
- **Zoznam behov na konci** a príkaz, ktorým dokument vznikol, takže sa dá zopakovať.

**Nespúšťa backtesty.** Píše sa len to, čo v histórii už je; matica sa nehľadá tak, že by
sa pustila, ale tak, že sa nájde tá najväčšia v histórii. Keď je meranie hotové, prečítaj
ho a dopíš záver — a keď v ňom niečo chýba, dopusti behy a spusti príkaz znova.

## 8i. Prop výzva: dostaneš sa k výplate skôr, než účet zhorí?

Portfólio (§8d) povie, koľko by stratégia zarobila na vlastnom účte. Na prop účte to
nestačí, lebo tam **účet zomiera podľa pravidla**, nie podľa toho, či došli peniaze: séria
strát, ktorá by na vlastnom účte znamenala zlý mesiac, tu znamená koniec a zaplatený
poplatok. Otázka teda znie inak — *s akou pravdepodobnosťou sa dostanem k výplate a koľko
výziev na to spálim*.

```bash
PY -m tester.webapp.cli prop "pair=BTC/USDT:USDT" --rules ftmo2
PY -m tester.webapp.cli prop --runs <id1>,<id2> --rules apex100 --risk 1
PY -m tester.webapp.cli prop "note~matica" --limit 50 --rules ftmo2 --daily 4 --cost 400
```

**Z čoho sa to počíta.** Výzva nemá žiadnu vlastnú konfiguráciu — berie **obchody
vybraných behov**, takže konfigurácia je tá, ktorou tie behy vznikli. Veľkosť pozície sa
neberie z behu, prepočíta sa z rizika (`riziko = zostatok × risk %`), takže peňaženka ani
poplatok behu na výsledok nevplývajú; parametre stratégie áno, celé. Výpis aj stránka preto
hlásia, z akej konfigurácie obchody sú, a varujú, keď sú **zliate rôzne konfigurácie**.

To isté je vo webapp na dvoch miestach — formulár je ten istý:

- karta **Analytika**, blok **Prop výzva** — nad vybranými behmi;
- karta **Nový beh**, blok **Prop výzva** — nad tým jedným behom, keď dobehne
  (zaškrtávatko „spočítať po dobehnutí behu"). Jeden beh býva na to málo obchodov, takže
  výpis zvyčajne povie `MALO DAT` — je to orientácia, nie záver.

Predlohy pravidiel (`--rules`, oddelené čiarkou; `all` = všetky, to je aj default):
`ftmo2`, `ftmo1`, `apex100`, `apex50`, `tradeify_growth`, `tradeify_select` a `custom`
(pravidlá z prepínačov nižšie). Tie isté obchody sa prehrajú cez každú predlohu a na konci
je **porovnávacia tabuľka** — pri každej firme najlepšie riziko podľa EV, šanca na výplatu
a verdikt. Vo webapp sú predlohy zaškrtávacie. Čísla sú odpísané z verejných stránok firiem
**k 2026-09-10** a firmy ich menia často — výpis zdroj vypíše aj s upozornením. Každé pole
sa dá prepísať (`--targets 10,5`, `--daily`, `--max-loss`, `--trailing`, `--min-days`,
`--day-share`, `--cost`, `--payout`, `--horizon`); prepisy platia na `custom` a na jedinú
vybranú predlohu — pri porovnaní viacerých firiem sa ich pravidlá berú tak, ako sú.
**Pred rozhodovaním ich prepíš podľa zmluvy, ktorú naozaj máš.**

**Ako sa to počíta.** Nie jedným behom, ale stovkami pokusov: výzva sa začne postupne na
každom obchode histórie a prehrá sa dopredu, kým nepadne cieľ alebo pravidlo. Zámerne to
**nie je bootstrap** — denný limit je o tom, ako sa straty zhlukujú v čase, a preskladanie
obchodov práve to rozbije. Pokusy sa prekrývajú, takže to nie je interval spoľahlivosti,
ale odpoveď na „keby som začal v náhodnom bode tejto histórie".

Hlavná páka je **riziko na obchod**, preto sa vypisuje celá tabuľka: väčšie riziko dosiahne
cieľ rýchlejšie **a** narazí na limit častejšie, a kde je optimum, sa nedá odhadnúť.

Čo výpis povie sám, keď na to príde:

| hláška | čo znamená |
|---|---|
| `PRILIS POMALA` | väčšina pokusov sa do horizontu k cieľu ani nedostane — nie je to o riziku, stratégia neurobí dosť obchodov |
| medián 0–2 dni | cieľ padol na jednom-dvoch obchodoch; taká výplata stojí na šťastí (firmy proti tomu majú minimum dní a konzistenciu) |
| „bežalo naraz až N pozícií" | obchody z viacerých trhov sa zliali do jedného účtu, ale simulácia ich odohrá za sebou — denný limit je podstrelený |

**Čo to nevie a robí to optimistickým:** vidí len **uzavreté** obchody, kým firmy merajú
denný limit aj drawdown na equity **vrátane otvorených pozícií**. Pozícia, ktorá išla hlboko
proti a nakoniec vyšla na TP, tu účet nezabije — v skutočnosti by mohla. Skutočná šanca je
teda **nižšia** než tá vypísaná. Nie sú tu ani pravidlá o novinkách, držaní cez noc a
podobne, ktorými firmy výplaty zamietajú.

## 8j. Syntetický trh: nechytáme sa vlastného backtestu?

Test proti náhode (§8c) losuje **vstupy** na skutočnom trhu. Toto je opačná otázka:
stratégia ostane nezmenená a náhodný je **trh**. Keď na trhu, v ktorom žiadna štruktúra
nie je, stratégia stále „nájde edge", tá výhoda nevznikla na trhu — vznikla v našom
backteste. Je to teda hlavne **detektor chýb enginu**: pohľad dopredu, fill model, ktorý
rozhoduje sporné bary v náš prospech, sizing, ktorý zvýhodňuje výhry. Také chyby na
skutočných dátach vyzerajú ako zisk a nič iné ich nechytí.

Nie je to náhodná prechádzka s vymyslenou volatilitou — tú by sa dalo odmietnuť tým, že
„nevyzerá ako trh". Berú sa **skutočné 1m bary** zdrojového trhu, zapamätá sa tvar každého
baru a **výnosy sa premiešajú po blokoch**. Zachová sa presne:

| | zdroj (BTC 1m, 2021-10 → 2026-09) | syntetický |
|---|---|---|
| σ výnosu 1m | 0,000747 | 0,000747 |
| špicatosť (fat tails) | 129,8 | 129,8 |
| zhluky volatility (autokorelácia \|r\|) | 0,390 | 0,383 |
| konečná cena | 81 231 | 81 231 |

Rozdelenie výnosov je tá istá množina čísel, len v inom poradí — preto sedí aj celkový
drift a stratégia s dlhým biasom nie je trestaná. Zmizne **poradie**: trendy, úrovne,
návraty, všetko, na čom môže stáť skutočná výhoda.

### Trh je pevný
Vygeneruje sa **raz** a ostáva. Keby vznikal pri každom teste nanovo, dva výsledky by sa
nedali porovnať. Recept (zdroj, okno, blok, seed) je v `tradebot/core/instruments_synthetic.json`
a `sha256` overí, že sviečky s ním stále sedia. Dáta sa **necommitujú** — sú veľké a
z receptu vzniknú bit po bite tie isté.

```bash
python -m tester.synthetic build synth      # vygeneruje (existujúci odmietne)
python -m tester.synthetic list             # recepty a či dáta sedia
python -m tester.synthetic verify synth
python -m tester.synthetic build synth --force   # POZOR: skoršie behy prestanú byť porovnateľné
```

Potom je to **obyčajný pár** — `SYNTH/USDT:USDT` je v ponuke ako každý iný (webapp ho
uvidí po reštarte) a beh na ňom ide do histórie ako každý iný.

Prvé použitie a čo z neho vyšlo: [docs/merania/SYNTETICKY_trh_2026-09-10.md](../docs/merania/SYNTETICKY_trh_2026-09-10.md) — edge na premiešanom trhu nie je (znamienka sa striedajú), ale vyplní sa tam len 0-57 % signálov oproti 72-95 % na skutočnom BTC. Limitka na úrovni medzery sa dočká len vtedy, keď sa cena na tú úroveň vráti.

### Ako to čítať
Na syntetickom trhu má vyjsť **nula**. Jedno okno nič nehovorí — pri dvadsiatich obchodoch
vyjde občas aj +0,12 %, presne ako na skutočnom trhu. Pozeraj **všetkých päť okien**: keď
sa čísla motajú okolo nuly a striedajú znamienko, engine je v poriadku. Keby vyšli
súvisle kladné, je to nález — ale o **nás**, nie o stratégii.

Záporný výsledok naopak nedokazuje nič: poplatky a spread berú aj na náhodnom trhu.

## 9. AI filter (FreqAI)

Model **nenahrádza** engine, dáva sa nad neho. Engine nájde setup presne ako dnes (parita
s Pine ostáva), model k signálu predpovie, či skôr príde take profit alebo stop, a signály
pod prahom sa preskočia. Zapnutý filter paritu **poruší** — obchodov bude menej — takže je
to rozšírenie mimo Pine a je **predvolene vypnuté**.

```bash
PY -m tester.webapp.cli run --profile <profil> --timerange 20250904-20260904 --ai
PY -m tester.webapp.cli run … --ai --ai-min-prob 0.45 --ai-adjust size=0.5:1.5
```

| prepínač | čo robí |
|---|---|
| `--ai` | zapne filter s predvolenými hodnotami |
| `--ai-min-prob` | prah istoty; pod ním sa signál preskočí (default 0,55) |
| `--ai-train-days` | dĺžka tréningového okna (default 730) |
| `--ai-backtest-days` | ako často sa pretrénuje (default 180) |
| `--ai-model` | model FreqAI (default `LightGBMClassifier`) |
| `--ai-adjust KLUC=OD:DO` | čo smie model meniť podľa istoty; opakovateľné |

To isté je vo webapp na karte **Nový beh** v bloku **AI filter (FreqAI)**: zaškrtávatko,
prah, okná, model a políčko na rozsah pri každom kľúči, ktorý daná stratégia dovolí meniť
(zoznam sa načíta z nej, takže sa mení so stratégiou). Kým nie je zaškrtnuté, do behu sa
nepridá nič.

### Nálepka, ktorú netreba vymýšľať
FreqAI štandardne predpovedá zmenu ceny o N sviečok dopredu, čo je vždy sporný cieľ. My
pre **každý signál** poznáme jeho SL aj TP z plánu, ktorý engine vypočítal — nálepka je
teda „tento signál skončil na TP" alebo „na SL". Keď v jednom bare padne oboje, počíta sa
to ako **stop**: v jednom bare nevieme, čo prišlo skôr, a optimistický odhad by model
naučil, že sporné obchody vychádzajú.

Bary bez signálu ostávajú bez nálepky a FreqAI ich z tréningu vyhodí — model sa učí len na
tom, čo engine naozaj ponúkol, nie na každom bare grafu.

Nálepka je **skutočný výsledok tak, ako ho stratégia obchoduje**: keď engine pred zásahom
TP alebo SL povie „zavri všetko" (koniec seansy — IBS tak končí ~27 % obchodov), obchod sa
v nálepke uzavrie na závere toho baru a `win`/`loss` je podľa znamienka. Model sa tak učí to
isté, čo sa potom hodnotí v behu, nie „bol by to dobrý obchod, keby sa držal do rána".
Trailing sa v nálepke nesimuluje (port-only, predvolene vypnutý).

Modely si FreqAI ukladá pod `identifier` a pri rovnakom páre a okne ich nabudúce načíta
namiesto tréningu. Meno preto nesie stratégiu a odtlačok profilu (`tb-<stratégia>-<hash>`),
inak by beh s inými parametrami ticho bežal na modeli z cudzích signálov.

### Prečo je príznakov len sedem
Trend, volatilita voči normálu, poloha v rozsahu (v smere obchodu), vzdialenosť stopu,
plánovaný RR, hodina a smer. Sú to tie isté veci, ktoré meria analytika, takže model vidí
ten istý svet, v akom robíme závery. Viac príznakov by sa pri stovkách nálepiek naučilo
vzorku — a to sme už raz videli pri úzkom hyperopte, ktorý skončil stratou vo všetkých
štyroch out-of-sample rokoch. Štandardné rozširovanie FreqAI (posunuté sviečky, korelované
páry, desiatky periód) je preto **vypnuté**.

### Prah závisí od winrate, nie od pocitu
**Toto je tá vec, na ktorej sa dá najľahšie pomýliť.** Model predpovedá pravdepodobnosť
výhry a tá sa točí okolo winrate stratégie. Pri winrate 35 % model málokedy prekročí 0,55,
takže prah 0,55 zahodí skoro všetko. Prah patrí **nad** winrate, nie nad 0,5 — pri 35 %
winrate skús 0,40–0,45 a pozri, koľko obchodov ostane.

### Časť 2: zmena vybraných parametrov podľa istoty

`--ai-adjust` škáluje **plán obchodu** podľa toho, aký si je model istý: pri istote na
prahu dolný koniec rozsahu, pri istote 1 horný. Mantinely sú zo zadania behu, takže model
nemôže poslať hodnotu ani do neba, ani na nulu.

```bash
PY -m tester.webapp.cli run … --ai --ai-adjust size=0.5:1.5 --ai-adjust tp=0.8:1.4
```

Vyberá sa zo zoznamu, ktorý **hovorí stratégia** (`StrategyHyperopt.AI_ADJUSTABLE`) —
generická vrstva kľúče menom nepozná. Pre IBS:

| kľúč | čo mení | staticky to isté robí |
|---|---|---|
| `size` | veľkosť pozície | `maxLossDollar` |
| `tp` | vzdialenosť take profitu (RR) | `rrRatio` |
| `sl` | vzdialenosť stopu | `minSlDistance` |

Škáluje sa **vzdialenosť od vstupu**, nie cena: `tp=…:1.2` znamená „o pätinu ďalej od
vstupu", nie „o pätinu vyššie". Pri `sl` sa navyše dopočíta množstvo — vzdialenejší stop
by pri tej istej veľkosti znamenal väčšiu stratu, takže **riziko na obchod ostáva to,
ktoré bolo zadané**, a mení sa len to, kde stop leží. Kto chce meniť aj riziko, má na to
`size`; oba násobky sa vtedy vynásobia.

Iný parameter zadať nejde a príkaz povie prečo:

```
'minSlDistance' sa modelom menit neda. Strategia ibs dovoli:
  size   veľkosť pozície  (staticky: maxLossDollar)
  tp     vzdialenosť take profitu (RR)  (staticky: rrRatio)
  sl     vzdialenosť stopu  (staticky: minSlDistance)
Ostatne parametre rozhoduju, ci signal VOBEC vznikne - v case, ked model predpoveda,
engine uz dobehol. Tam je jedina odpoved 'ber / neber' a to robi filter.
```

**Prečo len tri.** Všetko ostatné rozhoduje, či signál **vôbec vznikne** — `minSlDistance`
ako filter, štruktúrny filter, hodiny seansy. V čase, keď model predpovedá, engine už
dobehol a signál buď je, alebo nie je; tam je jediná zmysluplná odpoveď „ber / neber",
a to robí filter (`--ai-min-prob`).

**Filter sa dá aj vypnúť** (`--ai-min-prob 0`) a nechať len škálovanie. Je to jemnejší
zásah: vzorka ostane celá a model môže pridať hodnotu bez toho, aby ju najprv zničil —
čo je po výsledku filtra (nižšie) rozumnejší začiatok.

### Čo to stojí
- **Beh sa spomalí.** FreqAI trénuje walk-forward; s predvolenými hodnotami sú to dva
  tréningy na rok navrch k backtestu.
- **Výsledok prestane byť determinovaný.** Golden testy aj porovnanie s TradingView
  a MultiCharts platia len pre vetvu s vypnutým filtrom.
- **Málo nálepiek.** Nálepku dostane len bar so signálom, takže stratégia s 30 obchodmi
  za rok má v tréningovom okne pár desiatok nálepiek. Keď model v okne nevidí obe triedy,
  nenatrénuje sa — vtedy sa **nefiltruje** a beh dobehne ako obyčajný (v logu je o tom
  riadok). Filter má zmysel skúšať na konfigurácii, ktorá obchoduje často.

### Ako to dopadlo na IBS
Vrstva funguje mechanicky, ale **na IBS ju zapínať netreba**: na piatich referenčných
oknách je s filtrom lepšie 3 z 5 (medián +0,007 bodu, p = 0,50), teda hod mincou — a stojí
to 85 % obchodov (zo ~170 na okno ostáva 19–32). Podrobne aj s tabuľkou:
[docs/merania/AI_filter_2026-09-10.md](../docs/merania/AI_filter_2026-09-10.md).

Nie je to prekvapenie: analytika už skôr ukázala to isté z druhej strany — žiadna vopred
známa vlastnosť obchodov výsledok výrazne nekazí, takže nie je čo filtrovať. Model má
zmysel skúšať tam, kde je nálepiek rádovo viac.

## 10. Čo nerobiť

- Needituj `tradebot/core`, adaptéry ani referenčné profily kvôli tomu, aby beh „vyšiel".
- Nesťahuj dáta z burzy pri bežnom testovaní — páry a obdobia sú tie, čo sú v archíve
  ([docs/DATA.md](../docs/DATA.md)).
- Nezapisuj závery z jedného okna. Ak nemáš päť okien, napíš, že ich nemáš.
