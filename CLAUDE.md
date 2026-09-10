# Pokyny pre Claude Code v tomto repozitári

Repozitár je TradeBot — rámec pre porty TradingView stratégií do Pythonu (generické jadro
`tradebot/core`, registry stratégií `tradebot/strategies` — dnes „IBS Imbalance Breakout" a
ukážková „Demo Donchian Breakout" —, Freqtrade a MultiCharts adaptéry) plus webová aplikácia
pre testerov (`tester/webapp`). Ako pridať stratégiu: [docs/STRATEGIE.md](docs/STRATEGIE.md).
Pracujú v ňom dva druhy ľudí a pre každého platí iné:

| rola | kto | čo platí |
|---|---|---|
| **tester** | dostal klon, aby spúšťal backtesty a zdieľal výsledky | sekcia **Režim TESTER** nižšie — obmedzenia, presné príkazy |
| **developer** | autor / vývojár, robí čokoľvek: jadro, adaptéry, webapp, merania | sekcia **Režim DEVELOPER** — žiadne obmedzenia, len konvencie |

## Najprv zisti rolu — a spýtaj sa len raz

1. Pozri, či v koreni repozitára existuje súbor **`.ibs-role`** (je v `.gitignore`, každý
   klon má vlastný). Ak obsahuje `tester` alebo `developer`, tou rolou sa riaď a **nepýtaj sa**.
2. Ak súbor chýba, na začiatku prvej odpovede sa **spýtaj**: „Pracujeme ako **tester**
   (backtesty, história, aktualizácie — bez zásahov do kódu) alebo ako **developer**
   (čokoľvek)?" Odpoveď zapíš do `.ibs-role` (len to jedno slovo), aby sa to nepýtalo znova.
3. Rolu si môže používateľ kedykoľvek zmeniť („prepni na developer") — prepíš súbor.
4. Inštalátor `install-macos.sh` zapisuje `tester` sám, takže nainštalovaní testeri
   otázku nikdy nevidia.

Ak si neistý a používateľ hovorí o zmene kódu, testov, dokumentov alebo meraní, je to
developer. Ak hovorí o spúšťaní behov, parametroch, histórii a aktualizácii aplikácie,
je to tester.

---

# Režim DEVELOPER

Bez obmedzení. Platia len konvencie repozitára:

- Zmeny jadra musia prejsť `pytest` vrátane golden testov proti TradingView
  (`tester/tests/test_golden_tv_binance.py`). Rozšírenia mimo Pine majú default zhodný
  s Pine a sú v `PORT_ONLY_FIELDS` configu stratégie (`tradebot/strategies/<key>/config.py`).
- Nová stratégia = balík `tradebot/strategies/<key>/` + riadok v registry; celý postup,
  kontrakt enginu a definícia hotového sú v [docs/STRATEGIE.md](docs/STRATEGIE.md).
  Jadro a adaptéry nesmú poznať konkrétnu stratégiu menom — všetko ide cez `StrategySpec`.
  Stratégia sa píše **pre oba enginy naraz** (Freqtrade aj MultiCharts) a hotová je až
  so **základnou analytikou a posudkom**: `python -m tester.webapp.cli checkup --strategy
  <key> …` vyrobí `tradebot/strategies/<key>/docs/ANALYTIKA.md` (päť okien, charakter,
  skupiny obchodov, test proti náhode, Monte Carlo) a posudok od AI do nej dopíše AI —
  šesť otázok v tom dokumente ([docs/ANALYTIKA.md](docs/ANALYTIKA.md)).
- Backtest vždy s `--timeframe-detail 1m` a `--cache none` (skripty to robia samy);
  stratégiu nespúšťať priamo na 1m grafe (limity `*MaxBars` sú v baroch).
- Merania sa zapisujú ako datované dokumenty v `docs/merania/` s číslami **po rokoch** na piatich
  referenčných oknách (`20211001-20221001`, `20221001-20231001`, `20231001-20241001`,
  `20240904-20250904`, `20250904-20260904`); kľúčová metrika je break-even poplatok.
- Sťahujú a commitujú sa len oficiálne timeframy búrz (po rokoch v `data_archive/tester/`);
  zvyšok podľa [`tester/timeframes.json`](tester/timeframes.json) dopočíta `tester.timeframes`
  z 1m pri štarte webapp a čo aj tak chýba, si poskladá stratégia sama
  (`TradebotStrategyBase.ensure_timeframe`, len v backteste/hyperopte) — nič stiahnuté sa
  neprepíše a dopočítané do archívu nejde.
  Freqtrade beží len na TF, ktoré pozná jeho burza (2m a 4m sú preto len pre emulátor).
  Surový export spracuje importér zdroja — dnes `tester.dukas_import`
  (obal `./dukas-import.sh`, `.\dukas-import.ps1`): vyčistí, spraví feather v TF zdroja
  a rozdelí po rokoch do archívu; nič iné. ASCII pre QuoteManager robí `tester.quotemanager`
  zo skladu sviečok. Celá cesta dát: [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md),
  podrobne [docs/DATA.md](docs/DATA.md).
- Cesty v repozitári sú na jednom mieste v `tradebot/core/paths.py`; nikde inde sa nepíšu.
- Vyšší TF sa z 1m skladá výhradne cez `tradebot/core/candles.py` (webapp graf, simulátor,
  emulátor, súbory pre Freqtrade) — keby sa pravidlo rozišlo, porovnanie platforiem prestane
  niečo znamenať. Freqtrade si TF sám nedopočíta, pre `--timeframe` chce súbor na disku.
- Commity v štýle histórie: slovenská veta v imperatíve, čo a prečo.
- Backtesty, ktoré majú byť v histórii webapp, spúšťaj cez `python -m tester.webapp.cli run`
  (holý Freqtrade CLI ich do `runs/` nezapíše) — inak je to jedno.

Podrobnosti: [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) (prehľad a cesta dát),
[docs/ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md) (návrh),
[docs/FREQTRADE.md](docs/FREQTRADE.md) (krypto vetva), [docs/MULTICHARTS.md](docs/MULTICHARTS.md)
(MultiCharts vetva), [docs/HYPEROPT.md](docs/HYPEROPT.md) (hľadanie parametrov, FreqAI),
[docs/TYPY_STRATEGII.md](docs/TYPY_STRATEGII.md) (charakter stratégie a čo z neho vyplýva),
[docs/ANALYTIKA.md](docs/ANALYTIKA.md) (základná analytika stratégie a posudok),
[docs/DATA.md](docs/DATA.md) (dáta), [docs/WEBAPP.md](docs/WEBAPP.md)
(Tester), [docs/RUNNING.md](docs/RUNNING.md) (rozcestník), [README.md](README.md).

---

# Režim TESTER

Používateľ chce spúšťať backtesty, pozerať históriu, aktualizovať aplikáciu a zdieľať
výsledky cez GitHub. Podrobnosti: [docs/WEBAPP.md](docs/WEBAPP.md).

## Zlaté pravidlá

0. Stratégia sa volí prepínačom `--strategy <kľúč>` (default `ibs`; zoznam v
   [docs/STRATEGIE.md](docs/STRATEGIE.md)); profil musí patriť tej istej stratégii.
   Engine sa volí `--engine freqtrade|multicharts` (bez neho podľa toho, pre ktorý sú
   dáta), burza pre Freqtrade beh `--exchange tester|binance|…` (predvolená je fiktívna
   `tester`, ktorá pozná všetky naše timeframy). Signály sú v oboch rovnaké, fill model nie — závery pre MultiCharts patria
   emulátoru. Celý postup testovania: [tester/AI_TESTING.md](tester/AI_TESTING.md).
1. **Backtesty spúšťaj len cez `python -m tester.webapp.cli run …`** (alebo cez webapp
   v prehliadači). Holý `freqtrade backtesting` výsledok do histórie webapp **nezapíše**
   a tester ho neuvidí.
2. **Vždy `--timeframe-detail 1m`** — CLI aj webapp ho majú zapnutý, nevypínaj ho
   (`--no-detail` len na rýchly hrubý odhad, do záverov nie). Stratégiu nikdy nespúšťaj
   na 1m grafe: limity `*MaxBars` sú v baroch.
3. **Ku každému behu napíš `--note`**, čo testuje. Bez poznámky je história na nič.
4. **Testerov klon nie je vývojová vetva.** Neupravuj `tradebot/core`, adaptéry ani profily
   v `tradebot/strategies/<stratégia>/configs`, pokiaľ ťa o to výslovne nepožiadajú. Parametre sa menia cez `--set`
   alebo vo formulári, nie v kóde. Do gitu idú len dáta testera: história behov (`tester/runs/`)
   a vlastné profily (`tester/profiles/`). Vlastný profil si tester uloží tlačidlom
   **Uložiť ako profil** — z formulára (aj so zvoleným TF) alebo z detailu behu; tam sa
   dá aj premenovať a zmazať. Profily repozitára v `tradebot/strategies/<stratégia>/configs/` sa nemenia.
5. Jeden backtest naraz. Rok s 1m detailom trvá ~20–40 s; päť rokov ~3 minúty.
6. Nesťahuj dáta z burzy. Páry a obdobia sú len tie, čo sú v `data_archive/tester/`:
   futures perpetuály `BTC/USDT:USDT`, `ETH/USDT:USDT` (v ponuke `BTCUSDT.P`,
   `ETHUSDT.P`) a spot `BTC/USDT`, `ETH/USDT` (`BTCUSDT`, `ETHUSDT`), 2019–2026,
   a „burza" **MultiCharts** s Dukascopy CFD `NAS100/USD` (v ponuke `NAS100`), 2021–2026 —
   beh na nej ide cez emulátor MultiCharts, nie cez Freqtrade, profil `nas100_dukas_3m`
   z `docs/profily_archiv/ibs/`. Na spote sú len longy a páka 1 — webapp aj CLI beh
   s shortmi či pákou odmietnu.
7. Profil musí sedieť s párom: pre ETH použi `ethusdt_*` profil z `docs/profily_archiv/`.
   BTC profil na ETH dá stovky nezmyselných obchodov (prahy v bodoch nesedia) — webapp aj
   CLI na to varujú. V `tradebot/strategies/ibs/configs/` sú len tri referenčné profily (golden testy proti
   TradingView, MultiCharts); skúšané konfigurácie sú v `docs/profily_archiv/` a `--profile`
   berie aj cestu k súboru.
8. **„Len mi nastav parametre" znamená naozaj len nastaviť.** Keď má tester otvorenú
   webapp a povie, že chce iba nastaviť parametre, vyplň na karte **Nový beh** presne tie
   polia, ktoré vymenoval, a **nič nespúšťaj** — tlačidlo „▶ Spustiť backtest" nechaj
   nedotknuté. Podrobnosti nižšie.

## Python a cesty

Všetko sa spúšťa z **koreňa repozitára** Pythonom z `.venv`:

| | macOS / Linux | Windows |
|---|---|---|
| Python | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| Webapp | `./webapp.sh` | `.\webapp.ps1` alebo `webapp.cmd` |
| Setup (ak `.venv` chýba) | `deploy/freqtrade/scripts/setup.sh` | `deploy\freqtrade\scripts\setup.ps1` |

Nižšie píšem `PY` = ten Python. Ak `.venv` neexistuje, najprv spusti setup (~10 min).

## Backtest, ktorý sa objaví v histórii

```bash
PY -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --note "základ, rok 2025-26"

PY -m tester.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --set rrRatio=4 --set minSlDistance=0.25@pct \
   --timerange 20250904-20260904 --note "RR 4, SL filter 0,25 %"

PY -m tester.webapp.cli run --profile docs/profily_archiv/ibs/ethusdt_3m_binance_ny_sl_risk1.json --pair ETH/USDT:USDT \
   --timerange 20240904-20250904 --note "ETH kontrola"
```

- Ak webapp beží, beh ide do jej fronty a tester ho vidí v prehliadači naživo; CLI
  počká na výsledok a vypíše súhrn. Ak nebeží, CLI spustí backtest priamo a uloží ho
  do toho istého `tester/runs/` — história je rovnaká.
- Vždy zopakuj **päť referenčných okien**, keď hodnotíš zmenu parametra — jeden rok
  o stratégii nič nepovie: `20211001-20221001`, `20221001-20231001`, `20231001-20241001`,
  `20240904-20250904`, `20250904-20260904`.
- `--set` hodnoty: `true/false`, čísla, text; veľkostné polia `hodnota@jednotka`
  (`abs`, `ticks`, `atr`, `pct`). Zoznam parametrov: `PY -m tester.webapp.cli params [filter]`.
- Hľadanie parametra: `PY -m tester.webapp.cli sweep --param rrRatio=2:6:1 --goal break_even
  --max-dd 15` — mriežka obyčajných behov, každý ostane v histórii; kritérium a mantinely
  určujú, čo je „najlepšie". Mriežka nemá strop, pokojne beží cez noc, a `cli sweeps`
  (alebo ponuka **Predošlá mriežka** vo webapp) sa k nej vráti
  ([tester/AI_TESTING.md §7](tester/AI_TESTING.md)).
- Od troch parametrov `cli hyperopt --param rrRatio=2:8:0.5 …` (alebo `--suggested`): to
  isté zadanie, ale hľadá sa v rozsahu a víťaz sa sám preverí na piatich referenčných
  oknách — [docs/HYPEROPT.md](docs/HYPEROPT.md).
- Drží myšlienka aj mimo trhu, na ktorom sa ladila? `cli matrix --pairs all --timeframes 3m`
  (prahy sa prepočítajú na `atr`, inak by tabuľka klamala).
- Je ten edge odlíšiteľný od náhody? `cli nulltest "pair=BTC/USDT:USDT"` — tá istá
  stratégia s náhodnými vstupmi ako referenčný bod
  ([tester/AI_TESTING.md §8c](tester/AI_TESTING.md)).
- Koľko sa dá zarobiť a za aký drawdown? `cli portfolio --runs <id>,<id>,…` — vybrané behy
  ako jeden účet, tabuľka rizika a korelácie medzi členmi (§8d).
- Poplatok `--fee 0.0005` (Binance taker 0,05 %) a `--wallet 10000` sú default; pri
  porovnávaní s TradingView použi `--fee 0` a profil `*_ny_sl` (1 BTC)
  z `docs/profily_archiv/`. Peňaženka musí byť **rovná initial capital z grafu**
  (`--wallet 10000`), inak sedí PnL v mene, ale nie v percentách — TradingView ich počíta
  z počiatočného kapitálu. A páka musí stačiť na najväčšiu pozíciu, lebo Freqtrade na
  rozdiel od TradingView margin stráži a pozíciu oreže
  ([docs/merania/PARITA_pnl_tradingview_2026-09-08.md](docs/merania/PARITA_pnl_tradingview_2026-09-08.md)).

## Len nastaviť parametre vo webapp (bez spustenia)

Keď tester povie niečo ako „nastav mi rrRatio na 4 a SL filter na 0,25 %", „priprav mi
beh", „len to navoľ, spustím si to sám" — je to **nastavenie formulára, nie beh**:

1. Pracuj v prehliadači na karte **Nový beh** v otvorenej webapp (`http://127.0.0.1:8765`).
   Ak nebeží, spusti ju (viď nižšie) — ale beh ani vtedy nespúšťaj cez CLI.
2. Nastav **len tie polia, ktoré tester vymenoval**. Ostatné — profil, pár, timerange,
   poplatok, peňaženku, poznámku — nechaj tak, ako sú. Nič „pre istotu" nedopĺňaj
   a nevracaj na default.
3. **Neklikaj na „▶ Spustiť backtest".** Ani keď je formulár kompletný, ani keď sa zdá,
   že to tester chce — spustenie si vypýta výslovne („spusti to", „pusti backtest").
4. Nakoniec vypíš, čo si nastavil (pole → hodnota), a upozorni na polia, ktoré si nechal
   nezmenené a mohli by prekvapiť (napr. stará poznámka alebo iný timerange z minula).
5. Ak niektorý parameter vo formulári nie je alebo hodnota nesedí do rozsahu, nehádaj —
   povedz to a ukáž `PY -m tester.webapp.cli params <filter>`.

Ak tester chce parametre pripraviť **bez webapp**, nespúšťaj `run` — len mu poskladaj
príkaz s `--set` a nechaj ho naň kliknúť.

## Čítanie výsledkov

```bash
PY -m tester.webapp.cli list                       # posledné behy
PY -m tester.webapp.cli list "rrRatio>=4 pnl>0"    # rovnaká syntax ako vyhľadávanie vo webapp
PY -m tester.webapp.cli show <run_id> [--json]
```

Kľúčové číslo je **break-even poplatok** (% na stranu): koľko smie burza brať, aby beh
vyšiel na nulu. Binance taker berie 0,05 %. Referenčné hodnoty pre `*_ny_sl` profil sú
v README („Kde sme s výsledkami"). PnL v % závisí od sizingu a peňaženky, break-even nie.
Pri záveroch pozeraj **znamienko po rokoch**, nie súčet.

## Webapp: spustiť, overiť, reštartovať, zastaviť

```bash
PY -m tester.webapp.cli status              # beží? čo je vo fronte? stav gitu
```

**Spustenie na pozadí** (aby si mohol ďalej pracovať v tom istom termináli):

```bash
# macOS / Linux
nohup ./webapp.sh > /tmp/ibs-webapp.log 2>&1 &
# Windows PowerShell
Start-Process -FilePath .\webapp.cmd -WindowStyle Minimized
```

**Zastavenie / reštart** (aplikácia počúva na porte 8765):

```bash
# macOS / Linux
lsof -ti :8765 | xargs kill            # potom znova nohup ./webapp.sh …
```
```powershell
# Windows
Get-NetTCPConnection -LocalPort 8765 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

Reštart je potrebný po `git pull`, ktorý zmenil kód (`tradebot/`), a po zmene `.venv`.
Zmeny v `runs/` reštart nepotrebujú — história sa číta zo súborov pri každom dopyte.

Iný port: `TRADEBOT_WEB_PORT=9000 ./webapp.sh` (a potom `--url http://127.0.0.1:9000` v CLI).

## Aktualizácia na najnovšiu verziu

```bash
PY -m tester.webapp.cli push          # najprv odlož vlastné behy (viď nižšie)
git pull --rebase --autostash      # v koreni repozitára
PY -m tester.data_archive merge # ak pull priniesol nové dáta v data_archive/tester/
PY -m pytest -q                    # voliteľné: overenie (~30 s, 300+ testov)
```

Potom reštartuj webapp. Ak pull zmenil `pyproject.toml` alebo hlási chýbajúci balík,
spusti znova setup skript (nainštaluje, čo treba, `.venv` zachová). Na macOS sa dá
celá aktualizácia spraviť aj opätovným spustením inštalátora:
`curl -fsSL https://raw.githubusercontent.com/materko/imbalance_strategy/main/install-macos.sh | bash`.

## História behov cez GitHub

```bash
PY -m tester.webapp.cli pull    # stiahni behy ostatných (git pull --rebase --autostash)
PY -m tester.webapp.cli push    # commitni LEN runs/ a profiles/ a pushni na aktuálnu vetvu
```

To isté robia tlačidlá Pull/Push vo webapp. Push ide vždy do **`main`** (nie na vetvu,
na ktorej klon stojí; iný cieľ cez `TRADEBOT_GIT_BRANCH`) a commituje **výhradne** adresáre
`tester/runs/` a `tester/profiles/`,
autor je meno testera (`TRADEBOT_USER` alebo `git config user.name`). Každý beh je nový
adresár, konflikty prakticky nevznikajú.
Ak push zlyhá na „rejected", sprav pull a push znova. Ak zlyhá na „could not read
Username" alebo „Authentication failed", GitHub nemá uložené prihlásenie — `gh auth
login && gh auth setup-git` (macOS/Linux), prípadne credential helper podľa systému;
webapp návod vypíše sama. Commit ostáva lokálne, takže po prihlásení stačí Push znova. Ak tester zmenil kód a chce
ho poslať, to už nie je história behov — povedz mu, nech to rieši s autorom repozitára
(pull request), a **necommituj kód** za neho.

## Testy kódu (nie backtesty)

```bash
PY -m pytest -q                                  # všetko, ~30 s
PY -m pytest tester/tests/test_golden_tv_binance.py # parita s TradingView
```

Spúšťaj ich po `git pull`, alebo keď niečo padá a nevieš prečo. Ak padnú golden
testy, kód alebo dáta nesedia s referenciou — neopravuj to u testera, nahlás to.

## Keď niečo nefunguje

- `Permission denied` na `.sh`: `bash ./webapp.sh` (alebo `chmod +x *.sh deploy/freqtrade/scripts/*.sh`).
- „chýbajú dáta" / prázdny zoznam párov: `PY -m tester.data_archive merge`.
- Webapp odmietne beh s „Neplatný config": hodnota mimo Pine rozsahu — `params` ukáže rozsahy.
- Beh skončil `failed`: `PY -m tester.webapp.cli show <id>` vypíše chybu, log je v
  `runs/<id>/log.txt`.
- Port 8765 obsadený: stará inštancia beží — zastav ju (vyššie) alebo použi iný port.
- macOS `ta-lib`/`freqtrade` pri inštalácii: `brew install ta-lib`, potom setup znova.
- Tester chce niečo, čo tieto pravidlá zakazujú (zmenu kódu, sťahovanie dát): povedz mu,
  že je to vývojárska práca, a že rolu môže prepnúť („prepni na developer") — ale
  upozorni, že zmeny kódu z testerského klonu nepatria do histórie behov.
