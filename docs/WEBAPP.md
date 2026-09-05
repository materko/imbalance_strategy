# Webová aplikácia pre testerov

Lokálna stránka nad Freqtrade backtestom: tester si nastaví parametre stratégie,
vyberie pár a obdobie, spustí beh a po dobehnutí vidí to isté, čo Strategy Tester
v TradingView — štyri karty (Total PnL, Max drawdown, Profitable trades, Profit
factor), graf výnosnosti (kumulatívny PnL, buy and hold, stĺpce za obchod) a zoznam
obchodov. Každý beh sa uloží do gitu, takže história sa dá pushovať a pullovať
medzi testermi a hľadať v nej podľa parametrov.

## Spustenie bez Dockeru

Treba len **Python 3.11+ (64-bit)** a **git**; na macOS ešte `brew install ta-lib`
(Freqtrade ho potrebuje). Skript pri prvom spustení sám postaví `.venv`
(freqtrade + balík `ibs`, zhruba 10 minút), pri štarte zloží dáta z `data_archive/`,
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
aktualizuje, čo treba. Meno testera ide do `git config` repozitára a do `IBS_USER`
v spúšťači na Ploche, takže webapp ho má predvyplnené.

**macOS / Linux ručne**:
```bash
brew install ta-lib            # len macOS, raz
git clone https://github.com/materko/imbalance_strategy.git
cd imbalance_strategy
./webapp.sh
```

Koreňové `webapp.*` sú len obaly nad `platforms/freqtrade/scripts/webapp.*`.
Voliteľné: `-Port 9000` / `IBS_WEB_PORT=9000`, `-NoBrowser` / `NO_BROWSER=1`.
Server sa ukončí Ctrl+C. Aktualizácia kódu je `git pull` v koreni repozitára.

**Docker** (alternatíva, bez Git tlačidiel v UI):
```bash
docker compose -f docker/docker-compose.yml run --rm --service-ports webapp
```

## Meno testera

V hlavičke stránky je pole s menom. Ukladá sa ku každému behu (stĺpec v histórii,
hľadanie `user~jana`) a použije sa ako autor commitu pri Push. Drží sa v tomto
prehliadači; predvolené je `IBS_USER` z prostredia, inak `git config user.name`.

## Nový beh

**Východiskový profil** je len balík odchýlok od Pine defaultov. „(Pine defaulty)" dá
presne to, čo má TradingView bez zásahu do nastavení; okrem toho sú na výber iba tri
referenčné profily z `ibs/configs/` (golden test proti TradingView na Binance a Coinbase,
MultiCharts MNQ) — profil prepne aj pár na ten, pre ktorý je určený. Skúšané konfigurácie
z vývoja (NY seansa, SL filter, risk sizing…) sú v `docs/profily_archiv/` s tabuľkou
odchýlok a dajú sa načítať cestou cez CLI; vo formulári si tie isté hodnoty nastavíš
ručne alebo cez „Načítať do formulára" z histórie.

Ponuka má dve skupiny: **profily repozitára** (`ibs/configs/`, sú kód — testy a
merania sa na ne odvolávajú, preto sa z webapp nedajú meniť) a **vlastné profily**
testera (`user_data/profiles/`). Vlastný profil vznikne dvoma spôsobmi: tlačidlom
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

**Pár** je pomenovaný tak, ako ho volá burza, a ponuka je rozdelená na **Futures
(perpetual)** a **Spot**: `BTCUSDT.P` je perpetuál (`BTC/USDT:USDT` vo Freqtrade),
`BTCUSDT` je spot (`BTC/USDT`). Pod ponukou je vidno, o ktorý trh ide.

Na spote sa nedá shortovať ani páčiť — burza nemá čo požičať. Pri spotovom páre sa
preto `tradeDirection` prepne na „Long only", `leverage` na 1 a obe polia sa zamknú;
beh s inou hodnotou API odmietne (aj z CLI), nech sa nestane, že výsledok vyzerá
platne, hoci sa taký obchod v skutočnosti spraviť nedá. Spot beží s vlastným
Freqtrade configom (`config.binance.spot.json`, `trading_mode: spot`).

**Parametre** sú všetkých 114 polí `IBSConfig` — 110 Pine vstupov v rovnakých
skupinách, s rovnakými titulkami a tooltipmi ako v TradingView (parsuje sa to
priamo z `pine/imbalance_strategy_FULL.pine`, takže sa nemôžu rozísť), plus skupina
„Rozšírenia portu" (`atrLen`, `legacyPineSizing`, `leverage`, `minSlDistance`).
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
tabuľka `FEATURES` v `ibs/webapp/pine_meta.py`, lebo Pine ich nedeklaruje.

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

Tabuľka všetkých behov: pár, obdobie, počet obchodov, PnL %, profit factor, winrate,
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
`pair`, `timerange`, `fee`, `wallet`, `profile`, `note`, `user`, `status`. Slovo bez
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

Pod tým odchýlky od Pine defaultov (s Pine hodnotou vedľa), dôvody výstupu, zoznam
obchodov, všetky parametre a skrátený log Freqtradu.

**Načítať do formulára** vráti parametre aj nastavenia behu do formulára — na
úpravu jedného parametra a nový beh. **Uložiť ako profil** spraví z behu východiskový
profil pod vlastným menom (pýta si meno a krátky popis) — objaví sa v ponuke
„Východiskový profil" v skupine *Vlastné profily*. **Stiahnuť profil** dá JSON
použiteľný priamo cez `IBS_PROFILE=cesta.json` v CLI. **Zmazať** odstráni adresár behu.

## Kde história žije a ako sa zdieľa

```
platforms/freqtrade/user_data/runs/<YYYYMMDD-HHMMSS-odtlačok>/
    run.json        parametre, nastavenia, výsledok (súhrn), séria pre graf
    trades.json     obchody
    log.txt         skrátený log
    chart.json.gz   kresby enginu pre graf páru (zóny, boxy, štítky…)
```

Všetko okrem kresieb je čitateľný JSON, jeden adresár na beh, takže sa to mergeuje bez
konfliktov. Kresby sú gzip: ročný beh má ~90 000 objektov (12 MB v JSON, 1,5 MB
zbalené) a súbor sa po zápise už nemení, takže diff netreba. Sviečky sa k behu
neukladajú — čítajú sa z `user_data/data` (v gite ako `data_archive/`), takže graf
funguje aj pre beh stiahnutý od iného testera. Behy z čias pred týmto súborom ukážu
sviečky a obchody bez kresieb.

Ako kresby vznikajú: stratégia dostane cez `IBS_DRAW_OUT` cestu, kam má po backteste
vysypať finálny stav `DrawRegistry` (rovnaký mechanizmus ako `ibs.tools.plot`);
webapp súbor po dobehnutí presunie do adresára behu.

Vlastné profily žijú vedľa histórie:

```
platforms/freqtrade/user_data/profiles/<meno>.json
```

Formát je rovnaký ako pri profiloch repozitára — **len odchýlky** od Pine defaultov
plus metadáta s podtržníkom: `_instrument` (z neho sa nastaví pár), `_title` a
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

Tlačidlá **Pull** (`git pull --rebase --autostash`) a **Push** (commitne **len**
`runs/` a `profiles/` a pushne na aktuálnu vetvu) sú v hlavičke; výstup gitu sa zobrazí
celý. Kód ani iné súbory sa z UI nikdy necommitujú. Autor commitu je meno testera
z hlavičky.

Výsledkové zipy Freqtradu ostávajú v `backtest_results/` (gitignored) — beh ich
nepotrebuje, všetko podstatné je v `run.json`.

## Príkazový riadok a Claude Code

`python -m ibs.webapp.cli` robí to isté, čo stránka, z terminálu — pre Claude Code
testera a pre skripty. `run` ide cez API bežiacej webapp (beh vidno vo fronte), a keď
webapp nebeží, spustí backtest priamo do toho istého `runs/`. `list`/`show` čítajú
históriu, `pull`/`push` synchronizujú `runs/` a `profiles/`, `status` povie, či webapp beží,
`params` vypíše parametre s rozsahmi.

```bash
python -m ibs.webapp.cli run --profile docs/profily_archiv/btcusdt_3m_binance_ny_sl_risk1.json [--timeframe 5m] \
    --set rrRatio=4 --set minSlDistance=0.25@pct --timerange 20250904-20260904 --note "RR 4"
python -m ibs.webapp.cli list "rrRatio>=4 pnl>0"
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
  (`python -m ibs.tools.data_archive`, docs/RUNNING.md §C).
* Nemá prihlásenie — je na lokálne spustenie (alebo za reverse proxy).
* Nespúšťa hyperopt; na ten sú skripty v `platforms/freqtrade/scripts/`.

## Kód

`ibs/webapp/`: `pine_meta.py` (metadáta z Pine), `store.py` (behy a vyhľadávanie),
`runner.py` (fronta, Freqtrade podproces, spracovanie zipu), `chart.py` (sviečky
z feather súborov po oknách, orezanie kresieb na okno), `gitsync.py`,
`app.py` (FastAPI), `static/` (stránka bez frameworku, Plotly z CDN).
Export kresieb: `ibs/adapters/freqtrade/runner.py::export_chart`, serializácia
`ibs/core/drawing.py::objects_to_dicts`.
Testy: `ibs/tests/test_webapp.py`, `ibs/tests/test_chart_export.py`.
