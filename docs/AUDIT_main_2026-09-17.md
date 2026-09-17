# Audit main: logika, úplnosť a výkon výpočtov

Dátum: 17. 9. 2026. Auditovaný commit: `a052520b` (`main`, lokálny `origin/main` ukazoval na rovnaký commit). Remote som nefetchoval. Ide o audit kódu a lokálnych dát, nie o posudok ziskovosti stratégie.

## Záver

Architektúra má použiteľný základ: spoločné stavové enginy, registry stratégií, explicitné plány obchodov a centralizované skladanie sviečok. Najväčšie problémy sú na hraniciach medzi enginom, simulovaným brokerom, Freqtrade a analytikou. Tieto vrstvy si neodovzdávajú všetky informácie, ktoré už predchádzajúca vrstva pozná: identitu vyplneného orderu, typ vstupu, trailing, čas signálu a peňažné jednotky.

Našiel som reprodukovateľné chyby, ktoré menia vstupy, výstupy aj interpretáciu výsledkov. Zvlášť dotknuté sú MNQ/futures s hodnotou bodu odlišnou od 1, MultiCharts IBS s viacerými čakajúcimi ordermi, grafy väčšie než detekčný TF a porovnávanie funkcií medzi adaptérmi. Úspešná súčasná testovacia sada tieto kombinácie nepokrýva dostatočne.

Výkonový profil ukazuje, že pri skúšanom IBS profile dominuje prechádzanie zón, pivoty a seansové hodiny. Samotné čítanie feather súboru tvorilo malú časť času. Najprv by som opravil exekučné a analytické kontrakty, potom optimalizoval aktívnu množinu zón a spoločné predvýpočty. Zrýchlenie nesmie meniť fill model ani vynechať 1m detail.

## Rozsah a dôkazy

- Zmapovaná cesta: zdrojové dáta → import/archív → pracovné sviečky → runner → engine stratégie → broker/adaptér → výsledky/kresby → analytika/sweep/Monte Carlo.
- Najpodrobnejšie skontrolované: IBS engine a stavový automat, Freqtrade báza/runner, MultiCharts runner/emulátor, spúšťanie behov, peňažné metriky, analytické párovanie, výber Databento kontraktov. Pri ostatných stratégiách najmä kontrakt a napojenie na adaptéry. Nie je to dôkaz správnosti každého pravidla všetkých ôsmich stratégií.
- Kompletná sada: **1 157 passed, 29 skipped, 2 warnings, 46,77 s**.
- Cielená kontrola golden/parity/MC: **75 passed, 28 skipped, 14,30 s**. Týchto 28 preskočení sú testy Pine vstupov pre gap/range/sdzone/divergence bez deklarovaného dostupného Pine súboru. IBS golden testy v tejto sade prešli. Dôvod zostávajúceho jedného skipu z plnej sady tu nebol dodatočne rozlíšený.
- Diagnostické scenáre sú v `data/audit_main_probe.py` (lokálny ignorovaný súbor). Príkaz z koreňa: `.venv\Scripts\python.exe data/audit_main_probe.py`; profilovanie: rovnaký príkaz s `--benchmark`.
- Produkčný kód, parametre ani história behov neboli zmenené. Pôvodný necommitnutý `tester/profiles/testik.json` ostal nedotknutý.
- Meranie neobsahovalo živý MultiCharts broker ani celý Freqtrade backtest. Rozdiel medzi syntetickou reprodukciou, staticky potvrdenou chybou a potrebným integračným meraním je uvedený pri nálezoch.

## Potvrdené logické chyby

P1 = opraviť pred spoliehaním sa na výsledky dotknutej konfigurácie. P2 = významná chyba alebo medzera s užšou podmienkou použitia.

### A1 — P1: jednotky futures sa medzi výsledkom a analytikou rozchádzajú

**Miesta:** `tradebot/adapters/multicharts/emulator.py:281–321, 351–352`; `tester/montecarlo.py:79–98`; `tester/analytics.py:79–93`; `tradebot/core/instruments_databento.json`.

`rows_from_trades()` správne násobí zisk aj nominál `inst.point_value`. `summarize()` však zostaví objem iba ako `(open + close) * amount`, bez hodnoty bodu. Hrubý zisk je v dolároch, menovateľ v cenových bodoch krát kontrakty. Na MNQ (`point_value=2`) je súhrnný break-even poplatok dvojnásobný.

Reprodukcia: 1 MNQ kontrakt, vstup 100, výstup 110, bez poplatku. Zisk je 20 USD, obojstranný nominál 420 USD, break-even **4,7619 %**. Aktuálny súhrn dá **9,5238 %**. Ceny sú zámerne syntetické, aby bola chyba zrejmá.

`montecarlo.per_trade()` potom z rovnakého obchodu znova odvodí iba **10 USD**, pretože ignoruje hodnotu bodu aj uložené `gross_abs`. Pri jednom rovnakom inštrumente sa chyba v pomere gross/volume vykráti, ale peňažný výsledok, drawdown a škálovanie podľa dolárového rizika sú nesprávne. Pri zmesi inštrumentov sa nesprávne menia aj váhy agregácie. `analytics.gross_and_volume()` používa tú istú neúplnú konvenciu.

**Oprava:** jednotný obchodný záznam s `point_value`, menou, vstupným/výstupným nominálom, gross/net PnL a nákladmi; jeden spoločný výpočet metrík. Migrácia starších výsledkov musí rozlišovať chýbajúcu hodnotu bodu od hodnoty 1. Prepočítať súhrny a analytiku dotknutých MNQ behov.

**Ďalšie súvisiace riziko:** Freqtrade `custom_stake_amount()` v `base.py:595` tiež pracuje s `qty * price`, zatiaľ čo `tester/ftexchange.py` dáva `point_value` iba do informačného slovníka. Ponuka Freqtrade umožňuje aj off-exchange futures. Tento konkrétny celý Freqtrade beh nebol spustený; mapovanie kontraktov je nutné integračne overiť alebo takú kombináciu zablokovať.

### A2 — P1: emulátor nedodá HTF okná pri väčšom grafe

**Miesta:** `tradebot/adapters/multicharts/emulator.py:234–239`; `tradebot/strategies/ibs/htf.py:52–71, 119–130`.

Emulátor najprv zavolá `runner.on_bar()` a až potom dodá HTF bary uzavreté počas práve dokončeného grafového baru. Feeder však môže práve tieto bary potrebovať už pri aktuálnom volaní. Offset Pine `[1]` sám o sebe nestačí, ak je graf podstatne väčší než detekčný TF.

Reprodukcia na 180 minútach syntetických dát, detekčný TF 5m:

| Graf | HTF okná v emulátore | Rovnaký feeder s vopred načítanými dátami |
|---|---:|---:|
| 3m | 31 | 31 |
| 5m | 32 | 32 |
| 10m | **0** | 16 |
| 15m | **0** | 11 |

**Dopad:** SD detekcia nedostane vstup, takže výsledok môže vyzerať ako neobchodujúca stratégia. Ak bežia SR/LQ zdroje, beh môže obchodovať, ale iba neúplnú časť zamýšľanej stratégie.

**Oprava:** sprístupniť feederu dáta uzavreté do času vyhodnotenia grafového baru pred jeho vyhodnotením; samotný feeder ďalej stráži Pine offset. Regresia musí zachovať súčasné 3m/5m golden časovanie a pokryť aj 5m/3m, 10m/5m a 15m/5m.

### A3 — P1: MultiCharts runner môže priradiť pozícii cudzí SL/TP

**Miesta:** `tradebot/adapters/multicharts/runner.py:151–169, 248–259`; `tradebot/adapters/multicharts/emulator.py:201–212, 244–249`.

Emulovaný broker pozná presné ID vyplneného orderu, ale runneru odovzdá iba veľkosť pozície a počet uzavretých obchodov. `_adopt_open_plan()` vždy vezme posledný vložený čakajúci order. Broker pritom vyberá prvý order, ktorého cena sa vyplní. IBS povoľuje viac odlišných čakajúcich zón rovnakého smeru, takže problém sa netýka iba teoretického long/short OCO.

Reprodukcia: čakajú long A (entry 100, SL 90) a long B (entry 95, SL 85). Pozíciu otvorí A. Runner adoptuje **B: entry 95, SL 85**. Po uzavretí grafového baru môže emulátor prepísať správne počiatočné SL/TP plánom B; aj stavový automat dostane nesprávne `open_order_ids`.

**Oprava:** explicitné fill/close udalosti s ID, cenou, množstvom a časom. V emulátore nie je dôvod hádať. Pri živom adaptéri napojiť dostupnú identitu exekúcie alebo jasne obmedziť podporovaný počet čakajúcich vstupov. Testovať aj obchod otvorený a zavretý v jednom bare.

### A4 — P1: limitný vstup má zvyšok prvej minúty vypnutý stop

**Miesta:** `tradebot/adapters/multicharts/emulator.py:213, 218–221`.

Ak sa limitka naplní vnútri minúty a nie na jej open, emulátor preskočí všetky výstupy v tejto minúte. Pri určitých cenových vzťahoch však poradie entry → SL nie je nejednoznačné.

Reprodukcia: long limit 100, SL 99; ďalšia minúta O=101, H=101, L=98, C=98. Cena musí po vstupe na 100 prejsť aj stopom 99. Kód obchod ponechá otvorený a zavrie až na ďalšej minúte na **98**. Pri následnom odraze by rovnaká chyba mohla naopak neprávom zachrániť obchod.

**Oprava:** samostatne riešiť jednoznačné dosiahnutie stopu po vstupe a skutočne nejednoznačné intrabar poradie. Nejednoznačnosť evidovať; `ambiguous_minutes` dnes túto vynechanú situáciu nepočíta. Testovať long aj short a medzery pri otvorení.

### A5 — P1: `maxDailyWins` v MultiCharts ceste nefunguje

**Miesta:** `tradebot/adapters/multicharts/runner.py:177–181`; `tradebot/core/orders.py:64`; `tradebot/strategies/ibs/statemachine.py:413–415`.

IBS kontroluje `ctx.daily_win_limit_reached`, ale MC runner ho nikdy nenastaví; zostáva `False`. `closed_trades` nesie iba počet obchodov a nepovie ich zisk ani deň. Emulátor pritom ziskové obchody pozná.

**Dopad:** nastavenie limitu výhier neobmedzí MC vstupy. Freqtrade používa vlastný približný model výhier, takže ani jeho číslo nie je plnohodnotnou referenciou skutočných exekúcií.

**Oprava:** spoločná evidencia realizovaných obchodov a jednotná definícia dennej výhry (deň, poplatky, poradie aktualizácie). Na hranici dňa a po výhre otestovať prvý ďalší povolený/zakázaný vstup.

### A6 — P1: trailing štyroch stratégií sa vo Freqtrade stratí

**Miesta:** `tradebot/adapters/freqtrade/base.py:329–331`; `tradebot/adapters/freqtrade/runner.py:58–75`; balíky `gap`, `orb`, `range`, `sdzone`: `engine.py`, `freqtrade.py`.

Tieto štyri enginy vytvoria `TradePlan.trailing` a formulár ponúka `enableTrailing`. Freqtrade `SignalRow` však trailing nenesie a príslušné adaptéry neprepisujú `_trailing_stop()`. Zdedí sa metóda, ktorá vráti pôvodný pevný stop. IBS a divergence majú vlastnú implementáciu; MultiCharts berie trailing z plánu.

**Dopad:** zapnutie trailingu pri gap/orb/range/sdzone vo Freqtrade nemení stop podľa deklarácie. Porovnanie engineov a ladenie týchto parametrov je zavádzajúce. `structure` tiež dedí základnú metódu, ale nemá týmto nálezom potvrdený deklarovaný trailing — do zoznamu chybných prepínačov ho preto nezahŕňam.

**Oprava:** preniesť kompletný plán cez adaptér a implementovať spoločný trailing kontrakt; alternatívou je explicitne odmietnuť nepodporovanú funkciu. Testovať výslednú cenu výstupu cez adaptér, nielen vytvorenie `TrailingPlan`.

### A7 — P1: Freqtrade stráca typ orderu a simuluje iný stav než skutočný vstup

**Miesta:** `tradebot/adapters/freqtrade/runner.py:58–75, 141–150, 209–230`; `tradebot/adapters/freqtrade/base.py:563–571`; `tradebot/strategies/ibs/statemachine.py:477–493`.

`OrderIntent.order_type` sa do `SignalRow` neprenesie. Adaptér používa limitnú vstupnú cenu z plánu a kontrolovaná trieda má vstupný typ `limit`. IBS pritom vie v jednom behu vytvárať IMB limitky a Pin Bar/Engulfing market vstupy. Aj interný model fillov bez ohľadu na typ vyžaduje, aby bar pretínal plánovanú cenu.

Reprodukcia: market long s plánom entry 100, ďalší bar O=105, H=106, L=104. Interný model hlási **nevyplnený** vstup. Market vstup sa má v tomto modeli vykonať na ďalšom open, aj keď sa cena 100 už neobjaví. Odlišný interný stav ovplyvňuje blokovanie vstupov, životnosť zón a denný limit.

**Oprava:** zachovať typ a identitu orderu v celom toku. Overiť, či cieľové Freqtrade rozhranie umožňuje požadovanú kombináciu market/limit na jednotlivých vstupoch; nepodporovanú kombináciu označiť alebo odmietnuť. Doplniť gap, market, fill a exit v jednej sviečke a zrušenie čakajúceho orderu do integračných testov.

### A8 — P2: štart Freqtrade validuje indikátor proti inému TF než požadovanému

**Miesta:** `tradebot/adapters/freqtrade/base.py:149–156`; `tradebot/strategies/ibs/ta/trend.py:267–277`.

Konštruktor správne zistí `run_tf` z nastavení, ale skúšobný engine pre `startup_candle_count` vytvorí s `self.timeframe`, ktorý ešte obsahuje default triedy. To môže aj nesprávne vypočítať dĺžku rozbehu.

Reprodukcia: IBS `tradeDirection=Indicator`, iba Supertrend na 5m, požadovaný graf 5m. Samostatný engine na 5m vznikne, ale adaptér skončí na `ValueError`: Supertrend 5m nie je násobkom grafu **3m**.

**Oprava:** používať rovnaký účinný TF pri validácii, predhistórii aj finálnom runneri. Testovať prepísanie TF oproti defaultu triedy, najmä 2m, 5m, 15m a indikátorový smer.

### A9 — P1 pre používanie analytiky ako vstupného filtra: režim trhu obsahuje budúcnosť

**Miesta:** `tester/regime.py:86–94, 135–176`; `tester/analytics.py:210–232`.

`annotate()` vyberie posledný bar s otváracím časom `<= open_date` a použije jeho celý high/low/close. Pri vstupe na otvorení alebo uprostred tohto baru ešte tieto údaje nie sú známe. Navyše volatilitu normalizuje mediánom ATR celej dostupnej série vrátane budúcnosti.

Reprodukcia: všetky bary pred vstupom zostali rovnaké. Zmenil sa iba close/low vstupnej sviečky. `_regime_align` sa zmenil zo **„s trendom“ na „proti trendu“** a `_regime_pos` z **0,9808 na 0,0070**.

**Dopad:** tieto rozdelenia môžu opisovať výsledok spätne, ale nemajú byť označené ako informácia dostupná pri vstupe. Skresľujú odporúčania na filtrovanie. Toto nie je dôkaz, že sa tento konkrétny režim už používa priamo na generovanie obchodov.

**Oprava:** vyberať iba bary uzavreté pred rozhodnutím a referenčné ATR určovať z minulosti alebo oddeleného tréningového obdobia. Zaviesť prefix test: pridanie/zmena budúcich dát nesmie zmeniť historický príznak.

### A10 — P2: MultiCharts obchody sa nespárujú s plánom v analytike

**Miesta:** `tradebot/adapters/multicharts/emulator.py:301`; `tradebot/strategies/ibs/zones.py:195–197`; `tester/analytics.py:274–298`; `tester/portfolio.py:101–112`.

MC zapisuje do `enter_tag` pôvodné ID, pri IBS napríklad `LONG_42`. Analytika očakáva za poslednou dvojbodkou epochový čas signálu. IBS tag preskočí; pri stratégiách s číselným indexom baru za dvojbodkou ho zase nesprávne považuje za milisekundy.

**Dopad:** `_sl_pct` a `_rr_planned` chýbajú aj pri existujúcich kresbách a uloženom počiatočnom SL. Následné portfólio/prop výpočty môžu obchod preskočiť alebo použiť vzdialenosť realizovaného stratového výstupu ako náhradu stopu.

**Oprava:** oddeliť `order_id`, `signal_time_ms`, `fill_time_ms` a plné plánované úrovne. Analytika má plán čítať z obchodného záznamu; grafické boxy nemajú byť jediná databáza rizika. Reprodukcia s MC tagom a zodpovedajúcimi boxmi vrátila `_sl_pct=None`.

### A11 — P2: front-month séria sa rozhoduje podľa ešte neznámeho objemu dňa

**Miesta:** `tester/bento_import.py:132–169`.

Pre celý UTC deň sa vyberie kontrakt podľa súčtu objemu celého toho istého dňa. Rozhodnutie pre prvú rannú sviečku teda závisí od večerných obchodov. Môže ísť o vedomú definíciu historickej kontinuálnej série, ale nie o výber kontraktu reprodukovateľný v reálnom čase.

Reprodukcia: ranný prefix zvolí starší kontrakt s cenou 100. Po doplnení večerného veľkého objemu novšieho kontraktu sa aj tá istá ranná sviečka zmení na cenu **200**.

**Oprava:** deterministický roll kalendár alebo výber podľa predchádzajúcej uzavretej obchodnej seansy. Pravidlo uložiť do dátového manifestu. Pri rolloveroch definovať aj reset/prechod indikátorov a prípadnú otvorenú pozíciu. Tvrdenie komentára, že skok nevadí, lebo stratégie zatvárajú denne, neplatí univerzálne: auditovaný profil `MNQ_R05_WR80_najzisk.json` má `closeAtSessionEnd=false`.

**Ďalšia hrana:** fallback na `kand.iloc[0]` pri absencii novšieho kandidáta umožňuje návrat na starší kontrakt, hoci dokumentácia tvrdí, že roll ide iba dopredu. Túto vetvu treba pri úpravách ošetriť testom.

### A12 — P2: MultiCharts backtest nemá explicitnú predhistóriu

**Miesta:** `tradebot/adapters/multicharts/emulator.py:166–181`; `tradebot/strategies/ibs/engine.py:73–78`; `tradebot/adapters/freqtrade/base.py:155–156`.

MC najprv odreže chart/detail/HTF na požadované okno a potom vytvorí nový engine. `required_history` sa pri tejto ceste nepoužije. Freqtrade má startup candles. Pri dlhom indikátorovom TF sa smer musí počas meraného okna ešte rozbiehať; zóny, ATR a stav na začiatku tiež závisia od zvoleného začiatku behu.

**Oprava:** oddeliť interval načítania a rozbehu od hodnoteného intervalu. Počas rozbehu definovať, čo sa simuluje a či sa môžu preniesť otvorené pozície. Porovnať rovnaký hodnotený interval po rovnakom predchádzajúcom replayi. Nie každý rozdiel po zmene štartu je chyba stavovej stratégie; chýba jednotná a evidovaná politika.

### A13 — P2: dve identické zadania v jednej sekunde môžu mať rovnaké ID

**Miesta:** `tester/webapp/store.py:38–41`; `tester/webapp/runner.py:503–514`.

ID je čas s presnosťou na sekundu plus deterministický hash parametrov/nastavení. Pri rovnakom zadaní v tej istej sekunde je rovnaké; poznámka a používateľ sa do hashu nezapočítavajú. `submit()` následne prepíše `self.jobs[id]`, hoci fronta môže obsahovať obe položky.

**Dopad:** dvojklik, opakovaný API request alebo dve rovnaké automatické zadania môžu zlúčiť či prepísať behy. Existujúci komentár o nekolidovaní dvoch testerov preto neplatí pre totožné nastavenia.

**Oprava:** jedinečné ID (UUID alebo náhodný suffix) oddeliť od deterministického výpočtového kľúča. Ak má byť opakovaný request idempotentný, zaviesť to ako explicitný kontrakt. Testovať dve simultánne odoslania.

## Chýbajúce časti a ďalšie nezrovnalosti

1. **Reprodukovateľnosť behov.** `_persist()` ukladá parametre a settings, ale chýba commit/verzia enginu, identita vstupných dát, verzia fill modelu a účinné instrument metadata. Po zmene kódu alebo importu rovnaký profil nemusí zopakovať výsledok. To je zároveň nevyhnutný základ bezpečnej výpočtovej cache.
2. **Kontrakt schopností adaptérov.** Registry overuje najmä existenciu profilov, parametrov a šablón. Potrebuje aj explicitné schopnosti: market/limit, trailing, timeout, denný limit, margin, funding, warmup a podporované TF. Nepodporovaná kombinácia má zlyhať pred behom, nie potichu zmeniť stratégiu.
3. **Rozdielne významy metrík.** MC `max_drawdown_pct` je max peňažný pokles delený počiatočnou peňaženkou; Freqtrade wrapper preberá `max_drawdown_account`. Pred spoločným rankingom zjednotiť definíciu alebo označenie. MC pri nulových stratách navyše vracia profit factor ako absolútny zisk; napríklad 10 USD výhier znamená PF 10, 100 USD znamená PF 100. Nekonečný/neurčený pomer potrebuje explicitnú reprezentáciu.
4. **Výpočtový čas je meraný neúplne.** MC runner nastaví `duration_s` a `finished` pred `rows_from_trades`, `summarize`, exportom grafu a persistenciou. Čas v histórii teda nezahŕňa všetko, na čo čaká používateľ. Pridať samostatné časy load/prepare/engine/broker/serialize/persist a celkový wall time.
5. **Výber Freqtrade výsledku zo spoločného adresára.** Runner porovná zoznam ZIP pred/po behu a vezme najnovší nový súbor. Jednovláknová fronta chráni iba jeden proces; ďalšie CLI alebo webapp inštancie môžu vložiť cudzí výsledok. Každý beh potrebuje vlastnú výstupnú cestu a overenie identity výsledku.
6. **História v Gite má dva protichodné režimy.** `.gitignore` teraz ignoruje nové `tester/runs/`, ale dokumentácia aj `gitsync.push()` stále opisujú automatické zdieľanie celej histórie cez bežné `git add`. Nové ignorované behy sa tak automaticky nezdieľajú. Dohodnúť režim: lokálna história + explicitný export/zdieľanie vybraných behov, alebo iné úložisko; upraviť UI a dokumentáciu podľa toho.
7. **Exekučná realita nie je plne modelovaná.** MC peňaženka slúži primárne ako menovateľ percent; v emulátore nie je brokerové obmedzenie marginom/likvidáciou a `funding_fees` je nula. To je modelové obmedzenie, nie automaticky chyba intradenného scenára. Musí byť súčasťou metadát a porovnania enginov.
8. **Vývojárske pravidlá a skutočný kontrakt sa rozchádzajú.** Požiadavka „rovnaké signály cez oba enginy“ nemôže byť všeobecne zaručená, ak stratégia číta kontext pozície a každý runner si vyrobí iné fill/close udalosti. Porovnávať treba najprv engine na rovnakom event streame a až potom vysvetľovať rozdiely broker modelov.

## Chýbajúce testy s najväčšou hodnotou

- Kontrakt testovať od `OrderIntent` cez adaptér až po výsledný obchod: typ vstupu, identita plánu, trailing, timeout, session close a limit výhier.
- Dva čakajúce longy s rozdielnym entry/SL/TP, iba prvý sa naplní; tiež round trip v jednom bare.
- Krížová matica chart TF / detection TF vrátane grafu väčšieho než detection TF a nevzájomne deliteľných gridov.
- Jednotky pri `point_value=1, 2, 50`: súhrn, Monte Carlo, analytika a porovnanie adapterov.
- Prefix invariancia príznakov a výberu kontraktu: budúce dáta nesmú prepísať už známy stav.
- Rovnaký plán s trailingom on/off cez gap/orb/range/sdzone adaptéry.
- Predhistória a začiatok/koniec intervalu, DST, víkend, dátová medzera, roll a neúplná posledná sviečka.
- Integračné smoke testy so zachovanými explicitnými rozdielmi fill modelov. Golden test jedného IBS nastavenia nemá byť jediný dôkaz exekučnej parity.

## Výkon: namerané výpočty a odporúčané zmeny

### Meranie

Lokálny Windows/Python z `.venv`, profil `tester/profiles/MNQ_R05_WR80_najzisk.json`, MNQ, graf **3m**, obdobie **2025-10-01 až 2026-01-01**, aktuálny kód bez optimalizácií. Ide o konkrétnu vzorku, nie univerzálny benchmark každej stratégie.

- Načítanie celého pracovného 1m feather: **2 593 168 riadkov za 0,065 s** (lokálna OS cache mohla byť teplá).
- `emulate()`, vrátane prípravy barov a zbierania kresieb, bez finálneho JSON/gzip exportu: **1,774 s**.
- Spracovaných **29 415 grafových barov**, **24 obchodov**.
- Druhý beh s `cProfile`: približne **4,507 s** kumulatívne v `emulate`; profiler sám beh spomaľuje. Celkom približne **18,68 milióna volaní**. Časy nižšie sú z profilovaného behu; nesčítavajú sa, pretože obsahujú vnorené volania.

| Oblasť | Kumulatívny čas | Pozorovanie |
|---|---:|---|
| Stavový automat zón | 1,705 s | 5 392 900 kontrol `_is_active` |
| Pivoty | 0,753 s | 235 320 volaní, 8 na grafový bar |
| Seansové hodiny | 0,512 s | opakované TZ/dátumové konverzie |
| Hľadanie imbalance | 0,501 s | 15 966 volaní, prehľadávanie histórie |
| Indexovanie histórie | 0,447 s | 2 391 700 volaní |
| Príprava chart/detail/HTF barov | 0,309 s | tri cesty cez `bars_from_frame` |
| Elliott | 0,198 s | počíta sa aj pri `showElliott=false` |

### Poradie optimalizácií

**1. Aktívna množina zón namiesto kompletného zoznamu na každom bare.**

`StateMachine.on_bar()` prechádza až stovky historických zón, hoci `_advance` sa v meraní zavolal iba 147 116-krát oproti 5,39 milióna kontrol aktivity. Oddeliť archív zón/kresieb od zoznamu vykonávaných stavov, expirácie riešiť časovo a mať index pending/open orderov. Zachovať poradie zón, deduplikáciu gapov, OCO a presnú sémantiku `used` v stavoch 2–5. Neodstraňovať bez rozmyslu všetky časovo expirované zóny: niektoré ešte nesú živý lifecycle.

To je najväčší nameraný lokálny kandidát. Podiel celej state-machine vetvy bol asi 38 % profilu, ale nie všetok jej čas je odstrániteľný. Bez implementácie a regresie nesľubujem konkrétne násobné zrýchlenie.

**2. Spoločný výpočet pivotov a podmienené dekoratívne indikátory.**

Market structure, S/R, liquidity a Elliott počítajú high/low pivoty zvlášť. S/R a liquidity v meranom profile používajú rovnakú dĺžku 10. Cache výsledku pre aktuálny bar, dĺžku a high/low môže odstrániť opakovanie. Neskôr prichádza do úvahy rolling/min-max implementácia, ktorá musí zachovať pravidlá pri rovnakých extrémoch.

Elliott nemá obchodný filter a pri vypnutom zobrazení sa jeho pivoty stále počítajú. Jeho 0,198 s sa prekrýva s časom pivotov; nemožno ho pripočítať ako nezávislú úsporu. S/R alebo liquidity sa nesmú vypnúť len preto, že sa nekreslia — môžu vytvárať obchodné zóny.

**3. Predpočítať seansové masky a hranice dňa.**

`SessionClock.state()` opakovane konvertuje rovnaký deň do časových pásiem a skladá začiatky/konce okien. Cachovať hranice podľa lokálneho dátumu, pásma a konfigurácie; pri offline dátach pripraviť pole zone/trade/session-end flagov. DST a okná cez polnoc musia mať regresné testy. Vzorka ukazuje asi 11 % kumulatívneho času.

**4. Zdieľať prípravu dát medzi bodmi sweepu.**

Každý MC job znovu číta celý súbor, filtruje čas a buduje chart/detail/HTF objekty. Zaviesť nemenný pripravený dataset a index rozsahov 1m detailu pre každý grafový bar. Cache kľúč musí obsahovať identitu/verziu dát, časové okno, predhistóriu, TF a verziu agregácie. HTF volume SMA navyše závisí od `volSmaLen`. Engine a broker stav sa medzi jobmi zdieľať nesmú.

V nameranej vzorke samotné diskové čítanie nie je priorita číslo jeden. Pri veľkom sweepe, dlhom období a Freqtrade opakovaných štartoch môže byť amortizácia prípravy oveľa dôležitejšia; treba ju zmerať samostatne.

**5. Výpočtový režim bez grafického exportu pre hľadanie parametrov.**

Každý bežný job zbiera kresby a pripravuje chart export. Výber parametrov primárne potrebuje signály, plány, fills a metriky. Zaviesť režimy `metrics`, `trades`, `full-chart`; graf dopočítať pre finalistov. Najprv odstrániť analytickú závislosť od TP/SL boxov podľa A10. Samotné vypnutie prepínačov zobrazenia nie je dostatočný kontrakt pre výpočtový režim.

Čas serializeru/exportu v tomto audite nebol samostatne zmeraný, takže mu nepripisujem odhadované percento úspory.

**6. Paralelizovať nezávislé behy až po izolácii výstupov.**

Jednovláknová fronta dnes serializuje celý sweep. Nezávislé CPU joby môžu využiť viac jadier procesovým poolom. Pre Python stavový automat uprednostniť procesy; obyčajné vlákna nie sú náhrada procesového paralelizmu. Každý worker potrebuje vlastný engine, broker, pracovné súbory a výstupný adresár. Vopred vyriešiť spoločný ZIP adresár a dočasné AI konfigurácie. Nastaviť limit podľa pamäte a nepúšťať popri tom hyperopt, ktorý už využíva viac jadier.

Prínos je hlavne kratší čas celej mriežky, nie nutne kratší jednotlivý beh. Bez súbežného benchmarku neuvádzam 4×/8× sľub.

**7. Výpočtová cache s auditovateľným kľúčom.**

Samostatný kľúč pre dáta/prípravu a samostatný pre výsledok: commit/algoritmus, úplný normalizovaný config, instrument, dátový hash, interval, warmup, fill model, poplatky a wallet podľa závislosti enginu. Poznámka alebo používateľ nemajú znemožniť reuse výpočtu. Bežný Freqtrade result cache nech zostane vypnutý, kým nie je overené, že pokrýva aj vlastné profily a tieto závislosti.

**8. Numba/Cython až po algoritmických zmenách.**

Vhodné kandidáty sú pivoty, ATR/SMA a prehľadávanie imbalance nad číselnými poľami. Súčasný objektový stavový automat s enumami, dataclassmi a kresbami nie je dobrý prvý cieľ pre plošný JIT. Najprv odstrániť zbytočné volania, zmerať nový profil a až potom kompilovať zostávajúci hotspot.

### Ako overovať zrýchlenie

Pre starú/novú implementáciu porovnať kompletný stream signálov a orderov, ceny/množstvá fillov, konečný PnL a počet nejednoznačných minút. Pri plnom režime aj kresby. Použiť viac profilov, 3m/5m/15m, kratšie aj viacročné okno, zóny SR/LQ, indikátorový smer a trailing. Meranie opakovať aspoň trikrát po zahriatí a uvádzať medián, pamäť a celkový wall time vrátane exportu. Dôkaz zrýchlenia nesmie stáť len na zhodnom počte obchodov.

## Navrhované poradie práce

1. Uzamknúť reprodukcie A1–A10 do testov; opraviť jednotky, fill identitu/časovanie a podporu funkcií adaptérov. Staré dotknuté výsledky označiť ako vypočítané starším modelom.
2. Doplniť explicitný plán a fill udalosti do záznamov; opraviť analytické časovanie, warmup a dátový roll kontrakt. Uložiť commit a dátový manifest ku každému behu.
3. Zaviesť meranie fáz, aktívne zóny, spoločné pivoty a cache seáns. Overiť plnú regresiu aj golden testy.
4. Zaviesť pripravené datasety a výpočtový režim pre sweep, potom izolované procesové workery a bezpečný reuse výpočtov.

Audit neimplementuje žiadnu z týchto opráv. Report a lokálny diagnostický skript sú podklady pre samostatnú implementačnú prácu.
