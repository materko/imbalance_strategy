# Pokyny pre Claude Code v tomto repozitári

Repozitár je TradeBot — rámec pre porty TradingView stratégií do Pythonu (generické jadro
`tradebot/core`, registry stratégií `tradebot/strategies` — dnes „IBS Imbalance Breakout",
„Market Structure BOS / CHoCH" a ukážková „Demo Donchian Breakout" —, Freqtrade
a MultiCharts adaptéry; „IBSNet" a „ORBNet" sú IBS a ORB s jadrom v C# (.NET, `csharp/`), ktoré spúšťajú
NinjaTrader 8, MetaTrader 5 (`tradebot/adapters/mt5`) aj Freqtrade cez most `tradebot/adapters/csharp`) plus webová aplikácia
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
  Popisy parametrov pre formulár sú v `params.py` pri stratégii; **Pine zdroj sa robí
  len na vyžiadanie** a formulár na ňom nezávisí.
  Jadro a adaptéry nesmú poznať konkrétnu stratégiu menom — všetko ide cez `StrategySpec`.
  Stratégia sa píše **pre oba enginy naraz** (Freqtrade aj MultiCharts) a hotová je až
  so **základnou analytikou a posudkom**: `python -m tester.webapp.cli checkup --strategy
  <key> …` vyrobí `tradebot/strategies/<key>/docs/ANALYTIKA.md` (päť okien, charakter,
  skupiny obchodov, test proti náhode, slabnúci edge, Monte Carlo) a posudok dopíše AI —
  šesť otázok v tom dokumente ([docs/ANALYTIKA.md](docs/ANALYTIKA.md)).
- Backtest vždy s `--timeframe-detail 1m` a `--cache none` (skripty to robia samy);
  stratégiu nespúšťať priamo na 1m grafe (limity `*MaxBars` sú v baroch).
- Merania sa zapisujú ako datované dokumenty v `docs/merania/` (`python -m tester.webapp.cli paper`
  ich napíše z behov v histórii; záver dopisuje človek) s číslami **po rokoch** na piatich
  referenčných oknách (`20211001-20221001`, `20221001-20231001`, `20231001-20241001`,
  `20240904-20250904`, `20250904-20260904`); kľúčová metrika je break-even poplatok.
- Sťahujú a commitujú sa len oficiálne timeframy búrz (po rokoch v `data_archive/tester/`);
  zvyšok podľa [`tester/timeframes.json`](tester/timeframes.json) dopočíta `tester.timeframes`
  z 1m pri štarte webapp a čo aj tak chýba, si poskladá stratégia sama
  (`TradebotStrategyBase.ensure_timeframe`, len v backteste/hyperopte) — nič stiahnuté sa
  neprepíše a dopočítané do archívu nejde.
  Freqtrade beží len na TF, ktoré pozná jeho burza (2m a 4m sú preto len pre emulátor).
  Surový export spracuje importér zdroja — `tester.dukas_import` pre Dukascopy CFD
  (obal `./dukas-import.sh`, `.\dukas-import.ps1`) a `tester.bento_import` pre Databento
  CME futures (`./bento-import.sh`; kontrakty → front-month podľa objemu, bez
  back-adjustmentu): vyčistí, spraví feather v TF zdroja a rozdelí po rokoch do archívu;
  nič iné. ASCII pre QuoteManager robí `tester.quotemanager`
  zo skladu sviečok. Celá cesta dát: [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md),
  podrobne [docs/DATA.md](docs/DATA.md).
- Stratégia s jadrom v C# (`csharp/TradeBot.Strategies/<Meno>`, dnes `ibsnet`, `orbnet`): C# 5 bez NuGet
  (prekladá ho `csc.exe` z .NET Frameworku, Mono aj NinjaTrader), jadro ani adaptéry (NinjaTrader,
  MT5, most) nepoznajú stratégiu menom (`[TradeBotEngine("kľúč")]`), a zmena logiky musí prejsť paritou
  bar po bare proti Python predlohe (`python -m tester.compare.csharp_parity`,
  `tester/tests/test_csharp_parity.py`). Zmena v `ibs` = tá istá zmena v `csharp/…/IbsNet`, v `orb` v `csharp/…/OrbNet`.
  [docs/NINJATRADER.md](docs/NINJATRADER.md). MetaTrader 5 volá tú istú DLL cez statickú fasádu
  `StaticHost` (jediná trieda v globálnom namespace — MQL5 iné nevidí) z Expert Advisora v MQL5 (`tradebot/adapters/mt5`, šablóny `deploy/mt5`);
  fasáda musí dávať to isté, čo most (`tester/tests/test_mt5_static_host.py`) — [docs/MT5.md](docs/MT5.md).
  Staré kľúče `ibsninja`/`orbninja` sú aliasy (`tradebot.strategies.ALIASES`), história sa neprepisuje.
- Zoznam a hľadanie v histórii idú cez odvodený sqlite index (`tester/webapp/index.py`,
  `runs/.index/`, gitignored) — nikdy nie cez parsovanie všetkých `run.json`. Index musí
  odpovedať presne to isté, čo prehľadanie súborov (`tester/tests/test_run_index.py`).
  Staré behy sa z histórie odkladajú do `tester/archive/` (`cli archive`, vratné cez
  `--restore`); hromadné mazanie behov bez archívu je zakázané.
- Cesty v repozitári sú na jednom mieste v `tradebot/core/paths.py`; nikde inde sa nepíšu.
- Vyšší TF sa z 1m skladá výhradne cez `tradebot/core/candles.py` (webapp graf, simulátor,
  emulátor, súbory pre Freqtrade) — keby sa pravidlo rozišlo, porovnanie platforiem prestane
  niečo znamenať. Freqtrade si TF sám nedopočíta, pre `--timeframe` chce súbor na disku.
- Commity v štýle histórie: slovenská veta v imperatíve, čo a prečo.
- Backtesty, ktoré majú byť v histórii webapp, spúšťaj cez `python -m tester.webapp.cli run`
  (holý Freqtrade CLI ich do `runs/` nezapíše) — inak je to jedno.
- Viac strojov: jeden hub (`python -m tester.hub serve`, verejná adresa, token), agenti
  s `tester/agent.json` (webapp alebo `python -m tester.hub agent`), zadanie `cli run
  --remote [--queue --max-wait MIN]` — [docs/HUB.md](docs/HUB.md). Hub nepozná stratégie
  menom, nesie `params` + `settings` behu; výsledok je adresár behu, ktorý sa vráti do
  histórie zadávateľa.

Podrobnosti: [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) (prehľad a cesta dát),
[docs/ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md) (návrh),
[docs/FREQTRADE.md](docs/FREQTRADE.md) (krypto vetva), [docs/MULTICHARTS.md](docs/MULTICHARTS.md)
(MultiCharts vetva), [docs/NINJATRADER.md](docs/NINJATRADER.md) (C# jadro a NinjaTrader), [docs/MT5.md](docs/MT5.md) (MetaTrader 5), [docs/HYPEROPT.md](docs/HYPEROPT.md) (hľadanie parametrov, FreqAI),
[docs/TYPY_STRATEGII.md](docs/TYPY_STRATEGII.md) (charakter stratégie a čo z neho vyplýva),
[docs/ANALYTIKA.md](docs/ANALYTIKA.md) (základná analytika stratégie a posudok),
[docs/DATA.md](docs/DATA.md) (dáta), [docs/WEBAPP.md](docs/WEBAPP.md)
(Tester), [docs/HUB.md](docs/HUB.md) (distribuované počítanie),
[docs/RUNNING.md](docs/RUNNING.md) (rozcestník), [README.md](README.md).

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

## Podrobné postupy pre testera (načítaj až keď treba)

Presné príkazy (backtest do histórie, sweep/hyperopt/matrix, len nastaviť parametre vo webapp,
čítanie výsledkov, štart/reštart webapp, aktualizácia, história cez GitHub, testy, riešenie problémov)
sú v [CLAUDE.archive.md](CLAUDE.archive.md). **Neimportuj ho cez @** — prečítaj ho nástrojom Read,
až keď ich v režime TESTER potrebuješ. Pravidlo 8 („len nastaviť = nič nespúšťaj") platí vždy.
