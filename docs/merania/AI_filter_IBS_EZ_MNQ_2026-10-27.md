# AI filter (FreqAI) na IBS Entry Zone, MNQ — 2026-10-27

Otázka: pridá FreqAI niečo profilu IBS EZ, ktorý prešiel smernicou, keď (B) preskočí signály
s nízkou istotou, alebo (C) podľa istoty zmenší či zväčší pozíciu? **Nie** — na piatich rokoch je
najlepší PF bez AI a obe vetvy sú lepšie len v niektorých rokoch, ako pri hode mincou.
Rovnaký záver ako na IBS v [AI_filter_2026-09-10.md](AI_filter_2026-09-10.md).

## Zadanie

| | |
|---|---|
| profil | `tester/profiles/PRESIEL_SMERNICAMI_IBS_Entry_Zone_1.json` (`ibsentry`), `--set maxLossDollar=500` |
| trh | MNQ/USD (Databento), 3m, 1m detail, poplatok 1,755e-05 |
| engine | Freqtrade, `--exchange tester`, `--wallet 2000000` |
| obdobie | `20211001-20260904` jedným behom (dáta od 2019 → 730 dní tréningu pred začiatkom) |
| AI | `LightGBMClassifier`, tréning 730 dní, pretrénovanie 180 dní, sedem príznakov (AI_TESTING.md §9) |
| A | bez AI |
| B | `--ai --ai-min-prob 0.80` (prah nad winrate ~75 %) |
| C | `--ai --ai-min-prob 0 --ai-adjust size=0.5:1.5` (nič sa nezahodí, mení sa len veľkosť) |

**Peňaženka:** s predvolenými 10 000 $ Freqtrade odmietne všetky vstupy (586 signálov, 0 obchodov —
beh `20261027-082026-0d6350`), lebo pozícia MNQ pri riziku na obchod má nominál stovky tisíc $.
Riziko na obchod určuje `maxLossDollar`, nie peňaženka, takže zisk v $ sa s väčšou peňaženkou nemení.

## Výsledok — 10/2021 až 9/2026

| | A bez AI | B filter 0,80 | C veľkosť 0,5–1,5× |
|---|---|---|---|
| beh | `20261027-083154-e549d6` | `20261027-083307-1e522c` | `20261027-084200-60c41a` |
| obchody | 882 | 612 | 882 |
| WR | 72,8 % | 73,5 % | 72,8 % |
| **PF** | **1,50** | 1,48 | 1,47 |
| zisk | +44 844 $ | +30 670 $ | +52 190 $ |
| max prepad (z obchodov) | **4 038 $** | 5 180 $ | 5 858 $ |
| break-even | **0,0161 %** | 0,0154 % | 0,0150 % |

PF po rokoch (obchody podľa dátumu vstupu):

| rok | A | B | C |
|---|---|---|---|
| 21/22 | 1,55 (261) | **1,57** (172) | 1,51 |
| 22/23 | **1,10** (131) | 1,03 (103) | 1,06 |
| 23/24 | **1,19** (99) | 1,03 (64) | 1,15 |
| 24/25 | 1,76 (166) | **2,20** (112) | 1,85 |
| 25/26 | **1,81** (225) | 1,67 (161) | 1,76 |
| lepšie než A | — | 2 z 5 | 1 z 5 |

**B — čo filter vyhodil.** 273 vyhodených obchodov má PF 1,56, 609 ponechaných PF 1,48: filter
v súčte zahadzuje mierne lepšie obchody. Po rokoch sa to prehadzuje (24/25 ponechané 2,20 vs vyhodené 1,17;
23/24 ponechané 1,01 vs vyhodené 1,69) — znamienko bez stability je šum, nie model.

**C — prečo viac zisku.** Priemerný násobok veľkosti vyšiel ~1,2×, takže +16 % zisku je väčšia expozícia,
nie lepší výber: na stratových obchodoch dával model v priemere väčšiu pozíciu (1,24×) než na ziskových
(1,18×, posledný rok), prepad narástol o 45 % a PF klesol v štyroch rokoch z piatich.

Freqtrade má iný fill model než emulátor MultiCharts, na ktorom profil prešiel smernicou
(napr. 22/23 PF 1,10) — čísla porovnávať len A/B/C medzi sebou.

## Behy zo skúšania (posledný rok, tiež v histórii)

| beh | čo |
|---|---|
| `20261027-082026-0d6350` | C, riziko 1 000 $, peňaženka 10 000 $ → 0 obchodov |
| `20261027-082147-61d0f3`, `20261027-082235-92d165` | C a A, riziko 1 000 $ (profilové) — C +41 337 $ PF 1,74, A +33 344 $ PF 1,77 |
| `20261027-082306-402054`, `20261027-082325-f62e69`, `20261027-082642-a08fca` | A, C, B na `20250904-20260904`, riziko 500 $ — PF 1,81 / 1,75 / 1,73 |

## Záver

FreqAI so siedmimi príznakmi na IBS EZ nič nepridáva a ostáva vypnuté. Model má ~150 nálepiek
za rok a stratégia, ktorá už prešla smernicou, má obchody podobné — sedem hrubých príznakov ich
nerozlíši. Pred ďalším pokusom najprv bez modelu zistiť, či je niektorá skupina obchodov (hodina,
volatilita, trend, veľkosť stopu) stabilne horšia po rokoch; ak nie, model nemá čo nájsť. Potom
viac nálepiek (MNQ + ES + NAS100 spolu, voľnejší engine) a lepšie príznaky — s ohľadom na počet skúšok.

## Pre ďalšiu prácu (Rasto)

Používateľ to 27. 10. odložil ako zatiaľ nepoužiteľné a ďalšie ladenie nechal na kolegu. Toto stačí, aby sa dalo pokračovať.

**Inštalácia** (na macOS bez nej `import lightgbm` padá na `libomp.dylib`):

```bash
brew install libomp
.venv/bin/pip install "freqtrade[freqai]==$(.venv/bin/python -c 'import freqtrade;print(freqtrade.__version__)')" "joblib<1.6"
.venv/bin/python -c "import lightgbm, freqtrade.freqai; print('ok')"
```

Verziu Freqtradu treba pripnúť, inak pip nainštaluje novší a zmení výsledky všetkých behov.

**Zopakovanie behov** (jeden beh na 5 rokov trvá 1–9 min; B a C sú pomalšie, lebo trénujú):

```bash
.venv/bin/python -m tester.webapp.cli run --strategy ibsentry \
  --profile tester/profiles/PRESIEL_SMERNICAMI_IBS_Entry_Zone_1.json --set maxLossDollar=500 \
  --pair MNQ/USD --engine freqtrade --exchange tester --timeframe 3m --fee 1.755e-05 \
  --wallet 2000000 --timerange 20211001-20260904 \
  --ai --ai-min-prob 0.80 --note "FreqAI B: …"
```

Rozbor po rokoch a vyhodených obchodov: párovať `trades.json` behu s AI a behu A podľa `open_date`.
Obchod, ktorý chýba v behu B, filter vyhodil.

**Kde je kód:**

| čo | kde |
|---|---|
| príznaky (7), nálepka TP/SL, filter a škálovanie plánu | `tradebot/adapters/freqtrade/ai.py` (`feature_engineering_*`, `set_freqai_targets`) |
| config FreqAI (okná, model, vypnuté štandardné rozširovanie) | `tester/engines.py` (`AI_DEFAULTS`, `ai_config`) |
| čo smie model meniť (`size`, `tp`, `sl`) | `AI_ADJUSTABLE` v `tradebot/strategies/hyperopt.py` a v `hyperopt.py` stratégie |
| prepínače CLI / formulár | `tester/webapp/cli.py` (`--ai*`), `tester/webapp/api/settings.py` (`ai_for`), `tester/webapp/command.py` |
| návod | [tester/AI_TESTING.md §9](../../tester/AI_TESTING.md), [docs/HYPEROPT.md](../HYPEROPT.md) („FreqAI: pripojený ako filter nad portom“) |

**Obmedzenia, s ktorými treba rátať:**
- AI ide len cez Freqtrade. Emulátor MultiCharts ani natívny C# backtest, na ktorých stratégie prechádzajú smernicou, ho nemajú. Výsledok sa preto porovnáva len s behom A vo Freqtrade.
- Výsledok nie je deterministický. Modely sa ukladajú pod `identifier` (`tb-<stratégia>-<hash profilu>`), pri rovnakom profile a okne sa načítajú namiesto tréningu.
- Každé skúšané nastavenie AI (prah, okná, model, príznaky) je ďalšia skúška. Pri porovnávaní treba rátať, koľko ich bolo, a overovať na rokoch, na ktorých sa neladilo.

**Návrh poradia:**
1. Rozbor skupín obchodov behu A bez modelu: hodina, volatilita voči normálu, trend, veľkosť stopu, deň v týždni, vzdialenosť od VWAP. Hľadá sa skupina, ktorá je horšia **každý** rok. Ak taká nie je, model nemá čo nájsť.
2. Ak sa nájde, najprv ju skúsiť ako jednoduché pravidlo, ktoré je deterministické a dá sa dať aj do C# jadra. AI až potom.
3. Viac nálepiek: tréning na MNQ + ES + NAS100 spolu, alebo voľnejšie nastavenie enginu s viac signálmi.
4. Lepšie príznaky v `ai.py`: objem pri vstupe, čas od otvorenia NY, vzdialenosť od VWAP, režim dňa, výsledok predošlého obchodu. Vždy len pár, nie desiatky.
