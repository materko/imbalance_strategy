# Webová aplikácia pre testerov

Lokálna stránka nad Freqtrade backtestom: tester si nastaví parametre stratégie,
vyberie pár a obdobie, spustí beh a po dobehnutí vidí to isté, čo Strategy Tester
v TradingView — štyri karty (Total PnL, Max drawdown, Profitable trades, Profit
factor), graf výnosnosti (kumulatívny PnL, buy and hold, stĺpce za obchod) a zoznam
obchodov. Každý beh sa uloží do gitu, takže história sa dá pushovať a pullovať
medzi testermi a hľadať v nej podľa parametrov.

```powershell
.\platforms\freqtrade\scripts\webapp.ps1        # Windows
```
```bash
./platforms/freqtrade/scripts/webapp.sh         # macOS / Linux
docker compose -f docker/docker-compose.yml run --rm --service-ports webapp   # Docker
```

Otvor http://127.0.0.1:8765. Prvý štart zloží dáta z `data_archive/`, ak chýbajú.

## Nový beh

**Východiskový profil** predvyplní formulár z `ibs/configs/*.json` (odporúčaný
štart je `btcusdt_3m_binance_ny_sl_risk1`) a prepne pár na ten, pre ktorý je profil
určený. „(Pine defaulty)" dá presne to, čo má TradingView bez zásahu do nastavení.

**Parametre** sú všetkých 114 polí `IBSConfig` — 110 Pine vstupov v rovnakých
skupinách, s rovnakými titulkami a tooltipmi ako v TradingView (parsuje sa to
priamo z `imbalance_strategy_FULL.pine`, takže sa nemôžu rozísť), plus skupina
„Rozšírenia portu" (`atrLen`, `legacyPineSizing`, `leverage`, `minSlDistance`).
Zmenené hodnoty oproti profilu sú zvýraznené žlto, každá skupina ukazuje ich počet,
šípka ↺ vráti hodnotu profilu. Filter hľadá v názve, titulku aj tooltipe;
„len zmenené" ukáže iba odchýlky.

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
Kód ani iné súbory sa z UI nikdy necommitujú. Meno testera pri behu je `IBS_USER`,
inak `git config user.name`.

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
