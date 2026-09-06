# Pokyny pre Claude Code v tomto repozitári

Repozitár je port TradingView stratégie „IBS Imbalance Breakout" do Pythonu (jadro
`tradebot/core`, Freqtrade adaptér) plus webová aplikácia pre testerov (`tradebot/webapp`).
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
  (`tradebot/tests/test_golden_tv_binance.py`). Rozšírenia mimo Pine majú default zhodný
  s Pine a sú v `PORT_ONLY_FIELDS` (`tradebot/core/config.py`).
- Backtest vždy s `--timeframe-detail 1m` a `--cache none` (skripty to robia samy);
  stratégiu nespúšťať priamo na 1m grafe (limity `*MaxBars` sú v baroch).
- Merania sa zapisujú ako datované dokumenty v `docs/` s číslami **po rokoch** na piatich
  referenčných oknách (`20211001-20221001`, `20221001-20231001`, `20231001-20241001`,
  `20240904-20250904`, `20250904-20260904`); kľúčová metrika je break-even poplatok.
- Dáta len v oficiálnych timeframoch búrz, commitované po rokoch v `data_archive/`.
- Commity v štýle histórie: slovenská veta v imperatíve, čo a prečo.
- Backtesty, ktoré majú byť v histórii webapp, spúšťaj cez `python -m tradebot.webapp.cli run`
  (holý Freqtrade CLI ich do `runs/` nezapíše) — inak je to jedno.

Podrobnosti: [docs/ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md),
[docs/RUNNING.md](docs/RUNNING.md), [docs/WEBAPP.md](docs/WEBAPP.md), [README.md](README.md).

---

# Režim TESTER

Používateľ chce spúšťať backtesty, pozerať históriu, aktualizovať aplikáciu a zdieľať
výsledky cez GitHub. Podrobnosti: [docs/WEBAPP.md](docs/WEBAPP.md).

## Zlaté pravidlá

1. **Backtesty spúšťaj len cez `python -m tradebot.webapp.cli run …`** (alebo cez webapp
   v prehliadači). Holý `freqtrade backtesting` výsledok do histórie webapp **nezapíše**
   a tester ho neuvidí.
2. **Vždy `--timeframe-detail 1m`** — CLI aj webapp ho majú zapnutý, nevypínaj ho
   (`--no-detail` len na rýchly hrubý odhad, do záverov nie). Stratégiu nikdy nespúšťaj
   na 1m grafe: limity `*MaxBars` sú v baroch.
3. **Ku každému behu napíš `--note`**, čo testuje. Bez poznámky je história na nič.
4. **Testerov klon nie je vývojová vetva.** Neupravuj `tradebot/core`, adaptéry ani profily
   v `tradebot/configs/ibs`, pokiaľ ťa o to výslovne nepožiadajú. Parametre sa menia cez `--set`
   alebo vo formulári, nie v kóde. Do gitu ide len história behov (`runs/`).
5. Jeden backtest naraz. Rok s 1m detailom trvá ~20–40 s; päť rokov ~3 minúty.
6. Nesťahuj dáta z burzy. Páry a obdobia sú len tie, čo sú v `data_archive/`
   (BTC/USDT:USDT a ETH/USDT:USDT, 2019–2026).
7. Profil musí sedieť s párom: pre ETH použi `ethusdt_*` profil z `docs/profily_archiv/`.
   BTC profil na ETH dá stovky nezmyselných obchodov (prahy v bodoch nesedia) — webapp aj
   CLI na to varujú. V `tradebot/configs/ibs/` sú len tri referenčné profily (golden testy proti
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
| Setup (ak `.venv` chýba) | `platforms/freqtrade/scripts/setup.sh` | `platforms\freqtrade\scripts\setup.ps1` |

Nižšie píšem `PY` = ten Python. Ak `.venv` neexistuje, najprv spusti setup (~10 min).

## Backtest, ktorý sa objaví v histórii

```bash
PY -m tradebot.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --note "základ, rok 2025-26"

PY -m tradebot.webapp.cli run --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --set rrRatio=4 --set minSlDistance=0.25@pct \
   --timerange 20250904-20260904 --note "RR 4, SL filter 0,25 %"

PY -m tradebot.webapp.cli run --profile docs/profily_archiv/ibs/ethusdt_3m_binance_ny_sl_risk1.json --pair ETH/USDT:USDT \
   --timerange 20240904-20250904 --note "ETH kontrola"
```

- Ak webapp beží, beh ide do jej fronty a tester ho vidí v prehliadači naživo; CLI
  počká na výsledok a vypíše súhrn. Ak nebeží, CLI spustí backtest priamo a uloží ho
  do toho istého `platforms/freqtrade/user_data/runs/` — história je rovnaká.
- Vždy zopakuj **päť referenčných okien**, keď hodnotíš zmenu parametra — jeden rok
  o stratégii nič nepovie: `20211001-20221001`, `20221001-20231001`, `20231001-20241001`,
  `20240904-20250904`, `20250904-20260904`.
- `--set` hodnoty: `true/false`, čísla, text; veľkostné polia `hodnota@jednotka`
  (`abs`, `ticks`, `atr`, `pct`). Zoznam parametrov: `PY -m tradebot.webapp.cli params [filter]`.
- Poplatok `--fee 0.0005` (Binance taker 0,05 %) a `--wallet 10000` sú default; pri
  porovnávaní s TradingView použi `--fee 0 --wallet 400000` a profil `*_ny_sl` (1 BTC)
  z `docs/profily_archiv/`.

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
   povedz to a ukáž `PY -m tradebot.webapp.cli params <filter>`.

Ak tester chce parametre pripraviť **bez webapp**, nespúšťaj `run` — len mu poskladaj
príkaz s `--set` a nechaj ho naň kliknúť.

## Čítanie výsledkov

```bash
PY -m tradebot.webapp.cli list                       # posledné behy
PY -m tradebot.webapp.cli list "rrRatio>=4 pnl>0"    # rovnaká syntax ako vyhľadávanie vo webapp
PY -m tradebot.webapp.cli show <run_id> [--json]
```

Kľúčové číslo je **break-even poplatok** (% na stranu): koľko smie burza brať, aby beh
vyšiel na nulu. Binance taker berie 0,05 %. Referenčné hodnoty pre `*_ny_sl` profil sú
v README („Kde sme s výsledkami"). PnL v % závisí od sizingu a peňaženky, break-even nie.
Pri záveroch pozeraj **znamienko po rokoch**, nie súčet.

## Webapp: spustiť, overiť, reštartovať, zastaviť

```bash
PY -m tradebot.webapp.cli status              # beží? čo je vo fronte? stav gitu
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
PY -m tradebot.webapp.cli push          # najprv odlož vlastné behy (viď nižšie)
git pull --rebase --autostash      # v koreni repozitára
PY -m tradebot.tools.data_archive merge # ak pull priniesol nové dáta v data_archive/
PY -m pytest -q                    # voliteľné: overenie (~30 s, 300+ testov)
```

Potom reštartuj webapp. Ak pull zmenil `pyproject.toml` alebo hlási chýbajúci balík,
spusti znova setup skript (nainštaluje, čo treba, `.venv` zachová). Na macOS sa dá
celá aktualizácia spraviť aj opätovným spustením inštalátora:
`curl -fsSL https://raw.githubusercontent.com/materko/imbalance_strategy/main/install-macos.sh | bash`.

## História behov cez GitHub

```bash
PY -m tradebot.webapp.cli pull    # stiahni behy ostatných (git pull --rebase --autostash)
PY -m tradebot.webapp.cli push    # commitni LEN runs/ a pushni na aktuálnu vetvu
```

To isté robia tlačidlá Pull/Push vo webapp. Push commituje **výhradne** adresár
`platforms/freqtrade/user_data/runs/`, autor je meno testera (`TRADEBOT_USER` alebo
`git config user.name`). Každý beh je nový adresár, konflikty prakticky nevznikajú.
Ak push zlyhá na „rejected", sprav pull a push znova. Ak tester zmenil kód a chce
ho poslať, to už nie je história behov — povedz mu, nech to rieši s autorom repozitára
(pull request), a **necommituj kód** za neho.

## Testy kódu (nie backtesty)

```bash
PY -m pytest -q                                  # všetko, ~30 s
PY -m pytest tradebot/tests/test_golden_tv_binance.py # parita s TradingView
```

Spúšťaj ich po `git pull`, alebo keď niečo padá a nevieš prečo. Ak padnú golden
testy, kód alebo dáta nesedia s referenciou — neopravuj to u testera, nahlás to.

## Keď niečo nefunguje

- `Permission denied` na `.sh`: `bash ./webapp.sh` (alebo `chmod +x *.sh platforms/freqtrade/scripts/*.sh`).
- „chýbajú dáta" / prázdny zoznam párov: `PY -m tradebot.tools.data_archive merge`.
- Webapp odmietne beh s „Neplatný config": hodnota mimo Pine rozsahu — `params` ukáže rozsahy.
- Beh skončil `failed`: `PY -m tradebot.webapp.cli show <id>` vypíše chybu, log je v
  `runs/<id>/log.txt`.
- Port 8765 obsadený: stará inštancia beží — zastav ju (vyššie) alebo použi iný port.
- macOS `ta-lib`/`freqtrade` pri inštalácii: `brew install ta-lib`, potom setup znova.
- Tester chce niečo, čo tieto pravidlá zakazujú (zmenu kódu, sťahovanie dát): povedz mu,
  že je to vývojárska práca, a že rolu môže prepnúť („prepni na developer") — ale
  upozorni, že zmeny kódu z testerského klonu nepatria do histórie behov.
