# Audit stratégií na pohľad do budúcnosti (lookahead) — 2026-11-09

Auditovaný commit: `42f37abed` (`main`). Otázka: vidí niektorá stratégia v backteste niečo, čo by naživo
v tom okamihu ešte nevidela? Kontrola má dve časti — automatický test utnutia dát na všetkých stratégiách
v registry (smernica, krok 1b a 1c) a čítanie kódu tam, kam test nedovidí.

## 1. Záver

**Pohľad do budúcnosti sa nenašiel.** Všetky stratégie v registry (Python aj C# prepisy cez most, aj
varianty `…es`, `…mgc`, `…eod`) dali pri utnutých dátach presne ten istý výstup ako pri celých. Feedre
vyššieho TF a vlastné dáta stratégií berú len uzavreté sviečky. Jediné, čo sa dá vytknúť, nie je
pohľad do budúcnosti, ale optimistické plnenie (časť 4).

## 2. Test utnutia dát (`python -m tester.lookahead`)

Ako to funguje: stratégia sa prehrá v emulátore MultiCharts nad oknom a na každom bare sa zapíše, čo
engine povedal brokerovi — vstupy (cena, SL, TP, veľkosť, druh orderu), SL/TP otvorenej pozície
a zatvorenie seansy. Potom sa ten istý beh pustí s dátami utnutými na konci vybraného baru. Utína sa na
šiestich baroch s novým vstupom (1b) a na štyroch náhodných baroch, ktoré väčšinou padnú doprostred
sviečky vyššieho TF (1c). Výstup na všetkých baroch po utnutie musí byť zhodný.

Citlivosť je overená: verzia emulátora, v ktorej bar grafu nesie high/low o päť barov dopredu (ako
`shift(-5)`), sa chytí v každom utnutí (`tester/tests/test_lookahead.py`).

Profil stratégie: výber webapp (`tester/webapp_vyber.json`), inak prvý vlastný profil v `tester/profiles/`,
inak predvolený profil stratégie. Trh a TF sú z profilu.

| okno | stratégií | OK | rozdiel | chyba | utnutí spolu | barov s novým vstupom | čas (súčet) |
|---|---|---|---|---|---|---|---|
| 2. 2. – 16. 3. 2026 | 96 | 96 | 0 | 0 | 908 | 7 539 | 6,4 min |
| 3. 11. 2025 – 2. 3. 2026 | 96 | 96 | 0 | 0 | 940 | 21 252 | 12,6 min |

Trhy z profilov: MNQ, ES, MGC, 6E (Databento), NAS100 a EURUSD (Dukascopy), BTC perpetuál. C# prepisy
(`…net`, `…neteod`) bežali cez most s profilom svojej Python predlohy, tak ako ich púšťa webapp.

Málo signálov aj v štvormesačnom okne (overené hlavne náhodnými utnutiami): `flashorbes` (0), `structure` (1),
`flashorbmgc` (2), `scalp3mamgc` (2). V šesťtýždňovom okne k nim patrili aj `nb`, `orbnet`, `tmrmgc` a `varev`,
ktoré v dlhšom okne signály mali.

## 3. Čo test nevidí — prejdené v kóde

| zdroj | čo stratégia berie | prečo je to v poriadku |
|---|---|---|
| emulátor MultiCharts (`tradebot/adapters/multicharts/emulator.py`) | order zadaný na bare | plní sa až od ďalšieho baru (market na otvorení, limit/stop pri dotyku alebo na otvorení po medzere); SL/TP po 1m sviečkach, pri SL aj TP v jednej minúte SL |
| HTF bary v emulátore | bary informatívneho TF | do feedera idú len tie, ktorých koniec (`open + TF`) je najneskôr koniec baru grafu |
| skladanie TF (`tradebot/core/candles.py`) | `resample_ohlcv` | `label="left", closed="left"` — bar nesie čas otvorenia a len svoje minúty |
| IBS / IBS zóny (`ibs/htf.py`, `ibszones/htf.py`) | okno štyroch HTF barov | `htf_window_opens` počíta z času **zavretia** baru grafu a ide ešte o jeden HTF bar dozadu (Pine `[1]`, `lookahead_off`); platí aj vo Freqtrade ceste, kde feeder dostane celý informatívny DataFrame — vyberá podľa času |
| breakout (`breakout/htf.py`) | posledný uzavretý HTF bar | `floor(zavretie / HTF) × HTF − HTF` — bar, ktorý sa skončil najneskôr so zavretím baru grafu |
| divergence (`divergence/htf.py`) | 1h a 4h skladané z barov grafu | HTF bar sa použije až na prvom bare novej periódy — o bar neskôr, teda opatrne |
| Mag7 (`mag7/data.py`) | 1m dáta akcií Mag7 a SPX z vlastných súborov | index `k` = posledná minúta baru grafu; „bežný pohyb" len z predošlých dní (deň sa pridá do priemeru až po svojom spracovaní) |
| SPRÁVY (`spravy/calendar.py`) | kalendár červených správ USA | len plánované časy vydania (vopred známe), žiadne skutočné hodnoty; noha a vstup z barov po čase správy |
| AI vrstva (`tradebot/adapters/freqtrade/ai.py`) | nálepka TP/SL z budúcich barov | FreqAI utne DataFrame na konci tréningového okna ešte pred `set_freqai_targets`, takže nálepky nesiahajú do testovaného polroka; signál bez výsledku v okne nálepku nedostane |
| Freqtrade runner (`tradebot/adapters/freqtrade/runner.py`) | vlastný model plnenia | `_simulate_fills` beží pred `on_bar`, order z baru sa testuje až na ďalšom; Freqtrade otvára na sviečke po signáli, market na jej otvorení (`custom_entry_price`) |

## 4. Nie pohľad do budúcnosti, ale optimistické plnenie

- **`close_session` sa plní na close rozhodujúceho baru** (`MarketThisBar`). Platí pre koniec seansy aj pre
  výstup v čase (SPRÁVY `rNHold`). MultiCharts to robí rovnako; naživo príde market order o chvíľu neskôr,
  takže pri rýchlom trhu je výstup o sklz horší.
- **Opravy kalendára z profilu** (`newsAdd`, `newsSkip`) sa píšu spätne. Presunutá správa (shutdown) býva
  ohlásená dni vopred, takže to nie je výhoda, len to treba robiť s dátumom ohlásenia, nie podľa grafu.

## 5. Čo ostáva

- Stratégie s málo signálmi v okne (pod tromi) sú overené hlavne náhodnými utnutiami — pri zmene ich logiky
  pustiť test na dlhšom okne (`--from … --to …`).
- Test ide jedným profilom na stratégiu. Profil, ktorý zapína inú vetvu kódu (iný druh vstupu, filter
  vyššieho TF), sa overí `--strategy <kľúč> --profile <profil>`.
- Krok 1a (štart v rôznych dňoch) a 1d (závislosť od predošlých obchodov) test nerobí.
