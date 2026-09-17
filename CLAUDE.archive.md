# CLAUDE.archive.md — podrobné postupy pre režim TESTER

> Presunuté z CLAUDE.md (2026-09-17) kvôli úspore tokenov. Claude ho číta len na požiadanie.

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
  --max-dd 15` — mriežka behov; do histórie ide len jej tabuľka (`tester/sweeps/`), bod sa
  dá prehrať ako beh (`cli replay <id>` alebo klik v tabuľke); kritérium a mantinely
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
- Poplatok bez `--fee` je náklad **toho trhu** (krypto 0,05 % z objemu,
  CFD polovica spreadu v tickoch — `InstrumentSpec.cost`), `--wallet 10000` je default; pri
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
vyšiel na nulu; koľko berie tá burza, závisí od trhu (krypto 0,05 %, CFD spread).
Referenčné hodnoty pre `*_ny_sl` profil sú
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
PY -m tester.webapp.cli push    # commitni LEN runs/, sweeps/, profiles/ a analytics/ a pushni do main
```

To isté robia tlačidlá Pull/Push vo webapp. Push ide vždy do **`main`** (nie na vetvu,
na ktorej klon stojí; iný cieľ cez `TRADEBOT_GIT_BRANCH`) a commituje **výhradne** adresáre
`tester/runs/`, `tester/sweeps/` (tabuľky mriežok), `tester/profiles/` a `tester/analytics/`
(uložené analytiky). Graf behu sa do gitu nedáva — webapp ho dopočíta pri otvorení
(`cli chart <id>`) do lokálnej cache;
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