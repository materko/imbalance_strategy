# Webová aplikácia pre testerov

Lokálna stránka nad backtestom: tester si nastaví parametre stratégie,
vyberie pár a obdobie, spustí beh a po dobehnutí vidí to isté, čo Strategy Tester
v TradingView — štyri karty (Total PnL, Max drawdown, Profitable trades, Profit
factor), graf výnosnosti (kumulatívny PnL, buy and hold, stĺpce za obchod) a zoznam
obchodov. Každý beh sa uloží do gitu, takže história sa dá pushovať a pullovať
medzi testermi a hľadať v nej podľa parametrov.

**Engine si vyberáš** — `Freqtrade` (backtest Freqtradu) alebo `MultiCharts (emulátor)`
(ten istý runner, ktorý beží v štúdii, s brokerom podľa MultiCharts). Ponuka ukazuje len tie,
pre ktoré sú na disku dáta: Freqtrade potrebuje súbor pre zvolený timeframe, emulátor jediný
1m súbor. Krypto sa teda dá prehrať aj emulátorom a Dukascopy CFD aj cez Freqtrade — z toho
je porovnanie oboch ciest. Výsledok má v oboch prípadoch rovnaký tvar a história ich nerozlišuje
(engine je v detaile behu a dá sa podľa neho hľadať).

Pozor: signály sú v oboch enginoch rovnaké, **fill model nie**. Pre Dukascopy symboly je
referenciou emulátor — sedí s tým, čo v MultiCharts naozaj pobeží
([MULTICHARTS.md §E](MULTICHARTS.md), [FREQTRADE.md §G](FREQTRADE.md)).

## Spustenie bez Dockeru

Treba len **Python 3.11+ (64-bit)** a **git**; na macOS ešte `brew install ta-lib`
(Freqtrade ho potrebuje). Skript pri prvom spustení sám postaví `.venv`
(freqtrade + balík `tradebot`, zhruba 10 minút), pri štarte zloží dáta z archívov v gite,
ak chýbajú, a otvorí prehliadač na http://127.0.0.1:8765.

**Windows**: klonuj repozitár a dvojklikni na `webapp.cmd` v jeho koreni (obíde
ExecutionPolicy len pre tento skript), alebo v PowerShelli:
```powershell
git clone https://github.com/materko/imbalance_strategy.git
cd imbalance_strategy
.\webapp.ps1
```
Ak PowerShell odmietne spustiť `.ps1`, použi `webapp.cmd` alebo raz povoľ
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS jedným príkazom** — skript `install-macos.sh` overí a doinštaluje Xcode Command
Line Tools, Homebrew, `python@3.12` a `ta-lib`, spýta sa, kam repozitár klonovať a ako sa
má priečinok volať, aké meno testera a e-mail použiť pre git, naklonuje (alebo aktualizuje)
repozitár, postaví `.venv`, zloží dáta z archívu, dá na Plochu „IBS Backtester.command"
a ponúkne spustenie:
```bash
curl -fsSL https://raw.githubusercontent.com/materko/imbalance_strategy/main/install-macos.sh | bash
```
Otázky číta z terminálu, takže funguje aj cez `curl | bash`. Opakované spustenie len
aktualizuje, čo treba. Meno testera ide do `git config` repozitára a do `TRADEBOT_USER`
v spúšťači na Ploche, takže webapp ho má predvyplnené.

**macOS / Linux ručne**:
```bash
brew install ta-lib            # len macOS, raz
git clone https://github.com/materko/imbalance_strategy.git
cd imbalance_strategy
./webapp.sh
```

Koreňové `webapp.*` sú len obaly nad `tester/scripts/webapp.*`.
Voliteľné: `-Port 9000` / `TRADEBOT_WEB_PORT=9000`, `-NoBrowser` / `NO_BROWSER=1`.
Server sa ukončí Ctrl+C. Aktualizácia kódu je `git pull` v koreni repozitára.

**Docker** (alternatíva, bez Git tlačidiel v UI):
```bash
docker compose -f docker/docker-compose.yml run --rm --service-ports webapp
```

## Čo si aplikácia doplní pri štarte

Než začne počúvať, dorobí, čo chýba, a povie to na konzole:

1. **sviečky z archívu** — `data_archive merge`, keď v `data/tester/` chýba čokoľvek, čo
   je v `data_archive/` (nestačí, že tam je „aspoň niečo": s jediným rozbaleným zdrojom by
   bola ponuka párov poloprázdna);
2. **vyššie timeframy z 1m** — podľa [`tester/timeframes.json`](../tester/timeframes.json),
   dnes 2m, 3m, 4m, 5m, 15m, 30m, 1h, 4h, 1d, 1w. Freqtrade si ich z 1m nedopočíta, chce
   súbor na disku. Doplní sa len to, čo chýba; stiahnuté z burzy sa neprepisuje a
   dopočítané sa necommituje ([docs/DATA.md](DATA.md));
3. **ASCII pre QuoteManager** — pre symboly, ktoré bežia v MultiCharts (`TRADEBOT_QUOTEMANAGER=all`
   aj krypto, `=off` nič).

Prvý štart po pridaní timeframu preto chvíľu trvá (u nás 43 súborov ≈ 10 s), ďalšie už nie.
Ručne: `python -m tester.timeframes` a `python -m tester.data_archive merge`.

Ani to však nie je podmienka: **keď súbor pre beh chýba, poskladá si ho stratégia sama**
pri štarte behu (`ensure_timeframe` vo Freqtrade adaptéri, [docs/DATA.md](DATA.md)). Stačí
mať 1m sviečky — ponuka enginov to už tak aj počíta.

**Burza** je vlastný výber vedľa enginu. Predvolená je **Tester** — fiktívna burza
(`tester/ftexchange.py`), ktorá pozná naše páry aj všetky timeframy z `timeframes.json`,
takže 2m aj 4m sa dajú backtestovať a hyperoptovať, hoci ich Binance nemá. V ponuke je aj
skutočná burza, odkiaľ sviečky sú (Binance, prípadne nosná burza pre CFD) — na kontrolu, či
sa niečo nerozišlo s realitou; overené je, že na tom istom páre a profile dá **obchod po
obchode to isté** ([meranie](merania/BURZA_tester_vs_binance_2026-09-09.md)). Pri emulátore
MultiCharts je pole zamknuté: ten burzu nepotrebuje, číta priamo 1m sviečky.

Jediná podmienka behu sú 1m sviečky ([docs/FREQTRADE.md](FREQTRADE.md)).

## Meno testera

V hlavičke stránky je pole s menom. Ukladá sa ku každému behu (stĺpec v histórii,
hľadanie `user~jana`) a použije sa ako autor commitu pri Push. Drží sa v tomto
prehliadači; predvolené je `TRADEBOT_USER` z prostredia, inak `git config user.name`.

## Nový beh

Formulár je dvojstĺpcová mriežka: čo spolu súvisí, je vedľa seba (engine a burza, od a do,
timeframe a poplatok), sekcie oddeľuje vlások a dlhé vysvetlenia sú v tooltipoch, nie pod
každým poľom. Ľavý stĺpec skroluje sám a **Spustiť backtest** ostáva pripnuté na jeho
spodku, takže je na dosah aj pri rozpísanom formulári. Nad dátumami sú rýchle rozsahy
**1 rok / 2 roky / celé dáta** — počítajú sa od konca dát zvoleného páru.


**Stratégia** je prvý select: prepne formulár na parametre zvolenej stratégie, jej profily
a predvolený timeframe. Stratégie sú v registry `tradebot.strategies.STRATEGIES` (dnes IBS
Imbalance Breakout a ukážková Demo Donchian Breakout; ako pridať ďalšiu: `docs/STRATEGIE.md`).

**Východiskový profil** je len balík odchýlok od Pine defaultov zvolenej stratégie. „(Pine defaulty)" dá
presne to, čo má TradingView bez zásahu do nastavení; okrem toho sú na výber iba tri
referenčné profily z `tradebot/strategies/ibs/configs/` (golden test proti TradingView na Binance a Coinbase,
MultiCharts MNQ) — profil prepne aj pár na ten, pre ktorý je určený. Skúšané konfigurácie
z vývoja (NY seansa, SL filter, risk sizing…) sú v `docs/profily_archiv/` s tabuľkou
odchýlok a dajú sa načítať cestou cez CLI; vo formulári si tie isté hodnoty nastavíš
ručne alebo cez „Načítať do formulára" z histórie.

Vlastný profil patrí stratégii, s ktorou vznikol (kľúč `_strategy`), a ponuka ukazuje
len profily aktívnej stratégie. Ponuka má dve skupiny: **profily repozitára** (`tradebot/strategies/<stratégia>/configs/`, sú kód — testy a
merania sa na ne odvolávajú, preto sa z webapp nedajú meniť) a **vlastné profily**
testera (`tester/profiles/`). Vlastný profil vznikne dvoma spôsobmi: tlačidlom
**Uložiť ako profil** pod ponukou (uloží celý formulár — parametre, pár, TF, obdobie,
poplatok, peňaženku aj 1m detail) alebo rovnakým tlačidlom v detaile behu (uloží
nastavenie toho behu). **Premenovať**
a **Zmazať** fungujú len na vlastné profily. Zmeny profilov idú do gitu tým istým
**Push** ako história behov.

Meno je zároveň meno súboru, takže medzera sa mení na podtržník a diakritika padá
preč („Môj profil 5m" → `Moj_profil_5m`); keď sa profil uložiť nedá, vyskočí popup
s dôvodom. K profilu patrí aj **TF grafu**: limity `*MaxBars` sú v baroch, takže
profil ladený na 5m nesedí na 3m. Výber profilu preto TF prepne — profil repozitára
(nemá uložený TF) na 3m.

**Burza MultiCharts**: páry s Dukascopy dátami (`NAS100`) idú cez emulátor MultiCharts
priamo v procese webapp (bez Freqtrade) — ten istý runner ako študia v MultiCharts, jedna
pozícia, SL/TP po 1m; `timeframe_detail` sa ignoruje, 1m je vždy. Ako pridať symbol:
README, sekcia „Dukascopy dáta".

**Pár** je v ponuke ako **zdroj · trh · symbol** — `binance · futures · BTCUSDT.P`,
`binance · spot · BTCUSDT`, `dukascopy · cfd · NAS100` —, zoskupený podľa zdroja dát.
Z jedného riadku je tak vidno, odkiaľ sviečky sú a čo sa obchoduje, aj keď je select
zavretý; symbol je ten, ako ho volá burza (`BTCUSDT.P` je perpetuál, vo Freqtrade
`BTC/USDT:USDT`). Pod ponukou je celý popis trhu a rozsah dát.

Na spote sa nedá shortovať ani páčiť — burza nemá čo požičať. Pri spotovom páre sa
preto `tradeDirection` prepne na „Long only", `leverage` na 1 a obe polia sa zamknú;
beh s inou hodnotou API odmietne (aj z CLI), nech sa nestane, že výsledok vyzerá
platne, hoci sa taký obchod v skutočnosti spraviť nedá. Spot beží s vlastným
Freqtrade configom (`config.binance.spot.json`, `trading_mode: spot`).

**Parametre** sú všetky polia configu zvolenej stratégie — Pine vstupy v rovnakých
skupinách, s rovnakými titulkami a tooltipmi ako v TradingView (parsujú sa priamo z Pine
súboru stratégie, takže sa nemôžu rozísť), plus skupina „Rozšírenia portu" (polia, ktoré
Pine nemá). Pri IBS je to `tradebot/strategies/ibs/docs/sources/imbalance_strategy_FULL.pine` a rozšírenia `atrLen`,
`legacyPineSizing`, `leverage`, `minSlDistance`; pri demo stratégii 9 polí.
Pri IBS sa neponúkajú polia, ktoré v porte nerobia nič: `alert*` (v Pine notifikácie
TradingView) a tabuľky kreslené na graf v TradingView — `showDashboard`, `showTradeLog`,
`showDebugTable` s ich pozíciami a počtami riadkov; to isté ukazuje webapp vo vlastných
tabuľkách. V `IBSConfig` ostávajú, aby profil sedel s TV panelom, a do uloženého profilu
sa zapíšu s Pine defaultom. Kresliaci prepínač `showImbalance` ponuka má — ten rozhoduje,
či sa do kresieb behu dostanú imbalance boxy.
Panel vyzerá ako nastavenia v TradingView: vľavo zoznam skupín, vpravo všetky skupiny
pod sebou v jednom dlhom zozname, ktorý skroluje vo vlastnom okne (stránka stojí) —
klik na skupinu vľavo naň naskroluje a zvýraznenie sleduje, kde práve si. Jeden parameter na riadok; polia, ktoré Pine kreslí vedľa seba (hodina a minúta seansy,
zapnutie a časové pásmo), sú vedľa seba aj tu. Tooltip z Pine, identifikátor a rozsah
sa ukážu po podržaní myši na názve. Zmenené hodnoty oproti profilu sú žlté, skupina
ukazuje ich počet, ↺ vráti hodnotu profilu. Hľadanie prechádza všetky skupiny naraz
(názov, popis, identifikátor); „len zmenené" ukáže iba odchýlky.

Podnastavenia vypnutej feature sa neukazujú: keď je seansa vypnutá, nevidíš jej časy,
keď je vypnutý trailing, nevidíš jeho R-násobky, S/R a likviditné parametre sa ukážu,
až keď z nich obchoduješ alebo ich kreslíš. Prepínač so skrytými podnastaveniami má
vedľa seba „▸ N nastavení skrytých". Hľadanie a „len zmenené" ukážu aj skryté polia.
Hlavný prepínač feature má vedľa seba zrkadlový checkbox „kresliť" (IMB entry ↔
`showImbalance`, S/R ↔ `showSR`, likvidita ↔ `showLiqSweep`) — je to to isté pole ako
v jeho Pine skupine, len po ruke. Pine defaulty kreslia všetko. Závislosti sú ručná
tabuľka `FEATURES` v `tradebot/strategies/<stratégia>/meta.py`, lebo Pine ich nedeklaruje.

Polia s veľkosťou (`*Points`, `*Ticks`, `minSlDistance`) majú jednotku:
`abs` cenové body, `ticks` násobky ticku, `atr` násobky ATR grafového TF,
`pct` percento ceny. Holá hodnota v profile znamená pôvodnú Pine jednotku.

**Nastavenia behu**: pár (len tie, ktoré majú stiahnuté dáta — BTC a ETH), **timeframe
grafu** (TF, na ktorom stratégia počíta — ako keď v TradingView prepneš TF grafu; default 3m,
ponuka podľa stiahnutých dát; limity v baroch ako `*MaxBars` sa neprepočítavajú, takže 1m
alebo 15m je iná stratégia, nie len iné rozlíšenie; detekčný TF zón by mal byť aspoň taký
hrubý ako TF grafu), obdobie
(obmedzené na dostupné dáta), poplatok na stranu v % (Binance taker 0,05), peňaženka,
1m detail fillov (odporúčané, viď ARCHITECTURE_port.md §7) a poznámka — tú potom
vidíš v histórii, tak napíš, čo beh testuje.

Config sa validuje pri odoslaní (rozsahy z Pine `minval`/`maxval`, konzistencia
seáns, sizing), chyba sa ukáže vo formulári a nič sa nespustí.

## Fronta

Beží vždy jeden backtest; ostatné čakajú. Pri bežiacom sa ukazuje živý koniec logu.
Rok s 1m detailom trvá zhruba 20–30 sekúnd. ✕ beh zruší (aj bežiaci).

## História

Tabuľka všetkých behov: stratégia, pár, obdobie, počet obchodov, PnL %, profit factor, winrate,
max drawdown, **break-even poplatok** (% na stranu — koľko smie burza brať, aby beh
vyšiel na nulu; porovnaj s 0,05 % Binance taker) a odchýlky parametrov od Pine
defaultov ako štítky.

### Vyhľadávanie

Podmienky oddelené medzerou, všetky musia platiť:

```
rrRatio>=5 useStructureFilter=true pair~ETH pnl>0 note~seansa
```

`názov op hodnota`, kde op je `= != > < >= <= ~` (`~` = obsahuje text). Názov je
ktorýkoľvek parameter configu (SizeSpec sa porovnáva cez hodnotu) alebo skratka
výsledku: `pnl` (%), `pnl_abs`, `trades`, `pf`, `wr`, `dd`, `be` (break-even),
`pair`, `strategy` (alebo `strat`), `timerange`, `fee`, `wallet`, `profile`, `note`, `user`,
`status`. Slovo bez
operátora sa hľadá v poznámke, páre, profile a id.

### Detail behu

Karty ako v Strategy Testeri plus break-even poplatok a buy & hold; graf:

* **stĺpce** — PnL každého obchodu v % z počiatočného kapitálu (vlastná skrytá os
  v rovnakom pomere, aby nula sedela s krivkou),
* **zelená krivka** — kumulatívny PnL,
* **modrá** — buy and hold (zmena ceny páru od začiatku okna, denné vzorky).

**Graf páru** pod tým je to, čo by si videl v TradingView na grafe: sviečky páru
a všetko, čo engine v tomto behu nakreslil — pásy seáns, SD zóny (formácia bodkovane,
potvrdená s výplňou; tehlová = Demand/LONG, modrá = Supply/SHORT, zelená = volume
potvrdená, sivá = expirovaná), imbalance sviečky, TP/SL boxy, štítky stavového
automatu (SKIP, počítadlá, EXPIRED…), štruktúru (BOS/CHoCH, swingy), S/R úrovne,
liquidity sweepy a Elliott. Navrch sú skutočné obchody Freqtradu: trojuholník je
vstup (zelený long, červený short), krížik výstup, bodkovaná spojnica zelená pri zisku
a červená pri strate; hover ukáže ceny, čas, dôvod výstupu a PnL.

Ovládanie: šípky posúvajú okno, „prvý obchod" a klik na riadok v zozname obchodov
naň graf skočí, `okno` mení dĺžku (4 h – týždeň), `TF` je auto (3m, pri širšom okne
hrubší, aby to bolo max. 6 000 sviečok) alebo ručne, `skoč na` je dátum a čas
začiatku okna. Ťahanie myšou posúva, koliesko zoomuje; keď vyjdeš z načítaného okna,
dotiahne sa ďalšie. Zaškrtávacie polia vypínajú vrstvy (počet v zátvorke je za celý
beh) a voľba sa pamätá v prehliadači. Časy sú UTC.

Pod tým odchýlky od Pine defaultov (s Pine hodnotou vedľa), dôvody výstupu, Monte Carlo
(nižšie), zoznam obchodov, všetky parametre a skrátený log Freqtradu.

#### Monte Carlo — interval okolo výsledku a veľkosť účtu

Rozbaľovacia sekcia. Z obchodov behu sa losujú tisíce nových sérií — **po blokoch**
desiatich po sebe idúcich obchodov, aby sa série strát nerozsypali (jeden režim trhu
vyrobí päť SL za sebou a práve tie zabíjajú účet; `bloky po 1` je klasický bootstrap
s nezávislými obchodmi).

Karty ukazujú **edge**: break-even poplatok, jeho 90 % interval a pravdepodobnosť, že
prevýši zvolenú sadzbu — a **účet**: max drawdown v % z vrcholu, najdlhšiu sériu strát,
najdlhšie čakanie na nové maximum a konečný zostatok. Pod nimi sú dva histogramy
(rozdelenie break-even poplatku a max drawdownu) a tabuľka, ako často účet klesne pod
−10/−20/−30/−50 % počiatočného zostatku a ako často skončí na nule.

V paneli sa dá zmeniť poplatok (predvyplnený ten, s akým beh bežal — aj nulový),
**veľkosť účtu** a **riziko na obchod**: obchody sa preškálujú z `maxLossDollar` profilu,
takže sa dá pýtať „čo s tou istou stratégiou na účte 25 000 a rizikom 250". Pod tabuľkou
je odpoveď na opačnú otázku: koľko sa smie riskovať, aby 95 % ciest zostalo nad −20 %.
Profil s `legacyPineSizing` (pevný počet kontraktov) sa preškálovať nedá — pole je vtedy
zamknuté a odporúčanie sa nevypíše.

Ráta sa až po rozbalení, lebo beh s tisíckami obchodov trvá jednotky sekúnd; výsledok si
server pamätá, takže opätovné otvorenie je okamžité.

Pod 30 obchodov to samo napíše, že vzorka je primalá. A platí, že **bootstrap nemeria
pretrénovanie** (proti tomu chránia len dáta, ktoré optimalizátor nevidel) a že účet sa
počíta z uzavretých obchodov — priebeh otvorenej pozície, a teda margin, v tom nie je,
rovnako ako denné limity strát. To isté z CLI: `python -m tester.montecarlo <run_id>`
([tester/AI_TESTING.md §5](../tester/AI_TESTING.md)).

## Kde história žije a ako sa zdieľa

```
tester/runs/<YYYYMMDD-HHMMSS-odtlačok>/
    run.json        parametre, nastavenia (vrátane settings.strategy), výsledok (súhrn), séria pre graf
    trades.json     obchody
    log.txt         skrátený log
    chart.json.gz   kresby enginu pre graf páru (zóny, boxy, štítky…)
```

Všetko okrem kresieb je čitateľný JSON, jeden adresár na beh, takže sa to mergeuje bez
konfliktov. Kresby sú gzip: ročný beh má ~90 000 objektov (12 MB v JSON, 1,5 MB
zbalené) a súbor sa po zápise už nemení, takže diff netreba. Sviečky sa k behu
neukladajú — čítajú sa z pracovných `data/` platformy (v gite ako `data_archive/tester/`), takže graf
funguje aj pre beh stiahnutý od iného testera. Behy z čias pred týmto súborom ukážu
sviečky a obchody bez kresieb.

Ako kresby vznikajú: stratégia dostane cez `TRADEBOT_DRAW_OUT` cestu, kam má po backteste
vysypať finálny stav `DrawRegistry` (rovnaký mechanizmus ako `tester.plot`);
webapp súbor po dobehnutí presunie do adresára behu.

Vlastné profily žijú vedľa histórie:

```
tester/profiles/<meno>.json
```

Na rozdiel od profilov repozitára (tie držia len odchýlky od Pine defaultov) je
vlastný profil **úplný — zapíše sa každé pole configu**. Nezávisí tak na tom, čo je
práve default ani na profile, z ktorého vznikol: keď sa hocičo z toho neskôr zmení,
starý profil ostane presne taký, aký bol, a beh sa dá zopakovať.

K tomu metadáta s podtržníkom: `_instrument` (z neho sa nastaví pár), `_title` a
`_comment` (popis a z ktorého behu profil vznikol) a celé nastavenie behu —
`_timeframe`, `_timerange`, `_fee`, `_wallet`, `_detail`. Výber profilu ich všetky
prenesie do formulára (obdobie orezané na dáta, ktoré pre pár sú); čo profil nemá —
napríklad profily repozitára — nechá formulár tak, ako si ho nastavil.

`_base` hovorí, z ktorého profilu si vychádzal (pri uložení z formulára to, čo bolo
vybrané ako *Východiskový profil*, pri uložení z behu profil toho behu). Pod ponukou
je vtedy vidieť „vychádza z profilu …". Hodnoty sú vlastné a nemenné — je to záznam
pôvodu, nie odkaz: keď sa východiskový profil neskôr zmení, tvoj sa nepohne.

Meno súboru má 2–48 znakov: písmená bez diakritiky, číslice, `.`, `-`, `_`;
meno profilu repozitára sa použiť nedá, aby sa nedal prekryť.

Tlačidlá **Pull** a **Push** sú v hlavičke; výstup gitu sa zobrazí celý. Push commitne
**len** `runs/` a `profiles/` a pushne ich do **`main`** — nie na vetvu, na ktorej klon
práve stojí (inak história skončí na vývojárskej vetve a nikto ju neuvidí). Iný cieľ sa
dá nastaviť cez `TRADEBOT_GIT_BRANCH`. Keď sa vetva klonu a cieľ líšia, hlavička to ukáže
ako `vetva → main`.

Ak by mala vetva klonu oproti `main` commity mimo `runs/` a `profiles/`, Push sa
zastaví a povie to: kód z testerského klonu do `main` nepatrí, ten ide pull requestom.
Autor commitu je meno testera z hlavičky.

**Prihlásenie do GitHubu.** Webapp beží bez terminálu, takže sa git nemá koho spýtať na
heslo — bez uložených údajov Push spadne na `could not read Username … Device not
configured` (macOS) a aplikácia rovno vypíše návod. Stačí sa prihlásiť raz:

```bash
gh auth login && gh auth setup-git          # macOS/Linux, najjednoduchšie
git config --global credential.helper osxkeychain   # macOS bez gh: potom raz `git push`
git config --global credential.helper manager       # Windows
```

Commit sa spraví aj tak, takže po prihlásení stačí kliknúť Push znova — nič sa nestratí.

Behy z čias pred registry stratégií nemajú `settings.strategy` — čítajú sa ako `ibs`,
na disku sa nemenia.

Výsledkové zipy Freqtradu ostávajú v `backtest_results/` (gitignored) — beh ich
nepotrebuje, všetko podstatné je v `run.json`.

## Príkazový riadok a Claude Code

`python -m tester.webapp.cli` robí to isté, čo stránka, z terminálu — pre Claude Code
testera a pre skripty. `run` ide cez API bežiacej webapp (beh vidno vo fronte), a keď
webapp nebeží, spustí backtest priamo do toho istého `runs/`. `list`/`show` čítajú
históriu, `pull`/`push` synchronizujú `runs/` a `profiles/`, `status` povie, či webapp beží,
`params` vypíše parametre s rozsahmi. `run` aj `params` majú `--strategy <kľúč>` (default `ibs`).

```bash
python -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json [--timeframe 5m] \
    --set rrRatio=4 --set minSlDistance=0.25@pct --timerange 20250904-20260904 --note "RR 4"
python -m tester.webapp.cli list "rrRatio>=4 pnl>0"
```

Kompletné pokyny pre Claude Code (spúšťanie, reštart, aktualizácia, Git) sú
v [`CLAUDE.md`](../CLAUDE.md) v koreni repozitára — Claude Code ho načíta sám.
Pokyny majú dva režimy podľa súboru `.ibs-role` v koreni klonu (gitignored):
`tester` = obmedzenia a presné príkazy z CLAUDE.md, `developer` = bez obmedzení.
Ak súbor chýba, Claude Code sa na začiatku raz spýta a odpoveď si zapíše;
inštalátor pre macOS zapisuje `tester` automaticky. Rola sa dá kedykoľvek prepnúť
(„prepni na developer").

## Čo aplikácia nerobí

* Nesťahuje dáta — páry a obdobia sú len tie, čo sú v archíve
  (`python -m tester.data_archive`, docs/DATA.md).
* Nemá prihlásenie — je na lokálne spustenie (alebo za reverse proxy).
* Nespúšťa hyperopt; na ten sú skripty v `deploy/freqtrade/scripts/`.

## Kód

`tester/webapp/`: `pine_meta.py` (metadáta z Pine súboru stratégie, `param_metadata(spec)`),
`store.py` (behy a vyhľadávanie),
`runner.py` (fronta, Freqtrade podproces alebo emulátor MultiCharts, spracovanie zipu), `chart.py` (sviečky
z feather súborov po oknách, orezanie kresieb na okno), `gitsync.py`,
`app.py` (FastAPI), `static/` (stránka bez frameworku, Plotly z CDN).
Export kresieb: `tradebot/adapters/freqtrade/runner.py::export_chart`, serializácia
`tradebot/core/drawing.py::objects_to_dicts`.
Monte Carlo v detaile počíta `tester/montecarlo.py` (čistý výpočet nad obchodmi, bez znalosti
webapp); `app.py` ho len obalí endpointom `/api/runs/<id>/montecarlo` s pamäťou na posledné
výsledky.
Testy: `tester/tests/test_webapp.py`, `tester/tests/test_chart_export.py`,
`tester/tests/test_webapp_multicharts.py`, `tester/tests/test_montecarlo.py`.
Cesty (`tester/runs`, `tester/profiles`, dáta platforiem): `tradebot/core/paths.py`.
