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

**Windows** (PowerShell):
```powershell
git clone https://github.com/materko/imbalance_strategy.git
cd imbalance_strategy
.\platforms\freqtrade\scripts\webapp.ps1
```
Ak PowerShell odmietne spustiť skript, raz povoľ: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**macOS / Linux**:
```bash
brew install ta-lib            # len macOS, raz
git clone https://github.com/materko/imbalance_strategy.git
cd imbalance_strategy
./platforms/freqtrade/scripts/webapp.sh
```

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

**Východiskový profil** predvyplní formulár z `ibs/configs/*.json` (odporúčaný
štart je `btcusdt_3m_binance_ny_sl_risk1`) a prepne pár na ten, pre ktorý je profil
určený. „(Pine defaulty)" dá presne to, čo má TradingView bez zásahu do nastavení.

**Parametre** sú všetkých 114 polí `IBSConfig` — 110 Pine vstupov v rovnakých
skupinách, s rovnakými titulkami a tooltipmi ako v TradingView (parsuje sa to
priamo z `imbalance_strategy_FULL.pine`, takže sa nemôžu rozísť), plus skupina
„Rozšírenia portu" (`atrLen`, `legacyPineSizing`, `leverage`, `minSlDistance`).
Panel vyzerá ako nastavenia v TradingView: vľavo zoznam skupín, vpravo aktívna skupina,
jeden parameter na riadok; polia, ktoré Pine kreslí vedľa seba (hodina a minúta seansy,
zapnutie a časové pásmo), sú vedľa seba aj tu. Tooltip z Pine, identifikátor a rozsah
sa ukážu po podržaní myši na názve. Zmenené hodnoty oproti profilu sú žlté, skupina
ukazuje ich počet, ↺ vráti hodnotu profilu. Hľadanie prechádza všetky skupiny naraz
(názov, popis, identifikátor); „len zmenené" ukáže iba odchýlky.

Polia s veľkosťou (`*Points`, `*Ticks`, `minSlDistance`) majú jednotku:
`abs` cenové body, `ticks` násobky ticku, `atr` násobky ATR grafového TF,
`pct` percento ceny. Holá hodnota v profile znamená pôvodnú Pine jednotku.

**Nastavenia behu**: pár (len tie, ktoré majú stiahnuté dáta — BTC a ETH), obdobie
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

Pod tým odchýlky od Pine defaultov (s Pine hodnotou vedľa), dôvody výstupu, zoznam
obchodov, všetky parametre a skrátený log Freqtradu.

**Načítať do formulára** vráti parametre aj nastavenia behu do formulára — na
úpravu jedného parametra a nový beh. **Stiahnuť profil** dá JSON použiteľný
priamo cez `IBS_PROFILE=cesta.json` v CLI. **Zmazať** odstráni adresár behu.

## Kde história žije a ako sa zdieľa

```
platforms/freqtrade/user_data/runs/<YYYYMMDD-HHMMSS-odtlačok>/
    run.json      parametre, nastavenia, výsledok (súhrn), séria pre graf
    trades.json   obchody
    log.txt       skrátený log
```

Všetko je čitateľný JSON, jeden adresár na beh, takže sa to mergeuje bez konfliktov.
Tlačidlá **Pull** (`git pull --rebase --autostash`) a **Push** (commitne **len**
`runs/` a pushne na aktuálnu vetvu) sú v hlavičke; výstup gitu sa zobrazí celý.
Kód ani iné súbory sa z UI nikdy necommitujú. Autor commitu je meno testera z hlavičky.

Výsledkové zipy Freqtradu ostávajú v `backtest_results/` (gitignored) — beh ich
nepotrebuje, všetko podstatné je v `run.json`.

## Čo aplikácia nerobí

* Nesťahuje dáta — páry a obdobia sú len tie, čo sú v archíve
  (`python -m ibs.tools.data_archive`, docs/RUNNING.md §C).
* Nemá prihlásenie — je na lokálne spustenie (alebo za reverse proxy).
* Nespúšťa hyperopt; na ten sú skripty v `platforms/freqtrade/scripts/`.

## Kód

`ibs/webapp/`: `pine_meta.py` (metadáta z Pine), `store.py` (behy a vyhľadávanie),
`runner.py` (fronta, Freqtrade podproces, spracovanie zipu), `gitsync.py`,
`app.py` (FastAPI), `static/` (stránka bez frameworku, Plotly z CDN).
Testy: `ibs/tests/test_webapp.py`.
